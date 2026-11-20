#!/usr/bin/env python3
"""Negative tests of verify_measurement.py: every planted defect in the outputs must make it fail, and the real pair must pass.
usage: selftest_verify.py <cases-dir> <go-output> <rust-output>"""
import os, subprocess, sys, tempfile
cases, go, rs = sys.argv[1:4]
here = os.path.dirname(os.path.abspath(__file__))
tool = os.path.join(here, "verify_measurement.py")
good = open(go, encoding="utf-8").read()
lines = good.split("\n")[:-1]
def run(a, b, label, expect_fail=True):
    d = tempfile.mkdtemp()
    pa, pb = os.path.join(d, "a"), os.path.join(d, "b")
    open(pa, "w", encoding="utf-8").write(a)
    open(pb, "w", encoding="utf-8").write(b)
    r = subprocess.run([sys.executable, tool, cases, pa, pb, "--quiet"], capture_output=True, text=True)
    failed = r.returncode != 0
    ok = failed == expect_fail
    print("%-62s -> %s (%s)" % (label, "refused" if failed else "ACCEPTED", "as expected" if ok else "UNEXPECTED"))
    return ok
j = lambda ls: "\n".join(ls) + "\n"
results = [
    run(good, good, "the real pair", expect_fail=False),
    run("", "", "two EMPTY outputs (byte-identical)"),
    run(j(lines[:-5]), j(lines[:-5]), "two outputs truncated by 5 lines, identically"),
    run(good.rstrip("\n"), good.rstrip("\n"), "two outputs without the final newline, identically"),
    run(j([l for l in lines if not l.startswith("K10_")]), j([l for l in lines if not l.startswith("K10_")]), "a whole case missing from both, identically"),
    run(j([l for l in lines if "|pos_present|" not in l or not l.startswith("K01_")]), j([l for l in lines if "|pos_present|" not in l or not l.startswith("K01_")]), "one document missing from both, identically"),
    run(j(lines + [lines[3]]), j(lines + [lines[3]]), "a duplicated line in both"),
    run(j(lines + ["K99_unknown|-|compile|OK|unevaluated="]), j(lines + ["K99_unknown|-|compile|OK|unevaluated="]), "an unknown case in both"),
    run(j(lines + ["K08_max_items|pos_one|validate|OK"]), j(lines + ["K08_max_items|pos_one|validate|OK"]), "a document line for a refused schema, in both"),
    run(good, j(lines[:-1]), "outputs that differ by one line"),
    run(good, good.replace("MISSING_MANDATORY", "MISSING_MANDATORX", 1), "outputs that differ by one character"),
    run(good, "", "one output empty"),
]
print("%d of %d checks as expected" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
