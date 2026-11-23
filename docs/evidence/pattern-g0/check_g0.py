"""The G-0 check of the implementation plan of the pattern profile: are the OWNER PREREQUISITES of the plan met, and how do we know? An ISOLATED check, not a CI gate; it changes nothing and closes nothing.

It keeps three things apart, as the plan does (gate G-0 of docs/design/pattern-profile-plan/plan.yaml):
  decision   the owner's decision, RECORDED in docs/design/pattern-profile-plan/decisions.yaml with its source and date (a statement; this repository cannot authenticate it)
  evidence   what backs the decision: the files the record binds by SHA-256 to a base commit, and the artifacts the plan names (for OP-1: the specification text that fixes it)
  closure    the state of the gate: CLOSED only if a separate owner closure record exists and names the digest of the decision record; this check never closes a gate by itself
It evaluates the prerequisites that G-0 itself names in the plan (D1 to D6, OP-1, OP-2) and NOTHING later: OP-3 closes at G-6 and OP-4 at G-4; their records are only checked for consistency.

Verdicts (the last line): INVALID (the record is inconsistent, forged or stale), NOT_READY (a prerequisite is unmet or lacks evidence), READY_FOR_OWNER_CLOSURE (all prerequisites are recorded and evidenced; the gate is NOT closed),
CLOSED (READY and a valid owner closure record exists). Exit: 0 for READY_FOR_OWNER_CLOSURE or CLOSED, 1 for NOT_READY or INVALID (FAIL-EXPECT lines name what), 2 for an unreadable input (never a result).
Usage: check_g0.py [--record PATH] [--plan PATH] [--closure PATH] [--root DIR]"""
import hashlib, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
PLAN_DIR = os.path.join("docs", "design", "pattern-profile-plan")
STATUS_WORDS = {"CONFIRMED": "confirmed", "DECIDED": "decided", "ACCEPTED": "accepted_content", "PARTIAL": "partial", "HOLD": "hold", "REJECTED": "rejected", "DEFERRED": "deferred"}
G0_DECISIONS = ["D1", "D2", "D3", "D4", "D5", "D6"]
ALL_IDS = G0_DECISIONS + ["OP-1", "OP-2", "OP-3", "OP-4", "D7", "D8"]
OP2_OWNER_OUTCOMES = {"accepted_content", "rejected", "deferred"}       # the plan: accepted, rejected or deferred by the owner
invalid, unmet = [], []


def bad(label, detail=""):
    invalid.append(label); print("FAIL-EXPECT %s %s" % (label, detail))


def lack(label, detail=""):
    unmet.append(label); print("FAIL-EXPECT %s %s" % (label, detail))


def arg(argv, name, default):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else default


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def source_statuses(verbatim):
    """the statuses stated in the verbatim table of the owner's statement: id -> status word"""
    out = {}
    for line in verbatim.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 3 or cells[2] not in STATUS_WORDS:
            continue
        ids = cells[0]
        m = re.fullmatch(r"D(\d)-D(\d)", ids)
        if m:
            for n in range(int(m.group(1)), int(m.group(2)) + 1):
                out["D%d" % n] = STATUS_WORDS[cells[2]]
        else:
            out[ids] = STATUS_WORDS[cells[2]]
    return out


def main(argv):
    import yaml
    root = arg(argv, "--root", ROOT)
    rec_path = arg(argv, "--record", os.path.join(root, PLAN_DIR, "decisions.yaml"))
    plan_path = arg(argv, "--plan", os.path.join(root, PLAN_DIR, "plan.yaml"))
    clo_path = arg(argv, "--closure", os.path.join(root, PLAN_DIR, "g0-closure.yaml"))
    try:
        rec_raw = open(rec_path, "rb").read(); rec = yaml.safe_load(rec_raw)
        plan = yaml.safe_load(open(plan_path, encoding="utf-8"))
        assert isinstance(rec, dict) and isinstance(plan, dict)
        closure = yaml.safe_load(open(clo_path, encoding="utf-8")) if os.path.exists(clo_path) else None
    except BaseException as e:
        print("INCOMPLETE: an input cannot be read: %r" % (e,)); return 2

    # ---- the record: format, source, provenance
    if rec.get("decision_record_format") != 1:
        bad("record.format", "decision_record_format is not 1")
    src = rec.get("source") or {}
    ok_src = (src.get("kind") == "owner_statement" and re.fullmatch(r"\d{4}-\d\d-\d\d", str(src.get("date", ""))) and str(src.get("reference", "")).strip()
              and str(src.get("channel", "")).strip() and str(src.get("verbatim", "")).strip() and str(rec.get("recorded_on", "")) == str(src.get("date", "")))
    if not ok_src:
        bad("source.provenance", "the source needs kind owner_statement, a date equal to recorded_on, a channel, a reference and the verbatim statement")
    # ---- the files the evidence is bound to
    bt = rec.get("bound_to") or {}
    if not re.fullmatch(r"[0-9a-f]{40}", str(bt.get("base_commit", ""))):
        bad("bound.base_commit", "base_commit is not a 40-hex commit id")
    files = bt.get("files") or {}
    verified_files = set()
    for k, f in sorted(files.items()):
        p = os.path.join(root, f.get("path", ""))
        if not os.path.isfile(p):
            bad("bound.missing.%s" % k, "the bound file %s does not exist" % f.get("path")); continue
        if not re.fullmatch(r"[0-9a-f]{64}", str(f.get("sha256", ""))) or sha(p) != f["sha256"]:
            bad("bound.sha.%s" % k, "the SHA-256 of %s is not the recorded one (the evidence is stale or the record is wrong)" % f.get("path"))
        else:
            verified_files.add(k)
    # ---- the decisions: unique, complete, consistent with the verbatim source
    byid = {}
    for d in rec.get("decisions", []):
        if d.get("id") in byid:
            bad("decision.contradiction.%s" % d["id"], "the decision is recorded twice (statuses %s and %s)" % (byid[d["id"]].get("status"), d.get("status")))
        byid.setdefault(d.get("id"), d)
    stated = source_statuses(str(src.get("verbatim", "")))
    for i in ALL_IDS:
        d = byid.get(i)
        if d is None:
            (lack if i in G0_DECISIONS + ["OP-1", "OP-2"] else bad)("decision.missing.%s" % i, "no record of %s" % i); continue
        if i in stated and d.get("status") != stated[i]:
            bad("decision.vs-source.%s" % i, "the record says %r, the owner's statement says %r" % (d.get("status"), stated[i]))
        if i not in stated:
            bad("decision.not-in-source.%s" % i, "the owner's statement does not mention %s" % i)
    for i in set(byid) - set(ALL_IDS):
        bad("decision.unknown.%s" % i, "a decision the plan does not know")
    # ---- the plan: what G-0 itself requires, and where the later open points close
    g0 = next((g for g in plan.get("gates", []) if g.get("id") == "G-0"), None)
    crit = str((g0 or {}).get("criteria", ""))
    if g0 is None or not all(t in crit for t in ("D1 to D6", "OP-1", "OP-2")):
        bad("plan.g0.criteria", "gate G-0 of the plan no longer names D1 to D6, OP-1 and OP-2: this check evaluates what it names")
    if any(t in crit for t in ("OP-3", "OP-4")):
        bad("plan.g0.late-conditions", "G-0 names a later open point: this check does not demand conditions of G-4 or G-6 at G-0")
    closes = {o["id"]: o.get("closed_by") for o in plan.get("open_points", [])}
    for i in ("OP-1", "OP-2", "OP-3", "OP-4"):
        d = byid.get(i)
        if d is not None and d.get("closes_at") != closes.get(i):
            bad("plan.closes_at.%s" % i, "the record says %s closes at %s, the plan says %s" % (i, d.get("closes_at"), closes.get(i)))
    # ---- the prerequisites of G-0, each with its decision and its evidence
    rows = []                                    # (criterion, decision state, evidence state)

    def files_ok(d):
        need = d.get("evidence_files", [])
        miss = [k for k in need if k not in files]
        stale = [k for k in need if k in files and k not in verified_files]
        return not need or (not miss and not stale), miss, stale

    for i in G0_DECISIONS:
        d = byid.get(i)
        if d is None:
            rows.append((i, "MISSING", "n/a")); continue
        if d.get("status") != "confirmed":
            lack("decision.status.%s" % i, "%s is %r, not confirmed by the owner" % (i, d.get("status")))
        ok, miss, stale = files_ok(d)
        if not ok:
            lack("evidence.files.%s" % i, "the evidence files of %s are missing (%s) or stale (%s)" % (i, miss, stale))
        rows.append((i, "CONFIRMED" if d.get("status") == "confirmed" else "NOT CONFIRMED", "VERIFIED" if ok else "UNVERIFIED"))
    d = byid.get("OP-1")
    if d is None:
        rows.append(("OP-1", "MISSING", "n/a"))
    else:
        if d.get("status") != "decided":
            lack("decision.status.OP-1", "OP-1 is %r, not decided by the owner" % d.get("status"))
        ok, miss, stale = files_ok(d)
        st = d.get("spec_text")
        if st is None:
            lack("evidence.op1.spec-text", "the plan asks of G-0 'the specification text that fixes OP-1' as evidence: none is recorded")
            ev = "UNVERIFIED (the specification text that fixes OP-1 is missing)"
        else:
            p = os.path.join(root, str((st or {}).get("path", "")))
            if not os.path.isfile(p) or sha(p) != str((st or {}).get("sha256", "")) or "YAML 1.2" not in open(p, encoding="utf-8").read():
                bad("evidence.op1.spec-text", "the recorded specification text is missing, stale (SHA-256) or does not fix the YAML 1.2 scalar schema")
                ev = "UNVERIFIED (the recorded specification text does not check)"
            else:
                ev = "VERIFIED"
        if not ok:
            lack("evidence.files.OP-1", "the evidence files of OP-1 are missing (%s) or stale (%s)" % (miss, stale)); ev = "UNVERIFIED"
        rows.append(("OP-1", "DECIDED" if d.get("status") == "decided" else "NOT DECIDED", ev))
    d = byid.get("OP-2")
    if d is None:
        rows.append(("OP-2", "MISSING", "n/a"))
    else:
        if d.get("status") not in OP2_OWNER_OUTCOMES:
            lack("decision.status.OP-2", "OP-2 is %r: the plan accepts an owner decision of accepted, rejected or deferred" % d.get("status"))
        if d.get("normative") is not False:
            bad("op2.normative", "the content of the 47 cases is accepted, not made a normative conformance set: normative must be false")
        ok, miss, stale = files_ok(d)
        if not ok:
            lack("evidence.files.OP-2", "the evidence files of OP-2 are missing (%s) or stale (%s)" % (miss, stale))
        else:
            try:
                cases = yaml.safe_load(open(os.path.join(root, files["extension_cases"]["path"]), encoding="utf-8"))["cases"]
                review = yaml.safe_load(open(os.path.join(root, files["extension_review"]["path"]), encoding="utf-8"))["cases"]
            except BaseException as e:
                print("INCOMPLETE: the extension files cannot be read: %r" % (e,)); return 2
            if d.get("case_count") != len(cases) or len(review) != len(cases):
                bad("op2.count", "the record accepts %s cases, the case file has %d and the review %d" % (d.get("case_count"), len(cases), len(review)))
            for r in review if d.get("status") == "accepted_content" else []:           # only an ACCEPTED case needs its decisions confirmed and off hold
                dep = set(r.get("depends", []))
                hold = {x for x in dep if (byid.get(x) or {}).get("status") == "hold"}
                if hold:
                    bad("op2.depends.hold.%s" % r["id"], "the case depends on %s, which is on hold" % sorted(hold))
                not_conf = {x for x in dep if (byid.get(x) or {}).get("status") != "confirmed"} - hold
                if not_conf:
                    lack("op2.depends.%s" % r["id"], "the case is accepted but depends on %s, which the owner has not confirmed" % sorted(not_conf))
        rows.append(("OP-2", d.get("status", "?").upper(), "VERIFIED" if ok else "UNVERIFIED"))
    # ---- records that G-0 does NOT require (consistency only)
    d3 = byid.get("OP-3")
    if d3 is not None:
        if d3.get("status") == "partial" and not str(d3.get("precondition", "")).strip():
            bad("op3.precondition", "OP-3 is partial: the precondition (c and the counted operations fixed BEFORE the G-6 measurement) must be recorded")
    # ---- the verdict, the closure
    state = "INVALID" if invalid else ("NOT_READY" if unmet else "READY_FOR_OWNER_CLOSURE")
    if closure is not None:
        c_ok = (isinstance(closure, dict) and closure.get("closure_format") == 1 and closure.get("gate") == "G-0" and closure.get("closed_by") == "owner"
                and re.fullmatch(r"\d{4}-\d\d-\d\d", str(closure.get("date", ""))))
        if not c_ok:
            bad("closure.format", "the closure record needs closure_format 1, gate G-0, closed_by owner and a date"); state = "INVALID"
        elif closure.get("decisions_sha256") != hashlib.sha256(rec_raw).hexdigest():
            bad("closure.digest", "the closure record names another decision record (SHA-256): the decisions changed after the closure, or it closes a different record"); state = "INVALID"
        elif state != "READY_FOR_OWNER_CLOSURE":
            bad("closure.without-evidence", "a closure record exists but the prerequisites are not all met and evidenced (%s)" % state); state = "INVALID"
        else:
            state = "CLOSED"
    print("%-8s %-16s %s" % ("criterion", "decision", "evidence"))
    for c, dc, ev in rows:
        print("%-8s %-16s %s" % (c, dc, ev))
    if byid.get("OP-3") is not None:
        print("OP-3     %-16s closes at %s, not a G-0 prerequisite; precondition: %s" % (str(byid["OP-3"].get("status", "?")).upper(), byid["OP-3"].get("closes_at"), byid["OP-3"].get("precondition")))
    if byid.get("OP-4") is not None:
        print("OP-4     %-16s closes at %s, not a G-0 prerequisite" % (str(byid["OP-4"].get("status", "?")).upper(), byid["OP-4"].get("closes_at")))
    print("D7, D8   %s: on hold, no case depends on them" % ("HOLD" if all((byid.get(x) or {}).get("status") == "hold" for x in ("D7", "D8")) else "NOT ALL ON HOLD"))
    print("closure record: %s" % ("none (the gate is not closed by this check)" if closure is None else "present"))
    print("G-0: %s" % state)
    return 0 if state in ("READY_FOR_OWNER_CLOSURE", "CLOSED") else 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
