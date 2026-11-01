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
    fx._git(path, "read-tree", "HEAD")      # the index, so that `git status` means something in the tests that ask it
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


def sandbox_files(extra=(), without=()):
    """What run_release() reads from the working directory besides the artifacts: the schema files, project.yaml (added by the caller), dependency.yaml, the two
    grammar files of the provenance digests. They are COMMITTED, because the compiler stops when the working directory and the source commit disagree."""
    import test_compiler as tc
    repo = ROOT
    files = [
        ("schemas/atomic/shape.yaml", (tc._META.format(name="Shape", version="v0.1.dev") + "spec:\n  kind: AtomicPrimitive\n  fields: {a: 1}\n").encode(), "100644"),
        ("schemas/examples/c.yaml", (tc._META.format(name="Example", version="v0.1.dev") + tc._GOOD_COMPOSITION.lstrip("\n")).encode(), "100644"),
        ("schemas/index.yaml", (repo / "schemas" / "index.yaml").read_bytes(), "100644"),
        ("md.meta.schema.yaml", (repo / "md.meta.schema.yaml").read_bytes(), "100644"),
        ("dependency.yaml", b"schema_version: '1'\n", "100644"),
        ("commitment.yaml", b"kind: DeveloperCommitment\n", "100644"),     # a placeholder: the signed pledge is replaced by the test, but the file is a required input
        ("proposals/atom-grammar/check_grammar.py", (repo / "proposals/atom-grammar/check_grammar.py").read_bytes(), "100644"),
        ("proposals/atom-grammar/instance-grammar.schema.yaml", (repo / "proposals/atom-grammar/instance-grammar.schema.yaml").read_bytes(), "100644"),
    ]
    return [f for f in files if f[0] not in without] + list(extra)


def spec_paths(extra=()):
    """The schema files the sandbox's release carries as `specs` (the selection of the compiler: under schemas/, not an example, not the index, not hidden, not empty)."""
    paths = ["schemas/atomic/shape.yaml"]
    for name, content, _mode in extra:
        parts = name.split("/")
        if name.startswith("schemas/") and name.endswith(".yaml") and "examples" not in parts and parts[-1] != "index.yaml" and not any(p.startswith(".") for p in parts) and content:
            paths.append(name)
    return paths


def sandbox_paths(extra=()):
    """The default declaration of the sandbox: the golden files and every schema the record publishes (a spec that is not listed is refused)."""
    return golden_paths() + spec_paths(extra)


def expected_artifacts(paths, extra=()):
    """The artifacts block of `paths`, computed here from the committed bytes with the independent implementation (sha256 of the bytes, sha256sum-format manifest)."""
    content = {name: data for name, data, _m in list(fx.GOLDEN_FILES) + sandbox_files(extra)}
    files = [{"path": p, "digest": "sha256:" + fx.sha256_hex(content[p])} for p in sorted(paths, key=lambda p: p.encode("utf-8"))]
    return {"manifest_digest": fx.independent_manifest_digest(files), "files": files}


def release_sandbox(C, tmp_path, monkeypatch, version="0.1.6", files=None, paths=None, extra_files=(), without=(), real_commitment=False):
    """What tests/test_compiler.py::_release_sandbox did, as a real git checkout: run_release() resolves the artifacts from the git tree of HEAD, so the sandbox has one.

    Vault and the developer commitment are replaced; the issuer is the test issuer of the frozen fixtures, so a record this compiler writes can be re-authenticated by the
    same test keys as the golden record. Returns (directory, version, source_commit, calls) where `calls` counts the Vault calls.
    """
    import test_compiler as tc
    paths = sandbox_paths(extra_files) if paths is None else paths
    files = (commit_files(paths) if files is None else list(files)) + sandbox_files(extra_files, without)
    commit = checkout(tmp_path, files)
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
    if not real_commitment:
        monkeypatch.setattr(C, "_load_valid_commitment", lambda require_signature=True: commitment)
    monkeypatch.setattr(C, "_vault_get_cert", vault_cert)
    monkeypatch.setattr(C, "_vault_sign", vault_sign)
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


def porcelain(path):
    """What validate_release_prerequisites asks: `git status --porcelain` (untracked files included, ignored ones not)."""
    return subprocess.run(["git", "-C", str(path), "status", "--porcelain"], capture_output=True, text=True, check=True).stdout
