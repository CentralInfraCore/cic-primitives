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
run("the Go output is truncated (an incomplete table)", "incomplete", edit("namepat-go-output.txt", lambda t: "\n".join(t.splitlines()[:-1]) + "\n"))
run("a rule that is not a pure widening (the underscore dropped)", "not a pure widening", None, {"NAME_RULE_BOUNDED_A": "^[a-z][a-zA-Z0-9]*$"})
run("a rule that also adds names without an upper-case letter ('-')", "not a pure widening", None, {"NAME_RULE_BOUNDED_A": "^[a-z][a-zA-Z0-9_-]*$"})
run("the checker is replaced by one that accepts every name", "does not behave as the baseline", lambda d: open(d + "/../../../proposals/atom-grammar/check_grammar.py", "w").write("import sys\nsys.exit(0)\n"))
print("%d of %d checks as expected" % (sum(res), len(res)))
sys.exit(0 if all(res) else 1)
