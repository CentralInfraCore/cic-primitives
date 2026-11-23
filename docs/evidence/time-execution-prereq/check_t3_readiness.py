"""The READINESS check of the T3 time-stamping (docs/design/time-evidence/t3-execution-prerequisites.yaml): where is the time-stamping in its STATE MACHINE, and how do we know? An ISOLATED check, not a CI gate;
it performs nothing and can never give the GO. It keeps four things apart: the DECISIONS (proposed, or confirmed by a RECORDED statement), the CONDITIONS (each in a phase), the GO (a separate owner record) and the verdict.

PHASES of a condition (review T3-F3): `pre` (verified BEFORE the owner's GO), `capture` (verified only AFTER the GO, when the tokens exist), `preserve` (the end state). Under the STRICT preservation order (decision Q6a
`chosen: strict`) the conditions that carry `strict_phase: pre` count as `pre`; under `staged` they stay `preserve`.
VERDICTS, in order: INVALID (the record is inconsistent) | NOT_PREPARED (a decision is not confirmed, or a pre-execution condition is open) | PREPARED_FOR_OWNER_GO (every decision confirmed, every pre-execution condition verified WITH
evidence this check can read, no later-phase evidence) | GO_RECORDED (a valid separate GO record binds the prepared state) | EVIDENCE_CAPTURED (every capture condition verified) | PRESERVATION_COMPLETE (every preserve condition verified).
A condition that `needs_tokens` (it can only be true once the RFC 3161 tokens exist) is NEVER pre-execution, in EITHER preservation order (review T3-F6: a strict order must not demand evidence that cannot exist before the GO), may
not carry a `strict_phase`, and its evidence must be DIGEST-BOUND (`evidence.sha256`, checked against the file): a text match is enough for a reference, not for the final token and storage evidence.
THE GO BINDS (review, the digest scope): the decisions, the pre-execution conditions AND the EXPECTED SET of open records of the inventory (identifier, repository, path, ref, commit); a change of any of them after the GO
invalidates it.
NONE of them authorises anything: PREPARED_FOR_OWNER_GO is NOT the GO, and a later state needs the GO record. A condition of a later phase can be `verified` only after the GO record exists (`phase.without-go`) and in order
(`phase.order`), so evidence that can only exist after the execution is never demanded before it.

OWNER CONFIRMATIONS ARE NOT AUTHENTICATED (review T3-F4): a confirmation is a RECORDED STATEMENT {stated_by: owner, date, reference}; anyone who can edit the file can write it. The check verifies its FORM and that it claims to be
the owner's, not that it is. Authenticating it is a separate decision and is not part of the time-stamping.

THE EXACT RECORD SET (review T3-F5): when the condition C-Q1a-3 is verified, the dry-run manifest is parsed and compared with the inventory's EXPECTED SET of open records IDENTIFIER BY IDENTIFIER, with the commit and the ref of each:
a swapped record fails although the count is right. (The SHA-256 of each record's bytes is a separate check: verify_manifest.py.)

Exit: 0 for PREPARED_FOR_OWNER_GO or a later state, 1 for NOT_PREPARED or INVALID (FAIL-EXPECT lines name what is invalid; UNMET lines what is not yet met), 2 an unreadable input (never a result).
Usage: check_t3_readiness.py [--record PATH] [--inventory PATH] [--root DIR] [--go PATH] [--doc PATH] [--render]"""
import hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
REC = os.path.join(ROOT, "docs", "design", "time-evidence", "t3-execution-prerequisites.yaml")
GO = os.path.join(ROOT, "docs", "design", "time-evidence", "t3-execution-go.yaml")
INV = os.path.join(ROOT, "docs", "evidence", "time-expiry-inventory", "results", "inventory.json")
DOC = os.path.join(ROOT, "docs", "en", "T3-EXECUTION-PREREQUISITES.md")
DECISIONS = ["Q1a", "Q1b", "Q2", "Q3", "Q6", "Q6a"]
PHASES = ("pre", "capture", "preserve")
MARK = {"decisions": ("<!-- BEGIN DECISIONS TABLE -->", "<!-- END DECISIONS TABLE -->"), "conditions": ("<!-- BEGIN CONDITIONS TABLE -->", "<!-- END CONDITIONS TABLE -->")}
invalid, unmet = [], []


def bad(label, detail=""):
    invalid.append(label); print("FAIL-EXPECT %s %s" % (label, detail))


def flat(s):
    return " ".join(str(s).split()).replace("|", "/")


def render(rec):
    dt = ["| Decision | Topic | Status | Requirements that become binding if the owner confirms |", "|---|---|---|---|"]
    for d in rec["decisions"]:
        dt.append("| %s | %s | **%s**%s | %s |" % (d["id"], d["topic"], d["status"], (" (chosen: %s)" % d["chosen"]) if "chosen" in d and d["chosen"] else "", " ".join("(%d) %s" % (i + 1, flat(r)) for i, r in enumerate(d["requirements"]))))
    ct = ["| Condition | Decision | Phase | Kind | Status | Condition to verify | Evidence |", "|---|---|---|---|---|---|---|"]
    for c in rec["conditions"]:
        ev = c.get("evidence")
        ph = c["phase"] + ((" (strict: %s)" % c["strict_phase"]) if c.get("strict_phase") else "") + (" (needs tokens)" if c.get("needs_tokens") else "")
        ct.append("| %s | %s | %s | %s | **%s** | %s | %s |" % (c["id"], c["decision"], ph, c["kind"], c["status"], flat(c["text"]), ("`%s` contains %r (verified %s)" % (ev["path"], ev["must_contain"], c["verified_on"])) if ev else "none"))
    return {"decisions": "\n".join(dt), "conditions": "\n".join(ct)}


def prepared_digest(rec, eff, inv):
    """the digest of the PREPARED state: the decisions, the pre-execution conditions and the expected set of open records, canonically; a GO binds this digest"""
    body = {"expected_set": sorted(({k: r.get(k) for k in ("id", "repo", "path", "ref", "commit")} for r in inv.get("open_records", [])), key=lambda r: str(r["id"])),
            "decisions": [{k: d.get(k) for k in ("id", "status", "confirmation", "chosen", "requirements")} for d in rec["decisions"]],
            "pre": [{k: c.get(k) for k in ("id", "text", "status", "verified_on", "evidence")} for c in rec["conditions"] if eff(c) == "pre"]}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def main(argv):
    import yaml
    arg = lambda n, d: argv[argv.index(n) + 1] if n in argv and argv.index(n) + 1 < len(argv) else d
    root = arg("--root", ROOT)
    try:
        rec = yaml.safe_load(open(arg("--record", REC), encoding="utf-8")); inv = json.load(open(arg("--inventory", INV), encoding="utf-8"))
        assert isinstance(rec, dict)
        gopath = arg("--go", GO); go = yaml.safe_load(open(gopath, encoding="utf-8")) if os.path.exists(gopath) else None
    except BaseException as e:
        print("INCOMPLETE: an input cannot be read: %r" % (e,)); return 2
    if "--render" in argv:
        for k, v in render(rec).items():
            print("## %s\n%s\n" % (k, v))
        return 0
    if rec.get("prerequisites_format") != 2:
        bad("record.format", "prerequisites_format is not 2")
    src = rec.get("source") or {}
    if not (src.get("kind") in ("reviewer_recommendation", "owner_statement") and re.fullmatch(r"\d{4}-\d\d-\d\d", str(src.get("date", ""))) and str(src.get("reference", "")).strip() and str(src.get("authenticity", "")).strip()):
        bad("source.provenance", "the source needs a kind, a date, a reference and a statement of its authenticity")
    if rec.get("execution_go") is not None:
        bad("go.recorded-here", "execution_go must be null: the owner's GO to perform the time-stamping is a separate record and is never written in this file")
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
            if not (isinstance(c, dict) and c.get("stated_by") == "owner" and re.fullmatch(r"\d{4}-\d\d-\d\d", str(c.get("date", ""))) and str(c.get("reference", "")).strip()):
                bad("decision.confirmation.%s" % i, "a confirmed decision needs a recorded statement {stated_by: owner, date, reference}; the check verifies the form, it cannot authenticate the statement")
        elif c is not None:
            bad("decision.confirmation.%s" % i, "a decision that is not confirmed carries a confirmation")
        if not d.get("requirements"):
            bad("decision.requirements.%s" % i, "a decision states its requirements")
        if i == "Q6a":
            if d.get("chosen") not in (None, "staged", "strict"):
                bad("decision.chosen.Q6a", "chosen is %r: it is staged, strict or not yet chosen" % d.get("chosen"))
            elif d["status"] == "confirmed" and d.get("chosen") is None:
                bad("decision.chosen.Q6a", "Q6a is confirmed but the order is not chosen")
            elif d["status"] != "confirmed" and d.get("chosen") is not None:
                bad("decision.chosen.Q6a", "an order is chosen in a decision that is not confirmed")
        if d["status"] != "confirmed":
            unmet.append("decision %s is %s" % (i, d["status"]))
    for i in set(decs) - set(DECISIONS):
        bad("decision.unknown.%s" % i, "a decision this check does not know")
    strict = (decs.get("Q6a") or {}).get("chosen") == "strict"
    eff = lambda c: ("pre" if (strict and c.get("strict_phase") == "pre") else c.get("phase"))
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
        if c.get("phase") not in PHASES:
            bad("condition.phase.%s" % cid, "phase %r is not pre, capture or preserve" % c.get("phase"))
        if c.get("needs_tokens"):
            if c.get("phase") == "pre":
                bad("condition.tokens-phase.%s" % cid, "a condition that needs the tokens cannot be in the pre-execution phase: the tokens do not exist before the GO")
            if c.get("strict_phase"):
                bad("strict.needs-tokens.%s" % cid, "a condition that needs the tokens carries a strict_phase: the strict order would demand evidence that cannot exist before the GO")
        st, ev = c.get("status"), c.get("evidence")
        if st == "open":
            if ev is not None:
                bad("condition.open-with-evidence.%s" % cid, "an open condition names evidence: verify it or remove it")
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
                elif c.get("needs_tokens") and (not re.fullmatch(r"[0-9a-f]{64}", str(ev.get("sha256", ""))) or hashlib.sha256(open(p, "rb").read()).hexdigest() != ev["sha256"]):
                    bad("condition.digest.%s" % cid, "the evidence of a condition that needs the tokens must be digest-bound: evidence.sha256 equal to the SHA-256 of the file")
        else:
            bad("condition.status.%s" % cid, "status %r" % st)
    for i in DECISIONS:
        if i in decs and i != "Q6a" and not any(c.get("decision") == i for c in conds):                 # Q6a is a CHOICE (the order), its effect is in the phases of the Q6 conditions
            bad("decision.conditions.%s" % i, "a decision with no condition cannot be shown ready")
    for c in conds:
        if c.get("needs_tokens") and eff(c) == "pre":
            bad("phase.tokens-before-go.%s" % c.get("id"), "under the %s order the condition that needs the tokens is pre-execution" % ("strict" if strict else "chosen"))
    pre = [c for c in conds if eff(c) == "pre"]; cap = [c for c in conds if eff(c) == "capture"]; pres = [c for c in conds if eff(c) == "preserve"]
    for c in pre:
        if c.get("status") != "verified":
            unmet.append("pre-execution condition %s is open: %s" % (c.get("id"), str(c.get("text", ""))[:90]))
    prepared = not invalid and not unmet
    # the GO record
    state = None
    gd = None
    if go is not None:
        gd = prepared_digest(rec, eff, inv)
        if not (isinstance(go, dict) and go.get("go_format") == 1 and go.get("gate") == "t3-execution" and go.get("stated_by") == "owner" and re.fullmatch(r"\d{4}-\d\d-\d\d", str(go.get("date", ""))) and str(go.get("reference", "")).strip()):
            bad("go.format", "the GO record needs go_format 1, gate t3-execution, a recorded statement stated_by owner, a date and a reference")
        elif go.get("prepared_digest") != gd:
            bad("go.digest", "the GO names another prepared state (the decisions or the pre-execution conditions changed after the GO, or it binds a different record)")
        elif not prepared:
            bad("go.not-prepared", "a GO record exists but the record is not PREPARED_FOR_OWNER_GO")
    # later-phase evidence needs the GO, and the order
    go_ok = go is not None and not any(x.startswith("go.") for x in invalid)
    for c in cap + pres:
        if c.get("status") == "verified" and not go_ok:
            bad("phase.without-go", "%s (%s) is verified but no valid GO record exists: evidence of the execution cannot exist before it" % (c.get("id"), eff(c)))
    if any(c.get("status") == "verified" for c in pres) and any(c.get("status") != "verified" for c in cap):
        bad("phase.order", "a preserve condition is verified before every capture condition is")
    if invalid:
        state = "INVALID"
    elif not prepared:
        state = "NOT_PREPARED"
    elif not go_ok:
        state = "PREPARED_FOR_OWNER_GO"
    elif all(c.get("status") == "verified" for c in cap) and all(c.get("status") == "verified" for c in pres):
        state = "PRESERVATION_COMPLETE"
    elif all(c.get("status") == "verified" for c in cap):
        state = "EVIDENCE_CAPTURED"
    else:
        state = "GO_RECORDED"
    # the exact record set, when the dry run is claimed
    c3 = next((c for c in conds if c.get("id") == "C-Q1a-3"), None)
    if c3 and c3.get("status") == "verified":
        mp = os.path.join(root, (c3.get("evidence") or {}).get("path", ""))
        if os.path.isfile(mp):
            sys.path.insert(0, os.path.join(root, "docs", "evidence", "time-manifest"))
            try:
                import manifestlib as M
                _, count, entries = M.parse(open(mp, "rb").read())
            except BaseException as e:
                bad("manifest.form", "the dry-run manifest is not in the canonical form: %s" % (e,)); entries = None
            if entries is not None:
                got = {e[0]: e for e in entries}; want = {r["id"]: r for r in inv.get("open_records", [])}
                for i in sorted(set(want) - set(got)):
                    bad("manifest.set.missing.%s" % i, "the expected record is not in the manifest")
                for i in sorted(set(got) - set(want)):
                    bad("manifest.set.extra.%s" % i, "the manifest holds a record that is not in the expected set")
                for i in sorted(set(got) & set(want)):
                    g, w = got[i], want[i]
                    if (g[3], g[4], g[5], g[6]) != (w["repo"], w["commit"], w["ref"], w["path"]):
                        bad("manifest.entry.%s" % i, "the repository, commit, ref or path differs from the expected set")
                if not want:
                    bad("manifest.set.empty", "the inventory has no expected set of open records")
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
    if "--doc" in argv:
        try:
            doc = open(arg("--doc", DOC), encoding="utf-8").read(); tables = render(rec)
        except BaseException as e:
            print("INCOMPLETE: the document cannot be read: %r" % (e,)); return 2
        for k, (b, e) in MARK.items():
            if b in doc and e in doc:
                if doc.split(b, 1)[1].split(e, 1)[0].strip() != tables[k].strip():
                    bad("doc.table.%s" % k, "the %s table of the document differs from the table rendered from the record" % k)
            else:
                bad("doc.markers.%s" % k, "the document has no %s table markers" % k)
        nv = lambda cs: sum(1 for c in cs if c.get("status") == "verified")
        says = "Of the %d conditions, **%d of the %d pre-execution conditions are verified**, %d of %d capture, %d of %d preserve" % (len(conds), nv(pre), len(pre), nv(cap), len(cap), nv(pres), len(pres))
        if says not in doc:
            bad("doc.counts", "the document does not say: %s" % says)
        if invalid and state != "INVALID":
            state = "INVALID"
    if invalid:
        state = "INVALID"
    print("%-5s %-10s %s" % ("id", "status", "pre-execution conditions verified"))
    for i in DECISIONS:
        if i in decs:
            cs = [c for c in pre if c.get("decision") == i]
            print("%-5s %-10s %d of %d" % (i, decs[i].get("status"), sum(1 for c in cs if c.get("status") == "verified"), len(cs)))
    print("phases (order %s): pre %d of %d verified, capture %d of %d, preserve %d of %d" % ("STRICT" if strict else ("STAGED" if (decs.get("Q6a") or {}).get("chosen") == "staged" else "not chosen"), sum(1 for c in pre if c.get("status") == "verified"), len(pre), sum(1 for c in cap if c.get("status") == "verified"), len(cap), sum(1 for c in pres if c.get("status") == "verified"), len(pres)))
    for u in unmet:
        print("UNMET %s" % u)
    print("owner confirmations: recorded statements, NOT authenticated by this check (the form is verified, the author is not)")
    print("execution GO: %s" % ("none recorded (and it cannot be recorded in the prerequisites file)" if go is None else ("a GO record is present%s" % (" and binds the prepared state" if go_ok else ", INVALID"))))
    print("T3 time-stamping: %s" % state)
    return 0 if state in ("PREPARED_FOR_OWNER_GO", "GO_RECORDED", "EVIDENCE_CAPTURED", "PRESERVATION_COMPLETE") else 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
