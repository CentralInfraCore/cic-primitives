"""Tests of tools/release_candidate_precheck.py: each one breaks ONE thing in a small git repository and reads the message, not the exit status alone."""
import base64
import hashlib
import io
import os
import pathlib
import subprocess
import sys
from contextlib import redirect_stdout

import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import release_candidate_precheck as rcp  # noqa: E402

FILES = {
    "LICENSE.md": "licence\n",
    "proposals/atom-grammar/check_grammar.py": "print('grammar')\n",
    "proposals/atom-grammar/instance-grammar.schema.yaml": "type: object\n",
    "schemas/atomic/role.yaml": "role: 1\n",
    "é.yaml": "unicode path\n",
}
ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
       "PATH": "/usr/bin:/bin:/usr/local/bin"}


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=ENV)
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


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def b64(text):
    return base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode()


def manifest_for(commit, files=FILES):
    entries = [(p, sha(t)) for p, t in files.items()]
    digest = rcp.manifest_digest(entries)
    name = f"cic-primitives-{commit[:7]}-{digest[:8]}"
    return name, {"grammar": {name: {"repo": "x/y", "ref": "devel", "commit": commit,
                                     "files": [{"path": p, "sha256": s} for p, s in rcp.sorted_entries(entries)], "manifest_sha256": digest}}}


@pytest.fixture
def world(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "devel")
    pinned = commit_files(repo, FILES, "pinned")
    name, pins = manifest_for(pinned)
    mpath = tmp_path / "pins.yaml"
    mpath.write_text(yaml.safe_dump(pins), encoding="utf-8")
    return {"repo": repo, "pinned": pinned, "name": name, "pins": pins, "manifest": mpath, "tmp": tmp_path}


def run(world, mode="candidate", **kw):
    argv = [mode, "--repo", str(world["repo"]), "--manifest", str(world.get("manifest_override", world["manifest"])), "--pin", world.get("pin_override", world["name"]), "--devel", "devel"]
    for k, v in kw.items():
        argv += [f"--{k.replace('_', '-')}", str(v)]
    out = io.StringIO()
    with redirect_stdout(out):
        rc = rcp.main(argv)
    return rc, out.getvalue()


def rewrite_manifest(world, mutate):
    pins = yaml.safe_load(world["manifest"].read_text())
    mutate(pins["grammar"][world["name"]])
    p = world["tmp"] / "pins2.yaml"
    p.write_text(yaml.safe_dump(pins), encoding="utf-8")
    world["manifest_override"] = p


# ── candidate ────────────────────────────────────────────────────────────────────────────────────

def test_a_clean_candidate_passes_and_every_gate_stays_open(world):
    rc, out = run(world, release_head=world["pinned"], version="0.1.0")
    assert rc == 0, out
    assert "PASS  candidate: all 5 files are byte-identical" in out
    assert "PASS  release head: all 5 files are byte-identical" in out
    for gate in ("trust anchor", "signer authority", "certificate validity", "digest encoding", "signing and publishing"):
        assert f"OPEN  {gate}" in out
    assert "PASS  trust" not in out


def test_a_changed_file_at_the_candidate_fails(world):
    commit_files(world["repo"], {"schemas/atomic/role.yaml": "role: 2\n"}, "drift")
    head = git(world["repo"], "rev-parse", "HEAD")
    # the manifest still names the old bytes; the candidate is the new commit, which is also not the pinned one
    rc, out = run(world, commit=head)
    assert rc == 1
    assert "FAIL  candidate: schemas/atomic/role.yaml: pinned" in out
    assert "is not the pinned commit" in out


def test_an_absent_file_fails(world):
    rewrite_manifest(world, lambda pin: pin["files"].append({"path": "missing.md", "sha256": "0" * 64}))
    rc, out = run(world)
    assert rc == 1
    assert "FAIL  candidate: missing.md: absent at the commit" in out


def test_a_tampered_manifest_digest_fails(world):
    rewrite_manifest(world, lambda pin: pin.update(manifest_sha256="f" * 64))
    rc, out = run(world)
    assert rc == 1
    assert "FAIL  manifest digest" in out


def test_a_pin_name_that_does_not_carry_the_identity_fails(world):
    pins = yaml.safe_load(world["manifest"].read_text())
    body = pins["grammar"].pop(world["name"])
    pins["grammar"]["cic-primitives-abcdef0-12345678"] = body
    p = world["tmp"] / "renamed.yaml"
    p.write_text(yaml.safe_dump(pins), encoding="utf-8")
    world["manifest_override"], world["pin_override"] = p, "cic-primitives-abcdef0-12345678"
    rc, out = run(world)
    assert rc == 1
    assert "FAIL  pin name" in out


def test_the_manifest_is_ordered_by_path_bytes_not_by_line():
    a = rcp.sorted_entries([("é.yaml", "1"), ("z.yaml", "2")])
    assert [p for p, _ in a] == ["z.yaml", "é.yaml"]
    assert rcp.manifest_digest([("é.yaml", "b" * 64), ("z.yaml", "a" * 64)]) == hashlib.sha256(f"{'a' * 64}  z.yaml\n{'b' * 64}  é.yaml\n".encode()).hexdigest()


def test_the_manifest_order_is_utf8_bytes_not_utf16_units_and_not_the_digest():
    # U+FFFD < U+10000 in code points and in UTF-8; in UTF-16 the astral one (a surrogate pair) sorts first
    a, b = "a/\ufffd.yaml", "a/\U00010000.yaml"
    assert [p for p, _ in rcp.sorted_entries([(b, "1" * 64), (a, "2" * 64)])] == [a, b]
    # the digest does not order: the first path has the LARGER digest and still goes first
    assert [p for p, _ in rcp.sorted_entries([("b.md", "0" * 64), ("a.md", "f" * 64)])] == ["a.md", "b.md"]


def test_a_candidate_off_devel_fails(world):
    git(world["repo"], "checkout", "-q", "-b", "side")
    side = commit_files(world["repo"], {"x.txt": "x"}, "side")
    git(world["repo"], "checkout", "-q", "devel")
    _, pins = manifest_for(side)
    # same files at an off-devel commit
    name = next(iter(pins["grammar"]))
    p = world["tmp"] / "side.yaml"
    p.write_text(yaml.safe_dump(pins), encoding="utf-8")
    world["manifest_override"], world["pin_override"] = p, name
    rc, out = run(world)
    assert rc == 1
    assert "FAIL  candidate commit is on devel: it is not an ancestor" in out


def test_a_release_head_that_changes_a_pinned_file_fails(world):
    head = commit_files(world["repo"], {"LICENSE.md": "licence 2\n"}, "release prep touches a pinned file")
    rc, out = run(world, release_head=head)
    assert rc == 1
    assert "FAIL  release head: LICENSE.md: pinned" in out


def test_a_release_head_that_changes_only_other_files_passes_and_says_so(world):
    head = commit_files(world["repo"], {"release/r.yaml": "kind: PrimitiveRelease\n", "project.yaml": "v: 2\n"}, "release prep")
    rc, out = run(world, release_head=head)
    assert rc == 0, out
    assert "PASS  release head: all 5 files are byte-identical" in out
    assert "INFO  release head differs from the candidate in: project.yaml, release/r.yaml" in out


def test_no_release_head_is_an_open_item_not_a_pass(world):
    rc, out = run(world)
    assert rc == 0
    assert "OPEN  release head: not given" in out


def test_devel_having_moved_on_in_a_pinned_file_is_reported(world):
    commit_files(world["repo"], {"é.yaml": "moved\n"}, "devel moves")
    rc, out = run(world)
    assert rc == 0
    assert "has moved on in pinned files: é.yaml: a release cut from its head is NOT the pin" in out


def test_a_release_cut_from_the_moved_devel_head_is_not_the_pin(world):
    head = commit_files(world["repo"], {"é.yaml": "moved\n"}, "devel moves")
    rc, out = run(world, release_head=head)
    assert rc == 1
    assert "FAIL  release head: é.yaml: pinned" in out


@pytest.mark.parametrize("version,ok", [("0.1.1", True), ("0.2.0", True), ("1.0.0", True), ("0.1.5", False), ("0.3.0", False), ("2.0.0", False), ("1.0", False)])
def test_the_version_has_to_be_the_next_increment(world, version, ok):
    git(world["repo"], "tag", "primitives/@v0.1.0")
    rc, out = run(world, version=version)
    assert (rc == 0) == ok, out
    assert ("PASS  version" in out) == ok


def test_the_first_release_may_have_any_version(world):
    rc, out = run(world, version="0.9.0")
    assert rc == 0 and "no earlier tag" in out


# ── record ───────────────────────────────────────────────────────────────────────────────────────

def full_specs():
    """A record that digests every pinned file that is not one of the two provenance files."""
    return [{"id": p, "source_path": p, "meta_hash": b64(FILES[p])} for p in FILES if p not in rcp.PROVENANCE_FILES.values()]


def make_record(world, source, specs=None, prov_extra=None):
    prov = {"source_commit": source, "grammar_sha256": b64(FILES["proposals/atom-grammar/check_grammar.py"]),
            "grammar_schema_sha256": b64(FILES["proposals/atom-grammar/instance-grammar.schema.yaml"])}
    prov.update(prov_extra or {})
    rec = {"kind": "PrimitiveRelease", "version": "0.9.0", "provenance": prov,
           "specs": specs if specs is not None else full_specs()}
    p = world["tmp"] / "record.yaml"
    p.write_text(yaml.safe_dump(rec), encoding="utf-8")
    return p


def test_a_record_with_the_pin_and_all_digests_passes_but_leaves_the_gates_open(world):
    rc, out = run(world, "record", record=make_record(world, world["pinned"]))
    assert rc == 0, out
    assert "PASS  source_commit: all 5 files are byte-identical" in out
    assert "files the record digests itself (5 of 5)" in out
    assert "PASS  record digest coverage: all 5 pinned files have a digest of their own in the record" in out
    for gate in ("trust anchor", "signer authority", "certificate validity", "digest encoding", "signing and publishing"):
        assert f"OPEN  {gate}" in out
    assert "INFO  scope: PASS lines prove byte-identity" in out and "do not prove the signer's authority" in out


def test_a_record_that_digests_only_some_files_fails_even_when_the_commit_holds_all_of_them(world):
    only_role = [{"id": "role", "source_path": "schemas/atomic/role.yaml", "meta_hash": b64(FILES["schemas/atomic/role.yaml"])}]
    rc, out = run(world, "record", record=make_record(world, world["pinned"], specs=only_role))
    assert rc == 1
    assert "PASS  source_commit: all 5 files are byte-identical" in out
    assert "FAIL  record digest coverage: 3 of 5: 2 pinned files have no digest of their own in the record and rest on the source commit alone: LICENSE.md; \u00e9.yaml" in out


def test_all_digests_do_not_replace_the_source_commit(world):
    # the source commit stays mandatory: full digests with no commit is still a failure
    rc, out = run(world, "record", record=make_record(world, world["pinned"], prov_extra={"source_commit": None}))
    assert rc == 1 and "FAIL  source_commit: the record carries none" in out


def test_a_candidate_keeps_the_record_coverage_requirement_open(world):
    rc, out = run(world, release_head=world["pinned"])
    assert rc == 0
    assert "OPEN  record digest coverage: the record has to carry its own digest of all 12 pinned files" in out
    assert "INFO  scope: PASS lines prove byte-identity" in out and "do not prove the signer's authority" in out


def test_a_record_whose_source_commit_lacks_the_pin_fails(world):
    head = commit_files(world["repo"], {"schemas/atomic/role.yaml": "role: 2\n"}, "later")
    rc, out = run(world, "record", record=make_record(world, head))
    assert rc == 1
    assert "FAIL  source_commit: schemas/atomic/role.yaml: pinned" in out


def test_a_record_digest_that_is_not_the_pinned_file_fails_even_when_the_commit_holds_it(world):
    spec = [{"id": "role", "source_path": "schemas/atomic/role.yaml", "meta_hash": b64("role: 2\n")}]
    rc, out = run(world, "record", record=make_record(world, world["pinned"], specs=spec))
    assert rc == 1
    assert "FAIL  record digest of schemas/atomic/role.yaml: spec meta_hash does not equal the pinned file" in out


def test_a_provenance_digest_that_is_not_the_pinned_file_fails(world):
    rc, out = run(world, "record", record=make_record(world, world["pinned"], prov_extra={"grammar_sha256": b64("other")}))
    assert rc == 1
    assert "FAIL  record digest of proposals/atom-grammar/check_grammar.py: provenance.grammar_sha256" in out


def test_a_record_with_no_source_commit_fails(world):
    p = make_record(world, world["pinned"], prov_extra={"source_commit": None})
    rc, out = run(world, "record", record=p)
    assert rc == 1 and "FAIL  source_commit: the record carries none" in out


def test_a_source_commit_that_does_not_exist_fails(world):
    rc, out = run(world, "record", record=make_record(world, "0" * 40))
    assert rc == 1 and "FAIL  source_commit: does not exist in this repository" in out


def test_a_record_of_another_kind_fails(world):
    p = world["tmp"] / "r.yaml"
    p.write_text("kind: Something\n")
    rc, out = run(world, "record", record=p)
    assert rc == 1 and "kind is 'Something'" in out


def test_the_record_mode_needs_a_record(world):
    with pytest.raises(SystemExit):
        rcp.main(["record", "--repo", str(world["repo"]), "--manifest", str(world["manifest"]), "--pin", world["name"]])


def test_a_malformed_base64_digest_is_a_failure_not_a_crash(world):
    spec = [{"id": "role", "source_path": "schemas/atomic/role.yaml", "meta_hash": "not base64!"}]
    rc, out = run(world, "record", record=make_record(world, world["pinned"], specs=spec))
    assert rc == 1 and "FAIL  record digest of schemas/atomic/role.yaml" in out


def test_the_reencoding_is_lossless():
    assert rcp.b64_to_hex(b64("x")) == sha("x")
    with pytest.raises(Exception):
        rcp.b64_to_hex("%%%")


def test_an_unknown_pin_name_stops(world):
    world["pin_override"] = "nope"
    with pytest.raises(SystemExit):
        run(world)


# ── the negative evidence on release v0.2.0 (frozen, reproducible, never fixed away) ──────────────

REPO = pathlib.Path(__file__).resolve().parents[1]
V020_SOURCE = "9c67ea4478d3a7ebe74d31a00ec02db589ac9e32"
V020_PIN = "cic-primitives-73ae469-6a188078"


def has_commit(commit):
    return subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", f"{commit}^{{commit}}"], capture_output=True).returncode == 0


# Where the history is required (the gate sets CIC_REQUIRE_RELEASE_HISTORY), a missing commit or tag is a FAILURE, not a skip: a skipped test proves nothing.
HISTORY = has_commit(V020_SOURCE) and has_commit("primitives/@v0.2.0")
REQUIRED = os.environ.get("CIC_REQUIRE_RELEASE_HISTORY") == "1"


def test_the_history_of_release_v020_is_there_where_it_is_required():
    if REQUIRED:
        assert HISTORY, "CIC_REQUIRE_RELEASE_HISTORY=1 but the commit or the tag of release v0.2.0 is not in this clone (fetch-depth: 0 and the tags)"


@pytest.mark.skipif(not HISTORY and not REQUIRED, reason="the history and the tag of release v0.2.0 are not in this clone; run with the full history and the tags (the gate does)")
def test_release_v020_does_not_hold_the_pinned_grammar(tmp_path):
    # the v0.2.0 record lives on the tag, not on devel
    tag = subprocess.run(["git", "-C", str(REPO), "show", "primitives/@v0.2.0:release/cic-primitives-v0.2.0.yaml"], capture_output=True)
    assert tag.returncode == 0
    record_path = tmp_path / "cic-primitives-v0.2.0.yaml"
    record_path.write_bytes(tag.stdout)
    out = io.StringIO()
    with redirect_stdout(out):
        rc = rcp.main(["record", "--repo", str(REPO), "--manifest", str(REPO / "tests/fixtures/forms-pin-73ae469.yaml"), "--pin", V020_PIN, "--record", str(record_path)])
    text = out.getvalue()
    assert rc == 1
    # 4 pinned files are absent from the source commit, 5 are there with other bytes, 3 are identical
    assert text.count("absent at the commit") == 4
    assert text.count("source_commit: ") - text.count("absent at the commit") == 5
    # the record's own digests of four pinned files are not the pinned files
    assert text.count("FAIL  record digest of ") == 4
    # and only 2 of the 12 are digested by the record AND equal
    assert "files the record digests itself (2 of 12)" in text
    assert "FAIL  record digest coverage: 2 of 12" in text
