#!/usr/bin/env python3
"""Evidence for docs/en/GRAMMAR-NODE-NAME-PROFILE-DESIGN.md: how the candidate node-name rules behave in three regular-expression flavors, whether a
candidate only WIDENS the current rule, and what the pinned grammar's own checker does with a name.
usage: name_rule_check.py <names.json> <patterns.json> <go-pat-output> <rust-pat-output>
Exit 0 only if Go and Rust agree on every (pattern, name) and every claim stated in the output holds."""
import itertools, json, os, re, subprocess, sys, tempfile
names = json.load(open(sys.argv[1])); pats = json.load(open(sys.argv[2]))
problems = []

def parse(path, label):
    """The exact inventory of one raw output: one line `pattern|index|true` or `...|false` for EVERY (pattern, name index) and nothing else.
    A malformed line, an unknown pattern or index, a value other than true/false, a duplicate and a missing pair are each a problem."""
    got = {}
    for n, line in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
        f = line.split("|")
        if len(f) != 3:
            problems.append("%s line %d is malformed (%d fields): %r" % (label, n, len(f), line[:60])); continue
        p, i, m = f
        if p not in pats:
            problems.append("%s line %d names an unknown pattern %r" % (label, n, p)); continue
        if not (i.isascii() and i.isdigit() and int(i) < len(names) and str(int(i)) == i):
            problems.append("%s line %d names an unknown name index %r" % (label, n, i)); continue
        if m not in ("true", "false"):
            problems.append("%s line %d has the verdict %r, which is not true or false" % (label, n, m)); continue
        if (p, int(i)) in got:
            problems.append("%s line %d repeats (%s, %s)" % (label, n, p, i)); continue
        got[(p, int(i))] = (m == "true")
    for p in pats:
        for i in range(len(names)):
            if (p, i) not in got:
                problems.append("%s misses the pair (%s, %d)" % (label, p, i))
    return got

go_tab, rs_tab = parse(sys.argv[3], "go"), parse(sys.argv[4], "rust")
if problems:
    for p in problems[:20]: print("PROBLEM: " + p)
    print("RESULT: INCONSISTENT")
    sys.exit(1)
if go_tab != rs_tab:
    problems.append("Go and Rust differ on (pattern, name)")
tab = go_tab
import jsonschema
def js(p, n):   # the way the pinned checker applies a pattern: jsonschema (Draft 2020-12), re.search
    return jsonschema.Draft202012Validator({"type": "string", "minLength": 1, "pattern": pats[p]}).is_valid(n)
print("jsonschema", jsonschema.__version__ if hasattr(jsonschema, "__version__") else "?", "| python", sys.version.split()[0])
print("(py-js = jsonschema pattern, i.e. re.search; py-full = re.fullmatch; go/rust = RE2 / regex crate, unanchored-at-newline `$`)")
print("%-14s %-5s %-7s %-8s %-4s %-5s" % ("name", "rule", "py-js", "py-full", "go", "rust"))
diff = []
for p in sorted(x for x in pats if x != "LF"):
    for i, n in enumerate(names):
        a, b, c = js(p, n), bool(re.fullmatch(pats[p], n)), tab[(p, i)]
        print("%-14s %-5s %-7s %-8s %-4s %-5s" % (json.dumps(n)[1:-1][:12] or "(empty)", p, a, b, c, c))
        if not (a == b == c):
            diff.append((p, n, a, b, c))
print()
print("flavor differences (rule, name, py-js, py-full, go=rust):")
for d in diff: print("  ", d[0], json.dumps(d[1]), d[2], d[3], d[4])
only_newline = all(n.endswith("\n") and "\n" not in n[:-1] for _, n, a, b, c in diff)
if not only_newline: problems.append("a flavor difference other than a single trailing line feed")
# the line-feed guard: a pattern `\\n` searched in the name. Its result must not depend on the flavor, and (rule AND NOT guard) must equal a full match in every flavor
for i, n in enumerate(names):
    lf = ("\n" in n)
    if not (js("LF", n) == tab[("LF", i)] == lf):
        problems.append("the line-feed guard differs between flavors for %r" % n)
for p in ("OLD", "A", "C"):
    for i, n in enumerate(names):
        pair_go = tab[(p, i)] and not tab[("LF", i)]
        pair_py = js(p, n) and not js("LF", n)
        if not (pair_go == pair_py == bool(re.fullmatch(pats[p], n))):
            problems.append("the pair (%s, not LF) is not flavor-stable for %r" % (p, n))
print()
print("the pair (rule, and NOT a line feed anywhere) equals a full match in Python search, Python fullmatch, Go and Rust for every listed name and for the rules OLD, A, C: %s" % ("yes" if not [x for x in problems if x.startswith("the pair") or x.startswith("the line-feed")] else "NO"))
# the real checker
here = os.path.dirname(os.path.abspath(__file__))
chk = os.path.join(here, "..", "..", "..", "proposals", "atom-grammar", "check_grammar.py")
base = {"spec": {"identity": {"atomic_ref": "cic:core:Identity@v0.2.0", "kind": "NameProbe", "namespace": "cic:probe", "version": "v0.0.1"},
                 "config_surface": {"aggregate_ref": "cic:core:ConfigSurface@v0.2.0", "nodes": [{"name": None, "shape_type": "opaque"}]}}}
import yaml
print()
print("the pinned grammar's own checker (check_grammar.py) on a one-node composition:")
res = {}
for n in ["abc", "createdBy", "abc\n"]:
    d = json.loads(json.dumps(base)); d["spec"]["config_surface"]["nodes"][0]["name"] = n
    with tempfile.TemporaryDirectory() as t:
        f = os.path.join(t, "c.yaml"); open(f, "w").write(yaml.safe_dump(d))
        r = subprocess.run([sys.executable, chk, f], capture_output=True, text=True)
    res[n] = r.returncode
    print("  %-12s exit %d  %s" % (json.dumps(n)[1:-1], r.returncode, "accepted" if r.returncode == 0 else "refused"))
# the documented behavior of the V1 checker (design section 2, point 5; decision O3: recorded, not repaired). A change of ANY of the three results fails
# this check on purpose: the document states it, so a change must be a conscious, documented one.
DOCUMENTED_V1_CHECKER = {"abc": 0, "createdBy": 1, "abc\n": 0}
for n, want in DOCUMENTED_V1_CHECKER.items():
    if res[n] != want:
        problems.append("the V1 checker's documented behavior changed for %r: exit %d, documented %d (the design document must be revisited)" % (n, res[n], want))
if res["abc"] != 0 or res["createdBy"] == 0:
    problems.append("the checker does not behave as the baseline of the design assumes (abc accepted, createdBy refused)")
print("  => a name with a trailing line feed is %s by the current checker" % ("ACCEPTED" if res["abc\n"] == 0 else "refused"))
# bounded exhaustive: the candidate A only widens the current rule (fullmatch semantics), and the added names are exactly those with an upper-case letter
print()
alpha = ["a", "b", "Z", "Q", "0", "_", "-", " ", "\n", "é"]
A_BOUNDED = os.environ.get("NAME_RULE_BOUNDED_A", pats["A"])   # test hook of selftest_name_rule_check.py only
old, new = re.compile(pats["OLD"]), re.compile(A_BOUNDED)
count = widen = added = 0; bad_widen = []; bad_added = []
for L in range(1, 6):
    for t in itertools.product(alpha, repeat=L):
        s = "".join(t); count += 1
        o, a = bool(old.fullmatch(s)), bool(new.fullmatch(s))
        if o and not a: bad_widen.append(s)
        if a and not o:
            added += 1
            if not re.search(r"[A-Z]", s): bad_added.append(s)
print("bounded exhaustive check, alphabet %s, length 1..5: %d strings" % (json.dumps("".join(alpha))[1:-1], count))
print("  names valid under OLD but not under A (must be none): %d" % len(bad_widen))
print("  names valid under A but not under OLD: %d; of those without an upper-case letter (must be none): %d" % (added, len(bad_added)))
pair_bad = [s for s in ("".join(t) for L in range(1, 6) for t in itertools.product(alpha, repeat=L))
            if (bool(re.search(A_BOUNDED, s)) and "\n" not in s) != bool(new.fullmatch(s))]
print("  (A searched, and no line feed) differs from a full match of A: %d strings (must be none)" % len(pair_bad))
if pair_bad: problems.append("the pair (A, not LF) is not a full match in the bounded space")
# the V1 checker's actual language (re.search of the V1 pattern) is the V1 rule plus ONE line feed after a valid name; V2 refuses exactly those extra names
OLD_BOUNDED = os.environ.get("NAME_RULE_BOUNDED_OLD", pats["OLD"])     # test hook of selftest_name_rule_check.py only
oldb = re.compile(OLD_BOUNDED)
lang_bad = []; extra = 0; v2_refuses_other = []
for L in range(1, 6):
    for t in itertools.product(alpha, repeat=L):
        s_ = "".join(t)
        checker = bool(re.search(OLD_BOUNDED, s_))
        rule = bool(oldb.fullmatch(s_))
        plus_lf = s_.endswith("\n") and bool(oldb.fullmatch(s_[:-1]))
        if checker != (rule or plus_lf): lang_bad.append(s_)
        if checker and not rule: extra += 1
        v2 = bool(new.fullmatch(s_)) and "\n" not in s_
        if checker and not v2 and not plus_lf: v2_refuses_other.append(s_)
print("the V1 checker's search language = the V1 rule plus one line feed after a valid name, bounded exhaustive: %d differences (must be none); the extra names: %d" % (len(lang_bad), extra))
print("names the V1 checker accepts and V2 refuses, other than that extra language (must be none): %d" % len(v2_refuses_other))
if lang_bad: problems.append("the V1 checker's search language is not the V1 rule plus one line feed after a valid name")
if v2_refuses_other: problems.append("V2 refuses a name the V1 checker accepts that is not a valid name plus one line feed")
if bad_widen or bad_added: problems.append("rule A is not a pure widening that only adds upper-case letters after the first character")
print()
for p in problems: print("PROBLEM: " + p)
print("RESULT: " + ("INCONSISTENT" if problems else "CONSISTENT"))
sys.exit(1 if problems else 0)
