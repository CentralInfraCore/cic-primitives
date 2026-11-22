"""O2 / review F2 of #48: the AGGREGATE cost of evaluating many contracts, and where the responsibility for it lies. Isolated measurement; no implementation.

  real      : the three real release records against their composed schema: every pattern-constrained value, every distinct expression compiled once, the total compile and match time.
  synthetic : K distinct contracts, each the slowest expression found under PI <= 2048 (results/limit_space.txt), each with one worst-case value of 256 code points: the total against K.
  values    : one such contract, M worst-case values: the total against M (the compile cost is paid once per distinct expression).
Typed exits: 0 ok, 1 a measured expectation failed, 2 infrastructure (a record, a tag or the results file missing): never a result. Measured, one machine, best of 3 per figure; not guaranteed bounds.
"""
import os, re, shutil, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
_argv = sys.argv; _tmp = tempfile.mkdtemp(); sys.argv = [_argv[0], REPO]
try:
    import limit_space as L
    import compat_records as R            # the extraction of the pattern-constrained values of the real records (its ROOT = argv[1])
    import yaml
    N, S = L.N, L.S
except BaseException as e:
    print("INCOMPLETE: %r" % (e,)); sys.exit(2)
finally:
    sys.argv = _argv; shutil.rmtree(_tmp, ignore_errors=True)

fails = []


def best(f, reps=3):
    b = 1e9
    for _ in range(reps):
        t = time.perf_counter(); f(); b = min(b, time.perf_counter() - t)
    return b


def real():
    print("## real: the real records against their composed schema (own evaluator, each distinct expression compiled once)")
    print("%-62s %7s %9s %12s %12s" % ("record", "values", "distinct", "compile ms", "match ms"))
    for label, kind, ref, schema_kind in R.RECORDS:
        try:
            rec = yaml.safe_load(R.load(kind, ref))
            schema = R.C.compose(os.path.join(REPO, "docs", "design", "release-schemas"), schema_kind)
        except BaseException as e:
            print("INCOMPLETE: %s: %r" % (label, e)); sys.exit(2)
        pairs = []
        for path, expr, chain in R.pattern_nodes(schema["spec"]["config_surface"]["nodes"]):
            for v in R.values(rec, path, chain).strs:
                pairs.append((expr, v))
        distinct = sorted({e for e, _ in pairs})
        if len(pairs) < R.MIN_VALUES:
            print("INCOMPLETE: only %d values in %s" % (len(pairs), label)); sys.exit(2)

        def compile_all():
            return {e: N.Matcher(e) for e in distinct}
        ct = best(compile_all)
        ms = compile_all()
        mt = best(lambda: [ms[e].fullmatch(v) for e, v in pairs])
        bad = [(e, v) for e, v in pairs if not ms[e].fullmatch(v)]
        print("%-62s %7d %9d %12.3f %12.3f" % (label[:62], len(pairs), len(distinct), ct * 1000, mt * 1000))
        if bad:
            fails.append(label); print("FAIL-EXPECT %s: %d real value(s) do not match their contract, e.g. %r" % (label, len(bad), bad[0]))


def slowest_2048():
    try:
        lines = open(os.path.join(HERE, "results", "limit_space.txt"), encoding="utf-8").read().splitlines()
    except OSError as e:
        print("INCOMPLETE: results/limit_space.txt: %r" % (e,)); sys.exit(2)
    for i, l in enumerate(lines):
        if re.match(r"cap\s+2048:", l):
            return lines[i + 1].split("pattern:", 1)[1].strip()
    print("INCOMPLETE: the cap-2048 line is not in results/limit_space.txt"); sys.exit(2)


def variants(p, k):
    used = set(re.findall(r"[A-Za-z0-9]", p))
    free = [c for c in "cdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" if c not in used]
    if len(free) < k:
        print("INCOMPLETE: not enough free letters for %d variants" % k); sys.exit(2)
    return [(p.translate(str.maketrans("a", c)), c) for c in free[:k]]


def synthetic():
    p0 = slowest_2048()
    r = S.parse(p0)
    if not r.ok:
        print("INCOMPLETE: the cap-2048 expression is no longer accepted: %s" % r.reason); sys.exit(2)
    pi = L.E(p0)
    print("## synthetic: K distinct contracts, each the slowest expression found under PI <= 2048 (PI=%d, length %d), one value of 256 code points each" % (pi, len(p0)))
    print("%4s %12s %12s %12s %14s" % ("K", "compile ms", "match ms", "total ms", "total/K ms"))
    rows = []
    for k in (1, 2, 4, 8, 16, 32):
        vs = variants(p0, k)
        for q, _ in vs:
            if not S.parse(q).ok or L.E(q) != pi:
                print("INCOMPLETE: a variant is not equivalent to the original"); sys.exit(2)
        ct = best(lambda: [N.Matcher(q) for q, _ in vs], 2)
        ms = [N.Matcher(q) for q, _ in vs]
        mt = best(lambda: [m.fullmatch(c * 256) for m, (_, c) in zip(ms, vs)], 2)
        rows.append((k, ct * 1000, mt * 1000))
        print("%4d %12.1f %12.1f %12.1f %14.2f" % (k, ct * 1000, mt * 1000, (ct + mt) * 1000, (ct + mt) * 1000 / k))
    per = [(c + m) / k for k, c, m in rows]
    expect_linear = max(per) / min(per) < 2.0
    print("per-contract cost varies by a factor of %.2f over K = 1..32 (additive: the total is the sum of the parts)" % (max(per) / min(per)))
    if not expect_linear:
        fails.append("synthetic.additive"); print("FAIL-EXPECT synthetic.additive the per-contract cost is not constant")
    return p0, rows


def values_one_contract(p0):
    print("## values: one contract (the same expression), M values of 256 code points; compile once")
    m = N.Matcher(p0)
    ct = best(lambda: N.Matcher(p0), 2)
    print("compile once: %.1f ms" % (ct * 1000))
    print("%5s %12s %14s" % ("M", "match ms", "match/M ms"))
    for k in (1, 10, 100):
        mt = best(lambda: [m.fullmatch("a" * 256) for _ in range(k)], 2)
        print("%5d %12.1f %14.2f" % (k, mt * 1000, mt * 1000 / k))


def main():
    real()
    p0, rows = synthetic()
    values_one_contract(p0)
    k, c, mt = rows[-1]
    print("model (an extrapolation, NOT a measurement): total ~ sum over distinct expressions of compile(PI) + sum over values of match(PI, length); at about %.0f ms per worst-case contract and value, 1000 such contracts would take about %.0f s" % ((c + mt) / k, 1000 * (c + mt) / k / 1000))
    if fails:
        print("FAILED: %s" % ", ".join(fails)); return 1
    print("all expectations held"); return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
