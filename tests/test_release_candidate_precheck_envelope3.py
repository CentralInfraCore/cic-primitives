"""Tests of tools/release_candidate_precheck.py for envelope 3 records and for the release head's artifact declaration.

Each test breaks ONE thing in a small git repository and reads the message, not the exit status alone. The expected values are computed here with hashlib and plain git, not
with the tool. The tool is loaded through `load_tool`, which the planted-defect runs (test_release_candidate_precheck_envelope3_planted.py) point at a mutated copy.
"""
import base64
import hashlib
import importlib.util
import io
import os
import pathlib
import subprocess
from contextlib import redirect_stdout

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
TOOL = REPO / "tools" / "release_candidate_precheck.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("precheck_under_test", os.environ.get("PRECHECK_TOOL") or str(TOOL))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
       "PATH": "/usr/bin:/bin:/usr/local/bin"}
FILES = {
    "LICENSE.md": "licence\n",
    "proposals/atom-grammar/check_grammar.py": "print('grammar')\n",
    "proposals/atom-grammar/instance-grammar.schema.yaml": "type: object\n",
    "schemas/atomic/role.yaml": "role: 1\n",
    "é.yaml": "unicode path\n",
}
PATHS = sorted(FILES, key=lambda p: p.encode("utf-8"))


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=ENV, check=False)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def commit_files(repo, files, msg):
    for path, text in files.items():
        p = pathlib.Path(repo) / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD")


def hexdigest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def project_yaml(paths):
    return yaml.safe_dump({"project": {"name": "x"}, "compiler_settings": {"release_artifacts": {"paths": list(paths)}}})


def make_world(tmp_path, head_files=None):
    """A repository whose first commit holds the pinned FILES, and a second commit (the release head) that adds project.yaml declaring `PATHS` (or `head_files`)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "devel")
    pinned = commit_files(repo, FILES, "pinned")
    head = commit_files(repo, {"project.yaml": project_yaml(PATHS)} if head_files is None else head_files, "release head")
    manifest_text = "".join(f"{hexdigest(FILES[p])}  {p}\n" for p in PATHS)
    digest = hashlib.sha256(manifest_text.encode("utf-8")).hexdigest()
    name = f"cic-primitives-{pinned[:7]}-{digest[:8]}"
    pins = {"grammar": {name: {"repo": "x/y", "ref": "devel", "commit": pinned,
                               "files": [{"path": p, "sha256": hexdigest(FILES[p])} for p in PATHS], "manifest_sha256": digest}}}
    manifest = tmp_path / "pins.yaml"
    manifest.write_text(yaml.safe_dump(pins, allow_unicode=True), encoding="utf-8")
    return {"repo": repo, "pinned": pinned, "head": head, "name": name, "manifest": manifest, "tmp": tmp_path}


@pytest.fixture
def world(tmp_path):
    return make_world(tmp_path)


def run(world, mode, **kw):
    tool = load_tool()
    argv = [mode, "--repo", str(world["repo"]), "--manifest", str(world["manifest"]), "--pin", world["name"], "--devel", "devel", "--profile", "none"]
    for k, v in kw.items():
        argv += [f"--{k.replace('_', '-')}", str(v)]
    out = io.StringIO()
    with redirect_stdout(out):
        rc = tool.main(argv)
    return rc, out.getvalue()


def artifact_files(overrides=None, drop=(), extra=()):
    """The artifacts.files of an envelope 3 record that digests every pinned file correctly, with the given changes."""
    files = {p: "sha256:" + hexdigest(FILES[p]) for p in PATHS if p not in drop}
    files.update(overrides or {})
    entries = [{"path": p, "digest": d} for p, d in files.items()]
    return entries + list(extra)


def make_record(world, source=None, envelope=3, artifacts="default", legacy_digests=False, **top):
    """An envelope 3 record by default. `legacy_digests` fills the places of the earlier envelopes (spec meta_hash, provenance) with correct base64 digests."""
    def b64(text):
        return base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode()
    prov = {"source_commit": source or world["pinned"]}
    specs = []
    if legacy_digests:
        prov.update(grammar_sha256=b64(FILES["proposals/atom-grammar/check_grammar.py"]), grammar_schema_sha256=b64(FILES["proposals/atom-grammar/instance-grammar.schema.yaml"]))
        specs = [{"id": p, "source_path": p, "meta_hash": b64(FILES[p])} for p in FILES if not p.startswith("proposals/atom-grammar/check_grammar") and not p.endswith("instance-grammar.schema.yaml")]
    rec = {"kind": "PrimitiveRelease", "version": "0.9.0", "provenance": prov, "specs": specs}
    if envelope is not None:
        rec["release"] = {"envelope": envelope}
    if artifacts == "default":
        artifacts = {"manifest_digest": "sha256:" + "0" * 64, "files": artifact_files()}
    if artifacts is not None:
        rec["artifacts"] = artifacts
    rec.update(top)
    p = world["tmp"] / "record.yaml"
    p.write_text(yaml.safe_dump(rec, allow_unicode=True), encoding="utf-8")
    return p


# ── record mode, envelope 3 ──────────────────────────────────────────────────────────────────────

def test_an_envelope_3_record_that_digests_every_pinned_file_passes_and_leaves_the_gates_open(world):
    rc, out = run(world, "record", record=make_record(world))
    assert rc == 0, out
    assert "PASS  source_commit: all 5 files are byte-identical" in out
    assert "INFO  record read: envelope 3: artifacts.files only" in out and "tools/release_record_conformance.py" in out
    assert "files the record digests itself (5 of 5)" in out
    assert "PASS  record digest coverage: all 5 pinned files have a digest of their own in the record, and each equals the pinned file" in out
    for gate in ("manifest origin", "trust anchor", "signer authority", "certificate validity", "digest encoding", "signing and publishing"):
        assert f"OPEN  {gate}" in out
    assert "OPEN  digest encoding: the record side is a contract" in out
    assert "readiness: checks_passed_gates_open" in out and "readiness: ready" not in out


def test_a_pinned_file_missing_from_the_artifacts_fails_even_when_the_commit_holds_it(world):
    rc, out = run(world, "record", record=make_record(world, artifacts={"files": artifact_files(drop=["schemas/atomic/role.yaml"])}))
    assert rc == 1
    assert "PASS  source_commit: all 5 files are byte-identical" in out
    assert "FAIL  record digest coverage: 4 of 5 present and equal: 1 have no digest of their own in the record and rest on the source commit alone: schemas/atomic/role.yaml" in out
    assert "PASS  record digest coverage" not in out


def test_an_artifact_digest_that_is_not_the_pinned_file_fails(world):
    other = "sha256:" + hexdigest("not the file\n")
    rc, out = run(world, "record", record=make_record(world, artifacts={"files": artifact_files({"schemas/atomic/role.yaml": other})}))
    assert rc == 1
    assert "FAIL  record digest of schemas/atomic/role.yaml: artifacts.files does not equal the pinned file" in out
    assert "FAIL  record digest coverage: 4 of 5 present and equal" in out and "have a digest that is not the pinned file's" in out
    assert "PASS  record digest coverage" not in out


@pytest.mark.parametrize("bad", [
    pytest.param(lambda h: "sha256:" + h.upper(), id="uppercase hex"),
    pytest.param(lambda h: h, id="no algorithm prefix"),
    pytest.param(lambda h: "sha512:" + h, id="another algorithm"),
    pytest.param(lambda h: "sha256:" + h[:-1], id="63 hex digits"),
    pytest.param(lambda h: "sha256:" + h + "0", id="65 hex digits"),
    pytest.param(lambda h: base64.b64encode(bytes.fromhex(h)).decode(), id="base64 of the digest"),
    pytest.param(lambda h: "sha256:" + h + "\n", id="trailing newline"),
    pytest.param(lambda h: None, id="no digest"),
    pytest.param(lambda h: 12345, id="not a string"),
])
def test_a_digest_that_is_not_the_contract_form_is_not_coverage(world, bad):
    path = "schemas/atomic/role.yaml"
    rc, out = run(world, "record", record=make_record(world, artifacts={"files": artifact_files({path: bad(hexdigest(FILES[path]))})}))
    assert rc == 1, out
    assert f"FAIL  record digest of {path}: artifacts.files does not equal the pinned file" in out
    assert "PASS  record digest coverage" not in out


def test_a_path_listed_twice_is_not_coverage_even_when_both_digests_are_right(world):
    path = "schemas/atomic/role.yaml"
    twice = {"files": artifact_files(extra=[{"path": path, "digest": "sha256:" + hexdigest(FILES[path])}])}
    rc, out = run(world, "record", record=make_record(world, artifacts=twice))
    assert rc == 1, out
    assert f"FAIL  record digest of {path}" in out
    assert "PASS  record digest coverage" not in out


def test_an_envelope_3_record_reads_the_artifacts_only_not_the_places_of_the_earlier_envelopes(world):
    # every legacy place (spec meta_hash, provenance digests) is right, the artifacts block is empty: that is not coverage for envelope 3
    rc, out = run(world, "record", record=make_record(world, legacy_digests=True, artifacts={"files": []}))
    assert rc == 1, out
    assert "FAIL  record digest coverage: 0 of 5 present and equal" in out


@pytest.mark.parametrize("envelope", [None, 1, 2])
def test_an_earlier_envelope_reads_its_own_places_and_not_the_artifacts(world, envelope):
    # the artifacts block is complete and right, the legacy places are empty: for envelope 1 and 2 (and a record with no envelope) that is not coverage
    rc, out = run(world, "record", record=make_record(world, envelope=envelope))
    assert rc == 1, out
    assert "FAIL  record digest coverage: 0 of 5 present and equal" in out
    assert "record read: envelope 3" not in out
    # ... and with its own places filled it passes, as it always did
    rc, out = run(world, "record", record=make_record(world, envelope=envelope, legacy_digests=True, artifacts=None))
    assert rc == 0, out
    assert "PASS  record digest coverage: all 5 pinned files" in out
    assert "OPEN  digest encoding: the base64 -> sha256:hex mapping" in out


@pytest.mark.parametrize("artifacts", [None, "files", {"manifest_digest": "x"}, {"files": "x"}, {"files": {"a": 1}}])
def test_an_envelope_3_record_without_an_artifacts_list_fails(world, artifacts):
    rc, out = run(world, "record", record=make_record(world, artifacts=artifacts))
    assert rc == 1, out
    assert "FAIL  record digest coverage: an envelope 3 record carries no artifacts.files list" in out


def test_artifact_entries_that_are_not_mappings_with_a_path_are_ignored_not_a_crash(world):
    junk = {"files": artifact_files(extra=[None, "x", {"digest": "sha256:" + "0" * 64}, {"path": 5, "digest": "x"}])}
    rc, out = run(world, "record", record=make_record(world, artifacts=junk))
    assert rc == 0, out


@pytest.mark.parametrize("envelope", [4, 0, "3", 3.0, True, [3]])
def test_an_envelope_this_tool_does_not_read_fails(world, envelope):
    rc, out = run(world, "record", record=make_record(world, envelope=envelope))
    assert rc == 1, out
    assert "FAIL  record envelope: release.envelope is " in out
    assert "PASS  record digest coverage" not in out


def test_the_source_commit_stays_mandatory_when_the_artifacts_are_complete(world):
    # a source commit that lacks a pinned file: the artifact digests are right, the record is still refused
    repo = world["repo"]
    bare = commit_files(repo, {"unrelated": "x\n"}, "unrelated")
    git(repo, "checkout", "-q", "-b", "other", world["pinned"])
    (repo / "schemas/atomic/role.yaml").unlink()
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "drops a pinned file")
    without = git(repo, "rev-parse", "HEAD")
    assert bare != without
    rc, out = run(world, "record", record=make_record(world, source=without))
    assert rc == 1, out
    assert "FAIL  source_commit: schemas/atomic/role.yaml: absent at the commit" in out
    rc, out = run(world, "record", record=make_record(world, provenance={"source_commit": None}))
    assert rc == 1 and "FAIL  source_commit: the record carries none" in out


# ── candidate mode: the release head's declaration ───────────────────────────────────────────────

def test_a_release_head_that_declares_every_pinned_file_passes_and_the_record_gate_stays_open(world):
    rc, out = run(world, "candidate", release_head=world["head"], version="0.1.0")
    assert rc == 0, out
    assert "PASS  release artifact declaration: the release head declares all 5 pinned files among its 5 release artifacts" in out
    assert "OPEN  record digest coverage: the declaration only says what the compiler will digest" in out
    assert "PASS  record digest coverage" not in out
    assert "at most 6" not in out
    assert "OPEN  digest encoding: the record side is a contract" in out
    for gate in ("trust anchor", "signer authority", "certificate validity", "signing and publishing"):
        assert f"OPEN  {gate}" in out
    assert "readiness: checks_passed_gates_open" in out


def test_a_declaration_with_more_paths_than_the_pin_is_fine(tmp_path):
    w = make_world(tmp_path, {"project.yaml": project_yaml(PATHS + ["docs/a.md", "docs/b.md"])})
    rc, out = run(w, "candidate", release_head=w["head"])
    assert rc == 0, out
    assert "among its 7 release artifacts" in out


def test_a_declaration_that_leaves_a_pinned_file_out_fails(tmp_path):
    w = make_world(tmp_path, {"project.yaml": project_yaml([p for p in PATHS if p != "schemas/atomic/role.yaml"])})
    rc, out = run(w, "candidate", release_head=w["head"])
    assert rc == 1
    assert "FAIL  release artifact declaration: the release head does not declare 1 of the 5 pinned files as release artifacts" in out and "schemas/atomic/role.yaml" in out
    assert "PASS  release artifact declaration" not in out
    assert "OPEN  record digest coverage: the record has to carry its own digest of all 12 pinned files" in out


def test_a_path_spelled_differently_is_not_the_pinned_path(tmp_path):
    paths = ["./" + p if p == "LICENSE.md" else p for p in PATHS]
    w = make_world(tmp_path, {"project.yaml": project_yaml(paths)})
    rc, out = run(w, "candidate", release_head=w["head"])
    assert rc == 1 and "FAIL  release artifact declaration" in out and "LICENSE.md" in out


@pytest.mark.parametrize("project, kind", [
    pytest.param({"other": "x\n"}, "no project.yaml", id="no project.yaml"),
    pytest.param({"project.yaml": yaml.safe_dump({"compiler_settings": {"vault_key_name": "k"}})}, "none at the release head", id="no declaration"),
    pytest.param({"project.yaml": yaml.safe_dump({})}, "none at the release head", id="empty project.yaml"),
])
def test_a_head_without_a_declaration_keeps_the_old_open_gate_and_is_not_a_failure(tmp_path, project, kind):
    w = make_world(tmp_path, project)
    rc, out = run(w, "candidate", release_head=w["head"])
    assert rc == 0, out
    assert kind in out and "INFO  release artifact declaration" in out
    assert "OPEN  record digest coverage: the record has to carry its own digest of all 12 pinned files" in out and "at most 6 of the 12" in out
    assert "PASS  release artifact declaration" not in out
    assert "OPEN  digest encoding: the base64 -> sha256:hex mapping" in out


@pytest.mark.parametrize("text", [
    pytest.param(yaml.safe_dump({"compiler_settings": {"release_artifacts": {"paths": "LICENSE.md"}}}), id="paths is a string"),
    pytest.param(yaml.safe_dump({"compiler_settings": {"release_artifacts": {"paths": [1, 2]}}}), id="paths are not strings"),
    pytest.param(yaml.safe_dump({"compiler_settings": {"release_artifacts": {}}}), id="no paths key"),
    pytest.param(yaml.safe_dump({"compiler_settings": {"release_artifacts": ["LICENSE.md"]}}), id="a list instead of a mapping"),
    pytest.param("compiler_settings: [unclosed\n", id="does not parse"),
])
def test_a_declaration_that_is_not_a_list_of_paths_fails(tmp_path, text):
    w = make_world(tmp_path, {"project.yaml": text})
    rc, out = run(w, "candidate", release_head=w["head"])
    assert rc == 1, out
    assert "FAIL  release artifact declaration" in out
    assert "PASS  release artifact declaration" not in out


def test_without_a_release_head_the_declaration_is_not_read_and_the_old_gate_stays(world):
    rc, out = run(world, "candidate")
    assert rc == 0, out
    assert "release artifact declaration" not in out
    assert "OPEN  release head: not given" in out
    assert "OPEN  record digest coverage: the record has to carry its own digest of all 12 pinned files" in out


# ── the release v0.2.1 record, frozen ────────────────────────────────────────────────────────────

# Immutable identifiers of the evidence, like the v0.2.0 ones: the record is read from the release COMMIT and its bytes are pinned by their SHA-256. A tag is a mutable
# reference and is not the evidence.
V021_SOURCE = "106965b8cea7cce2081beb77008753af21e68b46"
V021_RELEASE_COMMIT = "5e8c3219b52399e3e764b0b0bb27de710f5445a4"
V021_RECORD_SHA256 = "e5d8268aede0d24f02e60a151099a2fdc7615172ed3105b0a05b6b5d19addf63"
V021_PIN = "cic-primitives-73ae469-6a188078"


def has_commit(commit):
    return subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", f"{commit}^{{commit}}"], capture_output=True, check=False).returncode == 0


COMMITS = has_commit(V021_SOURCE) and has_commit(V021_RELEASE_COMMIT)
REQUIRED = os.environ.get("CIC_REQUIRE_RELEASE_HISTORY") == "1"


def test_the_history_of_release_v021_is_there_where_it_is_required():
    if not REQUIRED:
        return
    assert COMMITS, "CIC_REQUIRE_RELEASE_HISTORY=1 but the commits of release v0.2.1 are not in this clone (fetch-depth: 0)"


@pytest.mark.skipif(not COMMITS and not REQUIRED, reason="the history of release v0.2.1 is not in this clone; run with the full history (the gate does)")
def test_release_v021_holds_the_pinned_grammar_twelve_of_twelve(tmp_path):
    shown = subprocess.run(["git", "-C", str(REPO), "show", f"{V021_RELEASE_COMMIT}:release/cic-primitives-v0.2.1.yaml"], capture_output=True, check=False)
    assert shown.returncode == 0
    assert hashlib.sha256(shown.stdout).hexdigest() == V021_RECORD_SHA256, "the record of v0.2.1 is not the frozen one"
    record_path = tmp_path / "cic-primitives-v0.2.1.yaml"
    record_path.write_bytes(shown.stdout)
    tool = load_tool()
    out = io.StringIO()
    with redirect_stdout(out):
        rc = tool.main(["record", "--repo", str(REPO), "--manifest", str(REPO / "tests/fixtures/forms-pin-73ae469.yaml"), "--pin", V021_PIN, "--record", str(record_path)])  # the real 12-file profile
    text = out.getvalue()
    assert rc == 0, text
    assert "PASS  source_commit: all 12 files are byte-identical to the manifest" in text
    assert "files the record digests itself (12 of 12)" in text
    assert "PASS  record digest coverage: all 12 pinned files have a digest of their own in the record, and each equals the pinned file" in text
    for gate in ("trust anchor", "signer authority", "certificate validity", "signing and publishing"):
        assert f"OPEN  {gate}" in text
    assert "readiness: checks_passed_gates_open" in text
