"""A value that ends in a newline is not a commit and not a digest (follow-up to PR #25; vectors in tests/e3_vectors_fullmatch.py).

Three things are shown, not one: (1) the vectors are refused by the verifier now; (2) they were NOT refused by the verifier of d2d8ec7, read from git, so the defect is
reproduced and not remembered; (3) the fix changes the verdict on no real record: the released v0.2.1 record still passes all three layers.
"""
import hashlib
import importlib.util
import os
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import e3_fixtures as fx  # noqa: E402
import e3_vectors_fullmatch as nv  # noqa: E402

V = fx.load_verifier()
ROOT = fx.ROOT
MERGE_COMMIT = "d2d8ec7422490053644779d3cca9fce388bb2886"      # the verifier as it was accepted and frozen
V021_SOURCE = "106965b8cea7cce2081beb77008753af21e68b46"
V021_RELEASE_COMMIT = "5e8c3219b52399e3e764b0b0bb27de710f5445a4"
V021_RECORD_SHA256 = "e5d8268aede0d24f02e60a151099a2fdc7615172ed3105b0a05b6b5d19addf63"
REQUIRED = os.environ.get("CIC_REQUIRE_RELEASE_HISTORY") == "1"
CONTEXT = {"$GOLDEN_COMMIT": nv.COMMIT}


def has_commit(commit):
    return subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", commit + "^{commit}"], capture_output=True, check=False).returncode == 0


def result_of(verifier, vector):
    bundle = fx.apply_ops(fx.load_golden(), vector["ops"], CONTEXT)
    fx.reauthenticate(bundle, vector["reauth"])
    return verifier.check_record(bundle), verifier.check_crypto(bundle)


@pytest.mark.parametrize("vector", nv.ALL, ids=lambda x: x["id"])
def test_the_value_is_refused_with_the_reason_of_its_form(vector):
    record, crypto = result_of(V, vector)
    assert record.status == "FAIL" and record.reason == vector["reason"], (record.status, record.reason, record.detail)
    assert crypto["status"] == vector["crypto"], "re-authenticated: the refusal has to come from the contract check, not from a stale signature"


@pytest.mark.parametrize("vector", nv.NEWLINE, ids=lambda x: x["id"])
def test_the_verifier_of_d2d8ec7_did_not_refuse_it_for_that_reason(vector, tmp_path):
    """The proof that the defect existed. The old verifier is read from git; where the history is required its absence is a failure, not a skip."""
    if not has_commit(MERGE_COMMIT):
        assert not REQUIRED, "CIC_REQUIRE_RELEASE_HISTORY=1 but %s is not in this clone (fetch-depth: 0)" % MERGE_COMMIT
        pytest.skip("the merge commit is not in this clone")
    source = subprocess.run(["git", "-C", str(ROOT), "show", "%s:tools/release_record_conformance.py" % MERGE_COMMIT], capture_output=True, check=True).stdout
    old_path = tmp_path / "release_record_conformance_d2d8ec7.py"
    old_path.write_bytes(source)
    spec = importlib.util.spec_from_file_location("release_record_conformance_d2d8ec7", old_path)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    record, _crypto = result_of(old, vector)
    assert not (record.status == "FAIL" and record.reason == vector["reason"]), "the old verifier already refused %s: there was no defect to fix" % vector["id"]


@pytest.mark.parametrize("vector", nv.CONTROLS, ids=lambda x: x["id"])
def test_the_controls_were_refused_before_the_fix_too(vector, tmp_path):
    if not has_commit(MERGE_COMMIT):
        assert not REQUIRED, "CIC_REQUIRE_RELEASE_HISTORY=1 but %s is not in this clone (fetch-depth: 0)" % MERGE_COMMIT
        pytest.skip("the merge commit is not in this clone")
    source = subprocess.run(["git", "-C", str(ROOT), "show", "%s:tools/release_record_conformance.py" % MERGE_COMMIT], capture_output=True, check=True).stdout
    old_path = tmp_path / "release_record_conformance_d2d8ec7.py"
    old_path.write_bytes(source)
    spec = importlib.util.spec_from_file_location("release_record_conformance_d2d8ec7", old_path)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    record, _crypto = result_of(old, vector)
    assert record.status == "FAIL" and record.reason == vector["reason"]


def test_the_released_v021_record_still_passes_every_layer(tmp_path):
    """The fix may not change what is said about a release that exists. The record is read from the release COMMIT and pinned by its SHA-256."""
    if not (has_commit(V021_SOURCE) and has_commit(V021_RELEASE_COMMIT)):
        assert not REQUIRED, "CIC_REQUIRE_RELEASE_HISTORY=1 but the commits of release v0.2.1 are not in this clone (fetch-depth: 0)"
        pytest.skip("the history of release v0.2.1 is not in this clone")
    shown = subprocess.run(["git", "-C", str(ROOT), "show", "%s:release/cic-primitives-v0.2.1.yaml" % V021_RELEASE_COMMIT], capture_output=True, check=True)
    assert hashlib.sha256(shown.stdout).hexdigest() == V021_RECORD_SHA256, "the record of v0.2.1 is not the frozen one"
    record_path = tmp_path / "cic-primitives-v0.2.1.yaml"
    record_path.write_bytes(shown.stdout)
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "release_record_conformance.py"), str(record_path), "--repo", str(ROOT), "--require", "record,blobs,crypto"],
                         capture_output=True, text=True, check=False)
    assert out.returncode == 0, out.stdout + out.stderr
    for layer in ("record   PASS", "blobs    PASS", "crypto   PASS"):
        assert layer in out.stdout
