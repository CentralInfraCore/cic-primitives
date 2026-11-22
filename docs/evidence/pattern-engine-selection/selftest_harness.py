"""Shows that the parity gate of selection_probe.py can FAIL, and that it fails FOR THE RIGHT REASON (review finding F2 of PR #47).
 1. POSITIVE CONTROL: the UNMODIFIED copy, in the same environment and with the same arguments, must exit 0 (with the canaries and without). If it does not, nothing below means anything and the
    self-test fails.
 2. PLANTED DEFECTS: one defect at a time is planted into a COPY of the Python-side files. A defect counts as DETECTED only when the probe reports a MEASURED failure that names the planted engine:
    exit 3 with a failed CANARY in a planted engine's runner, or exit 1 with a FAIL-EXPECT / DISAGREE line in which the planted engine(s) deviate (from the expectation, or from the unmodified Go
    runner). Exit 2 (INCOMPLETE: missing interpreter, crashed runner, wrong answer count) or a crash is an INFRASTRUCTURE FAILURE and is never a detection. Each defect runs twice: with the canaries
    (the gate as it runs) and without them (the parity layer alone); the second must be exit 1 with the same evidence. The same defect planted in two or three engines at once is planted too: outputs
    that agree prove nothing, the unmodified engines must still disagree with them.
 3. INFRASTRUCTURE CONTROLS: a missing interpreter, a crashing adapter and a missing runner file must end in exit 2 and be classified INFRASTRUCTURE, not DETECTED.
Usage: selftest_harness.py <python for the run> (the env of selection_probe.py is inherited). Exit 1 if a control fails, a defect is not detected, or an infrastructure failure is counted as detection."""
import os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); PY = sys.argv[1] if len(sys.argv) > 1 else sys.executable
FILES = ("engines.py", "nfa_engine.py", "runner_py.py", "fuzz_gen.py", "selection_probe.py", "construct_expect.py")
NFA_NOWRAP = ("nfa_engine.py", "            cur = nxt\n            if not cur:", "            cur = nxt\n            if acc in cur:\n                return True\n            if not cur:")
RE2_NOWRAP = ("engines.py", 'r = re2.compile(r"\\A(?:%s)\\z" % body)', "r = re2.compile(body)")
M = [("nfa: `.` also matches LF", {"nfa"}, [("nfa_engine.py", '                        ok = ch != "\\n"', "                        ok = True")]),
     ("nfa: prefix match instead of full match", {"nfa"}, [NFA_NOWRAP]),
     ("nfa: class upper bound exclusive", {"nfa"}, [("nfa_engine.py", "any(lo <= o <= hi for lo, hi in arg)", "any(lo <= o < hi or lo == hi == o for lo, hi in arg)")]),
     ("nfa: bounded repeat has one optional copy too few", {"nfa"}, [("nfa_engine.py", "            for _ in range(hi - lo):", "            for _ in range(max(0, hi - lo - 1)):")]),
     ("nfa: an optional copy may be skipped only at the end", {"nfa"}, [("nfa_engine.py", '                self.t[o].append(("eps", None, self.build(inner, cur))); self.t[o].append(("eps", None, nxt))', '                self.t[o].append(("eps", None, self.build(inner, cur)))')]),
     ("nfa: the visit mark is never advanced (a state is visited once per run)", {"nfa"}, [("nfa_engine.py", "o = ord(ch); gen += 1; nxt = []", "o = ord(ch); nxt = []")]),
     ("nfa adapter: refuses every accepted pattern with `?` (a compile failure on an accepted pattern)", {"nfa"}, [("engines.py", "            m = nfa_engine.compile(p)\n", '            m = nfa_engine.compile(p)\n            if "?" in p:\n                raise nfa_engine.Refused("planted")\n')]),
     ("re2g adapter: always answers match (constant engine)", {"re2g"}, [("engines.py", '        return lambda v: r.match(v) is not None\n    if engine == "nfa":', '        return lambda v: True\n    if engine == "nfa":')]),
     ("re2g+re2p adapters: no full-match wrapper (the same defect in two engines)", {"re2g", "re2p"}, [RE2_NOWRAP]),
     ("nfa+re2g+re2p: no full-match wrapper (the same defect in three engines)", {"nfa", "re2g", "re2p"}, [RE2_NOWRAP, NFA_NOWRAP])]
INFRA = [("a missing interpreter for nfa", {"CIC_ENGINE_PY_nfa": "/nonexistent/python3"}, []),
         ("an adapter that crashes (nfa)", {}, [("engines.py", "            m = nfa_engine.compile(p)\n", "            m = nfa_engine.compile(p)\n            raise RuntimeError('planted crash')\n")]),
         ("a missing runner file", {}, [("RM", "runner_py.py", "")])]


def make_copy(edits):
    root = tempfile.mkdtemp(); d = os.path.join(root, "pattern-engine-selection"); os.makedirs(d)
    for f in FILES:
        shutil.copy(os.path.join(HERE, f), d)
    os.symlink(os.path.abspath(os.path.join(HERE, "..", "grammar-pattern-measurement")), os.path.join(root, "grammar-pattern-measurement"))
    for e in edits:
        if e[0] == "RM":
            os.remove(os.path.join(d, e[1])); continue
        f, a, b = e; s = open(os.path.join(d, f), encoding="utf-8").read()
        if s.count(a) != 1:
            return None, "PLANT FAILED (%s: the text to replace is not there exactly once)" % f
        open(os.path.join(d, f), "w", encoding="utf-8").write(s.replace(a, b))
    return (root, d), None


def run(rd, canaries, extra_env=None):
    root, d = rd
    env = dict(os.environ, CIC_ENGINE_GROUPS="parity", CIC_ENGINE_FUZZ="300", CIC_ENGINE_DIR=d, CIC_ENGINE_CANARIES=canaries, **(extra_env or {}))
    out = os.path.join(root, "out" + canaries)
    r = subprocess.run([PY, os.path.join(d, "selection_probe.py"), out], capture_output=True, text=True, env=env)
    par = os.path.join(out, "parity.txt")
    return r.returncode, r.stdout + r.stderr, (open(par, encoding="utf-8").read() if os.path.exists(par) else "")


def evidence(rc, text, parity, planted):
    """Returns ('canary'|'parity', detail) when the run shows a MEASURED failure that names a planted engine, else None."""
    if rc == 3:
        m = re.search(r"CANARY (\S+) failed in (\S+) ", text)
        if m and (m.group(2) in planted):
            return "canary", "%s in %s" % (m.group(1), m.group(2))
        return None
    if rc != 1:
        return None
    for ln in parity.splitlines():
        if ln.startswith("FAIL-EXPECT") or ln.startswith("FAIL-COMPILE") or ln.startswith("DISAGREE"):
            vs = dict(re.findall(r"\b(nfa|re2g|re2p|re|regex|go|rust)=(\w+)", ln))
            ref = re.search(r"want=(\w+)", ln); ref = ref.group(1) if ref else vs.get("go")
            if ln.startswith("FAIL-COMPILE"):
                dev = {k for k, v in vs.items() if v not in ("match", "nomatch")}
            else:
                dev = {k for k, v in vs.items() if v != ref}
            if planted <= dev:
                return "parity", ln[:100]
    return None


bad = 0
base, why = make_copy([])
ctl = {c: run(base, c) for c in ("1", "0")}
for c, (rc, text, par) in ctl.items():
    ok = rc == 0
    print("%-92s canaries=%s exit=%d  %s" % ("POSITIVE CONTROL (unmodified copy, same environment)", c, rc, "OK" if ok else "FAILED: %s" % text[-300:].strip()))
    bad += not ok
if bad:
    print("the positive control failed: no result below can be trusted"); sys.exit(1)
for name, planted, edits in M:
    rd, why = make_copy(edits)
    if rd is None:
        print("%-92s %s" % (name, why)); bad += 1; continue
    r1 = run(rd, "1"); r0 = run(rd, "0")
    e1 = evidence(*r1, planted); e0 = evidence(*r0, planted)
    both = e1 is not None and e0 is not None and e0[0] == "parity"
    note = "with canaries: exit=%d %s; parity alone: exit=%d %s" % (r1[0], ("%s [%s]" % (e1[0], e1[1])) if e1 else "NO EVIDENCE" + (" (INFRASTRUCTURE)" if r1[0] == 2 else ""), r0[0], ("parity [%s]" % e0[1]) if e0 else "NO EVIDENCE" + (" (INFRASTRUCTURE)" if r0[0] == 2 else ""))
    print("%-92s %s  %s" % (name, "DETECTED" if both else "NOT DETECTED", note))
    bad += not both
for name, env, edits in INFRA:
    rd, why = make_copy(edits)
    if rd is None:
        print("%-92s %s" % (name, why)); bad += 1; continue
    rc, text, par = run(rd, "1", env)
    ok = rc == 2 and evidence(rc, text, par, {"nfa"}) is None
    print("%-92s INFRASTRUCTURE CONTROL exit=%d  %s" % (name, rc, "classified INFRASTRUCTURE, not a detection: OK" if ok else "WRONG: an infrastructure failure must be exit 2"))
    bad += not ok
sys.exit(1 if bad else 0)
