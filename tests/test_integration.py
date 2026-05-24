import os
import glob
import yaml
import pytest
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
