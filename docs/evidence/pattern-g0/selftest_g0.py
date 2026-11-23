"""Self-test of check_g0.py: can it FAIL, and for the right reason? Typed exits; infrastructure is never a detection.
The real state of the repository is checked as it is (A). The positive controls (B) run in a TEMPORARY ROOT that copies the bound files and adds a FIXTURE of the OP-1 specification text (the real one does not exist yet),
so that a complete package can be shown to pass. THE FIXTURE IS A TEST DOUBLE: the positive controls show that the STRUCTURE and the integrity rules accept a complete package; they are not, and must not be read as,
a check of the content of the real OP-1 specification, which only a review can judge. Every planted fault (C) is applied to that complete package and is counted only when the check does NOT reach READY_FOR_OWNER_CLOSURE or CLOSED,
exits 1, and prints a FAIL-EXPECT line of the intended check. D: an unreadable input exits 2.
Exit: 0 all as expected, 1 a mutant was not detected or a control failed, 2 the self-test itself could not run."""
import copy, hashlib, os, shutil, subprocess, sys, tempfile
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
CHECK = os.path.join(HERE, "check_g0.py")
PLAN_DIR = os.path.join("docs", "design", "pattern-profile-plan")
FIXTURE = os.path.join("docs", "design", "pattern-profile-spec", "op1-fixture.md")
FIXTURE_TEXT = ("FIXTURE of the specification text of OP-1 (a test double, not the real text): the YAML 1.2 core schema, the explicit tag rules, the duplicate key rule, "
                "the alias rule and the merge key rule.\n")
bad = 0


def report(label, ok, extra=""):
    global bad
    print("%-110s %s %s" % (label, "OK" if ok else "FAIL", extra))
    bad += not ok


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(args):
    r = subprocess.run([sys.executable, CHECK] + args, capture_output=True, text=True, timeout=600)
    return r.returncode, r.stdout + r.stderr


def build(root_dir, rec_mut=None, file_mut=None, spec_fixture=True, closure=None, rebind=True, fixture_after=None, fixture_replace=None):
    """a temporary root: the bound files copied, the record (mutated) written, the fixture added; returns the check's arguments"""
    import yaml
    rec = yaml.safe_load(open(os.path.join(ROOT, PLAN_DIR, "decisions.yaml"), encoding="utf-8"))
    for k, f in rec["bound_to"]["files"].items():
        dst = os.path.join(root_dir, f["path"]); os.makedirs(os.path.dirname(dst), exist_ok=True)
        data = open(os.path.join(ROOT, f["path"]), "rb").read()
        if file_mut and k in file_mut:
            data = file_mut[k](data.decode("utf-8")).encode("utf-8")
        open(dst, "wb").write(data)
        if rebind:
            f["sha256"] = sha(data)
    if spec_fixture:
        text = FIXTURE_TEXT.replace(*fixture_replace) if fixture_replace else FIXTURE_TEXT
        p = os.path.join(root_dir, FIXTURE); open(p, "w", encoding="utf-8").write(text)
        for d in rec["decisions"]:
            if d["id"] == "OP-1":
                d["spec_text"] = {"path": FIXTURE, "sha256": sha(text.encode("utf-8"))}
        if fixture_after:
            open(p, "w", encoding="utf-8").write(FIXTURE_TEXT + fixture_after)
    if rec_mut:
        rec_mut(rec)
    os.makedirs(os.path.join(root_dir, PLAN_DIR), exist_ok=True)
    rp = os.path.join(root_dir, PLAN_DIR, "decisions.yaml")
    open(rp, "w", encoding="utf-8").write(yaml.safe_dump(rec, sort_keys=False, allow_unicode=True))
    args = ["--root", root_dir, "--record", rp, "--plan", os.path.join(root_dir, rec["bound_to"]["files"]["plan"]["path"])]
    if closure is not None:
        cp = os.path.join(root_dir, PLAN_DIR, "g0-closure.yaml")
        c = {"closure_format": 1, "gate": "G-0", "closed_by": "owner", "date": "2026-11-24", "decisions_sha256": sha(open(rp, "rb").read())}
        c.update(closure)
        open(cp, "w", encoding="utf-8").write(yaml.safe_dump(c, sort_keys=False))
        args += ["--closure", cp]
    return args


def verdict(o):
    return [l for l in o.splitlines() if l.startswith("G-0: ")][-1][5:] if "G-0: " in o else "(none)"


def main():
    # A the real state
    rc, o = run([])
    named = [l.split()[1] for l in o.splitlines() if l.startswith("FAIL-EXPECT")]
    import yaml
    real = yaml.safe_load(open(os.path.join(ROOT, PLAN_DIR, "decisions.yaml"), encoding="utf-8"))
    if next(x for x in real["decisions"] if x["id"] == "OP-1").get("spec_text") is None:
        report("A real state: G-0 is NOT_READY for exactly one reason, the missing OP-1 specification text", rc == 1 and verdict(o) == "NOT_READY" and named == ["evidence.op1.spec-text"], "exit=%d fails=%s" % (rc, named))
    else:                                       # the record has moved on: the real package must then be complete (this branch is for the day the specification text is recorded)
        report("A real state: the OP-1 specification text is recorded, so every prerequisite is met and evidenced", rc == 0 and verdict(o) in ("READY_FOR_OWNER_CLOSURE", "CLOSED") and not named, "exit=%d fails=%s" % (rc, named))
    report("A real state: OP-3 (partial) and OP-4 do not block G-0", "OP-3     PARTIAL" in o and "not a G-0 prerequisite" in o and "decision.status.OP-3" not in o)
    # B positive controls
    d = tempfile.mkdtemp()
    try:
        rc, o = run(build(d))
        report("B positive control: a complete package is READY_FOR_OWNER_CLOSURE with OP-3 partial, and the gate is not closed", rc == 0 and verdict(o) == "READY_FOR_OWNER_CLOSURE" and "none (the gate is not closed" in o, "exit=%d" % rc)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    d = tempfile.mkdtemp()
    try:
        rc, o = run(build(d, closure={}))
        report("B positive control: a valid owner closure record that names the digest of the record gives CLOSED", rc == 0 and verdict(o) == "CLOSED", "exit=%d" % rc)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp()
    try:
        rc, o = run(build(d, rec_mut=lambda r: [x.__setitem__("evidence_files", x["evidence_files"] + ["obligations"]) for x in r["decisions"] if x["id"] == "D1"]))
        report("B positive control: an EXTRA evidence reference that is a bound, verified contract key does not reject a complete package", rc == 0 and verdict(o) == "READY_FOR_OWNER_CLOSURE", "exit=%d" % rc)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    def drop(i):
        return lambda r: r.__setitem__("decisions", [x for x in r["decisions"] if x["id"] != i])

    def setf(i, k, v):
        def f(r):
            for x in r["decisions"]:
                if x["id"] == i:
                    x[k] = v
        return f

    def both(*fs):
        return lambda r: [f(r) for f in fs]

    def row(rec, start, newrows):
        """replace the row of the owner's verbatim table that starts with `start` by newrows (a list of lines)"""
        lines = rec["source"]["verbatim"].split("\n"); out = []
        for l in lines:
            out += newrows if l.startswith(start) else [l]
        rec["source"]["verbatim"] = "\n".join(out)

    def src(k, v):
        return lambda r: r["source"].__setitem__(k, v)

    faults = [
        ("a decision is missing (D3)", dict(rec_mut=drop("D3")), "decision.missing.D3", "NOT_READY"),
        ("a contradictory record (D1 recorded twice, confirmed and rejected)", dict(rec_mut=lambda r: r["decisions"].append({"id": "D1", "kind": "decision", "status": "rejected", "text": "x"})), "decision.contradiction.D1", "INVALID"),
        ("the record disagrees with the owner's statement (D2 rejected, the statement says CONFIRMED)", dict(rec_mut=setf("D2", "status", "rejected")), "decision.vs-source.D2", "INVALID"),
        ("OP-3 recorded as decided although the owner's statement says PARTIAL", dict(rec_mut=setf("OP-3", "status", "decided")), "decision.vs-source.OP-3", "INVALID"),
        ("missing provenance (the source reference is empty)", dict(rec_mut=src("reference", "")), "source.provenance", "INVALID"),
        ("missing provenance (no verbatim statement)", dict(rec_mut=src("verbatim", "")), "source.provenance", "INVALID"),
        ("a wrong SHA-256 (the specification as recorded is not the file)", dict(rec_mut=lambda r: r["bound_to"]["files"]["spec"].__setitem__("sha256", "0" * 64)), "bound.sha.spec", "INVALID"),
        ("a bound file changed after the decision (the plan edited, the recorded SHA kept)", dict(file_mut={"plan": lambda t: t + "# edited\n"}, rebind=False), "bound.sha.plan", "INVALID"),
        ("a specification text of OP-1 that does not treat the aliases (a trivial text is not evidence)", dict(fixture_replace=("the alias rule and ", "")), "evidence.op1.spec-text", "INVALID"),
        ("an unmet prerequisite: the specification text of OP-1 is not recorded", dict(spec_fixture=False), "evidence.op1.spec-text", "NOT_READY"),
        ("the recorded specification text of OP-1 changed after its SHA-256 was recorded", dict(fixture_after="an edit after the record\n"), "evidence.op1.spec-text", "INVALID"),
        ("a prerequisite not confirmed (D1 on hold) while the 47 cases are deferred", dict(rec_mut=both(setf("D1", "status", "hold"), setf("OP-2", "status", "deferred"), lambda r: row(r, "| D1\u2013D6", ["| D1 | x | **HOLD** |", "| D2\u2013D6 | x | **CONFIRMED** |"]), lambda r: row(r, "| OP-2", ["| OP-2 | x | **DEFERRED** |"]))), "decision.status.D1", "NOT_READY"),
        ("the 47 cases accepted while D1, which they depend on, is on hold", dict(rec_mut=both(setf("D1", "status", "hold"), lambda r: row(r, "| D1\u2013D6", ["| D1 | x | **HOLD** |", "| D2\u2013D6 | x | **CONFIRMED** |"]))), "op2.depends.hold.E-PIN-01", "INVALID"),
        ("OP-2 treated as a normative conformance set (normative true)", dict(rec_mut=setf("OP-2", "normative", True)), "op2.normative", "INVALID"),
        ("OP-2 accepts 46 cases, not 47", dict(rec_mut=setf("OP-2", "case_count", 46)), "op2.count", "INVALID"),
        ("a case that depends on a decision on hold (E-PIN-01 depends on D7)", dict(file_mut={"extension_review": lambda t: t.replace("{id: E-PIN-01, rule: \"O-VA-01 step 3\", derive: \"one declaration, the value true; not the int 1 (a bool is not an int); so the single value is unknown\", depends: [D1]", "{id: E-PIN-01, rule: \"O-VA-01 step 3\", derive: \"one declaration, the value true; not the int 1 (a bool is not an int); so the single value is unknown\", depends: [D1, D7]", 1)}), "op2.depends.hold.E-PIN-01", "INVALID"),
        ("OP-3 recorded as closing at G-0 (the plan says G-6)", dict(rec_mut=setf("OP-3", "closes_at", "G-0")), "plan.closes_at.OP-3", "INVALID"),
        ("OP-3 partial without the precondition for the G-6 measurement", dict(rec_mut=setf("OP-3", "precondition", "")), "op3.precondition", "INVALID"),
        ("the plan demands a later open point at G-0 (G-0 names OP-3)", dict(file_mut={"plan": lambda t: t.replace("the 47 extension cases accepted, rejected or deferred by the owner (OP-2)\"", "the 47 extension cases accepted, rejected or deferred by the owner (OP-2); OP-3 closed\"", 1)}), "plan.g0.late-conditions", "INVALID"),
        ("the plan no longer names OP-2 at G-0", dict(file_mut={"plan": lambda t: t.replace("(OP-2)\", evidence: \"the owner's recorded decisions", "\", evidence: \"the owner's recorded decisions", 1)}), "plan.g0.criteria", "INVALID"),
        ("a decision the plan does not know (D9)", dict(rec_mut=lambda r: r["decisions"].append({"id": "D9", "kind": "decision", "status": "confirmed", "text": "x"})), "decision.unknown.D9", "INVALID"),
        ("a closure record while OP-1 has no specification text (closure without evidence)", dict(spec_fixture=False, closure={}), "closure.without-evidence", "INVALID"),
        ("a closure record that names another decision record (wrong digest)", dict(closure={"decisions_sha256": "1" * 64}), "closure.digest", "INVALID"),
        ("a closure record that is not an owner closure of G-0", dict(closure={"closed_by": "reviewer"}), "closure.format", "INVALID"),
        ("a decision that the owner's statement does not mention (OP-4 removed from the verbatim table)", dict(rec_mut=lambda r: row(r, "| OP-4", [])), "decision.not-in-source.OP-4", "INVALID"),
        ("the record format is not 1", dict(rec_mut=lambda r: r.__setitem__("decision_record_format", 2)), "record.format", "INVALID"),
        ("the base commit is not a commit id", dict(rec_mut=lambda r: r["bound_to"].__setitem__("base_commit", "main")), "bound.base_commit", "INVALID"),
        ("a bound file that does not exist (the specification path is wrong)", dict(rec_mut=lambda r: r["bound_to"]["files"]["spec"].__setitem__("path", "docs/en/NO-SUCH-FILE.md")), "bound.missing.spec", "INVALID"),
        ("the evidence of D1 names an unknown key, ALL required evidence kept (isolated: only the dangling reference is wrong)", dict(rec_mut=setf("D1", "evidence_files", ["spec", "extension_review", "no_such_key"])), "evidence.ref.D1", "INVALID"),
        ("the evidence of D1 names a contract key that is not bound in the record (obligations removed from bound_to), required evidence kept", dict(rec_mut=both(setf("D1", "evidence_files", ["spec", "extension_review", "obligations"]), lambda r: r["bound_to"]["files"].pop("obligations"))), "evidence.ref.D1", "INVALID"),
        ("the evidence of OP-3, which G-0 does not need, names an unknown key (every declared reference is checked)", dict(rec_mut=setf("OP-3", "evidence_files", ["plan", "ghost"])), "evidence.ref.OP-3", "INVALID"),
        ("the recorded specification text of OP-1 does not exist (a wrong path)", dict(rec_mut=lambda r: [x.__setitem__("spec_text", {"path": "docs/design/pattern-profile-spec/NO-SUCH.md", "sha256": "0" * 64}) for x in r["decisions"] if x["id"] == "OP-1"]), "evidence.op1.spec-text", "INVALID"),
        ("OP-1 is not decided (the owner's statement and the record both say PARTIAL)", dict(rec_mut=both(setf("OP-1", "status", "partial"), lambda r: row(r, "| OP-1", ["| OP-1 | x | **PARTIAL** |"]))), "decision.status.OP-1", "NOT_READY"),
        ("OP-2 is on hold, which is no owner outcome of accepted, rejected or deferred", dict(rec_mut=both(setf("OP-2", "status", "hold"), lambda r: row(r, "| OP-2", ["| OP-2 | x | **HOLD** |"]))), "decision.status.OP-2", "NOT_READY"),
        ("the OP-1 decision is missing", dict(rec_mut=drop("OP-1")), "decision.missing.OP-1", "NOT_READY"),
        ("the OP-2 decision is missing", dict(rec_mut=drop("OP-2")), "decision.missing.OP-2", "NOT_READY"),
        ("an accepted case depends on a decision that the owner did not confirm and that is not on hold (D2 rejected, E-PIN-04 depends on it)", dict(rec_mut=both(setf("D2", "status", "rejected"), lambda r: row(r, "| D1\u2013D6", ["| D1 | x | **CONFIRMED** |", "| D2 | x | **REJECTED** |", "| D3\u2013D6 | x | **CONFIRMED** |"]))), "op2.depends.E-PIN-04", "NOT_READY"),
        ("the evidence of D1 is an EMPTY list (the obligation to evidence the decision must not be removable)", dict(rec_mut=setf("D1", "evidence_files", [])), "evidence.files.D1", "NOT_READY"),
        ("the evidence_files field of D1 is removed altogether", dict(rec_mut=lambda r: [x.pop("evidence_files") for x in r["decisions"] if x["id"] == "D1"]), "evidence.files.D1", "NOT_READY"),
        ("the evidence of D2 declares only the specification, not the extension review", dict(rec_mut=setf("D2", "evidence_files", ["spec"])), "evidence.files.D2", "NOT_READY"),
        ("the evidence of OP-1 is an empty list", dict(rec_mut=setf("OP-1", "evidence_files", [])), "evidence.files.OP-1", "NOT_READY"),
        ("the evidence of OP-2 is an empty list", dict(rec_mut=setf("OP-2", "evidence_files", [])), "evidence.files.OP-2", "NOT_READY"),
        ("the key spec is bound to another existing file (the plan) whose digest is recorded correctly", dict(rec_mut=lambda r: r["bound_to"]["files"]["spec"].update(path="docs/design/pattern-profile-plan/plan.yaml", sha256=r["bound_to"]["files"]["plan"]["sha256"])), "bound.path.spec", "INVALID"),
    ]
    # The exact set of failures of each planted fault with a bounded set of causes (a cascade of more than 8 labels keeps the needle only). HOW THESE SETS WERE MADE: each is the observed output of the check on that fault, read by the author
    # and accepted only if every label follows causally from the planted fault (the cascades are explained in section 5 of docs/en/GRAMMAR-PATTERN-OWNER-DECISIONS.md). They are regression pins of the behaviour the author judged
    # right, not an independent proof; an independent review of each set is what would make them one.
    exact = {
        'a decision is missing (D3)': ['decision.missing.D3', 'op2.depends.E-PIN-14', 'op2.depends.E-PIN-15'],
        'a contradictory record (D1 recorded twice, confirmed and rejected)': ['decision.contradiction.D1'],
        "the record disagrees with the owner's statement (D2 rejected, the statement says CONFIRMED)": ['decision.status.D2', 'decision.vs-source.D2', 'op2.depends.E-PIN-04'],
        "OP-3 recorded as decided although the owner's statement says PARTIAL": ['decision.vs-source.OP-3'],
        'missing provenance (the source reference is empty)': ['source.provenance'],
        'a wrong SHA-256 (the specification as recorded is not the file)': ['bound.sha.spec', 'evidence.files.D1', 'evidence.files.D2', 'evidence.files.D3', 'evidence.files.D4', 'evidence.files.D5', 'evidence.files.D6'],
        'a bound file changed after the decision (the plan edited, the recorded SHA kept)': ['bound.sha.plan', 'evidence.files.OP-1'],
        'a specification text of OP-1 that does not treat the aliases (a trivial text is not evidence)': ['evidence.op1.spec-text'],
        'an unmet prerequisite: the specification text of OP-1 is not recorded': ['evidence.op1.spec-text'],
        'the recorded specification text of OP-1 changed after its SHA-256 was recorded': ['evidence.op1.spec-text'],
        'a prerequisite not confirmed (D1 on hold) while the 47 cases are deferred': ['decision.status.D1'],
        'OP-2 treated as a normative conformance set (normative true)': ['op2.normative'],
        'OP-2 accepts 46 cases, not 47': ['op2.count'],
        'a case that depends on a decision on hold (E-PIN-01 depends on D7)': ['op2.depends.hold.E-PIN-01'],
        'OP-3 recorded as closing at G-0 (the plan says G-6)': ['plan.closes_at.OP-3'],
        'OP-3 partial without the precondition for the G-6 measurement': ['op3.precondition'],
        'the plan demands a later open point at G-0 (G-0 names OP-3)': ['plan.g0.late-conditions'],
        'the plan no longer names OP-2 at G-0': ['plan.g0.criteria'],
        'a decision the plan does not know (D9)': ['decision.unknown.D9'],
        'a closure record while OP-1 has no specification text (closure without evidence)': ['closure.without-evidence', 'evidence.op1.spec-text'],
        'a closure record that names another decision record (wrong digest)': ['closure.digest'],
        'a closure record that is not an owner closure of G-0': ['closure.format'],
        "a decision that the owner's statement does not mention (OP-4 removed from the verbatim table)": ['decision.not-in-source.OP-4'],
        'the record format is not 1': ['record.format'],
        'the base commit is not a commit id': ['bound.base_commit'],
        'a bound file that does not exist (the specification path is wrong)': ['bound.missing.spec', 'bound.path.spec', 'evidence.files.D1', 'evidence.files.D2', 'evidence.files.D3', 'evidence.files.D4', 'evidence.files.D5', 'evidence.files.D6'],
        'the evidence of D1 names an unknown key, ALL required evidence kept (isolated: only the dangling reference is wrong)': ['evidence.ref.D1'],
        'the evidence of D1 names a contract key that is not bound in the record (obligations removed from bound_to), required evidence kept': ['evidence.ref.D1'],
        'the evidence of OP-3, which G-0 does not need, names an unknown key (every declared reference is checked)': ['evidence.ref.OP-3'],
        'the recorded specification text of OP-1 does not exist (a wrong path)': ['evidence.op1.spec-text'],
        "OP-1 is not decided (the owner's statement and the record both say PARTIAL)": ['decision.status.OP-1'],
        'OP-2 is on hold, which is no owner outcome of accepted, rejected or deferred': ['decision.status.OP-2'],
        'the OP-1 decision is missing': ['decision.missing.OP-1'],
        'the OP-2 decision is missing': ['decision.missing.OP-2'],
        'an accepted case depends on a decision that the owner did not confirm and that is not on hold (D2 rejected, E-PIN-04 depends on it)': ['decision.status.D2', 'op2.depends.E-PIN-04'],
        'the evidence of D1 is an EMPTY list (the obligation to evidence the decision must not be removable)': ['evidence.files.D1'],
        'the evidence_files field of D1 is removed altogether': ['evidence.files.D1'],
        'the evidence of D2 declares only the specification, not the extension review': ['evidence.files.D2'],
        'the evidence of OP-1 is an empty list': ['evidence.files.OP-1'],
        'the evidence of OP-2 is an empty list': ['evidence.files.OP-2'],
        'the key spec is bound to another existing file (the plan) whose digest is recorded correctly': ['bound.path.spec'],
    }
    for entry in faults:
        name, kw, needle, want = entry[:4]
        d = tempfile.mkdtemp()
        try:
            rc, o = run(build(d, **kw))
        finally:
            shutil.rmtree(d, ignore_errors=True)
        labels = sorted(l.split()[1] for l in o.splitlines() if l.startswith("FAIL-EXPECT"))
        named = [l for l in labels if needle in l]
        v = verdict(o)
        ok = rc == 1 and bool(named) and v == want and v not in ("READY_FOR_OWNER_CLOSURE", "CLOSED")
        if os.environ.get("CIC_G0_SHOW_LABELS"):
            print("LABELS %s => %s" % (name, labels))
        if name in exact:                                   # where the result has a bounded set of causes, the WHOLE set of failures is compared, not only the needle
            ok = ok and labels == sorted(exact[name])
        report("C planted: " + name, ok, "exit=%d verdict=%s needle=%s%s" % (rc, v, needle, " exact-set" if name in exact else ""))
    # E the base commit verified in git (--verify-git): the real files, a planted record
    def git_run(rec_mut=None):
        rec = yaml.safe_load(open(os.path.join(ROOT, PLAN_DIR, "decisions.yaml"), encoding="utf-8"))
        if rec_mut:
            rec_mut(rec)
        d = tempfile.mkdtemp()
        try:
            rp = os.path.join(d, "decisions.yaml"); open(rp, "w", encoding="utf-8").write(yaml.safe_dump(rec, sort_keys=False, allow_unicode=True))
            rc, o = run(["--root", ROOT, "--record", rp, "--plan", os.path.join(ROOT, PLAN_DIR, "plan.yaml"), "--verify-git"])
        finally:
            shutil.rmtree(d, ignore_errors=True)
        return rc, o, sorted(l.split()[1] for l in o.splitlines() if l.startswith("FAIL-EXPECT"))

    rc, o, labels = git_run()
    report("E --verify-git on the real record: the commit exists and every bound file is its blob (only the OP-1 text is still missing)", "base commit: verified in git" in o and labels == ["evidence.op1.spec-text"] or (labels == [] and rc == 0), "exit=%d labels=%s" % (rc, labels))
    rc, o, labels = git_run(lambda r: r["bound_to"].__setitem__("base_commit", "1" * 40))
    report("E --verify-git: a base commit that does not exist in the repository", rc == 1 and "bound.git.commit" in labels and verdict(o) == "INVALID", "exit=%d labels=%s" % (rc, labels))
    rc, o, labels = git_run(lambda r: r["bound_to"].__setitem__("base_commit", "7446f1f57e2bc3c9fe17e9ee7d986386903d61bc"))
    want_blobs = sorted("bound.git.blob.%s" % k for k in ("plan", "plan_doc", "extension_review", "review_doc"))     # the files of #54 and #53; extension-cases.yaml, the specification, the obligations and the vectors already exist, unchanged, at that commit (#52)
    report("E --verify-git: an older commit (#52) that exists but whose tree lacks the files of #53 and #54 recorded as bound to it, while the unchanged files match", rc == 1 and sorted(l for l in labels if l.startswith("bound.git")) == want_blobs and verdict(o) == "INVALID", "exit=%d labels=%s" % (rc, labels))
    rc, o = run(["--record", "/nonexistent/decisions.yaml"])
    report("D infra: the decision record is unreadable (exit 2, not a detection)", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)
    print("self-test: %s" % ("all as expected" if not bad else "%d problem(s)" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
