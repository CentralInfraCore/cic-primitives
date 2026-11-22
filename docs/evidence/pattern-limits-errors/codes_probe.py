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
        print("## determinism"); determinism()
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
    if fails:
        print("FAILED: %s" % ", ".join(fails)); sys.exit(1)
    print("all expectations held"); sys.exit(0)
