"""Self-test of check_t3_readiness.py: can it FAIL, and for the right reason? Typed exits; infrastructure is never a detection.
A: the real record. B: the STATE MACHINE in a TEMPORARY ROOT with fixture evidence: a prepared package (every decision confirmed, every pre-execution condition verified) is PREPARED_FOR_OWNER_GO and is NOT the GO; with a valid
separate GO record it is GO_RECORDED; capture and preserve evidence then advance it to EVIDENCE_CAPTURED and PRESERVATION_COMPLETE; the preservation ORDER (staged or strict) changes which conditions are pre-execution; valid NOT_PREPARED
cases stay NOT_PREPARED. C: planted faults (the record, the GO record, the manifest set, the document), each counted only when the verdict is INVALID, the exit is 1 and the intended FAIL-EXPECT line is printed.
D: an unreadable input exits 2. Exit: 0 all as expected, 1 a mutant was not detected or a control failed, 2 the self-test itself could not run."""
import copy, hashlib, json, os, shutil, subprocess, sys, tempfile
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
CHECK = os.path.join(HERE, "check_t3_readiness.py")
REC = os.path.join(ROOT, "docs", "design", "time-evidence", "t3-execution-prerequisites.yaml")
INV = os.path.join(ROOT, "docs", "evidence", "time-expiry-inventory", "results", "inventory.json")
MANIFEST = os.path.join(ROOT, "docs", "evidence", "time-manifest", "results", "DRYRUN-manifest.txt")
sys.path.insert(0, os.path.join(ROOT, "docs", "evidence", "time-manifest"))
import manifestlib as M
sys.path.insert(0, HERE)
bad = 0


def report(label, ok, extra=""):
    global bad
    print("%-118s %s %s" % (label, "OK" if ok else "FAIL", extra))
    bad += not ok


def run(args):
    r = subprocess.run([sys.executable, CHECK] + args, capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout + r.stderr


def verdict(o):
    return [l for l in o.splitlines() if l.startswith("T3 time-stamping: ")][-1][len("T3 time-stamping: "):] if "T3 time-stamping: " in o else "(none)"


def prepared_digest_of(rp, ip, root, extra=()):
    """the digest a GO must bind: computed by the check's own function on the same record"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("chk", CHECK); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    rec = yaml.safe_load(open(rp, encoding="utf-8")); strict = next(d for d in rec["decisions"] if d["id"] == "Q6a").get("chosen") == "strict"
    return m.prepared_digest(rec, lambda c: "pre" if (strict and c.get("strict_phase") == "pre") else c.get("phase"))


def build(root, mut=None, inv_mut=None, man_mut=None, confirm=True, order="staged", verify=("pre",), go=None, go_mut=None):
    """a temporary root with the real record made into a fixture: decisions confirmed, the listed phases verified with fixture evidence, optionally a GO record bound to the prepared state"""
    rec = yaml.safe_load(open(REC, encoding="utf-8")); inv = json.load(open(INV, encoding="utf-8"))
    os.makedirs(os.path.join(root, "evidence"), exist_ok=True)
    open(os.path.join(root, "evidence", "fixture.txt"), "w").write("fixture evidence: all good\n")
    strict = order == "strict"
    eff = lambda c: "pre" if (strict and c.get("strict_phase") == "pre") else c["phase"]
    for c in rec["conditions"]:
        if c["status"] == "verified":                      # keep the real evidence files reachable under the temporary root
            src = os.path.join(ROOT, c["evidence"]["path"]); dst = os.path.join(root, c["evidence"]["path"]); os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy(src, dst)
        elif eff(c) in verify:
            c["status"] = "verified"; c["verified_on"] = "2026-11-24"; c["evidence"] = {"path": "evidence/fixture.txt", "must_contain": "all good"}
    if confirm:
        for d in rec["decisions"]:
            d["status"] = "confirmed"; d["confirmation"] = {"stated_by": "owner", "date": "2026-11-24", "reference": "fixture"}
            if d["id"] == "Q6a":
                d["chosen"] = order
    man = open(MANIFEST, "rb").read()
    mp = os.path.join(root, "docs", "evidence", "time-manifest", "results"); os.makedirs(mp, exist_ok=True)
    if man_mut:
        _, _, entries = M.parse(man); entries = man_mut(list(entries)); man = M.render("fixture", entries)
    open(os.path.join(mp, "DRYRUN-manifest.txt"), "wb").write(man)
    for c in rec["conditions"]:
        if c["id"] == "C-Q1a-3":
            c["evidence"]["path"] = "docs/evidence/time-manifest/results/DRYRUN-manifest.txt"
    os.makedirs(os.path.join(root, "docs", "evidence", "time-manifest"), exist_ok=True)
    shutil.copy(os.path.join(ROOT, "docs", "evidence", "time-manifest", "manifestlib.py"), os.path.join(root, "docs", "evidence", "time-manifest", "manifestlib.py"))
    if mut:
        mut(rec)
    if inv_mut:
        inv_mut(inv)
    rp, ip = os.path.join(root, "rec.yaml"), os.path.join(root, "inv.json")
    open(rp, "w", encoding="utf-8").write(yaml.safe_dump(rec, sort_keys=False)); json.dump(inv, open(ip, "w"))
    args = ["--record", rp, "--inventory", ip, "--root", root, "--go", os.path.join(root, "no-go.yaml")]
    if go:
        g = {"go_format": 1, "gate": "t3-execution", "stated_by": "owner", "date": "2026-11-25", "reference": "fixture", "prepared_digest": prepared_digest_of(rp, ip, root)}
        if go_mut:
            go_mut(g)
        gp = os.path.join(root, "go.yaml"); open(gp, "w", encoding="utf-8").write(yaml.safe_dump(g, sort_keys=False)); args[args.index("--go") + 1] = gp
    return args


def main():
    rc, o = run([])
    report("A real record: NOT_PREPARED, valid (no FAIL-EXPECT), the unmet items listed, the confirmations stated as NOT authenticated, no GO", rc == 1 and verdict(o) == "NOT_PREPARED" and "FAIL-EXPECT" not in o and "UNMET decision Q6a is proposed" in o and "NOT authenticated" in o and "execution GO: none recorded" in o, "exit=%d" % rc)
    DOC = os.path.join(ROOT, "docs", "en", "T3-EXECUTION-PREREQUISITES.md"); doc = open(DOC, encoding="utf-8").read()
    rc, o = run(["--doc", DOC])
    report("A real record with the review document: the tables and the counts of the document equal the record", rc == 1 and verdict(o) == "NOT_PREPARED" and "FAIL-EXPECT" not in o, "exit=%d" % rc)
    states = (("PREPARED: every decision confirmed, every pre-execution condition verified (staged order), NO GO record: PREPARED_FOR_OWNER_GO and still not the GO", dict(), "PREPARED_FOR_OWNER_GO", 0),
              ("a valid separate GO record binds the prepared state: GO_RECORDED", dict(go=True), "GO_RECORDED", 0),
              ("after the GO every capture condition verified: EVIDENCE_CAPTURED", dict(go=True, verify=("pre", "capture")), "EVIDENCE_CAPTURED", 0),
              ("after the GO every capture and preserve condition verified: PRESERVATION_COMPLETE", dict(go=True, verify=("pre", "capture", "preserve")), "PRESERVATION_COMPLETE", 0),
              ("the STRICT order: the strict_phase conditions are pre-execution, so with them still open the record is NOT_PREPARED (the same fixture is PREPARED under the staged order)", dict(order="strict", mut=lambda r: [next(c for c in r["conditions"] if c["id"] == i).update(status="open", evidence=None) for i in ("C-Q6-3", "C-Q6-4", "C-Q6-6", "C-Q6-7")]), "NOT_PREPARED", 1),
              ("the STRICT order with the strict_phase conditions verified is PREPARED_FOR_OWNER_GO (the later-phase conditions of the other decisions stay open)", dict(order="strict"), "PREPARED_FOR_OWNER_GO", 0),
              ("a pre-execution condition still open (staged): NOT_PREPARED, valid", dict(mut=lambda r: next(c for c in r["conditions"] if c["id"] == "C-Q6-1").update(status="open", evidence=None)), "NOT_PREPARED", 1),
              ("the pre-execution conditions verified but the decisions only PROPOSED: NOT_PREPARED, valid", dict(confirm=False), "NOT_PREPARED", 1))
    for name, kw, want, rc_want in states:
        d = tempfile.mkdtemp()
        try:
            rc, o = run(build(d, **kw))
            report("B " + name, rc == rc_want and verdict(o) == want and "FAIL-EXPECT" not in o, "exit=%d verdict=%s" % (rc, verdict(o)))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def cond(r, cid):
        return next(c for c in r["conditions"] if c["id"] == cid)

    def dec(r, did):
        return next(x for x in r["decisions"] if x["id"] == did)

    def swap(entries):                                     # one record swapped for another well-formed one: the COUNT stays 92
        e = list(entries[0]); e[0] = "cic-schema-registry:standards/zzz/zzz.v0.0.1.yaml"; e[6] = "standards/zzz/zzz.v0.0.1.yaml"
        return sorted([tuple(e)] + list(entries[1:]), key=lambda x: x[0].encode("utf-8"))

    def wrong_commit(entries):
        e = list(entries[0]); e[4] = "9" * 40
        return [tuple(e)] + list(entries[1:])

    def extra_record(entries):
        e = list(entries[0]); e[0] = "cic-schema-registry:standards/zzz/zzz.v0.0.1.yaml"; e[6] = "standards/zzz/zzz.v0.0.1.yaml"
        return sorted(list(entries) + [tuple(e)], key=lambda x: x[0].encode("utf-8"))

    def drop_record(entries):
        return list(entries[1:])

    faults = [
        ("a decision is missing (Q6 removed)", dict(mut=lambda r: r.__setitem__("decisions", [x for x in r["decisions"] if x["id"] != "Q6"])), "decision.missing.Q6"),
        ("a decision this check does not know (Q9)", dict(mut=lambda r: r["decisions"].append({"id": "Q9", "status": "proposed", "confirmation": None, "requirements": ["x"]})), "decision.unknown.Q9"),
        ("a confirmed decision without a recorded statement (Q2)", dict(mut=lambda r: dec(r, "Q2").__setitem__("confirmation", None)), "decision.confirmation.Q2"),
        ("a confirmation that does not even claim to be the owner's (stated_by reviewer)", dict(mut=lambda r: dec(r, "Q2")["confirmation"].__setitem__("stated_by", "reviewer")), "decision.confirmation.Q2"),
        ("a decision that is only proposed carries a confirmation", dict(confirm=False, mut=lambda r: dec(r, "Q1a").__setitem__("confirmation", {"stated_by": "owner", "date": "2026-11-24", "reference": "x"})), "decision.confirmation.Q1a"),
        ("a decision with an unknown status", dict(mut=lambda r: dec(r, "Q3").__setitem__("status", "approved")), "decision.status.Q3"),
        ("Q6a confirmed but the order is not chosen", dict(mut=lambda r: dec(r, "Q6a").__setitem__("chosen", None)), "decision.chosen.Q6a"),
        ("Q6a with an order that is neither staged nor strict", dict(mut=lambda r: dec(r, "Q6a").__setitem__("chosen", "sometime")), "decision.chosen.Q6a"),
        ("a verified condition without evidence", dict(mut=lambda r: cond(r, "C-Q6-1").__setitem__("evidence", None)), "condition.evidence.C-Q6-1"),
        ("a verified condition whose evidence file does not exist", dict(mut=lambda r: cond(r, "C-Q6-1").__setitem__("evidence", {"path": "evidence/nope.txt", "must_contain": "x"})), "condition.evidence-file.C-Q6-1"),
        ("a verified condition whose evidence file does not contain the stated text", dict(mut=lambda r: cond(r, "C-Q6-1").__setitem__("evidence", {"path": "evidence/fixture.txt", "must_contain": "not in the file"})), "condition.evidence-text.C-Q6-1"),
        ("an open condition that names evidence", dict(confirm=False, verify=(), mut=lambda r: cond(r, "C-Q6-1").__setitem__("evidence", {"path": "x", "must_contain": "y"})), "condition.open-with-evidence.C-Q6-1"),
        ("a condition with an unknown phase", dict(mut=lambda r: cond(r, "C-Q6-1").__setitem__("phase", "later")), "condition.phase.C-Q6-1"),
        ("a condition that names an unknown decision", dict(mut=lambda r: cond(r, "C-Q6-1").__setitem__("decision", "Q7")), "condition.decision.C-Q6-1"),
        ("a decision with no condition (the conditions of Q3 removed)", dict(mut=lambda r: r.__setitem__("conditions", [c for c in r["conditions"] if c["decision"] != "Q3"])), "decision.conditions.Q3"),
        ("a condition recorded twice", dict(mut=lambda r: r["conditions"].append(copy.deepcopy(cond(r, "C-Q6-1")))), "condition.duplicate.C-Q6-1"),
        ("capture evidence verified WITHOUT a GO record (evidence that can only exist after the execution)", dict(verify=("pre", "capture")), "phase.without-go"),
        ("preserve evidence verified WITHOUT a GO record", dict(verify=("pre", "preserve")), "phase.without-go"),
        ("preserve evidence verified before the capture is complete (a GO exists)", dict(go=True, verify=("pre", "preserve")), "phase.order"),
        ("a GO record that is not stated by the owner", dict(go=True, go_mut=lambda g: g.__setitem__("stated_by", "reviewer")), "go.format"),
        ("a GO record without a date", dict(go=True, go_mut=lambda g: g.__setitem__("date", "")), "go.format"),
        ("a GO record that binds another prepared state (the digest of a state that changed)", dict(go=True, go_mut=lambda g: g.__setitem__("prepared_digest", "0" * 64)), "go.digest"),
        ("a GO record while the record is not prepared (a pre-execution condition is open)", dict(go=True, mut=lambda r: cond(r, "C-Q2-1").update(status="open", evidence=None)), "go.not-prepared"),
        ("a GO written into the prerequisites file", dict(mut=lambda r: r.__setitem__("execution_go", {"stated_by": "owner", "date": "2026-11-24"})), "go.recorded-here"),
        ("the internal latest date is not before the chain boundary", dict(mut=lambda r: r["dates"].__setitem__("internal_latest", "2026-12-31")), "dates.order"),
        ("the target is after the internal latest date", dict(mut=lambda r: r["dates"].__setitem__("target", "2026-12-20")), "dates.order"),
        ("the Q3 requirement no longer states the dates of the dates block", dict(mut=lambda r: r["dates"].__setitem__("target", "2026-11-29")), "dates.q3-text"),
        ("a record of the manifest SWAPPED for another one (the count is still 92)", dict(man_mut=swap), "manifest.set.missing."),
        ("...and the swapped-in record is reported as extra", dict(man_mut=swap), "manifest.set.extra.cic-schema-registry:standards/zzz/zzz.v0.0.1.yaml"),
        ("a record of the manifest missing (91)", dict(man_mut=drop_record), "manifest.set.missing."),
        ("an extra record in the manifest (93)", dict(man_mut=extra_record), "manifest.set.extra.cic-schema-registry:standards/zzz/zzz.v0.0.1.yaml"),
        ("a record of the manifest at another commit than the expected set pins", dict(man_mut=wrong_commit), "manifest.entry."),
        ("the inventory has no expected set of open records", dict(inv_mut=lambda i: i.__setitem__("open_records", [])), "manifest.set.empty"),
        ("the source has no statement of its authenticity", dict(mut=lambda r: r["source"].__setitem__("authenticity", "")), "source.provenance"),
        ("the record format is not 2", dict(mut=lambda r: r.__setitem__("prerequisites_format", 1)), "record.format"),
    ]
    for name, kw, needle in faults:
        d = tempfile.mkdtemp()
        try:
            rc, o = run(build(d, **kw))
        finally:
            shutil.rmtree(d, ignore_errors=True)
        named = [l for l in o.splitlines() if l.startswith("FAIL-EXPECT") and needle in l]
        report("C planted: " + name, rc == 1 and bool(named) and verdict(o) == "INVALID", "exit=%d verdict=%s needle=%s" % (rc, verdict(o), needle))
    for name, newdoc, needle in (("the decisions table of the document edited by hand (Q2 marked confirmed)", doc.replace("| Q2 | the time-stamp authorities | **proposed** |", "| Q2 | the time-stamp authorities | **confirmed** |", 1), "doc.table.decisions"),
                                 ("the conditions table of the document edited by hand (C-Q6-1 marked verified)", doc.replace("| C-Q6-1 | Q6 | pre | condition | **open** |", "| C-Q6-1 | Q6 | pre | condition | **verified** |", 1), "doc.table.conditions"),
                                 ("the document states other counts of the conditions", doc.replace("**3 of the 15 pre-execution conditions are verified**", "**4 of the 15 pre-execution conditions are verified**", 1), "doc.counts"),
                                 ("the document without the decisions table markers", doc.replace("<!-- BEGIN DECISIONS TABLE -->", "", 1), "doc.markers.decisions")):
        dd = tempfile.mkdtemp()
        try:
            f = os.path.join(dd, "doc.md"); open(f, "w", encoding="utf-8").write(newdoc)
            rc, o = run(["--doc", f])
        finally:
            shutil.rmtree(dd, ignore_errors=True)
        report("C planted (document): " + name, rc == 1 and verdict(o) == "INVALID" and any(l.startswith("FAIL-EXPECT") and needle in l for l in o.splitlines()), "exit=%d needle=%s" % (rc, needle))
    rc, o = run(["--record", "/nonexistent/record.yaml"])
    report("D infra: the record is unreadable (exit 2, not a detection)", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)
    print("self-test: %s" % ("all as expected" if not bad else "%d problem(s)" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
