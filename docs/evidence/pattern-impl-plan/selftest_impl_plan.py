"""Self-test of check_impl_plan.py: can it FAIL, and for the right reason? Typed exits; infrastructure is never a detection.
A: an unmodified positive control (exit 0); planted faults in COPIES of the plan, the document and the approved vector file, each counted only when the check exits 1 AND prints a FAIL-EXPECT line of the
   intended check;  C: an unreadable plan exits 2 and is not a detection.
Exit: 0 all as expected, 1 a mutant was not detected or a control failed, 2 the self-test itself could not run."""
import os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "..", "design")
PLAN = os.path.join(D, "pattern-profile-plan", "plan.yaml")
VEC = os.path.join(D, "pattern-profile-vectors", "pattern-profile.yaml")
DOC = os.path.join(HERE, "..", "..", "en", "GRAMMAR-PATTERN-IMPLEMENTATION-PLAN.md")
CHECK = os.path.join(HERE, "check_impl_plan.py")
bad = 0


def run(args):
    r = subprocess.run([sys.executable, CHECK] + args, capture_output=True, text=True, timeout=600)
    return r.returncode, r.stdout + r.stderr


def report(label, ok, extra=""):
    global bad
    print("%-100s %s %s" % (label, "OK" if ok else "FAIL", extra))
    bad += not ok


def sub(text, a, b):
    assert text.count(a) == 1, (text.count(a), a)
    return text.replace(a, b)


def main():
    plan, doc = (open(p, encoding="utf-8").read() for p in (PLAN, DOC))
    vec = open(VEC, "rb").read()
    rc, o = run([])
    report("A positive control (the plan as it is)", rc == 0 and "all expectations held" in o, "exit=%d" % rc)
    faults = [
        ("an obligation no unit implements (O-VA-13 removed from U-05)", dict(plan=sub(plan, "obligations: [O-VA-11, O-VA-12, O-VA-13]", "obligations: [O-VA-11, O-VA-12]")), "assignment.obligation.O-VA-13"),
        ("a unit without tests (U-04)", dict(plan=sub(plan, 'tests: ["approved:expressions"], needs: [], text: "tier 1', 'tests: [], needs: [], text: "tier 1')), "unit.tests.U-04"),
        ("a test that names no kind (U-04)", dict(plan=sub(plan, 'tests: ["approved:expressions"]', 'tests: ["approved:expressionz"]')), "unit.test.known.U-04.approved:expressionz"),
        ("the tests of a unit no longer cover a requirement (U-09 without plan P-04: R-VERIFIER-BUDGET)", dict(plan=sub(plan, 'tests: ["plan:P-02", "plan:P-07", "plan:P-04"]', 'tests: ["plan:P-02", "plan:P-07"]')), "unit.covers.U-09.O-VF-03.R-VERIFIER-BUDGET"),
        ("the tests of a unit no longer cover a requirement (U-05 without plan P-01: R-LINEAR)", dict(plan=sub(plan, 'tests: ["approved:values", "plan:P-01", "plan:P-05"]', 'tests: ["approved:values", "plan:P-05"]')), "unit.covers.U-05.O-VA-13.R-LINEAR"),
        ("a unit that comes after a unit of a later milestone (U-05 after U-08)", dict(plan=sub(plan, "after: [U-04, U-02], tests", "after: [U-04, U-02, U-08], tests")), "unit.after.U-05.U-08"),
        ("the milestones no longer follow the steps in order (M3 is step 9)", dict(plan=sub(plan, "step: 4, units: [U-01", "step: 9, units: [U-01")), "order.steps"),
        ("the owner's decisions no longer come before the implementation (G-0 removed from M0 and M1)", dict(plan=sub(sub(plan, "gates: [G-0], hold: false, text: \"the owner confirms", "gates: [], hold: false, text: \"the owner confirms"), "gates: [G-0], hold: false, text: \"the review package", "gates: [], hold: false, text: \"the review package")), "order.decisions-before-implementation"),
        ("the primary implementation is no longer on hold (M3)", dict(plan=sub(plan, "G-8, G-10], hold: true", "G-8, G-10], hold: false")), "hold.milestone.M3"),
        ("a plan item in no gate (P-01 removed from G-6)", dict(plan=sub(plan, "approval: review, typed_exits: true, plan_items: [P-01], hold: false}", "approval: review, typed_exits: true, plan_items: [], hold: false}")), "gate.plan-item-placed.P-01"),
        ("a gate without evidence (G-2)", dict(plan=sub(plan, 'evidence: "a conformance run with typed exits (0 ok, 1 a DISAGREE line, 2 infrastructure, 3 a failed canary of a native runner)"', 'evidence: ""')), "gate.fields.G-2"),
        ("a gate no milestone uses (G-9 removed from M5)", dict(plan=sub(plan, "gates: [G-7, G-9]", "gates: [G-7]")), "gate.used.G-9"),
        ("the counts of the plan no longer equal the files (512 approved)", dict(plan=sub(plan, "approved: 513", "approved: 512")), "counts.approved"),
        ("the Forms integration no longer listed as out of scope", dict(plan=sub(plan, '- "the integration of the Forms (a separate work package)"\n', "")), "scope.out-of-scope"),
        ("review F1 of #54: the standalone harness is built in a later milestone than the gates it executes (U-10a in M6)", dict(plan=sub(plan, 'module: "tests/pattern_profile/harness", milestone: M3', 'module: "tests/pattern_profile/harness", milestone: M6')), "gate.requires.G-2.U-10a"),
        ("review F2 of #54: a unit depends on itself (U-01 after U-01)", dict(plan=sub(plan, "module: reader.py, milestone: M3, after: []", "module: reader.py, milestone: M3, after: [U-01]")), "dag.self.U-01"),
        ("review F2 of #54: a cycle of two units in one milestone (U-01 after U-03, U-03 after U-01)", dict(plan=sub(plan, "module: reader.py, milestone: M3, after: []", "module: reader.py, milestone: M3, after: [U-03]")), "dag.cycle"),
        ("review F2 of #54: a cycle through three units (U-01 after U-06, U-06 after U-03, U-03 after U-01)", dict(plan=sub(sub(plan, "module: reader.py, milestone: M3, after: []", "module: reader.py, milestone: M3, after: [U-06]"), "module: validator.py, milestone: M3, after: [U-01, U-03, U-04]", "module: validator.py, milestone: M3, after: [U-03]")), "dag.cycle"),
        ("review F3 of #54: the reader no longer needs OP-1 although OP-1 blocks it", dict(plan=sub(plan, "needs: [D1, D4, D5, D6, OP-1], text: \"source-order mappings", "needs: [D1, D4, D5, D6], text: \"source-order mappings")), "op.blocks.U-01.OP-1"),
        ("review F3 of #54: the gate G-0 no longer names OP-1", dict(plan=sub(plan, "OP-1 (the YAML scalar schema, explicit tags, duplicate keys and aliases of the reader) closed by a recorded specification decision", "the open point of the YAML scalar schema closed by a recorded specification decision")), "op.closed-by.OP-1"),
        ("review F4 of #54: a pair covered only through the extension without a fallback (F-01 removed)", dict(plan="\n".join(l for l in plan.split("\n") if not l.startswith("- {id: F-01,"))), "fallback.needed.U-01.R-PIN-MISSING"),
        ("review F4 of #54: a fallback that names an unknown unit", dict(plan=sub(plan, "- {id: F-02, unit: U-01,", "- {id: F-02, unit: U-99,")), "fallback.known.F-02"),
        ("review F4 of #54: a claim of execution without an evidence reference", dict(plan=sub(plan, "state: not_started", "state: executed")), "execution.claim"),
        ("the plan document no longer mentions a unit (U-06)", dict(doc=doc.replace("U-06", "U-0x")), "text.mentions.U-06"),
        ("the approved vector file modified by one appended comment line", dict(vec=vec + b"# x\n"), "approved.unchanged"),
    ]
    for name, files, needle in faults:
        d = tempfile.mkdtemp()
        try:
            args = []
            for key, flag in (("plan", "--plan"), ("doc", "--doc"), ("vec", "--vectors")):
                if key in files:
                    f = os.path.join(d, key + ".dat"); data = files[key]
                    open(f, "wb").write(data if isinstance(data, bytes) else data.encode("utf-8")); args += [flag, f]
            rc, o = run(args)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        named = [l for l in o.splitlines() if l.startswith("FAIL-EXPECT") and needle in l]
        report("A planted: " + name, rc == 1 and bool(named), "exit=%d needle=%s" % (rc, needle))
    # OP-1: the reference resolver of the YAML 1.2 core schema agrees with the hand-written table and PyYAML measurably differs; a planted defect of the resolver is caught, the missing dependency exits 2
    def probe(env_extra=None):
        env = dict(os.environ); env.pop("CIC_OP1_PLANT", None); env.pop("CIC_OP1_NO_YAML", None); env.update(env_extra or {})
        r = subprocess.run([sys.executable, os.path.join(HERE, "op1_probe.py")], capture_output=True, text=True, env=env, timeout=300)
        return r.returncode, r.stdout + r.stderr
    rc, o = probe()
    report("O OP-1 probe positive control (the reference resolver agrees with the table; PyYAML differs)", rc == 0 and "PyYAML differs from the core schema on" in o, "exit=%d" % rc)
    for plant, needle in (("octal-int", "FAIL-EXPECT core.'010'"), ("bool-yaml11", "FAIL-EXPECT core.'on'"), ("underscore-int", "FAIL-EXPECT core.'1_000'")):
        rc, o = probe({"CIC_OP1_PLANT": plant})
        report("O planted: the reference resolver is wrong (%s)" % plant, rc == 1 and needle in o, "exit=%d" % rc)
    rc, o = probe({"CIC_OP1_NO_YAML": "1"})
    report("O infra: PyYAML is missing (exit 2, not a detection)", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)
    rc, o = run(["--plan", "/nonexistent/plan.yaml"])
    report("C infra: the plan is unreadable (exit 2, not a detection)", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)
    print("self-test: %s" % ("all as expected" if not bad else "%d problem(s)" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
