"""Shows that the self-test of scan_integers.py can fail: plants the defects of review #44 F1 (and each layer alone) into a copy of the scanner and requires
the self-test to go red where it must. The scanner has overlapping layers (defense in depth), so a SINGLE removed layer may be masked by another one: that
is reported as MASKED, not as detected; the combinations that stand for the reviewed defect must be DETECTED. Usage: selftest_mutants.py <python> """
import os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); PY = sys.argv[1] if len(sys.argv) > 1 else sys.executable
src = open(os.path.join(HERE, "scan_integers.py"), encoding="utf-8").read()
M = {
 "rc": ('    if r.returncode != 0:\n        raise Incomplete(', '    if False:\n        raise Incomplete('),
 "empty": ('    if not data.strip():\n        raise Incomplete("%s is empty" % name)\n', ''),
 "nodocs": ('    if not docs or not all(isinstance(d, (dict, list)) for d in docs):\n        raise Incomplete(', '    if False:\n        raise Incomplete('),
 "unreadable": ('        raise Incomplete("%s is not readable YAML (%s)" % (name, type(e).__name__))', '        return 0'),
 "need": ('            if p not in names:\n                raise Incomplete(', '            if False:\n                raise Incomplete('),
 "missing": ('    if missing:\n        raise Incomplete(', '    if False:\n        raise Incomplete('),
 "nofixtures": ('        if not files:\n            raise Incomplete(', '        if False:\n            raise Incomplete('),
 "bound >=": ('abs(t[1]) > LIM', 'abs(t[1]) >= LIM'),
 "negatives ignored": ('abs(t[1]) > LIM', 't[1] > LIM'),
}
def run(keys):
    s = src
    for k in keys:
        a, b = M[k]; assert s.count(a) == 1, k; s = s.replace(a, b)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "scan_integers.py"); open(p, "w", encoding="utf-8").write(s)
        return subprocess.run([PY, p, "--self-test"], capture_output=True, text=True).returncode != 0
must = [(("unreadable",), "an unreadable record counted as zero"), (("nofixtures",), "no fixture found tolerated"), (("bound >=",), "bound off by one"),
        (("negatives ignored",), "negative integers ignored"), (("rc", "empty", "nodocs"), "a git or read error counted as zero (the reviewed defect)"),
        (("need", "missing"), "a required record silently not processed"), (("rc", "need", "missing"), "a failed ls-tree not noticed"),
        (("rc", "empty", "nodocs", "unreadable", "need", "missing", "nofixtures"), "every completeness layer removed")]
bad = 0
for keys, what in must:
    ok = run(keys); bad += not ok
    print("%-12s %-62s [%s]" % ("DETECTED" if ok else "NOT DETECTED", what, "+".join(keys)))
for k in ("rc", "empty", "nodocs", "need", "missing"):
    print("%-12s one layer alone: %-45s [%s]" % ("DETECTED" if run((k,)) else "MASKED", "(another layer still refuses)", k))
sys.exit(1 if bad else 0)
