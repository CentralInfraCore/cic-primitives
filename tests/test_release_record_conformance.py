"""Conformance vectors of the release record contract, envelope 3 (docs/en/RELEASE-RECORD-CONTRACT.md), run against the reference verifier
(tools/release_record_conformance.py).

The compiler does not take part: it has not been changed, and when it is, its output has to meet these vectors; it does not get to say that it is right. The
expected values are in tests/fixtures/envelope3 and were recomputed outside this code base (see tests/e3_fixtures.py). The planted-defect proof that these tests can
fail is tests/test_release_record_conformance_planted.py.
"""
import copy
import json
import os
import pathlib
import re
import subprocess
import sys

import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import e3_fixtures as fx  # noqa: E402
import e3_vectors as vec  # noqa: E402

V = fx.load_verifier()
DOC = fx.ROOT / "docs" / "en" / "RELEASE-RECORD-CONTRACT.md"


@pytest.fixture(scope="module")
def repos(tmp_path_factory):
    base = tmp_path_factory.mktemp("e3repos")
    golden = fx.build_repo(base / "golden", fx.GOLDEN_FILES)
    special = fx.build_repo(base / "special", fx.SPECIAL_FILES)
    return {"golden": (str(base / "golden"), golden), "special": (str(base / "special"), special)}


@pytest.fixture(scope="module")
def context(repos):
    return {"$GOLDEN_COMMIT": repos["golden"][1], "$SPECIAL_COMMIT": repos["special"][1],
            "$DIGEST_CRLF_A": "sha256:" + fx.sha256_hex(b"alpha\r\n"),
            "$DIGEST_OF_B": "sha256:" + fx.sha256_hex(b"beta\n")}


def build(vector, context):
    bundle = fx.apply_ops(fx.load_golden(), vector["ops"], context)
    if vector["reauth"] != "none":
        fx.reauthenticate(bundle, vector["reauth"])
    return bundle


# ---------------------------------------------------------------- the golden record

def test_the_worked_example_of_the_contract_is_the_golden_record():
    expected = fx.load_expected()
    text = DOC.read_text(encoding="utf-8")
    assert expected["manifest_digest"] in text
    for entry in expected["files"]:
        assert entry["digest"][len("sha256:"):] in text


def test_the_expected_values_recompute_from_the_inputs_by_the_independent_implementation():
    expected, golden = fx.load_expected(), fx.load_golden()
    assert expected["files"] == fx.golden_files_record() == golden["artifacts"]["files"]
    assert expected["manifest_digest"] == fx.independent_manifest_digest(expected["files"]) == golden["artifacts"]["manifest_digest"]
    assert expected["manifest_text"] == "".join("%s  %s\n" % (f["digest"][7:], f["path"]) for f in expected["files"])
    canonical = fx.independent_canonical_bytes(golden)
    assert (fx.FIXTURES / "golden.canonical.json").read_bytes() == canonical
    assert expected["canonical_sha256_hex"] == fx.sha256_hex(canonical)
    assert expected["build_hash"] == fx.independent_build_hash(golden) == golden["release"]["build_hash"]


def test_the_source_commit_of_the_golden_record_is_the_commit_of_the_worked_example(repos):
    assert fx.load_golden()["provenance"]["source_commit"] == fx.load_expected()["source_commit"] == repos["golden"][1]


def test_the_digests_are_those_of_the_git_blob_bytes(repos):
    path, commit = repos["golden"]
    tree = V.load_tree(path, commit)
    for entry in fx.load_expected()["files"]:
        blob = V._git(path, "cat-file", "blob", tree[entry["path"]][2]).stdout
        assert entry["digest"] == "sha256:" + fx.sha256_hex(blob)


def test_the_compilers_own_canonical_bytes_are_the_independent_ones():
    # cross-check only: the expectation is not taken from the compiler, but a disagreement here would mean the verifier checks a different thing than the compiler signs
    from tools import compiler
    golden = fx.load_golden()
    payload = compiler._release_hash_payload(golden, 2)
    assert compiler.to_canonical_json(payload) == fx.independent_canonical_bytes(golden)


def test_the_golden_record_passes_every_layer_and_each_crypto_check_by_itself(repos):
    report = V.verify(fx.load_golden(), repos["golden"][0])
    assert report["record"].status == "PASS"
    assert report["blobs"].status == "PASS"
    assert report["crypto"]["status"] == "PASS"
    for part in ("build_hash", "signature", "countersign"):
        assert report["crypto"][part].status == "PASS", part
    assert V.first_reason(report) is None


def test_the_test_keys_are_the_keys_of_the_committed_certificates():
    golden = fx.load_golden()
    from cryptography import x509
    for label, cert in (("issuer", golden["release"]["createdBy"]["certificate"]), ("authority", golden["cic_countersign"]["authority"]["certificate"])):
        public = x509.load_pem_x509_certificate(cert.encode()).public_key().public_numbers()
        assert public == fx.key(label).public_key().public_numbers()


# ---------------------------------------------------------------- record layer vectors

@pytest.mark.parametrize("vector", vec.ALL_RECORD, ids=lambda x: x["id"])
def test_record_vector(vector, context):
    bundle = build(vector, context)
    result = V.check_record(bundle)
    if vector["reason"] is None:
        assert result.status == "PASS", (result.reason, result.detail)
        return
    assert result.status == "FAIL"
    assert result.reason == vector["reason"], (result.reason, result.detail)
    # re-authenticated: the refusal comes from the contract check, not from a stale signature
    crypto = V.check_crypto(bundle)
    assert crypto["status"] == vector["crypto"], crypto["status"]


def test_the_record_layer_does_not_need_git_or_the_compiler():
    # no repository and no compiler import: this layer works on the record alone
    result = V.check_record(fx.load_golden())
    assert result.status == "PASS"


# ---------------------------------------------------------------- blob layer vectors

@pytest.mark.parametrize("vector", vec.BLOBS, ids=lambda x: x["id"])
def test_blob_vector(vector, repos, context):
    bundle = build(vector, context)
    path, _commit = repos[vector["repo"]]
    assert V.check_record(bundle).status in ("PASS", "FAIL")
    result = V.check_blobs(bundle, path)
    assert result.status == "FAIL"
    assert result.reason == vector["reason"], (result.reason, result.detail, result.failures)


def test_blob_layer_is_not_run_without_a_repository_or_without_the_commit(repos):
    golden = fx.load_golden()
    assert V.check_blobs(golden, None).status == "NOT_RUN"
    elsewhere = copy.deepcopy(golden)
    elsewhere["provenance"]["source_commit"] = "1" * 40
    result = V.check_blobs(elsewhere, repos["golden"][0])
    assert result.status == "NOT_RUN" and "not available" in result.detail
    assert V.check_blobs({"provenance": {"source_commit": None}}, repos["golden"][0]).status == "NOT_RUN"
    assert V.check_blobs(dict(golden, artifacts={"files": []}), repos["golden"][0]).status == "NOT_RUN"


def test_every_failing_blob_is_listed_not_only_the_first(repos, context):
    bundle = fx.apply_ops(fx.load_golden(), [vec.s("artifacts.files.0.digest", "sha256:" + "6" * 64), vec.s("artifacts.files.1.digest", "sha256:" + "7" * 64)], context)
    result = V.check_blobs(bundle, repos["golden"][0])
    assert [r for r, _ in result.failures] == ["artifact_digest_mismatch"] * 2


# ---------------------------------------------------------------- crypto layer: the coverage of the existing signature

@pytest.mark.parametrize("vector", vec.CRYPTO, ids=lambda x: x["id"])
def test_crypto_coverage_vector(vector, context):
    bundle = build(vector, context)
    crypto = V.check_crypto(bundle)
    assert crypto["status"] == "FAIL"
    got = tuple(crypto[p].reason or crypto[p].status for p in ("build_hash", "signature", "countersign"))
    assert got == vector["parts"], got
    # each of the three is also available on its own
    assert V.check_build_hash(bundle).reason == (vector["parts"][0] if vector["parts"][0] != "PASS" else None)
    assert V.check_signature(bundle).reason == (vector["parts"][1] if vector["parts"][1] != "PASS" else None)
    assert V.check_countersign(bundle).reason == (vector["parts"][2] if vector["parts"][2] != "PASS" else None)


@pytest.mark.parametrize("name,ops", vec.COVERAGE_MUTATIONS, ids=[m[0] for m in vec.COVERAGE_MUTATIONS])
def test_the_same_defect_re_authenticated_is_a_validly_signed_record(name, ops, context):
    # the control of the series: nothing about the defect itself makes the crypto layer fail, so the failures above are the staleness of the signature
    bundle = fx.reauthenticate(fx.apply_ops(fx.load_golden(), ops, context))
    assert V.check_crypto(bundle)["status"] == "PASS"


def test_every_member_of_the_artifacts_block_and_the_commit_is_inside_the_hash():
    golden = fx.load_golden()
    base = V._compiler()
    reference = base.get_sha256_b64(base.to_canonical_json(base._release_hash_payload(golden, 2)))
    assert reference == golden["release"]["build_hash"]
    for dotted in ("artifacts.manifest_digest", "artifacts.files.0.path", "artifacts.files.0.digest", "provenance.source_commit", "provenance.envelope", "release.envelope", "kind", "version"):
        mutated = fx.apply_ops(golden, [vec.s(dotted, "x" if dotted != "provenance.envelope" else 9)], {})
        changed = base.get_sha256_b64(base.to_canonical_json(base._release_hash_payload(mutated, 2)))
        assert changed != reference, dotted
    for dotted in ("release.sign", "release.build_hash"):
        mutated = fx.apply_ops(golden, [vec.s(dotted, "x")], {})
        assert base.get_sha256_b64(base.to_canonical_json(base._release_hash_payload(mutated, 2))) == reference, dotted
    without = copy.deepcopy(golden)
    del without["cic_countersign"]
    assert base.get_sha256_b64(base.to_canonical_json(base._release_hash_payload(without, 2))) == reference


def test_an_absent_countersignature_is_incomplete_never_pass(repos):
    bundle = copy.deepcopy(fx.load_golden())
    del bundle["cic_countersign"]
    crypto = V.check_crypto(bundle)
    assert crypto["status"] == "INCOMPLETE"
    assert crypto["countersign"].status == "NOT_RUN"
    assert crypto["build_hash"].status == crypto["signature"].status == "PASS"


def test_a_countersignature_that_signs_another_payload_is_refused():
    bundle = copy.deepcopy(fx.load_golden())
    bundle["cic_countersign"]["signed_payload"] = "specs"
    assert V.check_countersign(bundle).reason == "countersign_invalid"


def test_crypto_checks_do_not_hide_one_another():
    bundle = copy.deepcopy(fx.load_golden())
    bundle["release"]["build_hash"] = "AAAA"
    crypto = V.check_crypto(bundle)
    assert [crypto[p].reason for p in ("build_hash", "signature", "countersign")] == ["build_hash_mismatch", "signature_invalid", "countersign_invalid"]


# ---------------------------------------------------------------- layers are not one verdict

def test_a_failing_layer_does_not_change_the_others(repos):
    path = repos["golden"][0]
    bad_blob = fx.reauthenticate(fx.apply_ops(fx.load_golden(), [vec.s("artifacts.files.0.digest", "sha256:" + "8" * 64), vec.FIX], {}))
    report = V.verify(bad_blob, path)
    assert (report["record"].status, report["blobs"].status, report["crypto"]["status"]) == ("PASS", "FAIL", "PASS")
    stale = fx.apply_ops(fx.load_golden(), [vec.s("provenance.source_commit", "0" * 40)], {})
    report = V.verify(stale, path)
    assert report["record"].status == "PASS" and report["crypto"]["status"] == "FAIL"
    assert report["blobs"].status == "NOT_RUN"


def test_the_report_has_no_overall_verdict_and_says_what_it_does_not_prove(repos):
    out = V.to_json(V.verify(fx.load_golden(), repos["golden"][0]))
    assert set(out) == {"record", "blobs", "crypto", "first_reason", "not_proven"}
    assert not any(k in out for k in ("valid", "ok", "authentic", "verdict"))
    assert any("who signed" in line for line in out["not_proven"])


# ---------------------------------------------------------------- the producer's declaration

@pytest.mark.parametrize("case", vec.DECLARATIONS, ids=lambda c: c[0])
def test_declaration_vector(case, repos, context):
    _id, reason, project = case
    tree = V.load_tree(repos["special"][0], repos["special"][1])
    refusal = V.validate_declaration(fx.expand(project, context), tree)
    assert (refusal[0] if refusal else None) == reason, refusal


def test_the_declaration_is_judged_against_the_tree_not_the_working_directory(tmp_path, monkeypatch, repos):
    (tmp_path / "only-here.txt").write_text("x")
    monkeypatch.chdir(tmp_path)
    tree = V.load_tree(repos["golden"][0], repos["golden"][1])
    refusal = V.validate_declaration({"compiler_settings": {"release_artifacts": {"paths": ["only-here.txt"]}}}, tree)
    assert refusal[0] == "declared_path_absent"


# ---------------------------------------------------------------- the reasons of the contract and the vectors cannot drift apart

def contract_reasons():
    text = DOC.read_text(encoding="utf-8")
    table = set(re.findall(r"^\| `([a-z_]+)` \|", text, re.M))
    named = set(re.findall(r"`((?:declaration_|declared_path_)[a-z_]+|artifact_absent|artifact_digest_mismatch|artifact_not_regular)`", text))
    return table | named


def test_the_verifier_gives_exactly_the_reasons_the_contract_names():
    verifier = set(V.RECORD_REASONS + V.CRYPTO_REASONS + V.BLOB_REASONS + V.DECLARATION_REASONS)
    # manifest-digest-absent is read as artifact_digest_form: the only reason the verifier gives that the contract table does not give for that case
    assert verifier == contract_reasons(), (verifier ^ contract_reasons())


def test_every_reason_has_at_least_one_targeted_negative_vector():
    covered = {x["reason"] for x in vec.ALL_RECORD + vec.BLOBS + vec.CRYPTO if x["reason"]}
    covered |= {r for _i, r, _p in vec.DECLARATIONS if r}
    missing = set(V.RECORD_REASONS + V.CRYPTO_REASONS + V.BLOB_REASONS + V.DECLARATION_REASONS) - covered
    assert not missing, missing


def test_vector_ids_are_unique():
    ids = [x["id"] for x in vec.ALL_RECORD + vec.BLOBS + vec.CRYPTO] + [c[0] for c in vec.DECLARATIONS]
    assert len(ids) == len(set(ids))


def test_the_checks_run_in_the_order_of_the_contract_table():
    order = [r for r in re.findall(r"^\| `([a-z_]+)` \|", DOC.read_text(encoding="utf-8"), re.M)]
    assert order == list(V.RECORD_REASONS + V.CRYPTO_REASONS)


# ---------------------------------------------------------------- the verifier only reads

def test_the_verifier_changes_nothing(repos, tmp_path):
    record = tmp_path / "record.yaml"
    record.write_text(yaml.dump(fx.load_golden(), sort_keys=False))
    before = (record.read_bytes(), subprocess.run(["git", "-C", repos["golden"][0], "count-objects", "-v"], capture_output=True).stdout,
              subprocess.run(["git", "-C", repos["golden"][0], "for-each-ref"], capture_output=True).stdout)
    V.verify(yaml.safe_load(record.read_text()), repos["golden"][0])
    after = (record.read_bytes(), subprocess.run(["git", "-C", repos["golden"][0], "count-objects", "-v"], capture_output=True).stdout,
             subprocess.run(["git", "-C", repos["golden"][0], "for-each-ref"], capture_output=True).stdout)
    assert before == after
    assert sorted(p.name for p in tmp_path.iterdir()) == ["record.yaml"]


def test_the_module_does_not_open_a_file_for_writing_or_sign():
    source = (fx.ROOT / "tools" / "release_record_conformance.py").read_text(encoding="utf-8")
    assert not re.search(r"open\([^)]*['\"][wax]", source)
    for forbidden in (".sign(", "hash-object", "write-tree", "commit-tree", "update-ref", "tag"):
        assert forbidden not in source, forbidden


# ---------------------------------------------------------------- command line

def run_cli(*args):
    # the planted-defect runs point E3_VERIFIER at a mutated copy; the copy lives elsewhere, so the repository root is put on the path for its compiler import
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": "/nonexistent", "PYTHONPATH": str(fx.ROOT)}
    script = os.environ.get("E3_VERIFIER") or str(fx.ROOT / "tools" / "release_record_conformance.py")
    return subprocess.run([sys.executable, script] + list(args), capture_output=True, text=True, env=env, cwd=str(fx.ROOT))


def test_cli_prints_the_three_layers_apart_and_the_open_claims(repos, tmp_path):
    record = tmp_path / "r.yaml"
    record.write_text(yaml.dump(fx.load_golden(), sort_keys=False))
    done = run_cli(str(record), "--repo", repos["golden"][0])
    assert done.returncode == 0, done.stdout + done.stderr
    assert re.search(r"^record\s+PASS", done.stdout, re.M)
    assert re.search(r"^blobs\s+PASS", done.stdout, re.M)
    assert re.search(r"^crypto\s+PASS", done.stdout, re.M)
    assert "NOT proven: who signed" in done.stdout
    # no sentence claims authenticity or fitness: the only lines that mention them are the ones that say they are not proven
    assert all(line.startswith("NOT proven") for line in done.stdout.splitlines() if "authentic" in line or "fit to publish" in line)


def test_cli_without_a_repository_says_the_blob_checks_were_not_made(tmp_path):
    record = tmp_path / "r.yaml"
    record.write_text(yaml.dump(fx.load_golden(), sort_keys=False))
    done = run_cli(str(record))
    assert done.returncode == 0
    assert "blobs    NOT_RUN" in done.stdout
    assert run_cli(str(record), "--require", "record,blobs").returncode == 3
    assert run_cli(str(record), "--require", "record,crypto").returncode == 0


def test_cli_exit_status_one_on_a_failing_layer(tmp_path):
    bad = fx.apply_ops(fx.load_golden(), [vec.s("provenance.source_commit", None)], {})
    record = tmp_path / "bad.yaml"
    record.write_text(yaml.dump(bad, sort_keys=False))
    done = run_cli(str(record), "--json")
    assert done.returncode == 1
    assert json.loads(done.stdout)["first_reason"] == "source_commit_missing"


def test_cli_unreadable_record_is_exit_status_two(tmp_path):
    assert run_cli(str(tmp_path / "missing.yaml")).returncode == 2
