"""Self-test of codes_probe.py: can the probe FAIL, and for the right reason? Same rules as the engine-selection self-test (typed exits; infrastructure is never a detection).

  positive control : the unmodified prototype must exit 0.
  planted defects  : each is switched on with CIC_CODES_PLANT; the probe must exit 1 AND print a FAIL-EXPECT line of the check that is meant to catch it (a bare non-zero exit is not a detection).
  infra controls   : a missing prototype module and a crashing one must give exit 2 (INCOMPLETE), which is never counted as a detection.
Exit: 0 all as expected, 1 a mutant was not detected / the control failed / an infra control was counted, 2 the self-test itself could not run.
"""
import os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, "codes_probe.py")

# planted defect -> a substring that one of the FAIL-EXPECT lines must contain
MUTANTS = [
    ("charset-before-length", "precedence.too-long-before-charset"),
    ("size-off-by-one", "boundary.PI == PI_MAX"),
    ("no-size-tier", "boundary.PI == PI_MAX + 1"),
    ("size-undercount", "boundary.PI == PI_MAX + 1"),
    ("row-removed", "totality"),
    ("nondeterministic", "determinism"),
    ("value-mismatch-before-length", "value.too-long-and-not-matching"),
]


def run(env_extra=None, probe=PROBE, cwd=HERE):
    env = dict(os.environ); env.pop("CIC_CODES_PLANT", None); env.update(env_extra or {})
    r = subprocess.run([sys.executable, probe], capture_output=True, text=True, env=env, cwd=cwd, timeout=900)
    return r.returncode, r.stdout + r.stderr


def main():
    bad = 0
    rc, o = run()
    ok = rc == 0
    print("%-34s exit=%d %s" % ("positive control (unmodified)", rc, "OK" if ok else "FAIL"))
    bad += not ok
    for plant, needle in MUTANTS:
        rc, o = run({"CIC_CODES_PLANT": plant})
        named = [l for l in o.splitlines() if l.startswith("FAIL-EXPECT") and needle in l]
        det = rc == 1 and bool(named)
        print("%-34s exit=%d expected check %-40r %s" % ("planted: " + plant, rc, needle, "DETECTED" if det else "NOT DETECTED"))
        bad += not det
    # infrastructure controls: a copy of the directory without / with a broken prototype module
    for name, mutate in (("infra: prototype module missing", lambda d: os.remove(os.path.join(d, "pattern_codes.py"))),
                         ("infra: prototype module crashes", lambda d: open(os.path.join(d, "pattern_codes.py"), "w").write("raise RuntimeError('planted')\n"))):
        d = tempfile.mkdtemp()
        try:
            for f in ("codes_probe.py", "pattern_codes.py"):
                shutil.copy(os.path.join(HERE, f), d)
            mutate(d)
            rc, o = run(probe=os.path.join(d, "codes_probe.py"), cwd=d)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        ok = rc == 2 and "INCOMPLETE" in o
        print("%-34s exit=%d %s" % (name, rc, "OK (not a detection)" if ok else "FAIL (counted as something else)"))
        bad += not ok
    print("self-test: %s" % ("all as expected" if not bad else "%d problem(s)" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
