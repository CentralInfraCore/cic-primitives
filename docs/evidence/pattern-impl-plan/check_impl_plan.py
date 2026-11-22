"""Consistency check of the implementation plan. An ISOLATED check, not a CI gate; it changes nothing and implements nothing.
Checks (a failure is a FAIL-EXPECT line, exit 1; an unreadable input is INCOMPLETE, exit 2, never a result):
  approved    the approved vector file is byte-for-byte the approved one (SHA-256 held here); the plan's counts (513 approved, 47 proposed, 560 in total) equal the files
  assignment  every one of the 27 obligations is assigned to at least one unit; every unit names known obligations and has tests
  coverage    for every requirement of the obligations of a unit, the unit's tests actually cover it: an approved vector kind that has a vector naming it, an extension group whose cases name it, or a plan item that lists it
  order       every unit belongs to exactly one milestone that lists it; a unit that comes `after` another is in the same or a later milestone; the milestones follow the seven steps in order; the milestones of the
              implementation (M3 on) come after the milestones of the owner's decisions (M0, M1), whose gate G-0 names D1 to D6; the implementation, the independent one, the integration and the gate are on hold
  gates       every gate has criteria, evidence and an approval of owner or review; a gate that claims typed exits says so; every plan item P-01 to P-11 is in at least one gate; every milestone gate exists and every gate is used
  text        the plan document mentions every unit, gate, milestone and open point
Usage: check_impl_plan.py [--plan PATH] [--obligations PATH] [--vectors PATH] [--cases PATH] [--doc PATH]"""
import hashlib, os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGN = os.path.join(HERE, "..", "..", "design")
PLAN = os.path.join(DESIGN, "pattern-profile-plan", "plan.yaml")
OBL = os.path.join(DESIGN, "pattern-profile-spec", "obligations.yaml")
CASES = os.path.join(DESIGN, "pattern-profile-spec", "extension-cases.yaml")
VEC = os.path.join(DESIGN, "pattern-profile-vectors", "pattern-profile.yaml")
DOC = os.path.join(HERE, "..", "..", "en", "GRAMMAR-PATTERN-IMPLEMENTATION-PLAN.md")
APPROVED_SHA256 = "e7ece43a9486187c16a482a96a86d22cf82407711be940920155f4e3abe277e0"
DECISIONS = {"D1", "D2", "D3", "D4", "D5", "D6"}
fails = []


def expect(label, cond, detail=""):
    if not cond:
        fails.append(label); print("FAIL-EXPECT %s %s" % (label, detail))


def arg(argv, name, default):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else default


def main(argv):
    import yaml
    try:
        plan = yaml.safe_load(open(arg(argv, "--plan", PLAN), encoding="utf-8"))
        obl = yaml.safe_load(open(arg(argv, "--obligations", OBL), encoding="utf-8"))
        vraw = open(arg(argv, "--vectors", VEC), "rb").read(); vec = yaml.safe_load(vraw)
        cases = yaml.safe_load(open(arg(argv, "--cases", CASES), encoding="utf-8"))
        doc = open(arg(argv, "--doc", DOC), encoding="utf-8").read()
    except BaseException as e:
        print("INCOMPLETE: an input cannot be read: %r" % (e,)); return 2
    expect("approved.unchanged", hashlib.sha256(vraw).hexdigest() == APPROVED_SHA256, "the vector file is not the approved one (SHA-256 %s)" % hashlib.sha256(vraw).hexdigest())
    n_app = sum(len(vec[k]) for k in ("expressions", "values", "schemas")); n_ext = len(cases["cases"]); base = plan["conformance_base"]
    expect("counts.approved", base["approved"] == n_app, "the plan says %s approved vectors, the file has %d" % (base["approved"], n_app))
    expect("counts.extension", base["extension_proposed"] == n_ext, "the plan says %s proposed cases, the file has %d" % (base["extension_proposed"], n_ext))
    expect("counts.total", base["total_if_all_accepted"] == n_app + n_ext, "the plan says %s in total" % base["total_if_all_accepted"])
    obs = {o["id"]: o for o in obl["obligations"]}; plan_reqs = {p["id"]: set(p.get("reqs", [])) for p in obl["plan"]}
    kind_reqs = {k: set() for k in ("expressions", "values", "schemas")}
    for k in kind_reqs:
        for v in vec[k]:
            kind_reqs[k] |= set(v.get("req", []))
    grp_reqs = collections.defaultdict(set)
    for c in cases["cases"]:
        grp_reqs[c["id"].rsplit("-", 1)[0]] |= set(c.get("req", []))
    units = {u["id"]: u for u in plan["units"]}; ms = {m["id"]: m for m in plan["milestones"]}; gates = {g["id"]: g for g in plan["gates"]}
    mindex = {m["id"]: i for i, m in enumerate(plan["milestones"])}
    for name, items in (("unit", plan["units"]), ("milestone", plan["milestones"]), ("gate", plan["gates"])):
        ids = [x["id"] for x in items]
        for i, n in collections.Counter(ids).items():
            expect("%s.id.unique.%s" % (name, i), n == 1)
    assigned = collections.defaultdict(list)
    for u in plan["units"]:
        i = u["id"]
        expect("unit.text.%s" % i, bool(str(u.get("text", "")).strip()) and bool(u.get("module")))
        expect("unit.obligations.%s" % i, bool(u.get("obligations")))
        expect("unit.needs.%s" % i, set(u.get("needs", [])) <= DECISIONS, "decisions outside D1..D6: %s" % sorted(set(u.get("needs", [])) - DECISIONS))
        for o in u.get("obligations", []):
            expect("unit.obligation.known.%s.%s" % (i, o), o in obs, "unknown obligation")
            assigned[o].append(i)
        tests = u.get("tests") or []
        expect("unit.tests.%s" % i, bool(tests), "a unit without tests")
        covered = set()
        for t in tests:
            kind, _, name = t.partition(":")
            if kind == "approved":
                expect("unit.test.known.%s.%s" % (i, t), name in kind_reqs, "unknown approved vector kind")
                covered |= kind_reqs.get(name, set())
            elif kind == "extension":
                expect("unit.test.known.%s.%s" % (i, t), name in grp_reqs, "unknown extension group")
                covered |= grp_reqs.get(name, set())
            elif kind == "plan":
                expect("unit.test.known.%s.%s" % (i, t), name in plan_reqs, "unknown plan item")
                covered |= plan_reqs.get(name, set())
            else:
                expect("unit.test.known.%s.%s" % (i, t), False, "a test is approved:KIND, extension:GROUP or plan:P-NN")
        for o in u.get("obligations", []):
            for r in (obs.get(o) or {}).get("reqs", []):
                expect("unit.covers.%s.%s.%s" % (i, o, r), r in covered, "the tests of the unit do not cover this requirement of %s" % o)
        m = u.get("milestone")
        expect("unit.milestone.%s" % i, m in ms and i in ms[m].get("units", []), "the unit is not listed by its milestone %r" % m)
        for a in u.get("after", []):
            expect("unit.after.%s.%s" % (i, a), a in units and units[a].get("milestone") in mindex and m in mindex and mindex[units[a]["milestone"]] <= mindex[m], "a unit that comes after %s must be in the same or a later milestone" % a)
    for o in obs:
        expect("assignment.obligation.%s" % o, o in assigned, "no unit implements this obligation")
    for m in plan["milestones"]:
        for u in m.get("units", []):
            expect("milestone.unit.%s.%s" % (m["id"], u), u in units and units[u].get("milestone") == m["id"], "the unit is not assigned to this milestone")
        for g in m.get("gates", []):
            expect("milestone.gate.%s.%s" % (m["id"], g), g in gates, "unknown gate")
    steps = [m.get("step") for m in plan["milestones"]]
    expect("order.steps", steps == sorted(steps) and steps == list(range(1, len(steps) + 1)), "the milestones must follow the steps 1..%d in order: %s" % (len(steps), steps))
    first_impl = min(mindex[m["id"]] for m in plan["milestones"] if m.get("units"))
    g0_idx = [mindex[m["id"]] for m in plan["milestones"] if "G-0" in m.get("gates", [])]
    expect("order.decisions-before-implementation", bool(g0_idx) and max(g0_idx) < first_impl, "the gate of the owner's decisions (G-0) must come before the first milestone with units")
    expect("order.g0.names-decisions", "D1 to D6" in str(gates.get("G-0", {}).get("criteria", "")), "G-0 must name D1 to D6")
    for mid in ("M3", "M4", "M5", "M6"):
        expect("hold.milestone.%s" % mid, ms.get(mid, {}).get("hold") is True, "this milestone is on hold until the owner's GO")
    for gid in ("G-11", "G-12", "G-13"):
        expect("hold.gate.%s" % gid, gates.get(gid, {}).get("hold") is True, "this gate is on hold")
    used = {g for m in plan["milestones"] for g in m.get("gates", [])}
    in_gate = set()
    for g in plan["gates"]:
        i = g["id"]
        expect("gate.fields.%s" % i, bool(str(g.get("criteria", "")).strip()) and bool(str(g.get("evidence", "")).strip()), "criteria and evidence are required")
        expect("gate.approval.%s" % i, g.get("approval") in ("owner", "review"))
        expect("gate.typed-exits.%s" % i, isinstance(g.get("typed_exits"), bool))
        for p in g.get("plan_items", []):
            expect("gate.plan.known.%s.%s" % (i, p), p in plan_reqs)
            in_gate.add(p)
        expect("gate.used.%s" % i, i in used, "no milestone uses this gate")
    for p in plan_reqs:
        expect("gate.plan-item-placed.%s" % p, p in in_gate, "this plan item is in no gate")
    for xid in [u["id"] for u in plan["units"]] + [g["id"] for g in plan["gates"]] + [m["id"] for m in plan["milestones"]] + [o["id"] for o in plan.get("open_points", [])]:
        expect("text.mentions.%s" % xid, xid in doc, "the plan document does not mention it")
    expect("scope.out-of-scope", any("Forms" in str(x) for x in plan.get("out_of_scope", [])), "the Forms integration must be listed as a separate work package")
    print("units %d, gates %d, milestones %d; obligations %d all assigned; plan items %d all in a gate; open points %d" % (len(units), len(gates), len(ms), len(obs), len(plan_reqs), len(plan.get("open_points", []))))
    print("## obligation -> units")
    for o in obs:
        print("%-9s %s" % (o, " ".join(assigned.get(o, []))))
    print("## milestone -> units / gates")
    for m in plan["milestones"]:
        print("%-3s step %d %-6s units %-30s gates %s" % (m["id"], m["step"], "HOLD" if m.get("hold") else "", " ".join(m.get("units", [])) or "-", " ".join(m.get("gates", [])) or "-"))
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
