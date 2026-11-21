"""Child-process runner of one Python-side engine (it runs under the interpreter that has the engine installed).
  runner_py.py <engine> verdicts <cases.json>   one line per case:  id|verdict|compile_ns|match_ns   verdict = match | nomatch | refused
  runner_py.py <engine> bench <case.json>       one line:           compile_ns_min|match_ns_median|peak_kb_above_start|states   (case = {p, input_hex, compiles, matches})
cases = [{id, p, input_hex}]. The value cap (256 code points) is applied here, as the profile's wrapper does. A refusal by the engine is 'refused', never a verdict."""
import json, os, resource, statistics, sys, time, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engines as E


def _status(key):
    for l in open("/proc/self/status"):
        if l.startswith(key + ":"):
            return int(l.split()[1])
    return 0


def main():
    engine, mode, path = sys.argv[1:4]
    cases = json.load(open(path))
    if not cases:
        print("no cases: refusing to produce an empty result", file=sys.stderr); sys.exit(2)
    if mode == "bench":
        c = cases if isinstance(cases, dict) else cases[0]
        v = bytes.fromhex(c["input_hex"]).decode("utf-8")
        E.compile(engine, "a")(v)                       # warm up: imports and one-time allocations are not the case's
        rss0 = _status("VmRSS")
        try:
            open("/proc/self/clear_refs", "w").write("5")   # reset the peak (VmHWM) to the current size
        except OSError:
            sys.exit("INCOMPLETE: /proc/self/clear_refs is not writable: the peak memory cannot be measured")
        cs = []
        for _ in range(c["compiles"]):
            t = time.perf_counter_ns(); m = E.compile(engine, c["p"]); cs.append(time.perf_counter_ns() - t)
        ms = []
        for _ in range(c["matches"]):
            t = time.perf_counter_ns(); m(v); ms.append(time.perf_counter_ns() - t)
        print("%d|%d|%d|%d" % (min(cs), statistics.median(ms), max(0, _status("VmHWM") - rss0), getattr(getattr(m, "__self__", None), "states", 0)))
        return
    for c in cases:
        v = bytes.fromhex(c["input_hex"]).decode("utf-8")
        t0 = time.perf_counter_ns()
        try:
            m = E.compile(engine, c["p"])
        except E.Unsupported:
            print("%s|refused|0|0" % c["id"]); continue
        t1 = time.perf_counter_ns()
        r = (E.cap(v) or c.get("nocap")) and m(v)      # nocap: the timing group measures the ENGINE on long values; the cap is the profile's wrapper
        t2 = time.perf_counter_ns()
        print("%s|%s|%d|%d" % (c["id"], "match" if r else "nomatch", t1 - t0, t2 - t1))


if __name__ == "__main__":
    main()
