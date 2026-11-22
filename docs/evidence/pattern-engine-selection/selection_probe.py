"""Engine selection for the pattern profile (P1, O5): compares the candidates on parity, running time and memory. MEASUREMENT only: no grammar, checker, Forms or verifier changes.
Candidates: Python-side  re (baseline), regex, re2g (google-re2), re2p (pyre2, silent fallback turned off), nfa (own linear-time evaluator, nfa_engine.py);  native  go (regexp), rust (regex crate).
Groups (CIC_ENGINE_GROUPS, default all):
  parity     the 117 semantic cases + the in-subset constructs (hand-authored, independent expectation) + a seeded differential fuzz of generated in-subset patterns: the five linear-time engines
             (nfa, re2g, re2p, go, rust) must agree on EVERY case; `re` and `regex` run only the hand-authored cases (backtracking: not run on generated patterns by design)
  timing     the 46 timing cases of the profile probe + cases at the profile's size limits (value 256 code points); Python-side engines that hang are killed at the limit and reported
  bench      compile time, match time and peak memory (above an empty-pattern baseline of the same engine), one process per (engine, case)
  constructs what each engine does with the 84 probed constructs (defense in depth: the closed-subset classifier stands in front of every engine)
Fail-closed: a missing interpreter or toolchain is an error (CIC_ENGINE_REQUIRE=1 is implied), a runner that fails a CANARY (known-answer case) makes the run INCOMPLETE, exit 1.
Env: CIC_ENGINE_PY_<name> = interpreter of the engine (re, regex, re2g, re2p, nfa); CIC_PROBE_GO, CIC_PROBE_CARGO as for probe_engines.py; CIC_ENGINE_DIR = directory with engines.py / nfa_engine.py / runner_py.py
(the self-test points it at a copy with a planted defect); CIC_ENGINE_FUZZ = number of generated patterns (default 1500).
Exit codes (review finding F2: only a MEASURED failure counts as detection): 0 all good; 1 a measured disagreement / expectation failure; 3 a canary (known-answer) case failed in a runner;
2 INCOMPLETE for any other reason (missing interpreter or toolchain, crashed runner, wrong number of answers): an infrastructure failure, never a detection.
Usage: selection_probe.py <outdir>"""
import json, os, re, shutil, subprocess, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.environ.get("CIC_ENGINE_DIR", HERE)
sys.path.insert(0, DIR); sys.path.insert(1, os.path.join(HERE, "..", "grammar-pattern-measurement"))
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
_keep = sys.argv; sys.argv = [sys.argv[0], tempfile.mkdtemp()]
import probe_engines as PE      # the corpora and the Go/Rust drivers of the profile probe (importing it runs nothing)
sys.argv = _keep
import fuzz_gen, construct_expect
EXIT_DISAGREE, EXIT_INFRA, EXIT_CANARY = 1, 2, 3


def die(code, msg):
    print(msg, file=sys.stderr); sys.exit(code)
PYENG = ["re", "regex", "re2g", "re2p", "nfa"]
LINEAR = ["nfa", "re2g", "re2p", "go", "rust"]
BACKTRACKING = ["re", "regex"]
ONLY = set(os.environ.get("CIC_ENGINE_GROUPS", "versions,parity,timing,bench,constructs").split(","))
GO = os.environ.get("CIC_PROBE_GO", "go").split(); CARGO = os.environ.get("CIC_PROBE_CARGO", "cargo").split()
RUNNERS = os.environ.get("CIC_PROBE_RUNNERS", os.path.join(HERE, "..", "grammar-pattern-measurement", "runners"))
FUZZ_N = int(os.environ.get("CIC_ENGINE_FUZZ", "1500")); FUZZ_SEED = 20261121
CANARIES = [{"id": "canary.match", "p": "^a+$", "input": "aaa", "want": "match"}, {"id": "canary.nomatch", "p": "^a+$", "input": "aab", "want": "nomatch"},
            {"id": "canary.refused", "p": "a(", "input": "a", "want": "compile_error"}, {"id": "canary.lf", "p": "^a+$", "input": "aa\n", "want": "nomatch"},
            {"id": "canary.dot_lf", "p": "^a.c$", "input": "a\nc", "want": "nomatch"}, {"id": "canary.dot_u", "p": "^a.c$", "input": "a\U0001F600c", "want": "match"}]


def py_of(name):
    p = os.environ.get("CIC_ENGINE_PY_" + name.replace("_default", ""))
    if not p:
        die(EXIT_INFRA, "INCOMPLETE: CIC_ENGINE_PY_%s (the interpreter that has %s installed) is not set" % (name, name))
    return p


def hexed(c):
    return {"id": c["id"], "p": c["p"], "input_hex": c["input"].encode("utf-8").hex(), "nocap": bool(c.get("nocap")), "alarm": c.get("alarm", 0)}


def run_py(name, cases, timeout=600):
    """Batch run of a Python-side engine (verdicts). Returns {id: (verdict, compile_ns, match_ns)}; canaries are appended and checked."""
    allc = cases + CANARIES
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump([hexed(c) for c in allc], f)
    try:
        r = subprocess.run([py_of(name), os.path.join(DIR, "runner_py.py"), name, "verdicts", f.name], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        die(EXIT_INFRA, "INCOMPLETE: the %s runner exceeded %ds on a batch" % (name, timeout))
    if r.returncode != 0:
        die(EXIT_INFRA, "INCOMPLETE: the %s runner failed (rc=%d): %s" % (name, r.returncode, (r.stderr or r.stdout)[-500:]))
    res = {}
    for line in r.stdout.splitlines():
        if line.count("|") != 3:
            continue
        i, v, a, b = line.rsplit("|", 3); res[i] = ("compile_error" if v == "refused" else v, int(a), int(b))
    if set(res) != {c["id"] for c in allc}:
        die(EXIT_INFRA, "INCOMPLETE: the %s runner answered %d of %d cases" % (name, len(res), len(allc)))
    for c in CANARIES:
        if os.environ.get("CIC_ENGINE_CANARIES", "1") != "0" and res[c["id"]][0] != c["want"]:     # =0 only in the self-test, to see the parity layer alone
            die(EXIT_CANARY, "INCOMPLETE: CANARY %s failed in %s (answered %s, expected %s): a stale, constant or wrong engine; no result of it is used" % (c["id"], name, res[c["id"]][0], c["want"]))
    return {c["id"]: res[c["id"]] for c in cases}


def run_py_killable(name, cases, limit):
    """One case per child process, killed at the limit: for the backtracking engines. Returns {id: (verdict|timeout, compile_ns, match_ns)}."""
    out = {}
    for c in cases:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump([hexed(c)], f)
        try:
            r = subprocess.run([py_of(name), os.path.join(DIR, "runner_py.py"), name, "verdicts", f.name], capture_output=True, text=True, timeout=limit)
            if r.returncode != 0 or r.stdout.count("|") != 3:
                die(EXIT_INFRA, "INCOMPLETE: the %s runner failed on %s: %s" % (name, c["id"], (r.stderr or r.stdout)[-300:]))
            i, v, a, b = r.stdout.strip().rsplit("|", 3); out[c["id"]] = ("compile_error" if v == "refused" else v, int(a), int(b))
        except subprocess.TimeoutExpired:
            out[c["id"]] = ("timeout>%ds" % limit, 0, limit * 10**9)
    return out


def run_ext(kind, cases, tmp):
    """Go or Rust runner of the profile probe (with its canaries): {id: (verdict, 0, ns)}."""
    PE.GO, PE.CARGO, PE.RUNNERS = GO, CARGO, RUNNERS
    try:
        r = PE.ext_run(kind, cases, tmp)
    except SystemExit as e:                              # probe_engines.py exits with a message: a failed canary is a detection, everything else is infrastructure
        m = str(e.code); die(EXIT_CANARY if "CANARY" in m else EXIT_INFRA, m)
    except (subprocess.TimeoutExpired, OSError) as e:
        die(EXIT_INFRA, "INCOMPLETE: the %s runner could not be run: %s" % (kind, type(e).__name__))
    if r is None:
        die(EXIT_INFRA, "INCOMPLETE: the %s toolchain is not available" % kind)
    return {i: (v, 0, e) for i, (v, e) in r.items()}


def short(s, n=44):
    return s.replace("\n", "\\n").encode("ascii", "backslashreplace").decode()[:n]


def parity(tmp, lines_out):
    """Four separate results (review finding F3): A conformance to an INDEPENDENT hand-authored expectation (117 semantic cases + the 24 accepted constructs with a counterpart each),
    B differential agreement of the five linear-time engines on generated cases (no independent expectation exists there: agreement is NOT correctness), C a second opinion on the generated
    cases from the stdlib `re` (backtracking, so bounded to 2 s per case), D the number of classifier-ACCEPTED patterns that a linear-time engine refused to compile (each one is a failure).
    Returns the number of failures."""
    sem_cases, sem_expect = PE.semantic_cases()
    sem = [{"id": c["id"], "p": c["p"], "input": c["input"]} for c in sem_cases]
    import subset_check as S
    expect = {i: ("match" if w else "nomatch") for i, w in sem_expect.items()}
    con = []; accepted = [c for c in PE.construct_cases() if S.parse(c["p"]).ok]
    if {c["id"][4:] for c in accepted} != set(construct_expect.EXPECT):
        die(EXIT_INFRA, "INCOMPLETE: construct_expect.py does not cover exactly the accepted constructs: %s" % sorted({c["id"][4:] for c in accepted} ^ set(construct_expect.EXPECT)))
    for c in accepted:
        pairs = construct_expect.EXPECT[c["id"][4:]]
        if pairs[0][0] != c["input"]:
            die(EXIT_INFRA, "INCOMPLETE: construct_expect.py: the first input of %s is not the probed one" % c["id"])
        for n, (inp, want) in enumerate(pairs):
            cid = c["id"] if n == 0 else c["id"] + ".alt"
            con.append({"id": cid, "p": c["p"], "input": inp}); expect[cid] = want
    fz, fst = fuzz_gen.gen(FUZZ_N, FUZZ_SEED)
    fz_alarm = [dict(c, alarm=2) for c in fz]
    hand = sem + con
    res = {}
    for e in PYENG:
        res[e] = run_py(e, hand, 600) if e in BACKTRACKING else run_py(e, hand + fz, 1800)
    for k in ("go", "rust"):
        res[k] = run_ext(k, hand + fz, tmp)
    re_fz = run_py("re", fz_alarm, 1800)                  # the stdlib re as a bounded second opinion on the generated cases
    fail_a = {e: 0 for e in res}; lines = []; bad = 0; refused_accepted = 0; diff_bad = 0
    for c in hand + fz:
        i = c["id"]; v = {e: res[e][i][0] for e in res if i in res[e]}
        for e in LINEAR:                                  # D: an accepted pattern must compile in every linear-time engine
            if v[e] not in ("match", "nomatch"):
                refused_accepted += 1; bad += 1; lines.append("FAIL-COMPILE %-14s %s  %s=%s" % (i, short(c["p"], 50), e, v[e]))
        if i in expect:                                   # A: every engine against the independent expectation
            for e in v:
                if v[e] != expect[i]:
                    fail_a[e] += 1
            if any(v[e] != expect[i] for e in LINEAR):
                bad += 1; lines.append("FAIL-EXPECT  %-14s %s | %s  want=%s %s" % (i, short(c["p"], 50), short(c["input"], 30), expect[i], " ".join("%s=%s" % (e, v[e]) for e in v)))
        elif len({v[e] for e in LINEAR}) != 1:            # B: differential, generated cases
            diff_bad += 1; bad += 1
            lines.append("DISAGREE %-14s %s | %s  %s" % (i, short(c["p"], 50), short(c["input"], 30), " ".join("%s=%s" % (e, v[e]) for e in v)))
    cons = {}; oc = {"checked": 0, "timeout": 0, "disagree": 0, "refused": 0}
    for c in fz:
        i = c["id"]; lin = {res[e][i][0] for e in LINEAR}
        r = re_fz[i][0]
        if r == "timeout":
            oc["timeout"] += 1
        elif r == "compile_error":
            oc["refused"] += 1                              # an accepted pattern that stdlib re does not compile is reported, not a failure of the linear engines
        else:
            oc["checked"] += 1
            if len(lin) == 1 and r not in lin:
                oc["disagree"] += 1; bad += 1
                lines.append("ORACLE-DISAGREE %-14s %s | %s  re=%s linear=%s" % (i, short(c["p"], 50), short(c["input"], 30), r, "/".join(sorted(lin))))
    lines_out.append("A. conformance to the INDEPENDENT hand-authored expectation: %d cases (%d semantic + %d from the %d accepted constructs, each with a counterpart); engines: %s ; backtracking engines (counted, not failing the run): %s" % (
        len(hand), len(sem), len(con), len(accepted), ", ".join(LINEAR), ", ".join(BACKTRACKING)))
    for e in res:
        lines_out.append("   %-6s differs from the expectation on %d of %d cases" % (e, fail_a[e], len(hand)))
    lines_out.append("B. DIFFERENTIAL agreement of the linear-time engines on %d generated patterns / %d fuzz cases (seed %d; %d generated texts refused by the classifier and dropped): disagreements %d. (Agreement is not correctness: no independent expectation exists for these cases.)" % (
        fst["patterns"], fst["cases"], FUZZ_SEED, fst["refused_by_classifier"], diff_bad))
    lines_out.append("C. second opinion on the generated cases from the stdlib re (2 s per case): checked %d, timed out %d, not compiled by re %d, disagreeing with the linear consensus %d" % (oc["checked"], oc["timeout"], oc["refused"], oc["disagree"]))
    lines_out.append("D. classifier-ACCEPTED patterns that a linear-time engine refused to compile (each is a failure): %d" % refused_accepted)
    lines_out.append("failures in total: %d" % bad)
    lines_out.extend(lines[:80])
    return bad


MAXCASES = [("max.bounded_alt", "^(a|aa){1,255}$", "a" * 255 + "b"), ("max.optional_run", "^" + "a?" * 84 + "a" * 84 + "$", "a" * 84 + "b"),
            ("max.group_optional", "^(a?){255}a{255}$", "a" * 255 + "b"), ("max.star3", "^a*a*a*$", "a" * 255 + "b"), ("max.nested_bounded", "^(a{30}){30}$", "a" * 256),
            ("max.big_class_runs", "^" + "[a-z]{255}" * 25 + "$", "a" * 256), ("max.alt_255", "^(a|b){255}$", "ab" * 127 + "a")]


def timing(tmp, lines_out):
    cs = PE.timing_cases() + [{"id": i, "p": p, "input": v} for i, p, v in MAXCASES]
    for c in cs:
        c.setdefault("input", ""); c["nocap"] = True        # the engine is measured on long values: the 256 code point cap is the profile's wrapper, not an engine property
    import subset_check as S
    res = {}
    for e in PYENG:
        res[e] = run_py_killable(e, cs, 10) if e in BACKTRACKING else run_py(e, cs, 1800)
    for k in ("go", "rust"):
        res[k] = run_ext(k, cs, tmp)
    order = PYENG + ["go", "rust"]
    lines_out.append("%-30s %s   (match time in ns; compile time is included in none of them; 'timeout' = killed at 10 s)" % ("case", " ".join("%-14s" % e for e in order)))
    bad = 0
    for c in cs:
        i = c["id"]
        cell = []
        for e in order:
            v, _, ns = res[e][i]
            cell.append("%-14s" % (v[:7] + ":" + str(ns) if v.startswith("timeout") else str(ns)))
        insub = S.parse(c["p"]).ok
        verd = {res[e][i][0] for e in LINEAR if insub or e != "nfa"}
        dis = len(verd) != 1
        flag = "  <-- LINEAR ENGINES DISAGREE" if dis else ""
        if not insub:
            flag += "  [outside the subset: nfa refuses by design, shown as 0]"
        bad += dis
        lines_out.append("%-30s %s  %s%s" % (i, " ".join(cell), short(c["p"], 36), flag))
    worst = {e: max(res[e][c["id"]][2] for c in cs) for e in order}
    lines_out.append("worst match time per engine over all %d cases (ns): %s" % (len(cs), ", ".join("%s=%d" % (e, worst[e]) for e in order)))
    return bad


def bench_cases():
    cs = [("B0.baseline", "a", "a")]
    for n, (p, sample, kind) in enumerate(PE.CONTRACTS):
        cs.append(("B%d.contract" % (n + 1), p, sample))
    cs += [("S1.nested_30x30", "^(a{30}){30}$", "a" * 256), ("S2.group_255x3", "^([a-z]{255}){3}$", "a" * 256), ("S3.25_class_runs", "^" + "[a-z]{255}" * 25 + "$", "a" * 256),
           ("S4.alt_255", "^(a|b){255}$", "ab" * 127 + "a"), ("S5.opt_group_255", "^(a?){255}a{255}$", "a" * 255), ("S6.bounded_alt_nomatch", "^(a|aa){1,255}$", "a" * 255 + "b"),
           ("S7.optional_run_84", "^" + "a?" * 84 + "a" * 84 + "$", "a" * 84 + "b"), ("S8.star3_nomatch", "^.*.*.*$", "a" * 255 + "\n")]
    return cs


def bench(tmp, lines_out):
    cs = bench_cases(); table = {}
    for cid, p, v in cs:
        for e in PYENG + ["go", "rust"]:
            case = {"p": p, "native": PE.native(p, "go"), "input_hex": v.encode("utf-8").hex(), "compiles": 5, "matches": 3 if e in BACKTRACKING else 7}
            f = os.path.join(tmp, "bench.json"); json.dump(case, open(f, "w"))
            try:
                if e in PYENG:
                    r = subprocess.run([py_of(e), os.path.join(DIR, "runner_py.py"), e, "bench", f], capture_output=True, text=True, timeout=30)
                elif e == "go":
                    r = subprocess.run(GO + ["run", ".", f], cwd=os.path.join(HERE, "bench", "go"), capture_output=True, text=True, timeout=300)
                else:
                    env = dict(os.environ, CARGO_TARGET_DIR=os.path.join(tmp, "cargo-bench-target"))
                    r = subprocess.run(CARGO + ["run", "-q", "--release", "--locked", "--", f], cwd=os.path.join(HERE, "bench", "rust"), capture_output=True, text=True, timeout=900, env=env)
            except subprocess.TimeoutExpired:
                table[(cid, e)] = None; continue
            if r.returncode != 0 or r.stdout.count("|") != 3:
                if e in PYENG and "Unsupported" in (r.stderr or ""):
                    table[(cid, e)] = "refused"; continue
                die(EXIT_INFRA, "INCOMPLETE: bench %s on %s failed: %s" % (e, cid, (r.stderr or r.stdout)[-300:]))
            a, b, m, st = r.stdout.strip().split("|"); table[(cid, e)] = (int(a), int(b), int(m))
    order = PYENG + ["go", "rust"]
    lines_out.append("one process per (engine, case); compile = best of 5 (ns); match = median of 7 (3 for re/regex) (ns); memory = peak resident kB above the size before the case (VmHWM reset by /proc/self/clear_refs after a warm-up; imports and the runtime are not counted; the 'a' baseline case shows the noise floor)")
    lines_out.append("%-24s %s" % ("case", " ".join("%-27s" % e for e in order)))
    lines_out.append("%-24s %s" % ("", " ".join("%-27s" % "compile/match/+mem" for e in order)))
    for cid, p, v in cs:
        cell = []
        for e in order:
            t = table[(cid, e)]
            cell.append("%-27s" % ("TIMEOUT>30s" if t is None else t if isinstance(t, str) else "%d/%d/+%d" % (t[0], t[1], t[2])))
        lines_out.append("%-24s %s" % (cid, " ".join(cell)))
    return 0


def constructs(tmp, lines_out):
    cs = PE.construct_cases()
    res = {}
    for e in PYENG + ["re2p_default"]:
        res[e] = run_py_killable(e, cs, 10) if e in BACKTRACKING else run_py(e, cs, 600)
    for k in ("go", "rust"):
        res[k] = run_ext(k, cs, tmp)
    import subset_check as S
    order = PYENG + ["re2p_default", "go", "rust"]
    fb = [c["id"] for c in cs if res["re2p_default"][c["id"]][0] != "compile_error" and res["re2p"][c["id"]][0] == "compile_error"]
    lines_out.append("pyre2 with its DEFAULT fallback silently accepts %d constructs that RE2 itself refuses (it hands them to Python `re`: backtracking, other semantics): %s" % (len(fb), ", ".join(i[4:] for i in fb)))
    lines_out.append("%-30s %s subset   (compile_error = the engine refuses the expression; the closed-subset classifier refuses everything marked REFUSE BEFORE any engine sees it)" % ("construct", " ".join("%-13s" % e for e in order)))
    for c in cs:
        i = c["id"]
        lines_out.append("%-30s %s %s" % (i, " ".join("%-13s" % res[e][i][0] for e in order), "ACCEPT" if S.parse(c["p"]).ok else "REFUSE"))
    return 0


def versions(tmp, lines_out):
    """E3: the run's evidence names the engines that ACTUALLY ran (versions, not just names), so that a later change of an engine cannot silently inherit this run's conformance claim."""
    import hashlib
    for e in PYENG:
        r = subprocess.run([py_of(e), os.path.join(DIR, "runner_py.py"), e, "version"], capture_output=True, text=True)
        if r.returncode != 0:
            die(EXIT_INFRA, "INCOMPLETE: the %s runner cannot report its version: %s" % (e, (r.stderr or r.stdout)[-300:]))
        lines_out.append("%-6s %s" % (e, r.stdout.strip()))
    for k, cmd in (("go", GO + ["version"]), ("cargo", CARGO + ["--version"])):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            die(EXIT_INFRA, "INCOMPLETE: `%s` failed: %s" % (" ".join(cmd), (r.stderr or r.stdout)[-300:]))
        lines_out.append("%-6s %s" % (k, r.stdout.strip()))
    for label, path in (("rust regex crate (runner of the profile probe)", os.path.join(RUNNERS, "rust", "Cargo.lock")), ("rust regex crate (bench)", os.path.join(HERE, "bench", "rust", "Cargo.lock"))):
        txt = open(path, encoding="utf-8").read()
        m = re.search(r'name = "regex"\nversion = "([^"]+)"', txt)
        lines_out.append("%-46s %s (Cargo.lock sha256 %s)" % (label, m.group(1) if m else "NOT FOUND", hashlib.sha256(txt.encode()).hexdigest()[:16]))
    for label, path in (("go.mod of the profile probe runner", os.path.join(RUNNERS, "go", "go.mod")), ("go.mod of the bench", os.path.join(HERE, "bench", "go", "go.mod"))):
        lines_out.append("%-46s %s" % (label, " ; ".join(l.strip() for l in open(path, encoding="utf-8") if l.startswith(("go ", "toolchain")))))
    for f in ("nfa_engine.py", "engines.py", "construct_expect.py", "fuzz_gen.py"):
        lines_out.append("%-46s sha256 %s" % (f, hashlib.sha256(open(os.path.join(DIR, f), "rb").read()).hexdigest()))
    lines_out.append("subset_check.py (the classifier in front of every engine) sha256 %s" % hashlib.sha256(open(os.path.join(HERE, "..", "grammar-pattern-measurement", "subset_check.py"), "rb").read()).hexdigest())
    return 0


def main():
    tmp = tempfile.mkdtemp(); bad = 0
    for name, fn in (("versions", versions), ("parity", parity), ("timing", timing), ("bench", bench), ("constructs", constructs)):
        if name not in ONLY:
            continue
        t = time.time(); lines = []
        b = fn(tmp, lines); bad += b
        open(os.path.join(OUT, "%s.txt" % name), "w", encoding="utf-8").write("\n".join(lines) + "\n")
        print("%-10s done in %ds, problems: %d" % (name, time.time() - t, b)); sys.stdout.flush()
    return EXIT_DISAGREE if bad else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:                                  # a crash is an infrastructure failure, never a detection (F2)
        import traceback
        die(EXIT_INFRA, "INCOMPLETE: the probe crashed:\n" + traceback.format_exc())
