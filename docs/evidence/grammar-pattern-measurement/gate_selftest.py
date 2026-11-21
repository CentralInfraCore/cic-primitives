"""Shows that probe_engines.py can fail. Plants defects and requires exit 1 with DISAGREES cases or a failed CANARY (a known-answer case that a constant, wrong or stale runner fails):
  M1  Python matches with $ instead of \\Z (the legacy trailing-line-feed defect), Go and Rust untouched
  M2  the SAME defect in BOTH the Go runner and the Rust runner (they always answer `match`): identical defects in two implementations; two outputs that agree prove nothing
  M3  the SAME defect in both runners the other way (they always answer `nomatch`)
  M4  Go and Rust both match with the unanchored search instead of the full match (the wrapper dropped)
Usage: gate_selftest.py <python> ; env CIC_PROBE_GO, CIC_PROBE_CARGO as for probe_engines.py"""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); PY = sys.argv[1] if len(sys.argv) > 1 else sys.executable
src = open(os.path.join(HERE, "probe_engines.py"), encoding="utf-8").read()
env = dict(os.environ, CIC_PROBE_GROUPS="semantic", CIC_PROBE_REQUIRE="1")


def run(label, driver_src, runners):
    d = tempfile.mkdtemp(); shutil.copy(os.path.join(HERE, "subset_check.py"), d); shutil.copy(os.path.join(HERE, "inventory-output.txt"), d)
    open(os.path.join(d, "probe_engines.py"), "w", encoding="utf-8").write(driver_src)
    e = dict(env, CIC_PROBE_RUNNERS=runners, CARGO_TARGET_DIR=tempfile.mkdtemp())   # a target directory of its own: a mutant binary must never be left where the real runner is built
    r = subprocess.run([PY, os.path.join(d, "probe_engines.py"), os.path.join(d, "out")], capture_output=True, text=True, env=e, timeout=1500)
    n = open(os.path.join(d, "out", "probe-semantic.txt"), encoding="utf-8").read().count("DISAGREES") if os.path.exists(os.path.join(d, "out", "probe-semantic.txt")) else -1
    canary = "CANARY" in (r.stdout + r.stderr)
    hit = r.returncode == 1 and (n > 0 or canary)
    print("%-62s exit=%d disagreeing cases=%d canary=%s  %s" % (label, r.returncode, n, "failed" if canary else "ok", "DETECTED" if hit else "NOT DETECTED"))
    return hit


def mutated_runners(go_edit, rs_edit):
    d = tempfile.mkdtemp(); shutil.copytree(os.path.join(HERE, "runners"), d, dirs_exist_ok=True, ignore=shutil.ignore_patterns("target"))
    for f, (a, b) in (("go/main.go", go_edit), ("rust/src/main.rs", rs_edit)):
        t = open(os.path.join(d, f), encoding="utf-8").read(); assert t.count(a) == 1, (f, a); open(os.path.join(d, f), "w", encoding="utf-8").write(t.replace(a, b))
    return d


ok = True
a = 'return r"\\A(?:%s)%s" % (strip_anchors(p), r"\\Z" if lang == "py" else r"\\z")'
assert src.count(a) == 1
ok &= run("M1 Python uses $ instead of \\Z", src.replace(a, 'return r"\\A(?:%s)%s" % (strip_anchors(p), "$" if lang == "py" else r"\\z")'), os.path.join(HERE, "runners"))
ok &= run("M2 both runners always answer match", src, mutated_runners(("m := re.MatchString(string(in))", "m := re.MatchString(string(in)) || true"), ("let m = re.is_match(&input);", "let m = re.is_match(&input) || true;")))
ok &= run("M3 both runners always answer nomatch", src, mutated_runners(("m := re.MatchString(string(in))", "m := re.MatchString(string(in)) && false"), ("let m = re.is_match(&input);", "let m = re.is_match(&input) && false;")))
ok &= run("M4 both runners drop the full-match wrapper", src.replace('r"\\A(?:%s)%s" % (strip_anchors(p), r"\\Z" if lang == "py" else r"\\z")', 'r"\\A(?:%s)%s" % (strip_anchors(p), r"\\Z" if lang == "py" else "")'), os.path.join(HERE, "runners"))
sys.exit(0 if ok else 1)
