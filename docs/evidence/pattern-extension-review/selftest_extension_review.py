"""Self-test of check_extension_review.py: can it FAIL, and for the right reason? Typed exits; infrastructure is never a detection.
A: an unmodified positive control (exit 0); planted faults in COPIES of the review data, the cases, the document and the approved vector file, each counted only when the check exits 1 AND prints a FAIL-EXPECT
   line of the intended check;  B: a planted defect of the executable reading (the version compared by Python equality);  C: an unreadable input exits 2 and is not a detection.
Exit: 0 all as expected, 1 a mutant was not detected or a control failed, 2 the self-test itself could not run."""
import os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "..", "design")
REVIEW, CASES = os.path.join(D, "pattern-profile-spec", "extension-review.yaml"), os.path.join(D, "pattern-profile-spec", "extension-cases.yaml")
VEC = os.path.join(D, "pattern-profile-vectors", "pattern-profile.yaml")
DOC = os.path.join(HERE, "..", "..", "en", "GRAMMAR-PATTERN-EXTENSION-CASES-REVIEW.md")
CHECK = os.path.join(HERE, "check_extension_review.py")
bad = 0


def run(args, env_extra=None):
    env = dict(os.environ); env.pop("CIC_SPECMODEL_PLANT", None); env.update(env_extra or {})
    r = subprocess.run([sys.executable, CHECK] + args, capture_output=True, text=True, env=env, timeout=600)
    return r.returncode, r.stdout + r.stderr


def report(label, ok, extra=""):
    global bad
    print("%-96s %s %s" % (label, "OK" if ok else "FAIL", extra))
    bad += not ok


def sub(text, a, b):
    assert text.count(a) >= 1, a
    return text.replace(a, b, 1)


def main():
    review, cases, doc = (open(p, encoding="utf-8").read() for p in (REVIEW, CASES, DOC))
    vec = open(VEC, "rb").read()
    rc, o = run([])
    report("A positive control (the package as it is)", rc == 0 and "all expectations held" in o, "exit=%d" % rc)
    first_entry = [l for l in review.splitlines() if l.startswith("- {id: E-PIN-13,")][0]
    faults = [
        ("a case without a review entry (E-PIN-13 removed from the review data)", dict(review=review.replace(first_entry + "\n", "")), "review.ids.equal"),
        ("a decision outside D1 to D6 (D7)", dict(review=sub(review, "{id: E-TRV-01, rule: \"O-RD-03\", derive: \"in source order the node's own contract comes before its fields; the own contract (?i)a is the first refused (group extension); path n/contract/0\", depends: [D4]", "{id: E-TRV-01, rule: \"O-RD-03\", derive: \"in source order the node's own contract comes before its fields; the own contract (?i)a is the first refused (group extension); path n/contract/0\", depends: [D4, D7]")), "review.depends.known.E-TRV-01"),
        ("a dependency outside the group's set (E-TRV-01 depends on D1)", dict(review=sub(review, "path n/contract/0\", depends: [D4]", "path n/contract/0\", depends: [D4, D1]")), "review.depends.group.E-TRV-01"),
        ("a missing derivation (E-PIN-05)", dict(review=sub(review, "one declaration, the int 0; an int but not 1; unknown", "x")), "review.derive.E-PIN-05"),
        ("a rule that names an unknown obligation", dict(review=sub(review, "rule: \"O-RD-06\"", "rule: \"O-RD-99\"")), "review.rule.known.E-PIN-33.O-RD-99"),
        ("a case whose expectation no longer follows the rules (E-PIN-01 expects conflict)", dict(cases=sub(cases, "pin: [true], schema: \"a: {contract: [{type: pattern, expression: '^a$'}]}\", expect: {outcome: refuse, code: pattern_profile_unknown", "pin: [true], schema: \"a: {contract: [{type: pattern, expression: '^a$'}]}\", expect: {outcome: refuse, code: pattern_profile_conflict")), "model.E-PIN-01"),
        ("a requirement that does not exist in the approved set", dict(cases=sub(cases, "req: [R-PIN-UNKNOWN], pin: [true]", "req: [R-NOPE], pin: [true]")), "case.reqs.known.E-PIN-01.R-NOPE"),
        ("the case table of the document edited by hand", dict(doc=sub(doc, "refuse `pattern_profile_unknown` | one declaration, the value true;", "refuse `pattern_profile_missing` | one declaration, the value true;")), "doc.table.in-sync"),
        ("the decision table of the document no longer matches the data (D4 needs 6)", dict(doc=sub(doc, "| D4 | 7 ", "| D4 | 6 ")), "doc.counts.D4"),
        ("the group table of the document no longer matches the data (E-TRV 8)", dict(doc=sub(doc, "| `E-TRV` | 7 |", "| `E-TRV` | 8 |")), "doc.group.E-TRV"),
        ("the approved vector file modified by one appended comment line", dict(vec=vec + b"# x\n"), "approved.unchanged"),
    ]
    for name, files, needle in faults:
        d = tempfile.mkdtemp()
        try:
            args = []
            for key, flag, content in (("review", "--review", review), ("cases", "--cases", cases), ("doc", "--doc", doc), ("vec", "--vectors", vec)):
                if key in files:
                    f = os.path.join(d, key + ".dat"); data = files[key]
                    open(f, "wb").write(data if isinstance(data, bytes) else data.encode("utf-8")); args += [flag, f]
            rc, o = run(args)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        named = [l for l in o.splitlines() if l.startswith("FAIL-EXPECT") and needle in l]
        report("A planted: " + name, rc == 1 and bool(named), "exit=%d needle=%s" % (rc, needle))
    rc, o = run([], {"CIC_SPECMODEL_PLANT": "equality-version"})
    report("B planted model defect: the version compared by Python equality (true and 1.0 pass)", rc == 1 and any(l.startswith("FAIL-EXPECT model.E-PIN-01") for l in o.splitlines()), "exit=%d" % rc)
    rc, o = run(["--review", "/nonexistent/review.yaml"])
    report("C infra: the review data is unreadable (exit 2, not a detection)", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)
    print("self-test: %s" % ("all as expected" if not bad else "%d problem(s)" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
