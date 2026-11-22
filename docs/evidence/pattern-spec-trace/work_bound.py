"""Review F3 of #52: the deterministic WORK bound of the evaluator. The first form W <= c x PI x N allows ZERO work for a zero-size program (PI = 0) and for the empty value (N = 0), both of which the accepted
profile allows and both of which cost something (the start state is entered, the accept state is checked). The proposed form is  W <= c x (PI + 1) x (N + 1).
This ISOLATED measurement counts the state visits of the own evaluator (limit_space.work, a deterministic stand-in for time) on a corpus that includes the zero-size programs and the empty value, reports the
largest observed ratio W / ((PI+1)(N+1)), checks the provisional constant, and shows that the first form is refuted by measurement. The exact constant and the counted operations are fixed in the
implementation measurement plan; a measured ratio is not a guarantee. Typed exits: 0 ok, 1 a FAIL-EXPECT line, 2 infrastructure.
Usage: work_bound.py [--c CONSTANT]      (CIC_WORK_PLANT=inflate multiplies the counted work by N + 1, a planted quadratic defect, for the self-test)"""
import os, re, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pattern-limits-errors"))
_argv = sys.argv; _tmp = tempfile.mkdtemp(); sys.argv = [_argv[0], _tmp]
try:
    import limit_space as L
    PE, N_, S = L.PE, L.N, L.S
except BaseException as e:
    print("INCOMPLETE: %r" % (e,)); sys.exit(2)
finally:
    sys.argv = _argv; shutil.rmtree(_tmp, ignore_errors=True)

C_PROVISIONAL = 8.0
fails = []


def expect(label, cond, detail=""):
    if not cond:
        fails.append(label); print("FAIL-EXPECT %s %s" % (label, detail))


def slow_patterns():
    try:
        lines = open(os.path.join(HERE, "..", "pattern-limits-errors", "results", "limit_space.txt"), encoding="utf-8").read().splitlines()
    except OSError as e:
        print("INCOMPLETE: limit_space.txt: %r" % (e,)); sys.exit(2)
    out = []
    for i, l in enumerate(lines):
        m = re.match(r"cap\s+(\d+):", l)
        if m and int(m.group(1)) <= 2048:
            out.append(lines[i + 1].split("pattern:", 1)[1].strip())
    return out


def corpus():
    c = []
    for p, sample, kind in PE.CONTRACTS:
        for v in ("", sample, sample + "x", "a" * 16, "a" * 256):
            c.append((p, v))
    for p in ("a{0}", "(a{0}){255}", "(a{0,255}a{0,255}a{0,255}a{0,255}a{0,255}){0}b", "a*", "a?", "a{0,255}", "[a-z]*"):
        for v in ("", "b", "a", "a" * 16, "a" * 256):
            c.append((p, v))
    for p in slow_patterns():
        for v in ("", "a", "a" * 16, "a" * 256, "a" * 255 + "b"):
            c.append((p, v))
    return c


def main(argv):
    cc = float(argv[argv.index("--c") + 1]) if "--c" in argv else C_PROVISIONAL
    plant = os.environ.get("CIC_WORK_PLANT", "")
    rows, worst = [], (0.0, "")
    zero_cases = 0; old_violations = 0
    for p, v in corpus():
        r = S.parse(p)
        if not r.ok or L.E(p) > 2048:
            print("INCOMPLETE: a corpus expression is not accepted: %r" % (p[:50],)); return 2
        pi = L.E(p); n = len(v)
        if plant == "no-zero-cases" and (pi == 0 or n == 0):      # planted: a corpus that cannot refute the first form
            continue
        m = N_.Matcher(p)
        w, _ = L.work(m, v)
        if plant == "inflate":
            w *= (n + 1)
        ratio = w / float((pi + 1) * (n + 1))
        rows.append((p, n, pi, w, ratio))
        if ratio > worst[0]:
            worst = (ratio, "%s (N=%d, PI=%d, W=%d)" % (p[:40], n, pi, w))
        expect("bound.%s.N%d" % (p[:30], n), w <= cc * (pi + 1) * (n + 1), "W=%d, c=%s, PI=%d, N=%d, ratio %.2f" % (w, cc, pi, n, ratio))
        if (pi == 0 or n == 0) and w > 0:
            old_violations += 1                      # W <= c x PI x N would force W = 0 here, for every c
        zero_cases += (pi == 0 or n == 0)
    print("corpus: %d (expression, value) pairs, of them %d with PI = 0 or N = 0" % (len(rows), zero_cases))
    print("largest observed ratio W / ((PI+1)(N+1)): %.3f at %s" % worst)
    print("the first form W <= c x PI x N is refuted for every c by %d corpus pairs (PI = 0 or N = 0 with W > 0)" % old_violations)
    expect("old-bound.refuted", old_violations > 0, "no corpus pair refutes the first form: the corpus lacks a zero-size program or an empty value")
    print("provisional constant c = %s (a measurement, not a guarantee; the exact constant and the counted operations belong to the implementation measurement plan)" % cc)
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
