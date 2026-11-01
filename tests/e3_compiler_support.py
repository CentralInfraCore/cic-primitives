"""Support for the tests of the compiler's envelope 3 output (tests/test_compiler_envelope3.py).

The compiler is loaded through `load_compiler`, which the planted-defect runs point (E3_COMPILER) at a mutated copy. Everything the vectors expect comes from the frozen
fixtures (tests/e3_fixtures.py, tests/e3_vectors.py, tests/fixtures/envelope3), which the compiler change does not touch (tests/test_conformance_frozen.py).
"""
import datetime
import importlib.util
import os
import pathlib
import subprocess
import types

import yaml

import e3_fixtures as fx

ROOT = fx.ROOT
FIXED_NOW = datetime.datetime(2026, 11, 1, 12, 0, 0)


def load_compiler():
    override = os.environ.get("E3_COMPILER")
    if override:
        spec = importlib.util.spec_from_file_location("compiler_under_test", override)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    from tools import compiler
    return compiler


class _FixedDatetime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(FIXED_NOW.year, FIXED_NOW.month, FIXED_NOW.day, FIXED_NOW.hour, tzinfo=tz or datetime.timezone.utc)


def fix_the_clock(monkeypatch, module):
    """The compiler reads the clock for the release timestamp and for certificate and commitment dates; a historical record is checked as of a day it was valid."""
    monkeypatch.setattr(module, "datetime", types.SimpleNamespace(
        datetime=_FixedDatetime, date=datetime.date, timezone=datetime.timezone, timedelta=datetime.timedelta))


def project_yaml(paths):
    return yaml.dump({"project": {"name": "cic-primitives", "owner": "Dev"},
                      "compiler_settings": {"release_artifacts": {"paths": list(paths)}}}, sort_keys=False)


def checkout(path, files):
    """A repository at `path` whose HEAD is one commit holding `files` [(path, bytes, mode)], and whose working directory holds the same files."""
    commit = fx.build_repo(path, files)
    fx._git(path, "update-ref", "refs/heads/main", commit)
    fx._git(path, "symbolic-ref", "HEAD", "refs/heads/main")
    for name, content, mode in files:
        if mode in ("100644", "100755"):
            target = pathlib.Path(path) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    return commit


def golden_paths():
    return [p for p, _c, _m in fx.GOLDEN_FILES]


def commit_files(paths):
    """The golden files plus the project.yaml that declares `paths`."""
    return list(fx.GOLDEN_FILES) + [("project.yaml", project_yaml(paths).encode("utf-8"), "100644")]


def release_sandbox(C, tmp_path, monkeypatch, version="0.1.6", files=None, paths=None):
    """What tests/test_compiler.py::_release_sandbox did, as a real git checkout: run_release() resolves the artifacts from the git tree of HEAD, so the sandbox has one.

    Vault and the developer commitment are replaced; the issuer is the test issuer of the frozen fixtures, so a record this compiler writes can be re-authenticated by the
    same test keys as the golden record. Returns (directory, version, source_commit, calls) where `calls` counts the Vault calls.
    """
    import test_compiler as tc
    paths = golden_paths() if paths is None else paths
    files = commit_files(paths) if files is None else files
    commit = checkout(tmp_path, files)
    repo = ROOT
    (tmp_path / "proposals").mkdir(exist_ok=True)
    (tmp_path / "proposals" / "atom-grammar").symlink_to(repo / "proposals" / "atom-grammar", target_is_directory=True)
    (tmp_path / "schemas" / "atomic").mkdir(parents=True)
    (tmp_path / "schemas" / "atomic" / "shape.yaml").write_text(tc._META.format(name="Shape", version="v0.1.dev") + "spec:\n  kind: AtomicPrimitive\n  fields: {a: 1}\n")
    (tmp_path / "schemas" / "examples").mkdir()
    (tmp_path / "schemas" / "examples" / "c.yaml").write_text(tc._META.format(name="Example", version="v0.1.dev") + tc._GOOD_COMPOSITION.lstrip("\n"))
    (tmp_path / "dependency.yaml").write_text("schema_version: '1'\n")
    (tmp_path / "md.meta.schema.yaml").write_text((repo / "md.meta.schema.yaml").read_text())
    (tmp_path / "schemas" / "index.yaml").write_text((repo / "schemas" / "index.yaml").read_text())
    monkeypatch.chdir(tmp_path)

    calls = {"vault": 0}
    issuer_cert = fx.certificate("issuer", "root", 12)
    developer_cert = fx.certificate("developer", "root", 11)
    validity = {"from": str(FIXED_NOW.date()), "until": "2099-01-01"}
    commitment = {"kind": "DeveloperCommitment", "validity": validity,
                  "createdBy": {"name": "Dev", "email": "d@e", "certificate": developer_cert}}

    def vault_cert(*a, **k):
        calls["vault"] += 1
        return issuer_cert

    def vault_sign(digest, *a, **k):
        calls["vault"] += 1
        return fx.vault_signature("issuer", digest)

    settings = dict(tc._RELEASE_SETTINGS)
    monkeypatch.setenv("VAULT_ADDR", "https://vault")
    monkeypatch.setenv("VAULT_TOKEN", "token")
    monkeypatch.setattr(C, "validate_release_prerequisites", lambda: (version, "primitives/"))
    monkeypatch.setattr(C, "_load_valid_commitment", lambda require_signature=True: commitment)
    monkeypatch.setattr(C, "_vault_get_cert", vault_cert)
    monkeypatch.setattr(C, "_vault_sign", vault_sign)
    # the settings of the WORKING DIRECTORY'S project.yaml: deliberately without the declaration, which has to come from the commit
    monkeypatch.setattr(C, "load_project_config", lambda full_config=False: (
        {"project": {"name": "cic-primitives", "owner": "Dev"}, "compiler_settings": settings} if full_config else settings))
    monkeypatch.setattr(C, "CONFIG", settings)
    return tmp_path, version, commit, calls


def written_record(directory, version):
    return yaml.safe_load((pathlib.Path(directory) / "release" / ("cic-primitives-v%s.yaml" % version)).read_text(encoding="utf-8"))


def countersign(bundle):
    """What the external service does: sign the build_hash it is given, with its own key, and return the block (tests only; the service is not touched)."""
    bundle["cic_countersign"] = {
        "authority": {"name": "Conformance Fixture Authority", "certificate": fx.certificate("authority", "root", 13),
                      "root_certificate": fx.certificate("root", "root", 10, ca=True)},
        "signed_payload": "build_hash",
        "sign": fx.vault_signature("authority", bundle["release"]["build_hash"]),
    }
    return bundle


def git_tree_via_plumbing(repo, commit):
    """An independent reading of the tree, for the comparison with the compiler's own listing."""
    out = subprocess.run(["git", "-C", str(repo), "ls-tree", "-r", "-t", "-z", "--full-tree", commit], capture_output=True, check=True).stdout
    tree = {}
    for record in out.split(b"\0"):
        if record:
            meta, _t, name = record.partition(b"\t")
            mode, kind, oid = meta.decode().split(" ")
            tree[name.decode("utf-8", "surrogateescape")] = (mode, kind, oid)
    return tree
