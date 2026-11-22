"""Review finding F1 of PR #47: the evaluator reviewed at d1e0b8c precomputed the epsilon closure of EVERY state (nfa_closure_precomputed.py). This probe measures what that costs on VALID
patterns of the closed subset that make large closures, and compares it with the evaluator that follows the closure on the fly (nfa_engine.py). Patterns the classifier refuses are reported as
refused and not measured. Compile memory is the tracemalloc peak of the compile; times are best of 3 (compile) and median of 5 (match); the value is 256 code points (the profile cap) and, for
the current evaluator only, 65536 (a length no profile wrapper lets through: the engine's own scaling).
Verdicts of the two evaluators are compared on every case: they must be identical (the rewrite must not change semantics).
Usage: closure_probe.py [out.txt]   Exit 1 if a verdict differs or a pattern the probe lists as accepted turns out refused."""
import os, statistics, sys, time, tracemalloc
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(1, os.path.join(HERE, "..", "grammar-pattern-measurement"))
import nfa_engine as NEW, nfa_closure_precomputed as OLD, subset_check as S
CASES = [
    ("opt_chain_255", "^(a?){255}$", "a" * 256), ("opt_chain_255_tail", "^(a?){255}a{255}$", "a" * 255 + "b"),
    ("nested_opt_10x10x10", "^(((a?){10}){10}){10}$", "a" * 256), ("nested_opt_4level", "^((((a?){5}){5}){5}){5}$", "a" * 256),
    ("alt_of_opts_255", "^(a?|b?|c?){255}$", "ab" * 128), ("alt_8_255", "^(a|b|c|d|e|f|g|h){255}$", "abcdefgh" * 32),
    ("star_alt_opts", "^(a?|b?|c?)*$", "ab" * 128), ("opt_runs_x3", "^(a?){255}(b?){255}(c?){255}$", "a" * 256),
    ("class_runs_25", "^" + "[a-z]{255}" * 25 + "$", "a" * 256), ("plain_a_255", "^a{255}$", "a" * 255),
    ("opt_1000_flat", "^" + "a?" * 120 + "$", "a" * 120),
]
tm = lambda f, n: sorted(time.perf_counter_ns() - (f(), time.perf_counter_ns())[1] for _ in range(n))
def best_ns(f, n):
    r = []
    for _ in range(n):
        t = time.perf_counter_ns(); f(); r.append(time.perf_counter_ns() - t)
    return r
def compile_peak(mod, p):
    tracemalloc.start(); tracemalloc.reset_peak(); m = mod.compile(p); peak = tracemalloc.get_traced_memory()[1]; tracemalloc.stop(); return m, peak
def main():
    out = []; bad = 0
    out.append("%-22s %7s %9s %8s | %-26s | %-26s | %s" % ("case", "states", "closuresum", "closMax", "OLD compile ms / peak kB / match ms", "NEW compile ms / peak kB / match ms", "NEW 65536 cp ms"))
    for name, p, v in CASES:
        if not S.parse(p).ok:
            out.append("%-22s REFUSED by the classifier (%s): not measured" % (name, S.parse(p).reason)); continue
        mo, po = compile_peak(OLD, p); mn, pn = compile_peak(NEW, p)
        csum = sum(len(c) for c in mo.closure); cmax = max(len(c) for c in mo.closure)
        co = min(best_ns(lambda: OLD.compile(p), 3)); cn = min(best_ns(lambda: NEW.compile(p), 3))
        xo = statistics.median(best_ns(lambda: mo.fullmatch(v), 5)); xn = statistics.median(best_ns(lambda: mn.fullmatch(v), 5))
        vl = v * (65536 // max(1, len(v)) + 1); vl = vl[:65536]; xl = statistics.median(best_ns(lambda: mn.fullmatch(vl), 3))
        same = all(mo.fullmatch(x) == mn.fullmatch(x) for x in (v, v[:-1], v + "x", "", "ab", v[::-1]))
        if not same:
            bad += 1
        out.append("%-22s %7d %9d %8d | %8.2f / %8d / %8.2f | %8.2f / %8d / %8.2f | %9.1f%s" % (name, mn.states, csum, cmax, co / 1e6, po // 1024, xo / 1e6, cn / 1e6, pn // 1024, xn / 1e6, xl / 1e6, "" if same else "  <-- VERDICTS DIFFER"))
    out.append("closuresum = total entries of the precomputed closures (OLD); a quadratic growth of it against `states` is the F1 concern. NEW has no closure table.")
    open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results", "closure.txt"), "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
    return 1 if bad else 0
if __name__ == "__main__":
    sys.exit(main())
