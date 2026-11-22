"""O2 measurement: what the candidate limits of the pattern profile really allow, and what that costs. Isolated measurement, no implementation, no grammar change.

Groups (each prints lines that results/limit_space.txt keeps; the exit code is typed: 0 ok, 1 a measured expectation failed, 2 infrastructure problem):
  boundary : for each candidate limit the largest accepted and the smallest refused value are run through the classifier (subset_check.parse).
  space    : the LARGEST NFA program (states) that the candidate limits admit, by exhaustive dynamic programming over the repeat / group family, then verified by building it.
  search   : an independent random hill-climb over the real classifier + evaluator (alternations included) must not beat the DP result (a cross-check of the DP's assumptions).
  cost     : compile time, match time (N = 256 code points), tracemalloc peak and the number of live states, as a function of the program size.
Measured values, one machine, one run each; they are not guaranteed bounds.
"""
import os, random, sys, time, tracemalloc

HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(EV, "grammar-pattern-measurement"))
sys.path.insert(0, os.path.join(EV, "pattern-engine-selection"))
import subset_check as S
import nfa_engine as N
_argv = sys.argv
import shutil, tempfile
_tmp = tempfile.mkdtemp()
sys.argv = [_argv[0], _tmp]      # probe_engines reads argv[1] as an output directory at import time; give it a scratch directory that is removed again
try:
    import probe_engines as PE
finally:
    sys.argv = _argv
    shutil.rmtree(_tmp, ignore_errors=True)

EXIT_FAIL, EXIT_INFRA = 1, 2
failures = []
E_SEARCH_CAP = 30000   # the random searches build the NFA of every candidate; above this size one candidate costs seconds (the DP optimum, E = 241250, is built and timed separately)


def out(line):
    print(line)


def expect(label, cond, detail=""):
    if not cond:
        failures.append(label)
        out("FAIL-EXPECT %s %s" % (label, detail))


def states_of(p):
    return N.Matcher(p).states


# ---------------------------------------------------------------- boundary
def boundary():
    out("## boundary: largest accepted / smallest refused value of each candidate limit")
    L = S.LIMITS
    rows = [
        ("length", "a" * L["length"], "a" * (L["length"] + 1)),
        ("repeat count", "a{%d}" % L["repeat"], "a{%d}" % (L["repeat"] + 1)),
        ("group depth", "(" * L["depth"] + "a" + ")" * L["depth"], "(" * (L["depth"] + 1) + "a" + ")" * (L["depth"] + 1)),
        ("repeat product", "(a{%d}){%d}" % (L["repeat_product"] // 4, 4), "(a{%d}){%d}" % (L["repeat_product"] // 4 + 1, 4)),
        ("unbounded quantifiers", "a*" * L["unbounded"], "a*" * (L["unbounded"] + 1)),
        ("unbounded on a group", "(a)", "(a)*"),
    ]
    for name, ok_p, bad_p in rows:
        a, b = S.parse(ok_p), S.parse(bad_p)
        expect("boundary.%s.accept" % name, a.ok, a.reason)
        expect("boundary.%s.refuse" % name, not b.ok)
        out("%-24s accepted: len=%-4d %-6s | refused: len=%-4d %-6s %s" % (name, len(ok_p), "ACCEPT" if a.ok else "REFUSE", len(bad_p), "REFUSE" if not b.ok else "ACCEPT", b.reason))
    # anchors count towards the length: 254 body chars + two anchors is 256 (accepted), 255 + two is 257 (refused)
    a = S.parse("^" + "a" * 254 + "$"); b = S.parse("^" + "a" * 255 + "$")
    expect("boundary.length.anchors", a.ok and not b.ok)
    out("%-24s accepted: len=256 %-6s | refused: len=257 %-6s %s" % ("length with both anchors", "ACCEPT" if a.ok else "REFUSE", "REFUSE" if not b.ok else "ACCEPT", b.reason))
    # the value length limit belongs to the evaluator rule, not to the classifier: a value of 256 code points is matched, 257 never matches
    m = N.Matcher("a{0,255}")
    out("%-24s 256 code points: %s | 257 code points: %s (value-length rule applied by the caller, see 3.4)" % ("value length", m.fullmatch("a" * 255), m.fullmatch("a" * 257)))


# ---------------------------------------------------------------- DP: the largest program the limits admit
CAP_MAX = S.LIMITS["repeat_product"]
REP_MAX = S.LIMITS["repeat"]
LEN_MAX = S.LIMITS["length"]
DEPTH = S.LIMITS["depth"]
H_SET = sorted(set(list(range(1, 33)) + [40, 48, 50, 60, 64, 80, 100, 120, 125, 128, 150, 200, 250, 255]))
ATOMS = [("a", 1, 1), ("[a-z]", 5, 1), (".", 1, 1)]   # text, chars, states


def qtxt(h):
    return "{0,%d}" % h


def solve():
    memo = {}

    def K(d, cap):
        """best[n] = (states, text) of a concat of total length n whose items all have repeat product <= cap, at group depth budget d."""
        key = (d, cap)
        if key in memo:
            return memo[key]
        item = {}   # chars -> (states, text)

        def put(k, s, t):
            if k <= LEN_MAX and (k not in item or s > item[k][0]):
                item[k] = (s, t)
        for t, c, s in ATOMS:
            put(c, s, t)
            for h in H_SET:
                if h <= min(cap, REP_MAX):
                    put(c + len(qtxt(h)), 2 * h * s, t + qtxt(h))   # lo = 0: h optional copies, each an extra state plus the atom
        if d > 0:
            for h in H_SET:
                if h > cap or h > REP_MAX:
                    continue
                inner = K(d - 1, cap // h)
                for n, (s, t) in enumerate(inner):
                    if t is None:
                        continue
                    put(n + 2 + len(qtxt(h)), h * (1 + s), "(" + t + ")" + qtxt(h))
        best = [(0, "")] + [(-1, None)] * LEN_MAX
        for n in range(1, LEN_MAX + 1):
            for k, (s, t) in item.items():
                if k <= n and best[n - k][1] is not None:
                    v = best[n - k][0] + s
                    if v > best[n][0]:
                        best[n] = (v, best[n - k][1] + t)
        memo[key] = best
        return best
    return K(DEPTH, CAP_MAX)


def space():
    out("## space: the largest NFA program the candidate limits admit (DP over atoms, {0,h}, groups; no alternation, <=3 unbounded quantifiers ignored)")
    best = solve()
    s, p = max(((v[0], v[1]) for v in best if v[1] is not None), key=lambda x: x[0])
    r = S.parse(p)
    expect("space.dp-pattern-accepted", r.ok, r.reason)
    real = states_of(p) if r.ok else -1
    out("DP optimum: %d states predicted, %d states built; pattern length %d; classifier stats %s" % (s, real, len(p), dict(r.stats)))
    out("DP optimum pattern: %s" % p)
    expect("space.model-equals-build", real == s + 1 - 1 or abs(real - s) <= 1, "predicted %d built %d" % (s, real))   # +1 for the accept state
    # the program size at a few lengths shows how steeply it grows with the text
    for n in (16, 32, 64, 128, 256):
        v = max(best[: n + 1], key=lambda x: x[0] if x[1] is not None else -1)
        out("best program within %3d characters: %6d states" % (n, v[0]))
    return p, real


# ---------------------------------------------------------------- independent search (alternations, anchors, mixed shapes)
def mutate(p, rnd):
    pieces = ["a", "[a-z]", ".", "a{0,%d}" % rnd.choice([3, 10, 50, 255]), "(a{0,%d}){0,%d}" % (rnd.choice([5, 25, 100, 250]), rnd.choice([2, 4, 10])),
              "(a|b{0,%d})" % rnd.choice([10, 100, 255]), "a*", "[a-c]{0,%d}" % rnd.choice([10, 100, 255]), "(a{0,%d}|b{0,%d}){0,%d}" % (rnd.choice([5, 25]), rnd.choice([5, 25]), rnd.choice([2, 4, 8]))]
    q = p
    for _ in range(rnd.choice([1, 1, 2])):
        r = rnd.random()
        if r < 0.5 or not q:
            i = rnd.randrange(len(q) + 1); q = q[:i] + rnd.choice(pieces) + q[i:]
        elif r < 0.75:
            i = rnd.randrange(len(q)); j = min(len(q), i + rnd.randrange(1, 10)); q = q[:i] + q[j:]
        else:
            i = rnd.randrange(len(q) + 1); q = q[:i] + rnd.choice(pieces) + q[min(len(q), i + rnd.randrange(1, 6)):]
    return q


def search(dp_states, iters=4000, seed=20261122):
    out("## search: independent random hill-climb on the real classifier and evaluator (%d candidates, seed %d)" % (iters, seed))
    rnd = random.Random(seed)
    cur, cur_s, tried, accepted = "a", 1, 0, 0
    top = (1, "a")
    for _ in range(iters):
        q = mutate(cur, rnd); tried += 1
        r = S.parse(q)
        if not r.ok or E(q) > 2 * E_SEARCH_CAP:
            continue
        accepted += 1
        s = states_of(q)
        if s >= cur_s or rnd.random() < 0.02:
            cur, cur_s = q, s
        if s > top[0]:
            top = (s, q)
    out("candidates %d, accepted by the classifier %d; best program found by the search: %d states (length %d)" % (tried, accepted, top[0], len(top[1])))
    out("best pattern found: %s" % top[1])
    expect("search.not-above-dp", top[0] <= dp_states, "search %d > DP %d: the DP model misses a shape" % (top[0], dp_states))
    return top


# ---------------------------------------------------------------- cost vs program size
def fam(target):
    """a pattern of about `target` states: concat of 'a{0,255}' (510 states, 8 characters) and one remainder item."""
    full, rem = divmod(target, 510)
    p = "a{0,255}" * full
    if rem >= 2:
        p += "a{0,%d}" % (rem // 2)
    return p or "a"


def timeit(f, reps):
    best = 1e9
    for _ in range(reps):
        t = time.perf_counter(); f(); best = min(best, time.perf_counter() - t)
    return best


def cost():
    out("## cost: the own evaluator against the program size (family a{0,255} repeated; value = 256 x 'a'; compile best of 3, match best of 3, one process)")
    out("%8s %8s %7s %12s %12s %12s %10s" % ("states", "P", "length", "compile ms", "match ms", "peak kB", "ms/(P*N)ns"))
    rows = []
    for target in (510, 1020, 2040, 4080, 8160, 16320):
        p = fam(target)
        if len(p) > LEN_MAX:
            continue
        r = S.parse(p)
        expect("cost.family.accepted.%d" % target, r.ok, r.reason)
        tracemalloc.start()
        m = N.Matcher(p)
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        c = timeit(lambda: N.Matcher(p), 3)
        v = "a" * 256
        mt = timeit(lambda: m.fullmatch(v), 3)
        P = m.states + m.ranges + m.edges
        rows.append((m.states, P, len(p), c * 1000, mt * 1000, peak / 1024))
        out("%8d %8d %7d %12.2f %12.2f %12.0f %10.1f" % (m.states, P, len(p), c * 1000, mt * 1000, peak / 1024, mt * 1e9 / (P * 256)))
    return rows


def contracts():
    out("## contracts: program size of the 9 existing contracts")
    mx = 0
    for n, (p, sample, kind) in enumerate(PE.CONTRACTS):
        m = N.Matcher(p); mx = max(mx, m.states)
        out("c%d states=%4d length=%3d %s" % (n, m.states, len(p), p))
    out("largest existing contract: %d states" % mx)
    return mx


# ---------------------------------------------------------------- the implementation-independent size measure E and the work counter
def expanded(node):
    """PI, the normative size measure of the proposal: defined by recurrence on the expression text alone (no engine): an atom (literal, '.', class) 1; a sequence the sum; an alternation 1 + the sum of its
    branches; a bounded repeat {lo,hi} lo x PI(x) + (hi-lo) x (1 + PI(x)); an unbounded repeat (*, +, {lo,}) 1 + (lo+1) x PI(x). For the reference construction the NFA has exactly PI + 1 states (the accept state)."""
    k = node[0]
    if k in ("lit", "any", "cls"):
        return 1
    if k == "cat":
        return sum(expanded(x) for x in node[1])
    if k == "alt":
        return 1 + sum(expanded(x) for x in node[1])
    _, inner, lo, hi = node
    x = expanded(inner)
    return 1 + (lo + 1) * x if hi is None else lo * x + (hi - lo) * (1 + x)


def E(p):
    return expanded(N.parse_ast(p))


def work(m, value):
    """The number of state visits of the simulation (a deterministic stand-in for time): closure visits over the whole match. Verdict must equal Matcher.fullmatch."""
    eps, out_, step, acc = m.eps, m.out, m.step, m.prog.accept
    mark = [0] * m.states; gen = 1; w = 0
    cur = []; stack = [m.start]
    while stack:
        x = stack.pop()
        if mark[x] == gen:
            continue
        mark[x] = gen; w += 1
        if out_[x]:
            cur.append(x)
        stack.extend(eps[x])
    for ch in value:
        o = ord(ch); gen += 1; nxt = []
        for s_ in cur:
            for kind, arg, n_ in step[s_]:
                w += 1
                ok = (arg == ch) if kind == "c" else (ch != "\n") if kind == "any" else any(lo <= o <= hi for lo, hi in arg)
                if ok:
                    stack.append(n_)
                    while stack:
                        x = stack.pop()
                        if mark[x] == gen:
                            continue
                        mark[x] = gen; w += 1
                        if out_[x]:
                            nxt.append(x)
                        stack.extend(eps[x])
        cur = nxt
        if not cur:
            break
    return w, acc in cur


def worksearch(cap, iters=1500, seed=20261123):
    out("## worksearch (PI <= %d): the pattern that maximizes the simulation work on a 256-code-point value (hill-climb, %d candidates, seed %d; values 'a' x 256 and 'a' x 255 + 'b')" % (cap, iters, seed))
    rnd = random.Random(seed)
    vals = ["a" * 256, "a" * 255 + "b"]

    def score(q):
        m = N.Matcher(q)
        return max(work(m, v)[0] for v in vals)

    def fits(q):
        return S.parse(q).ok and E(q) <= cap
    seeds = []
    for unit in ("a{0,255}", "(a{0,250}){0,4}", "((a{0,10}){0,10}){0,10}", "((a?){10}){0,10}", "(a{0,25}|b{0,25}){0,10}"):
        k = 1
        while fits(unit * (k + 1)) and len(unit) * (k + 1) <= 256:
            k += 1
        if fits(unit * k):
            seeds.append(unit * k)
    cur, cur_w = max(((q, score(q)) for q in seeds), key=lambda x: x[1])
    top = (cur_w, cur)
    for _ in range(iters):
        q = mutate(cur, rnd)
        if not fits(q):
            continue
        w = score(q)
        if w >= cur_w or rnd.random() < 0.02:
            cur, cur_w = q, w
        if w > top[0]:
            top = (w, q)
    m = N.Matcher(top[1])
    for v in vals:
        w, ok = work(m, v)
        expect("worksearch.verdict-equals-matcher", ok == m.fullmatch(v))
    mt = timeit(lambda: m.fullmatch(vals[0]), 3); ct = timeit(lambda: N.Matcher(top[1]), 3)
    out("cap %6d: worst work %9d visits; pattern length %3d; PI=%6d; match %8.1f ms; compile %7.2f ms" % (cap, top[0], len(top[1]), E(top[1]), mt * 1000, ct * 1000))
    out("  pattern: %s" % top[1])
    return top


def ratio():
    out("## size: the measure PI against the NFA states over accepted patterns (DP optimum, the 9 contracts, random mutations up to E <= %d)" % E_SEARCH_CAP)
    rnd = random.Random(7)
    worst = (0.0, "")
    ps = [p for p, _, _ in PE.CONTRACTS] + [solve_pat()]
    cur = "a"
    for _ in range(600):
        cur = mutate(cur, rnd) if rnd.random() < 0.9 else "a"
        if S.parse(cur).ok and E(cur) <= E_SEARCH_CAP:
            ps.append(cur)
    for p in ps:
        e = E(p); st = states_of(p)
        expect("size.states==PI+1", st == e + 1, "%s states=%d PI=%d" % (p[:40], st, e))
    out("patterns %d: the NFA has exactly PI + 1 states on every one of them" % len(ps))


def solve_pat():
    best = solve()
    return max(((v[0], v[1]) for v in best if v[1] is not None), key=lambda x: x[0])[1]


def main():
    groups = sys.argv[1].split(",") if len(sys.argv) > 1 else ["boundary", "contracts", "space", "size", "search", "worksearch", "cost"]
    dp = None
    if "boundary" in groups:
        boundary()
    if "contracts" in groups:
        contracts()
    if "space" in groups:
        p, real = space(); dp = real
        out("worst match at the DP optimum (value = 256 x 'a', then 256 x 'a' + 'b'):")
        m = N.Matcher(p)
        for lab, v in (("a*256", "a" * 256), ("a*256+b", "a" * 256 + "b")):
            tracemalloc.start(); N.Matcher(p); peak = tracemalloc.get_traced_memory()[1]; tracemalloc.stop()
            out("  value %-8s match %8.1f ms, compile %8.1f ms, compile peak %6.0f kB, P=%d (states %d + ranges %d + edges %d)" % (lab, timeit(lambda: m.fullmatch(v), 3) * 1000, timeit(lambda: N.Matcher(p), 3) * 1000, peak / 1024, m.states + m.ranges + m.edges, m.states, m.ranges, m.edges))
    if "size" in groups:
        ratio()
    if "worksearch" in groups:
        for cap in (512, 1024, 2048, 4096, 8192, 30000):
            worksearch(cap)
    if "search" in groups:
        search(dp if dp is not None else real_dp())
    if "cost" in groups:
        cost()
    if failures:
        out("FAILED: %s" % ", ".join(failures))
        return EXIT_FAIL
    out("all expectations held")
    return 0


def real_dp():
    p, real = space()
    return real


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as e:   # infrastructure problem, never counted as a detection
        print("INCOMPLETE: %r" % (e,)); sys.exit(EXIT_INFRA)
