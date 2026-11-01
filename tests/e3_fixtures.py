"""Fixtures of the envelope 3 conformance vectors (docs/en/RELEASE-RECORD-CONTRACT.md, section 12).

The expected values do not come from the code under test. The artifact digests, the manifest digest, the canonical bytes and the build hash of the golden record are
written down in tests/fixtures/envelope3/golden.expected.json and were recomputed with sha256sum and openssl, not with tools/compiler.py; `independent_*` below is a
second, separate implementation of the same rules, used to re-authenticate mutated records. Keys are test-only and derived from fixed labels, so the committed
certificates and signatures belong to keys that can be re-derived here (no private key file exists); the certificates are valid for a century, so a check of
certificate dates inside the existing signature check never decides a vector.

Nothing here talks to Vault, and nothing here signs anything outside the tests.
"""
import base64
import copy
import datetime
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess

import yaml
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import utils as asym_utils
from cryptography.hazmat.primitives.asymmetric.ec import ECDSA, SECP256R1, derive_private_key
from cryptography.x509.oid import NameOID

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures" / "envelope3"
E_ACUTE = "\N{LATIN SMALL LETTER E WITH ACUTE}"

# the worked example of section 8: file name -> content
GOLDEN_FILES = [
    ("a.txt", b"alpha\n", "100644"),
    ("d/b.txt", b"beta\n", "100644"),
    (E_ACUTE + ".txt", (E_ACUTE + "\n").encode("utf-8"), "100644"),
]
SPECIAL_FILES = [
    ("a.txt", b"alpha-special\n", "100644"),
    ("d/b.txt", b"beta\n", "100644"),
    (E_ACUTE + ".txt", (E_ACUTE + "\n").encode("utf-8"), "100644"),
    ("l", b"a.txt", "120000"),          # a symbolic link
    ("m", "0123456789abcdef0123456789abcdef01234567", "160000"),   # a submodule (a commit object that is not in this repository)
]


def load_verifier():
    """The verifier under test; E3_VERIFIER points at a mutated copy during the planted-defect runs."""
    override = os.environ.get("E3_VERIFIER")
    if override:
        spec = importlib.util.spec_from_file_location("release_record_conformance_under_test", override)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    from tools import release_record_conformance
    return release_record_conformance


# ---------------------------------------------------------------- keys and certificates (test-only, derived)

def _scalar(label):
    n = int("FFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551", 16)
    return int.from_bytes(hashlib.sha256(b"cic-envelope3-conformance-test-key/" + label.encode()).digest(), "big") % (n - 1) + 1


def key(label):
    return derive_private_key(_scalar(label), SECP256R1())


def _name(cn):
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])


def certificate(subject_label, issuer_label, serial, ca=False):
    subject_key, issuer_key = key(subject_label), key(issuer_label)
    builder = (x509.CertificateBuilder()
               .subject_name(_name("TEST ONLY " + subject_label))
               .issuer_name(_name("TEST ONLY " + issuer_label))
               .public_key(subject_key.public_key())
               .serial_number(serial)
               .not_valid_before(datetime.datetime(2026, 1, 1))
               .not_valid_after(datetime.datetime(2125, 12, 31)))
    if ca:
        builder = builder.add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
    return builder.sign(issuer_key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM).decode()


def vault_signature(label, build_hash_b64):
    """`vault:v1:<base64 DER>` over a pre-hashed digest, the format run_verify_release reads."""
    der = key(label).sign(base64.b64decode(build_hash_b64), ECDSA(asym_utils.Prehashed(hashes.SHA256())))
    return "vault:v1:" + base64.b64encode(der).decode()


# ---------------------------------------------------------------- independent implementation of the contract rules

def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def b64_sha256(data):
    return base64.b64encode(hashlib.sha256(data).digest()).decode()


def independent_manifest_digest(files):
    text = "".join("%s  %s\n" % (f["digest"][len("sha256:"):], f["path"]) for f in files)
    return "sha256:" + sha256_hex(text.encode("utf-8"))


def independent_canonical_bytes(bundle):
    """What build_hash covers under envelope 2 and 3: the whole bundle except release.sign, release.build_hash and cic_countersign."""
    payload = json.loads(json.dumps(bundle, sort_keys=True, default=str))
    payload.pop("cic_countersign", None)
    payload["release"].pop("sign", None)
    payload["release"].pop("build_hash", None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def independent_build_hash(bundle):
    return b64_sha256(independent_canonical_bytes(bundle))


def reauthenticate(bundle, how="all"):
    """Recompute build_hash and re-sign, as the test keys allow. how: all | hash_only | hash_sign (not the counter-signature) | hash_countersign (not the signature)."""
    bundle["release"]["build_hash"] = independent_build_hash(bundle)
    if how in ("all", "hash_sign"):
        bundle["release"]["sign"] = vault_signature("issuer", bundle["release"]["build_hash"])
    if how in ("all", "hash_countersign") and "cic_countersign" in bundle:
        bundle["cic_countersign"]["sign"] = vault_signature("authority", bundle["release"]["build_hash"])
    return bundle


# ---------------------------------------------------------------- a git repository built from plumbing only (no hooks, no signing, fixed dates)

def _git(repo, *args, data=None, env_extra=None):
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null", "LC_ALL": "C"}
    env.update(env_extra or {})
    done = subprocess.run(["git", "-C", str(repo)] + list(args), input=data, capture_output=True, env=env, check=True)
    return done.stdout


def _tree(repo, entries):
    """entries: [(name, content, mode)] with '/' nested names; returns the tree id."""
    direct, nested = [], {}
    for name, content, mode in entries:
        head, _slash, rest = name.partition("/")
        if rest:
            nested.setdefault(head, []).append((rest, content, mode))
        else:
            direct.append((head, content, mode))
    lines = []
    for head, content, mode in direct:
        if mode == "160000":
            lines.append(b"160000 commit " + content.encode() + b"\t" + head.encode("utf-8"))
        else:
            oid = _git(repo, "hash-object", "-w", "--stdin", data=content).strip().decode()
            lines.append(mode.encode() + b" blob " + oid.encode() + b"\t" + head.encode("utf-8"))
    for head, sub in nested.items():
        lines.append(b"040000 tree " + _tree(repo, sub).encode() + b"\t" + head.encode("utf-8"))
    return _git(repo, "mktree", "-z", "--missing", data=b"\0".join(lines) + b"\0").strip().decode()


def build_repo(path, files):
    """A repository with one commit holding `files` [(path, content, mode)]; returns the commit id. The commit id depends only on the files."""
    path = pathlib.Path(path)
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q")
    tree = _tree(path, files)
    stamp = {"GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid", "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+0000",
             "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid", "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+0000"}
    return _git(path, "commit-tree", tree, "-m", "conformance fixture", env_extra=stamp).strip().decode()


# ---------------------------------------------------------------- the golden record

def golden_files_record():
    files = [{"path": p, "digest": "sha256:" + sha256_hex(c)} for p, c, _mode in GOLDEN_FILES]
    return sorted(files, key=lambda f: f["path"].encode("utf-8"))


def assemble_golden(source_commit):
    """The golden record, assembled from the fixed inputs (used by tests/e3_generate_golden.py, which writes the committed copy)."""
    files = golden_files_record()
    developer = certificate("developer", "root", 11)
    issuer = certificate("issuer", "root", 12)
    authority = certificate("authority", "root", 13)
    root = certificate("root", "root", 10, ca=True)
    bundle = {
        "kind": "PrimitiveRelease",
        "version": "0.0.1",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "validity": {"from": "2026-01-01", "until": "2125-12-31"},
        "createdBy": {"name": "Conformance Fixture Developer", "email": "developer@example.invalid", "certificate": developer},
        "specs": [
            {"id": "alpha", "source_path": "schemas/atomic/alpha.yaml", "meta_hash": b64_sha256(b"alpha-spec\n"), "spec": {"kind": "Alpha"}},
            {"id": "beta", "source_path": "schemas/atomic/beta.yaml", "meta_hash": b64_sha256(b"beta-spec\n"), "spec": {"kind": "Beta"}},
        ],
        "provenance": {
            "envelope": 3,
            "source_commit": source_commit,
            "dependency_lock_sha256": b64_sha256(b"dependency.yaml fixture"),
            "grammar_sha256": b64_sha256(b"check_grammar.py fixture"),
            "grammar_schema_sha256": b64_sha256(b"instance-grammar.schema.yaml fixture"),
        },
        "artifacts": {"manifest_digest": independent_manifest_digest(files), "files": files},
        "release": {"envelope": 3, "createdBy": {"name": "Conformance Fixture Issuer", "email": "issuer@example.invalid", "certificate": issuer}},
        "cic_countersign": {"authority": {"name": "Conformance Fixture Authority", "certificate": authority, "root_certificate": root}, "signed_payload": "build_hash"},
    }
    bundle["release"]["build_hash"] = independent_build_hash(bundle)
    bundle["release"]["sign"] = vault_signature("issuer", bundle["release"]["build_hash"])
    bundle["cic_countersign"]["sign"] = vault_signature("authority", bundle["release"]["build_hash"])
    return bundle


def load_golden():
    with open(FIXTURES / "golden-record.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_expected():
    return json.loads((FIXTURES / "golden.expected.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- the mutation language of the vectors

TOKEN = re.compile(r"<<U\+([0-9A-F]{4,6})>>")


def expand(value, context):
    """Strings may carry <<U+XXXX>> for a character that does not belong in a source file, and $NAME for a value of the run (e.g. $GOLDEN_COMMIT)."""
    if isinstance(value, str):
        if value in context:
            return context[value]
        return TOKEN.sub(lambda m: chr(int(m.group(1), 16)), value)
    if isinstance(value, list):
        return [expand(v, context) for v in value]
    if isinstance(value, dict):
        return {k: expand(v, context) for k, v in value.items()}
    return value


def _walk(node, dotted):
    parts = dotted.split(".")
    for part in parts[:-1]:
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node, parts[-1]


def apply_ops(bundle, ops, context):
    bundle = copy.deepcopy(bundle)
    for op in ops:
        kind = op["op"]
        if kind == "fix_manifest":
            bundle["artifacts"]["manifest_digest"] = independent_manifest_digest(bundle["artifacts"]["files"])
            continue
        parent, last = _walk(bundle, op["at"])
        idx = int(last) if isinstance(parent, list) else last
        if kind == "set":
            parent[idx] = expand(op["value"], context)
        elif kind == "delete":
            del parent[idx]
        elif kind == "swap":
            seq = parent[idx]
            seq[op["i"]], seq[op["j"]] = seq[op["j"]], seq[op["i"]]
        elif kind == "remove_item":
            del parent[idx][op["i"]]
        elif kind == "insert_item":
            parent[idx].insert(op["i"], expand(op["value"], context))
        elif kind == "insert_copy":
            parent[idx].insert(op["i"], copy.deepcopy(parent[idx][op["src"]]))
        else:
            raise ValueError("unknown op %r" % kind)
    return bundle
