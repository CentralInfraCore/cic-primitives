import pytest
from tools import compiler
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


def test_load_valid_commitment_ok(mocker):
    mocker.patch("os.path.isfile", return_value=True)
    today = datetime.datetime.now(datetime.timezone.utc).date()
    mocker.patch("tools.compiler.load_yaml", return_value={
        "kind": "DeveloperCommitment",
        "validity": {"from": str(today), "until": "2099-01-01"},
        "createdBy": {"name": "Test", "email": "t@example.com", "certificate": "PEM"},
    })
    result = compiler._load_valid_commitment()
    assert result["kind"] == "DeveloperCommitment"


# ── run_verify_release ────────────────────────────────────────────────────────

def _make_test_key_and_cert():
    """Generates an ephemeral ECDSA P-256 key pair and self-signed certificate for tests."""
    from cryptography.hazmat.primitives.asymmetric.ec import generate_private_key, SECP256R1
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography import x509
    from cryptography.x509.oid import NameOID

    private_key = generate_private_key(SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test Dev")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .serial_number(x509.random_serial_number())
        .public_key(private_key.public_key())
        .sign(private_key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    return private_key, cert_pem


def _sign_hash(private_key, content_hash_b64):
    """Signs a pre-hashed digest with an ECDSA private key, returns vault:v1:... format."""
    from cryptography.hazmat.primitives.asymmetric.ec import ECDSA
    from cryptography.hazmat.primitives.asymmetric import utils as asym_utils
    from cryptography.hazmat.primitives import hashes

    hash_bytes = base64.b64decode(content_hash_b64)
    sig_bytes = private_key.sign(hash_bytes, ECDSA(asym_utils.Prehashed(hashes.SHA256())))
    return "vault:v1:" + base64.b64encode(sig_bytes).decode()


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
