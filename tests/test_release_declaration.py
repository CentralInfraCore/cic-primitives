"""The declaration of the files this repository publishes (project.yaml, compiler_settings.release_artifacts.paths), measured.

The list was approved by the owner as content (docs/en/RELEASE-ARTIFACT-CLASSIFICATION.md, 30 paths). This file is the evidence that the declaration in project.yaml IS that list
and that it works with the compiler of this repository: the paths exist in the commit under test, every schema the compiler would publish as a `spec` is among them, the twelve
files of the Forms grammar pin are a subset, and the artifacts block the compiler produces from it is the same on every run and equals one computed here from the git blobs.

What it does NOT show, deliberately: that a release cut from this commit contains the bytes the Forms pin names (the pin is a historical commit; eleven of the twelve files are
identical at this commit, P0-4-MIGRATION.md is not, and nothing here pretends otherwise), that a release may be made, or that anything is authentic. The release branch from the
historical pin is another commit state with its own declaration and its own evidence.
"""
import hashlib
import itertools
import pathlib
import re
import subprocess
import sys

import pytest
import yaml
from jsonschema import validate

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import e3_fixtures as fx  # noqa: E402

from tools import compiler  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
V = fx.load_verifier()


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT)] + list(args), capture_output=True, check=True).stdout


@pytest.fixture(scope="module")
def commit():
    return git("rev-parse", "HEAD").decode().strip()


@pytest.fixture(scope="module")
def tree(commit):
    return compiler._git_tree(commit)


@pytest.fixture(scope="module")
def declared():
    project = yaml.safe_load((ROOT / "project.yaml").read_text(encoding="utf-8"))
    return project["compiler_settings"]["release_artifacts"]["paths"]


def approved_paths():
    """The approved content: the yaml block of the classification document, which the owner's decision produced."""
    doc = (ROOT / "docs" / "en" / "RELEASE-ARTIFACT-CLASSIFICATION.md").read_text(encoding="utf-8")
    block = re.search(r"```yaml\n(.*?)```", doc, re.S).group(1)
    return yaml.safe_load(block)["compiler_settings"]["release_artifacts"]["paths"]


def forms_pin_paths():
    pin = yaml.safe_load((ROOT / "tests" / "fixtures" / "forms-pin-73ae469.yaml").read_text(encoding="utf-8"))
    return [f["path"] for f in pin["grammar"]["cic-primitives-73ae469-6a188078"]["files"]]


def test_the_declaration_is_the_list_the_owner_approved(declared):
    assert len(declared) == 30
    assert declared == approved_paths()


def test_the_declaration_is_explicit_unique_and_sorted_by_utf8_bytes(declared):
    assert len(set(declared)) == len(declared)
    assert declared == sorted(declared, key=lambda p: p.encode("utf-8"))
    assert not any(ch in p for p in declared for ch in "*?[]{}")


def test_the_compiler_accepts_the_declaration_as_the_commit_holds_it(commit, tree):
    project = compiler._declaration_from_commit(tree)
    assert compiler._validate_release_artifact_declaration(project, tree) is None
    assert V.validate_declaration(project, tree) is None      # the reference reading agrees


def test_every_path_is_a_regular_file_in_the_commit_under_test(declared, tree):
    for path in declared:
        assert path in tree, path
        mode, kind, _oid = tree[path]
        assert kind == "blob" and mode in ("100644", "100755"), (path, mode, kind)


def test_every_schema_the_compiler_would_publish_as_a_spec_is_listed(declared, tree):
    specs = compiler._release_schema_files_in_tree(tree)
    assert len(specs) == 13
    assert set(specs) <= set(declared), sorted(set(specs) - set(declared))


def test_the_working_directorys_spec_selection_is_the_same_and_listed(declared):
    # in a clean checkout (the gate's) the selection the compiler makes from the working directory is the one it makes from the commit
    assert set(compiler._release_schema_files()) <= set(declared)


def test_the_twelve_files_of_the_forms_grammar_pin_are_a_subset(declared):
    pin = forms_pin_paths()
    assert len(pin) == 12
    assert set(pin) <= set(declared), sorted(set(pin) - set(declared))
    # the other way round is not required: the producer's list is its own, not the consumer's
    assert len(set(declared) - set(pin)) == 18


def test_the_artifacts_block_is_the_same_on_every_run_and_in_every_declared_order(declared, tree):
    blocks = {repr(compiler._build_release_artifacts(list(order), tree))
              for order in (declared, list(reversed(declared)), sorted(declared), sorted(declared, key=lambda p: p[::-1]))}
    assert len(blocks) == 1
    # and a handful of random-looking permutations of the first six, to make the order argument
    first = declared[:6]
    assert len({repr(compiler._build_release_artifacts(list(p) + declared[6:], tree)) for p in itertools.islice(itertools.permutations(first), 40)}) == 1


def test_the_block_equals_one_computed_here_from_the_git_blobs(declared, commit, tree):
    block = compiler._build_release_artifacts(declared, tree)
    files = [{"path": p, "digest": "sha256:" + hashlib.sha256(git("show", "%s:%s" % (commit, p))).hexdigest()} for p in sorted(declared, key=lambda p: p.encode("utf-8"))]
    assert block["files"] == files
    assert block["manifest_digest"] == fx.independent_manifest_digest(files)


def test_the_reference_verifier_reads_that_block_as_a_conforming_artifact_list(declared, commit, tree):
    block = compiler._build_release_artifacts(declared, tree)
    record = {"provenance": {"envelope": 3, "source_commit": commit}, "release": {"envelope": 3}, "artifacts": block}
    for check in (V._check_source_commit, V._check_artifacts_present, V._check_path_form, V._check_path_duplicate, V._check_order, V._check_digest_form,
                  V._check_manifest_digest_form, V._check_manifest):
        assert check(record) is None, check.__name__
    blobs = V.check_blobs(record, str(ROOT))
    assert blobs.status == "PASS", blobs.failures


def test_the_real_project_yaml_meets_its_schema():
    project = yaml.safe_load((ROOT / "project.yaml").read_text(encoding="utf-8"))
    validate(instance=project, schema=yaml.safe_load((ROOT / "project.schema.yaml").read_text(encoding="utf-8")))


def test_the_declaration_names_no_consumer_and_no_generated_or_tooling_file(declared):
    for path in declared:
        assert not path.startswith(("tests/", "tools/", ".github/", "ai/", "features/", "release/")), path
        assert path not in ("project.yaml", "commitment.yaml", "requirements.in", "requirements.txt"), path
