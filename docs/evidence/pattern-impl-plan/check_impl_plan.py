"""Consistency check of the implementation plan. An ISOLATED check, not a CI gate; it changes nothing and implements nothing.
Checks (a failure is a FAIL-EXPECT line, exit 1; an unreadable input is INCOMPLETE, exit 2, never a result):
  approved    the approved vector file is byte-for-byte the approved one (SHA-256 held here); the plan's counts (513 approved, 47 proposed, 560 in total) equal the files
  assignment  every one of the 27 obligations is assigned to at least one unit; every unit names known obligations and has tests
  coverage    for every requirement of the obligations of a unit, the unit's tests actually cover it: an approved vector kind that has a vector naming it, an extension group whose cases name it, or a plan item that lists it
  order       every unit belongs to exactly one milestone that lists it; a unit that comes `after` another is in the same or a later milestone; the milestones follow the seven steps in order; the milestones of the
              implementation (M3 on) come after the milestones of the owner's decisions (M0, M1), whose gate G-0 names D1 to D6; the implementation, the independent one, the integration and the gate are on hold
  dag         the dependencies between units form a DAG: no unit depends on itself, no cycle (also inside one milestone), and a topological order can be produced (review F2 of #54)
  harness     a gate that is executed by a tool or by units lists them in requires_units, and each of those units is in the same or an EARLIER milestone than the gate (the harness that executes a gate is built
              no later than the gate that needs it; review F1 of #54)
  prerequisite an open point that blocks a unit is a recorded need of that unit, is closed by a gate whose criteria name it, and that gate comes in an EARLIER milestone than the unit (review F3 of #54)
  levels      three levels of coverage are kept apart: planned, baseline (what the approved vectors and the plan items that do NOT depend on the extension cover), executed (none: nothing exists). A (unit,
              requirement) pair covered only through the extension needs a fallback test independent of it (review F4 of #54); a claim of execution needs an evidence reference
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
    ext_plans = {p["id"] for p in obl["plan"] if p.get("status") == "proposed-extension"}      # the plan items that rest on the extension cases
    units = {u["id"]: u for u in plan["units"]}; ms = {m["id"]: m for m in plan["milestones"]}; gates = {g["id"]: g for g in plan["gates"]}
    ops = {o["id"]: o for o in plan.get("open_points", [])}
    mindex = {m["id"]: i for i, m in enumerate(plan["milestones"])}
    for name, items in (("unit", plan["units"]), ("milestone", plan["milestones"]), ("gate", plan["gates"])):
        ids = [x["id"] for x in items]
        for i, n in collections.Counter(ids).items():
            expect("%s.id.unique.%s" % (name, i), n == 1)
    assigned = collections.defaultdict(list); pairs = []
    for u in plan["units"]:
        i = u["id"]
        expect("unit.text.%s" % i, bool(str(u.get("text", "")).strip()) and bool(u.get("module")))
        expect("unit.obligations.%s" % i, bool(u.get("obligations")))
        expect("unit.needs.%s" % i, set(u.get("needs", [])) <= DECISIONS | set(ops), "needs outside D1..D6 and the open points: %s" % sorted(set(u.get("needs", [])) - DECISIONS - set(ops)))
        for o in u.get("obligations", []):
            expect("unit.obligation.known.%s.%s" % (i, o), o in obs, "unknown obligation")
            assigned[o].append(i)
        tests = u.get("tests") or []
        expect("unit.tests.%s" % i, bool(tests), "a unit without tests")
        covered = set(); base_covered = set()
        for t in tests:
            kind, _, name = t.partition(":")
            if kind == "approved":
                expect("unit.test.known.%s.%s" % (i, t), name in kind_reqs, "unknown approved vector kind")
                covered |= kind_reqs.get(name, set()); base_covered |= kind_reqs.get(name, set())
            elif kind == "extension":
                expect("unit.test.known.%s.%s" % (i, t), name in grp_reqs, "unknown extension group")
                covered |= grp_reqs.get(name, set())                  # planned only: the extension is not baseline
            elif kind == "plan":
                expect("unit.test.known.%s.%s" % (i, t), name in plan_reqs, "unknown plan item")
                covered |= plan_reqs.get(name, set())
                if name not in ext_plans:
                    base_covered |= plan_reqs.get(name, set())
            else:
                expect("unit.test.known.%s.%s" % (i, t), False, "a test is approved:KIND, extension:GROUP or plan:P-NN")
        for o in u.get("obligations", []):
            for r in (obs.get(o) or {}).get("reqs", []):
                expect("unit.covers.%s.%s.%s" % (i, o, r), r in covered, "the tests of the unit do not cover this requirement of %s" % o)
                pairs.append((i, r, r in covered, r in base_covered))
        m = u.get("milestone")
        expect("unit.milestone.%s" % i, m in ms and i in ms[m].get("units", []), "the unit is not listed by its milestone %r" % m)
        for a in u.get("after", []):
            expect("unit.after.%s.%s" % (i, a), a in units and units[a].get("milestone") in mindex and m in mindex and mindex[units[a]["milestone"]] <= mindex[m], "a unit that comes after %s must be in the same or a later milestone" % a)
    for o in obs:
        expect("assignment.obligation.%s" % o, o in assigned, "no unit implements this obligation")
    # ---- the dependency graph (review F2)
    edges = {i: [a for a in u.get("after", []) if a in units] for i, u in units.items()}
    for i, deps in edges.items():
        expect("dag.self.%s" % i, i not in deps, "a unit depends on itself")
    indeg = {i: 0 for i in units}
    for i, deps in edges.items():
        for a in deps:
            if a != i:
                indeg[i] += 1
    ready = sorted(i for i, n in indeg.items() if n == 0); order = []
    rev = collections.defaultdict(list)
    for i, deps in edges.items():
        for a in deps:
            if a != i:
                rev[a].append(i)
    while ready:
        x = ready.pop(0); order.append(x)
        for y in sorted(rev[x]):
            indeg[y] -= 1
            if indeg[y] == 0:
                ready.append(y)
    expect("dag.cycle", len(order) == len(units), "the dependencies contain a cycle through %s" % sorted(set(units) - set(order)))
    # ---- the harness and the units a gate needs (review F1)
    gate_ms = {}
    for m in plan["milestones"]:
        for g in m.get("gates", []):
            gate_ms.setdefault(g, mindex[m["id"]])
    for g in plan["gates"]:
        for u in g.get("requires_units", []):
            expect("gate.requires.known.%s.%s" % (g["id"], u), u in units, "unknown unit")
            if u in units and g["id"] in gate_ms and units[u].get("milestone") in mindex:
                expect("gate.requires.%s.%s" % (g["id"], u), mindex[units[u]["milestone"]] <= gate_ms[g["id"]], "the unit that executes or enables this gate is built in a LATER milestone than the gate")
    # ---- the open points that block units (review F3)
    for o in plan.get("open_points", []):
        for u in o.get("blocks", []):
            expect("op.blocks.known.%s.%s" % (o["id"], u), u in units, "unknown unit")
            expect("op.blocks.%s.%s" % (u, o["id"]), u in units and o["id"] in units[u].get("needs", []), "the open point blocks this unit but is not among its needs")
        g = o.get("closed_by")
        expect("op.closed-by.%s" % o["id"], g in gates and o["id"] in str(gates[g].get("criteria", "")), "the open point must be closed by a gate whose criteria name it")
        for u in o.get("blocks", []):
            if g in gate_ms and u in units and units[u].get("milestone") in mindex:
                expect("op.order.%s.%s" % (o["id"], u), gate_ms[g] < mindex[units[u]["milestone"]], "the gate that closes the open point comes too late for the unit")
    for i, u in units.items():
        for n in u.get("needs", []):
            if n in ops:
                expect("op.needs.%s.%s" % (i, n), i in ops[n].get("blocks", []), "the unit needs the open point but the open point does not list it as blocked")
    # ---- the three levels of coverage (review F4)
    fb = plan.get("extension_fallbacks", [])
    fb_ids = [f["id"] for f in fb]
    expect("fallback.ids.unique", len(fb_ids) == len(set(fb_ids)))
    for f in fb:
        expect("fallback.known.%s" % f["id"], f.get("unit") in units and bool(f.get("covers")) and bool(str(f.get("method", "")).strip()) and bool(str(f.get("status", "")).strip()), "a fallback names a known unit, the requirements, a method and a status")
        for r in f.get("covers", []):
            expect("fallback.reqs.known.%s.%s" % (f["id"], r), r in (set(q["id"] for q in vec["requirements"]) | set(q["id"] for q in vec["not_testable_by_vectors"])))
    n_planned = sum(1 for p in pairs if p[2]); n_base = sum(1 for p in pairs if p[3]); only_ext = [(u, r) for u, r, pl, ba in pairs if pl and not ba]
    for u, r in sorted(set(only_ext)):
        expect("fallback.needed.%s.%s" % (u, r), any(f.get("unit") == u and r in f.get("covers", []) for f in fb), "this (unit, requirement) pair is covered only through the extension: a fallback test independent of it is required")
    ex = plan.get("execution") or {}
    expect("execution.claim", ex.get("state") == "not_started" or bool(ex.get("evidence")), "a claim of execution needs an evidence reference; no implementation exists")
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
    print("coverage levels over %d (unit, requirement) pairs: planned %d, baseline (without the extension) %d, covered only through the extension %d pairs (each with a fallback), executed %s" % (len(pairs), n_planned, n_base, len(set(only_ext)), "none (state %s)" % ex.get("state")))
    print("topological order of the units: %s" % " ".join(order))
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
