"""Traceability and consistency check of the implementation specification package. An ISOLATED check, not a CI gate; it implements nothing of the profile and changes nothing.
Checks (a failure is a FAIL-EXPECT line, exit 1; an unreadable input is INCOMPLETE, exit 2, never a result):
  approved   the approved vector file is byte-for-byte the approved one (SHA-256 held here, independently of the package): the 513 vectors are an unchanged reference
  structure  obligations and plan items: unique ids, roles from the allowed set, texts present, requirements known, every obligation says how it is verified
  coverage   every one of the 66 requirements and the 4 requirements that a verdict vector cannot test is named by at least one obligation; an obligation that names a requirement without a verdict vector
             has a plan item; an obligation verified by vectors names only requirements that have at least one vector; every role has an obligation; every plan item is used
  spec       the specification text mentions every obligation id and every plan id
  covers     every requirement of an obligation is actually COVERED by what the obligation cites: by the approved vectors (when it cites them and a vector names the requirement) or by a cited plan
             item whose own requirements include it (a plan id that merely exists is not enough); an obligation may carry spec_must_contain phrases that must stand in the text and in the specification
  property   the accept/refuse CLASS of a schema is invariant under every permutation of the delivery order (the reported code and path are not), and the delivery digest, unlike the content digest, tells
             two delivery orders apart
  evidence   the EVIDENCE IDENTIFIER (review F2 of #52, second round) binds the whole validation input: the profile version, the contracts, the typed pin declarations, the implementation identity and the
             conformance reference. A changed pin with unchanged contracts changes both keys and must never make an earlier result reusable; a component digest alone is never a reuse key; the typed
             canonical encoding of a declared value is equal for two values iff they are identical
  extension  the proposed extension cases are consistent with the rules of the text (the executable reading spec_model.py), every case group belongs to a plan item, and the same model reproduces the
             verdicts and positions of the 20 schema vectors of the approved set
This is STRUCTURAL traceability plus the consistency checks above: it shows that the package is complete and self-consistent, NOT that the plan items, once executed, give full semantic coverage.
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
        planreqs = {p["id"]: set(p.get("reqs", [])) for p in plan}
        for r in rs:
            by_vec = ver.get("vectors") is True and r in reqs and r in byreq
            by_plan = any(r in planreqs.get(p, set()) for p in pl)
            expect("obligation.covers.%s.%s" % (i, r), by_vec or by_plan, "neither the cited vectors nor a cited plan item that lists this requirement covers it")
        for phrase in o.get("spec_must_contain", []):
            expect("consistency.text.%s" % i, phrase.lower() in str(o.get("text", "")).lower(), "the obligation text lacks %r" % phrase)
            expect("consistency.spec.%s" % i, phrase.lower() in spec.lower(), "the specification lacks %r" % phrase)
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
        try:
            got = M.validate_case(c["schema"], c.get("pin"), c.get("pin_text"))
        except BaseException as ex:                      # a model that crashes is a failed check, never a pass and never an infrastructure problem
            got = ("model_raised", type(ex).__name__)
        e = c["expect"]
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
    # the binding of a result to its input: the class is order independent, the code and the path are not, and the delivery digest sees the order
    import itertools
    seen_code_change = False
    def classes(decl, items, label):
        nonlocal seen_code_change
        outs = [M.validate_delivered(decl, list(pm)) for pm in itertools.permutations(items)]
        cl = {o[0] for o in outs}
        expect("property.class-order-independent.%s" % label, len(cl) == 1, "the class changes with the delivery order: %s" % sorted(cl))
        if len({o[1:] for o in outs}) > 1:
            seen_code_change = True
    for c in cases["cases"]:
        if c["id"].startswith("E-TRV"):
            try:
                items = M.deliver(c["schema"])
            except Exception:
                continue
            if 1 < len(items) <= 5:
                classes(c["pin"], items, c["id"])
    for sv in vec["schemas"]:
        if len(sv["contracts"]) >= 2 and sv["pin"]["state"] in ("ok", "declared"):
            items = [(("n%d" % i, "contract", 0), __import__("vectors_lib").dec(c["expr"])) for i, c in enumerate(sv["contracts"], 1)]
            decl = sv["pin"]["versions"] if sv["pin"]["state"] == "declared" else [sv["pin"]["version"]]
            if len(items) <= 5:
                classes(decl, items, sv["id"])
    expect("property.code-depends-on-order", seen_code_change, "no case shows that the reported code or path depends on the delivery order (the corpus does not demonstrate the difference)")
    cmap = {c["id"]: c for c in cases["cases"]}
    try:
        a, b = M.deliver(cmap["E-TRV-01"]["schema"]), M.deliver(cmap["E-TRV-02"]["schema"])
        expect("digest.content-equal", M.content_digest(a) == M.content_digest(b), "the two documents have different content")
        expect("digest.order-sensitive", M.delivery_digest(a) != M.delivery_digest(b), "the delivery digest does not tell the two delivery orders apart")
        ra, rb = M.validate(cmap["E-TRV-01"]["schema"], [1]), M.validate(cmap["E-TRV-02"]["schema"], [1])
        ia, ib = M.deliver(cmap["E-TRV-01"]["schema"]), M.deliver(cmap["E-TRV-02"]["schema"])
        ka = M.class_key(1, ia, [1], "impl", "ref"); kb = M.class_key(1, ib, [1], "impl", "ref")
        expect("evidence.order-only.class-key-equal", ka == kb, "the same contracts in another delivery order must share the class key")
        expect("evidence.order-only.result-key-differs", M.result_key(1, ia, [1], "impl", "ref") != M.result_key(1, ib, [1], "impl", "ref"), "the result key must tell the two delivery orders apart")
        pa = dict(class_key=ka, result_key=M.result_key(1, ia, [1], "impl", "ref"), content=M.content_digest(ia), delivery=M.delivery_digest(ia))
        pb = dict(class_key=kb, result_key=M.result_key(1, ib, [1], "impl", "ref"), content=M.content_digest(ib), delivery=M.delivery_digest(ib))
        expect("evidence.order-only.reuse-class", M.may_reuse(pa, pb, "class") is True, "the class may be reused across a reordering")
        expect("evidence.order-only.no-reuse-code-path", M.may_reuse(pa, pb, "code_path") is False, "the code and path must not be reused across a reordering")
        expect("digest.class-equal-code-differs", ra[0] == rb[0] == "refuse" and ra[1] != rb[1], "the two orders must give the same class and a different code: %s %s" % (ra, rb))
    except KeyError as ex:
        expect("digest.cases-present", False, "missing case %s" % ex)
    # ---- the evidence identifier: a changed pin with unchanged contracts must never make an earlier result reusable (the FALSE_REUSE of the review)
    items = [(("a", "contract", 0), "^a$")]
    ctx = (1, items)
    variants = [("[1]", [1]), ("[2]", [2]), ("[]", []), ("[1,2]", [1, 2]), ("[true]", [True]), ("[1.0]", [1.0])]
    recs = {}
    for name, d in variants:
        recs[name] = dict(class_key=M.class_key(1, items, d, "impl", "ref"), result_key=M.result_key(1, items, d, "impl", "ref"), content=M.content_digest(items), delivery=M.delivery_digest(items),
                          verdict=M.validate_delivered(d, items))
    expect("evidence.pin-bound.class-keys-distinct", len({r["class_key"] for r in recs.values()}) == len(recs), "two pin variants with different verdicts share a class key")
    expect("evidence.pin-bound.result-keys-distinct", len({r["result_key"] for r in recs.values()}) == len(recs), "two pin variants share a result key")
    for name in recs:
        if name != "[1]":
            for what in ("class", "code_path", "result"):
                expect("evidence.pin-change-no-reuse.%s.%s" % (name, what), M.may_reuse(recs["[1]"], recs[name], what) is False,
                       "an earlier result (pin [1], %s) must not be reusable for %s with pin %s (%s)" % (recs["[1]"]["verdict"][0], what, name, recs[name]["verdict"]))
    same = dict(class_key=M.class_key(1, items, [1, 1], "impl", "ref"), result_key=M.result_key(1, items, [1, 1], "impl", "ref"), content=M.content_digest(items), delivery=M.delivery_digest(items))
    expect("evidence.pin-set.identical-declarations", M.may_reuse(recs["[1]"], same, "class") is True and M.may_reuse(recs["[1]"], same, "code_path") is False,
           "identical declarations are one declaration for the class (same set) but another delivery for the code and path")
    base = (M.class_key(1, items, [1], "impl", "ref"), M.result_key(1, items, [1], "impl", "ref"))
    for label, other in (("profile-version", (M.class_key(2, items, [1], "impl", "ref"), M.result_key(2, items, [1], "impl", "ref"))),
                         ("implementation", (M.class_key(1, items, [1], "impl2", "ref"), M.result_key(1, items, [1], "impl2", "ref"))),
                         ("conformance-reference", (M.class_key(1, items, [1], "impl", "ref2"), M.result_key(1, items, [1], "impl", "ref2")))):
        expect("evidence.context-bound.%s" % label, other[0] != base[0] and other[1] != base[1], "a changed %s must change both keys" % label)
    # domain separation (review F6): every component digest and every identifier has its own tag, the tags are the ones the specification lists, and no two digests coincide on the empty input
    empty = [M.content_digest([]), M.delivery_digest([]), M.pin_ordered_digest([]), M.pin_set_digest([])]
    expect("evidence.domain-separation.components-distinct", len(set(empty)) == 4, "two component digests coincide on the empty input: they share a domain tag or have none")
    one = [(("a", "contract", 0), "^a$")]
    expect("evidence.domain-separation.content-vs-delivery", M.content_digest(one) != M.delivery_digest(one), "the content and the delivery digest of the same single contract coincide")
    expect("evidence.domain-separation.keys-distinct", M.class_key(1, one, [1], "i", "r") != M.result_key(1, one, [1], "i", "r"), "the class key and the result key coincide")
    for t in M.ALL_TAGS:
        expect("spec.tag.%s" % t.decode("ascii"), t.decode("ascii") in spec, "the specification does not list this domain tag")
    expect("evidence.domain-separation.tags-distinct", len(set(M.ALL_TAGS)) == len(M.ALL_TAGS), "two domain tags are equal")
    # the scope of the keys (review F5): only the schema pattern validation after a SUCCESSFUL document read gets a key; a reader error gets none
    for c in cases["cases"]:
        if c["id"].startswith("E-RDR") or (c["expect"]["outcome"] == "reader_error" and c.get("pin_text") is None):
            ev = M.evidence_for_schema(c["schema"], c.get("pin") or [1], 1, "impl", "ref")
            expect("evidence.scope.reader-error-no-key.%s" % c["id"], ev is None, "a document the reader refused must get no evidence key")
    ev_ok = M.evidence_for_schema("a: {contract: [{type: pattern, expression: '^a$'}]}", [1], 1, "impl", "ref")
    expect("evidence.scope.successful-read-gets-keys", ev_ok is not None and ev_ok["verdict"] == ("accept",) and ev_ok["class_key"] != ev_ok["result_key"], "a successfully read schema must get both keys and its verdict")
    # the typed canonical encoding is equal iff the values are identical
    import random
    rnd = random.Random(20261123)
    sample = []
    for c in cases["cases"]:
        try:
            sample += list(M.read_pin(c["pin_text"])) if c.get("pin_text") is not None else list(c.get("pin") or [])
        except M.ReaderError:
            pass
    def gen(d):
        k = rnd.choice(["null", "bool", "int", "float", "str", "list", "map"] if d > 0 else ["null", "bool", "int", "float", "str"])
        if k == "null": return None
        if k == "bool": return rnd.choice([True, False])
        if k == "int": return rnd.choice([0, 1, -1, 2, 99])
        if k == "float": return rnd.choice([0.0, -0.0, 1.0, float("nan"), 2.5])
        if k == "str": return rnd.choice(["", "1", "a", "x"])
        if k == "list": return [gen(d - 1) for _ in range(rnd.randrange(0, 3))]
        keys = []
        pairs = []
        for _ in range(rnd.randrange(0, 3)):
            kk = gen(0)
            if not any(M.identical(kk, k2) for k2 in keys):
                keys.append(kk); pairs.append((kk, gen(d - 1)))
        rnd.shuffle(pairs)
        return M.TMap(pairs)
    sample += [gen(3) for _ in range(120)]
    bad = 0; npairs = 0
    for i in range(len(sample)):
        for j in range(i, len(sample)):
            npairs += 1
            if M.identical(sample[i], sample[j]) != (M.enc(sample[i]) == M.enc(sample[j])):
                bad += 1
    expect("evidence.encoding.injective-on-identity", bad == 0, "%d of %d pairs: the encoding and the identity rule disagree" % (bad, npairs))
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
