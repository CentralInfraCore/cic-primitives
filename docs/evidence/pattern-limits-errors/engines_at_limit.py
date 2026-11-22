"""O2 measurement: does every engine compile and run the programs the proposal accepts, and what do the native engines do with the programs the CANDIDATE LIMITS (without a size rule) admit?
Engines: the own evaluator (nfa), Go regexp, Rust regex (default limits). Rule D of the engine selection: an accepted expression must compile everywhere; for PI <= PI_MAX a compile error in any engine is a FAILURE (exit 1);
above PI_MAX the line is a finding (DIVERGENCE), not a failure, because the proposal refuses those expressions. Infrastructure problems (a missing toolchain, a failed canary) exit 2 / 3 and are never a result.
"""
import os, shutil, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_argv = sys.argv; _tmp = tempfile.mkdtemp(); sys.argv = [_argv[0], _tmp]
try:
    import limit_space as L
    PE, N, S = L.PE, L.N, L.S
except BaseException as e:
    print("INCOMPLETE: %r" % (e,)); sys.exit(2)
finally:
    sys.argv = _argv; shutil.rmtree(_tmp, ignore_errors=True)
import pattern_codes as C

fails = []


def family(target):
    full, rem = divmod(target, 510)
    p = "a{0,255}" * full + ("a{0,%d}" % (rem // 2) if rem >= 2 else "")
    return p


def cases():
    cs = []
    cs.append(("pi.2048", "a{0,255}" * 4 + "a{0,4}"))
    cs.append(("pi.2049", "a{0,255}" * 4 + "a{0,4}a"))
    for t in (4096, 8192, 16320):
        cs.append(("fam.%d" % t, family(t)))
    cs.append(("worst-work.23802", "((a{0,10}){0,10}){0,10}((a[a*]{0,10}){0,10}){0,10}((a{0,10}){0,10}){0,10}((a.{0,10}){0,10}){0,10}((a{0,10}){0,10}){0,10}a*((a.{0,10}){0,10}){0,10}((a{0,10}){0,10}){0,10}((a{0,10}){0,10}){0,10}((aa*a{0,10}){0,10}(a{0,10}){0,10}){0,10}((a{0,10}){0,10}){0,10}"))
    cs.append(("dp-optimum.241250", L.solve_pat()))
    return cs


def main():
    cs = cases(); ext = []
    for i, (cid, p) in enumerate(cs):
        r = S.parse(p)
        if not r.ok:
            print("INCOMPLETE: the case %s is not accepted by the classifier: %s" % (cid, r.reason)); return 2
        ext.append({"id": cid, "p": p, "input": "a" * 256})
    res = {}
    for kind in ("go", "rust"):
        try:
            res[kind] = PE.ext_run(kind, ext, tempfile.mkdtemp())
        except SystemExit as e:
            msg = str(e.code)
            print("%s: %s" % ("CANARY" if "CANARY" in msg else "INCOMPLETE", msg)); return 3 if "CANARY" in msg else 2
        if res[kind] is None:
            print("INCOMPLETE: %s toolchain not available" % kind); return 2
    print("%-20s %7s %6s | %-24s | %-24s | %-24s" % ("case", "PI", "len", "nfa (verdict, compile+match ms)", "go (verdict, match ns)", "rust (verdict, match ns)"))
    for cid, p in cs:
        pi = C.size(N.parse_ast(p))
        t = time.perf_counter()
        try:
            m = N.Matcher(p); nv = "match" if m.fullmatch("a" * 256) else "nomatch"
        except BaseException as e:
            nv = "error:" + type(e).__name__
        nt = (time.perf_counter() - t) * 1000
        g, r_ = res["go"][cid], res["rust"][cid]
        print("%-20s %7d %6d | %-8s %12.1f | %-8s %14d | %-8s %14d" % (cid, pi, len(p), nv, nt, g[0], g[1], r_[0], r_[1]))
        bad = [n for n, v in (("nfa", nv), ("go", g[0]), ("rust", r_[0])) if v.startswith("compile_error") or v.startswith("error")]
        if bad:
            if pi <= C.PI_MAX:
                fails.append(cid); print("FAIL-EXPECT %s: an accepted expression with PI <= %d does not compile in %s" % (cid, C.PI_MAX, ",".join(bad)))
            else:
                print("DIVERGENCE %s (PI %d > %d, refused by the proposal): compile error in %s" % (cid, pi, C.PI_MAX, ",".join(bad)))
        verdicts = {nv, g[0], r_[0]} - {"compile_error"}
        if not bad and len(verdicts) > 1:
            fails.append(cid); print("FAIL-EXPECT %s: the engines disagree on the verdict: %s" % (cid, sorted(verdicts)))
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
