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
