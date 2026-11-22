"""Self-test of the vector tooling: can the vector check and the conformance run FAIL, and for the right reason? Typed exits; infrastructure is never a detection.

  A  check_vectors.py: an unmodified positive control (exit 0); planted faults in a COPY of the vector file, each counted only when the check exits 1 AND prints a FAIL-EXPECT line of the intended check;
  B  conform.py: an unmodified positive control (exit 0, native runners included); planted defects in the prototype (CIC_CODES_PLANT), in the implementation of the text (CIC_SPEC_PLANT) and in the Go
     runner (a copy that accepts any value with a line feed), each counted only when the run exits 1 AND prints `DISAGREE <impl> <vector id>` for the intended vector;
  C  infrastructure controls: an unreadable vector file (exit 2 for both tools), a missing Go toolchain (exit 2): not detections.
Exit: 0 all as expected, 1 a mutant was not detected / a control failed / an infrastructure control was counted, 2 the self-test itself could not run."""
import os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
VEC = os.path.join(HERE, "..", "..", "design", "pattern-profile-vectors", "pattern-profile.yaml")
CHECK, CONFORM = os.path.join(HERE, "check_vectors.py"), os.path.join(HERE, "conform.py")
bad = 0


def run(args, env_extra=None):
    env = dict(os.environ)
    for k in ("CIC_CODES_PLANT", "CIC_SPEC_PLANT", "CIC_CONFORM_PLANT", "CIC_VECTORS"):
        env.pop(k, None)
    env.update(env_extra or {})
    r = subprocess.run([sys.executable] + args, capture_output=True, text=True, env=env, cwd=HERE, timeout=1200)
    return r.returncode, r.stdout + r.stderr


def line_of(text, vid):
    for l in text.splitlines():
        if l.startswith("- {id: %s," % vid):
            return l
    raise SystemExit("INCOMPLETE: no vector %s in the file" % vid)


def report(label, ok, extra=""):
    global bad
    print("%-58s %s %s" % (label, "OK" if ok else "FAIL", extra))
    bad += not ok


def faults():
    text = open(VEC, encoding="utf-8").read()
    def drop(*ids):
        t = text
        for i in ids:
            t = t.replace(line_of(t, i) + "\n", "")
        return t
    return [
        ("a requirement without a vector", drop("X-T101"), "coverage.requirement.R-T1-EMPTY"),
        ("a code without a vector", drop("X-T101"), "coverage.code.pattern_empty"),
        ("an unknown requirement", text.replace(line_of(text, "V-M001"), line_of(text, "V-M001").replace("R-MATCH-FULL", "R-NOPE")), "req.known.V-M001.R-NOPE"),
        ("a duplicate id", text.replace("{id: X-A002,", "{id: X-A001,"), "id.unique.X-A001"),
        ("an unknown code", text.replace(line_of(text, "X-S110"), line_of(text, "X-S110").replace("pattern_empty_branch", "pattern_made_up")), "code.known.X-S110"),
        ("a non-ASCII character in an expression", text.replace("{id: X-A001, expr: 'a',", "{id: X-A001, expr: '" + chr(233) + "',"), "enc.X-A001"),
        ("the only pin-missing vectors removed", drop("S-002", "S-005"), "coverage.code.pattern_profile_missing"),
        ("a limit without its refusing side", drop("X-S102"), "boundary.R-LIM-DEPTH"),
        ("an accepted expression without its PI", text.replace("{id: X-A001, expr: 'a', expect: accept, pi: 1,", "{id: X-A001, expr: 'a', expect: accept,"), "pi.present.X-A001"),
        ("a value vector with a verdict of another kind", text.replace(line_of(text, "V-M001"), line_of(text, "V-M001").replace("expect: match", "expect: accept")), "expect.V-M001"),
        ("a schema refusal without its position", text.replace(line_of(text, "S-010"), line_of(text, "S-010").replace(" at: 2,", "")), "schema.at.required.S-010"),
        ("a pin refusal that carries a position", text.replace(line_of(text, "S-002"), line_of(text, "S-002").replace("code: pattern_profile_missing,", "code: pattern_profile_missing, at: 1,")), "schema.at.forbidden.S-002"),
        ("a schema refusal with a position outside the schema", text.replace(line_of(text, "S-010"), line_of(text, "S-010").replace("at: 2,", "at: 7,")), "schema.at.required.S-010"),
        ("the declared pi_max changed to 4096", text.replace("  pi_max: 2048", "  pi_max: 4096"), "meta.limits.pi_max"),
        ("the declared length limit changed to 255", text.replace("  length: 256", "  length: 255", 1), "meta.limits.length"),
        ("the profile name changed", text.replace("  name: pattern", "  name: patterns", 1), "meta.profile.name"),
        ("a decided code removed from the code list", text.replace("  - pattern_empty\n", "", 1), "meta.codes.expression"),
        ("every accepted PI-boundary vector moved away from pi_max", text.replace("expect: accept, pi: 2048,", "expect: accept, pi: 2047,"), "meta.boundary.pi_max"),
        ("the known pin version of the schema vectors changed", text.replace("pin: {state: ok, version: 1}", "pin: {state: ok, version: 2}"), "meta.pin.known-version"),
    ]


def main():
    rc, o = run([CHECK])
    report("A positive control (unmodified vector file)", rc == 0, "exit=%d" % rc)
    for name, content, needle in faults():
        d = tempfile.mkdtemp()
        try:
            f = os.path.join(d, "v.yaml"); open(f, "w", encoding="utf-8").write(content)
            rc, o = run([CHECK, f])
        finally:
            shutil.rmtree(d, ignore_errors=True)
        named = [l for l in o.splitlines() if l.startswith("FAIL-EXPECT") and needle in l]
        report("A planted: " + name, rc == 1 and bool(named), "exit=%d needle=%s" % (rc, needle))
    rc, o = run([CONFORM])
    report("B positive control (all implementations, native)", rc == 0, "exit=%d" % rc)
    plants = [("CIC_CODES_PLANT", "charset-before-length", "DISAGREE P X-T107"), ("CIC_CODES_PLANT", "size-off-by-one", "DISAGREE P X-Z101"),
              ("CIC_CODES_PLANT", "no-size-tier", "DISAGREE P X-Z102"), ("CIC_CODES_PLANT", "size-undercount", "DISAGREE P.pi X-A013"),
              ("CIC_CODES_PLANT", "row-removed", "DISAGREE P X-Q130"), ("CIC_CODES_PLANT", "value-mismatch-before-length", "DISAGREE P V-L007"),
              ("CIC_CODES_PLANT", "early-size", "DISAGREE P X-A027"), ("CIC_SPEC_PLANT", "no-class-precheck-spec", "DISAGREE S X-K101"),
              ("CIC_SPEC_PLANT", "count-before-bounds-spec", "DISAGREE S X-Q108"), ("CIC_SPEC_PLANT", "depth-before-extension-spec", "DISAGREE S X-S124"),
              ("CIC_CONFORM_PLANT", "last-refused", "DISAGREE P.schema S-010"), ("CIC_CONFORM_PLANT", "pin-after-expressions", "DISAGREE P.schema S-005")]
    for var, plant, needle in plants:
        rc, o = run([CONFORM, "--no-native"], {var: plant})
        report("B planted: %s=%s" % (var, plant), rc == 1 and needle in o, "exit=%d needle=%r" % (rc, needle))
    # vector files with a wrong position or wrong metadata: the conformance run must see it (the whole triple is compared, the declared limits are compared with the implementation)
    text = open(VEC, encoding="utf-8").read()
    for name, content, needle in (("S-010 with the position of the third contract", text.replace(line_of(text, "S-010"), line_of(text, "S-010").replace("at: 2,", "at: 3,")), "DISAGREE P.schema S-010"),
                                  ("pi_max declared as 4096", text.replace("  pi_max: 2048", "  pi_max: 4096"), "DISAGREE P.meta limits.pi_max")):
        d = tempfile.mkdtemp()
        try:
            f = os.path.join(d, "v.yaml"); open(f, "w", encoding="utf-8").write(content)
            rc, o = run([CONFORM, "--no-native"], {"CIC_VECTORS": f})
        finally:
            shutil.rmtree(d, ignore_errors=True)
        report("B vector file: " + name, rc == 1 and needle in o, "exit=%d needle=%r" % (rc, needle))
    # planted defects in a COPY of the Go runner. (1) any value with a line feed matches: the canary `lf_refused` of the runner must catch it (exit 3, a failed canary: no result of that runner is used);
    # (2) only a value with a line feed AND the text abc matches: all four canaries pass, so only the vectors can see it
    for label, cond, want in (("any line feed", 'bytes.Contains(in, []byte("\\n"))', None), ("a line feed after abc", 'bytes.Contains(in, []byte("\\n")) && bytes.Contains(in, []byte("abc"))', "DISAGREE G V-M021")):
        d = tempfile.mkdtemp()
        try:
            src = os.path.join(HERE, "..", "grammar-pattern-measurement", "runners")
            os.makedirs(os.path.join(d, "go"))
            for f in os.listdir(os.path.join(src, "go")):
                shutil.copy(os.path.join(src, "go", f), os.path.join(d, "go", f))
            os.symlink(os.path.abspath(os.path.join(src, "rust")), os.path.join(d, "rust"))
            m = os.path.join(d, "go", "main.go"); t = open(m).read()
            assert "m := re.MatchString(string(in))" in t
            t = t.replace("m := re.MatchString(string(in))", "m := re.MatchString(string(in)) || (" + cond + ")").replace('import (\n', 'import (\n\t"bytes"\n', 1)
            open(m, "w").write(t)
            rc, o = run([CONFORM], {"CIC_PROBE_RUNNERS": d})
        finally:
            shutil.rmtree(d, ignore_errors=True)
        if want is None:
            report("B planted: the Go runner matches %s (canary)" % label, rc == 3 and "CANARY" in o, "exit=%d" % rc)
        else:
            report("B planted: the Go runner matches %s (vectors)" % label, rc == 1 and want in o, "exit=%d needle=%r" % (rc, want))
    rc, o = run([CHECK], {"CIC_VECTORS": "/nonexistent/v.yaml"})
    report("C infra: the vector file is unreadable (check)", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)
    rc, o = run([CONFORM, "--no-native"], {"CIC_VECTORS": "/nonexistent/v.yaml"})
    report("C infra: the vector file is unreadable (conform)", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)
    rc, o = run([CONFORM], {"CIC_PROBE_GO": "/nonexistent/go-toolchain"})
    report("C infra: the Go toolchain is missing", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)
    print("self-test: %s" % ("all as expected" if not bad else "%d problem(s)" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
