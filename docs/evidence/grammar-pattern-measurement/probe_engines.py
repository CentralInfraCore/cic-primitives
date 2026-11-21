"""Measures what Python (re), Go (regexp, RE2) and Rust (regex crate) do with the expressions of the candidate P1 profile. MEASUREMENT only: no grammar, no checker is changed.

Matching rule under test (the spec's implementation): the expression with its OUTER ^ and $ removed, matched as a FULL match: native string \\A(?:body)\\Z for Python and
\\A(?:body)\\z for Go and Rust. Nothing else is configured (no flags). The legacy column is Python re.search of the ORIGINAL expression: what the jsonschema library does today.
Groups:  semantic  the 9 distinct `pattern` contracts of the measured trees against hand-authored inputs and an independent expected verdict
         constructs  syntax inside and outside the candidate subset: does each engine compile it, and what does it do
         limits     compile limits per engine (repeat count, nesting, expression length, nested repeat)
         timing     worst-case behavior on adversarial input (Python is run under a per-case time limit)
Usage: probe_engines.py <outdir> ; env CIC_PROBE_GO and CIC_PROBE_CARGO name the go and cargo commands (container stand-ins are fine); CIC_PROBE_REQUIRE=1 makes a missing toolchain an error.
Exit 0: every in-subset case agrees with its expectation in all three engines. Exit 1: a disagreement or an incomplete run."""
import json, os, re, shutil, signal, subprocess, sys, tempfile, time, warnings
warnings.filterwarnings("ignore")   # Python warns about constructs outside the subset (nested set, set intersection); the compile verdict is what is recorded
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import subset_check as S

OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
RUNNERS = os.environ.get("CIC_PROBE_RUNNERS", os.path.join(HERE, "runners"))   # the self-test of the gate points this at a copy with a planted defect
ONLY = set(os.environ.get("CIC_PROBE_GROUPS", "semantic,constructs,limits,timing").split(","))
GO = os.environ.get("CIC_PROBE_GO", "go").split(); CARGO = os.environ.get("CIC_PROBE_CARGO", "cargo").split()
LF, CR, NUL, LS, E, ASTRAL = "\n", "\r", "\x00", "\u2028", "\u00e9", "\U0001F600"


def strip_anchors(p):
    a = p.startswith("^"); b = p.endswith("$") and not re.search(r"(?<!\\)(\\\\)*\\\$$", p)
    return p[(1 if a else 0):len(p) - (1 if b else 0)]


def native(p, lang):
    return r"\A(?:%s)%s" % (strip_anchors(p), r"\Z" if lang == "py" else r"\z")


# ---- the 9 distinct pattern contracts of the measured trees (checked against inventory-output.txt below): expression, a valid sample, characters that keep it valid when appended
CONTRACTS = [
    (r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$", "1.2.3", ""),
    (r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})$", "2026-11-02T10:00:00Z", ""),
    (r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$", "2026-11-02", ""),
    (r"^[0-9a-f]{40}$", "a" * 40, ""),
    (r"^sha256:[0-9a-f]{64}$", "sha256:" + "b" * 64, ""),
    (r"^[A-Za-z0-9+/]{43}=$", "A" * 43 + "=", ""),
    (r"^vault:v1:.+$", "vault:v1:abc", "any_but_lf"),
    (r"^[a-z0-9][a-z0-9./_:-]*$", "a0./_:-b", ""),
    (r"^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$", "10.0.0.0/24", ""),
]
VARIANTS = [("valid", lambda s: s, True), ("empty", lambda s: "", False), ("trailing_lf", lambda s: s + LF, False), ("leading_lf", lambda s: LF + s, False),
            ("trailing_cr", lambda s: s + CR, None), ("trailing_crlf", lambda s: s + CR + LF, False), ("double_lf", lambda s: s + LF + LF, False),
            ("trailing_nul", lambda s: s + NUL, None), ("trailing_u2028", lambda s: s + LS, None), ("trailing_e_acute", lambda s: s + E, None),
            ("trailing_astral", lambda s: s + ASTRAL, None), ("truncated", lambda s: s[:-1], None), ("one_more_char", lambda s: s + "0", None)]


def semantic_cases():
    cs, expect = [], {}
    for pi, (p, sample, kind) in enumerate(CONTRACTS):
        for name, f, exp in VARIANTS:
            v = f(sample)
            if exp is None:                      # the independent oracle for the variants whose verdict depends on the expression
                if kind == "any_but_lf" and name in ("trailing_cr", "trailing_nul", "trailing_u2028", "trailing_e_acute", "trailing_astral", "one_more_char", "truncated"):
                    exp = True                   # `.+` takes any code point except LF
                elif name == "truncated" and sample == "1.2.3":
                    exp = False
                elif name == "one_more_char" and p.startswith("^(0|[1-9]"):
                    exp = True                   # 1.2.30 is valid
                elif name == "one_more_char" and p.endswith("*$"):
                    exp = True                   # [a-z0-9./_:-]* takes a '0'
                elif name == "truncated" and p.endswith("*$"):
                    exp = True                   # a0./_:- is still valid
                elif name == "truncated" and p == r"^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$":
                    exp = True                   # 10.0.0.0/2 is valid
                elif name == "one_more_char" and p.endswith("[0-9]{1,2}$"):
                    exp = False                  # /240 has three digits
                elif name == "truncated" and p.endswith(r"(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})$"):
                    exp = False
                elif name == "one_more_char" and p.endswith(r"(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})$"):
                    exp = False                  # ...Z0
                else:
                    exp = False
            cid = "sem.%d.%s" % (pi, name)
            cs.append({"id": cid, "p": p, "input": v}); expect[cid] = exp
    return cs, expect


# ---- constructs: (label, expression, input, in_subset_expected)
CONSTRUCTS = [
    ("literal", "abc", "abc"), ("dot", "a.c", "abc"), ("dot_lf", "a.c", "a\nc"), ("dot_cr", "a.c", "a\rc"), ("dot_u2028", "a.c", "a\u2028c"), ("dot_astral", "a.c", "a" + ASTRAL + "c"),
    ("class", "[a-c]+", "abc"), ("class_dash_end", "[a-]+", "a-"), ("class_escaped_dash", r"[a\-z]+", "a-z"), ("group", "(ab)+", "abab"), ("alternation", "a|b", "b"),
    ("repeat_exact", "a{3}", "aaa"), ("repeat_range", "a{2,3}", "aaaa"), ("repeat_open", "a{2,}", "aaa"), ("optional", "ab?", "a"), ("star", "a*", ""),
    ("escape_dot", r"a\.c", "a.c"), ("escape_backslash", r"a\\c", "a\\c"), ("anchors_outer", "^abc$", "abc"), ("anchor_escaped_dollar", r"^a\$$", "a$"),
    ("class_digit_escape", r"\d+", "123"), ("class_word_escape", r"\w+", "abc"), ("class_space_escape", r"a\sb", "a b"), ("word_boundary", r"\bab", "ab"),
    ("negated_class", "[^a]", "\n"), ("negated_class_b", "[^a]", "b"), ("posix_class", "[[:alpha:]]+", "abc"), ("class_unicode_property", r"\p{L}+", "abc"),
    ("inline_flag_i", "(?i)abc", "ABC"), ("inline_flag_s", "(?s)a.c", "a\nc"), ("flag_x", "(?x)a b", "ab"), ("non_capturing_group", "(?:ab)+", "abab"),
    ("lookahead", "a(?=b)", "a"), ("neg_lookahead", "a(?!b)", "a"), ("lookbehind", "(?<=a)b", "b"), ("named_group_py", "(?P<n>a)", "a"), ("named_group_angle", "(?<n>a)", "a"),
    ("backreference", r"(a)\1", "aa"), ("lazy_star", "a*?", ""), ("lazy_plus", "a+?", "a"), ("possessive", "a++", "aa"), ("lazy_range", "a{1,2}?", "a"),
    ("repeat_out_of_order", "a{2,1}", "a"), ("repeat_lower_missing", "a{,3}", "aa"), ("repeat_literal_brace", "a{", "a{"), ("repeat_brace_text", "a{x}", "a{x}"),
    ("hex_escape", r"\x41", "A"), ("unicode_escape", r"\u0041", "A"), ("newline_escape", r"a\nb", "a\nb"), ("tab_escape", r"a\tb", "a\tb"), ("octal_escape", r"\101", "A"),
    ("anchor_mid_dollar", "a$b", "ab"), ("anchor_mid_caret", "a^b", "ab"), ("anchor_A", r"\Aab", "ab"), ("anchor_z_lower", r"ab\z", "ab"), ("anchor_Z_upper", r"ab\Z", "ab"),
    ("quote_Q", r"\Qa.b\E", "a.b"), ("dollar_before_lf", "ab$", "ab\n"), ("nested_quantifier", "(a+)+", "aaa"), ("empty_alternative", "a|", ""), ("empty_group", "()", ""),
    ("class_range_reversed", "[z-a]", "m"), ("class_with_bracket", r"[\]]", "]"), ("class_leading_bracket", "[]a]", "]"), ("class_intersection", "[a-z&&[^b]]", "a"),
    ("non_ascii_literal", "é", "é"), ("lone_unmatched_paren", "(a", "a"), ("unmatched_close", "a)", "a)"), ("star_at_start", "*a", "a"), ("double_star", "a**", "a"),
]


def construct_cases():
    return [{"id": "con.%s" % l, "p": p, "input": i} for l, p, i in CONSTRUCTS]


def limit_cases():
    cs = []
    for n in (100, 255, 256, 500, 1000, 1001, 2000, 5000, 100000):
        cs.append({"id": "lim.repeat.%d" % n, "p": "a{%d}" % n, "input": ""})
    for n in (4, 8, 16, 32, 64, 128, 200, 250, 251, 500, 1000, 1001, 2000):
        cs.append({"id": "lim.nesting.%d" % n, "p": "(" * n + "a" + ")" * n, "input": "a"})
    for n in (256, 1024, 4096, 65536, 262144):
        cs.append({"id": "lim.length.%d" % n, "p": "a" * n, "input": "a" * n})
    for n in (64, 1000, 5000):
        cs.append({"id": "lim.alternatives.%d" % n, "p": "|".join("w%d" % i for i in range(n)), "input": "w1"})
    for outer, inner in ((10, 10), (30, 30), (100, 100), (255, 255), (1000, 1000)):
        cs.append({"id": "lim.nested_repeat.%dx%d" % (outer, inner), "p": "(a{%d}){%d}" % (inner, outer), "input": "a"})
    for n in (8, 64, 255):
        cs.append({"id": "lim.class_items.%d" % n, "p": "[" + "".join(chr(0x21 + i % 90) if chr(0x21 + i % 90) not in "\\]^-[" else "z" for i in range(n)) + "]", "input": "a"})
    return cs


def timing_cases():
    cs = []
    for n in (20, 24, 28, 32, 36):
        cs.append({"id": "tim.alt_in_plus.%d" % n, "p": "^(a|aa)+$", "input": "a" * n + "b"})
        cs.append({"id": "tim.nested_plus.%d" % n, "p": "^(a+)+$", "input": "a" * n + "b"})
    for n in (128, 256, 512, 1024):          # the candidate rule: at most 3 unbounded quantifiers and a short value: the worst case inside the rule
        cs.append({"id": "tim.consecutive_star3.%d" % n, "p": "^" + "a*" * 3 + "$", "input": "a" * n + "b"})
    for n in (2000, 8000):
        cs.append({"id": "tim.consecutive_star2.%d" % n, "p": "^" + "a*" * 2 + "$", "input": "a" * n + "b"})
    for k in (3, 4, 5):
        for n in (500, 2000, 8000):
            cs.append({"id": "tim.consecutive_star%d.%d" % (k, n), "p": "^" + "a*" * k + "$", "input": "a" * n + "b"})
    for n in (4096, 65536):
        cs.append({"id": "tim.semver_adversarial.%d" % n, "p": CONTRACTS[0][0], "input": "1" * n + "x"})
        cs.append({"id": "tim.vault_long.%d" % n, "p": CONTRACTS[6][0], "input": "vault:v1:" + "x" * n})
        cs.append({"id": "tim.cidr_adversarial.%d" % n, "p": CONTRACTS[8][0], "input": "1." * (n // 2) + "x"})
    return cs


def py_timed(c, limit_s):
    """One case in a child process that is KILLED at the limit: a signal cannot always interrupt the matcher."""
    code = ("import re,sys,time,json,warnings\nwarnings.filterwarnings('ignore')\nc=json.load(sys.stdin)\nr=re.compile(c['native'])\nt=time.perf_counter()\nm=r.match(c['input'])\n"
            "print(('match' if m else 'nomatch'),int((time.perf_counter()-t)*1e9))")
    try:
        r = subprocess.run([sys.executable, "-c", code], input=json.dumps({"native": native(c["p"], "py"), "input": c["input"]}), capture_output=True, text=True, timeout=limit_s)
    except subprocess.TimeoutExpired:
        return ("timeout>%ds" % limit_s, limit_s * 10**9)
    if r.returncode != 0:
        return ("compile_error", 0)
    v, e = r.stdout.split(); return (v, int(e))


def py_run(cases, limit_s=10):
    res = {}
    if limit_s >= 10:                         # the timing group: every case in its own killable child
        return {c["id"]: py_timed(c, limit_s) for c in cases}
    class TO(Exception):
        pass
    def h(*a):
        raise TO()
    signal.signal(signal.SIGALRM, h)
    for c in cases:
        try:
            t = time.perf_counter(); r = re.compile(native(c["p"], "py"))
        except Exception:
            res[c["id"]] = ("compile_error", 0); continue
        except RecursionError:
            res[c["id"]] = ("compile_error", 0); continue
        try:
            signal.alarm(limit_s); t = time.perf_counter()
            m = r.match(c["input"]); e = int((time.perf_counter() - t) * 1e9)
            signal.alarm(0)
            res[c["id"]] = ("match" if m else "nomatch", e)
        except TO:
            res[c["id"]] = ("timeout>%ds" % limit_s, limit_s * 10**9)
    return res


def legacy_run(cases):
    out = {}
    for c in cases:
        try:
            out[c["id"]] = "match" if re.search(c["p"], c["input"]) else "nomatch"
        except Exception:
            out[c["id"]] = "compile_error"
    return out


CANARIES = [{"id": "canary.match", "p": "a+", "input": "aaa", "want": "match"}, {"id": "canary.nomatch", "p": "a+", "input": "aab", "want": "nomatch"},
            {"id": "canary.compile_error", "p": "a(", "input": "a", "want": "compile_error"}, {"id": "canary.lf_refused", "p": "a+", "input": "aa" + LF, "want": "nomatch"}]


def ext_run(kind, cases, tmp):
    """Runs the Go or Rust runner on the cases AND on the canaries (known answers). A runner that is stale (a binary left by another build), constant or wrong
    fails a canary and the run is INCOMPLETE: no result of it is used."""
    f = os.path.join(tmp, "cases-%s.json" % kind)
    json.dump([{"id": c["id"], "native": native(c["p"], "go"), "input_hex": c["input"].encode("utf-8").hex()} for c in cases + CANARIES], open(f, "w"))
    if kind == "go":
        cmd, cwd = GO + ["run", ".", f], os.path.join(RUNNERS, "go")
    else:
        cmd, cwd = CARGO + ["run", "-q", "--locked", "--", f], os.path.join(RUNNERS, "rust")
    if shutil.which(cmd[0]) is None:
        if os.environ.get("CIC_PROBE_REQUIRE") == "1":
            sys.exit("INCOMPLETE: %s is not available" % cmd[0])
        return None
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        sys.exit("INCOMPLETE: the %s runner failed (rc=%d): %s" % (kind, r.returncode, (r.stderr or r.stdout)[-600:]))
    res = {}
    for line in r.stdout.splitlines():
        i, v, e = line.rsplit("|", 2); res[i] = (v, int(e))
    if set(res) != {c["id"] for c in cases + CANARIES}:
        sys.exit("INCOMPLETE: the %s runner answered %d of %d cases" % (kind, len(res), len(cases) + len(CANARIES)))
    for c in CANARIES:
        if res[c["id"]][0] != c["want"]:
            sys.exit("INCOMPLETE: CANARY %s failed in the %s runner (answered %s, expected %s): a stale, constant or wrong runner; no result of it is used" % (c["id"], kind, res[c["id"]][0], c["want"]))
    return {c["id"]: res[c["id"]] for c in cases}


def show(s):
    return s.replace("\n", "\\n").replace("\r", "\\r").replace("\x00", "\\0").replace("\u2028", "\\u2028").encode("ascii", "backslashreplace").decode()[:60]


def main():
    tmp = tempfile.mkdtemp()
    # the contract list must be the inventory's list
    inv = [l.split(None, 4)[4].strip() for l in open(os.path.join(HERE, "inventory-output.txt"), encoding="utf-8") if re.match(r"^(primitives|registry|release-schemas) +contract ", l)]
    inv = {e if len(e) < 90 else None for e in inv}
    long_ones = [p for p, _, _ in CONTRACTS if len(p) >= 90]
    assert {p for p, _, _ in CONTRACTS if len(p) < 90} <= inv and len([e for e in inv if e]) == len(CONTRACTS) - len(long_ones), "CONTRACTS differs from inventory-output.txt"
    bad = 0
    groups = [("semantic", *semantic_cases()), ("constructs", construct_cases(), None), ("limits", limit_cases(), None), ("timing", timing_cases(), None)]
    for name, cases, expect in groups:
        if name not in ONLY:
            continue
        py = py_run(cases, limit_s=10 if name == "timing" else 5)
        go = ext_run("go", cases, tmp); rs = ext_run("rust", cases, tmp)
        if go is None or rs is None:
            print("group %s: Go or Rust toolchain missing, group not complete" % name); bad += 1
        leg = legacy_run(cases) if name != "timing" else {c["id"]: "-" for c in cases}   # no in-process run of the catastrophic cases: the timing group runs only in killable children
        lines = ["%-34s %-12s %-12s %-12s %-12s %s" % ("case", "python_full", "go", "rust", "legacy_search", "expression / input" + ("  [expected]" if expect else ""))]
        for c in cases:
            i = c["id"]
            v = [py[i][0], go[i][0] if go else "-", rs[i][0] if rs else "-"]
            ex = ""
            if expect is not None:
                want = "match" if expect[i] else "nomatch"; ex = "  [%s]" % want
                if any(x != want for x in v):
                    ex += "  <-- DISAGREES"; bad += 1
            elif name == "constructs":
                insub = S.parse(c["p"]).ok
                if insub and len(set(v)) != 1:
                    ex = "  <-- IN THE SUBSET BUT THE ENGINES DISAGREE"; bad += 1
                ex += "  subset=%s" % ("ACCEPT" if insub else "REFUSE")
            if name == "timing":
                el = "  ns py=%s go=%s rust=%s" % (py[i][1], go[i][1] if go else "-", rs[i][1] if rs else "-")
                ex += el
            lines.append("%-34s %-12s %-12s %-12s %-12s %s%s" % (i, v[0], v[1], v[2], leg[i], show(c["p"]) + " | " + show(c["input"]), ex))
        open(os.path.join(OUT, "probe-%s.txt" % name), "w", encoding="utf-8").write("\n".join(lines) + "\n")
        print("%-10s %d cases written" % (name, len(cases)))
    print("disagreements or incomplete groups:", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
