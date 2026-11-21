"""Shows that the self-test of compat_records.py can fail: one defect at a time is planted into a copy and `--self-test` must go red. Exit 1 if a defect is not detected."""
import os, subprocess, sys, tempfile, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); src = open(os.path.join(HERE, "compat_records.py"), encoding="utf-8").read()
M = [("the 256 code point limit is not applied", "    if not S.parse(expr).ok or len(v) > VALUE_MAX:", "    if not S.parse(expr).ok:"),
     ("the subset check is not applied", "    if not S.parse(expr).ok or len(v) > VALUE_MAX:", "    if len(v) > VALUE_MAX:"),
     ("element-level gaps are not refused", "    if bad:\n", "    if False:\n"),
     ("an expression outside the subset is not refused", "    if outside:\n", "    if False:\n"),
     ("too few values are not refused", "    if n_vals < MIN_VALUES:\n", "    if False:\n"),
     ("a mandatory key missing in an element is not counted", "                if mandatory:\n                    a.missing += 1", "                if mandatory:\n                    pass"),
     ("a null where null is not allowed is not counted", "            if v is None:\n                if not nullable:\n                    a.null_bad += 1", "            if v is None:\n                if not nullable:\n                    pass"),
     ("a null item inside a collection is not counted", "                if it is None:\n                    if not nullable:\n                        a.null_bad += 1", "                if it is None:\n                    if not nullable:\n                        pass"),
     ("a non-string leaf value is not counted", "                    else:\n                        a.type_bad += 1\n                else:", "                    else:\n                        pass\n                else:"),
     ("an element that is not a mapping is not counted", "            if not isinstance(x, dict):\n                a.type_bad += 1; continue", "            if not isinstance(x, dict):\n                continue"),
     ("a collection that is not a list is not counted", "                if not isinstance(v, list):\n                    a.type_bad += 1; continue", "                if not isinstance(v, list):\n                    continue")]
bad = 0
for name, a, b in M:
    if src.count(a) != 1:
        print("%-60s PLANT FAILED" % name); bad += 1; continue
    d = tempfile.mkdtemp(); shutil.copy(os.path.join(HERE, "subset_check.py"), d); open(os.path.join(d, "compat_records.py"), "w", encoding="utf-8").write(src.replace(a, b))
    r = subprocess.run([sys.executable, os.path.join(d, "compat_records.py"), "--self-test"], capture_output=True, cwd=os.path.abspath(os.path.join(HERE, "..", "..", "..")))
    det = r.returncode != 0
    print("%-60s %s" % (name, "DETECTED" if det else "NOT DETECTED")); bad += not det
sys.exit(1 if bad else 0)
