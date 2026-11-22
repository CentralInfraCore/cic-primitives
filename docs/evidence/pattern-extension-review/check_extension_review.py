"""Consistency check of the REVIEW PACKAGE of the 47 proposed extension cases. An ISOLATED check, not a CI gate; it changes nothing and does not add a case to the approved vector set.
Checks (a failure is a FAIL-EXPECT line, exit 1; an unreadable input is INCOMPLETE, exit 2, never a result):
  approved   the approved vector file (513 vectors) is byte-for-byte the approved one (SHA-256 held here, independently of the package)
  review     every case of extension-cases.yaml has exactly one review entry and vice versa; each entry has a derivation, a rule that names a known obligation or a section of the specification, and decision
             dependencies from D1 to D6 inside its group's set; no case depends on D7 or D8 (they are on hold); every requirement named by a case exists in the approved vector file
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
fails = []


def expect(label, cond, detail=""):
    if not cond:
        fails.append(label); print("FAIL-EXPECT %s %s" % (label, detail))


def arg(argv, name, default):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else default


def flat(s):
    return " ".join(str(s).split())


def render(cases, review):
    rv = {r["id"]: r for r in review["cases"]}
    out = ["| Case | Input | Expected | Derivation from the text | Rule | Depends on |", "|---|---|---|---|---|---|"]
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
        out.append("| %s | %s | %s | %s | %s | %s |" % (c["id"], inp.replace("|", "/"), exp, flat(r["derive"]).replace("|", "/"), r["rule"], ", ".join(r["depends"]) or "none"))
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
        print(render(cases, review)); return 0
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
    for c in cases["cases"]:
        for q in c.get("req", []):
            expect("case.reqs.known.%s.%s" % (c["id"], q), q in reqs, "unknown requirement")
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
