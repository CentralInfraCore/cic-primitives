import pytest
import pathlib

from tools import compiler
from _helpers import cert_subject_name, make_test_key_and_cert, sign_hash
import os
import yaml
import sys
import hashlib
import base64
import datetime
from jsonschema import ValidationError


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_project_config(version="0.1.0", component="primitives/"):
    return {
        "project": {"main_branch": f"{component}main"},
        "compiler_settings": {
            "meta_schema_file": "md.meta.schema.yaml",
            "meta_schemas_dir": ".",
            "source_dir": "schemas",
            "canonical_source_file": "schemas/index.yaml",
            "dependencies_dir": "dependencies",
            "release_dir": "release",
            "vault_key_name": "cic-my-sign-key",
        }
    }


# ── load_yaml ─────────────────────────────────────────────────────────────────

def test_load_yaml_valid(tmp_path):
    data = {"name": "test", "version": "1.0.0"}
    p = tmp_path / "schema.yaml"
    p.write_text(yaml.safe_dump(data))
    assert compiler.load_yaml(p) == data


def test_load_yaml_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        compiler.load_yaml(tmp_path / "missing.yaml")


def test_load_yaml_invalid_yaml(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("name: test: version: 1.0.0")
    with pytest.raises(yaml.YAMLError):
        compiler.load_yaml(p)


# ── write_yaml ────────────────────────────────────────────────────────────────

def test_write_yaml(tmp_path):
    f = tmp_path / "out.yaml"
    data = {"key1": "value1", "key2": {"nested": "val"}, "list": [1, 2, 3]}
    compiler.write_yaml(str(f), data)
    assert f.exists()
    assert yaml.safe_load(f.read_text()) == data


# ── hash helpers ──────────────────────────────────────────────────────────────

def test_get_sha256_hex():
    data = b"test"
    assert compiler.get_sha256_hex(data) == hashlib.sha256(data).hexdigest()


def test_get_sha256_b64():
    data = b"test"
    expected = base64.b64encode(hashlib.sha256(data).digest()).decode()
    assert compiler.get_sha256_b64(data) == expected


# ── run_validation ────────────────────────────────────────────────────────────

def test_run_validation_success(mocker):
    mocker.patch("glob.glob", return_value=["schemas/test.yaml"])
    mocker.patch("tools.compiler.load_yaml", side_effect=[
        {"type": "object", "properties": {"metadata": {}, "spec": {}}},
        {"metadata": {"name": "x"}, "spec": {}}
    ])
    mocker.patch("tools.compiler.validate", return_value=None)
    compiler.run_validation()


def test_run_validation_meta_schema_load_failure(mocker):
    mocker.patch("tools.compiler.load_yaml", side_effect=IOError("not found"))
    with pytest.raises(SystemExit) as e:
        compiler.run_validation()
    assert e.value.code == 1


def test_run_validation_schema_invalid(mocker):
    mocker.patch("glob.glob", return_value=["schemas/test.yaml"])
    mocker.patch("tools.compiler.load_yaml", side_effect=[
        {"type": "object"},
        {"metadata": {}, "spec": {}}
    ])
    mocker.patch("tools.compiler.validate", side_effect=ValidationError("bad"))
    with pytest.raises(SystemExit) as e:
        compiler.run_validation()
    assert e.value.code == 1


# ── run_primitive_validation ──────────────────────────────────────────────────

def test_run_primitive_validation_skips_when_no_config(mocker):
    mocker.patch.object(compiler, "CONFIG", {})
    compiler.run_primitive_validation()


def test_run_primitive_validation_valid(mocker):
    mocker.patch.object(compiler, "CONFIG", {"primitive_schema_file": "schemas/index.yaml", "source_dir": "schemas"})
    mocker.patch("glob.glob", return_value=["schemas/atomic/shape.yaml"])
    mocker.patch("tools.compiler.load_yaml", side_effect=[
        {"spec": {"type": "object"}},
        {"metadata": {"name": "Shape"}, "spec": {"kind": "AtomicPrimitive"}}
    ])
    mocker.patch("tools.compiler.validate", return_value=None)
    compiler.run_primitive_validation()


def test_run_primitive_validation_invalid(mocker):
    mocker.patch.object(compiler, "CONFIG", {"primitive_schema_file": "schemas/index.yaml", "source_dir": "schemas"})
    mocker.patch("glob.glob", return_value=["schemas/atomic/bad.yaml"])
    mocker.patch("os.path.getsize", return_value=100)
    mocker.patch("tools.compiler.load_yaml", side_effect=[
        {"spec": {"type": "object"}},
        {"metadata": {}, "spec": {}}
    ])
    mocker.patch("tools.compiler.validate", side_effect=ValidationError("invalid primitive"))
    with pytest.raises(SystemExit) as e:
        compiler.run_primitive_validation()
    assert e.value.code == 1


# ── run_domain_compatibility_check ───────────────────────────────────────────

def _make_managed_entity():
    return {
        "spec": {
            "slots": {
                "identity":       {"mode": "required"},
                "config_surface": {"mode": "required"},
                "state_surface":  {"mode": "required"},
                "lifecycle":      {"mode": "sealed"},
            }
        }
    }


def test_domain_check_valid(mocker, tmp_path):
    domain_file = tmp_path / "domain.yaml"
    domain_file.write_text(yaml.dump({
        "spec": {
            "kind": "DomainComposition",
            "base": {"ref": str(tmp_path / "managed-entity.yaml")},
            "identity": {},
            "config_surface": {},
            "state_surface": {},
        }
    }))
    me_file = tmp_path / "managed-entity.yaml"
    me_file.write_text(yaml.dump(_make_managed_entity()))

    mocker.patch.object(compiler, "CONFIG", {"primitive_schema_file": "schemas/index.yaml", "source_dir": str(tmp_path)})
    mocker.patch("glob.glob", return_value=[str(domain_file)])
    compiler.run_domain_compatibility_check()


def test_domain_check_sealed_override(mocker, tmp_path):
    domain_file = tmp_path / "domain.yaml"
    domain_file.write_text(yaml.dump({
        "spec": {
            "kind": "DomainComposition",
            "base": {"ref": str(tmp_path / "managed-entity.yaml")},
            "identity": {},
            "config_surface": {},
            "state_surface": {},
            "lifecycle": {},   # ← sealed — nem szabad felülírni
        }
    }))
    me_file = tmp_path / "managed-entity.yaml"
    me_file.write_text(yaml.dump(_make_managed_entity()))

    mocker.patch.object(compiler, "CONFIG", {"primitive_schema_file": "schemas/index.yaml", "source_dir": str(tmp_path)})
    mocker.patch("glob.glob", return_value=[str(domain_file)])
    with pytest.raises(SystemExit) as e:
        compiler.run_domain_compatibility_check()
    assert e.value.code == 1


def test_domain_check_required_missing(mocker, tmp_path):
    domain_file = tmp_path / "domain.yaml"
    domain_file.write_text(yaml.dump({
        "spec": {
            "kind": "DomainComposition",
            "base": {"ref": str(tmp_path / "managed-entity.yaml")},
            "identity": {},
            # config_surface hiányzik — required
        }
    }))
    me_file = tmp_path / "managed-entity.yaml"
    me_file.write_text(yaml.dump(_make_managed_entity()))

    mocker.patch.object(compiler, "CONFIG", {"primitive_schema_file": "schemas/index.yaml", "source_dir": str(tmp_path)})
    mocker.patch("glob.glob", return_value=[str(domain_file)])
    with pytest.raises(SystemExit) as e:
        compiler.run_domain_compatibility_check()
    assert e.value.code == 1


# ── run_release ───────────────────────────────────────────────────────────────

def test_run_release_no_vault_vars(mocker):
    mocker.patch.object(os, "getenv", return_value=None)
    mocker.patch("tools.compiler.validate_release_prerequisites", return_value=("0.1.1", "primitives/"))
    mocker.patch("tools.compiler.load_project_config", return_value=make_project_config()["compiler_settings"])
    with pytest.raises(SystemExit) as e:
        compiler.run_release()
    assert e.value.code == 1


def test_validate_release_dirty_git(mocker):
    mocker.patch("tools.compiler.load_project_config", return_value=make_project_config())
    mocker.patch("tools.compiler.run_git_command", side_effect=lambda cmd: "M somefile.yaml" if "status" in cmd else "")
    with pytest.raises(SystemExit) as e:
        compiler.validate_release_prerequisites()
    assert e.value.code == 1


def test_validate_release_wrong_branch(mocker):
    mocker.patch("tools.compiler.load_project_config", return_value=make_project_config())
    def git_cmd(cmd):
        if "status" in cmd: return ""
        if "rev-parse" in cmd: return "main"
        return ""
    mocker.patch("tools.compiler.run_git_command", side_effect=git_cmd)
    with pytest.raises(SystemExit) as e:
        compiler.validate_release_prerequisites()
    assert e.value.code == 1


def test_validate_release_invalid_version_increment(mocker):
    mocker.patch("tools.compiler.load_project_config", return_value=make_project_config())
    def git_cmd(cmd):
        if "status" in cmd: return ""
        if "rev-parse" in cmd: return "primitives/releases/v0.9.0"
        if "tag" in cmd: return "primitives/@v0.1.0"
        return ""
    mocker.patch("tools.compiler.run_git_command", side_effect=git_cmd)
    with pytest.raises(SystemExit) as e:
        compiler.validate_release_prerequisites()
    assert e.value.code == 1


def test_validate_release_first_release(mocker):
    mocker.patch("tools.compiler.load_project_config", return_value=make_project_config())
    def git_cmd(cmd):
        if "status" in cmd: return ""
        if "rev-parse" in cmd: return "primitives/releases/v0.1.1"
        if "tag" in cmd: return ""
        return ""
    mocker.patch("tools.compiler.run_git_command", side_effect=git_cmd)
    version, component = compiler.validate_release_prerequisites()
    assert version == "0.1.1"
    assert component == "primitives/"


# ── _verify_cert_signature ───────────────────────────────────────────────────

def test_verify_cert_signature_ok():
    private_key, cert_pem = _make_test_key_and_cert()
    content_hash = compiler.get_sha256_b64(b"test payload")
    signature = _sign_hash(private_key, content_hash)
    ok, reason = compiler._verify_cert_signature(cert_pem, signature, content_hash)
    assert ok, reason


def test_verify_cert_signature_wrong_key():
    _, cert_pem = _make_test_key_and_cert()
    other_key, _ = _make_test_key_and_cert()
    content_hash = compiler.get_sha256_b64(b"test payload")
    # Sign with a different key — verification against cert must fail
    signature = _sign_hash(other_key, content_hash)
    ok, reason = compiler._verify_cert_signature(cert_pem, signature, content_hash)
    assert not ok


def test_verify_cert_signature_bad_format():
    _, cert_pem = _make_test_key_and_cert()
    ok, reason = compiler._verify_cert_signature(cert_pem, "not-vault-format", "AAAA")
    assert not ok
    assert "format" in reason.lower()


def test_verify_cert_signature_invalid_cert():
    ok, reason = compiler._verify_cert_signature("NOT A CERT", "vault:v1:AAAA", "AAAA")
    assert not ok


# ── _load_valid_commitment ────────────────────────────────────────────────────

def test_load_valid_commitment_missing_file(tmp_path, mocker):
    mocker.patch("os.path.isfile", return_value=False)
    with pytest.raises(SystemExit) as e:
        compiler._load_valid_commitment()
    assert e.value.code == 1


def test_load_valid_commitment_wrong_kind(tmp_path, mocker):
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("tools.compiler.load_yaml", return_value={"kind": "WrongKind"})
    with pytest.raises(SystemExit) as e:
        compiler._load_valid_commitment()
    assert e.value.code == 1


def test_load_valid_commitment_expired(mocker):
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("tools.compiler.load_yaml", return_value={
        "kind": "DeveloperCommitment",
        "validity": {"from": "2020-01-01", "until": "2021-01-01"},
    })
    with pytest.raises(SystemExit) as e:
        compiler._load_valid_commitment()
    assert e.value.code == 1


def _make_signed_commitment(key=None, cert=None, until="2099-01-01"):
    """A commitment whose pledge really is signed over {createdBy, validity}.

    The fixture used to carry `certificate: "PEM"` and no pledge at all, and
    passed — which was the defect: the loader checked the date window and
    nothing else.
    """
    if key is None or cert is None:
        key, cert = make_test_key_and_cert("Test Dev")
    today = datetime.datetime.now(datetime.timezone.utc).date()
    validity = {"from": str(today), "until": until}
    created_by = {"name": "Test", "email": "t@example.com", "certificate": cert}
    content_hash = compiler.get_sha256_b64(
        compiler.to_canonical_json({"createdBy": created_by, "validity": validity}))
    return key, {
        "kind": "DeveloperCommitment",
        "validity": validity,
        "createdBy": created_by,
        "pledge": {"content_hash": content_hash, "sign": sign_hash(key, content_hash)},
    }


def test_load_valid_commitment_ok(mocker):
    mocker.patch("os.path.isfile", return_value=True)
    _, commitment = _make_signed_commitment()
    mocker.patch("tools.compiler.load_yaml", return_value=commitment)
    result = compiler._load_valid_commitment()
    assert result["kind"] == "DeveloperCommitment"


def test_commitment_without_a_pledge_is_rejected(mocker):
    """The exact shape the old fixture had: dates only, no signature."""
    mocker.patch("os.path.isfile", return_value=True)
    _, commitment = _make_signed_commitment()
    del commitment["pledge"]
    mocker.patch("tools.compiler.load_yaml", return_value=commitment)
    with pytest.raises(SystemExit) as e:
        compiler._load_valid_commitment()
    assert e.value.code == 1


def test_commitment_with_edited_fields_is_rejected(mocker):
    """A forged identity: the name is changed after the pledge was signed."""
    mocker.patch("os.path.isfile", return_value=True)
    _, commitment = _make_signed_commitment()
    commitment["createdBy"]["name"] = "Mallory"
    mocker.patch("tools.compiler.load_yaml", return_value=commitment)
    with pytest.raises(SystemExit) as e:
        compiler._load_valid_commitment()
    assert e.value.code == 1


def test_commitment_with_extended_validity_is_rejected(mocker):
    """Stretching the window after signing must break the hash."""
    mocker.patch("os.path.isfile", return_value=True)
    _, commitment = _make_signed_commitment()
    commitment["validity"]["until"] = "2199-01-01"
    mocker.patch("tools.compiler.load_yaml", return_value=commitment)
    with pytest.raises(SystemExit) as e:
        compiler._load_valid_commitment()
    assert e.value.code == 1


def test_commitment_signed_by_another_key_is_rejected(mocker):
    """The hash is right, the signature is someone else's."""
    mocker.patch("os.path.isfile", return_value=True)
    _, commitment = _make_signed_commitment()
    other_key, _ = make_test_key_and_cert("Someone Else")
    commitment["pledge"]["sign"] = sign_hash(
        other_key, commitment["pledge"]["content_hash"])
    mocker.patch("tools.compiler.load_yaml", return_value=commitment)
    with pytest.raises(SystemExit) as e:
        compiler._load_valid_commitment()
    assert e.value.code == 1


def test_commitment_without_certificate_is_rejected(mocker):
    """Nothing to verify the signature against."""
    mocker.patch("os.path.isfile", return_value=True)
    _, commitment = _make_signed_commitment()
    del commitment["createdBy"]["certificate"]
    mocker.patch("tools.compiler.load_yaml", return_value=commitment)
    with pytest.raises(SystemExit) as e:
        compiler._load_valid_commitment()
    assert e.value.code == 1


# ── run_verify_release ────────────────────────────────────────────────────────

# The implementations live in tests/_helpers.py so the two test modules share
# one copy. These names stay as thin aliases: they are used ~20 times below.
_make_test_key_and_cert = make_test_key_and_cert
_sign_hash = sign_hash


def _make_valid_bundle(specs=None, private_key=None, cert_pem=None,
                       release_private_key=None, release_cert_pem=None):
    """Builds a PrimitiveRelease bundle with a real ECDSA signature."""
    if private_key is None or cert_pem is None:
        private_key, cert_pem = _make_test_key_and_cert()
    if release_private_key is None or release_cert_pem is None:
        release_private_key, release_cert_pem = _make_test_key_and_cert()
    if specs is None:
        specs = [{"id": "shape", "source_path": "schemas/atomic/shape.yaml",
                  "meta_hash": "abc", "spec": {"kind": "AtomicPrimitive"}}]
    validity = {"from": "2026-01-01", "until": "2099-01-01"}
    created_by = {"name": "Test Dev", "email": "dev@example.com", "certificate": cert_pem}
    release_created_by = {"name": "Test Releaser", "email": "releaser@example.com",
                          "certificate": release_cert_pem}
    hash_payload = {
        "createdBy": created_by,
        "releasedBy": release_created_by,
        "specs": specs,
        "validity": validity,
    }
    build_hash = compiler.get_sha256_b64(compiler.to_canonical_json(hash_payload))
    signature = _sign_hash(release_private_key, build_hash)
    return {
        "kind": "PrimitiveRelease",
        "version": "0.1.5",
        "timestamp": "2026-05-24T00:00:00+00:00",
        "validity": validity,
        "createdBy": created_by,
        "specs": specs,
        "release": {
            "createdBy": release_created_by,
            "build_hash": build_hash,
            "sign": signature,
        },
    }


def test_verify_release_ok(mocker, tmp_path):
    bundle = _make_valid_bundle()
    artifact = tmp_path / "release.yaml"
    artifact.write_text(yaml.dump(bundle))
    mocker.patch("os.path.isfile", side_effect=lambda p: str(p) == str(artifact))
    compiler.run_verify_release(str(artifact))


def test_verify_release_missing_cert(mocker, tmp_path):
    bundle = _make_valid_bundle()
    del bundle["createdBy"]["certificate"]
    artifact = tmp_path / "release.yaml"
    artifact.write_text(yaml.dump(bundle))
    mocker.patch("os.path.isfile", side_effect=lambda p: str(p) == str(artifact))
    with pytest.raises(SystemExit) as e:
        compiler.run_verify_release(str(artifact))
    assert e.value.code == 1


def test_verify_release_hash_mismatch(mocker, tmp_path):
    bundle = _make_valid_bundle()
    bundle["release"]["build_hash"] = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    artifact = tmp_path / "release.yaml"
    artifact.write_text(yaml.dump(bundle))
    mocker.patch("os.path.isfile", side_effect=lambda p: str(p) == str(artifact))
    with pytest.raises(SystemExit) as e:
        compiler.run_verify_release(str(artifact))
    assert e.value.code == 1


def test_verify_release_bad_signature(mocker, tmp_path):
    """A tampered signature (wrong key) must fail verification."""
    bundle = _make_valid_bundle()
    # Replace signature with one from a different key
    other_key, _ = _make_test_key_and_cert()
    bundle["release"]["sign"] = _sign_hash(other_key, bundle["release"]["build_hash"])
    artifact = tmp_path / "release.yaml"
    artifact.write_text(yaml.dump(bundle))
    mocker.patch("os.path.isfile", side_effect=lambda p: str(p) == str(artifact))
    with pytest.raises(SystemExit) as e:
        compiler.run_verify_release(str(artifact))
    assert e.value.code == 1


def test_verify_release_wrong_kind(mocker, tmp_path):
    bundle = _make_valid_bundle()
    bundle["kind"] = "SomethingElse"
    artifact = tmp_path / "release.yaml"
    artifact.write_text(yaml.dump(bundle))
    mocker.patch("os.path.isfile", side_effect=lambda p: str(p) == str(artifact))
    with pytest.raises(SystemExit) as e:
        compiler.run_verify_release(str(artifact))
    assert e.value.code == 1


def test_verify_release_strict_meta_hash_mismatch_fails(tmp_path, mocker):
    """--strict: meta_hash mismatch against a local source file is a hard failure."""
    src = tmp_path / "shape.yaml"
    src.write_bytes(b"different content")
    specs = [{"id": "shape", "source_path": str(src), "meta_hash": "AAAA", "spec": {}}]
    bundle = _make_valid_bundle(specs=specs)
    artifact = tmp_path / "release.yaml"
    artifact.write_text(yaml.dump(bundle))
    # signature verification passes — testing strict meta_hash logic specifically
    mocker.patch("tools.compiler._verify_cert_signature", return_value=(True, "OK"))
    with pytest.raises(SystemExit) as e:
        compiler.run_verify_release(str(artifact), strict=True)
    assert e.value.code == 1


def test_verify_release_non_strict_meta_hash_mismatch_warns(tmp_path, capsys, mocker):
    """Default (non-strict): meta_hash mismatch is only a warning."""
    src = tmp_path / "shape.yaml"
    src.write_bytes(b"different content")
    specs = [{"id": "shape", "source_path": str(src), "meta_hash": "AAAA", "spec": {}}]
    bundle = _make_valid_bundle(specs=specs)
    artifact = tmp_path / "release.yaml"
    artifact.write_text(yaml.dump(bundle))
    mocker.patch("tools.compiler._verify_cert_signature", return_value=(True, "OK"))
    compiler.run_verify_release(str(artifact), strict=False)
    captured = capsys.readouterr()
    assert "WARNING" in captured.out or "⚠" in captured.out


# ── run_pledge ────────────────────────────────────────────────────────────────

def test_run_pledge_no_vault_vars(mocker):
    mocker.patch.object(os, "getenv", return_value=None)
    mocker.patch("tools.compiler.validate_release_prerequisites", return_value=("0.1.5", "primitives/"))
    with pytest.raises(SystemExit) as e:
        compiler.run_pledge()
    assert e.value.code == 1


def test_run_pledge_no_cert_path(mocker):
    mocker.patch.object(os, "getenv", side_effect=lambda k, d=None: {
        "VAULT_ADDR": "https://vault:8200",
        "VAULT_TOKEN": "token",
    }.get(k, d))
    mocker.patch("tools.compiler.load_project_config", return_value={
        "project": {"owner": "Dev"},
        "compiler_settings": {"vault_key_name": "key", "vault_cert_path": None, "owner_email": "", "validity_days": 365},
    })
    with pytest.raises(SystemExit) as e:
        compiler.run_pledge()
    assert e.value.code == 1


# ── main ──────────────────────────────────────────────────────────────────────

def test_main_no_arguments(mocker):
    mocker.patch.object(sys, "argv", ["compiler.py"])
    with pytest.raises(SystemExit) as e:
        compiler.main()
    assert e.value.code == 1


def test_main_unknown_command(mocker):
    mocker.patch.object(sys, "argv", ["compiler.py", "unknown"])
    with pytest.raises(SystemExit) as e:
        compiler.main()
    assert e.value.code == 1


def test_main_help(mocker, capsys):
    mocker.patch.object(sys, "argv", ["compiler.py", "--help"])
    compiler.main()
    captured = capsys.readouterr()
    assert "validate" in captured.out
    assert "pledge" in captured.out
    assert "verify-release" in captured.out


def test_main_verify_release_missing_arg(mocker):
    mocker.patch.object(sys, "argv", ["compiler.py", "verify-release"])
    with pytest.raises(SystemExit) as e:
        compiler.main()
    assert e.value.code == 1


# ---------------------------------------------------------------------------
# Version injection
# ---------------------------------------------------------------------------

def test_inject_version_replaces_any_dev_placeholder():
    """Every vX.Y[.Z].dev is a placeholder, not just the literal v0.0.dev.

    Regression: the check compared against 'v0.0.dev' literally. shape.yaml and
    role.yaml moved to v0.1.dev, so a release would have shipped those two files
    still saying '.dev' while every other spec carried the real version.
    """
    doc = {
        "a": {"version": "v0.0.dev"},
        "b": {"version": "v0.1.dev"},
        "c": [{"version": "v2.13.dev"}, {"version": "v1.0.0.dev"}],
        "keep": {"version": "v0.1.5", "note": "v0.1.dev is fine inside prose"},
    }
    out = compiler._inject_version(doc, "0.2.0")
    assert out["a"]["version"] == "0.2.0"
    assert out["b"]["version"] == "0.2.0"
    assert out["c"][0]["version"] == "0.2.0"
    assert out["c"][1]["version"] == "0.2.0"
    # A released version is not a placeholder and must survive untouched.
    assert out["keep"]["version"] == "v0.1.5"
    # Only whole-string placeholders are replaced, never a substring.
    assert out["keep"]["note"] == "v0.1.dev is fine inside prose"


# ---------------------------------------------------------------------------
# Release envelope (what build_hash actually covers)
# ---------------------------------------------------------------------------

def _make_v2_bundle():
    """A bundle signed under envelope v2: the hash covers the whole artifact."""
    bundle = _make_valid_bundle()
    release_key, release_cert = make_test_key_and_cert("Test Releaser")
    bundle["release"]["createdBy"]["certificate"] = release_cert
    bundle["release"]["envelope"] = 2
    bundle["provenance"] = {"envelope": 2, "source_commit": "0" * 40}
    payload = compiler._release_hash_payload(bundle, 2)
    build_hash = compiler.get_sha256_b64(compiler.to_canonical_json(payload))
    bundle["release"]["build_hash"] = build_hash
    bundle["release"]["sign"] = sign_hash(release_key, build_hash)
    return bundle


def test_envelope_v1_still_verifies(mocker, tmp_path):
    """release/cic-primitives-v0.1.5.yaml was signed under v1 and must keep working."""
    bundle = _make_valid_bundle()
    assert "envelope" not in bundle["release"]  # absent means v1
    artifact = tmp_path / "release.yaml"
    artifact.write_text(yaml.dump(bundle))
    mocker.patch("os.path.isfile", side_effect=lambda p: str(p) == str(artifact))
    compiler.run_verify_release(str(artifact))


def test_envelope_v2_verifies(mocker, tmp_path):
    bundle = _make_v2_bundle()
    artifact = tmp_path / "release.yaml"
    artifact.write_text(yaml.dump(bundle))
    mocker.patch("os.path.isfile", side_effect=lambda p: str(p) == str(artifact))
    compiler.run_verify_release(str(artifact))


def test_envelope_v1_leaves_version_and_timestamp_unsigned(mocker, tmp_path):
    """The exact forgery an audit demonstrated: relabel the release, still verify.

    Kept as a test rather than fixed in place, because v0.1.5 is already signed
    this way. It documents precisely what a v1 artifact does NOT prove.
    """
    bundle = _make_valid_bundle()
    bundle["version"] = "9.9.9"
    bundle["timestamp"] = "2099-01-01T00:00:00+00:00"
    artifact = tmp_path / "release.yaml"
    artifact.write_text(yaml.dump(bundle))
    mocker.patch("os.path.isfile", side_effect=lambda p: str(p) == str(artifact))
    compiler.run_verify_release(str(artifact))  # no exception: v1 cannot see this


def test_envelope_v2_catches_relabelled_version(mocker, tmp_path):
    """The same forgery under v2 must break build_hash."""
    bundle = _make_v2_bundle()
    bundle["version"] = "9.9.9"
    bundle["timestamp"] = "2099-01-01T00:00:00+00:00"
    artifact = tmp_path / "release.yaml"
    artifact.write_text(yaml.dump(bundle))
    mocker.patch("os.path.isfile", side_effect=lambda p: str(p) == str(artifact))
    with pytest.raises(SystemExit) as e:
        compiler.run_verify_release(str(artifact))
    assert e.value.code == 1


def test_envelope_v2_catches_tampered_provenance(mocker, tmp_path):
    bundle = _make_v2_bundle()
    bundle["provenance"]["source_commit"] = "f" * 40
    artifact = tmp_path / "release.yaml"
    artifact.write_text(yaml.dump(bundle))
    mocker.patch("os.path.isfile", side_effect=lambda p: str(p) == str(artifact))
    with pytest.raises(SystemExit) as e:
        compiler.run_verify_release(str(artifact))
    assert e.value.code == 1


def test_unknown_envelope_version_is_rejected(mocker, tmp_path):
    bundle = _make_valid_bundle()
    bundle["release"]["envelope"] = 99
    artifact = tmp_path / "release.yaml"
    artifact.write_text(yaml.dump(bundle))
    mocker.patch("os.path.isfile", side_effect=lambda p: str(p) == str(artifact))
    with pytest.raises(SystemExit) as e:
        compiler.run_verify_release(str(artifact))
    assert e.value.code == 1


# ---------------------------------------------------------------------------
# CIC counter-signature (the schema described it; the verifier ignored it)
# ---------------------------------------------------------------------------

def _add_countersign(bundle, authority_key=None, authority_cert=None, root_pem=None):
    if authority_key is None:
        authority_key, authority_cert = make_test_key_and_cert("CIC Source CA")
    bundle["cic_countersign"] = {
        "authority": {
            "name": "CIC Source CA",
            "certificate": authority_cert,
            "root_certificate": root_pem if root_pem is not None else authority_cert,
        },
        "signed_payload": "build_hash",
        "sign": sign_hash(authority_key, bundle["release"]["build_hash"]),
    }
    return bundle


def test_countersign_verifies(mocker, tmp_path):
    bundle = _add_countersign(_make_valid_bundle())
    artifact = tmp_path / "release.yaml"
    artifact.write_text(yaml.dump(bundle))
    mocker.patch("os.path.isfile", side_effect=lambda p: str(p) == str(artifact))
    compiler.run_verify_release(str(artifact))


def test_forged_countersign_is_rejected(mocker, tmp_path):
    """The exact forgery an audit demonstrated: replace sign and root, still 'OK'."""
    bundle = _add_countersign(_make_valid_bundle())
    bundle["cic_countersign"]["sign"] = "vault:v1:" + "A" * 88
    artifact = tmp_path / "release.yaml"
    artifact.write_text(yaml.dump(bundle))
    mocker.patch("os.path.isfile", side_effect=lambda p: str(p) == str(artifact))
    with pytest.raises(SystemExit) as e:
        compiler.run_verify_release(str(artifact))
    assert e.value.code == 1


def test_countersign_not_chaining_to_its_root_is_rejected(mocker, tmp_path):
    """An authority certificate that its own declared root did not issue."""
    _, unrelated_root = make_test_key_and_cert("Unrelated Root")
    bundle = _add_countersign(_make_valid_bundle(), root_pem=unrelated_root)
    artifact = tmp_path / "release.yaml"
    artifact.write_text(yaml.dump(bundle))
    mocker.patch("os.path.isfile", side_effect=lambda p: str(p) == str(artifact))
    with pytest.raises(SystemExit) as e:
        compiler.run_verify_release(str(artifact))
    assert e.value.code == 1


def test_countersign_wrong_signed_payload_is_rejected(mocker, tmp_path):
    bundle = _add_countersign(_make_valid_bundle())
    bundle["cic_countersign"]["signed_payload"] = "something_else"
    artifact = tmp_path / "release.yaml"
    artifact.write_text(yaml.dump(bundle))
    mocker.patch("os.path.isfile", side_effect=lambda p: str(p) == str(artifact))
    with pytest.raises(SystemExit) as e:
        compiler.run_verify_release(str(artifact))
    assert e.value.code == 1


# ---------------------------------------------------------------------------
# Certificate chain and signature: the branches that decide trust
# ---------------------------------------------------------------------------

def test_chain_accepts_a_genuinely_issued_certificate():
    root_key, root_pem = make_test_key_and_cert("Test Root")
    _, leaf_pem = make_test_key_and_cert(
        "Leaf", issuer_key=root_key, issuer_name=cert_subject_name("Test Root"))
    ok, reason = compiler._verify_cert_chain(leaf_pem, root_pem)
    assert ok, reason


def test_chain_rejects_an_expired_root():
    """A chain check that accepts an expired CA proves nothing about today."""
    root_key, root_pem = make_test_key_and_cert(
        "Old Root", not_before_days=-800, not_after_days=-400)
    _, leaf_pem = make_test_key_and_cert(
        "Leaf", issuer_key=root_key, issuer_name=cert_subject_name("Old Root"))
    ok, reason = compiler._verify_cert_chain(leaf_pem, root_pem)
    assert not ok
    assert "expired" in reason


def test_chain_rejects_a_not_yet_valid_certificate():
    root_key, root_pem = make_test_key_and_cert("Test Root")
    _, leaf_pem = make_test_key_and_cert(
        "Future Leaf", not_before_days=30, not_after_days=400,
        issuer_key=root_key, issuer_name=cert_subject_name("Test Root"))
    ok, reason = compiler._verify_cert_chain(leaf_pem, root_pem)
    assert not ok
    assert "not valid yet" in reason


def test_chain_rejects_an_unrelated_root():
    _, root_pem = make_test_key_and_cert("Unrelated Root")
    _, leaf_pem = make_test_key_and_cert("Leaf")
    ok, reason = compiler._verify_cert_chain(leaf_pem, root_pem)
    assert not ok
    assert "issuer mismatch" in reason


def test_chain_rejects_garbage_pem():
    _, root_pem = make_test_key_and_cert("Root")
    ok, reason = compiler._verify_cert_chain("not a certificate", root_pem)
    assert not ok
    assert "parse error" in reason


def test_signature_rejects_a_foreign_prefix():
    """Only vault:v1: is a signature this tool knows how to read."""
    key, cert = make_test_key_and_cert()
    digest = compiler.get_sha256_b64(b"payload")
    real = sign_hash(key, digest)
    ok, reason = compiler._verify_cert_signature(
        cert, real.replace("vault:v1:", "vault:v9:"), digest)
    assert not ok
    assert "signature format" in reason.lower()


def test_signature_rejects_undecodable_base64():
    key, cert = make_test_key_and_cert()
    digest = compiler.get_sha256_b64(b"payload")
    ok, reason = compiler._verify_cert_signature(cert, "vault:v1:!!!!", digest)
    assert not ok


def test_fingerprint_of_garbage_is_none():
    assert compiler._cert_fingerprint("not a pem") is None


def test_fingerprint_is_stable_and_distinguishing():
    _, a = make_test_key_and_cert("A")
    _, b = make_test_key_and_cert("B")
    assert compiler._cert_fingerprint(a) == compiler._cert_fingerprint(a)
    assert compiler._cert_fingerprint(a) != compiler._cert_fingerprint(b)


# ---------------------------------------------------------------------------
# Provenance block: what the signature covers about the build's origin
# ---------------------------------------------------------------------------

def test_collect_provenance_records_the_source_and_digests():
    p = compiler._collect_provenance()
    assert p["envelope"] == compiler.RELEASE_ENVELOPE_VERSION
    # In a git checkout this is a real commit id; the point is that the field
    # exists so the signature covers it either way.
    assert "source_commit" in p
    for key in ("dependency_lock_sha256", "grammar_sha256", "grammar_schema_sha256"):
        assert key in p


def test_collect_provenance_digest_follows_the_file(tmp_path, monkeypatch):
    """A changed dependency lock must change the digest the release signs."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "dependency.yaml").write_text("a: 1\n")
    first = compiler._collect_provenance()["dependency_lock_sha256"]
    (tmp_path / "dependency.yaml").write_text("a: 2\n")
    second = compiler._collect_provenance()["dependency_lock_sha256"]
    assert first != second


def test_collect_provenance_survives_a_missing_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    p = compiler._collect_provenance()
    assert p["dependency_lock_sha256"] is None


# ---------------------------------------------------------------------------
# The release grammar gate
# ---------------------------------------------------------------------------

def _grammar_sandbox(tmp_path, composition_text):
    """A tree run_grammar_gate() can run in: the real grammar, a chosen corpus."""
    repo = pathlib.Path(compiler.__file__).resolve().parent.parent
    (tmp_path / "proposals").mkdir()
    (tmp_path / "proposals" / "atom-grammar").symlink_to(
        repo / "proposals" / "atom-grammar", target_is_directory=True)
    (tmp_path / "schemas" / "examples").mkdir(parents=True)
    (tmp_path / "schemas" / "examples" / "c.yaml").write_text(composition_text)
    return tmp_path


_GOOD_COMPOSITION = """
spec:
  kind: AtomicPrimitive
  config_surface:
    nodes:
      - name: replicas
        shape_type: scalar
        scalar_type: integer
        role: config
        optional: true
        default: 1
        contract:
          - type: range
            expression: "1..1000"
"""

_BAD_COMPOSITION = _GOOD_COMPOSITION.replace("default: 1", "default: 0")


def test_grammar_gate_passes_a_clean_composition(tmp_path, monkeypatch):
    monkeypatch.chdir(_grammar_sandbox(tmp_path, _GOOD_COMPOSITION))
    compiler.run_grammar_gate()


def test_grammar_gate_refuses_to_release_a_rejected_composition(tmp_path, monkeypatch):
    """A release must not ship what this repository's own gate rejects."""
    monkeypatch.chdir(_grammar_sandbox(tmp_path, _BAD_COMPOSITION))
    with pytest.raises(SystemExit) as e:
        compiler.run_grammar_gate()
    assert e.value.code == 1


def test_grammar_gate_refuses_unparseable_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(_grammar_sandbox(tmp_path, "spec: [unclosed\n"))
    with pytest.raises(SystemExit) as e:
        compiler.run_grammar_gate()
    assert e.value.code == 1


def test_grammar_gate_refuses_to_run_without_the_grammar(tmp_path, monkeypatch):
    """Missing checker is a failure, not a skip: absence must not read as pass."""
    (tmp_path / "schemas" / "examples").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as e:
        compiler.run_grammar_gate()
    assert e.value.code == 1


# ---------------------------------------------------------------------------
# Vault transport
# ---------------------------------------------------------------------------

def test_vault_sign_returns_the_signature(mocker):
    resp = mocker.Mock(status_code=200)
    resp.json.return_value = {"data": {"signature": "vault:v1:abc"}}
    mocker.patch("tools.compiler.requests.post", return_value=resp)
    assert compiler._vault_sign("aGFzaA==", "https://v", "t", "k", False) == "vault:v1:abc"


def test_vault_sign_exits_on_an_error_response(mocker):
    resp = mocker.Mock(status_code=403, text="permission denied")
    mocker.patch("tools.compiler.requests.post", return_value=resp)
    with pytest.raises(SystemExit):
        compiler._vault_sign("aGFzaA==", "https://v", "t", "k", False)


def test_vault_get_cert_returns_the_pem(mocker):
    resp = mocker.Mock(status_code=200)
    resp.json.return_value = {"data": {"data": {"crt": "-----BEGIN CERTIFICATE-----"}}}
    mocker.patch("tools.compiler.requests.get", return_value=resp)
    got = compiler._vault_get_cert("https://v", "t", "kv/certs/crt", False)
    assert got.startswith("-----BEGIN CERTIFICATE-----")


def test_vault_get_cert_exits_on_an_error_response(mocker):
    resp = mocker.Mock(status_code=404, text="no such path")
    mocker.patch("tools.compiler.requests.get", return_value=resp)
    with pytest.raises(SystemExit):
        compiler._vault_get_cert("https://v", "t", "kv/certs/crt", False)


def test_vault_get_cert_rejects_a_malformed_path():
    """`mount/secret/key` or nothing — a guessed path fetches the wrong secret."""
    with pytest.raises(SystemExit):
        compiler._vault_get_cert("https://v", "t", "just-a-name", False)


# ---------------------------------------------------------------------------
# run_release: the whole envelope v2 assembly, with Vault and git mocked
# ---------------------------------------------------------------------------

_META = """metadata:
  name: {name}
  version: {version}
  description: Sandbox fixture for the release tests.
  owner: Test
  tags: [test]
  validatedBy:
    name: cic-primitives
    version: v0.1.dev
"""

_RELEASE_SETTINGS = {
    "source_dir": "schemas",
    "meta_schemas_dir": "./",
    "meta_schema_file": "md.meta.schema.yaml",
    "primitive_schema_file": "schemas/index.yaml",
    "vault_key_name": "k",
    "vault_cert_path": "kv/c/crt",
    "validity_days": 365,
}


def _release_sandbox(tmp_path, monkeypatch, mocker, version="0.1.6"):
    """A tree run_release() can complete in without Vault, git or a network.

    Worth the setup: run_release had 104 of its 120 lines uncovered, and it is
    the function that decides what a signed artifact contains. Every property
    asserted below — that the envelope is v2, that the hash covers the whole
    bundle, that provenance is inside it — was previously only checked by
    reading the code.
    """
    repo = pathlib.Path(compiler.__file__).resolve().parent.parent
    (tmp_path / "proposals").mkdir()
    (tmp_path / "proposals" / "atom-grammar").symlink_to(
        repo / "proposals" / "atom-grammar", target_is_directory=True)
    (tmp_path / "schemas" / "atomic").mkdir(parents=True)
    (tmp_path / "schemas" / "atomic" / "shape.yaml").write_text(
        _META.format(name="Shape", version="v0.1.dev")
        + "spec:\n  kind: AtomicPrimitive\n  fields: {a: 1}\n")
    (tmp_path / "schemas" / "examples").mkdir()
    (tmp_path / "schemas" / "examples" / "c.yaml").write_text(
        _META.format(name="Example", version="v0.1.dev") + _GOOD_COMPOSITION.lstrip("\n"))
    (tmp_path / "dependency.yaml").write_text("schema_version: '1'\n")
    # run_release() runs the three older validations first; they need the two
    # meta-schemas and a docs tree, so the sandbox carries the real ones.
    repo_root = pathlib.Path(compiler.__file__).resolve().parent.parent
    for name in ("md.meta.schema.yaml",):
        (tmp_path / name).write_text((repo_root / name).read_text())
    (tmp_path / "schemas" / "index.yaml").write_text(
        (repo_root / "schemas" / "index.yaml").read_text())
    monkeypatch.chdir(tmp_path)

    dev_key, dev_cert = make_test_key_and_cert("Dev")
    rel_key, rel_cert = make_test_key_and_cert("Releaser")
    today = datetime.datetime.now(datetime.timezone.utc).date()
    validity = {"from": str(today), "until": "2099-01-01"}
    created_by = {"name": "Dev", "email": "d@e", "certificate": dev_cert}
    commitment = {
        "kind": "DeveloperCommitment", "validity": validity, "createdBy": created_by,
    }

    monkeypatch.setenv("VAULT_ADDR", "https://vault")
    monkeypatch.setenv("VAULT_TOKEN", "token")
    mocker.patch("tools.compiler.validate_release_prerequisites",
                 return_value=(version, "primitives/"))
    mocker.patch("tools.compiler._load_valid_commitment", return_value=commitment)
    mocker.patch("tools.compiler._vault_get_cert", return_value=rel_cert)
    mocker.patch("tools.compiler._vault_sign",
                 side_effect=lambda digest, *a, **k: sign_hash(rel_key, digest))
    mocker.patch("tools.compiler.load_project_config", side_effect=lambda full_config=False: (
        {"project": {"name": "cic-primitives", "owner": "Dev"},
         "compiler_settings": _RELEASE_SETTINGS}
        if full_config else _RELEASE_SETTINGS))
    return tmp_path, version


def test_release_writes_an_envelope_v2_bundle(tmp_path, monkeypatch, mocker):
    root, version = _release_sandbox(tmp_path, monkeypatch, mocker)
    compiler.run_release()
    artifact = root / "release" / f"cic-primitives-v{version}.yaml"
    assert artifact.is_file()
    bundle = yaml.safe_load(artifact.read_text())
    assert bundle["kind"] == "PrimitiveRelease"
    assert bundle["release"]["envelope"] == compiler.RELEASE_ENVELOPE_VERSION == 2
    assert bundle["provenance"]["envelope"] == 2
    assert "source_commit" in bundle["provenance"]


def test_release_hash_covers_the_whole_bundle(tmp_path, monkeypatch, mocker):
    """Recomputing the v2 payload over the written artifact must reproduce it."""
    root, version = _release_sandbox(tmp_path, monkeypatch, mocker)
    compiler.run_release()
    bundle = yaml.safe_load(
        (root / "release" / f"cic-primitives-v{version}.yaml").read_text())
    recomputed = compiler.get_sha256_b64(compiler.to_canonical_json(
        compiler._release_hash_payload(bundle, 2)))
    assert recomputed == bundle["release"]["build_hash"]


def test_release_injects_the_version_into_every_spec(tmp_path, monkeypatch, mocker):
    """The v0.1.dev regression: a placeholder must not reach a signed artifact."""
    root, version = _release_sandbox(tmp_path, monkeypatch, mocker)
    compiler.run_release()
    bundle = yaml.safe_load(
        (root / "release" / f"cic-primitives-v{version}.yaml").read_text())
    versions = [s["spec"].get("metadata", {}).get("version")
                for s in bundle["specs"] if isinstance(s.get("spec"), dict)]
    assert all(v is None or not str(v).endswith(".dev") for v in versions)


def test_release_refuses_a_composition_the_grammar_rejects(tmp_path, monkeypatch, mocker):
    """The gate that was missing: a release must not ship a rejected composition."""
    root, _ = _release_sandbox(tmp_path, monkeypatch, mocker)
    (root / "schemas" / "examples" / "c.yaml").write_text(_BAD_COMPOSITION)
    with pytest.raises(SystemExit) as e:
        compiler.run_release()
    assert e.value.code == 1
    assert not (root / "release").exists()


def test_release_without_vault_credentials_exits(tmp_path, monkeypatch, mocker):
    _release_sandbox(tmp_path, monkeypatch, mocker)
    monkeypatch.delenv("VAULT_TOKEN")
    with pytest.raises(SystemExit):
        compiler.run_release()


# ---------------------------------------------------------------------------
# run_pledge: what the developer actually commits to
# ---------------------------------------------------------------------------

def _pledge_sandbox(tmp_path, monkeypatch, mocker):
    monkeypatch.chdir(tmp_path)
    key, cert = make_test_key_and_cert("Dev")
    monkeypatch.setenv("VAULT_ADDR", "https://vault")
    monkeypatch.setenv("VAULT_TOKEN", "token")
    mocker.patch("tools.compiler._vault_get_cert", return_value=cert)
    mocker.patch("tools.compiler._vault_sign",
                 side_effect=lambda digest, *a, **k: sign_hash(key, digest))
    mocker.patch("tools.compiler.load_project_config", side_effect=lambda full_config=False: (
        {"project": {"name": "cic-primitives", "owner": "Dev",
                     "contacts": [{"type": "email", "value": "d@e"}]},
         "compiler_settings": _RELEASE_SETTINGS}
        if full_config else _RELEASE_SETTINGS))
    return key, cert


def test_pledge_writes_a_commitment_its_own_loader_accepts(tmp_path, monkeypatch, mocker):
    """The round trip that matters: what run_pledge writes must verify.

    Before the pledge was cryptographically checked, this round trip proved
    nothing — the loader looked at dates only. Now it is the test that would
    catch a payload change on either side.
    """
    _pledge_sandbox(tmp_path, monkeypatch, mocker)
    compiler.run_pledge()
    assert (tmp_path / "commitment.yaml").is_file()
    commitment = compiler._load_valid_commitment()
    assert commitment["kind"] == "DeveloperCommitment"


def test_pledge_hash_covers_created_by_and_validity(tmp_path, monkeypatch, mocker):
    _pledge_sandbox(tmp_path, monkeypatch, mocker)
    compiler.run_pledge()
    commitment = compiler.load_yaml("commitment.yaml")
    expected = compiler.get_sha256_b64(compiler.to_canonical_json(
        {"createdBy": commitment["createdBy"], "validity": commitment["validity"]}))
    assert commitment["pledge"]["content_hash"] == expected


def test_a_pledge_edited_after_signing_stops_verifying(tmp_path, monkeypatch, mocker):
    """End to end: write a real pledge, tamper it, watch the loader refuse."""
    _pledge_sandbox(tmp_path, monkeypatch, mocker)
    compiler.run_pledge()
    commitment = compiler.load_yaml("commitment.yaml")
    commitment["createdBy"]["name"] = "Mallory"
    compiler.write_yaml("commitment.yaml", commitment)
    with pytest.raises(SystemExit) as e:
        compiler._load_valid_commitment()
    assert e.value.code == 1


def test_pledge_without_vault_credentials_exits(tmp_path, monkeypatch, mocker):
    _pledge_sandbox(tmp_path, monkeypatch, mocker)
    monkeypatch.delenv("VAULT_ADDR")
    with pytest.raises(SystemExit):
        compiler.run_pledge()


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------

def test_cli_without_arguments_exits(monkeypatch):
    monkeypatch.setattr("sys.argv", ["compiler.py"])
    with pytest.raises(SystemExit):
        compiler.main()


def test_cli_rejects_an_unknown_command(monkeypatch):
    monkeypatch.setattr("sys.argv", ["compiler.py", "not-a-command"])
    with pytest.raises(SystemExit):
        compiler.main()


def test_cli_verify_release_requires_a_file(monkeypatch):
    monkeypatch.setattr("sys.argv", ["compiler.py", "verify-release"])
    with pytest.raises(SystemExit):
        compiler.main()


def test_cli_trust_root_without_a_path_exits(monkeypatch):
    """A flag that silently does nothing is worse than a rejected one."""
    monkeypatch.setattr(
        "sys.argv", ["compiler.py", "verify-release", "a.yaml", "--trust-root"])
    with pytest.raises(SystemExit) as e:
        compiler.main()
    assert e.value.code == 2


def test_cli_passes_strict_and_trust_root_through(monkeypatch, mocker):
    called = {}
    mocker.patch("tools.compiler.run_verify_release",
                 side_effect=lambda p, strict=False, trust_root=None: called.update(
                     path=p, strict=strict, trust_root=trust_root))
    monkeypatch.setattr("sys.argv", [
        "compiler.py", "verify-release", "a.yaml", "--strict",
        "--trust-root", "root.pem"])
    compiler.main()
    assert called == {"path": "a.yaml", "strict": True, "trust_root": "root.pem"}


def test_cli_dispatches_validate(monkeypatch, mocker):
    v = mocker.patch("tools.compiler.run_validation")
    mocker.patch("tools.compiler.run_primitive_validation")
    mocker.patch("tools.compiler.run_domain_compatibility_check")
    monkeypatch.setattr("sys.argv", ["compiler.py", "validate"])
    compiler.main()
    v.assert_called_once()


# ---------------------------------------------------------------------------
# to_canonical_json: the function every hash in this repository is taken over
# ---------------------------------------------------------------------------

def test_canonical_json_is_independent_of_key_order():
    """Found by mutation testing: `sort_keys=True` -> `False` SURVIVED.

    Every digest here — build_hash, the pledge hash, meta_hash — is taken over
    this function's output. If key order leaked into it, two objects with the
    same content but different insertion order would hash differently, and no
    test would have noticed: every expected value in the suite is computed with
    the same function, so a mutation moves both sides together.

    This asserts the property directly instead, against a literal.
    """
    a = {"b": 1, "a": {"y": 2, "x": 3}, "c": [1, {"n": 1, "m": 2}]}
    b = {"c": [1, {"m": 2, "n": 1}], "a": {"x": 3, "y": 2}, "b": 1}
    assert compiler.to_canonical_json(a) == compiler.to_canonical_json(b)
    assert compiler.to_canonical_json(a) == (
        b'{"a":{"x":3,"y":2},"b":1,"c":[1,{"m":2,"n":1}]}')


def test_canonical_json_has_no_incidental_whitespace():
    """Separators are part of the contract: a space would change every digest."""
    assert compiler.to_canonical_json({"a": 1, "b": [1, 2]}) == b'{"a":1,"b":[1,2]}'


def test_canonical_json_preserves_list_order():
    """Sequences are ordered data; only MAPPING order is incidental."""
    assert (compiler.to_canonical_json([1, 2]) != compiler.to_canonical_json([2, 1]))


def test_sha256_helpers_are_stable_and_distinguishing():
    assert compiler.get_sha256_b64(b"a") == compiler.get_sha256_b64(b"a")
    assert compiler.get_sha256_b64(b"a") != compiler.get_sha256_b64(b"b")
    assert compiler.get_sha256_hex(b"a") != compiler.get_sha256_hex(b"b")


# ---------------------------------------------------------------------------
# Release version increments (mutation survivors in the gap logic)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("latest,candidate,allowed", [
    ("0.1.5", "0.1.6", True),    # patch
    ("0.1.5", "0.2.0", True),    # minor
    ("0.1.5", "1.0.0", True),    # major
    ("0.1.5", "0.1.7", False),   # patch gap
    ("0.1.5", "0.3.0", False),   # minor gap
    ("0.1.5", "2.0.0", False),   # major gap
    ("0.1.5", "0.2.1", False),   # minor bump with a non-zero patch
    ("0.1.5", "0.1.5", False),   # no increment at all
])
def test_release_version_must_be_the_next_increment(
        latest, candidate, allowed, mocker, monkeypatch, tmp_path):
    """A release that skips a version leaves an unexplained hole in the chain."""
    monkeypatch.chdir(tmp_path)
    mocker.patch("tools.compiler.load_project_config", return_value={
        "project": {"main_branch": "primitives/main"}})
    mocker.patch("tools.compiler.run_git_command", side_effect=lambda cmd: {
        "status": "", "rev-parse": f"primitives/releases/v{candidate}",
        "tag": f"primitives/@v{latest}",
    }[cmd[1]])
    if allowed:
        version, _ = compiler.validate_release_prerequisites()
        assert version == candidate
    else:
        with pytest.raises(SystemExit):
            compiler.validate_release_prerequisites()
