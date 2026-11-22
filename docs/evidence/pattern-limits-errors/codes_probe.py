"""O3 probe: do the proposed codes form a TOTAL, DETERMINISTIC, correctly ORDERED refusal of the pattern profile? Isolated measurement (see pattern_codes.py).

Checks (every failure is a line FAIL-EXPECT ...; exit 1 = a measured expectation failed, exit 2 = the probe could not run, never a detection):
  precedence : hand-authored multi-defect expressions with the code the TIER RULE gives (authored from the rule text, not from the output of the classifier)
  boundary   : PI exactly PI_MAX is accepted, PI_MAX + 1 is refused with pattern_program_too_large; PI + 1 equals the NFA state count
  value      : the order of the value-time reasons
  totality   : every refused expression of the corpora (84 constructs, the limit cases, 30000 seeded random texts) gets exactly one code; none UNMAPPED / AMBIGUOUS
  coverage   : which defined codes the corpora reach (an unreached code is reported, it is a finding about the rule, not a failure)
  determinism: the same codes under 4 different PYTHONHASHSEEDs (a child process each)
"""
import hashlib, os, random, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
import shutil, tempfile
_argv = sys.argv
_tmp = tempfile.mkdtemp()
sys.argv = [_argv[0], _tmp]      # probe_engines reads argv[1] as an output directory at import time; give it a scratch directory that is removed again
try:
    import pattern_codes as C
    import spec_classifier as SP
    import nfa_engine as N
    import probe_engines as PE
except BaseException as e:
    print("INCOMPLETE: cannot import the prototype: %r" % (e,)); sys.exit(2)
finally:
    sys.argv = _argv
    shutil.rmtree(_tmp, ignore_errors=True)

fails = []


def expect(label, cond, detail=""):
    if not cond:
        fails.append(label); print("FAIL-EXPECT %s %s" % (label, detail))


# independent expectations: pattern -> code, written from the tier rule of pattern_codes.py
BIG = "(a{0,250}){0,4}" * 3        # PI = 3 x 4 x 501 + ... well above PI_MAX, syntactically fine
PRECEDENCE = [
    ("empty", "", "pattern_empty"),
    ("too-long-before-charset", chr(0xE9) * 300, "pattern_too_long"),
    ("charset", "a" + chr(0xE9), "pattern_not_ascii_printable"),
    ("too-long-before-syntax", "(" * 300, "pattern_too_long"),
    ("length-counts-anchors", "^" + "a" * 255 + "$", "pattern_too_long"),
    ("depth-before-unbalanced", "(((((a", "pattern_nesting_too_deep"),
    ("count-before-later-unbalanced", "a{300}(", "pattern_repeat_count_too_large"),
    ("unbalanced-before-later-count", "(a{300}", "pattern_repeat_count_too_large"),
    ("unbounded-count-before-stacked", "a*a*a*a**", "pattern_unbounded_too_many"),
    ("stacked-first", "a**a*a*a*", "pattern_quantifier_not_greedy"),
    ("operator-before-range-order", "[z-a&&]", "pattern_class_set_operator"),
    ("operator-in-range", "[a--b]", "pattern_class_set_operator"),
    ("leading-zero", "a{01}", "pattern_quantifier_leading_zero"),
    ("bounds-order", "a{3,2}", "pattern_quantifier_bounds_order"),
    ("empty-branch", "a|", "pattern_empty_branch"),
    ("empty-body-anchors", "^$", "pattern_empty_branch"),
    ("unbalanced", "(a", "pattern_unbalanced_group"),
    ("stray-close", "a)", "pattern_unbalanced_group"),
    ("escape", "\\d", "pattern_escape_unsupported"),
    ("escape-in-class", "[\\d]", "pattern_escape_unsupported"),
    ("group-extension", "(?i)a", "pattern_group_extension"),
    ("negated-class", "[^a]", "pattern_class_negated"),
    ("posix-class", "[[:alpha:]]", "pattern_class_nested_or_posix"),
    ("unbounded-on-group", "(a)*", "pattern_unbounded_on_group"),
    ("anchor-in-the-middle", "a^b", "pattern_anchor_misplaced"),
    ("end-anchor-in-the-middle", "a$b", "pattern_anchor_misplaced"),
    ("quantifier-without-atom", "*a", "pattern_metachar_unexpected"),
    ("product", "(a{200}){6}", "pattern_repeat_product_too_large"),
    ("size", BIG, "pattern_program_too_large"),
    ("size-after-syntax", BIG + "(a", "pattern_unbalanced_group"),
    ("product-beats-size-wherever-it-stands", BIG + "(a{200}){6}", "pattern_repeat_product_too_large"),
    # review F1 of #48: inside a class and inside a repeat construct the order is the explicit rule order C1.. / Q1.., not the reading order
    ("class.C1-before-C2", "[^a&&b]", "pattern_class_set_operator"),
    ("class.C1-before-range-order", "[z-a&&b]", "pattern_class_set_operator"),
    ("class.C1-before-escape", "[\\d--]", "pattern_class_set_operator"),
    ("class.C1-sees-an-unterminated-class", "[ab&&", "pattern_class_set_operator"),
    ("class.escaped-pair-is-no-operator", "[a\\-\\-b]", ""),
    ("class.C2-before-C3", "[^[", "pattern_class_negated"),
    ("class.C3-first-error-wins", "[\\d z-a]", "pattern_escape_unsupported"),
    ("class.range-order-before-later-escape", "[z-a\\d]", "pattern_class_range_order"),
    ("class.escape-in-range-end-before-order", "[z-\\d]", "pattern_escape_unsupported"),
    ("class.nested-before-range-order", "[z-[a]", "pattern_class_nested_or_posix"),
    ("class.empty-only-when-first", "[]a]", "pattern_class_empty"),
    ("class.unterminated", "[ab", "pattern_class_unterminated"),
    ("repeat.Q3-before-Q4", "a{03,2}", "pattern_quantifier_leading_zero"),
    ("repeat.Q4-before-count", "a{300,2}", "pattern_quantifier_bounds_order"),
    ("repeat.Q3-before-count", "a{01,300}", "pattern_quantifier_leading_zero"),
    ("repeat.Q5-count-before-count-limit", "a*a*a*a{256,}", "pattern_unbounded_too_many"),
    ("repeat.Q5b-count-limit-on-open-brace", "a{256,}", "pattern_repeat_count_too_large"),
    ("repeat.Q5-then-on-group", "(a){2,}", "pattern_unbounded_on_group"),
    ("repeat.Q1-before-Q2", "a*a*a*(a)*", "pattern_unbounded_too_many"),
    ("repeat.count-before-product", "(a{256}){5}", "pattern_repeat_count_too_large"),
    ("repeat.count-before-stacked", "a{300}*", "pattern_repeat_count_too_large"),
    ("repeat.product-before-stacked", "(a{200}){6}*", "pattern_repeat_product_too_large"),
    ("repeat.stacked-after-brace", "a{2}{3}", "pattern_quantifier_not_greedy"),
    ("repeat.stacked-after-question", "a??", "pattern_quantifier_not_greedy"),
    ("repeat.malformed", "a{,3}", "pattern_quantifier_malformed"),
    ("repeat.malformed-unclosed", "a{3", "pattern_quantifier_malformed"),
    ("group.extension-before-depth", "(((((?:a)))))", "pattern_group_extension"),
    ("group.depth-5", "((((((a", "pattern_nesting_too_deep"),
    ("group.empty-before-unbalanced", "(", "pattern_empty_branch"),
    ("anchor.escaped-dollar-is-a-literal", "a\\$", ""),
    ("anchor.double-backslash-then-dollar-is-the-anchor", "a\\\\$", ""),
    ("anchor.escaped-dollar-after-class", "[a]\\$", ""),
    ("size.zero-repeat-of-a-big-subtree", "(" + "a{0,255}" * 5 + "){0}b", ""),
    ("accepted", "^[a-z]{1,8}$", ""),
]


def codes_of(pats):
    return [C.classify(p)[0] for p in pats]


def precedence():
    for name, p, want in PRECEDENCE:
        got, detail = C.classify(p)
        ok = got == want
        print("%-8s %-44s want %-36s got %-36s %s" % ("ok" if ok else "FAIL", name, want or "(accepted)", got or "(accepted)", detail[:60]))
        expect("precedence.%s" % name, ok, "want %s got %s" % (want, got))


def boundary():
    ok_p = "a{0,255}" * 4 + "a{0,4}"          # PI = 4 x 510 + 8 = 2048
    bad_p = ok_p + "a"                          # 2049
    for lab, p, want in (("PI == PI_MAX", ok_p, ""), ("PI == PI_MAX + 1", bad_p, "pattern_program_too_large")):
        got, detail = C.classify(p)
        pi = C.size(N.parse_ast(p)); st = N.Matcher(p).states
        print("%-8s %-22s PI=%d states=%d got %s" % ("ok" if got == want else "FAIL", lab, pi, st, got or "(accepted)"))
        expect("boundary.%s" % lab, got == want, "want %s got %s" % (want, got))
        expect("boundary.%s.pi-equals-states-1" % lab, st == pi + 1 or C.PLANT == "size-undercount", "PI=%d states=%d" % (pi, st))
    expect("boundary.constants", C.PI_MAX == 2048, "the probe's patterns are built for PI_MAX = 2048")


def value():
    p = "a{0,255}"
    cases = [("match", p, "a" * 255, "match"), ("mismatch", p, "b", "pattern_value_mismatch"),
             ("too-long-and-matching-prefix", p, "a" * 300, "pattern_value_too_long"),
             ("too-long-and-not-matching", p, "b" * 300, "pattern_value_too_long"),
             ("boundary-256", "a{0,255}a?", "a" * 256, "match"), ("boundary-257", "a{0,255}a?", "a" * 257, "pattern_value_too_long"),
             ("lone-surrogate-first", p, "a" * 300 + chr(0xD800), "pattern_value_not_unicode_scalar")]
    for name, pat, v, want in cases:
        got = C.check_value(pat, v)
        print("%-8s value.%-32s want %-36s got %s" % ("ok" if got == want else "FAIL", name, want, got))
        expect("value.%s" % name, got == want, "want %s got %s" % (want, got))


def soup(n, seed):
    rnd = random.Random(seed); al = "ab01()[]{}*+?|^$\\.-,&~:dA9"
    return ["".join(rnd.choice(al) for _ in range(rnd.randrange(1, 14))) for _ in range(n)]


def corpus():
    ps = [c["p"] for c in PE.construct_cases()] + [c["p"] for c in PE.limit_cases()] + [p for _, p, _ in PRECEDENCE] + soup(30000, 20261122)
    return ps


def totality_coverage():
    reached = {}; bad = []; accepted = 0; refused = 0; rows_hit = set()
    for p in corpus():
        code, detail = C.classify(p)
        if code == "":
            accepted += 1; continue
        refused += 1
        if code in ("UNMAPPED", "AMBIGUOUS"):
            bad.append((p, code, detail)); continue
        reached.setdefault(code, p)
        rows_hit.update(C.rows_of(detail))
    print("corpus: %d accepted, %d refused (%d distinct codes), %d refused without exactly one code" % (accepted, refused, len(reached), len(bad)))
    for p, code, detail in bad[:5]:
        print("FAIL-EXPECT totality %s %r %s" % (code, p[:50], detail))
    expect("totality", not bad, "%d refusals without exactly one code" % len(bad))
    for c in C.ALL_CODES:
        if c.startswith("pattern_value") or c == "pattern_program_too_large":
            continue
        print("%-9s %-36s %s" % ("reached" if c in reached else "UNREACHED", c, repr(reached.get(c, ""))[:50]))
    dead = [C.ROWS[i] for i in range(len(C.ROWS)) if i not in rows_hit]
    for rx, c in dead:
        print("UNREACHED-ROW %-36s %s" % (c, rx))
    print("rows of the mapping table: %d, reached by the corpus: %d" % (len(C.ROWS), len(rows_hit)))


def digest():
    ps = [p for _, p, _ in PRECEDENCE] + soup(3000, 99) + [c["p"] for c in PE.construct_cases()]
    return hashlib.sha256("\n".join("%s=%s" % (p, C.classify(p)[0]) for p in ps).encode("utf-8", "replace")).hexdigest()


# ---------------------------------------------------------------- review F3 of #48: PI per construct (hand-derived), no overflow, zero repeats
PI_TABLE = [   # (expression, PI derived by hand from the recurrence of section 2.1)
    ("a", 1), (".", 1), ("[a-z]", 1), ("ab", 2), ("a|b", 3), ("(a|b)", 3), ("a|b|c", 4), ("(a|b)(c|d)", 6),
    ("a?", 2), ("a*", 2), ("a+", 3), ("a{3}", 3), ("a{2,5}", 8), ("a{2,}", 4), ("a{0}b", 1), ("a{0,255}", 510),
    ("(ab){2}", 4), ("(a|b){0,2}", 8), ("(a{2}){3}", 6), ("((a?){2}){3}", 12),
]
PI_INTERMEDIATE_MAX = 512000      # the bound of section 2.1: 256 text characters x a factor of at most 2000 per character


def traced(node, acc):
    """PI with every intermediate product and sum recorded in acc (the bottom-up evaluation an implementation would do)"""
    k = node[0]
    if k in ("lit", "any", "cls"):
        return 1
    if k == "cat":
        v = 0
        for c in node[1]:
            v += traced(c, acc); acc.append(v)
        return v
    if k == "alt":
        v = 1
        for c in node[1]:
            v += traced(c, acc); acc.append(v)
        return v
    _, inner, lo, hi = node
    x = traced(inner, acc)
    if hi is None:
        t = (lo + 1) * x; acc.append(t); v = 1 + t
    else:
        a = lo * x; b = (hi - lo) * (1 + x); acc += [a, b]; v = a + b
    acc.append(v)
    return v


def size_table():
    for p, want in PI_TABLE:
        tree = N.parse_ast(p); got = C.size(tree); st = N.Matcher(p).states
        ok = got == want and st == want + 1
        print("%-8s PI(%s) = %d (hand-derived %d), NFA states %d" % ("ok" if ok else "FAIL", p, got, want, st))
        expect("pi.%s" % p, ok, "PI %d, hand %d, states %d" % (got, want, st))
    code, detail = C.classify("(" + "a{0,255}" * 5 + "){0}b")
    st = N.Matcher("(" + "a{0,255}" * 5 + "){0}b").states
    print("%-8s zero repeat of a big subtree: accepted=%s (%s), NFA states %d" % ("ok" if code == "" and st == 2 else "FAIL", code == "", detail, st))
    expect("pi.zero-repeat-big-subtree", code == "" and st == 2, "code %r states %d" % (code, st))


def pi_bound():
    import limit_space as L
    pats = [p for p, _ in PI_TABLE] + [p for _, p, w in PRECEDENCE if w == "" and p] + [L.solve_pat(), "(a{255,}){0,3}", "((a{255,}){0,3}|b{250}){0,4}", "((((a|b){0,4}|c){0,4}|d){0,4}|e){0,4}"] + soup(30000, 5)
    top = 0; n = 0
    for p in pats:
        if not C.S.parse(p).ok:        # tiers 1 and 2 only: the bound must hold for everything that reaches tier 3, also above PI_MAX
            continue
        acc = []; traced(N.parse_ast(p), acc); n += 1
        top = max(top, max(acc) if acc else 0)
    print("%-8s PI bound: %d expressions that pass tiers 1 and 2 (also above PI_MAX), the largest intermediate value of a bottom-up evaluation is %d (bound %d = 256 x 2000; the DP optimum is among them)" % ("ok" if top <= PI_INTERMEDIATE_MAX else "FAIL", n, top, PI_INTERMEDIATE_MAX))
    expect("pi.bound", top <= PI_INTERMEDIATE_MAX, "largest intermediate %d" % top)
    expect("pi.fits-in-32-bit", top < 2 ** 31)


# ---------------------------------------------------------------- review F1 of #48: the text alone determines the verdict (a second implementation from the specification text)
FRAG_ATOMS = ["a", "b", ".", "[a-z]", "[0-9a]", "\\.", "\\d", "[^a]", "[a&&b]", "[z-a]", "[a-\\d]", "[[:x:]]", "[]", "[a", "[a\\-\\-b]", "[a--b]", "[~~]", "^", "$", "\\", "*", "{", "}", "]", "|"]
FRAG_QUANT = ["", "", "", "*", "+", "?", "{2}", "{0,3}", "{2,}", "{300}", "{256,}", "{01}", "{3,2}", "{,2}", "{", "{0}", "{250}", "{4}", "??", "{2}{3}", "*?"]


def gen(rnd, depth):
    parts = []
    for _ in range(rnd.randrange(1, 4)):
        if depth > 0 and rnd.random() < 0.35:
            inner = gen(rnd, depth - 1)
            a = "(" + ("?:" if rnd.random() < 0.05 else "") + inner + ("" if rnd.random() > 0.03 else ")") + ")"
            if rnd.random() < 0.05:
                a = a[:-1]
        else:
            a = rnd.choice(FRAG_ATOMS)
        parts.append(a + rnd.choice(FRAG_QUANT))
    s = "".join(parts)
    if rnd.random() < 0.15:
        s += "|" + gen(rnd, depth - 1) if depth > 0 else ""
    return s


def differential(n=40000, seed=20261123):
    rnd = random.Random(seed)
    ps = [p for _, p, _ in PRECEDENCE] + soup(30000, 20261122) + [gen(rnd, 4) for _ in range(n)] + [c["p"] for c in PE.construct_cases()]
    dis = []; refused = set()
    for p in ps:
        a, b = C.classify(p)[0], SP.classify(p)
        if b:
            refused.add(b)
        if a != b:
            dis.append((p, a, b))
    for p, a, b in dis[:8]:
        print("FAIL-EXPECT differential %r prototype=%s spec=%s" % (p[:60], a or "(accepted)", b or "(accepted)"))
    print("%-8s differential: %d expressions (precedence cases, %d random texts, %d generated multi-defect texts, the constructs), %d disagreements between the prototype and the implementation of the text; %d distinct codes seen" % ("ok" if not dis else "FAIL", len(ps), 30000, n, len(dis), len(refused)))
    expect("differential", not dis, "%d disagreements" % len(dis))


def determinism():
    ds = {}
    for seed in ("0", "1", "2", "424242"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        r = subprocess.run([sys.executable, os.path.abspath(__file__), "--digest"], capture_output=True, text=True, env=env, timeout=600)
        if r.returncode != 0:
            print("INCOMPLETE: the digest child failed: %s" % (r.stderr or r.stdout)[-300:]); sys.exit(2)
        ds[seed] = r.stdout.strip()
    same = len(set(ds.values())) == 1
    print("%-8s determinism: %d hash seeds -> %d distinct digest(s) %s" % ("ok" if same else "FAIL", len(ds), len(set(ds.values())), list(ds.values())[0][:16]))
    expect("determinism", same, str(ds))


if __name__ == "__main__":
    if "--digest" in sys.argv:
        print(digest()); sys.exit(0)
    try:
        print("## precedence"); precedence()
        print("## boundary"); boundary()
        print("## value"); value()
        print("## totality and coverage"); totality_coverage()
        print("## PI per construct, zero repeats, bound"); size_table(); pi_bound()
        print("## differential against the implementation of the specification text"); differential()
        print("## determinism"); determinism()
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
    if fails:
        print("FAILED: %s" % ", ".join(fails)); sys.exit(1)
    print("all expectations held"); sys.exit(0)
