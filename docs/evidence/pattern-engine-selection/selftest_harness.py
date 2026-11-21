"""Shows that the parity gate of selection_probe.py can FAIL: one defect at a time is planted into a COPY of the Python-side engine files, the parity group is run against the copy and must
exit 1 (a disagreement, or an INCOMPLETE run when a canary fails). Each defect is run twice: with the canaries (the gate as it runs) and with the canaries switched off (the parity layer alone): both must exit 1. A defect that no case sees would be reported NOT DETECTED. The same defect planted in two engines at once is
planted too: two outputs that agree prove nothing, the other engines must still disagree with them.
Usage: selftest_harness.py <python for the run> (the env of selection_probe.py is inherited). Exit 1 if a defect is not detected."""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); PY = sys.argv[1] if len(sys.argv) > 1 else sys.executable
M = [("nfa: `.` also matches LF", [("nfa_engine.py", '                        ok = ch != "\\n"', "                        ok = True")]),
     ("nfa: prefix match instead of full match", [("nfa_engine.py", "            cur = nxt\n            if not cur:", "            cur = nxt\n            if acc in cur:\n                return True\n            if not cur:")]),
     ("nfa: class upper bound exclusive", [("nfa_engine.py", "any(lo <= o <= hi for lo, hi in arg)", "any(lo <= o < hi or lo == hi == o for lo, hi in arg)")]),
     ("nfa: bounded repeat has one optional copy too few", [("nfa_engine.py", "            for _ in range(hi - lo):", "            for _ in range(max(0, hi - lo - 1)):")]),
     ("nfa: an optional copy may be skipped only at the end", [("nfa_engine.py", '                self.t[o].append(("eps", None, self.build(inner, cur))); self.t[o].append(("eps", None, nxt))', '                self.t[o].append(("eps", None, self.build(inner, cur)))')]),
     ("re2g adapter: always answers match (constant engine)", [("engines.py", '        return lambda v: r.match(v) is not None\n    if engine == "nfa":', '        return lambda v: True\n    if engine == "nfa":')]),
     ("re2g+re2p adapters: no full-match wrapper (the same defect in two engines)", [("engines.py", 'r = re2.compile(r"\\A(?:%s)\\z" % body)', "r = re2.compile(body)")]),
     ("nfa+re2g+re2p: no full-match wrapper (the same defect in three engines)", [("engines.py", 'r = re2.compile(r"\\A(?:%s)\\z" % body)', "r = re2.compile(body)"), ("nfa_engine.py", "            cur = nxt\n            if not cur:", "            cur = nxt\n            if acc in cur:\n                return True\n            if not cur:")])]
bad = 0
for name, edits in M:
    root = tempfile.mkdtemp(); d = os.path.join(root, "pattern-engine-selection"); os.makedirs(d)
    for f in ("engines.py", "nfa_engine.py", "runner_py.py", "fuzz_gen.py", "selection_probe.py"):
        shutil.copy(os.path.join(HERE, f), d)
    os.symlink(os.path.abspath(os.path.join(HERE, "..", "grammar-pattern-measurement")), os.path.join(root, "grammar-pattern-measurement"))
    ok = True
    for f, a, b in edits:
        s = open(os.path.join(d, f), encoding="utf-8").read()
        if s.count(a) != 1:
            print("%-78s PLANT FAILED (%s: the text to replace is not there exactly once)" % (name, f)); ok = False; break
        open(os.path.join(d, f), "w", encoding="utf-8").write(s.replace(a, b))
    if not ok:
        bad += 1; continue
    res = {}
    for canaries in ("1", "0"):
        env = dict(os.environ, CIC_ENGINE_GROUPS="parity", CIC_ENGINE_FUZZ="300", CIC_ENGINE_DIR=d, CIC_ENGINE_CANARIES=canaries)
        r = subprocess.run([PY, os.path.join(d, "selection_probe.py"), os.path.join(root, "out" + canaries)], capture_output=True, text=True, env=env)
        out = r.stdout + r.stderr
        res[canaries] = (r.returncode != 0, "canary" if "CANARY" in out else "parity")
    both = res["1"][0] and res["0"][0]
    print("%-78s with canaries: %-8s parity alone: %-8s %s" % (name, ("caught by " + res["1"][1]) if res["1"][0] else "MISSED", "DETECTED" if res["0"][0] else "MISSED", "DETECTED" if res["1"][0] else "NOT DETECTED"))
    bad += not res["1"][0] or not res["0"][0]
sys.exit(1 if bad else 0)
