import pytest
from tools import compiler
import os
import yaml
import sys
import hashlib
import base64
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


def test_main_validate(mocker):
    mocker.patch.object(sys, "argv", ["compiler.py", "validate"])
    mocker.patch("tools.compiler.run_validation")
    mocker.patch("tools.compiler.run_primitive_validation")
    mocker.patch("tools.compiler.run_domain_compatibility_check")
    compiler.main()


def test_main_release(mocker):
    mocker.patch.object(sys, "argv", ["compiler.py", "release"])
    mocker.patch("tools.compiler.run_release")
    compiler.main()


def test_main_verify_release_missing_arg(mocker):
    mocker.patch.object(sys, "argv", ["compiler.py", "verify-release"])
    with pytest.raises(SystemExit) as e:
        compiler.main()
    assert e.value.code == 1


def test_main_verify_release_with_arg(mocker):
    mocker.patch.object(sys, "argv", ["compiler.py", "verify-release", "release/test.yaml"])
    mocker.patch("tools.compiler.run_verify_release")
    compiler.main()


# ── run_git_command ───────────────────────────────────────────────────────────

def test_run_git_command_success(mocker):
    mock_result = mocker.MagicMock()
    mock_result.stdout = "abc123\n"
    mocker.patch("subprocess.run", return_value=mock_result)
    assert compiler.run_git_command(["git", "rev-parse", "HEAD"]) == "abc123"


def test_run_git_command_failure(mocker):
    import subprocess
    mocker.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git", stderr="fatal error"))
    with pytest.raises(SystemExit) as e:
        compiler.run_git_command(["git", "rev-parse", "HEAD"])
    assert e.value.code == 1


# ── get_reproducible_repo_hash ────────────────────────────────────────────────

def _make_popen_mocks(mocker, archive_rc=0, digest_rc=0, b64_rc=0, b64_out="abc123base64hash"):
    archive_mock = mocker.MagicMock()
    archive_mock.returncode = archive_rc
    digest_mock = mocker.MagicMock()
    digest_mock.returncode = digest_rc
    b64_mock = mocker.MagicMock()
    b64_mock.communicate.return_value = (b64_out, "")
    b64_mock.returncode = b64_rc
    mocker.patch("subprocess.Popen", side_effect=[archive_mock, digest_mock, b64_mock])
    return archive_mock, digest_mock, b64_mock


def test_get_reproducible_repo_hash_success(mocker):
    _make_popen_mocks(mocker, b64_out="abc123base64hash")
    assert compiler.get_reproducible_repo_hash("deadbeef") == "abc123base64hash"


def test_get_reproducible_repo_hash_archive_failure(mocker):
    _make_popen_mocks(mocker, archive_rc=1, b64_out="")
    with pytest.raises(SystemExit) as e:
        compiler.get_reproducible_repo_hash("deadbeef")
    assert e.value.code == 1


def test_get_reproducible_repo_hash_digest_failure(mocker):
    _make_popen_mocks(mocker, digest_rc=1, b64_out="")
    with pytest.raises(SystemExit) as e:
        compiler.get_reproducible_repo_hash("deadbeef")
    assert e.value.code == 1


# ── validate_release_prerequisites — valid increment paths ───────────────────

def test_validate_release_valid_patch_increment(mocker):
    mocker.patch("tools.compiler.load_project_config", return_value=make_project_config())
    def git_cmd(cmd):
        if "status" in cmd: return ""
        if "rev-parse" in cmd: return "primitives/releases/v0.1.2"
        if "tag" in cmd: return "primitives/@v0.1.1"
        return ""
    mocker.patch("tools.compiler.run_git_command", side_effect=git_cmd)
    version, component = compiler.validate_release_prerequisites()
    assert version == "0.1.2"


def test_validate_release_valid_minor_increment(mocker):
    mocker.patch("tools.compiler.load_project_config", return_value=make_project_config())
    def git_cmd(cmd):
        if "status" in cmd: return ""
        if "rev-parse" in cmd: return "primitives/releases/v0.2.0"
        if "tag" in cmd: return "primitives/@v0.1.3"
        return ""
    mocker.patch("tools.compiler.run_git_command", side_effect=git_cmd)
    version, _ = compiler.validate_release_prerequisites()
    assert version == "0.2.0"


def test_validate_release_valid_major_increment(mocker):
    mocker.patch("tools.compiler.load_project_config", return_value=make_project_config())
    def git_cmd(cmd):
        if "status" in cmd: return ""
        if "rev-parse" in cmd: return "primitives/releases/v1.0.0"
        if "tag" in cmd: return "primitives/@v0.9.9"
        return ""
    mocker.patch("tools.compiler.run_git_command", side_effect=git_cmd)
    version, _ = compiler.validate_release_prerequisites()
    assert version == "1.0.0"


# ── _vault_sign ───────────────────────────────────────────────────────────────

def test_vault_sign_success(mocker):
    mock_resp = mocker.MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": {"signature": "vault:v1:ecdsa-sig"}}
    mocker.patch("requests.post", return_value=mock_resp)
    result = compiler._vault_sign("hash64", "https://vault", "token", "key", False)
    assert result == "vault:v1:ecdsa-sig"


def test_vault_sign_failure(mocker):
    mock_resp = mocker.MagicMock()
    mock_resp.status_code = 403
    mock_resp.text = "permission denied"
    mocker.patch("requests.post", return_value=mock_resp)
    with pytest.raises(SystemExit) as e:
        compiler._vault_sign("hash64", "https://vault", "token", "key", False)
    assert e.value.code == 1


# ── _vault_get_cert ───────────────────────────────────────────────────────────

def test_vault_get_cert_success(mocker):
    mock_resp = mocker.MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": {"data": {"pem": "-----BEGIN CERTIFICATE-----"}}}
    mocker.patch("requests.get", return_value=mock_resp)
    result = compiler._vault_get_cert("https://vault", "token", "secret/cic-cert/pem", False)
    assert result == "-----BEGIN CERTIFICATE-----"


def test_vault_get_cert_invalid_path_format(mocker):
    with pytest.raises(SystemExit) as e:
        compiler._vault_get_cert("https://vault", "token", "bad-path", False)
    assert e.value.code == 1


def test_vault_get_cert_failure(mocker):
    mock_resp = mocker.MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = "not found"
    mocker.patch("requests.get", return_value=mock_resp)
    with pytest.raises(SystemExit) as e:
        compiler._vault_get_cert("https://vault", "token", "secret/cic-cert/pem", False)
    assert e.value.code == 1


# ── run_primitive_validation — None instance ─────────────────────────────────

def test_run_primitive_validation_none_instance(mocker):
    mocker.patch.object(compiler, "CONFIG", {"primitive_schema_file": "schemas/index.yaml", "source_dir": "schemas"})
    mocker.patch("glob.glob", return_value=["schemas/atomic/empty.yaml"])
    mocker.patch("os.path.getsize", return_value=10)
    mocker.patch("tools.compiler.load_yaml", side_effect=[
        {"spec": {"type": "object"}},
        None,
    ])
    compiler.run_primitive_validation()


# ── run_domain_compatibility_check — edge paths ──────────────────────────────

def test_domain_check_skips_when_no_config(mocker):
    mocker.patch.object(compiler, "CONFIG", {})
    compiler.run_domain_compatibility_check()


def test_domain_check_no_base_ref(mocker, tmp_path, capsys):
    domain_file = tmp_path / "domain.yaml"
    domain_file.write_text(yaml.dump({
        "spec": {"kind": "DomainComposition", "base": {}}
    }))
    mocker.patch.object(compiler, "CONFIG", {"primitive_schema_file": "schemas/index.yaml", "source_dir": str(tmp_path)})
    mocker.patch("glob.glob", return_value=[str(domain_file)])
    compiler.run_domain_compatibility_check()
    out = capsys.readouterr().out
    assert "WARNING" in out


def test_domain_check_exception_in_load(mocker, tmp_path):
    domain_file = tmp_path / "domain.yaml"
    domain_file.write_text(yaml.dump({
        "spec": {"kind": "DomainComposition", "base": {"ref": "nonexistent.yaml"}}
    }))
    mocker.patch.object(compiler, "CONFIG", {"primitive_schema_file": "schemas/index.yaml", "source_dir": str(tmp_path)})
    mocker.patch("glob.glob", return_value=[str(domain_file)])

    original_load = compiler.load_yaml
    call_count = [0]
    def patched_load(path):
        call_count[0] += 1
        if call_count[0] == 1:
            return original_load(path)
        raise IOError("file not found")
    mocker.patch("tools.compiler.load_yaml", side_effect=patched_load)

    with pytest.raises(SystemExit) as e:
        compiler.run_domain_compatibility_check()
    assert e.value.code == 1


# ── run_release — happy path ──────────────────────────────────────────────────

def test_run_release_happy_path(mocker, tmp_path):
    schema_file = tmp_path / "shape.yaml"
    schema_file.write_bytes(b"kind: AtomicPrimitive\nspec: {}\n")

    mocker.patch("tools.compiler.validate_release_prerequisites", return_value=("0.1.4", "primitives/"))
    mocker.patch("tools.compiler.run_validation")
    mocker.patch("tools.compiler.run_primitive_validation")
    mocker.patch("tools.compiler.run_domain_compatibility_check")
    mocker.patch.dict(os.environ, {"VAULT_ADDR": "https://v", "VAULT_TOKEN": "tok", "VAULT_CERT": "CERT"}, clear=False)
    mocker.patch.object(compiler, "CONFIG", {"source_dir": str(tmp_path), "vault_key_name": "key"})
    mocker.patch("tools.compiler._vault_sign", return_value="vault:v1:sig")
    mocker.patch("tools.compiler.load_project_config", return_value={"project": {"name": "cic-primitives"}})
    mocker.patch("os.makedirs")

    written = {}
    mocker.patch("tools.compiler.write_yaml", side_effect=lambda p, d: written.update({"path": p, "data": d}))

    compiler.run_release()

    assert "cic-primitives-v0.1.4.yaml" in written["path"]
    bundle = written["data"]
    assert bundle["kind"] == "PrimitiveRelease"
    assert bundle["version"] == "0.1.4"
    assert len(bundle["specs"]) == 1
    assert bundle["specs"][0]["id"] == "shape"
    assert bundle["release"]["sign"] == "vault:v1:sig"
    assert bundle["release"]["cert"] == "CERT"


def test_run_release_with_vault_cert_path(mocker, tmp_path):
    schema_file = tmp_path / "role.yaml"
    schema_file.write_bytes(b"kind: AtomicPrimitive\n")

    mocker.patch("tools.compiler.validate_release_prerequisites", return_value=("0.1.5", "primitives/"))
    mocker.patch("tools.compiler.run_validation")
    mocker.patch("tools.compiler.run_primitive_validation")
    mocker.patch("tools.compiler.run_domain_compatibility_check")
    mocker.patch.dict(os.environ, {
        "VAULT_ADDR": "https://v", "VAULT_TOKEN": "tok",
        "VAULT_CERT_PATH": "secret/cic/pem",
    }, clear=False)
    mocker.patch.object(compiler, "CONFIG", {"source_dir": str(tmp_path), "vault_key_name": "key"})
    mocker.patch("tools.compiler._vault_sign", return_value="vault:v1:sig")
    mocker.patch("tools.compiler._vault_get_cert", return_value="PEM_CERT")
    mocker.patch("tools.compiler.load_project_config", return_value={"project": {"name": "cic-primitives"}})
    mocker.patch("os.makedirs")

    written = {}
    mocker.patch("tools.compiler.write_yaml", side_effect=lambda p, d: written.update({"path": p, "data": d}))

    compiler.run_release()
    assert written["data"]["release"]["cert"] == "PEM_CERT"


# ── mutation-targeted tests ───────────────────────────────────────────────────

def test_validate_release_skips_double_major_bump(mocker):
    """Kill mutant 120: v2.0.0 from v0.9.9 is NOT valid (correct next major is v1.0.0)."""
    mocker.patch("tools.compiler.load_project_config", return_value=make_project_config())
    def git_cmd(cmd):
        if "status" in cmd: return ""
        if "rev-parse" in cmd: return "primitives/releases/v2.0.0"
        if "tag" in cmd: return "primitives/@v0.9.9"
        return ""
    mocker.patch("tools.compiler.run_git_command", side_effect=git_cmd)
    with pytest.raises(SystemExit) as e:
        compiler.validate_release_prerequisites()
    assert e.value.code == 1


def test_run_release_vault_token_missing_exits(mocker, monkeypatch):
    """Kill mutant 194: missing VAULT_TOKEN alone must trigger sys.exit(1)."""
    mocker.patch("tools.compiler.validate_release_prerequisites", return_value=("0.1.4", "primitives/"))
    monkeypatch.setenv("VAULT_ADDR", "https://vault")
    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    with pytest.raises(SystemExit) as e:
        compiler.run_release()
    assert e.value.code == 1


def test_run_release_vault_addr_missing_exits(mocker, monkeypatch):
    """Kill mutant 194: missing VAULT_ADDR alone must trigger sys.exit(1)."""
    mocker.patch("tools.compiler.validate_release_prerequisites", return_value=("0.1.4", "primitives/"))
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    monkeypatch.setenv("VAULT_TOKEN", "tok")
    with pytest.raises(SystemExit) as e:
        compiler.run_release()
    assert e.value.code == 1


def test_run_release_no_cacert_tls_disabled(mocker, monkeypatch, tmp_path, capsys):
    """Kill mutants 189+191: no VAULT_CACERT → verify=False AND TLS disabled warning printed."""
    schema_file = tmp_path / "shape.yaml"
    schema_file.write_bytes(b"kind: AtomicPrimitive\n")

    mocker.patch("tools.compiler.validate_release_prerequisites", return_value=("0.1.4", "primitives/"))
    mocker.patch("tools.compiler.run_validation")
    mocker.patch("tools.compiler.run_primitive_validation")
    mocker.patch("tools.compiler.run_domain_compatibility_check")

    monkeypatch.setenv("VAULT_ADDR", "https://vault")
    monkeypatch.setenv("VAULT_TOKEN", "tok")
    monkeypatch.setenv("VAULT_CERT", "CERT")
    monkeypatch.delenv("VAULT_CACERT", raising=False)

    mocker.patch.object(compiler, "CONFIG", {"source_dir": str(tmp_path), "vault_key_name": "key"})
    mock_sign = mocker.patch("tools.compiler._vault_sign", return_value="vault:v1:sig")
    mocker.patch("tools.compiler.load_project_config", return_value={"project": {"name": "cic-primitives"}})
    mocker.patch("os.makedirs")
    mocker.patch("tools.compiler.write_yaml")

    compiler.run_release()

    assert mock_sign.call_args[0][4] is False
    out = capsys.readouterr().out
    assert "TLS verification is disabled" in out


def test_run_release_vault_cert_env_no_warning(mocker, monkeypatch, tmp_path, capsys):
    """Kill mutant 241: when VAULT_CERT is set, no 'Neither...set' warning must appear."""
    schema_file = tmp_path / "shape.yaml"
    schema_file.write_bytes(b"kind: AtomicPrimitive\n")

    mocker.patch("tools.compiler.validate_release_prerequisites", return_value=("0.1.4", "primitives/"))
    mocker.patch("tools.compiler.run_validation")
    mocker.patch("tools.compiler.run_primitive_validation")
    mocker.patch("tools.compiler.run_domain_compatibility_check")

    monkeypatch.setenv("VAULT_ADDR", "https://vault")
    monkeypatch.setenv("VAULT_TOKEN", "tok")
    monkeypatch.setenv("VAULT_CERT", "MY_CERT")
    monkeypatch.delenv("VAULT_CERT_PATH", raising=False)
    monkeypatch.delenv("VAULT_CACERT", raising=False)

    mocker.patch.object(compiler, "CONFIG", {"source_dir": str(tmp_path), "vault_key_name": "key"})
    mocker.patch("tools.compiler._vault_sign", return_value="vault:v1:sig")
    mocker.patch("tools.compiler.load_project_config", return_value={"project": {"name": "cic-primitives"}})
    mocker.patch("os.makedirs")
    mocker.patch("tools.compiler.write_yaml")

    compiler.run_release()

    out = capsys.readouterr().out
    assert "Neither" not in out


def test_domain_check_continues_after_no_base_ref(mocker, tmp_path):
    """Kill mutant 281: continue (not break) after no base_ref — second domain must still be checked."""
    first_file = tmp_path / "first.yaml"
    first_file.write_text(yaml.dump({
        "spec": {"kind": "DomainComposition", "base": {}}
    }))
    second_file = tmp_path / "second.yaml"
    second_file.write_text(yaml.dump({
        "spec": {
            "kind": "DomainComposition",
            "base": {"ref": str(tmp_path / "managed-entity.yaml")},
            "identity": {},
            "config_surface": {},
            "state_surface": {},
            "lifecycle": {},
        }
    }))
    me_file = tmp_path / "managed-entity.yaml"
    me_file.write_text(yaml.dump(_make_managed_entity()))

    mocker.patch.object(compiler, "CONFIG", {"primitive_schema_file": "schemas/index.yaml", "source_dir": str(tmp_path)})
    mocker.patch("glob.glob", return_value=[str(first_file), str(second_file)])

    with pytest.raises(SystemExit) as e:
        compiler.run_domain_compatibility_check()
    assert e.value.code == 1


def test_run_primitive_validation_excludes_empty_files(mocker):
    """Kill mutant 294: files with size 0 must be excluded and never validated."""
    mocker.patch.object(compiler, "CONFIG", {"primitive_schema_file": "schemas/index.yaml", "source_dir": "schemas"})
    mocker.patch("glob.glob", return_value=["schemas/atomic/empty.yaml", "schemas/atomic/shape.yaml"])
    mocker.patch("os.path.getsize", side_effect=lambda f: 0 if "empty" in f else 100)
    validate_mock = mocker.patch("tools.compiler.validate", return_value=None)
    mocker.patch("tools.compiler.load_yaml", side_effect=[
        {"spec": {"type": "object"}},
        {"metadata": {"name": "Shape"}, "spec": {"kind": "AtomicPrimitive"}},
    ])
    compiler.run_primitive_validation()
    assert validate_mock.call_count == 1


def test_domain_check_non_domain_yaml_not_collected(mocker, tmp_path, capsys):
    """Kill mutant 315: a YAML file that is not DomainComposition must not generate a WARNING."""
    other_file = tmp_path / "other.yaml"
    other_file.write_text(yaml.dump({"kind": "AtomicPrimitive", "spec": {}}))

    mocker.patch.object(compiler, "CONFIG", {"primitive_schema_file": "schemas/index.yaml", "source_dir": str(tmp_path)})
    mocker.patch("glob.glob", return_value=[str(other_file)])

    compiler.run_domain_compatibility_check()

    out = capsys.readouterr().out
    assert "WARNING" not in out


def test_domain_check_continues_after_examples_invalid(mocker, tmp_path):
    """Kill mutant 359: an examples/invalid file must not break the collection loop."""
    invalid_file = str(tmp_path / "examples" / "invalid" / "bad.yaml")
    domain_file = tmp_path / "domain.yaml"
    domain_file.write_text(yaml.dump({
        "spec": {
            "kind": "DomainComposition",
            "base": {"ref": str(tmp_path / "managed-entity.yaml")},
            "identity": {},
            "config_surface": {},
            "state_surface": {},
            "lifecycle": {},
        }
    }))
    me_file = tmp_path / "managed-entity.yaml"
    me_file.write_text(yaml.dump(_make_managed_entity()))

    mocker.patch.object(compiler, "CONFIG", {"primitive_schema_file": "schemas/index.yaml", "source_dir": str(tmp_path)})
    mocker.patch("glob.glob", return_value=[invalid_file, str(domain_file)])

    with pytest.raises(SystemExit) as e:
        compiler.run_domain_compatibility_check()
    assert e.value.code == 1


def test_verify_release_nonexistent_source_path_no_crash(mocker, tmp_path):
    """Kill mutant 415: source_path pointing to a missing file must not crash (and is skipped)."""
    specs = [{"id": "shape", "source_path": "/nonexistent/path/shape.yaml",
              "meta_hash": "abc", "spec": {"kind": "AtomicPrimitive"}}]
    content_hash = compiler.get_sha256_b64(compiler.to_canonical_json(specs))
    bundle = {
        "kind": "PrimitiveRelease",
        "version": "0.1.0",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "specs": specs,
        "release": {"content_hash": content_hash, "sign": "sig", "cert": "cert"},
    }
    p = tmp_path / "bundle.yaml"
    p.write_text(yaml.dump(bundle))
    mocker.patch("os.path.isfile", side_effect=lambda path: str(path) == str(p))
    mocker.patch("tools.compiler.load_yaml", return_value=bundle)

    compiler.run_verify_release(str(p))


# ── verify-release — schema validation failure ────────────────────────────────

def test_verify_release_schema_validation_failure(mocker, tmp_path):
    bad_bundle = {"kind": "PrimitiveRelease", "version": "0.0.1"}  # hiányos
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.dump(bad_bundle))
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("tools.compiler.load_yaml", side_effect=[
        bad_bundle,
        {"type": "object", "required": ["specs"], "properties": {"specs": {"type": "array"}}},
    ])
    with pytest.raises(SystemExit) as e:
        compiler.run_verify_release(str(p))
    assert e.value.code == 1
