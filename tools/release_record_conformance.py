#!/usr/bin/env python3
"""Reference verifier of the release record contract, envelope 3 (docs/en/RELEASE-RECORD-CONTRACT.md).

It is the yardstick the compiler change will be measured against: the compiler does not get to say that its own output is right. It READS. It creates no record,
signs nothing, publishes nothing and writes no source data; git is only asked to list and print objects.

    release_record_conformance.py RECORD [--repo PATH] [--require record,blobs,crypto] [--json]

Three layers, reported apart. The success of one is never taken for the success of another:

  record   the record alone (contract sections 4 to 8 and 11, the structural reasons). No git, no signature.
  blobs    the artifact digests against the git tree of `provenance.source_commit` in --repo. NOT_RUN when no repository or no commit is available; that is an
           addition to the record's own evidence, not a condition of it (section 11).
  crypto   the checks inherited from envelope 2: `release.build_hash` recomputed over the whole bundle, `release.sign` and `cic_countersign` verified over it.
           The functions are those of tools/compiler.py (run_verify_release), not a model of them. Reported per check, and the layer is PASS only when all three
           pass; an absent counter-signature makes it INCOMPLETE, never PASS.

None of it says who signed (the trust gates of section 2 are out of scope): no layer, and no combination of layers, is "valid" or "authentic".

`validate_declaration` is the producer-side counterpart (section 6): a pure function over a parsed project.yaml and a git tree listing, the rule the compiler has to
agree with. It does not read the working directory.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys

import yaml

PASS, FAIL, NOT_RUN, INCOMPLETE = "PASS", "FAIL", "NOT_RUN", "INCOMPLETE"
ABSENT = object()
SUPPORTED_ENVELOPE = 3
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
REGULAR_MODES = ("100644", "100755")

# every reason this module can give, in the order of section 11; tests/test_release_record_conformance.py compares this list with the contract text
RECORD_REASONS = (
    "envelope_mismatch", "envelope_unsupported", "envelope_too_old",
    "source_commit_missing", "source_commit_form",
    "artifacts_missing", "artifact_path_form", "artifact_path_duplicate", "artifact_order", "artifact_digest_form", "artifact_manifest_mismatch",
    "spec_source_path_duplicate",
)
CRYPTO_REASONS = ("build_hash_mismatch", "signature_invalid", "countersign_invalid")
BLOB_REASONS = ("artifact_absent", "artifact_digest_mismatch", "artifact_not_regular")
DECLARATION_REASONS = (
    "declaration_missing", "declaration_empty", "declaration_unknown_key", "declaration_path_form", "declaration_path_duplicate",
    "declared_path_absent", "declared_path_not_regular",
)


class Result:
    def __init__(self, status, reason=None, detail="", failures=None):
        self.status, self.reason, self.detail = status, reason, detail
        self.failures = failures if failures is not None else ([(reason, detail)] if reason else [])

    def as_dict(self):
        return {"status": self.status, "reason": self.reason, "detail": self.detail, "failures": [list(f) for f in self.failures]}


# ---------------------------------------------------------------- paths and digests (sections 3, 7, 8)

def path_form_error(path):
    """None when `path` is a path of the contract; otherwise what is wrong with it."""
    if not isinstance(path, str) or not path:
        return "not a non-empty string"
    try:
        path.encode("utf-8")
    except UnicodeEncodeError:
        return "not UTF-8"
    if any(ord(c) < 0x20 or ord(c) == 0x7F for c in path):
        return "control character"
    if "\\" in path:
        return "backslash"
    if path.startswith("/"):
        return "absolute"
    if path.endswith("/"):
        return "trailing slash"
    for segment in path.split("/"):
        if segment == "":
            return "empty segment"
        if segment in (".", ".."):
            return "'%s' segment" % segment
    return None


def path_key(path):
    return path.encode("utf-8")


def manifest_text(files):
    """The sha256sum-format text of section 8; the caller has already checked the paths and the digests."""
    return "".join("%s  %s\n" % (f["digest"][len("sha256:"):], f["path"]) for f in files)


def manifest_digest(files):
    return "sha256:" + hashlib.sha256(manifest_text(files).encode("utf-8")).hexdigest()


def blob_digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _same(a, b):
    """Equal in type and value: True is not 1 and 3.0 is not 3."""
    return type(a) is type(b) and a == b


# ---------------------------------------------------------------- the record layer: one function per reason, run in the order of RECORD_CHECKS

def _check_envelope(bundle):
    provenance = bundle.get("provenance")
    release = bundle.get("release")
    p = provenance.get("envelope", ABSENT) if isinstance(provenance, dict) else ABSENT
    r = release.get("envelope", ABSENT) if isinstance(release, dict) else ABSENT
    if not _same(p, r) and not (p is ABSENT and r is ABSENT):
        return "envelope_mismatch", "provenance.envelope=%r, release.envelope=%r" % (_show(p), _show(r))
    if p is ABSENT or type(p) is not int:
        return "envelope_unsupported", "envelope=%r" % (_show(p),)
    if p < SUPPORTED_ENVELOPE:
        return "envelope_too_old", "envelope=%d" % p
    if p > SUPPORTED_ENVELOPE:
        return "envelope_unsupported", "envelope=%d" % p
    return None


def _show(value):
    return "(absent)" if value is ABSENT else value


def _check_source_commit(bundle):
    provenance = bundle.get("provenance")
    value = provenance.get("source_commit") if isinstance(provenance, dict) else None
    if value is None or value == "":
        return "source_commit_missing", "absent, null or empty"
    if not isinstance(value, str) or not COMMIT_RE.match(value):
        return "source_commit_form", "not 40 lowercase hexadecimal digits: %r" % (value,)
    return None


def _files(bundle):
    artifacts = bundle.get("artifacts")
    files = artifacts.get("files") if isinstance(artifacts, dict) else None
    return files if isinstance(files, list) else None


def _check_artifacts_present(bundle):
    files = _files(bundle)
    if not files:
        return "artifacts_missing", "artifacts.files is absent or empty"
    return None


def _entry_path(entry):
    return entry.get("path") if isinstance(entry, dict) else None


def _check_path_form(bundle):
    for index, entry in enumerate(_files(bundle)):
        problem = path_form_error(_entry_path(entry))
        if problem:
            return "artifact_path_form", "files[%d]: %s" % (index, problem)
    return None


def _check_path_duplicate(bundle):
    seen = set()
    for entry in _files(bundle):
        if entry["path"] in seen:
            return "artifact_path_duplicate", "path %r is repeated" % entry["path"]
        seen.add(entry["path"])
    return None


def _check_order(bundle):
    files = _files(bundle)
    for before, after in zip(files, files[1:]):
        if not path_key(before["path"]) < path_key(after["path"]):
            return "artifact_order", "%r is listed before %r" % (before["path"], after["path"])
    return None


def _check_digest_form(bundle):
    for index, entry in enumerate(_files(bundle)):
        digest = entry.get("digest") if isinstance(entry, dict) else None
        if not isinstance(digest, str) or not DIGEST_RE.match(digest):
            return "artifact_digest_form", "files[%d].digest is not sha256: and 64 lowercase hexadecimal digits" % index
    declared = bundle["artifacts"].get("manifest_digest")
    # not in section 11 by name: an absent or malformed manifest digest is read as a digest of the wrong form (see the note in docs/en/RELEASE-RECORD-CONFORMANCE.md)
    if not isinstance(declared, str) or not DIGEST_RE.match(declared):
        return "artifact_digest_form", "artifacts.manifest_digest is not sha256: and 64 lowercase hexadecimal digits"
    return None


def _check_manifest(bundle):
    recomputed = manifest_digest(_files(bundle))
    if bundle["artifacts"]["manifest_digest"] != recomputed:
        return "artifact_manifest_mismatch", "recomputed %s" % recomputed
    return None


def _check_spec_source_paths(bundle):
    seen = set()
    for spec in bundle.get("specs") or []:
        path = spec.get("source_path") if isinstance(spec, dict) else None
        if path in seen:
            return "spec_source_path_duplicate", "source_path %r is shared" % (path,)
        if path is not None:
            seen.add(path)
    return None


RECORD_CHECKS = (
    ("envelope", _check_envelope),
    ("source_commit", _check_source_commit),
    ("artifacts_present", _check_artifacts_present),
    ("path_form", _check_path_form),
    ("path_duplicate", _check_path_duplicate),
    ("order", _check_order),
    ("digest_form", _check_digest_form),
    ("manifest", _check_manifest),
    ("spec_source_paths", _check_spec_source_paths),
)


def check_record(bundle):
    """Section 11, the structural reasons, in order. The first refusal ends the layer (a record that fails an earlier check is not examined for the later ones)."""
    if not isinstance(bundle, dict):
        return Result(FAIL, "envelope_unsupported", "the record is not a mapping")
    for _name, check in RECORD_CHECKS:
        refusal = check(bundle)
        if refusal:
            return Result(FAIL, *refusal)
    return Result(PASS)


# ---------------------------------------------------------------- the blob layer: git objects, read-only

def _git(repo, *args):
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null", "LC_ALL": "C"}
    return subprocess.run(["git", "-C", repo] + list(args), capture_output=True, env=env)


def load_tree(repo, commit):
    """{path: (mode, type, oid)} of the whole tree of `commit`, directories included. None when the commit is not available."""
    if _git(repo, "cat-file", "-e", commit + "^{commit}").returncode != 0:
        return None
    listing = _git(repo, "ls-tree", "-r", "-t", "-z", "--full-tree", commit)
    if listing.returncode != 0:
        return None
    tree = {}
    for record in listing.stdout.split(b"\0"):
        if not record:
            continue
        meta, _tab, name = record.partition(b"\t")
        mode, kind, oid = meta.decode("ascii").split(" ")
        tree[name.decode("utf-8", "surrogateescape")] = (mode, kind, oid)
    return tree


def check_blobs(bundle, repo, record_result=None):
    """Each listed artifact against the tree of the source commit. NOT_RUN, with the reason, when it cannot be asked."""
    if repo is None:
        return Result(NOT_RUN, detail="no repository given; the blob checks were not made")
    if _check_source_commit(bundle) is not None:
        return Result(NOT_RUN, detail="the record carries no usable source_commit")
    files = _files(bundle)
    if not files or any(path_form_error(_entry_path(e)) for e in files):
        return Result(NOT_RUN, detail="the artifact list is not usable, so there is nothing to look up")
    commit = bundle["provenance"]["source_commit"]
    tree = load_tree(repo, commit)
    if tree is None:
        return Result(NOT_RUN, detail="source commit %s is not available in %s; the blob checks were not made" % (commit, repo))
    failures = []
    for entry in files:
        path, digest = entry["path"], entry.get("digest")
        found = tree.get(path)
        if found is None:
            failures.append(("artifact_absent", path))
            continue
        mode, kind, oid = found
        if kind != "blob" or mode not in REGULAR_MODES:
            failures.append(("artifact_not_regular", "%s is mode %s, type %s" % (path, mode, kind)))
            continue
        data = _git(repo, "cat-file", "blob", oid)
        if data.returncode != 0:
            failures.append(("artifact_absent", "%s: blob %s cannot be read" % (path, oid)))
        elif blob_digest(data.stdout) != digest:
            failures.append(("artifact_digest_mismatch", "%s: the blob is %s" % (path, blob_digest(data.stdout))))
    if failures:
        return Result(FAIL, failures[0][0], failures[0][1], failures)
    return Result(PASS)


# ---------------------------------------------------------------- the crypto layer: the envelope 2 checks, with the compiler's own functions

class CryptoUnavailable(Exception):
    pass


def _compiler():
    """tools/compiler.py reads project.yaml from the working directory when it is imported; outside a repository root it exits, which is reported, not hidden."""
    try:
        try:
            from tools import compiler
        except ImportError:
            import compiler
    except SystemExit:
        raise CryptoUnavailable("tools/compiler.py cannot be imported from this directory (it needs project.yaml in the working directory)")
    except ImportError as exc:
        raise CryptoUnavailable("tools/compiler.py cannot be imported: %s" % exc)
    return compiler


def check_build_hash(bundle, compiler=None):
    compiler = compiler or _compiler()
    release = bundle.get("release")
    recorded = release.get("build_hash") if isinstance(release, dict) else None
    # envelope 3 covers the bundle by the envelope 2 rule (section 4): the whole bundle except release.sign, release.build_hash and cic_countersign
    payload = compiler._release_hash_payload(bundle, 2)
    recomputed = compiler.get_sha256_b64(compiler.to_canonical_json(payload))
    if recorded != recomputed:
        return Result(FAIL, "build_hash_mismatch", "recorded %r, recomputed %s" % (recorded, recomputed))
    return Result(PASS)


def check_signature(bundle, compiler=None):
    compiler = compiler or _compiler()
    release = bundle.get("release") if isinstance(bundle.get("release"), dict) else {}
    issuer = release.get("createdBy") if isinstance(release.get("createdBy"), dict) else {}
    certificate, sign, recorded = issuer.get("certificate"), release.get("sign"), release.get("build_hash")
    if not (certificate and sign and recorded):
        return Result(FAIL, "signature_invalid", "release.createdBy.certificate, release.sign or release.build_hash is missing")
    ok, why = compiler._verify_cert_signature(certificate, sign, recorded)
    return Result(PASS) if ok else Result(FAIL, "signature_invalid", why)


def check_countersign(bundle, compiler=None):
    compiler = compiler or _compiler()
    countersign = bundle.get("cic_countersign")
    if not countersign:
        return Result(NOT_RUN, detail="absent: the record carries no CIC counter-signature, which proves nothing either way")
    authority = countersign.get("authority") if isinstance(countersign.get("authority"), dict) else {}
    release = bundle.get("release") if isinstance(bundle.get("release"), dict) else {}
    certificate, sign, recorded = authority.get("certificate"), countersign.get("sign"), release.get("build_hash")
    if countersign.get("signed_payload") != "build_hash":
        return Result(FAIL, "countersign_invalid", "signed_payload is not 'build_hash'")
    if not (certificate and sign and recorded):
        return Result(FAIL, "countersign_invalid", "authority.certificate, sign or release.build_hash is missing")
    ok, why = compiler._verify_cert_signature(certificate, sign, recorded)
    return Result(PASS) if ok else Result(FAIL, "countersign_invalid", why)


def check_crypto(bundle):
    """The three checks, each on its own and all of them run, so one failure does not hide another. Layer status: FAIL if any failed, PASS if all three passed,
    INCOMPLETE otherwise (an absent counter-signature, an envelope this verifier does not read)."""
    gate = _check_envelope(bundle)
    if gate:
        return {"status": NOT_RUN, "detail": "the envelope is not 3 (%s); the envelope 3 rule for build_hash does not apply" % gate[0],
                "build_hash": Result(NOT_RUN), "signature": Result(NOT_RUN), "countersign": Result(NOT_RUN)}
    try:
        compiler = _compiler()
    except CryptoUnavailable as exc:
        return {"status": NOT_RUN, "detail": str(exc), "build_hash": Result(NOT_RUN), "signature": Result(NOT_RUN), "countersign": Result(NOT_RUN)}
    parts = {"build_hash": check_build_hash(bundle, compiler), "signature": check_signature(bundle, compiler), "countersign": check_countersign(bundle, compiler)}
    statuses = [p.status for p in parts.values()]
    if FAIL in statuses:
        status = FAIL
    elif all(s == PASS for s in statuses):
        status = PASS
    else:
        status = INCOMPLETE
    return dict(parts, status=status, detail="")


# ---------------------------------------------------------------- the producer's declaration (section 6)

def validate_declaration(project, tree):
    """(reason, detail) when the declaration in a parsed project.yaml is refused, else None. `tree` is load_tree() of the source commit: nothing is resolved against
    the working directory."""
    settings = project.get("compiler_settings") if isinstance(project, dict) else None
    declaration = settings.get("release_artifacts") if isinstance(settings, dict) else None
    if not isinstance(declaration, dict):
        return "declaration_missing", "compiler_settings.release_artifacts is absent"
    unknown = sorted(k for k in declaration if k != "paths")
    if unknown:
        return "declaration_unknown_key", "not part of this version: %s" % ", ".join(str(k) for k in unknown)
    paths = declaration.get("paths")
    if not isinstance(paths, list):
        return "declaration_missing", "release_artifacts.paths is absent or not a list"
    if not paths:
        return "declaration_empty", "release_artifacts.paths is empty"
    for path in paths:
        problem = path_form_error(path)
        if problem:
            return "declaration_path_form", "%r: %s" % (path, problem)
    seen = set()
    for path in paths:
        if path in seen:
            return "declaration_path_duplicate", "%r" % path
        seen.add(path)
    for path in paths:
        if path not in tree:
            return "declared_path_absent", "%r is not in the tree of the source commit" % path
    for path in paths:
        mode, kind, _oid = tree[path]
        if kind != "blob" or mode not in REGULAR_MODES:
            return "declared_path_not_regular", "%r is mode %s, type %s" % (path, mode, kind)
    return None


# ---------------------------------------------------------------- the whole

def verify(bundle, repo=None):
    return {"record": check_record(bundle), "blobs": check_blobs(bundle, repo), "crypto": check_crypto(bundle)}


def first_reason(report):
    """The first refusal in the order of section 11: the record layer, then the blob layer, then the crypto layer."""
    if report["record"].reason:
        return report["record"].reason
    for part in ("build_hash", "signature", "countersign"):
        if report["crypto"][part].reason:
            return report["crypto"][part].reason
    return report["blobs"].reason


def to_json(report):
    crypto = report["crypto"]
    return {"record": report["record"].as_dict(), "blobs": report["blobs"].as_dict(),
            "crypto": {"status": crypto["status"], "detail": crypto["detail"],
                       **{k: crypto[k].as_dict() for k in ("build_hash", "signature", "countersign")}},
            "first_reason": first_reason(report),
            "not_proven": NOT_PROVEN}


NOT_PROVEN = (
    "who signed (no trust anchor, signer authority or certificate validity at the release date is established)",
    "that the record is authentic or the release is fit to publish",
    "that the layers not run (or INCOMPLETE) hold",
)


def _print(report):
    rec, blobs, crypto = report["record"], report["blobs"], report["crypto"]
    print("record   %s%s" % (rec.status, "  %s: %s" % (rec.reason, rec.detail) if rec.reason else ""))
    print("blobs    %s%s" % (blobs.status, "  %s" % blobs.detail if blobs.detail else ""))
    for reason, detail in blobs.failures:
        print("           %s: %s" % (reason, detail))
    print("crypto   %s%s" % (crypto["status"], "  %s" % crypto["detail"] if crypto["detail"] else ""))
    for part in ("build_hash", "signature", "countersign"):
        r = crypto[part]
        print("  %-12s %s%s" % (part, r.status, "  %s: %s" % (r.reason, r.detail) if r.reason else ("  %s" % r.detail if r.detail else "")))
    for line in NOT_PROVEN:
        print("NOT proven: %s" % line)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("record")
    parser.add_argument("--repo", help="git repository that holds the source commit; enables the blobs layer")
    parser.add_argument("--require", default="", help="comma-separated layers that must be PASS for exit status 0 (record,blobs,crypto)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        with open(args.record, encoding="utf-8") as fh:
            bundle = yaml.safe_load(fh)
    except (OSError, yaml.YAMLError) as exc:
        print("cannot read %s: %s" % (args.record, exc), file=sys.stderr)
        return 2
    report = verify(bundle, args.repo)
    if args.json:
        print(json.dumps(to_json(report), indent=2, sort_keys=True))
    else:
        _print(report)
    status = {"record": report["record"].status, "blobs": report["blobs"].status, "crypto": report["crypto"]["status"]}
    required = [x for x in args.require.split(",") if x]
    if any(s == FAIL for s in status.values()):
        return 1
    if any(status.get(layer) != PASS for layer in required):
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
