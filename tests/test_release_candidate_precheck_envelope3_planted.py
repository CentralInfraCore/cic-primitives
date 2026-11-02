"""Planted-defect proof of tests/test_release_candidate_precheck_envelope3.py: a test that cannot fail proves nothing.

Each mutant is a copy of tools/release_candidate_precheck.py with ONE defect planted (a check weakened, a branch crossed, a gate turned into a pass). The envelope 3 tests are
run against it in a subprocess (PRECHECK_TOOL) and MUST fail. Every mutant is compiled first, so a mutant that dies of a syntax error is not counted as killed. The unmutated copy
is run too and must pass, so that a failure is the defect and not the harness.
"""
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
TOOL = REPO / "tools" / "release_candidate_precheck.py"
SUITE = REPO / "tests" / "test_release_candidate_precheck_envelope3.py"

# (name, [(old, new), ...]): every `old` occurs exactly once in the tool
MUTANTS = [
    ("uppercase hex accepted",
     [('ARTIFACT_DIGEST = re.compile(r"sha256:([0-9a-f]{64})")', 'ARTIFACT_DIGEST = re.compile(r"sha256:([0-9a-fA-F]{64})")'), ("return m.group(1)", "return m.group(1).lower()")]),
    ("algorithm prefix optional", [('ARTIFACT_DIGEST = re.compile(r"sha256:([0-9a-f]{64})")', 'ARTIFACT_DIGEST = re.compile(r"(?:sha256:)?([0-9a-f]{64})")')]),
    ("prefix match instead of the whole string", [("ARTIFACT_DIGEST.fullmatch(value)", "ARTIFACT_DIGEST.match(value)")]),
    ("a path listed twice takes its first digest", [("digests[0] if len(digests) == 1 else None", "digests[0]")]),
    ("envelope 3 reads the places of the earlier envelopes", [("digested = artifact_digests(report, rec)\n        if digested is None:", "digested = legacy_digests(rec, prov)\n        if digested is None:")]),
    ("an earlier envelope also reads the artifacts", [("digested = legacy_digests(rec, prov)\n    else:", "digested = artifact_digests(report, rec) or legacy_digests(rec, prov)\n    else:")]),
    ("an unknown envelope is read as an earlier one", [("elif envelope is None or (type(envelope) is int and envelope in LEGACY_ENVELOPES):", "elif True:")]),
    ("envelope 3.0 is read as 3", [("if type(envelope) is int and envelope == ENVELOPE_WITH_ARTIFACTS:", "if envelope == ENVELOPE_WITH_ARTIFACTS:")]),
    ("envelope true is read as 1", [("(type(envelope) is int and envelope in LEGACY_ENVELOPES)", "(envelope in LEGACY_ENVELOPES)")]),
    ("the digest comparison always agrees", [("same = decode(value) == hexsha", "same = True")]),
    ("a declaration that leaves a pinned file out is accepted", [("not in set(paths)]\n    if missing:\n", "not in set(paths)]\n    if False:\n")]),
    ("no declaration counts as a declared head", [('release_artifacts): an earlier record can digest at most 6 of the 12")\n        return False', 'release_artifacts): an earlier record can digest at most 6 of the 12")\n        return True')]),
    ("the declaration is not checked to be a list of paths", [("    if not isinstance(paths, list) or not all(isinstance(x, str) for x in paths):", "    if False:")]),
    ("a differently spelled path counts as the pinned one", [('f["path"] not in set(paths)', 'f["path"] not in set(p.lstrip("./") for p in paths)')]),
    ("the record coverage gate becomes a pass once the head declares", [('report.add(OPEN, "record digest coverage", "the declaration only says', 'report.add(PASS, "record digest coverage", "the declaration only says')]),
    ("the declaration is read at the pinned commit, not at the release head", [('blob(repo, head, "project.yaml")', 'blob(repo, pin["commit"], "project.yaml")')]),
    ("the candidate ignores that the head declares", [("gates(report, args.release_date, declared=declared)", "gates(report, args.release_date, declared=False)")]),
    ("the record mode ignores that the record is envelope 3", [("declared=envelope == ENVELOPE_WITH_ARTIFACTS)", "declared=False)")]),
]


def run_suite(tool_path):
    env = {"PRECHECK_TOOL": str(tool_path), "PATH": "/usr/bin:/bin:/usr/local/bin"}
    return subprocess.run([sys.executable, "-m", "pytest", str(SUITE), "-x", "-q", "-p", "no:cacheprovider"], cwd=REPO, env=env, capture_output=True, text=True, check=False)


def test_the_unmutated_copy_passes_the_suite(tmp_path):
    copy = tmp_path / "release_candidate_precheck.py"
    copy.write_text(TOOL.read_text(encoding="utf-8"), encoding="utf-8")
    result = run_suite(copy)
    assert result.returncode == 0, result.stdout[-3000:]


@pytest.mark.parametrize("name, changes", MUTANTS, ids=[m[0] for m in MUTANTS])
def test_a_planted_defect_fails_the_suite(tmp_path, name, changes):
    text = TOOL.read_text(encoding="utf-8")
    for old, new in changes:
        assert text.count(old) == 1, f"the text to mutate occurs {text.count(old)} times: {old[:70]!r}"
        text = text.replace(old, new)
    mutant = tmp_path / "release_candidate_precheck.py"
    mutant.write_text(text, encoding="utf-8")
    compile(text, str(mutant), "exec")        # a mutant that does not compile would die for the wrong reason
    result = run_suite(mutant)
    assert result.returncode != 0, f"the planted defect {name!r} SURVIVED: no test noticed it"
    assert "SyntaxError" not in result.stdout + result.stderr, f"{name!r} died of a syntax error"
