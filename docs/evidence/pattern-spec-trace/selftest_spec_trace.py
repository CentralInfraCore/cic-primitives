"""Self-test of check_spec_trace.py: can it FAIL, and for the right reason? Typed exits; infrastructure is never a detection.
A: an unmodified positive control (exit 0); planted faults in COPIES of the obligations, the specification text, the extension cases and the vector file, each counted only when the check exits 1 AND prints
   a FAIL-EXPECT line of the intended check;
B: planted defects of the executable reading (spec_model.py, CIC_SPECMODEL_PLANT): the version compared by Python equality (true and 1.0 pass), the own contract visited after the children, identity by a serialisation, a verdict that depends on the delivery order, an order-erasing digest, an evidence key that omits the pin declarations (the FALSE_REUSE), a reuse decided by a component digest alone, a reader that merges the keys 1, true and 1.0;
C: infrastructure controls: an unreadable obligations file exits 2 and is not a detection.
Exit: 0 all as expected, 1 a mutant was not detected or a control failed, 2 the self-test itself could not run."""
import os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "..", "design")
OBL, CASES = os.path.join(D, "pattern-profile-spec", "obligations.yaml"), os.path.join(D, "pattern-profile-spec", "extension-cases.yaml")
VEC = os.path.join(D, "pattern-profile-vectors", "pattern-profile.yaml")
SPEC = os.path.join(HERE, "..", "..", "en", "GRAMMAR-PATTERN-IMPLEMENTATION-SPEC.md")
CHECK = os.path.join(HERE, "check_spec_trace.py")
bad = 0


def run(args, env_extra=None):
    env = dict(os.environ); env.pop("CIC_SPECMODEL_PLANT", None); env.update(env_extra or {})
    r = subprocess.run([sys.executable, CHECK] + args, capture_output=True, text=True, env=env, timeout=600)
    return r.returncode, r.stdout + r.stderr


def report(label, ok, extra=""):
    global bad
    print("%-92s %s %s" % (label, "OK" if ok else "FAIL", extra))
    bad += not ok


def sub(text, a, b, count=1):
    assert a in text, a
    return text.replace(a, b, count)


def main():
    obl, cases, spec = (open(p, encoding="utf-8").read() for p in (OBL, CASES, SPEC))
    vec = open(VEC, "rb").read()
    rc, o = run([])
    report("A positive control (the package as it is)", rc == 0 and "all expectations held" in o, "exit=%d" % rc)
    faults = [
        ("a requirement no obligation names (R-LINEAR)", dict(obl=sub(sub(obl, "text: \"the evaluator is linear", "text: \"the evaluator is linear"), "reqs: [R-LINEAR], verify: {plan: [P-01]}", "reqs: [R-INDEPENDENT-CHECK], verify: {plan: [P-01]}").replace("reqs: [R-VERSION-EVIDENCE, R-LINEAR]", "reqs: [R-VERSION-EVIDENCE]")), "coverage.requirement.R-LINEAR"),
        ("an obligation that names an unknown requirement", dict(obl=sub(obl, "R-MATCH-FULL,", "R-NOPE,")), "obligation.reqs.known.O-VA-11.R-NOPE"),
        ("an obligation without any verification", dict(obl=sub(obl, "reqs: [R-COMPAT-CONTRACTS], verify: {vectors: true}", "reqs: [R-COMPAT-CONTRACTS], verify: {}")), "obligation.verify.O-VA-10"),
        ("a plan item that no obligation uses", dict(obl=sub(obl, "verify: {plan: [P-08, P-09]}", "verify: {plan: [P-08]}")), "plan.referenced.P-09"),
        ("the specification text without a mention of an obligation (O-VA-07)", dict(spec=spec.replace("O-VA-07", "O-VA-0x")), "spec.mentions.O-VA-07"),
        ("an obligation for a requirement no vector can test, without a plan item", dict(obl=sub(obl, "reqs: [R-LINEAR], verify: {plan: [P-01]}", "reqs: [R-LINEAR], verify: {vectors: true}")), "obligation.nt-needs-plan.O-VA-13"),
        ("a role without an obligation (gate)", dict(obl=sub(obl, "roles: [gate]", "roles: [verifier]").replace("roles: [producer, verifier, gate]", "roles: [producer, verifier]")), "roles.coverage.gate"),
        ("a duplicate obligation id", dict(obl=sub(obl, "id: O-VA-10,", "id: O-VA-09,")), "obligation.id.unique.O-VA-09"),
        ("an extension case whose expectation no longer follows the rules", dict(cases=sub(cases, "pin: [true], schema: \"a: {contract: [{type: pattern, expression: '^a$'}]}\", expect: {outcome: refuse, code: pattern_profile_unknown", "pin: [true], schema: \"a: {contract: [{type: pattern, expression: '^a$'}]}\", expect: {outcome: refuse, code: pattern_profile_conflict")), "extension.model.E-PIN-01"),
        ("an extension case of a group with no plan item", dict(cases=cases + "- {id: E-ZZ-01, req: [R-PIN-MISSING], pin: [], schema: \"a: {type: string}\", expect: {outcome: accept}}\n"), "extension.group.E-ZZ-01"),
        ("the approved vector file modified by one appended comment line (the 513 vectors are a reference)", dict(vec=vec + b"# x\n"), "approved.unchanged"),
        ("review F4: a plan item that does not list the requirement the obligation relies on it for (R-PIN-IDENTICAL)", dict(obl=sub(obl, "reqs: [R-PIN-MISSING, R-PIN-UNKNOWN, R-PIN-CONFLICT, R-PIN-IDENTICAL, R-PIN-FIRST, R-PIN-ONLY-IF-PATTERN], method: \"extension cases for the pin", "reqs: [R-PIN-MISSING, R-PIN-UNKNOWN, R-PIN-CONFLICT, R-PIN-FIRST, R-PIN-ONLY-IF-PATTERN], method: \"extension cases for the pin")), "obligation.covers.O-RD-04.R-PIN-IDENTICAL"),
        ("review F4: the machine-readable text of O-VF-01 names fewer steps than the specification (steps 1 to 3)", dict(obl=sub(obl, "repeat steps 0 to 3 of the validation order INDEPENDENTLY", "repeat steps 1 to 3 of the validation order INDEPENDENTLY")), "consistency.text.O-VF-01"),
        ("review F4: the specification no longer says steps 0 to 3", dict(spec=spec.replace("steps 0 to 3", "steps 1 to 3")), "consistency.spec.O-VF-01"),
    ]
    for name, files, needle in faults:
        d = tempfile.mkdtemp()
        try:
            args = []
            for key, flag, content, path in (("obl", "--obligations", obl, OBL), ("spec", "--spec", spec, SPEC), ("cases", "--cases", cases, CASES), ("vec", "--vectors", vec, VEC)):
                if key in files:
                    f = os.path.join(d, key + ".dat"); data = files[key]
                    open(f, "wb").write(data if isinstance(data, bytes) else data.encode("utf-8")); args += [flag, f]
            rc, o = run(args)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        named = [l for l in o.splitlines() if l.startswith("FAIL-EXPECT") and needle in l]
        report("A planted: " + name, rc == 1 and bool(named), "exit=%d needle=%s" % (rc, needle))
    for plant, needle in (("equality-version", "extension.model.E-PIN-01"), ("contract-last", "extension.model.E-TRV-01"),
                          ("json-identity", "extension.model.E-PIN-18"), ("json-identity", "model_raised"),
                          ("stop-at-first-accept", "property.class-order-independent.S-010"), ("digest-sorted", "digest.order-sensitive"),
                          ("key-without-pin", "evidence.pin-bound.class-keys-distinct"), ("key-without-pin", "evidence.pin-change-no-reuse"),
                          ("reuse-by-partial", "evidence.pin-change-no-reuse"), ("python-keys", "extension.model.E-PIN-28"), ("python-keys", "extension.model.E-PIN-32")):
        rc, o = run([], {"CIC_SPECMODEL_PLANT": plant})
        named = [l for l in o.splitlines() if l.startswith("FAIL-EXPECT") and needle in l]
        report("B planted model defect: " + plant, rc == 1 and bool(named), "exit=%d needle=%s" % (rc, needle))
    # review F3: the work bound. The provisional constant holds; a planted quadratic evaluator, a too small constant and a corpus without a zero-size program or an empty value are each rejected
    def wb(args, env_extra=None):
        env = dict(os.environ); env.pop("CIC_WORK_PLANT", None); env.update(env_extra or {})
        r = subprocess.run([sys.executable, os.path.join(HERE, "work_bound.py")] + args, capture_output=True, text=True, env=env, timeout=600)
        return r.returncode, r.stdout + r.stderr
    rc, o = wb([])
    report("F positive control of the work bound (c x (PI+1) x (N+1), the first form refuted)", rc == 0 and "refuted for every c" in o, "exit=%d" % rc)
    rc, o = wb([], {"CIC_WORK_PLANT": "inflate"})
    report("F planted: a quadratic evaluator (work multiplied by N + 1) violates the bound", rc == 1 and "FAIL-EXPECT bound." in o, "exit=%d" % rc)
    rc, o = wb(["--c", "0.5"])
    report("F planted: a constant that is too small is rejected", rc == 1 and "FAIL-EXPECT bound." in o, "exit=%d" % rc)
    rc, o = wb([], {"CIC_WORK_PLANT": "no-zero-cases"})
    report("F planted: a corpus without a zero-size program and without the empty value cannot refute the first form", rc == 1 and "FAIL-EXPECT old-bound.refuted" in o, "exit=%d" % rc)
    rc, o = run(["--obligations", "/nonexistent/obligations.yaml"])
    report("C infra: the obligations file is unreadable (exit 2, not a detection)", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)
    print("self-test: %s" % ("all as expected" if not bad else "%d problem(s)" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
