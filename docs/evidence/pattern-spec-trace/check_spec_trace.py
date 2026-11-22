"""Traceability and consistency check of the implementation specification package. An ISOLATED check, not a CI gate; it implements nothing of the profile and changes nothing.
Checks (a failure is a FAIL-EXPECT line, exit 1; an unreadable input is INCOMPLETE, exit 2, never a result):
  approved   the approved vector file is byte-for-byte the approved one (SHA-256 held here, independently of the package): the 513 vectors are an unchanged reference
  structure  obligations and plan items: unique ids, roles from the allowed set, texts present, requirements known, every obligation says how it is verified
  coverage   every one of the 66 requirements and the 4 requirements that a verdict vector cannot test is named by at least one obligation; an obligation that names a requirement without a verdict vector
             has a plan item; an obligation verified by vectors names only requirements that have at least one vector; every role has an obligation; every plan item is used
  spec       the specification text mentions every obligation id and every plan id
  extension  the proposed extension cases are consistent with the rules of the text (the executable reading spec_model.py), every case group belongs to a plan item, and the same model reproduces the
             verdicts and positions of the 20 schema vectors of the approved set
Usage: check_spec_trace.py [--obligations PATH] [--spec PATH] [--vectors PATH] [--cases PATH]"""
import hashlib, os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGN = os.path.join(HERE, "..", "..", "design")
OBL = os.path.join(DESIGN, "pattern-profile-spec", "obligations.yaml")
CASES = os.path.join(DESIGN, "pattern-profile-spec", "extension-cases.yaml")
VEC = os.path.join(DESIGN, "pattern-profile-vectors", "pattern-profile.yaml")
SPEC = os.path.join(HERE, "..", "..", "en", "GRAMMAR-PATTERN-IMPLEMENTATION-SPEC.md")
APPROVED_SHA256 = "e7ece43a9486187c16a482a96a86d22cf82407711be940920155f4e3abe277e0"      # the vector file approved in #50 and #51
ROLES = {"reader", "validator", "producer", "verifier", "gate"}
PLAN_STATUS = {"non-vector-test", "reader-test", "proposed-extension"}
GROUP_PLAN = {"E-PIN": "P-07", "E-TRV": "P-08", "E-RDR": "P-06"}
fails = []


def expect(label, cond, detail=""):
    if not cond:
        fails.append(label); print("FAIL-EXPECT %s %s" % (label, detail))


def arg(argv, name, default):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else default


def main(argv):
    import yaml
    sys.path.insert(0, HERE)
    try:
        obl = yaml.safe_load(open(arg(argv, "--obligations", OBL), encoding="utf-8"))
        vec_path = arg(argv, "--vectors", VEC)
        vraw = open(vec_path, "rb").read(); vec = yaml.safe_load(vraw)
        cases = yaml.safe_load(open(arg(argv, "--cases", CASES), encoding="utf-8"))
        spec = open(arg(argv, "--spec", SPEC), encoding="utf-8").read()
    except BaseException as e:
        print("INCOMPLETE: an input cannot be read: %r" % (e,)); return 2
    expect("approved.unchanged", hashlib.sha256(vraw).hexdigest() == APPROVED_SHA256, "the vector file is not the approved one (SHA-256 %s)" % hashlib.sha256(vraw).hexdigest())
    reqs = {r["id"] for r in vec["requirements"]}; nt = {r["id"] for r in vec["not_testable_by_vectors"]}
    byreq = collections.defaultdict(list)
    for k in ("expressions", "values", "schemas"):
        for v in vec[k]:
            for r in v.get("req", []):
                byreq[r].append(v["id"])
    obs = obl["obligations"]; plan = obl["plan"]
    ids = [o["id"] for o in obs]; pids = [p["id"] for p in plan]
    for i, n in collections.Counter(ids).items():
        expect("obligation.id.unique.%s" % i, n == 1)
    for i, n in collections.Counter(pids).items():
        expect("plan.id.unique.%s" % i, n == 1)
    used_plan, covered, rolecount = set(), set(), collections.Counter()
    for o in obs:
        i = o["id"]
        expect("obligation.roles.%s" % i, bool(o.get("roles")) and set(o["roles"]) <= ROLES, "roles %s" % o.get("roles"))
        expect("obligation.text.%s" % i, bool(str(o.get("text", "")).strip()))
        rs = o.get("reqs") or []
        expect("obligation.reqs.present.%s" % i, bool(rs))
        for r in rs:
            expect("obligation.reqs.known.%s.%s" % (i, r), r in reqs or r in nt, "unknown requirement")
        covered |= set(rs)
        for role in o.get("roles", []):
            rolecount[role] += 1
        ver = o.get("verify") or {}
        pl = ver.get("plan") or []
        expect("obligation.verify.%s" % i, ver.get("vectors") is True or bool(pl), "an obligation must be verified by vectors or by a plan item")
        for p in pl:
            expect("obligation.plan.known.%s.%s" % (i, p), p in pids)
            used_plan.add(p)
        if any(r in nt for r in rs):
            expect("obligation.nt-needs-plan.%s" % i, bool(pl), "names a requirement that no verdict vector can test, so it needs a plan item")
        if ver.get("vectors") is True:
            for r in rs:
                expect("obligation.vectors.cover.%s.%s" % (i, r), r in reqs and r in byreq, "verified by vectors but no vector names this requirement")
    for p in plan:
        i = p["id"]
        expect("plan.status.%s" % i, p.get("status") in PLAN_STATUS)
        for f in ("method", "evidence", "cases"):
            expect("plan.field.%s.%s" % (i, f), bool(str(p.get(f, "")).strip()))
        for r in p.get("reqs", []):
            expect("plan.reqs.known.%s.%s" % (i, r), r in reqs or r in nt)
        expect("plan.referenced.%s" % i, i in used_plan, "no obligation uses this plan item")
    for r in sorted(reqs | nt):
        expect("coverage.requirement.%s" % r, r in covered, "no obligation names this requirement")
    for role in sorted(ROLES):
        expect("roles.coverage.%s" % role, rolecount[role] > 0, "no obligation for this role")
    for i in ids + pids:
        expect("spec.mentions.%s" % i, i in spec, "the specification text does not mention it")
    # the proposed extension cases against the executable reading of the rules
    import spec_model as M
    cids = [c["id"] for c in cases["cases"]]
    expect("extension.ids.unique", len(cids) == len(set(cids)))
    for c in cases["cases"]:
        g = c["id"].rsplit("-", 1)[0]
        expect("extension.group.%s" % c["id"], g in GROUP_PLAN and GROUP_PLAN[g] in pids, "the case group has no plan item")
        for r in c.get("req", []):
            expect("extension.req.known.%s.%s" % (c["id"], r), r in reqs)
        got = M.validate(c["schema"], c["pin"]); e = c["expect"]
        if e["outcome"] == "accept":
            ok = got == ("accept",)
        elif e["outcome"] == "refuse":
            ok = got[0] == "refuse" and got[1] == e["code"] and got[2] == e["at"]
        else:
            ok = got[0] == "reader_error" and got[1] == e["kind"]
        expect("extension.model.%s" % c["id"], ok, "model %s, expected %s" % (got, e))
    # the same rules reproduce the schema vectors of the approved set (the flat schemas of the vector file)
    for s in vec["schemas"]:
        pin = s["pin"]; st = pin["state"]
        decl = [] if st == "missing" else (pin["versions"] if st in ("conflict", "declared") else [pin["version"]])
        doc = {"n%d" % i: {"contract": [{"type": "pattern", "expression": __import__("vectors_lib").dec(c["expr"])}]} for i, c in enumerate(s["contracts"], 1)}
        got = M.validate(yaml.safe_dump(doc, default_flow_style=False, allow_unicode=True) if doc else "{}", decl)
        if s["expect"] == "accept":
            ok = got == ("accept",)
        else:
            at = None if s.get("at") is None else "n%d/contract/0" % s["at"]
            ok = got[0] == "refuse" and got[1] == s["code"] and got[2] == at
        expect("approved.schema-vectors.model.%s" % s["id"], ok, "model %s, vector %s %s at %s" % (got, s["expect"], s.get("code"), s.get("at")))
    print("obligations %d, plan items %d, requirements %d (+%d not testable by vectors), extension cases %d, approved schema vectors %d" % (len(obs), len(plan), len(reqs), len(nt), len(cases["cases"]), len(vec["schemas"])))
    print("## requirement -> obligations")
    for r in sorted(reqs | nt):
        print("%-26s %s" % (r, " ".join(o["id"] for o in obs if r in (o.get("reqs") or []))))
    print("## plan item -> obligations")
    for p in plan:
        print("%-5s %-18s %s" % (p["id"], p["status"], " ".join(o["id"] for o in obs if p["id"] in ((o.get("verify") or {}).get("plan") or []))))
    if fails:
        print("FAILED: %d expectation(s)" % len(fails)); return 1
    print("all expectations held"); return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(HERE, "..", "pattern-vectors"))
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
