"""The yardstick may not move under the compiler.

The reference verifier, the golden fixtures, the vectors and the planted-defect proof of the envelope 3 conformance (PR #25) are frozen at the state that was
accepted and merged, d2d8ec7. tests/fixtures/envelope3/FROZEN.sha256 lists their SHA-256 digests as they were computed from the git objects of that merge commit;
the list is NOT regenerated from the working tree. A change to any of them (to make a compiler change pass, for instance) is a red test here and has to be made
in a change of its own that updates the list, where a reviewer sees it.

Two readings: the working tree against the list (always), and, where the history is present (the gate fetches all of it), the list against the blobs of the merge
commit itself, so the list cannot be edited together with a file without the mismatch showing.

A change of the yardstick that is wanted goes through tests/fixtures/envelope3/AMENDMENTS.yaml, never through an edit of the list: an amendment names the file, the digest it
had (which has to be the one of the list), the digest it has now (which has to be the working tree) and the reason, so that the difference to the accepted state is one
reviewable file. The list itself keeps the digests of d2d8ec7 and is still compared with its blobs.
"""
import hashlib
import os
import pathlib
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIST = ROOT / "tests" / "fixtures" / "envelope3" / "FROZEN.sha256"
AMENDMENTS = ROOT / "tests" / "fixtures" / "envelope3" / "AMENDMENTS.yaml"
MERGE_COMMIT = "d2d8ec7422490053644779d3cca9fce388bb2886"
REQUIRED = os.environ.get("CIC_REQUIRE_RELEASE_HISTORY") == "1"


def frozen():
    out = {}
    for line in LIST.read_text(encoding="utf-8").splitlines():
        digest, _sp, path = line.partition("  ")
        out[path] = digest
    return out


def amendments():
    return (yaml.safe_load(AMENDMENTS.read_text(encoding="utf-8")) or {}).get("amendments") or []


def expected():
    """The digest each file has to have now: the frozen one, or the `to_sha256` of its amendment."""
    out = dict(frozen())
    for a in amendments():
        out[a["path"]] = a["to_sha256"]
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
def test_the_working_tree_matches_the_frozen_digest_or_its_amendment(path):
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected()[path], (
        "%s differs from the state accepted in %s and from its amendment, if it has one: change the yardstick in a change of its own that lists it in AMENDMENTS.yaml, "
        "not together with the compiler" % (path, MERGE_COMMIT[:7]))


def test_every_amendment_starts_from_the_frozen_digest_and_changes_something():
    seen = set()
    for a in amendments():
        assert a["path"] in frozen(), "%s is not part of the frozen yardstick" % a["path"]
        assert a["path"] not in seen, "%s is amended twice: one amendment per file, from the accepted state" % a["path"]
        seen.add(a["path"])
        assert a["from_sha256"] == frozen()[a["path"]], "the amendment of %s does not start from the frozen digest" % a["path"]
        assert a["to_sha256"] != a["from_sha256"], "the amendment of %s changes nothing" % a["path"]
        assert len(a["to_sha256"]) == 64 and str(a.get("change", "")).strip(), "the amendment of %s has no digest or no reason" % a["path"]


def test_the_released_records_are_not_amendable():
    """A release record is evidence, not part of the yardstick that may move: the list holds the v0.1.5 record and no amendment may touch it."""
    assert all(not a["path"].startswith("release/") for a in amendments())


@pytest.mark.parametrize("path", sorted(frozen()))
def test_the_frozen_digest_is_that_of_the_merge_commit(path):
    if not has_commit(MERGE_COMMIT):
        assert not REQUIRED, "CIC_REQUIRE_RELEASE_HISTORY=1 but %s is not in this clone (fetch-depth: 0)" % MERGE_COMMIT
        pytest.skip("the merge commit is not in this clone")
    blob = subprocess.run(["git", "-C", str(ROOT), "show", "%s:%s" % (MERGE_COMMIT, path)], capture_output=True, check=True).stdout
    assert hashlib.sha256(blob).hexdigest() == frozen()[path]
