"""Self-test of check_t3_readiness.py: can it FAIL, and for the right reason? Typed exits; infrastructure is never a detection.
A: the real record (NOT_READY, every unmet item listed, no invalidity). B: positive controls in a TEMPORARY ROOT with fixture evidence (a complete package is READY_FOR_OWNER_GO and still records no GO; decisions confirmed but one
condition open, and conditions verified but decisions only proposed, stay NOT_READY). C: planted faults, each counted only when the verdict is INVALID, the exit is 1 and the intended FAIL-EXPECT line is printed.
D: an unreadable input exits 2. Exit: 0 all as expected, 1 a mutant was not detected or a control failed, 2 the self-test itself could not run."""
import copy, json, os, shutil, subprocess, sys, tempfile
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
CHECK = os.path.join(HERE, "check_t3_readiness.py")
REC = os.path.join(ROOT, "docs", "design", "time-evidence", "t3-execution-prerequisites.yaml")
INV = os.path.join(ROOT, "docs", "evidence", "time-expiry-inventory", "results", "inventory.json")
bad = 0


def report(label, ok, extra=""):
    global bad
    print("%-112s %s %s" % (label, "OK" if ok else "FAIL", extra))
    bad += not ok


def run(args):
    r = subprocess.run([sys.executable, CHECK] + args, capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout + r.stderr


def verdict(o):
    return [l for l in o.splitlines() if l.startswith("T3 time-stamping: ")][-1][len("T3 time-stamping: "):] if "T3 time-stamping: " in o else "(none)"


def build(root, mut=None, inv_mut=None, confirm_all=True, verify_all=True):
    rec = yaml.safe_load(open(REC, encoding="utf-8")); inv = json.load(open(INV, encoding="utf-8"))
    os.makedirs(os.path.join(root, "evidence"), exist_ok=True)
    fx = os.path.join(root, "evidence", "fixture.txt"); open(fx, "w").write("fixture evidence: all good\n")
    for c in rec["conditions"]:
        if c["status"] == "verified":                      # keep the real evidence files reachable under the temporary root
            src = os.path.join(ROOT, c["evidence"]["path"]); dst = os.path.join(root, c["evidence"]["path"]); os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy(src, dst)
        elif verify_all:
            c["status"] = "verified"; c["verified_on"] = "2026-11-24"; c["evidence"] = {"path": "evidence/fixture.txt", "must_contain": "all good"}
    if confirm_all:
        for d in rec["decisions"]:
            d["status"] = "confirmed"; d["confirmation"] = {"by": "owner", "date": "2026-11-24", "reference": "fixture"}
    if mut:
        mut(rec)
    if inv_mut:
        inv_mut(inv)
    rp, ip = os.path.join(root, "rec.yaml"), os.path.join(root, "inv.json")
    open(rp, "w", encoding="utf-8").write(yaml.safe_dump(rec, sort_keys=False)); json.dump(inv, open(ip, "w"))
    return ["--record", rp, "--inventory", ip, "--root", root]


def main():
    rc, o = run([])
    report("A real record: NOT_READY, valid (no FAIL-EXPECT), the unmet items listed, no GO recorded", rc == 1 and verdict(o) == "NOT_READY" and "FAIL-EXPECT" not in o and "UNMET decision Q6 is only proposed" in o and "execution GO: none recorded" in o, "exit=%d" % rc)
    DOC = os.path.join(ROOT, "docs", "en", "T3-EXECUTION-PREREQUISITES.md"); doc = open(DOC, encoding="utf-8").read()
    rc, o = run(["--doc", DOC])
    report("A real record with the review document: the tables and the counts of the document equal the record", rc == 1 and verdict(o) == "NOT_READY" and "FAIL-EXPECT" not in o, "exit=%d" % rc)
    for name, newdoc, needle in (("the decisions table of the document edited by hand (Q2 marked confirmed)", doc.replace("| Q2 | the time-stamp authorities | **proposed** |", "| Q2 | the time-stamp authorities | **confirmed** |", 1), "doc.table.decisions"),
                                 ("the conditions table of the document edited by hand (C-Q6-1 marked verified)", doc.replace("| C-Q6-1 | Q6 | condition | **open** |", "| C-Q6-1 | Q6 | condition | **verified** |", 1), "doc.table.conditions"),
                                 ("the document states other counts of the conditions", doc.replace("**19 are open**", "**18 are open**", 1), "doc.counts"),
                                 ("the document without the decisions table markers", doc.replace("<!-- BEGIN DECISIONS TABLE -->", "", 1), "doc.markers.decisions")):
        dd = tempfile.mkdtemp()
        try:
            f = os.path.join(dd, "doc.md"); open(f, "w", encoding="utf-8").write(newdoc)
            rc, o = run(["--doc", f])
        finally:
            shutil.rmtree(dd, ignore_errors=True)
        report("C planted (document): " + name, rc == 1 and verdict(o) == "INVALID" and any(l.startswith("FAIL-EXPECT") and needle in l for l in o.splitlines()), "exit=%d needle=%s" % (rc, needle))
    d = tempfile.mkdtemp()
    try:
        rc, o = run(build(d))
        report("B positive control: all decisions confirmed and all conditions verified is READY_FOR_OWNER_GO, and the file still records no GO", rc == 0 and verdict(o) == "READY_FOR_OWNER_GO" and "execution GO: none recorded" in o, "exit=%d" % rc)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    for name, kw in (("all decisions confirmed but ONE condition still open", dict(mut=lambda r: next(c for c in r["conditions"] if c["id"] == "C-Q6-1").update(status="open", evidence=None))),
                     ("all conditions verified but the decisions only PROPOSED", dict(confirm_all=False))):
        d = tempfile.mkdtemp()
        try:
            rc, o = run(build(d, **kw))
            report("B stays NOT_READY (valid): " + name, rc == 1 and verdict(o) == "NOT_READY" and "FAIL-EXPECT" not in o, "exit=%d verdict=%s" % (rc, verdict(o)))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def cond(r, cid):
        return next(c for c in r["conditions"] if c["id"] == cid)

    def dec(r, did):
        return next(x for x in r["decisions"] if x["id"] == did)

    faults = [
        ("a decision is missing (Q6 removed)", dict(mut=lambda r: r.__setitem__("decisions", [x for x in r["decisions"] if x["id"] != "Q6"])), "decision.missing.Q6"),
        ("a decision this check does not know (Q9)", dict(mut=lambda r: r["decisions"].append({"id": "Q9", "status": "proposed", "confirmation": None, "requirements": ["x"]})), "decision.unknown.Q9"),
        ("a confirmed decision without a confirmation (Q2)", dict(mut=lambda r: dec(r, "Q2").__setitem__("confirmation", None)), "decision.confirmation.Q2"),
        ("a confirmation by someone who is not the owner", dict(mut=lambda r: dec(r, "Q2")["confirmation"].__setitem__("by", "reviewer")), "decision.confirmation.Q2"),
        ("a decision that is only proposed carries a confirmation", dict(confirm_all=False, mut=lambda r: dec(r, "Q1a").__setitem__("confirmation", {"by": "owner", "date": "2026-11-24", "reference": "x"})), "decision.confirmation.Q1a"),
        ("a decision with an unknown status", dict(mut=lambda r: dec(r, "Q3").__setitem__("status", "approved")), "decision.status.Q3"),
        ("a decision without requirements", dict(mut=lambda r: dec(r, "Q3").__setitem__("requirements", [])), "decision.requirements.Q3"),
        ("a verified condition without evidence", dict(mut=lambda r: cond(r, "C-Q6-1").__setitem__("evidence", None)), "condition.evidence.C-Q6-1"),
        ("a verified condition whose evidence file does not exist", dict(mut=lambda r: cond(r, "C-Q6-1").__setitem__("evidence", {"path": "evidence/nope.txt", "must_contain": "x"})), "condition.evidence-file.C-Q6-1"),
        ("a verified condition whose evidence file does not contain the stated text", dict(mut=lambda r: cond(r, "C-Q6-1").__setitem__("evidence", {"path": "evidence/fixture.txt", "must_contain": "not in the file"})), "condition.evidence-text.C-Q6-1"),
        ("an open condition that names evidence", dict(confirm_all=False, verify_all=False, mut=lambda r: cond(r, "C-Q6-1").__setitem__("evidence", {"path": "x", "must_contain": "y"})), "condition.open-with-evidence.C-Q6-1"),
        ("a condition that names an unknown decision", dict(mut=lambda r: cond(r, "C-Q6-1").__setitem__("decision", "Q7")), "condition.decision.C-Q6-1"),
        ("a decision with no condition (the conditions of Q3 removed)", dict(mut=lambda r: r.__setitem__("conditions", [c for c in r["conditions"] if c["decision"] != "Q3"])), "decision.conditions.Q3"),
        ("a condition recorded twice", dict(mut=lambda r: r["conditions"].append(copy.deepcopy(cond(r, "C-Q6-1")))), "condition.duplicate.C-Q6-1"),
        ("the internal latest date is not before the chain boundary", dict(mut=lambda r: r["dates"].__setitem__("internal_latest", "2026-12-31")), "dates.order"),
        ("the target is after the internal latest date", dict(mut=lambda r: r["dates"].__setitem__("target", "2026-12-20")), "dates.order"),
        ("the Q3 requirement no longer states the dates of the dates block", dict(mut=lambda r: r["dates"].__setitem__("target", "2026-11-29")), "dates.q3-text"),
        ("a GO is recorded in this file", dict(mut=lambda r: r.__setitem__("execution_go", {"by": "owner", "date": "2026-11-24"})), "go.recorded-here"),
        ("the dry-run manifest does not hold the open records of the inventory (the inventory says 89 registry records)", dict(inv_mut=lambda i: i["registry"].__setitem__("records", 89)), "manifest.count"),
        ("the source has no statement of its authenticity", dict(mut=lambda r: r["source"].__setitem__("authenticity", "")), "source.provenance"),
        ("the record format is not 1", dict(mut=lambda r: r.__setitem__("prerequisites_format", 2)), "record.format"),
    ]
    for name, kw, needle in faults:
        d = tempfile.mkdtemp()
        try:
            rc, o = run(build(d, **kw))
        finally:
            shutil.rmtree(d, ignore_errors=True)
        named = [l for l in o.splitlines() if l.startswith("FAIL-EXPECT") and needle in l]
        report("C planted: " + name, rc == 1 and bool(named) and verdict(o) == "INVALID", "exit=%d verdict=%s needle=%s" % (rc, verdict(o), needle))
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
