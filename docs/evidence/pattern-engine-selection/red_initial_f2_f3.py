"""RED-initial run for review findings F2 and F3 of PR #47: the PREVIOUS head (d1e0b8c) is extracted from git into a temp directory and run, to show that the weaknesses the review named were real.
 F2: the previous probe, run with a MISSING interpreter for `nfa`, exits non-zero; the previous harness counted every non-zero exit as a detected defect (`r.returncode != 0`).
 F3: the previous decision rule (`dis = len(lin) != 1 or (want is not None and lin != {want})`) cannot fail when ALL linear engines answer compile_error for an accepted pattern that has no
     expectation (a construct or a generated case); the new rules (D) and the 48 construct expectations can. The old rule is reproduced verbatim on a synthetic verdict table: no engine is planted.
Usage: red_initial_f2_f3.py [commit]   (default d1e0b8c630ee586e2b090ec25388b8b14a262564). Needs the env of selection_probe.py for F2."""
import os, shutil, subprocess, sys, tempfile
COMMIT = sys.argv[1] if len(sys.argv) > 1 else "d1e0b8c630ee586e2b090ec25388b8b14a262564"
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=HERE, text=True).strip()
root = tempfile.mkdtemp(); d = os.path.join(root, "pattern-engine-selection"); os.makedirs(d)
for f in ("engines.py", "nfa_engine.py", "runner_py.py", "fuzz_gen.py", "selection_probe.py"):
    open(os.path.join(d, f), "wb").write(subprocess.check_output(["git", "show", "%s:docs/evidence/pattern-engine-selection/%s" % (COMMIT, f)], cwd=REPO))
os.symlink(os.path.join(REPO, "docs", "evidence", "grammar-pattern-measurement"), os.path.join(root, "grammar-pattern-measurement"))
env = dict(os.environ, CIC_ENGINE_GROUPS="parity", CIC_ENGINE_FUZZ="50", CIC_ENGINE_DIR=d, CIC_ENGINE_PY_nfa="/nonexistent/python3")
r = subprocess.run([sys.executable, os.path.join(d, "selection_probe.py"), os.path.join(root, "out")], capture_output=True, text=True, env=env)
print("F2: previous probe with a missing nfa interpreter: exit=%d (the previous harness rule `returncode != 0` calls this DETECTED: %s)" % (r.returncode, "yes" if r.returncode != 0 else "no"))
print("    last line: %s" % ((r.stderr or r.stdout).strip().splitlines() or [""])[-1][:160])
# F3: the previous rule, verbatim, on a synthetic table
lin_verdicts = {"nfa": "compile_error", "re2g": "compile_error", "re2p": "compile_error", "go": "compile_error", "rust": "compile_error"}
lin = {lin_verdicts[e] for e in lin_verdicts}; want = None
dis = len(lin) != 1 or (want is not None and lin != {want})
print("F3: previous rule on an ACCEPTED pattern without an expectation when all five linear engines answer compile_error: dis=%s (a pass)" % dis)
new_flag = any(v not in ("match", "nomatch") for v in lin_verdicts.values())
print("    new rule D (an accepted pattern must compile in every linear engine): failure=%s" % new_flag)
sys.exit(0 if (r.returncode != 0 and not dis and new_flag) else 1)
