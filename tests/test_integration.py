import os
import pytest
from tools import compiler

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True)
def repo_cwd():
    original = os.getcwd()
    os.chdir(REPO_ROOT)
    yield
    os.chdir(original)


def test_validate_real_schemas():
    compiler.run_validation()
    compiler.run_primitive_validation()
    compiler.run_domain_compatibility_check()
