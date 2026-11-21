"""Shows that the vectors of the subset classifier can fail: plants one defect at a time into a copy of subset_check.py and requires selftest_subset.py to go red.
A defect that a second layer of the classifier hides is reported MASKED, never DETECTED. Exit 1 if a defect that must be detected is not."""
import os, subprocess, sys, tempfile, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); src = open(os.path.join(HERE, "subset_check.py"), encoding="utf-8").read()
BS = chr(92)
M = [("escape d allowed", 'ESCAPABLE = set("%s%s.[]()*+?{}|^$-")' % (BS * 2, ""), 'ESCAPABLE = set("%s%s.[]()*+?{}|^$-d")' % (BS * 2, ""), True),
     ("negated class allowed", '            if self.peek() == "^":\n                raise Refused("negated class is not in the subset")\n', "", True),
     ("group extension allowed", '            if self.peek() == "?":\n                raise Refused("group extension \'(?\' is not in the subset")\n', "", True),
     ("lazy quantifier allowed", '        if self.peek() in ("?", "*", "+", "{"):\n            raise Refused("lazy, possessive or stacked quantifier is not in the subset")\n', "", True),
     ("length limit removed", '        if st["length"] > LIMITS["length"]:', "        if False:", True),
     ("repeat limit removed", '        if st["max_repeat"] > LIMITS["repeat"]:', "        if False:", True),
     ("depth limit removed", '        if st["depth"] > LIMITS["depth"]:', "        if False:", True),
     ("unbounded-count limit removed", '        if st["unbounded"] > LIMITS["unbounded"]:', "        if False:", True),
     ("repeat-product limit removed", '        if st["repeat_product"] > LIMITS["repeat_product"]:', "        if False:", True),
     ("unbounded quantifier on a group allowed (the * + branch)", '                if kind == "group":\n                    raise Refused("an unbounded quantifier on a group (resource rule: it may only follow a single atom)")\n        elif c == "{":', "        elif c == \"{\":", True),
     ("non-ASCII allowed", "        if any(not (0x20 <= ord(ch) <= 0x7E) for ch in p):", "        if False:", True),
     ("empty pattern allowed", '        if not p:\n            raise Refused("empty pattern")\n', "", True),
     ("class set operators allowed", '            for op in ("&&", "--", "~~"):', '            for op in ():', True),
     ("only && refused (-- and ~~ allowed)", '("&&", "--", "~~")', '("&&",)', True),
     ("leading zero in a repetition count allowed", '                if num and len(num) > 1 and num[0] == "0":', "                if False:", True),
     ("empty alternative allowed", '        if self.i == start:\n            raise Refused("an empty alternative', '        if False:\n            raise Refused("an empty alternative', True),
     ("anchor in the middle allowed (explicit check only)", '        if "^" in re.sub(', '        if False and "^" in re.sub(', False)]   # masked: the atom rule refuses '^' and '$' first
bad = 0
for name, a, b, must in M:
    if src.count(a) != 1:
        print("%-62s PLANT FAILED (the text to replace is not in subset_check.py exactly once)" % name); bad += 1; continue
    d = tempfile.mkdtemp(); shutil.copy(os.path.join(HERE, "selftest_subset.py"), d); open(os.path.join(d, "subset_check.py"), "w", encoding="utf-8").write(src.replace(a, b))
    det = subprocess.run([sys.executable, os.path.join(d, "selftest_subset.py")], capture_output=True).returncode != 0
    print("%-62s %s" % (name, "DETECTED" if det else ("MASKED (a second layer refuses it)" if not must else "NOT DETECTED")))
    bad += (must and not det)
sys.exit(1 if bad else 0)
