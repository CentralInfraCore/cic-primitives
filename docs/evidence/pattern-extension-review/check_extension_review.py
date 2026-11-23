"""Consistency check of the REVIEW PACKAGE of the 47 proposed extension cases. An ISOLATED check, not a CI gate; it changes nothing and does not add a case to the approved vector set.
Checks (a failure is a FAIL-EXPECT line, exit 1; an unreadable input is INCOMPLETE, exit 2, never a result):
  approved   the approved vector file (513 vectors) is byte-for-byte the approved one (SHA-256 held here, independently of the package)
  review     every case of extension-cases.yaml has exactly one review entry and vice versa; each entry has a derivation, a rule that names a known obligation or a section of the specification, and decision
             dependencies from D1 to D6 inside its group's set; no case depends on D7 or D8 (they are on hold); every requirement named by a case exists in the approved vector file
  verifies   what a case really VERIFIES is kept apart from what it is only RELATED to (review F1 of #53): every requirement a case names is in exactly one of `verifies` and `related`, a case may verify a requirement
             only if its expected outcome is the kind of outcome that the requirement states (a reader error never verifies a pattern verdict), and nothing that it could verify is left as merely related;
             the coverage of a requirement counts the verifying cases only
  decisions  the decision dependencies are COMPLETE as far as the features of a case show it (review F2 of #53): each decision D1 to D6 has a feature rule (a wrong-typed or conflicting declared pin, a null
             declaration, an accepted schema without a pattern contract, the traversal group, an expression that is not a string, any reader error); a case whose features need a decision that it does not list fails.
             THE LIMIT: this is a lower bound by features, not a proof of completeness; a dependency that none of the six rules sees can be found only by review
  model      the executable reading of the rules (spec_model.py) gives the expected result of every case (0 differences)
  doc        the case table of the review document is exactly the table rendered from the data (nothing is hand-edited into it)
Usage: check_extension_review.py [--render] [--review PATH] [--cases PATH] [--doc PATH] [--vectors PATH] [--obligations PATH]"""
import hashlib, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGN = os.path.join(HERE, "..", "..", "design")
REVIEW = os.path.join(DESIGN, "pattern-profile-spec", "extension-review.yaml")
CASES = os.path.join(DESIGN, "pattern-profile-spec", "extension-cases.yaml")
OBL = os.path.join(DESIGN, "pattern-profile-spec", "obligations.yaml")
VEC = os.path.join(DESIGN, "pattern-profile-vectors", "pattern-profile.yaml")
DOC = os.path.join(HERE, "..", "..", "en", "GRAMMAR-PATTERN-EXTENSION-CASES-REVIEW.md")
APPROVED_SHA256 = "e7ece43a9486187c16a482a96a86d22cf82407711be940920155f4e3abe277e0"
BEGIN, END = "<!-- BEGIN CASE TABLE -->", "<!-- END CASE TABLE -->"
DECISIONS = {"D1", "D2", "D3", "D4", "D5", "D6"}
PIN_CODES = {"pattern_profile_missing", "pattern_profile_unknown", "pattern_profile_conflict"}
BEGIN2, END2 = "<!-- BEGIN REQ TABLE -->", "<!-- END REQ TABLE -->"
fails = []


def may_verify(req, e):
    """may a case with the expected result e VERIFY the requirement req? A reader error is not a pattern verdict and verifies none of them."""
    o, code = e["outcome"], e.get("code")
    if o == "reader_error":
        return False
    return {"R-PIN-UNKNOWN": o == "refuse" and code == "pattern_profile_unknown",
            "R-PIN-CONFLICT": o == "refuse" and code == "pattern_profile_conflict",
            "R-PIN-MISSING": o == "refuse" and code == "pattern_profile_missing",
            "R-PIN-IDENTICAL": (o == "refuse" and code == "pattern_profile_unknown") or o == "accept",
            "R-PIN-ONLY-IF-PATTERN": o == "accept",
            "R-PIN-FIRST": o == "refuse" and code in PIN_CODES,
            "R-SCHEMA-ORDER": o == "refuse" and code not in PIN_CODES,
            "R-SCHEMA-WHOLE": o == "refuse" and code not in PIN_CODES}.get(req, False)


def has_null(c):
    if any(v is None for v in (c.get("pin") or [])):
        return True
    return bool(re.search(r"(^|[\s\[,{:])(null|~)([\s\],}]|$)", str(c.get("pin_text") or "")))


def required_decisions(c):
    """the decisions that the FEATURES of a case need (a lower bound, not a proof)"""
    e = c["expect"]; need = set()
    has_pin = bool(c.get("pin")) or bool(c.get("pin_text"))
    contract = "type: pattern" in c["schema"]
    if has_pin and contract and ((e["outcome"] == "refuse" and e.get("code") in ("pattern_profile_unknown", "pattern_profile_conflict"))
                                 or (e["outcome"] == "reader_error" and e.get("kind") in ("duplicate_key", "non_scalar_key") and c.get("pin_text"))):
        need.add("D1")
    if has_null(c):
        need.add("D2")
    if e["outcome"] == "accept" and not contract and has_pin:
        need.add("D3")
    if c["id"].startswith("E-TRV"):
        need.add("D4")
    if e["outcome"] == "reader_error" and e.get("kind") == "expression_not_a_string":
        need.add("D5")
    if e["outcome"] == "reader_error":
        need.add("D6")
    return need


def expect(label, cond, detail=""):
    if not cond:
        fails.append(label); print("FAIL-EXPECT %s %s" % (label, detail))


def arg(argv, name, default):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else default


def flat(s):
    return " ".join(str(s).split())


def render(cases, review):
    rv = {r["id"]: r for r in review["cases"]}
    out = ["| Case | Input | Expected | Derivation from the text | Rule | Depends on | Verifies | Only related |", "|---|---|---|---|---|---|---|---|"]
    for c in cases["cases"]:
        e = c["expect"]
        if "pin_text" in c:
            inp = "pin (YAML text) `%s`" % flat(c["pin_text"])
        elif "pin" in c:
            import yaml as _y
            inp = "pin `%s`" % flat(_y.safe_dump(c["pin"], default_flow_style=True).rstrip().rstrip("."))
        else:
            inp = ""
        if c["id"].startswith(("E-TRV", "E-RDR")) or "schema" in c and c["schema"].strip() != "a: {contract: [{type: pattern, expression: '^a$'}]}":
            inp = (inp + "; " if inp else "") + "schema `%s`" % flat(c["schema"])
        if e["outcome"] == "accept":
            exp = "accept"
        elif e["outcome"] == "refuse":
            exp = "refuse `%s`" % e["code"] + (" at `%s`" % e["at"] if e.get("at") else "")
        else:
            exp = "reader error `%s`" % e["kind"]
        r = rv[c["id"]]
        out.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (c["id"], inp.replace("|", "/"), exp, flat(r["derive"]).replace("|", "/"), r["rule"], ", ".join(r["depends"]) or "none", ", ".join(r.get("verifies", [])) or "none", ", ".join(r.get("related", [])) or "none"))
    return "\n".join(out)


def render_reqs(cases, review):
    """the requirement matrix: which cases VERIFY a requirement and which are only RELATED to it"""
    rv = {r["id"]: r for r in review["cases"]}; verif, rel = {}, {}
    for c in cases["cases"]:
        for q in rv[c["id"]].get("verifies", []):
            verif.setdefault(q, []).append(c["id"])
        for q in rv[c["id"]].get("related", []):
            rel.setdefault(q, []).append(c["id"])
    out = ["| Requirement | Verified by (cases) | Only related (cases) |", "|---|---|---|"]
    for q in sorted(set(verif) | set(rel)):
        out.append("| %s | %d: %s | %d: %s |" % (q, len(verif.get(q, [])), ", ".join(verif.get(q, [])) or "none", len(rel.get(q, [])), ", ".join(rel.get(q, [])) or "none"))
    return "\n".join(out)


def main(argv):
    import yaml
    sys.path.insert(0, os.path.join(HERE, "..", "pattern-spec-trace"))
    try:
        review = yaml.safe_load(open(arg(argv, "--review", REVIEW), encoding="utf-8"))
        cases = yaml.safe_load(open(arg(argv, "--cases", CASES), encoding="utf-8"))
        obl = yaml.safe_load(open(arg(argv, "--obligations", OBL), encoding="utf-8"))
        vraw = open(arg(argv, "--vectors", VEC), "rb").read(); vec = yaml.safe_load(vraw)
        doc = open(arg(argv, "--doc", DOC), encoding="utf-8").read() if "--render" not in argv else ""
    except BaseException as e:
        print("INCOMPLETE: an input cannot be read: %r" % (e,)); return 2
    if "--render" in argv:
        print(render(cases, review)); print(); print(render_reqs(cases, review)); return 0
    expect("approved.unchanged", hashlib.sha256(vraw).hexdigest() == APPROVED_SHA256, "the vector file is not the approved one (SHA-256 %s)" % hashlib.sha256(vraw).hexdigest())
    reqs = {r["id"] for r in vec["requirements"]}; obs = {o["id"] for o in obl["obligations"]}
    cids = [c["id"] for c in cases["cases"]]; rids = [r["id"] for r in review["cases"]]
    expect("review.ids.unique", len(cids) == len(set(cids)) and len(rids) == len(set(rids)))
    expect("review.ids.equal", set(cids) == set(rids), "missing from the review: %s; not a case: %s" % (sorted(set(cids) - set(rids)), sorted(set(rids) - set(cids))))
    for r in review["cases"]:
        i = r["id"]; g = i.rsplit("-", 1)[0]
        grp = (review.get("groups") or {}).get(g)
        expect("review.group.%s" % i, grp is not None, "no group %s" % g)
        expect("review.derive.%s" % i, len(flat(r.get("derive", ""))) >= 25, "the derivation is missing or too short")
        toks = re.findall(r"O-[A-Z]{2}-\d\d", r.get("rule", ""))
        expect("review.rule.%s" % i, bool(r.get("rule")) and (bool(toks) or "section" in r["rule"]), "the rule names neither an obligation nor a section")
        for t in toks:
            expect("review.rule.known.%s.%s" % (i, t), t in obs, "unknown obligation")
        deps = set(r.get("depends", []))
        expect("review.depends.known.%s" % i, deps <= DECISIONS, "decisions outside D1..D6 (D7 and D8 are on hold): %s" % sorted(deps - DECISIONS))
        if grp:
            expect("review.depends.group.%s" % i, deps <= set(grp["depends"]), "depends on %s outside the group's set %s" % (sorted(deps - set(grp["depends"])), grp["depends"]))
        expect("review.status.%s" % i, r.get("status") == "proposed", "status %r" % r.get("status"))
    rvm = {r["id"]: r for r in review["cases"]}
    for c in cases["cases"]:
        for q in c.get("req", []):
            expect("case.reqs.known.%s.%s" % (c["id"], q), q in reqs, "unknown requirement")
        r = rvm.get(c["id"])
        if r is None:
            continue
        ver, relt = list(r.get("verifies", [])), list(r.get("related", []))
        expect("verifies.partition.%s" % c["id"], sorted(ver + relt) == sorted(c.get("req", [])) and not (set(ver) & set(relt)), "verifies %s and related %s are not a partition of the requirements the case names %s" % (ver, relt, c.get("req", [])))
        for q in ver:
            expect("verifies.sound.%s.%s" % (c["id"], q), may_verify(q, c["expect"]), "the expected result %s is not the kind of outcome that %s states: the case cannot verify it, only be related to it" % (c["expect"], q))
        for q in relt:
            expect("verifies.complete.%s.%s" % (c["id"], q), not may_verify(q, c["expect"]), "the expected result is the kind of outcome that %s states: the case verifies it" % q)
        miss = required_decisions(c) - set(r.get("depends", []))
        expect("decisions.complete.%s" % c["id"], not miss, "the features of the case need %s, which it does not list" % sorted(miss))
    import spec_model as M
    for c in cases["cases"]:
        try:
            got = M.validate_case(c["schema"], c.get("pin"), c.get("pin_text"))
        except BaseException as ex:
            got = ("model_raised", type(ex).__name__)
        e = c["expect"]
        if e["outcome"] == "accept":
            ok = got == ("accept",)
        elif e["outcome"] == "refuse":
            ok = got[0] == "refuse" and got[1] == e["code"] and got[2] == e["at"]
        else:
            ok = got[0] == "reader_error" and got[1] == e["kind"]
        expect("model.%s" % c["id"], ok, "model %s, expected %s" % (got, e))
    if BEGIN2 in doc and END2 in doc:
        try:
            freshq = render_reqs(cases, review).strip()
        except KeyError as ex:
            freshq = None
        if freshq is not None:
            expect("doc.reqtable.in-sync", doc.split(BEGIN2, 1)[1].split(END2, 1)[0].strip() == freshq, "the requirement matrix of the document differs from the matrix rendered from the data")
    else:
        expect("doc.reqtable.markers", False, "the document has no requirement-matrix markers")
    if BEGIN in doc and END in doc:
        have = doc.split(BEGIN, 1)[1].split(END, 1)[0].strip()
        try:
            fresh = render(cases, review).strip()
        except KeyError as ex:                       # a case without a review entry: reported above, and the table cannot be rendered
            fresh = None
            expect("doc.table.in-sync", False, "the table cannot be rendered: no review entry for %s" % ex)
        if fresh is not None:
            expect("doc.table.in-sync", have == fresh, "the case table of the document differs from the table rendered from the data")
    else:
        expect("doc.table.markers", False, "the document has no case-table markers")
    groups = {}
    for c in cases["cases"]:
        groups[c["id"].rsplit("-", 1)[0]] = groups.get(c["id"].rsplit("-", 1)[0], 0) + 1
    deps = {d: sum(1 for r in review["cases"] if d in r.get("depends", [])) for d in sorted(DECISIONS)}
    for d, n in deps.items():
        expect("doc.counts.%s" % d, ("| %s | %d " % (d, n)) in doc, "the decision table of the document does not say that %d cases need %s" % (n, d))
    for g, n in groups.items():
        expect("doc.group.%s" % g, ("| `%s` | %d |" % (g, n)) in doc, "the group table of the document does not say %d cases for %s" % (n, g))
    nv = sum(1 for r in review["cases"] if r.get("verifies")); nvq = sum(len(r.get("verifies", [])) for r in review["cases"]); nrq = sum(len(r.get("related", [])) for r in review["cases"])
    extra = sum(1 for c in cases["cases"] if c["id"] in rvm and set(rvm[c["id"]].get("depends", [])) - required_decisions(c))
    print("requirement links: %d verified, %d only related; %d of %d cases verify at least one requirement; %d cases list a decision above the lower bound of the feature rules" % (nvq, nrq, nv, len(cids), extra))
    print("cases %d (%s); cases that need each decision: %s; D7 and D8: none" % (len(cids), ", ".join("%s %d" % kv for kv in sorted(groups.items())), ", ".join("%s %d" % kv for kv in deps.items())))
    if fails:
        print("FAILED: %d expectation(s)" % len(fails)); return 1
    print("all expectations held"); return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
