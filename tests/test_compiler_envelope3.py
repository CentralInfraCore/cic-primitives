"""The compiler writes envelope 3 (docs/en/RELEASE-RECORD-CONTRACT.md), and is held to the frozen yardstick of PR #25.

The compiler does not certify its own output here. What it writes is read back by the reference verifier (tools/release_record_conformance.py, which does not import
the compiler's new functions), compared with values that were recomputed outside this code base (tests/fixtures/envelope3), and put through the same vectors as the
golden record. The planted-defect proof that these tests can fail is tests/test_compiler_envelope3_planted.py.
"""
import ast
import copy
import datetime
import itertools
import json
import pathlib
import re
import subprocess
import sys

import pytest
import yaml
from jsonschema import ValidationError, validate

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import e3_compiler_support as sup  # noqa: E402
import e3_fixtures as fx  # noqa: E402
import e3_vectors as vec  # noqa: E402

C = sup.load_compiler()
V = fx.load_verifier()
ROOT = fx.ROOT


@pytest.fixture(scope="module")
def repos(tmp_path_factory):
    base = tmp_path_factory.mktemp("e3compiler")
    golden = fx.build_repo(base / "golden", fx.GOLDEN_FILES)
    special = fx.build_repo(base / "special", fx.SPECIAL_FILES)
    return {"golden": (base / "golden", golden), "special": (base / "special", special)}


def run_release_in(directory, monkeypatch, C=C):
    monkeypatch.chdir(directory)
    C.run_release()


# ---------------------------------------------------------------- the compiler's reading of the git tree and its declaration rules

def test_the_envelope_the_compiler_writes_is_3():
    assert C.RELEASE_ENVELOPE_VERSION == 3


def test_the_hash_payload_of_envelope_3_is_that_of_envelope_2_and_unknown_ones_have_none():
    golden = fx.load_golden()
    assert C._release_hash_payload(golden, 3) == C._release_hash_payload(golden, 2)
    assert C._release_hash_payload(golden, 4) is None
    assert C._release_hash_payload(golden, 0) is None


@pytest.mark.parametrize("which", ["golden", "special"])
def test_the_compilers_tree_listing_is_the_references_and_the_plumbings(which, repos, monkeypatch):
    path, commit = repos[which]
    monkeypatch.chdir(path)
    listing = C._git_tree(commit)
    assert listing == V.load_tree(str(path), commit) == sup.git_tree_via_plumbing(path, commit)


@pytest.mark.parametrize("case", vec.DECLARATIONS, ids=lambda c: c[0])
def test_the_compiler_refuses_a_declaration_for_the_reason_of_the_vector(case, repos, monkeypatch):
    # the same table as the reference verifier's declaration vectors, run on the compiler's own function
    _id, reason, project = case
    path, commit = repos["special"]
    monkeypatch.chdir(path)
    refusal = C._validate_release_artifact_declaration(fx.expand(project, {}), C._git_tree(commit))
    assert (refusal[0] if refusal else None) == reason, refusal


def test_the_compiler_and_the_reference_agree_on_every_declaration_vector(repos, monkeypatch):
    path, commit = repos["special"]
    monkeypatch.chdir(path)
    tree = C._git_tree(commit)
    for _id, _reason, project in vec.DECLARATIONS:
        project = fx.expand(project, {})
        ours = C._validate_release_artifact_declaration(project, tree)
        theirs = V.validate_declaration(project, tree)
        assert (ours and ours[0]) == (theirs and theirs[0]), _id


@pytest.mark.parametrize("order", list(itertools.permutations(range(3))))
def test_the_same_declared_set_in_any_order_gives_the_same_artifacts_block(order, repos, monkeypatch):
    path, commit = repos["golden"]
    monkeypatch.chdir(path)
    names = sup.golden_paths()
    block = C._build_release_artifacts([names[i] for i in order], C._git_tree(commit))
    expected = fx.load_expected()
    assert block == {"manifest_digest": expected["manifest_digest"], "files": expected["files"]}
    # byte-identical on repeated runs
    again = C._build_release_artifacts([names[i] for i in order], C._git_tree(commit))
    assert json.dumps(block, sort_keys=True) == json.dumps(again, sort_keys=True)


def test_the_listed_order_is_utf8_bytes_not_utf16_units(tmp_path, monkeypatch):
    # U+FF5E (EF BD 9E) sorts before U+10000 (F0 90 80 80) in UTF-8; in UTF-16 the surrogate D800 would put U+10000 first
    files = [(chr(0xFF5E) + ".txt", b"x\n", "100644"), (chr(0x10000) + ".txt", b"y\n", "100644")]
    commit = fx.build_repo(tmp_path, files)
    monkeypatch.chdir(tmp_path)
    paths = [p for p, _c, _m in reversed(files)]
    block = C._build_release_artifacts(paths, C._git_tree(commit))
    assert [f["path"] for f in block["files"]] == [chr(0xFF5E) + ".txt", chr(0x10000) + ".txt"]
    record = {"artifacts": block}
    assert V._check_order(record) is None


# ---------------------------------------------------------------- what run_release writes

def test_run_release_writes_an_envelope_3_record_that_meets_the_contract(tmp_path, monkeypatch):
    root, version, commit, calls = sup.release_sandbox(C, tmp_path, monkeypatch)
    run_release_in(root, monkeypatch)
    bundle = sup.written_record(root, version)
    assert bundle["release"]["envelope"] == bundle["provenance"]["envelope"] == 3
    assert bundle["provenance"]["source_commit"] == commit
    # the artifacts block equals the independently recomputed one (sha256sum of the worked example), not the output of another run of the compiler
    expected = fx.load_expected()
    assert bundle["artifacts"] == {"manifest_digest": expected["manifest_digest"], "files": expected["files"]}
    report = V.verify(sup.countersign(bundle), str(root))
    assert report["record"].status == "PASS", (report["record"].reason, report["record"].detail)
    assert report["blobs"].status == "PASS", report["blobs"].failures
    assert report["crypto"]["status"] == "PASS"
    assert V.first_reason(report) is None


def test_the_hash_the_compiler_wrote_is_the_independent_one(tmp_path, monkeypatch):
    root, version, _commit, _calls = sup.release_sandbox(C, tmp_path, monkeypatch)
    run_release_in(root, monkeypatch)
    bundle = sup.written_record(root, version)
    assert bundle["release"]["build_hash"] == fx.independent_build_hash(bundle)


def test_without_a_counter_signature_the_compilers_record_is_incomplete_not_passed(tmp_path, monkeypatch):
    root, version, _commit, _calls = sup.release_sandbox(C, tmp_path, monkeypatch)
    run_release_in(root, monkeypatch)
    report = V.verify(sup.written_record(root, version), str(root))
    assert (report["record"].status, report["blobs"].status, report["crypto"]["status"]) == ("PASS", "PASS", "INCOMPLETE")


def test_the_digest_is_of_the_blob_bytes_not_of_the_working_directory(tmp_path, monkeypatch):
    root, version, _commit, _calls = sup.release_sandbox(C, tmp_path, monkeypatch)
    # the working copies are changed after the commit: CRLF, other bytes, a file removed
    (root / "a.txt").write_bytes(b"alpha\r\n")
    (root / "d" / "b.txt").write_bytes(b"another\n")
    (root / (fx.E_ACUTE + ".txt")).unlink()
    run_release_in(root, monkeypatch)
    bundle = sup.written_record(root, version)
    assert bundle["artifacts"]["files"] == fx.load_expected()["files"]


def test_a_filter_in_the_checkout_does_not_reach_the_digest(tmp_path, monkeypatch):
    attributes = ("100644", b"*.txt text eol=crlf\n")
    files = sup.commit_files(sup.golden_paths()) + [(".gitattributes", attributes[1], attributes[0])]
    root, version, _commit, _calls = sup.release_sandbox(C, tmp_path, monkeypatch, files=files)
    fx._git(root, "config", "core.autocrlf", "true")
    run_release_in(root, monkeypatch)
    assert sup.written_record(root, version)["artifacts"]["files"] == fx.load_expected()["files"]


def test_the_declaration_comes_from_the_commit_not_from_the_working_directory(tmp_path, monkeypatch):
    root, _version, commit, _calls = sup.release_sandbox(C, tmp_path, monkeypatch)
    # the working copy of project.yaml declares something else entirely; the commit's declaration is the one that is read
    (root / "project.yaml").write_text(sup.project_yaml(["a.txt"]))
    project = C._declaration_from_commit(C._git_tree(commit))
    assert project["compiler_settings"]["release_artifacts"]["paths"] == sup.golden_paths()


def test_a_working_directory_that_declares_something_else_stops_the_release(tmp_path, monkeypatch, capsys):
    root, _version, _commit, calls = sup.release_sandbox(C, tmp_path, monkeypatch)
    (root / "project.yaml").write_text(sup.project_yaml(["a.txt"]))
    with pytest.raises(SystemExit) as stop:
        run_release_in(root, monkeypatch)
    out = capsys.readouterr().out
    assert stop.value.code == 1 and "worktree_differs_from_source_commit" in out and "project.yaml" in out
    assert calls["vault"] == 0 and not (root / "release").exists()


def test_a_declaration_in_the_working_directory_only_is_no_declaration(tmp_path, monkeypatch, capsys):
    files = list(fx.GOLDEN_FILES)   # the commit has no project.yaml
    root, version, _commit, calls = sup.release_sandbox(C, tmp_path, monkeypatch, files=files)
    (root / "project.yaml").write_text(sup.project_yaml(sup.golden_paths()))
    with pytest.raises(SystemExit) as stop:
        run_release_in(root, monkeypatch)
    assert stop.value.code == 1
    assert "declaration_missing" in capsys.readouterr().out
    assert not (root / "release").exists() and calls["vault"] == 0


def test_the_working_directory_does_not_stand_in_for_the_commit_on_the_paths_either(tmp_path, monkeypatch, capsys):
    # a file that is only in the working directory, not in the commit, is not an artifact
    root, version, _commit, calls = sup.release_sandbox(C, tmp_path, monkeypatch, paths=sup.golden_paths() + ["untracked.txt"])
    (root / "untracked.txt").write_text("only here\n")
    with pytest.raises(SystemExit) as stop:
        run_release_in(root, monkeypatch)
    assert stop.value.code == 1
    assert "declared_path_absent" in capsys.readouterr().out
    assert calls["vault"] == 0


@pytest.mark.parametrize("paths,reason", [
    ([], "declaration_empty"),
    (["a.txt", "a.txt"], "declaration_path_duplicate"),
    (["../a.txt"], "declaration_path_form"),
    (["/a.txt"], "declaration_path_form"),
    (["d"], "declared_path_not_regular"),
    (["missing.txt"], "declared_path_absent"),
])
def test_run_release_refuses_before_any_vault_call(paths, reason, tmp_path, monkeypatch, capsys):
    root, _v, _commit, calls = sup.release_sandbox(C, tmp_path, monkeypatch, paths=paths)
    with pytest.raises(SystemExit) as stop:
        run_release_in(root, monkeypatch)
    assert stop.value.code == 1
    assert reason in capsys.readouterr().out
    assert calls["vault"] == 0
    assert not (root / "release").exists()


def test_run_release_without_any_declaration_stops_with_declaration_missing(tmp_path, monkeypatch, capsys):
    plain = yaml.dump({"project": {"name": "x"}, "compiler_settings": {"source_dir": "schemas"}}).encode()
    root, _v, _commit, calls = sup.release_sandbox(C, tmp_path, monkeypatch, files=list(fx.GOLDEN_FILES) + [("project.yaml", plain, "100644")])
    with pytest.raises(SystemExit):
        run_release_in(root, monkeypatch)
    assert "declaration_missing" in capsys.readouterr().out and calls["vault"] == 0


def test_run_release_refuses_when_it_cannot_name_the_source_commit(tmp_path, monkeypatch, capsys):
    root, _v, _commit, calls = sup.release_sandbox(C, tmp_path, monkeypatch)
    real = subprocess.run

    def failing(command, *args, **kwargs):
        if list(command[:3]) == ["git", "rev-parse", "HEAD"]:
            raise subprocess.CalledProcessError(128, command)
        return real(command, *args, **kwargs)

    monkeypatch.setattr(C.subprocess, "run", failing)
    with pytest.raises(SystemExit) as stop:
        run_release_in(root, monkeypatch)
    assert stop.value.code == 1
    assert calls["vault"] == 0 and not (root / "release").exists()


def test_the_source_commit_is_never_null_and_is_forty_lowercase_hex(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)   # not a git repository
    with pytest.raises(SystemExit) as stop:
        C._source_commit()
    assert stop.value.code == 1
    root = tmp_path / "r"
    root.mkdir()
    commit = sup.checkout(root, list(fx.GOLDEN_FILES))
    monkeypatch.chdir(root)
    assert C._source_commit() == commit and re.fullmatch(r"[0-9a-f]{40}", commit)
    assert C._collect_provenance()["source_commit"] == commit


@pytest.mark.parametrize("printed", ["", "HEAD", "abc", "a" * 39, "a" * 41, "A" * 40, "g" * 40, "a" * 64, "a" * 40 + "\n" + "b" * 40])
def test_a_source_commit_that_is_not_forty_lowercase_hex_is_refused(printed, monkeypatch):
    real = subprocess.run

    def said(command, *args, **kwargs):
        if list(command[:3]) == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(command, 0, stdout=printed + "\n", stderr="")
        return real(command, *args, **kwargs)

    monkeypatch.setattr(C.subprocess, "run", said)
    with pytest.raises(SystemExit) as stop:
        C._source_commit()
    assert stop.value.code == 1


PATH_VECTORS = [(x["id"], fx.expand(x["ops"][0]["value"], {})) for x in vec.PATHS
                if x["ops"][0]["op"] == "set" and x["ops"][0]["at"] == "artifacts.files.0.path" and isinstance(x["ops"][0]["value"], str)]


@pytest.mark.parametrize("vid,path", PATH_VECTORS, ids=[p[0] for p in PATH_VECTORS])
def test_the_compilers_path_rule_refuses_every_path_of_the_path_vectors(vid, path):
    assert C._release_artifact_path_problem(path) is not None, vid


def test_the_compilers_path_rule_refuses_the_rest_of_the_path_vectors():
    for odd in (7, None, "", chr(0xD800) + ".txt"):
        assert C._release_artifact_path_problem(odd) is not None, odd


@pytest.mark.parametrize("path", [p for p, _c, _m in fx.GOLDEN_FILES] + ["A.txt", "a b.txt", "d/e/f.g", ".hidden", "d/.hidden", "a..b", "-x"])
def test_the_compilers_path_rule_accepts_ordinary_paths(path):
    assert C._release_artifact_path_problem(path) is None


def test_run_release_checks_the_source_paths_of_the_specs_it_writes(tmp_path, monkeypatch):
    root, version, _commit, _calls = sup.release_sandbox(C, tmp_path, monkeypatch)
    seen = []
    real = C._check_unique_source_paths
    monkeypatch.setattr(C, "_check_unique_source_paths", lambda specs: (seen.append(list(specs)), real(specs))[1])
    run_release_in(root, monkeypatch)
    written = sup.written_record(root, version)
    assert seen and [e["source_path"] for e in seen[0]] == [e["source_path"] for e in written["specs"]]


def test_two_runs_of_the_same_release_give_the_same_build_hash(tmp_path, monkeypatch):
    root, version, _commit, _calls = sup.release_sandbox(C, tmp_path, monkeypatch)
    sup.fix_the_clock(monkeypatch, C)
    run_release_in(root, monkeypatch)
    first = sup.written_record(root, version)
    (root / "release" / ("cic-primitives-v%s.yaml" % version)).unlink()
    run_release_in(root, monkeypatch)
    second = sup.written_record(root, version)
    assert first["release"]["build_hash"] == second["release"]["build_hash"]
    assert fx.independent_canonical_bytes(first) == fx.independent_canonical_bytes(second)


def test_duplicate_spec_source_paths_are_refused(monkeypatch):
    specs = [{"source_path": "schemas/atomic/a.yaml"}, {"source_path": "schemas/atomic/a.yaml"}]
    with pytest.raises(SystemExit) as stop:
        C._check_unique_source_paths(specs)
    assert stop.value.code == 1
    C._check_unique_source_paths([{"source_path": "schemas/atomic/a.yaml"}, {"source_path": "schemas/atomic/b.yaml"}])


# ---------------------------------------------------------------- the rest of the record is the source commit's too

SHAPE = "schemas/atomic/shape.yaml"


def refused_for(root, monkeypatch, capsys, calls, *words):
    with pytest.raises(SystemExit) as stop:
        run_release_in(root, monkeypatch)
    out = capsys.readouterr().out
    assert stop.value.code == 1 and "worktree_differs_from_source_commit" in out, out
    for word in words:
        assert word in out, out
    assert calls["vault"] == 0 and not (root / "release").exists()


def test_a_clean_sandbox_is_consistent_and_the_guard_names_what_it_checked(tmp_path, monkeypatch, capsys):
    root, version, _commit, _calls = sup.release_sandbox(C, tmp_path, monkeypatch)
    assert sup.porcelain(root) == ""
    run_release_in(root, monkeypatch)
    assert "are the source commit's bytes" in capsys.readouterr().out


def test_an_ignored_schema_file_leaves_git_status_clean_and_is_refused(tmp_path, monkeypatch, capsys):
    root, _v, _c, calls = sup.release_sandbox(C, tmp_path, monkeypatch, extra_files=[(".gitignore", b"schemas/atomic/ignored.yaml\n", "100644")])
    import test_compiler as tc
    (root / "schemas" / "atomic" / "ignored.yaml").write_text(tc._META.format(name="Ignored", version="v0.1.dev") + "spec:\n  kind: AtomicPrimitive\n  fields: {a: 1}\n")
    assert sup.porcelain(root) == "", "the premise: the status the prerequisites ask is clean"
    refused_for(root, monkeypatch, capsys, calls, "schemas/atomic/ignored.yaml", "not in the source commit")


def test_an_assume_unchanged_schema_file_with_other_bytes_is_refused(tmp_path, monkeypatch, capsys):
    root, _v, _c, calls = sup.release_sandbox(C, tmp_path, monkeypatch)
    fx._git(root, "update-index", "--assume-unchanged", SHAPE)
    (root / SHAPE).write_text((root / SHAPE).read_text().replace("a: 1", "a: 2"))
    assert sup.porcelain(root) == ""
    refused_for(root, monkeypatch, capsys, calls, SHAPE, "differ from the source commit")


def test_a_line_end_filter_leaves_git_status_clean_and_is_refused(tmp_path, monkeypatch, capsys):
    root, _v, _c, calls = sup.release_sandbox(C, tmp_path, monkeypatch, extra_files=[(".gitattributes", b"*.yaml text eol=crlf\n", "100644")])
    for yaml_file in (root / "schemas").rglob("*.yaml"):
        yaml_file.write_bytes(yaml_file.read_bytes().replace(b"\n", b"\r\n"))
    assert sup.porcelain(root) == "", "the premise: a CRLF working copy of a text=eol=crlf file is clean to git"
    refused_for(root, monkeypatch, capsys, calls, "differ from the source commit")


def test_a_skip_worktree_schema_file_that_is_missing_is_refused(tmp_path, monkeypatch, capsys):
    import test_compiler as tc
    content = (tc._META.format(name="Sparse", version="v0.1.dev") + "spec:\n  kind: AtomicPrimitive\n  fields: {a: 1}\n").encode()
    root, _v, _c, calls = sup.release_sandbox(C, tmp_path, monkeypatch, extra_files=[("schemas/atomic/sparse.yaml", content, "100644")])
    fx._git(root, "update-index", "--skip-worktree", "schemas/atomic/sparse.yaml")
    (root / "schemas" / "atomic" / "sparse.yaml").unlink()
    assert sup.porcelain(root) == "", "the premise: a sparse checkout leaves the status clean"
    refused_for(root, monkeypatch, capsys, calls, "schemas/atomic/sparse.yaml", "does not offer")


@pytest.mark.parametrize("path", ["dependency.yaml", "proposals/atom-grammar/check_grammar.py", "proposals/atom-grammar/instance-grammar.schema.yaml", "project.yaml"])
def test_an_input_of_the_provenance_or_the_issuer_with_other_bytes_is_refused(path, tmp_path, monkeypatch, capsys):
    root, _v, _c, calls = sup.release_sandbox(C, tmp_path, monkeypatch)
    fx._git(root, "update-index", "--assume-unchanged", path)
    with open(root / path, "ab") as fh:
        fh.write(b"\n# changed after the commit\n")
    assert sup.porcelain(root) == ""
    refused_for(root, monkeypatch, capsys, calls, path, "differ from the source commit")


def test_a_provenance_input_that_the_commit_holds_and_the_working_directory_lacks_is_refused(tmp_path, monkeypatch, capsys):
    path = "dependency.yaml"     # the grammar files are read by the release grammar gate first, which stops on its own
    root, _v, _c, calls = sup.release_sandbox(C, tmp_path, monkeypatch)
    fx._git(root, "update-index", "--skip-worktree", path)
    (root / path).unlink()
    assert sup.porcelain(root) == ""
    refused_for(root, monkeypatch, capsys, calls, path, "missing from the working directory")


def test_an_ignored_commitment_file_that_the_commit_does_not_hold_is_refused(tmp_path, monkeypatch, capsys):
    root, _v, _c, calls = sup.release_sandbox(C, tmp_path, monkeypatch, extra_files=[(".gitignore", b"commitment.yaml\n", "100644")])
    (root / "commitment.yaml").write_text("kind: DeveloperCommitment\n")
    assert sup.porcelain(root) == ""
    refused_for(root, monkeypatch, capsys, calls, "commitment.yaml", "not in the source commit")


def test_a_symbolic_link_for_a_schema_file_is_refused(tmp_path, monkeypatch, capsys):
    root, _v, _c, calls = sup.release_sandbox(C, tmp_path, monkeypatch)
    fx._git(root, "update-index", "--assume-unchanged", SHAPE)
    (root / SHAPE).unlink()
    (root / SHAPE).symlink_to(root / "schemas" / "examples" / "c.yaml")
    refused_for(root, monkeypatch, capsys, calls, SHAPE)


def test_the_tree_selection_of_schema_files_is_the_glob_selection(tmp_path, monkeypatch):
    import test_compiler as tc
    meta = tc._META.format(name="X", version="v0.1.dev") + "spec:\n  kind: AtomicPrimitive\n  fields: {a: 1}\n"
    extra = [("schemas/atomic/.hidden.yaml", meta.encode(), "100644"), ("schemas/atomic/empty.yaml", b"", "100644"), ("schemas/atomic/nested/deep.yaml", meta.encode(), "100644"),
             ("schemas/aggregate/agg.yaml", meta.encode(), "100644"), ("schemas/examples/x.yaml", meta.encode(), "100644"), ("schemas/atomic/notes.txt", b"x", "100644"),
             ("schemas/.dot/inside.yaml", meta.encode(), "100644"), ("other/atomic/outside.yaml", meta.encode(), "100644")]
    root, _v, commit, _c = sup.release_sandbox(C, tmp_path, monkeypatch, extra_files=extra)
    from_tree = C._release_schema_files_in_tree(C._git_tree(commit))
    assert from_tree == C._release_schema_files()
    assert "schemas/atomic/nested/deep.yaml" in from_tree and "schemas/atomic/.hidden.yaml" not in from_tree and "schemas/atomic/empty.yaml" not in from_tree


# ---------------------------------------------------------------- the signature covers what the compiler wrote

@pytest.fixture(scope="module")
def compiler_record(tmp_path_factory):
    mp = pytest.MonkeyPatch()
    try:
        root = tmp_path_factory.mktemp("e3written")
        directory, version, _commit, _calls = sup.release_sandbox(C, root, mp)
        mp.chdir(directory)
        C.run_release()
        return sup.countersign(sup.written_record(directory, version))
    finally:
        mp.undo()


@pytest.mark.parametrize("vector", vec.CRYPTO, ids=lambda x: x["id"])
def test_the_coverage_vectors_on_the_record_the_compiler_wrote(vector, compiler_record):
    bundle = fx.apply_ops(compiler_record, vector["ops"], {})
    if vector["reauth"] != "none":
        fx.reauthenticate(bundle, vector["reauth"])
    crypto = V.check_crypto(bundle)
    assert crypto["status"] == "FAIL"
    assert tuple(crypto[p].reason or crypto[p].status for p in ("build_hash", "signature", "countersign")) == vector["parts"]


@pytest.mark.parametrize("name,ops", vec.COVERAGE_MUTATIONS, ids=[m[0] for m in vec.COVERAGE_MUTATIONS])
def test_the_same_defect_re_authenticated_is_a_validly_signed_compiler_record(name, ops, compiler_record):
    assert V.check_crypto(fx.reauthenticate(fx.apply_ops(compiler_record, ops, {})))["status"] == "PASS"


def test_the_record_vectors_hold_for_the_compilers_record_too(compiler_record):
    # a structural defect applied to what the compiler wrote is refused for the reason of the vector, and the crypto layer of the re-authenticated record passes
    applied = 0
    for vector in vec.ALL_RECORD:
        # vectors that name golden-only content (the second spec's source path) or that are positive cases are the golden record's own
        if vector["id"] in ("specs-share-a-source-path",) or vector["reason"] is None:
            continue
        applied += 1
        bundle = fx.apply_ops(compiler_record, vector["ops"], {})
        if vector["reauth"] != "none":
            fx.reauthenticate(bundle, vector["reauth"])
        result = V.check_record(bundle)
        assert (result.status, result.reason) == ("FAIL", vector["reason"]), vector["id"]
    assert applied > 80


# ---------------------------------------------------------------- the old envelopes keep verifying, on real historical records

def verify_release(path, monkeypatch):
    sup.fix_the_clock(monkeypatch, C)
    monkeypatch.chdir(ROOT)
    C.run_verify_release(str(path))


def test_the_real_envelope_1_record_still_verifies(monkeypatch, capsys):
    record = ROOT / "release" / "cic-primitives-v0.1.5.yaml"
    bundle = yaml.safe_load(record.read_text())
    assert "provenance" not in bundle and "envelope" not in bundle["release"]
    verify_release(record, monkeypatch)
    out = capsys.readouterr().out
    assert "release envelope: v1" in out and "build_hash verified" in out and "Release signature verified" in out


V020_RELEASE_COMMIT = "960ee0f048d969a85ad20819bc0f2366ad91fa40"
V020_RECORD_SHA256 = "955fab2d6d9638c773f29fbe97a3279f9f10b9539c4e3e79957df0acef9a57a6"


def test_the_real_envelope_2_record_still_verifies(tmp_path, monkeypatch, capsys):
    import hashlib
    import os
    have = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", V020_RELEASE_COMMIT + "^{commit}"], capture_output=True).returncode == 0
    if not have:
        assert os.environ.get("CIC_REQUIRE_RELEASE_HISTORY") != "1", "CIC_REQUIRE_RELEASE_HISTORY=1 but the commit of release v0.2.0 is not in this clone"
        pytest.skip("the history of release v0.2.0 is not in this clone")
    blob = subprocess.run(["git", "-C", str(ROOT), "show", "%s:release/cic-primitives-v0.2.0.yaml" % V020_RELEASE_COMMIT], capture_output=True, check=True).stdout
    assert hashlib.sha256(blob).hexdigest() == V020_RECORD_SHA256, "this is not the frozen record of v0.2.0"
    record = tmp_path / "cic-primitives-v0.2.0.yaml"
    record.write_bytes(blob)
    bundle = yaml.safe_load(blob)
    assert bundle["release"]["envelope"] == bundle["provenance"]["envelope"] == 2
    verify_release(record, monkeypatch)
    out = capsys.readouterr().out
    assert "release envelope: v2" in out and "build_hash verified" in out and "counter-signature verified" in out


def test_an_unknown_envelope_is_still_refused_by_verify_release(tmp_path, monkeypatch):
    bundle = yaml.safe_load((ROOT / "release" / "cic-primitives-v0.1.5.yaml").read_text())
    bundle["release"]["envelope"] = 99
    record = tmp_path / "r.yaml"
    record.write_text(yaml.dump(bundle, sort_keys=False))
    with pytest.raises(SystemExit) as stop:
        verify_release(record, monkeypatch)
    assert stop.value.code == 1


def test_verify_release_reads_an_envelope_3_record_and_says_what_it_leaves_to_the_conformance_check(compiler_record, tmp_path, monkeypatch, capsys):
    record = tmp_path / "r.yaml"
    record.write_text(yaml.dump(compiler_record, sort_keys=False))
    verify_release(record, monkeypatch)
    out = capsys.readouterr().out
    assert "release envelope: v3" in out and "build_hash verified" in out
    assert "NOT proven" in out and "release_record_conformance" in out


def test_verify_release_does_not_hand_the_verdict_to_the_reference_verifier():
    source = (ROOT / "tools" / "compiler.py").read_text(encoding="utf-8")
    imports = [n for n in ast.walk(ast.parse(source)) if isinstance(n, (ast.Import, ast.ImportFrom))]
    names = " ".join(getattr(n, "module", "") or " ".join(a.name for a in n.names) for n in imports)
    assert "release_record_conformance" not in names


def test_the_reference_verifier_does_not_call_the_compilers_new_functions():
    source = (ROOT / "tools" / "release_record_conformance.py").read_text(encoding="utf-8")
    for name in ("_git_tree", "_build_release_artifacts", "_validate_release_artifact_declaration", "_source_commit", "_declaration_from_commit", "_resolve_release_artifacts",
                 "_check_unique_source_paths"):
        assert not re.search(r"(?<![A-Za-z0-9])" + re.escape(name) + r"\b", source), name


# ---------------------------------------------------------------- the schemas

SCHEMA = yaml.safe_load((ROOT / "release.schema.yaml").read_text())
PROJECT_SCHEMA = yaml.safe_load((ROOT / "project.schema.yaml").read_text())


def test_the_release_schema_accepts_the_compilers_record_and_the_real_old_ones(compiler_record):
    validate(instance=compiler_record, schema=SCHEMA)
    validate(instance=yaml.safe_load((ROOT / "release" / "cic-primitives-v0.1.5.yaml").read_text()), schema=SCHEMA)


@pytest.mark.parametrize("mutate", [
    lambda b: b.pop("artifacts"),
    lambda b: b["artifacts"].pop("manifest_digest"),
    lambda b: b["artifacts"].__setitem__("files", []),
    lambda b: b["artifacts"]["files"][0].__setitem__("digest", "b6a98d9ce9a2d9149288fa3df42d377c3e42737afdcdaf714e33c0a100b51060"),
    lambda b: b["artifacts"]["files"][0].__setitem__("digest", "sha256:" + "A" * 64),
    lambda b: b["provenance"].__setitem__("source_commit", None),
    lambda b: b["provenance"].__setitem__("source_commit", "F" * 40),
    lambda b: b.pop("provenance"),
], ids=["artifacts-absent", "manifest-absent", "files-empty", "digest-no-prefix", "digest-uppercase", "commit-null", "commit-uppercase", "provenance-absent"])
def test_the_release_schema_refuses_an_incomplete_envelope_3_record(mutate, compiler_record):
    bundle = copy.deepcopy(compiler_record)
    mutate(bundle)
    with pytest.raises(ValidationError):
        validate(instance=bundle, schema=SCHEMA)


def test_the_release_schema_leaves_envelope_2_records_as_they_were(compiler_record):
    bundle = copy.deepcopy(compiler_record)
    bundle["release"]["envelope"] = 2
    bundle["provenance"]["envelope"] = 2
    bundle["provenance"]["source_commit"] = None
    del bundle["artifacts"]
    validate(instance=bundle, schema=SCHEMA)


def test_the_project_schema_knows_the_declaration_and_nothing_else_under_it():
    base = {"project": {"name": "n", "description": "d", "license": "l", "owner": "o", "main_branch": "main"},
            "compiler_settings": {"meta_schemas_dir": ".", "source_dir": "s", "meta_schema_file": "m", "vault_key_name": "k"}}
    ok = copy.deepcopy(base)
    ok["compiler_settings"]["release_artifacts"] = {"paths": ["a.txt"]}
    validate(instance=ok, schema=PROJECT_SCHEMA)
    for bad in ({"paths": []}, {"paths": ["a.txt"], "include": ["*"]}, {"paths": "a.txt"}, {"include": ["*"]}, {}, {"paths": [1]}):
        broken = copy.deepcopy(base)
        broken["compiler_settings"]["release_artifacts"] = bad
        with pytest.raises(ValidationError):
            validate(instance=broken, schema=PROJECT_SCHEMA)
