#!/usr/bin/env python3
"""Negative tests of name_rule_check.py: each planted defect must be refused, with its own reason, and the real inputs must be accepted.
usage: selftest_name_rule_check.py   (run from this directory)"""
import json, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
res = []
def run(label, want_reason, mutate=None, env=None):
    root = tempfile.mkdtemp()
    d = root + "/docs/evidence/grammar-node-name-measurement"
    os.makedirs(d)
    for f in ("names.json", "patterns.json", "namepat-go-output.txt", "namepat-rust-output.txt", "name_rule_check.py"):
        shutil.copy(os.path.join(HERE, f), d)
    top = os.path.join(HERE, "..", "..", "..")
    shutil.copytree(os.path.join(top, "proposals", "atom-grammar"), root + "/proposals/atom-grammar", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(top, "schemas"), root + "/schemas")
    if mutate: mutate(d)
    e = dict(os.environ, **(env or {}))
    r = subprocess.run([sys.executable, "-W", "ignore", d + "/name_rule_check.py", d + "/names.json", d + "/patterns.json", d + "/namepat-go-output.txt", d + "/namepat-rust-output.txt"], capture_output=True, text=True, env=e)
    out = r.stdout + r.stderr
    failed = r.returncode != 0
    if want_reason is None:
        ok = not failed
    else:
        ok = failed and want_reason in out
    print("%-66s -> %s (%s)" % (label, "refused" if failed else "accepted", "as expected" if ok else "UNEXPECTED"))
    res.append(ok)
def edit(name, f):
    def go(d):
        text = open(d + "/" + name).read()      # read first: opening for writing truncates the file
        new = f(text)
        assert new != text, "the planted edit changed nothing"
        open(d + "/" + name, "w").write(new)
    return go
run("the real inputs", None)
run("Go and Rust outputs differ in one line", "Go and Rust differ", edit("namepat-rust-output.txt", lambda t: t.replace("A|4|true", "A|4|false", 1)))
run("the Go output is truncated (an incomplete table)", "misses the pair", edit("namepat-go-output.txt", lambda t: "\n".join(t.splitlines()[:-1]) + "\n"))
run("a rule that is not a pure widening (the underscore dropped)", "not a pure widening", None, {"NAME_RULE_BOUNDED_A": "^[a-z][a-zA-Z0-9]*$"})
run("a rule that also adds names without an upper-case letter ('-')", "not a pure widening", None, {"NAME_RULE_BOUNDED_A": "^[a-z][a-zA-Z0-9_-]*$"})
run("the checker is replaced by one that accepts every name", "does not behave as the baseline", lambda d: open(d + "/../../../proposals/atom-grammar/check_grammar.py", "w").write("import sys\nsys.exit(0)\n"))
def both(f):
    def go(d):
        for n in ("namepat-go-output.txt", "namepat-rust-output.txt"):
            edit(n, f)(d)
    return go
# the SAME defect in both outputs: byte identity of the two is no evidence of correctness
run("both outputs: a duplicated line (the second would overwrite)", "repeats", both(lambda t: t + t.splitlines()[0] + "\n"))
run("both outputs: a duplicated line whose verdict differs", "repeats", both(lambda t: t + (lambda f: "|".join(f[:2] + ["false" if f[2] == "true" else "true"]))(t.splitlines()[0].split("|")) + "\n"))
run("both outputs: a verdict that is neither true nor false", "not true or false", both(lambda t: t.replace("A|4|true", "A|4|maybe", 1)))
run("both outputs: an empty verdict", "not true or false", both(lambda t: t.replace("A|4|true", "A|4|", 1)))
run("both outputs: a line of an unknown pattern", "unknown pattern", both(lambda t: t + "ZZ|0|true\n"))
run("both outputs: a line of an unknown name index", "unknown name index", both(lambda t: t + "A|999|true\n"))
run("both outputs: a non-canonical name index (leading zero)", "unknown name index", both(lambda t: t.replace("A|4|true", "A|04|true", 1)))
run("both outputs: a malformed line", "malformed", both(lambda t: t + "garbage\n"))
run("both outputs: the same pair missing", "misses the pair", both(lambda t: "\n".join(l for l in t.splitlines() if not l.startswith("A|4|")) + "\n"))
run("both outputs: empty", "misses the pair", both(lambda t: ""))
# the documented V1 newline behavior of the checker is asserted, not only printed
STUB = "import sys, re, yaml\nd = yaml.safe_load(open(sys.argv[1]))\nn = d['spec']['config_surface']['nodes'][0]['name']\nsys.exit(0 if re.fullmatch(r'^[a-z][a-z0-9_]*$', n) else 1)\n"
run("the checker is repaired (abc\\n now refused): the documented V1 behavior changed", "documented behavior changed", lambda d: open(d + "/../../../proposals/atom-grammar/check_grammar.py", "w").write(STUB))
run("the V1 checker's language is described wrongly (\\Z instead of $)", "search language", None, {"NAME_RULE_BOUNDED_OLD": "^[a-z][a-z0-9_]*\\Z"})
print("%d of %d checks as expected" % (sum(res), len(res)))
sys.exit(0 if all(res) else 1)
