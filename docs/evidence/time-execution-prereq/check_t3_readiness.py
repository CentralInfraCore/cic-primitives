"""The READINESS check of the T3 time-stamping (docs/design/time-evidence/t3-execution-prerequisites.yaml): are the decisions confirmed, are the conditions verified, and how do we know? An ISOLATED check, not a CI gate;
it performs nothing and can never give the GO. It keeps three things apart (decision, condition, GO) and reports a VERDICT: INVALID (the record is inconsistent), NOT_READY (a decision is not confirmed or a condition is open),
READY_FOR_OWNER_GO (every decision confirmed by the owner and every condition verified WITH EVIDENCE THIS CHECK CAN READ; the time-stamping is still NOT started and still needs the owner's separate GO).
Rules: a decision is `proposed`, `confirmed` or `rejected`; `confirmed` needs a confirmation {by: owner, date, reference}; a condition is `open` (no evidence) or `verified` (a date and evidence {path, must_contain} that exists in the
repository and contains the text); a constraint is a condition that is a standing rule; every condition names an existing decision and every decision has a condition; the dates are ordered target < internal latest < the
chain boundary of the inventory; the dry-run manifest holds exactly the open records of the inventory; `execution_go` must be null in this file (a GO is a separate act, never recorded here).
Exit: 0 READY_FOR_OWNER_GO, 1 NOT_READY or INVALID (FAIL-EXPECT lines name what is invalid; UNMET lines what is not yet met), 2 an unreadable input (never a result).
The tables of the review document (docs/en/T3-EXECUTION-PREREQUISITES.md: the decisions, the conditions) must equal the tables rendered from the record (--render prints them): nothing is hand-edited into them.
Usage: check_t3_readiness.py [--record PATH] [--inventory PATH] [--root DIR] [--doc PATH] [--render]"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
REC = os.path.join(ROOT, "docs", "design", "time-evidence", "t3-execution-prerequisites.yaml")
INV = os.path.join(ROOT, "docs", "evidence", "time-expiry-inventory", "results", "inventory.json")
DECISIONS = ["Q1a", "Q1b", "Q2", "Q3", "Q6"]
DOC = os.path.join(ROOT, "docs", "en", "T3-EXECUTION-PREREQUISITES.md")
MARK = {"decisions": ("<!-- BEGIN DECISIONS TABLE -->", "<!-- END DECISIONS TABLE -->"), "conditions": ("<!-- BEGIN CONDITIONS TABLE -->", "<!-- END CONDITIONS TABLE -->")}


def render(rec):
    dt = ["| Decision | Topic | Status | Requirements that become binding if the owner confirms |", "|---|---|---|---|"]
    for d in rec["decisions"]:
        dt.append("| %s | %s | **%s** | %s |" % (d["id"], d["topic"], d["status"], " ".join("(%d) %s" % (i + 1, " ".join(r.split()).replace("|", "/")) for i, r in enumerate(d["requirements"]))))
    ct = ["| Condition | Decision | Kind | Status | Condition to verify before the time-stamping | Evidence |", "|---|---|---|---|---|---|"]
    for c in rec["conditions"]:
        ev = c.get("evidence")
        ct.append("| %s | %s | %s | **%s** | %s | %s |" % (c["id"], c["decision"], c["kind"], c["status"], " ".join(c["text"].split()).replace("|", "/"), ("`%s` contains %r (verified %s)" % (ev["path"], ev["must_contain"], c["verified_on"])) if ev else "none"))
    return {"decisions": "\n".join(dt), "conditions": "\n".join(ct)}
invalid, unmet = [], []


def bad(label, detail=""):
    invalid.append(label); print("FAIL-EXPECT %s %s" % (label, detail))


def main(argv):
    import yaml
    arg = lambda n, d: argv[argv.index(n) + 1] if n in argv and argv.index(n) + 1 < len(argv) else d
    root = arg("--root", ROOT)
    try:
        rec = yaml.safe_load(open(arg("--record", REC), encoding="utf-8")); inv = json.load(open(arg("--inventory", INV), encoding="utf-8"))
        assert isinstance(rec, dict)
    except BaseException as e:
        print("INCOMPLETE: an input cannot be read: %r" % (e,)); return 2
    if "--render" in argv:
        for k, v in render(rec).items():
            print("## %s\n%s\n" % (k, v))
        return 0
    if rec.get("prerequisites_format") != 1:
        bad("record.format", "prerequisites_format is not 1")
    src = rec.get("source") or {}
    if not (src.get("kind") in ("reviewer_recommendation", "owner_statement") and re.fullmatch(r"\d{4}-\d\d-\d\d", str(src.get("date", ""))) and str(src.get("reference", "")).strip() and str(src.get("authenticity", "")).strip()):
        bad("source.provenance", "the source needs a kind, a date, a reference and a statement of its authenticity")
    if rec.get("execution_go") is not None:
        bad("go.recorded-here", "execution_go must be null: the owner's GO to perform the time-stamping is a separate act and is never recorded in this file")
    decs = {}
    for d in rec.get("decisions", []):
        if d.get("id") in decs:
            bad("decision.duplicate.%s" % d["id"], "recorded twice")
        decs.setdefault(d.get("id"), d)
    for i in DECISIONS:
        d = decs.get(i)
        if d is None:
            bad("decision.missing.%s" % i, "no record of %s" % i); continue
        if d.get("status") not in ("proposed", "confirmed", "rejected"):
            bad("decision.status.%s" % i, "status %r" % d.get("status")); continue
        c = d.get("confirmation")
        if d["status"] == "confirmed":
            if not (isinstance(c, dict) and c.get("by") == "owner" and re.fullmatch(r"\d{4}-\d\d-\d\d", str(c.get("date", ""))) and str(c.get("reference", "")).strip()):
                bad("decision.confirmation.%s" % i, "a confirmed decision needs a confirmation {by: owner, date, reference}")
        elif c is not None:
            bad("decision.confirmation.%s" % i, "a decision that is not confirmed carries a confirmation")
        if not d.get("requirements"):
            bad("decision.requirements.%s" % i, "a decision states its requirements")
        if d["status"] == "proposed":
            unmet.append("decision %s is only proposed" % i)
        elif d["status"] == "rejected":
            unmet.append("decision %s is rejected" % i)
    for i in set(decs) - set(DECISIONS):
        bad("decision.unknown.%s" % i, "a decision this check does not know")
    conds = rec.get("conditions", []); seen = set()
    for c in conds:
        cid = c.get("id")
        if cid in seen:
            bad("condition.duplicate.%s" % cid, "recorded twice")
        seen.add(cid)
        if c.get("decision") not in DECISIONS:
            bad("condition.decision.%s" % cid, "names an unknown decision %r" % c.get("decision"))
        if c.get("kind") not in ("condition", "constraint"):
            bad("condition.kind.%s" % cid, "kind %r" % c.get("kind"))
        st, ev = c.get("status"), c.get("evidence")
        if st == "open":
            if ev is not None:
                bad("condition.open-with-evidence.%s" % cid, "an open condition names evidence: verify it or remove it")
            unmet.append("condition %s is open: %s" % (cid, str(c.get("text", ""))[:90]))
        elif st == "verified":
            ok = isinstance(ev, dict) and ev.get("path") and ev.get("must_contain") and re.fullmatch(r"\d{4}-\d\d-\d\d", str(c.get("verified_on", "")))
            if not ok:
                bad("condition.evidence.%s" % cid, "a verified condition needs a date and evidence {path, must_contain}")
            else:
                p = os.path.join(root, ev["path"])
                if not os.path.isfile(p):
                    bad("condition.evidence-file.%s" % cid, "the evidence file %s does not exist" % ev["path"])
                elif ev["must_contain"] not in open(p, encoding="utf-8", errors="replace").read():
                    bad("condition.evidence-text.%s" % cid, "the evidence file does not contain %r" % ev["must_contain"])
        else:
            bad("condition.status.%s" % cid, "status %r" % st)
    for i in DECISIONS:
        if i in decs and not any(c.get("decision") == i for c in conds):
            bad("decision.conditions.%s" % i, "a decision with no condition cannot be shown ready")
    # the dates
    dt = rec.get("dates") or {}
    boundary = next((c["boundary"] for c in inv["classes"] if c["id"] == "registry"), None)
    if not (re.fullmatch(r"\d{4}-\d\d-\d\d", str(dt.get("target", ""))) and re.fullmatch(r"\d{4}-\d\d-\d\d", str(dt.get("internal_latest", ""))) and boundary):
        bad("dates.format", "the target, the internal latest date or the inventory's boundary is not a date")
    else:
        if not (dt["target"] < dt["internal_latest"] < boundary[:10]):
            bad("dates.order", "the target %s, the internal latest %s and the chain boundary %s are not in order" % (dt["target"], dt["internal_latest"], boundary))
        q3 = " ".join(" ".join(decs.get("Q3", {}).get("requirements", [])).split())
        if dt["target"] not in q3 or dt["internal_latest"] not in q3:
            bad("dates.q3-text", "the Q3 requirement does not state the dates of the dates block")
    # the dry-run manifest must hold exactly the open records of the inventory
    open_n = inv["registry"]["records"] + sum(1 for t in inv["tag_records"] if t["repo"] == "cic-yang" and t.get("own_release_record"))
    for c in conds:
        if c.get("id") == "C-Q1a-3" and c.get("status") == "verified":
            p = os.path.join(root, (c.get("evidence") or {}).get("path", ""))
            if os.path.isfile(p) and ("count: %d\n" % open_n) not in open(p, encoding="utf-8", errors="replace").read():
                bad("manifest.count", "the dry-run manifest does not hold exactly the %d open records of the inventory" % open_n)
    if "--doc" in argv:
        try:
            doc = open(arg("--doc", DOC), encoding="utf-8").read()
            tables = render(rec)
        except BaseException as e:
            print("INCOMPLETE: the document cannot be read: %r" % (e,)); return 2
        for k, (b, e) in MARK.items():
            if b in doc and e in doc:
                if doc.split(b, 1)[1].split(e, 1)[0].strip() != tables[k].strip():
                    bad("doc.table.%s" % k, "the %s table of the document differs from the table rendered from the record" % k)
            else:
                bad("doc.markers.%s" % k, "the document has no %s table markers" % k)
        nv = sum(1 for c in conds if c.get("status") == "verified"); no = sum(1 for c in conds if c.get("status") == "open")
        needle = "Of the %d conditions **%d are verified**" % (len(conds), nv)
        if "Of the %d conditions" % len(conds) not in doc or ("**%d are verified**" % nv) not in doc or ("**%d are open**" % no) not in doc:
            bad("doc.counts", "the document does not say: of the %d conditions %d are verified and %d are open" % (len(conds), nv, no))
    state = "INVALID" if invalid else ("NOT_READY" if unmet else "READY_FOR_OWNER_GO")
    print("%-5s %-10s %s" % ("id", "status", "conditions verified"))
    for i in DECISIONS:
        if i in decs:
            cs = [c for c in conds if c.get("decision") == i]
            print("%-5s %-10s %d of %d" % (i, decs[i].get("status"), sum(1 for c in cs if c.get("status") == "verified"), len(cs)))
    for u in unmet:
        print("UNMET %s" % u)
    print("execution GO: %s" % ("none recorded (and it cannot be recorded in this file)" if rec.get("execution_go") is None else "RECORDED HERE: invalid"))
    print("T3 time-stamping: %s" % state)
    return 0 if state == "READY_FOR_OWNER_GO" else 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
