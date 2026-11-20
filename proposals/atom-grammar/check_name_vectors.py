#!/usr/bin/env python3
"""Gate for the node-name grammar (cic-primitives #39, decision D1; design: docs/en/GRAMMAR-NODE-NAME-PROFILE-DESIGN.md).

Runs the four-verdict vectors in name-vectors/node-name.yaml and proves with seeded faults that each check can fail.

Usage:
    check_name_vectors.py              # every check below
    check_name_vectors.py --self-test  # the above on the real tree, then every seeded fault must turn it red, each in its own check

Checks (a failing or crashing check is a FAIL; nothing is skipped silently):
  C1  the vector file: structure, coverage, and the v1 columns DERIVED from the V1 pattern (a hand edit cannot move them), the v1_forms column against the
      committed Forms measurement
  C2  v2 through the REAL checker (check_grammar.py, version bound to 2): every name verdict
  C3  the version binding: three distinct errors, no default, the pinned version read from shape.yaml, the context mismatch refused at load time
  C4  the version is a property of the pinned grammar, never a key of a document: refused at node, spec and config_surface level
  C5  V1 regression: the pinned V1 files (the commit of the Forms pin, read from git, digests compared) give the v1_checker verdicts on the same vectors
  C6  the release schema set: the composed schemas have no finding under V2 and exactly the three `createdBy` findings under the pinned V1 checker
  C7  widening, bounded exhaustive, on the real V2 name sub-schema: V1-valid implies V2-valid, the added names all have an upper-case letter, and the
      sub-schema equals the reference function for every string
  C8  Go and Rust: the two runners (docs/evidence/node-name-v2-parity/go and rust: they apply the rule they are GIVEN to the names they are given) are BUILT AND RUN
      on every run, on inputs generated from the current grammar file and the current vector file; the fresh output has the exact inventory, equals the v2 column
      and the other runner's. Nothing recorded is trusted: a changed runner changes the result. Without a Go or a Rust toolchain C8 is NOT RUN, and with
      CIC_REQUIRE_NAME_RUNNERS=1 (the gate) it is a FAIL.

Without the history of the pinned V1 commit, C5 and C6 are NOT RUN: that is printed, and with CIC_REQUIRE_RELEASE_HISTORY=1 (the gate) it is a FAIL.
check_name_vectors.py --export DIR writes the inputs of the runners (names.json, rule.json) from the real files.
Environment: CIC_NAME_GO and CIC_NAME_CARGO name the go and cargo commands (default: go, cargo); CARGO_TARGET_DIR is honored.
Dependencies: PyYAML, jsonschema, git. No network, no clock.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
GRAMMAR = HERE / "check_grammar.py"
SCHEMA = HERE / "instance-grammar.schema.yaml"
VECTORS = HERE / "name-vectors" / "node-name.yaml"
SHAPE = ROOT / "schemas" / "atomic" / "shape.yaml"
FORMS_PIN = ROOT / "tests" / "fixtures" / "forms-pin-73ae469.yaml"
FORMS_OUT = ROOT / "docs" / "evidence" / "grammar-node-name-measurement" / "go-output.txt"
PARITY = ROOT / "docs" / "evidence" / "node-name-v2-parity"
RELEASE_SCHEMAS = ROOT / "docs" / "design" / "release-schemas"
GIT_DIR = os.environ.get("CIC_NAME_GATE_GIT_DIR") or str(ROOT / ".git")
REQUIRE_HISTORY = os.environ.get("CIC_REQUIRE_RELEASE_HISTORY") == "1"
REQUIRE_RUNNERS = os.environ.get("CIC_REQUIRE_NAME_RUNNERS") == "1"
GO_CMD = os.environ.get("CIC_NAME_GO", "go")
CARGO_CMD = os.environ.get("CIC_NAME_CARGO", "cargo")
PIN = "cic-primitives-73ae469-6a188078"
CLASSES = {"valid_all", "valid_v2_only", "invalid_all", "line_feed_checker_defect", "line_feed", "long"}
VERDICTS = {"accept", "refuse"}
NOT_RUN = "NOT RUN"


class NotRun(Exception):
    pass


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def vectors():
    return yaml.safe_load(VECTORS.read_text(encoding="utf-8"))


def acc(b) -> str:
    return "accept" if b else "refuse"


def verdict_of(grammar, validator, name) -> str:
    """The verdict of a checker on one node name: no finding at all on a one-node composition."""
    doc = grammar.as_document({"name": name, "shape_type": "opaque"})
    return acc(not grammar.check_document(doc, validator))


# --------------------------------------------------------------------------------------------------------------------------------------------------------
def c1_vector_file():
    out = []
    v = vectors()
    if v.get("vectors_format") != 1:
        return ["vectors_format is not 1"]
    ng = v["node_name_grammar"]
    v1 = re.compile(ng["v1_rule"])
    names = v["names"]
    ids = [n["id"] for n in names]
    if len(ids) != len(set(ids)):
        out.append("duplicate vector ids")
    texts = [n["name"] for n in names]
    if len(texts) != len(set(texts)):
        out.append("the same name twice")
    if {n["class"] for n in names} != CLASSES:
        out.append("the classes are %s, required exactly %s" % (sorted({n["class"] for n in names}), sorted(CLASSES)))
    must = {"": "the empty name", "createdBy": "createdBy", "abc\n": "a valid name plus one line feed", "a" * 300: "a long name"}
    for t, why in must.items():
        if t not in texts:
            out.append("the vector for %s is missing" % why)
    forms = {}
    if FORMS_OUT.exists():
        for line in FORMS_OUT.read_text(encoding="utf-8").splitlines():
            p = line.split("|")
            if len(p) >= 4 and p[1] == "-" and p[2] == "compile":
                forms[p[0]] = "accept" if p[3] == "OK" else "refuse"
    else:
        out.append("the committed Forms measurement %s is missing" % FORMS_OUT.relative_to(ROOT))
    for n in names:
        for col in ("v1_rule", "v1_checker", "v2"):
            if n[col] not in VERDICTS:
                out.append("%s: %s is %r" % (n["id"], col, n[col]))
        t = n["name"]
        rule = bool(v1.fullmatch(t))
        checker = rule or (t.endswith("\n") and bool(v1.fullmatch(t[:-1])))   # the V1 checker's flavor: one line feed after a valid name
        if n["v1_rule"] != acc(rule):
            out.append("%s: v1_rule is %s, the V1 pattern gives %s" % (n["id"], n["v1_rule"], acc(rule)))
        if n["v1_checker"] != acc(checker):
            out.append("%s: v1_checker is %s, the V1 pattern with the checker's flavor gives %s" % (n["id"], n["v1_checker"], acc(checker)))
        fc = n.get("forms_case")
        if fc is None:
            if n["v1_forms"] != "unmeasured":
                out.append("%s: v1_forms is %s without a measurement case" % (n["id"], n["v1_forms"]))
        elif forms.get(fc) is None:
            out.append("%s: the measurement case %s is not in the committed Forms output" % (n["id"], fc))
        elif n["v1_forms"] != forms[fc]:
            out.append("%s: v1_forms is %s, the committed Forms measurement says %s" % (n["id"], n["v1_forms"], forms[fc]))
    return out


def c2_v2_checker():
    g = load_module(GRAMMAR, "_name_grammar_v2")
    validator = g.load_schema(node_name_grammar=2)
    out = []
    for n in vectors()["names"]:
        got = verdict_of(g, validator, n["name"])
        if got != n["v2"]:
            out.append("%s %r: the checker gives %s, the vector says %s" % (n["id"], n["name"][:20], got, n["v2"]))
    return out


def decode(x):
    if isinstance(x, dict) and "str" in x:
        return str(x["str"])
    if isinstance(x, dict) and "float" in x:
        return float(x["float"])
    return x


def c3_binding():
    g = load_module(GRAMMAR, "_name_grammar_bind")
    out = []
    for b in vectors()["binding"]:
        ctx, pin = decode(b["context"]), decode(b["pin"])
        try:
            got = g.bind_node_name_grammar(ctx, pin)
            got = "ok" if got == ctx else "ok-with-another-version"
        except g.GrammarVersionError as e:
            got = e.code
        if got != b["expect"]:
            out.append("%s (%s): %s, expected %s" % (b["id"], b["description"], got, b["expect"]))
    # the pinned grammar declares its version: read from shape.yaml, never defaulted
    pinned = g.pinned_node_name_version()
    if pinned != 2:
        out.append("shape.yaml declares %r, expected the integer 2" % (pinned,))
    for label, call, code in (
        ("no context version", lambda: g.load_schema(), "NODE_NAME_GRAMMAR_VERSION_MISSING"),
        ("context version None", lambda: g.load_schema(node_name_grammar=None), "NODE_NAME_GRAMMAR_VERSION_MISSING"),
        ("context version 1 against the pin 2", lambda: g.load_schema(node_name_grammar=1), "NODE_NAME_GRAMMAR_VERSION_CONFLICT"),
        ("context version \"2\"", lambda: g.load_schema(node_name_grammar="2"), "NODE_NAME_GRAMMAR_VERSION_UNKNOWN"),
    ):
        try:
            call()
            out.append("load_schema with %s did not refuse (expected %s)" % (label, code))
        except g.GrammarVersionError as e:
            if e.code != code:
                out.append("load_schema with %s refused with %s, expected %s" % (label, e.code, code))
    return out


def c4_document_keys():
    g = load_module(GRAMMAR, "_name_grammar_keys")
    validator = g.load_schema(node_name_grammar=2)
    out = []
    base = lambda: {"spec": {"identity": {"kind": "K"}, "config_surface": {"nodes": [{"name": "a", "shape_type": "opaque"}]}}}
    for d in vectors()["document_keys"]:
        doc = base()
        if d["where"] == "node":
            doc["spec"]["config_surface"]["nodes"][0]["node_name_grammar"] = 2
        elif d["where"] == "spec":
            doc["spec"]["node_name_grammar"] = 2
        elif d["where"] == "config_surface":
            doc["spec"]["config_surface"]["node_name_grammar"] = 2
        else:
            out.append("%s: unknown place %r" % (d["id"], d["where"])); continue
        if not g.check_document(doc, validator):
            out.append("%s (%s): the document is accepted" % (d["id"], d["description"]))
    if g.check_document(base(), validator):
        out.append("the baseline document without the key is refused (the test would prove nothing)")
    return out


def pinned_v1():
    """The two V1 files of the Forms pin, read from the commit of the pin and compared with the pinned digests; returns a directory with them."""
    pin = yaml.safe_load(FORMS_PIN.read_text(encoding="utf-8"))["grammar"][PIN]
    want = {f["path"]: f["sha256"] for f in pin["files"]}
    commit = pin["commit"]
    probe = subprocess.run(["git", "--git-dir", GIT_DIR, "cat-file", "-e", commit + "^{commit}"], capture_output=True)
    if probe.returncode != 0:
        if REQUIRE_HISTORY:
            raise AssertionError("CIC_REQUIRE_RELEASE_HISTORY=1 but the commit %s of the V1 pin is not in the clone (fetch-depth: 0)" % commit)
        raise NotRun("the history of %s is absent" % commit)
    d = Path(tempfile.mkdtemp(prefix="v1pin-"))
    for rel in ("proposals/atom-grammar/check_grammar.py", "proposals/atom-grammar/instance-grammar.schema.yaml"):
        blob = subprocess.run(["git", "--git-dir", GIT_DIR, "show", "%s:%s" % (commit, rel)], capture_output=True, check=True).stdout
        got = hashlib.sha256(blob).hexdigest()
        if got != want[rel]:
            raise AssertionError("%s at %s has the digest %s, the pin says %s" % (rel, commit[:7], got, want[rel]))
        (d / Path(rel).name).write_bytes(blob)
    return d


def c5_v1_regression():
    d = pinned_v1()
    try:
        g = load_module(d / "check_grammar.py", "_name_grammar_v1")
        validator = g.load_schema()          # the V1 API: no version argument, nothing to bind
        out = []
        for n in vectors()["names"]:
            got = verdict_of(g, validator, n["name"])
            if got != n["v1_checker"]:
                out.append("%s %r: the pinned V1 checker gives %s, the vector says %s" % (n["id"], n["name"][:20], got, n["v1_checker"]))
        return out
    finally:
        shutil.rmtree(d, ignore_errors=True)


def c6_release_schemas():
    d = pinned_v1()
    try:
        g1 = load_module(d / "check_grammar.py", "_name_grammar_v1b")
        v1 = g1.load_schema()
        g2 = load_module(GRAMMAR, "_name_grammar_v2b")
        v2 = g2.load_schema(node_name_grammar=2)
        sys.path.insert(0, str(RELEASE_SCHEMAS))
        try:
            import compose as C
        finally:
            sys.path.pop(0)
        out = []
        for kind in ("PrimitiveRelease", "ModuleRelease"):
            doc = C.compose(str(RELEASE_SCHEMAS), kind)
            f2 = g2.check_document(doc, v2)
            if f2:
                out.append("%s: %d finding(s) under V2, expected none: %s" % (kind, len(f2), str(f2[0])[:80]))
            f1 = g1.check_document(doc, v1)
            if len(f1) != 3 or any("createdBy" not in str(f) for f in f1):
                out.append("%s: the pinned V1 checker gives %d finding(s), expected exactly the three createdBy findings" % (kind, len(f1)))
        return out
    finally:
        shutil.rmtree(d, ignore_errors=True)


def v2_reference(s: str, rule) -> bool:
    return bool(re.fullmatch(rule["pattern"], s)) and not re.search(rule["not_pattern"], s)


def c7_widening():
    g = load_module(GRAMMAR, "_name_grammar_w")
    from jsonschema import Draft202012Validator
    schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
    sub = Draft202012Validator(schema["properties"]["name"])
    ng = vectors()["node_name_grammar"]
    v1, rule = re.compile(ng["v1_rule"]), ng["v2_rule"]
    alpha = ["a", "b", "Z", "Q", "0", "_", "-", " ", "\n", "é"]
    narrowed, added_no_upper, differs, count = [], [], [], 0
    for L in range(1, 6):
        for t in itertools.product(alpha, repeat=L):
            s = "".join(t); count += 1
            got = sub.is_valid(s)
            ref = v2_reference(s, rule)
            old = bool(v1.fullmatch(s))
            if got != ref:
                differs.append(s)
            if old and not got:
                narrowed.append(s)
            if got and not old and not re.search("[A-Z]", s):
                added_no_upper.append(s)
    out = []
    if differs: out.append("the V2 name sub-schema differs from the reference function for %d string(s), first %r" % (len(differs), differs[0]))
    if narrowed: out.append("%d V1-valid name(s) are not V2-valid, first %r" % (len(narrowed), narrowed[0]))
    if added_no_upper: out.append("%d name(s) added by V2 have no upper-case letter, first %r" % (len(added_no_upper), added_no_upper[0]))
    return out


def extract_rule():
    schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
    name = schema["properties"]["name"]
    return {"min_length": name.get("minLength"), "pattern": name.get("pattern"),
            "not_pattern": (name.get("not") or {}).get("pattern")}


def export_inputs(out: Path):
    """What the runners are given, generated from the CURRENT files: the names and ids of the vector file, the rule of the grammar file's name sub-schema."""
    (out / "names.json").write_text(json.dumps([{"id": n["id"], "name": n["name"]} for n in vectors()["names"]], ensure_ascii=True) + "\n", encoding="utf-8")
    (out / "rule.json").write_text(json.dumps(extract_rule()) + "\n", encoding="utf-8")


def run_tool(cmd, cwd, env=None, timeout=900):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=dict(os.environ, **(env or {})))


def toolchain(cmd: str, version_args) -> str:
    """The version line of a tool, or NotRun (a FAIL when the gate requires the runners) if it is absent."""
    exe = shutil.which(cmd) or (cmd if os.path.exists(cmd) else None)
    if exe is None:
        if REQUIRE_RUNNERS:
            raise AssertionError("CIC_REQUIRE_NAME_RUNNERS=1 but %r is not available" % cmd)
        raise NotRun("%r is not available" % cmd)
    r = subprocess.run([exe] + version_args, capture_output=True, text=True)
    return (r.stdout or r.stderr).strip().splitlines()[0] if r.returncode == 0 else exe


def parse_runner(label, text, want, out):
    got = {}
    for i, line in enumerate(text.splitlines(), 1):
        f = line.split("|")
        if len(f) != 2 or f[1] not in VERDICTS:
            out.append("%s: output line %d is malformed or not accept/refuse: %r" % (label, i, line[:40])); continue
        if f[0] not in want:
            out.append("%s: output line %d names the unknown vector %r" % (label, i, f[0])); continue
        if f[0] in got:
            out.append("%s: output line %d repeats %s" % (label, i, f[0])); continue
        got[f[0]] = f[1]
    for k in want:
        if k not in got:
            out.append("%s: the output misses the vector %s" % (label, k))
        elif got[k] != want[k]:
            out.append("%s: %s is %s, the vector says %s" % (label, k, got[k], want[k]))
    return got


def c8_go_rust():
    out = []
    for rel in ("go/main.go", "go/go.mod", "rust/Cargo.toml", "rust/Cargo.lock", "rust/src/main.rs"):
        if not (PARITY / rel).exists():
            out.append("the runner source %s is missing (docs/evidence/node-name-v2-parity/)" % rel)
    if out:
        return out
    go_version = toolchain(GO_CMD, ["version"])
    cargo_version = toolchain(CARGO_CMD, ["--version"])
    work = Path(tempfile.mkdtemp(prefix="namerun-"))
    try:
        export_inputs(work)
        want = {n["id"]: n["v2"] for n in vectors()["names"]}
        names, rule = str(work / "names.json"), str(work / "rule.json")
        results = {}
        r = run_tool([GO_CMD, "run", ".", names, rule], PARITY / "go", env={"GOTOOLCHAIN": "local"})
        if r.returncode != 0:
            out.append("go: the runner failed (exit %d): %s" % (r.returncode, (r.stderr or r.stdout).strip()[:300]))
        else:
            results["go"] = parse_runner("go", r.stdout, want, out)
        env = {"CARGO_TARGET_DIR": os.environ.get("CARGO_TARGET_DIR") or str(work / "target")}
        r = run_tool([CARGO_CMD, "run", "-q", "--locked", "--manifest-path", str(PARITY / "rust" / "Cargo.toml"), "--", names, rule], PARITY / "rust", env=env)
        if r.returncode != 0:
            out.append("rust: the runner failed (exit %d): %s" % (r.returncode, (r.stderr or r.stdout).strip()[:300]))
        else:
            results["rust"] = parse_runner("rust", r.stdout, want, out)
        if len(results) == 2 and results["go"] != results["rust"]:
            out.append("the Go and the Rust outputs differ")
        print("         (%s; %s; %d names; rule %s)" % (go_version, cargo_version, len(want), (work / "rule.json").read_text(encoding="utf-8").strip()))
        return out
    finally:
        shutil.rmtree(work, ignore_errors=True)


CHECKS = [("C1 vector file", c1_vector_file), ("C2 v2 through the real checker", c2_v2_checker), ("C3 version binding", c3_binding),
          ("C4 no version key in a document", c4_document_keys), ("C5 V1 regression (pinned files)", c5_v1_regression),
          ("C6 release schema set", c6_release_schemas), ("C7 widening (bounded exhaustive)", c7_widening), ("C8 Go and Rust parity", c8_go_rust)]


def run_checks(quiet=False):
    """Returns {check name: 'PASS' | 'FAIL' | 'NOT RUN'}; a crash is a FAIL with the exception as its reason."""
    result = {}
    for name, fn in CHECKS:
        try:
            problems = fn()
            result[name] = "FAIL" if problems else "PASS"
        except NotRun as e:
            problems, result[name] = [str(e)], NOT_RUN
        except Exception as e:  # a gate that tracebacks on its own input is not a gate
            problems, result[name] = ["crashed: %s: %s" % (type(e).__name__, str(e)[:200])], "FAIL"
        if not quiet:
            print("%-8s %s" % (result[name], name))
            for p in problems[:6]:
                print("         - " + p)
            if len(problems) > 6:
                print("         ... %d more" % (len(problems) - 6))
    return result


# --------------------------------------------------------------------------------------------------------------------------------------------------------
def sub1(text: str, pattern: str, repl: str) -> str:
    new, n = re.subn(pattern, repl, text, count=1, flags=re.S)
    assert n == 1 and new != text, "the planted edit changed nothing: %r" % pattern
    return new


def edit(path: Path, f):
    path.write_text(f(path.read_text(encoding="utf-8")), encoding="utf-8")


def seeded_faults():
    """(label, mutate(tree), the checks that must turn red). Each fault is applied to a copy of the tree."""
    ag = "proposals/atom-grammar/"
    PAR = "docs/evidence/node-name-v2-parity"
    def vec(f):
        def go(t):
            d = yaml.safe_load((t / ag / "name-vectors/node-name.yaml").read_text(encoding="utf-8"))
            f(d)
            body = (t / ag / "name-vectors/node-name.yaml").read_text(encoding="utf-8")
            head = "".join(l for l in body.splitlines(True) if l.startswith("#"))
            (t / ag / "name-vectors/node-name.yaml").write_text(head + yaml.safe_dump(d, sort_keys=False, width=200), encoding="utf-8")
        return go
    def flip(row_id, col):
        return vec(lambda d: [r.__setitem__(col, "refuse" if r[col] == "accept" else "accept") for r in d["names"] if r["id"] == row_id])
    return [
        ("the V2 pattern is narrowed back to the V1 pattern", lambda t: edit(t / ag / "instance-grammar.schema.yaml", lambda s: sub1(s, r"\^\[a-z\]\[a-zA-Z0-9_\]\*\$", "^[a-z][a-z0-9_]*$")), {"C2", "C7", "C8"}),
        ("the line-feed guard is dropped", lambda t: edit(t / ag / "instance-grammar.schema.yaml", lambda s: sub1(s, r"\n\s*not:\s*\n\s*pattern:[^\n]*", "")), {"C2", "C7", "C8"}),
        ("the V2 pattern also admits the hyphen", lambda t: edit(t / ag / "instance-grammar.schema.yaml", lambda s: sub1(s, r"\^\[a-z\]\[a-zA-Z0-9_\]\*\$", "^[a-z][a-zA-Z0-9_-]*$")), {"C2", "C7", "C8"}),
        ("the binding defaults to the pin when the context supplies nothing", lambda t: edit(t / ag / "check_grammar.py", lambda s: sub1(s, r"(def bind_node_name_grammar\(context_version, pin_version\):\n)", r"\1    if context_version is None:\n        context_version = pin_version\n")), {"C3"}),
        ("a boolean is accepted as a version", lambda t: edit(t / ag / "check_grammar.py", lambda s: sub1(s, r"isinstance\(v, bool\) or ", "")), {"C3"}),
        ("a context that differs from the pin is not refused", lambda t: edit(t / ag / "check_grammar.py", lambda s: sub1(s, r"if context_version != pin_version:", "if False:")), {"C3"}),
        ("shape.yaml declares version 1", lambda t: edit(t / "schemas/atomic/shape.yaml", lambda s: sub1(s, r"node_name_grammar:\s*\n\s*version:\s*2", "node_name_grammar:\n    version: 1")), {"C3"}),
        ("a document key node_name_grammar is no longer looked for", lambda t: edit(t / ag / "check_grammar.py", lambda s: sub1(s, r"\n\s*check_no_version_key\(doc, \"\$\", out\)", "")), {"C4"}),
        ("the pinned digest of the V1 checker is altered", lambda t: edit(t / "tests/fixtures/forms-pin-73ae469.yaml", lambda s: sub1(s, r"(check_grammar\.py\n\s*sha256: )[0-9a-f]{8}", r"\g<1>00000000")), {"C5", "C6"}),
        ("a v2 verdict of the vector file is flipped", flip("N06", "v2"), {"C2", "C8"}),
        ("the Go runner accepts every name (the review's counterexample)", lambda t: edit(t / PAR / "go/main.go", lambda s: sub1(s, r"ok := (utf8\.RuneCountInString[^\n]*)", r"ok := true || (\1)")), {"C8"}, "go: N"),
        ("the Go runner drops the start anchor of the rule it is given", lambda t: edit(t / PAR / "go/main.go", lambda s: sub1(s, r"pat\.MatchString\(n\.Name\)", "(pat.MatchString(n.Name) || regexp.MustCompile(r.Pattern[1:]).MatchString(n.Name))")), {"C8"}, "go: N"),
        ("the Go runner hard-codes the V1 pattern instead of the rule it is given", lambda t: edit(t / PAR / "go/main.go", lambda s: sub1(s, r"regexp\.MustCompile\(r\.Pattern\)", 'regexp.MustCompile("^[a-z][a-z0-9_]*$")')), {"C8"}, "go: N"),
        ("the Rust runner accepts every name", lambda t: edit(t / PAR / "rust/src/main.rs", lambda s: sub1(s, r"let ok = name\.chars\(\)[^\n]*", "let ok = true;")), {"C8"}, "rust: N"),
        ("the Rust runner drops the start anchor of the rule it is given", lambda t: edit(t / PAR / "rust/src/main.rs", lambda s: sub1(s, r"pat\.is_match\(name\)", "regex::Regex::new(&pattern[1..]).unwrap().is_match(name)")), {"C8"}, "rust: N"),
        ("the Rust runner prints nothing", lambda t: edit(t / PAR / "rust/src/main.rs", lambda s: sub1(s, r'println!\("\{\}\|\{\}", id, if ok \{ "accept" \} else \{ "refuse" \}\);', "let _ = (id, ok);")), {"C8"}, "rust: the output misses the vector"),
        ("the Rust runner repeats a line", lambda t: edit(t / PAR / "rust/src/main.rs", lambda s: sub1(s, r'(println!\("\{\}\|\{\}", id, if ok \{ "accept" \} else \{ "refuse" \}\);)', r"\1\n        \1")), {"C8"}, "rust: output line"),
        ("the Go runner reads another rule file than the one it is given", lambda t: edit(t / PAR / "go/main.go", lambda s: sub1(s, r"os\.Args\[2\]", "os.Args[1]")), {"C8"}, "go: the runner failed"),
        ("a v1_checker verdict of the vector file is flipped", flip("N23", "v1_checker"), {"C1", "C5"}),
        ("the createdBy row is removed from the vector file", vec(lambda d: d.update(names=[r for r in d["names"] if r["name"] != "createdBy"])), {"C1"}),
    ]


def copy_tree(dst: Path):
    shutil.copytree(HERE, dst / "proposals/atom-grammar", ignore=shutil.ignore_patterns("__pycache__"), copy_function=shutil.copy)   # fresh mtimes: cargo goes by mtime
    for rel in ("schemas/atomic/shape.yaml", "tests/fixtures/forms-pin-73ae469.yaml", "docs/design/release-schemas", "docs/evidence/grammar-node-name-measurement/go-output.txt",
                "docs/evidence/node-name-v2-parity"):
        src = ROOT / rel
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, target, ignore=shutil.ignore_patterns("__pycache__", "target"), copy_function=shutil.copy)
        elif src.exists():
            shutil.copy(src, target)


def run_in(tree: Path):
    env = dict(os.environ, CIC_NAME_GATE_GIT_DIR=GIT_DIR)
    r = subprocess.run([sys.executable, str(tree / "proposals/atom-grammar/check_name_vectors.py")], capture_output=True, text=True, env=env, timeout=900)
    red = {m.group(1) for m in re.finditer(r"^FAIL\s+(C\d)", r.stdout, re.M)}
    return r.returncode, red, r.stdout


def self_test() -> int:
    print("--- the real tree must pass ---")
    real = run_checks()
    bad = [k for k, v in real.items() if v != "PASS"]
    if bad:
        print("self-test: the real tree does not pass (%s): the faults below would prove nothing" % ", ".join(bad))
        return 1
    print("\n--- every seeded fault must turn the gate red, in the named check ---")
    failures = 0
    # one cargo target directory for the whole self-test: the runner crates are built once, a faulted runner is rebuilt alone
    shared = tempfile.mkdtemp(prefix="namecargo-")
    os.environ.setdefault("CARGO_TARGET_DIR", shared)
    for fault in seeded_faults():
        label, mutate, expect = fault[0], fault[1], fault[2]
        needle = fault[3] if len(fault) > 3 else None
        tree = Path(tempfile.mkdtemp(prefix="namegate-"))
        try:
            copy_tree(tree)
            try:
                mutate(tree)
            except AssertionError as e:
                print("  \033[91mBROKEN FAULT\033[0m  %s: %s" % (label, e)); failures += 1; continue
            rc, red, tail = run_in(tree)
            if rc != 0 and expect <= red and (needle is None or needle in tail):
                print("  \033[92mred\033[0m   %s  [%s]" % (label, ",".join(sorted(red))))
            else:
                print("  \033[91mLEAKED\033[0m %s  (exit %d, red: %s, expected: %s%s)" % (label, rc, ",".join(sorted(red)) or "none", ",".join(sorted(expect)),
                                                                                    "" if needle is None else ", and the output naming %r" % needle))
                failures += 1
        finally:
            shutil.rmtree(tree, ignore_errors=True)
    total = len(seeded_faults())
    shutil.rmtree(shared, ignore_errors=True)
    print("\nself-test: %d/%d seeded faults turned the gate red" % (total - failures, total))
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--export", metavar="DIR", help="write the inputs of the Go and Rust runners (names.json, rule.json) from the real grammar and vector files, then stop")
    args = ap.parse_args()
    if args.export:
        Path(args.export).mkdir(parents=True, exist_ok=True)
        export_inputs(Path(args.export))
        return 0
    if args.self_test:
        return self_test()
    res = run_checks()
    failed = [k for k, v in res.items() if v == "FAIL"]
    not_run = [k for k, v in res.items() if v == NOT_RUN]
    if not_run:
        print("\nNOT RUN (no history of the pinned V1 commit; a skipped check proves nothing): " + ", ".join(not_run))
    print("\nname vectors: %d/%d checks pass%s" % (sum(1 for v in res.values() if v == "PASS"), len(res), "" if not failed else ", FAILED: " + ", ".join(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
