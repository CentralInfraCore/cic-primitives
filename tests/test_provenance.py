"""Tests for the provenance checker.

It had none. A gate whose own behaviour is unverified is the thing this
repository keeps discovering the hard way — this checker already shipped one
fail-open (a required dependency that was not declared at all came out green),
and nothing would have caught a second.

Everything here runs offline: the network paths are exercised through the
`--offline` contract, and the enforcement logic is tested without fetching, so
the suite stays deterministic and runnable in CI without credentials.
"""

import textwrap

import pytest
import yaml

from tools import check_provenance as prov


def _write(tmp_path, doc):
    path = tmp_path / "dependency.yaml"
    path.write_text(yaml.dump(doc, sort_keys=False))
    return path


def test_no_declared_paths_is_not_a_failure(tmp_path):
    """A repository that vendors nothing has nothing to verify."""
    path = _write(tmp_path, {"schema_version": "1", "dependencies": [
        {"name": "base-repo", "source": "github.com/x/y", "tag": "v1"},
    ]})
    status, results = prov.check(path, offline=True, required=None)
    assert status == 0
    assert results == []


def test_required_dependency_that_is_not_declared_fails(tmp_path):
    """The fail-open this checker shipped with.

    Five repositories carried cic-primitives' atoms while declaring no origin
    for them, and `--require cic-primitives` reported success on every one,
    because it only enforced what it happened to find.
    """
    path = _write(tmp_path, {"schema_version": "1", "dependencies": [
        {"name": "base-repo", "source": "github.com/x/y", "tag": "v1",
         "imported_paths": ["tools/"]},
    ]})
    status, results = prov.check(path, offline=True, required={"cic-primitives"})
    assert status != 0
    missing = [r for r in results if r.dep == "cic-primitives"]
    assert missing and "does not declare it at all" in missing[0].error


def test_required_dependency_declared_without_paths_fails(tmp_path):
    """Declared but claiming nothing: there is no claim to check."""
    path = _write(tmp_path, {"schema_version": "1", "dependencies": [
        {"name": "cic-primitives", "source": "github.com/x/y", "tag": "v1",
         "imported_paths": []},
    ]})
    status, results = prov.check(path, offline=True, required={"cic-primitives"})
    assert status != 0
    assert any("no imported_paths" in (r.error or "") for r in results)


def test_offline_reports_unverified_and_does_not_pass(tmp_path):
    """Silence is not success: offline must not look like a clean result."""
    path = _write(tmp_path, {"schema_version": "1", "dependencies": [
        {"name": "cic-primitives", "source": "github.com/x/y", "tag": "v1",
         "imported_paths": ["schemas/atomic/"]},
    ]})
    status, results = prov.check(path, offline=True, required=None)
    assert status == 2
    assert all("UNVERIFIED" in (r.error or "") for r in results)


def test_only_required_dependencies_decide_the_exit_code(tmp_path):
    """base-repo seeds paths every repo must customise; enforcing it is wrong."""
    path = _write(tmp_path, {"schema_version": "1", "dependencies": [
        {"name": "base-repo", "source": "github.com/x/y", "tag": "v1",
         "imported_paths": ["Makefile"]},
        {"name": "cic-primitives", "source": "github.com/x/z", "tag": "v1",
         "imported_paths": ["schemas/atomic/"]},
    ]})
    status, results = prov.check(path, offline=True, required={"cic-primitives"})
    enforced = {r.dep: r.enforced for r in results}
    assert enforced["base-repo"] is False
    assert enforced["cic-primitives"] is True
    assert status == 2  # offline, and the required one is unverifiable


def test_comparison_reports_differs_missing_and_extra(tmp_path):
    """The core comparison, without touching the network."""
    local = tmp_path / "local"
    upstream = tmp_path / "up"
    for root in (local, upstream):
        (root / "schemas" / "atomic").mkdir(parents=True)
    (upstream / "schemas" / "atomic" / "same.yaml").write_text("a: 1\n")
    (local / "schemas" / "atomic" / "same.yaml").write_text("a: 1\n")
    (upstream / "schemas" / "atomic" / "changed.yaml").write_text("b: 1\n")
    (local / "schemas" / "atomic" / "changed.yaml").write_text("b: 2\n")
    (upstream / "schemas" / "atomic" / "gone.yaml").write_text("c: 1\n")
    (local / "schemas" / "atomic" / "added.yaml").write_text("d: 1\n")

    res = prov.Result("cic-primitives")
    prov.compare(local, upstream, ["schemas/atomic/"], res)

    assert res.differs == ["schemas/atomic/changed.yaml"]
    assert res.missing == ["schemas/atomic/gone.yaml"]
    assert res.extra == ["schemas/atomic/added.yaml"]
    # `extra` alone must not fail: remote-merge seeds a path, it does not freeze it.
    assert res.failed  # because `differs` and `missing` are present

    clean = prov.Result("cic-primitives")
    prov.compare(local, local, ["schemas/atomic/"], clean)
    assert not clean.failed


def test_clone_url_forms():
    assert prov.clone_url("github.com/a/b") == "https://github.com/a/b.git"
    assert prov.clone_url("https://github.com/a/b") == "https://github.com/a/b"
    assert prov.clone_url("git@github.com:a/b.git") == "git@github.com:a/b.git"


def test_unreadable_dependency_file_is_an_error(tmp_path):
    path = tmp_path / "dependency.yaml"
    path.write_text("a: [unclosed\n")
    status, results = prov.check(path, offline=True, required=None)
    assert status == 2
