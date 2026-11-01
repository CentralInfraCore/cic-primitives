"""Planted-defect proof for the envelope 3 conformance vectors: the vectors are only worth something if breaking the check they target turns them red.

Two series. (1) every check of the reference verifier is switched off in turn, in this process, and each reason it owns must lose at least one vector. (2) small
breaks in the verifier's source (tests/e3_mutants.py) are run against the whole vector suite in a subprocess; the targeted vector has to be among the failures, and
the mutants that cannot change behaviour are listed with the reason and have to survive.
"""
import concurrent.futures
import os
import pathlib
import re
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import e3_fixtures as fx  # noqa: E402
import e3_mutants as mutants  # noqa: E402
import e3_vectors as vec  # noqa: E402

V = fx.load_verifier()
SOURCE = fx.ROOT / "tools" / "release_record_conformance.py"

# which reasons each record check owns
OWNS = {
    "envelope": ["envelope_mismatch", "envelope_unsupported", "envelope_too_old"],
    "source_commit": ["source_commit_missing", "source_commit_form"],
    "artifacts_present": ["artifacts_missing"],
    "path_form": ["artifact_path_form"],
    "path_duplicate": ["artifact_path_duplicate"],
    "order": ["artifact_order"],
    "digest_form": ["artifact_digest_form"],
    "manifest_digest_form": ["artifact_manifest_digest_form"],
    "manifest": ["artifact_manifest_mismatch"],
    "spec_source_paths": ["spec_source_path_duplicate"],
}


@pytest.fixture(scope="module")
def context():
    return {"$GOLDEN_COMMIT": "0" * 40, "$SPECIAL_COMMIT": "1" * 40, "$DIGEST_CRLF_A": "sha256:" + "2" * 64, "$DIGEST_OF_B": "sha256:" + "3" * 64}


def outcome(vector, context):
    bundle = fx.apply_ops(fx.load_golden(), vector["ops"], context)
    if vector["reauth"] != "none":
        fx.reauthenticate(bundle, vector["reauth"])
    try:
        result = V.check_record(bundle)
    except Exception as exc:  # a crash is a red test as well
        return "crash:%s" % type(exc).__name__
    return result.reason if result.status == "FAIL" else "PASS"


def test_the_check_names_here_are_the_ones_of_the_verifier():
    assert [name for name, _fn in V.RECORD_CHECKS] == list(OWNS)
    assert [r for rs in OWNS.values() for r in rs] == list(V.RECORD_REASONS)


@pytest.mark.parametrize("check", list(OWNS))
def test_switching_a_record_check_off_turns_its_vectors_red(check, monkeypatch, context):
    intact = {x["id"]: outcome(x, context) for x in vec.ALL_RECORD}
    for x in vec.ALL_RECORD:
        assert intact[x["id"]] == (x["reason"] or "PASS"), x["id"]
    monkeypatch.setattr(V, "RECORD_CHECKS", tuple((n, f) if n != check else (n, lambda bundle: None) for n, f in V.RECORD_CHECKS))
    for reason in OWNS[check]:
        targeted = [x for x in vec.ALL_RECORD if x["reason"] == reason]
        assert targeted, reason
        red = [x["id"] for x in targeted if outcome(x, context) != reason]
        assert red, "no vector for %s turned red with the check %s switched off" % (reason, check)


@pytest.mark.parametrize("name,part", [("check_build_hash", "build_hash"), ("check_signature", "signature"), ("check_countersign", "countersign")])
def test_switching_a_crypto_check_off_turns_its_vectors_red(name, part, monkeypatch):
    index = ("build_hash", "signature", "countersign").index(part)
    reason = ("build_hash_mismatch", "signature_invalid", "countersign_invalid")[index]
    targeted = [x for x in vec.CRYPTO if x["parts"][index] == reason]
    assert targeted
    monkeypatch.setattr(V, name, lambda bundle, compiler=None: V.Result(V.PASS))
    for x in targeted:
        bundle = fx.apply_ops(fx.load_golden(), x["ops"], {})
        if x["reauth"] != "none":
            fx.reauthenticate(bundle, x["reauth"])
        # with the check off, the reason this vector is there to show no longer appears
        assert V.check_crypto(bundle)[part].reason != reason, x["id"]


# ---------------------------------------------------------------- source mutants

def run_mutant(mutant, tmp):
    source = SOURCE.read_text(encoding="utf-8")
    assert source.count(mutant["old"]) == 1, "%s: the planted text occurs %d times" % (mutant["id"], source.count(mutant["old"]))
    path = pathlib.Path(tmp) / ("m_%s.py" % mutant["id"])
    mutated = source.replace(mutant["old"], mutant["new"])
    compile(mutated, mutant["id"], "exec")   # a break that is not even valid Python is killed for the wrong reason
    path.write_text(mutated, encoding="utf-8")
    env = dict(os.environ, E3_VERIFIER=str(path), PYTHONDONTWRITEBYTECODE="1")
    # a defect meant to be caught is run against the vectors that target it (the run is short); one documented as equivalent is run against all of them
    select = ["-k", " or ".join(mutant["kills"])] if mutant["kills"] else []
    done = subprocess.run([sys.executable, "-m", "pytest", str(fx.ROOT / "tests" / "test_release_record_conformance.py"), "-q", "--tb=no", "-rf", "-p", "no:cacheprovider"] + select,
                          capture_output=True, text=True, env=env, cwd=str(fx.ROOT))
    failed = [line for line in done.stdout.splitlines() if line.startswith("FAILED")]
    assert "no tests ran" not in done.stdout and done.returncode != 5, "%s: the targeted vectors %s do not exist" % (mutant["id"], mutant["kills"])
    return done.returncode, failed


@pytest.fixture(scope="module")
def mutant_results(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("mutants")
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {m["id"]: pool.submit(run_mutant, m, tmp) for m in mutants.MUTANTS}
        return {k: f.result() for k, f in futures.items()}


def test_mutant_ids_are_unique():
    ids = [m["id"] for m in mutants.MUTANTS]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("mutant", [m for m in mutants.MUTANTS if not m["equivalent"]], ids=lambda m: m["id"])
def test_a_planted_defect_turns_the_targeted_vector_red(mutant, mutant_results):
    code, failed = mutant_results[mutant["id"]]
    assert code != 0, "the planted defect %s was not detected by any vector" % mutant["id"]
    assert any(any(k in line for k in mutant["kills"]) for line in failed), "%s: failed %s, none of the targeted %s" % (mutant["id"], failed[:5], mutant["kills"])


@pytest.mark.parametrize("mutant", [m for m in mutants.MUTANTS if m["equivalent"]], ids=lambda m: m["id"])
def test_an_equivalent_mutant_survives_and_says_why(mutant, mutant_results):
    code, failed = mutant_results[mutant["id"]]
    assert len(mutant["equivalent"]) > 30
    assert code == 0, "%s is documented as equivalent but %s" % (mutant["id"], failed[:3])
