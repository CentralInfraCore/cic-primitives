import os
import json
import glob
import yaml
import pytest
import tempfile
from jsonschema import validate, ValidationError
from tools import compiler

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INVALID_DIR = os.path.join(REPO_ROOT, "schemas", "examples", "invalid")


@pytest.fixture(autouse=True)
def repo_cwd():
    original = os.getcwd()
    os.chdir(REPO_ROOT)
    yield
    os.chdir(original)


def _load_invalid_docs(filename):
    """Load both YAML documents from an invalid example file."""
    path = os.path.join(INVALID_DIR, filename)
    with open(path) as f:
        docs = list(yaml.safe_load_all(f))
    # First doc: preamble (why_invalid, expected_error)
    # Second doc: the actual invalid schema
    assert len(docs) == 2, f"{filename}: expected 2 YAML documents"
    return docs[0], docs[1]


def test_validate_real_schemas():
    compiler.run_validation()
    compiler.run_primitive_validation()
    compiler.run_domain_compatibility_check()


def test_invalid_missing_required_metadata():
    """missing-required-metadata.yaml must fail primitive schema validation."""
    index = compiler.load_yaml("schemas/index.yaml")
    meta_schema = index["spec"]
    _, schema_doc = _load_invalid_docs("missing-required-metadata.yaml")
    with pytest.raises(ValidationError):
        validate(instance=schema_doc, schema=meta_schema)


def test_invalid_aggregate_slot_mode():
    """aggregate-invalid-slot-mode.yaml must fail primitive schema validation."""
    index = compiler.load_yaml("schemas/index.yaml")
    meta_schema = index["spec"]
    _, schema_doc = _load_invalid_docs("aggregate-invalid-slot-mode.yaml")
    with pytest.raises(ValidationError):
        validate(instance=schema_doc, schema=meta_schema)


def test_invalid_domain_sealed_override():
    """domain-sealed-override.yaml overrides a sealed slot — verify the violation is detected."""
    _, domain = _load_invalid_docs("domain-sealed-override.yaml")
    base = compiler.load_yaml("schemas/aggregate/managed-entity.yaml")
    base_slots = base.get("spec", {}).get("slots", {})
    domain_spec = domain.get("spec", {})
    domain_slot_keys = set(domain_spec.keys()) - {"kind", "base"}

    sealed_violations = [
        name for name, slot_def in base_slots.items()
        if slot_def.get("mode") == "sealed" and name in domain_slot_keys
    ]
    assert sealed_violations, "Expected sealed slot violations but found none"
    assert "lifecycle_surface" in sealed_violations


# ---------------------------------------------------------------------------
# verify-release tesztek
# ---------------------------------------------------------------------------

def _make_bundle(specs, tamper_hash=False, wrong_kind=False):
    """Build a minimal valid PrimitiveRelease bundle dict for testing."""
    content_hash = compiler.get_sha256_b64(compiler.to_canonical_json(specs))
    if tamper_hash:
        content_hash = content_hash[:-4] + "XXXX"
    return {
        "kind": "WrongKind" if wrong_kind else "PrimitiveRelease",
        "version": "0.0.1",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "specs": specs,
        "release": {
            "content_hash": content_hash,
            "sign": "vault:v1:test",
            "cert": "-----BEGIN CERTIFICATE-----\nMIIBtest\n-----END CERTIFICATE-----",
        },
    }


def _write_bundle(bundle):
    """Write a bundle dict to a temp file, return the path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w")
    yaml.dump(bundle, tmp, sort_keys=False)
    tmp.close()
    return tmp.name


def test_verify_release_valid_bundle():
    """A correctly assembled bundle passes verify."""
    specs = [{"id": "shape", "source_path": "schemas/atomic/shape.yaml",
              "meta_hash": "abc=", "spec": {"kind": "AtomicPrimitive"}}]
    path = _write_bundle(_make_bundle(specs))
    try:
        compiler.run_verify_release(path)
    finally:
        os.unlink(path)


def test_verify_release_content_hash_mismatch(capsys):
    """A bundle with a tampered content_hash raises SystemExit."""
    specs = [{"id": "shape", "source_path": "schemas/atomic/shape.yaml",
              "meta_hash": "abc=", "spec": {"kind": "AtomicPrimitive"}}]
    path = _write_bundle(_make_bundle(specs, tamper_hash=True))
    try:
        with pytest.raises(SystemExit):
            compiler.run_verify_release(path)
        out = capsys.readouterr().out
        assert "MISMATCH" in out
    finally:
        os.unlink(path)


def test_verify_release_wrong_kind(capsys):
    """A bundle with wrong kind raises SystemExit."""
    specs = [{"id": "shape", "source_path": "x.yaml",
              "meta_hash": "abc=", "spec": {}}]
    path = _write_bundle(_make_bundle(specs, wrong_kind=True))
    try:
        with pytest.raises(SystemExit):
            compiler.run_verify_release(path)
    finally:
        os.unlink(path)


def test_verify_release_meta_hash_mismatch_warning(capsys):
    """If source file exists but content differs, a warning is printed but verify still passes."""
    source_path = "schemas/atomic/shape.yaml"
    specs = [{"id": "shape", "source_path": source_path,
              "meta_hash": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
              "spec": {"kind": "AtomicPrimitive"}}]
    path = _write_bundle(_make_bundle(specs))
    try:
        compiler.run_verify_release(path)
        out = capsys.readouterr().out
        assert "meta_hash mismatches" in out
    finally:
        os.unlink(path)


def test_release_schema_validates_valid_bundle():
    """A well-formed bundle passes validation against release.schema.yaml."""
    release_schema = compiler.load_yaml("release.schema.yaml")
    specs = [{"id": "shape", "source_path": "schemas/atomic/shape.yaml",
              "meta_hash": "abc=", "spec": {"kind": "AtomicPrimitive"}}]
    bundle = _make_bundle(specs)
    validate(instance=bundle, schema=release_schema)


def test_release_schema_rejects_missing_content_hash():
    """A bundle missing release.content_hash fails release.schema.yaml validation."""
    release_schema = compiler.load_yaml("release.schema.yaml")
    specs = [{"id": "shape", "source_path": "x.yaml",
              "meta_hash": "abc=", "spec": {}}]
    bundle = _make_bundle(specs)
    del bundle["release"]["content_hash"]
    with pytest.raises(ValidationError):
        validate(instance=bundle, schema=release_schema)
