"""Planted-defect proof of tests/test_release_record_conformance_fullmatch.py: put the end anchor `$` back and the vectors have to turn red.

Each mutant is a copy of the verifier with the fix undone at one place. The vector suite is run against it in a subprocess (E3_VERIFIER) and the vectors that target the
place have to be among the failures; the unmutated copy has to pass, so that a failure is the defect and not the harness.
"""
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
SOURCE = REPO / "tools" / "release_record_conformance.py"
SUITE = REPO / "tests" / "test_release_record_conformance_fullmatch.py"

MUTANTS = [
    ("the digest pattern ends with $ again", ('DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}\\Z")', 'DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")'),
     ["digest-trailing-newline", "manifest-digest-trailing-newline"]),
    ("the commit pattern ends with $ again", ('COMMIT_RE = re.compile(r"^[0-9a-f]{40}\\Z")', 'COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")'),
     ["source-commit-trailing-newline"]),
    ("the digest pattern is not anchored at the end", ('DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}\\Z")', 'DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}")'),
     ["digest-trailing-newline", "manifest-digest-trailing-newline"]),
]


def run_suite(verifier):
    env = {"E3_VERIFIER": str(verifier), "PATH": "/usr/bin:/bin:/usr/local/bin"}
    return subprocess.run([sys.executable, "-m", "pytest", str(SUITE), "-q", "-rf", "-p", "no:cacheprovider", "-k", "not d2d8ec7 and not v021"], cwd=REPO, env=env,
                          capture_output=True, text=True, check=False)


def test_the_unmutated_copy_passes_the_suite(tmp_path):
    copy = tmp_path / "release_record_conformance.py"
    copy.write_text(SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
    result = run_suite(copy)
    assert result.returncode == 0, result.stdout[-3000:]


@pytest.mark.parametrize("name, change, targets", MUTANTS, ids=[m[0] for m in MUTANTS])
def test_a_planted_defect_turns_the_targeted_vectors_red(tmp_path, name, change, targets):
    old, new = change
    text = SOURCE.read_text(encoding="utf-8")
    assert text.count(old) == 1, "the text to mutate occurs %d times: %r" % (text.count(old), old)
    text = text.replace(old, new)
    mutant = tmp_path / "release_record_conformance.py"
    mutant.write_text(text, encoding="utf-8")
    compile(text, str(mutant), "exec")        # a mutant that does not compile would die for the wrong reason
    result = run_suite(mutant)
    assert result.returncode != 0, "the planted defect %r SURVIVED" % name
    failed = [line for line in result.stdout.splitlines() if line.startswith("FAILED")]
    for target in targets:
        assert any(target in line for line in failed), "%r: the vector %s did not fail; failures: %s" % (name, target, failed)
