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
    open(pa, "wb").write(a if isinstance(a, bytes) else a.encode("utf-8"))
    open(pb, "wb").write(b if isinstance(b, bytes) else b.encode("utf-8"))
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

def swap(ls, prefix, new_line, drop_prefix=None):
    """Replace the first line starting with prefix; optionally drop the lines starting with drop_prefix."""
    out, done = [], False
    for l in ls:
        if not done and l.startswith(prefix):
            out.append(new_line); done = True
        elif drop_prefix and l.startswith(drop_prefix):
            continue
        else:
            out.append(l)
    assert done, prefix
    return out
gb = good.encode("utf-8")
i = gb.index(b"MISSING_MANDATORY")
# F4.2: two outputs that differ in the raw bytes but are equal after a lossy decode (two different invalid UTF-8 bytes)
bad_a = gb[:i] + b"\xff" + gb[i + 1:]
bad_b = gb[:i] + b"\xfe" + gb[i + 1:]
results += [
    run(bad_a, bad_b, "F4.2 raw bytes differ, equal after a lossy decode"),
    run(bad_a, bad_a, "F4.2 the same invalid UTF-8 in both"),
    run(good, good.replace("\n", "\r\n"), "F4.2 equal after line-end normalisation only"),
]
# F4.3: the compile result must be exactly what the inventory expects
k01 = [l for l in lines if l.startswith("K01_mandatory|-|compile|")][0]
garbage = j(swap(lines, "K01_mandatory|-|compile|", "K01_mandatory|-|compile|FAIL", "K01_mandatory|pos"))
garbage = garbage.replace("K01_mandatory|neg_absent|validate|MISSING_MANDATORY@$.a\n", "")
refused_unexpected = j(swap(lines, "K01_mandatory|-|compile|", "K01_mandatory|-|compile|ERR[SCHEMA_INVALID] SCHEMA_INVALID@x", "K01_mandatory|pos"))
refused_unexpected = refused_unexpected.replace("K01_mandatory|neg_absent|validate|MISSING_MANDATORY@$.a\n", "")
k08_ok = j(swap(lines, "K08_max_items|-|compile|", "K08_max_items|-|compile|OK|unevaluated=") .__add__(["K08_max_items|neg_two|validate|OK", "K08_max_items|pos_one|validate|OK"]))
k08_wrong = j(swap(lines, "K08_max_items|-|compile|", "K08_max_items|-|compile|ERR[SCHEMA_INVALID] SCHEMA_INVALID@x"))
results += [
    run(garbage, garbage, "F4.3 a malformed compile result counted as a refusal"),
    run(refused_unexpected, refused_unexpected, "F4.3 a case that must compile was refused"),
    run(k08_ok, k08_ok, "F4.3 the case that must be refused compiled"),
    run(k08_wrong, k08_wrong, "F4.3 the refusal has another code than expected"),
]
print("%d of %d checks as expected" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
