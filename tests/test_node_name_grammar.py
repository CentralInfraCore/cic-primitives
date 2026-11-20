"""The node-name grammar, version 2 (cic-primitives #39, decision D1; design: docs/en/GRAMMAR-NODE-NAME-PROFILE-DESIGN.md).

Written BEFORE the implementation: the first run is red on purpose (docs/evidence/node-name-grammar-v2/red-initial.txt), and each test names the requirement it
proves. The vectors are proposals/atom-grammar/name-vectors/node-name.yaml; the gate is proposals/atom-grammar/check_name_vectors.py (which also runs the seeded
faults). The historical release records are not touched: their blob digests are listed in tests/fixtures/node-name/historical-records.sha256 and read from the tags
(where the history is present; the gate fetches all of it: CIC_REQUIRE_RELEASE_HISTORY=1).
"""
import hashlib
import importlib.util
import os
import pathlib
import re
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
GRAMMAR = ROOT / "proposals" / "atom-grammar" / "check_grammar.py"
GATE = ROOT / "proposals" / "atom-grammar" / "check_name_vectors.py"
VECTORS = yaml.safe_load((ROOT / "proposals" / "atom-grammar" / "name-vectors" / "node-name.yaml").read_text(encoding="utf-8"))
RECORDS = ROOT / "tests" / "fixtures" / "node-name" / "historical-records.sha256"
REQUIRED = os.environ.get("CIC_REQUIRE_RELEASE_HISTORY") == "1"


def grammar():
    spec = importlib.util.spec_from_file_location("_name_grammar_test", GRAMMAR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def decode(x):
    if isinstance(x, dict) and "str" in x:
        return str(x["str"])
    if isinstance(x, dict) and "float" in x:
        return float(x["float"])
    return x


def run_py(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=ROOT)


# --- explicit version binding, three distinct errors, no implicit default -------------------------------------------------------------------------------
@pytest.mark.parametrize("vec", VECTORS["binding"], ids=lambda v: v["id"])
def test_binding_vectors(vec):
    g = grammar()
    ctx, pin = decode(vec["context"]), decode(vec["pin"])
    if vec["expect"] == "ok":
        assert g.bind_node_name_grammar(ctx, pin) == ctx
    else:
        with pytest.raises(g.GrammarVersionError) as e:
            g.bind_node_name_grammar(ctx, pin)
        assert e.value.code == vec["expect"]


def test_the_three_errors_are_distinct_codes():
    g = grammar()
    codes = {"NODE_NAME_GRAMMAR_VERSION_MISSING", "NODE_NAME_GRAMMAR_VERSION_UNKNOWN", "NODE_NAME_GRAMMAR_VERSION_CONFLICT"}
    assert {b["expect"] for b in VECTORS["binding"]} - {"ok"} == codes
    assert issubclass(g.GrammarVersionError, Exception)


def test_load_schema_has_no_implicit_default():
    g = grammar()
    for call in (lambda: g.load_schema(), lambda: g.load_schema(node_name_grammar=None)):
        with pytest.raises(g.GrammarVersionError) as e:
            call()
        assert e.value.code == "NODE_NAME_GRAMMAR_VERSION_MISSING"


@pytest.mark.parametrize("flag,code", [(None, "NODE_NAME_GRAMMAR_VERSION_MISSING"), ("1", "NODE_NAME_GRAMMAR_VERSION_CONFLICT"),
                                       ("3", "NODE_NAME_GRAMMAR_VERSION_UNKNOWN"), ("two", "NODE_NAME_GRAMMAR_VERSION_UNKNOWN"), ("2.0", "NODE_NAME_GRAMMAR_VERSION_UNKNOWN")])
def test_the_command_line_has_no_default_either(flag, code):
    args = [GRAMMAR, "--self-test"] + ([] if flag is None else ["--node-name-grammar", flag])
    r = run_py(*args)
    assert r.returncode != 0
    assert code in r.stdout + r.stderr


def test_the_command_line_with_the_bound_version_runs_the_self_test():
    r = run_py(GRAMMAR, "--self-test", "--node-name-grammar", "2")
    assert r.returncode == 0, r.stdout[-400:] + r.stderr[-400:]


def test_no_caller_relies_on_a_default():
    """Every call of load_schema in the repository names its version; the compiler's gate supplies the context's."""
    offenders = []
    for path in list((ROOT / "tools").glob("*.py")) + list((ROOT / "proposals").rglob("*.py")) + list((ROOT / "tests").glob("*.py")):
        if path.name in ("test_node_name_grammar.py", "check_name_vectors.py"):
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\bload_schema\(\s*\)", line) and not line.lstrip().startswith(("#", "def ")):
                offenders.append("%s:%d" % (path.relative_to(ROOT), n))
    assert offenders == []


def test_the_compiler_release_gate_supplies_the_context_version():
    text = (ROOT / "tools" / "compiler.py").read_text(encoding="utf-8")
    assert re.search(r"NODE_NAME_GRAMMAR_CONTEXT\s*=\s*2", text)
    assert re.search(r"load_schema\(node_name_grammar=NODE_NAME_GRAMMAR_CONTEXT\)", text)


# --- the grammar file set declares its version; a document never does -------------------------------------------------------------------------------
def test_the_pinned_grammar_declares_version_2_as_an_integer():
    shape = yaml.safe_load((ROOT / "schemas" / "atomic" / "shape.yaml").read_text(encoding="utf-8"))
    v = shape["spec"]["node_name_grammar"]["version"]
    assert v == 2 and type(v) is int


def test_a_document_key_is_refused_wherever_it_sits():
    g = grammar()
    validator = g.load_schema(node_name_grammar=2)
    for place in ("node", "spec", "config_surface"):
        doc = {"spec": {"identity": {"kind": "K"}, "config_surface": {"nodes": [{"name": "a", "shape_type": "opaque"}]}}}
        {"node": lambda: doc["spec"]["config_surface"]["nodes"][0].update(node_name_grammar=2),
         "spec": lambda: doc["spec"].update(node_name_grammar=2),
         "config_surface": lambda: doc["spec"]["config_surface"].update(node_name_grammar=2)}[place]()
        assert g.check_document(doc, validator), place


# --- V2: the rule, as a full match, with the line-feed guard, through the real checker ----------------------------------------------------------------
@pytest.mark.parametrize("row", VECTORS["names"], ids=lambda r: r["id"])
def test_v2_verdict_of_the_real_checker(row):
    g = grammar()
    validator = g.load_schema(node_name_grammar=2)
    doc = g.as_document({"name": row["name"], "shape_type": "opaque"})
    assert ("accept" if not g.check_document(doc, validator) else "refuse") == row["v2"]


def test_case_is_identity_the_checker_does_not_normalize():
    g = grammar()
    validator = g.load_schema(node_name_grammar=2)
    doc = g.as_document({"name": "createdBy", "shape_type": "opaque"})
    doc["spec"]["config_surface"]["nodes"].append({"name": "createdby", "shape_type": "opaque"})
    assert g.check_document(doc, validator) == []          # two names that differ only in case: two fields
    assert doc["spec"]["config_surface"]["nodes"][0]["name"] == "createdBy"


def test_the_self_test_of_the_checker_covers_version_2():
    g = grammar()
    assert any("createdBy" in str(v) for v in g.MUST_ACCEPT.values())
    assert any("\\n" in str(v) or "\n" in str(v) for v in g.MUST_REJECT.values())


# --- the gate, its seeded faults, and the historical release records --------------------------------------------------------------------------------------
def test_the_name_gate_passes():
    """The gate, including C8: the Go and the Rust runner are built and run on inputs generated from the current files (review F1 of #41). In the gate
    (CIC_REQUIRE_RELEASE_HISTORY=1, CIC_REQUIRE_NAME_RUNNERS=1) nothing may be NOT RUN."""
    r = run_py(GATE)
    assert r.returncode == 0, r.stdout[-1500:]
    if REQUIRED or os.environ.get("CIC_REQUIRE_NAME_RUNNERS") == "1":
        assert "NOT RUN" not in r.stdout, r.stdout[-800:]
    assert "PASS     C8 Go and Rust parity" in r.stdout or (os.environ.get("CIC_REQUIRE_NAME_RUNNERS") != "1" and "NOT RUN" in r.stdout)


def run_gate_with(**env):
    return subprocess.run([sys.executable, str(GATE)], capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, **env))


def test_a_missing_toolchain_is_a_failure_where_the_runners_are_required():
    r = run_gate_with(CIC_NAME_GO="/nonexistent/go", CIC_REQUIRE_NAME_RUNNERS="1")
    assert r.returncode != 0
    assert re.search(r"^FAIL\s+C8", r.stdout, re.M), r.stdout[-600:]
    assert "CIC_REQUIRE_NAME_RUNNERS=1 but" in r.stdout


def test_a_missing_toolchain_is_never_a_silent_pass_elsewhere():
    r = run_gate_with(CIC_NAME_GO="/nonexistent/go", CIC_REQUIRE_NAME_RUNNERS="0")
    assert re.search(r"^NOT RUN\s+C8", r.stdout, re.M), r.stdout[-600:]
    assert "NOT RUN (" in r.stdout          # printed again in the summary: a skipped check proves nothing


# The seeded faults of the gate (python proposals/atom-grammar/check_name_vectors.py --self-test) run in `make grammar.local`, like the access vectors' faults; they are not
# repeated here: they rebuild the Go and Rust runners for every faulted copy, and the gate has a time budget.


def test_the_historical_release_records_are_untouched():
    lines = [l.split("  ", 1) for l in RECORDS.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 4
    tree = ROOT / "release" / "cic-primitives-v0.1.5.yaml"
    assert hashlib.sha256(tree.read_bytes()).hexdigest() == dict((p.split(":", 1)[1], d) for d, p in lines)["release/cic-primitives-v0.1.5.yaml"]
    for digest, where in lines:
        shown = subprocess.run(["git", "-C", str(ROOT), "show", where], capture_output=True)
        if shown.returncode != 0:
            assert not REQUIRED, "CIC_REQUIRE_RELEASE_HISTORY=1 but %s is not in this clone (fetch-depth: 0, the tags)" % where
            continue
        assert hashlib.sha256(shown.stdout).hexdigest() == digest, where


def test_the_verification_of_a_record_does_not_depend_on_the_grammar():
    for rel in ("tools/release_record_conformance.py",):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert not re.search(r"check_grammar|instance-grammar|node_name_grammar|load_schema", text), rel
