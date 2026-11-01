"""Planted-defect proof for the compiler's envelope 3 output: small breaks in tools/compiler.py (tests/e3_compiler_mutants.py) are run against
tests/test_compiler_envelope3.py in a subprocess; a break meant to be caught has to turn one of the tests that target it red (a break that fails only an unrelated test
does not count, and one that is not valid Python is refused before it is run), and the breaks that cannot change behaviour are listed with the reason and have to survive.
"""
import concurrent.futures
import os
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import e3_compiler_mutants as mutants  # noqa: E402
import e3_fixtures as fx  # noqa: E402

SOURCE = fx.ROOT / "tools" / "compiler.py"


def run_mutant(mutant, tmp):
    mutated = SOURCE.read_text(encoding="utf-8")
    for old, new in mutant["edits"]:
        assert mutated.count(old) == 1, "%s: the planted text occurs %d times: %r" % (mutant["id"], mutated.count(old), old[:60])
        mutated = mutated.replace(old, new)
    compile(mutated, mutant["id"], "exec")
    path = pathlib.Path(tmp) / ("c_%s.py" % mutant["id"])
    path.write_text(mutated, encoding="utf-8")
    env = dict(os.environ, E3_COMPILER=str(path), PYTHONDONTWRITEBYTECODE="1")
    select = ["-k", " or ".join(mutant["kills"])] if mutant["kills"] else []
    done = subprocess.run([sys.executable, "-m", "pytest", str(fx.ROOT / "tests" / "test_compiler_envelope3.py"), "-q", "--tb=no", "-rf", "-p", "no:cacheprovider"] + select,
                          capture_output=True, text=True, env=env, cwd=str(fx.ROOT))
    failed = [line for line in done.stdout.splitlines() if line.startswith("FAILED")]
    assert done.returncode != 5 and "no tests ran" not in done.stdout, "%s: the targeted tests %s do not exist" % (mutant["id"], mutant["kills"])
    return done.returncode, failed


@pytest.fixture(scope="module")
def results(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("compiler_mutants")
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {m["id"]: pool.submit(run_mutant, m, tmp) for m in mutants.MUTANTS}
        return {k: f.result() for k, f in futures.items()}


def test_mutant_ids_are_unique():
    ids = [m["id"] for m in mutants.MUTANTS]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("mutant", [m for m in mutants.MUTANTS if not m["equivalent"]], ids=lambda m: m["id"])
def test_a_planted_defect_in_the_compiler_turns_the_targeted_test_red(mutant, results):
    code, failed = results[mutant["id"]]
    assert code != 0, "the planted defect %s was not detected by any test" % mutant["id"]
    assert any(any(k in line for k in mutant["kills"]) for line in failed), "%s: failed %s, none of the targeted %s" % (mutant["id"], failed[:4], mutant["kills"])


@pytest.mark.parametrize("mutant", [m for m in mutants.MUTANTS if m["equivalent"]], ids=lambda m: m["id"])
def test_an_equivalent_mutant_of_the_compiler_survives_and_says_why(mutant, results):
    code, failed = results[mutant["id"]]
    assert len(mutant["equivalent"]) > 30
    assert code == 0, "%s is documented as equivalent but %s" % (mutant["id"], failed[:3])
