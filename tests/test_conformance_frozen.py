"""The yardstick may not move under the compiler.

The reference verifier, the golden fixtures, the vectors and the planted-defect proof of the envelope 3 conformance (PR #25) are frozen at the state that was
accepted and merged, d2d8ec7. tests/fixtures/envelope3/FROZEN.sha256 lists their SHA-256 digests as they were computed from the git objects of that merge commit;
the list is NOT regenerated from the working tree. A change to any of them (to make a compiler change pass, for instance) is a red test here and has to be made
in a change of its own that updates the list, where a reviewer sees it.

Two readings: the working tree against the list (always), and, where the history is present (the gate fetches all of it), the list against the blobs of the merge
commit itself, so the list cannot be edited together with a file without the mismatch showing.
"""
import hashlib
import os
import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIST = ROOT / "tests" / "fixtures" / "envelope3" / "FROZEN.sha256"
MERGE_COMMIT = "d2d8ec7422490053644779d3cca9fce388bb2886"
REQUIRED = os.environ.get("CIC_REQUIRE_RELEASE_HISTORY") == "1"


def frozen():
    out = {}
    for line in LIST.read_text(encoding="utf-8").splitlines():
        digest, _sp, path = line.partition("  ")
        out[path] = digest
    return out


def has_commit(commit):
    return subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", commit + "^{commit}"], capture_output=True).returncode == 0


def test_the_list_names_the_yardstick():
    names = set(frozen())
    assert {"tools/release_record_conformance.py", "tests/e3_vectors.py", "tests/e3_fixtures.py", "tests/fixtures/envelope3/golden-record.yaml",
            "tests/fixtures/envelope3/golden.expected.json", "tests/fixtures/envelope3/golden.canonical.json", "tests/test_release_record_conformance.py",
            "tests/test_release_record_conformance_planted.py", "tests/e3_mutants.py", "release/cic-primitives-v0.1.5.yaml"} <= names
    assert all(len(d) == 64 for d in frozen().values())


@pytest.mark.parametrize("path", sorted(frozen()))
def test_the_working_tree_matches_the_frozen_digest(path):
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == frozen()[path], (
        "%s differs from the state accepted in %s: change the yardstick in a change of its own, not together with the compiler" % (path, MERGE_COMMIT[:7]))


@pytest.mark.parametrize("path", sorted(frozen()))
def test_the_frozen_digest_is_that_of_the_merge_commit(path):
    if not has_commit(MERGE_COMMIT):
        assert not REQUIRED, "CIC_REQUIRE_RELEASE_HISTORY=1 but %s is not in this clone (fetch-depth: 0)" % MERGE_COMMIT
        pytest.skip("the merge commit is not in this clone")
    blob = subprocess.run(["git", "-C", str(ROOT), "show", "%s:%s" % (MERGE_COMMIT, path)], capture_output=True, check=True).stdout
    assert hashlib.sha256(blob).hexdigest() == frozen()[path]
