"""The negative and coverage vectors of the envelope 3 contract (docs/en/RELEASE-RECORD-CONTRACT.md, section 12), as data.

A vector is a defect applied to the committed golden record: `ops` (see e3_fixtures.apply_ops), then `reauth` (what is recomputed and re-signed with the test keys:
all, hash_only, hash_sign, hash_countersign, none). A structural defect is re-authenticated by default, so the refusal comes from the contract check and not from the
signature, and the crypto layer of such a record is expected to PASS. `expect` names the reason of the layer under test; `crypto` is the status the crypto layer
must show.

`repo` is the git repository the blob layer is run against: "golden" (the tree of the worked example), "special" (the same files plus a symbolic link and a
submodule), or None.
"""

GOLDEN_COMMIT = "$GOLDEN_COMMIT"


def v(id, layer, reason, ops=(), reauth="all", repo=None, crypto="PASS", note="", parts=None):
    return {"id": id, "layer": layer, "reason": reason, "ops": list(ops), "reauth": reauth, "repo": repo, "crypto": crypto, "note": note, "parts": parts}


def s(at, value):
    return {"op": "set", "at": at, "value": value}


def d(at):
    return {"op": "delete", "at": at}


FIX = {"op": "fix_manifest"}
DIG = "sha256:" + "0" * 64


def files_only(*entries):
    """Replace the artifact list by entries [(path, digest)] and recompute the manifest digest."""
    return [s("artifacts.files", [{"path": p, "digest": g} for p, g in entries]), FIX]


# the envelope checks refuse before anything else: the crypto layer is NOT_RUN for them, the envelope 3 rule for build_hash does not apply
ENVELOPE = [
    v("envelope-v1-explicit", "record", "envelope_too_old", [s("provenance.envelope", 1), s("release.envelope", 1)], crypto="NOT_RUN"),
    v("envelope-v2", "record", "envelope_too_old", [s("provenance.envelope", 2), s("release.envelope", 2)], crypto="NOT_RUN"),
    v("envelope-0", "record", "envelope_too_old", [s("provenance.envelope", 0), s("release.envelope", 0)], crypto="NOT_RUN"),
    v("envelope-provenance-3-release-2", "record", "envelope_mismatch", [s("release.envelope", 2)], crypto="NOT_RUN"),
    v("envelope-provenance-2-release-3", "record", "envelope_mismatch", [s("provenance.envelope", 2)], crypto="NOT_RUN"),
    v("envelope-provenance-3-release-absent", "record", "envelope_mismatch", [d("release.envelope")], crypto="NOT_RUN"),
    v("envelope-provenance-absent-release-3", "record", "envelope_mismatch", [d("provenance.envelope")], crypto="NOT_RUN"),
    v("envelope-provenance-3-release-4", "record", "envelope_mismatch", [s("release.envelope", 4)], crypto="NOT_RUN"),
    v("envelope-3-and-true", "record", "envelope_mismatch", [s("release.envelope", True)], crypto="NOT_RUN", note="True == 1 in Python; the contract compares type and value"),
    v("envelope-1-and-true", "record", "envelope_mismatch", [s("provenance.envelope", 1), s("release.envelope", True)], crypto="NOT_RUN", note="1 == True in Python"),
    v("envelope-3-and-float-3", "record", "envelope_mismatch", [s("release.envelope", 3.0)], crypto="NOT_RUN", note="3 == 3.0 in Python"),
    v("envelope-both-4", "record", "envelope_unsupported", [s("provenance.envelope", 4), s("release.envelope", 4)], crypto="NOT_RUN"),
    v("envelope-both-string-3", "record", "envelope_unsupported", [s("provenance.envelope", "3"), s("release.envelope", "3")], crypto="NOT_RUN"),
    v("envelope-both-true", "record", "envelope_unsupported", [s("provenance.envelope", True), s("release.envelope", True)], crypto="NOT_RUN"),
    v("envelope-both-float-3", "record", "envelope_unsupported", [s("provenance.envelope", 3.0), s("release.envelope", 3.0)], crypto="NOT_RUN"),
    v("envelope-both-null", "record", "envelope_unsupported", [s("provenance.envelope", None), s("release.envelope", None)], crypto="NOT_RUN"),
    v("envelope-both-absent", "record", "envelope_unsupported", [d("provenance.envelope"), d("release.envelope")], crypto="NOT_RUN",
      note="a real v1 record omits the field; the contract table sends 'both absent' to envelope_unsupported, not to envelope_too_old"),
    v("envelope-after-the-source-commit-defect", "record", "envelope_too_old", [s("provenance.envelope", 2), s("release.envelope", 2), s("provenance.source_commit", None)],
      crypto="NOT_RUN", note="the envelope check comes first; the later defect is not examined"),
]

SOURCE_COMMIT = [
    v("source-commit-null", "record", "source_commit_missing", [s("provenance.source_commit", None)]),
    v("source-commit-absent", "record", "source_commit_missing", [d("provenance.source_commit")]),
    v("source-commit-empty", "record", "source_commit_missing", [s("provenance.source_commit", "")]),
    v("provenance-absent", "record", "envelope_mismatch", [d("provenance")], crypto="NOT_RUN", note="the envelope sits in provenance too, so this is refused earlier"),
    v("source-commit-uppercase", "record", "source_commit_form", [s("provenance.source_commit", "F0CF873C0E2F889D440CC7411535A63A89A41E9F")]),
    v("source-commit-short", "record", "source_commit_form", [s("provenance.source_commit", "f0cf873")]),
    v("source-commit-41-digits", "record", "source_commit_form", [s("provenance.source_commit", "f0cf873c0e2f889d440cc7411535a63a89a41e9f0")]),
    v("source-commit-not-hex", "record", "source_commit_form", [s("provenance.source_commit", "g0cf873c0e2f889d440cc7411535a63a89a41e9f")]),
    v("source-commit-a-number", "record", "source_commit_form", [s("provenance.source_commit", 12345)]),
]

ARTIFACTS = [
    v("artifacts-absent", "record", "artifacts_missing", [d("artifacts")]),
    v("artifacts-files-absent", "record", "artifacts_missing", [d("artifacts.files")]),
    v("artifacts-files-empty", "record", "artifacts_missing", [s("artifacts.files", [])]),
    v("artifacts-files-not-a-list", "record", "artifacts_missing", [s("artifacts.files", {"a.txt": DIG})]),
]


def path_vector(id, path, note=""):
    return v(id, "record", "artifact_path_form", [s("artifacts.files.0.path", path)], note=note)


PATHS = [
    path_vector("path-dot-dot", "../a.txt"),
    path_vector("path-dot-dot-inside", "d/../a.txt"),
    path_vector("path-dot", "./a.txt"),
    path_vector("path-dot-inside", "d/./b.txt"),
    path_vector("path-empty-segment", "d//b.txt"),
    path_vector("path-empty", ""),
    path_vector("path-leading-slash", "/a.txt", "an absolute path"),
    path_vector("path-trailing-slash", "d/", "a directory spelling"),
    path_vector("path-backslash", "d\\b.txt"),
    path_vector("path-nul", "a<<U+0000>>.txt"),
    path_vector("path-line-feed", "a<<U+000A>>b.txt", "a line feed would split a manifest line"),
    path_vector("path-carriage-return", "a<<U+000D>>b.txt"),
    path_vector("path-tab", "a<<U+0009>>b.txt"),
    path_vector("path-del", "a<<U+007F>>b.txt"),
    path_vector("path-unit-separator", "a<<U+001F>>b.txt"),
    path_vector("path-a-number", 7),
    path_vector("path-null", None),
    v("path-lone-surrogate", "record", "artifact_path_form", [s("artifacts.files.0.path", "a<<U+D800>>.txt")], note="not representable as UTF-8"),
    v("path-entry-not-a-mapping", "record", "artifact_path_form", [s("artifacts.files.0", "a.txt")]),
    v("path-key-absent", "record", "artifact_path_form", [d("artifacts.files.0.path")]),
]

DUPLICATES = [
    v("path-repeated", "record", "artifact_path_duplicate", [{"op": "insert_copy", "at": "artifacts.files", "i": 1, "src": 0}, FIX]),
    v("path-repeated-with-another-digest", "record", "artifact_path_duplicate",
      [{"op": "insert_copy", "at": "artifacts.files", "i": 1, "src": 0}, s("artifacts.files.1.digest", "sha256:" + "1" * 64), FIX],
      note="the later entry must not overwrite the earlier one, whatever its digest"),
    v("path-repeated-at-the-end", "record", "artifact_path_duplicate", [{"op": "insert_copy", "at": "artifacts.files", "i": 3, "src": 2}, FIX]),
    v("path-case-only-difference-is-two-paths", "record", None, [s("artifacts.files.0.path", "A.txt"), FIX, {"op": "insert_item", "at": "artifacts.files", "i": 1,
      "value": {"path": "a.txt", "digest": DIG}}, FIX], note="positive: no case folding; 'A.txt' < 'a.txt' < 'd/b.txt' is a well-formed unique sorted list"),
]

def two_files(first, second):
    return [s("artifacts.files", [{"path": first, "digest": DIG}, {"path": second, "digest": DIG}]), FIX]


ORDER = [
    v("order-utf8-bytes-not-utf16-units", "record", None, two_files("<<U+FF5E>>.txt", "<<U+10000>>.txt"),
      note="positive: U+FF5E (EF BD 9E) sorts before U+10000 (F0 90 80 80) in UTF-8; in UTF-16 the surrogate D800 would put U+10000 first"),
    v("order-utf16-order-is-refused", "record", "artifact_order", two_files("<<U+10000>>.txt", "<<U+FF5E>>.txt")),
    v("order-swapped-first-two", "record", "artifact_order", [{"op": "swap", "at": "artifacts.files", "i": 0, "j": 1}, FIX]),
    v("order-reversed", "record", "artifact_order", [{"op": "swap", "at": "artifacts.files", "i": 0, "j": 2}, FIX]),
    v("order-code-point-vs-utf8-is-the-same-here", "record", "artifact_order", [{"op": "swap", "at": "artifacts.files", "i": 1, "j": 2}, FIX],
      note="d/b.txt before the e-acute file: 0x64 < 0xC3 in the UTF-8 bytes"),
]

DIGESTS = [
    v("digest-no-prefix", "record", "artifact_digest_form", [s("artifacts.files.0.digest", "b6a98d9ce9a2d9149288fa3df42d377c3e42737afdcdaf714e33c0a100b51060"), FIX]),
    v("digest-uppercase", "record", "artifact_digest_form", [s("artifacts.files.0.digest", "sha256:B6A98D9CE9A2D9149288FA3DF42D377C3E42737AFDCDAF714E33C0A100B51060"), FIX]),
    v("digest-63-digits", "record", "artifact_digest_form", [s("artifacts.files.0.digest", "sha256:" + "a" * 63), FIX]),
    v("digest-65-digits", "record", "artifact_digest_form", [s("artifacts.files.0.digest", "sha256:" + "a" * 65), FIX]),
    v("digest-other-algorithm", "record", "artifact_digest_form", [s("artifacts.files.0.digest", "sha512:" + "a" * 64), FIX]),
    v("digest-base64", "record", "artifact_digest_form", [s("artifacts.files.0.digest", "ZG9lcyBub3QgbWF0dGVy"), FIX]),
    v("digest-a-number", "record", "artifact_digest_form", [s("artifacts.files.0.digest", 5)]),
    v("digest-absent", "record", "artifact_digest_form", [d("artifacts.files.0.digest")]),
    v("manifest-digest-absent", "record", "artifact_digest_form", [d("artifacts.manifest_digest")],
      note="the contract names no reason for this; it is read as a digest of the wrong form (see docs/en/RELEASE-RECORD-CONFORMANCE.md)"),
    v("manifest-digest-no-prefix", "record", "artifact_digest_form", [s("artifacts.manifest_digest", "39e022575a650d2c2cf04a4d65ae8744e04d0ccb3699fb417db9c4c160b2ec53")]),
    v("manifest-digest-wrong", "record", "artifact_manifest_mismatch", [s("artifacts.manifest_digest", "sha256:" + "0" * 64)]),
    v("manifest-digest-of-another-order", "record", "artifact_manifest_mismatch", [s("artifacts.manifest_digest", "sha256:2f1b7f2d3bf95c4e0b9a2d6f1d0a3f1d78e0a2e1c7a1b3f1d9c0e5a47b2d1c8e")],
      note="a well-formed digest that is not the recomputed one"),
    v("manifest-after-a-file-digest-changed", "record", "artifact_manifest_mismatch", [s("artifacts.files.0.digest", "sha256:" + "2" * 64)],
      note="a file digest changed and the manifest digest was not recomputed"),
]

SPECS = [
    v("specs-share-a-source-path", "record", "spec_source_path_duplicate", [s("specs.1.source_path", "schemas/atomic/alpha.yaml")]),
]

# the coverage of the existing signature (section 12): a defect applied to the SIGNED record, build_hash and release.sign left as they were
COVERAGE_MUTATIONS = [
    ("path", [s("artifacts.files.0.path", "a2.txt")]),
    ("digest", [s("artifacts.files.0.digest", "sha256:" + "3" * 64)]),
    ("count-added", [{"op": "insert_item", "at": "artifacts.files", "i": 3, "value": {"path": "z" + "\N{LATIN SMALL LETTER E WITH ACUTE}", "digest": "sha256:" + "4" * 64}}]),
    ("count-removed", [{"op": "remove_item", "at": "artifacts.files", "i": 2}]),
    ("order", [{"op": "swap", "at": "artifacts.files", "i": 0, "j": 1}]),
    ("source-commit", [s("provenance.source_commit", "0" * 40)]),
    ("manifest-digest", [s("artifacts.manifest_digest", "sha256:" + "5" * 64)]),
    ("spec-meta-hash", [s("specs.0.meta_hash", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")]),
]

CRYPTO = []
P = "PASS"
for name, ops in COVERAGE_MUTATIONS:
    # signed record, defect, nothing recomputed: build_hash no longer matches. The two signatures still verify over the STALE build_hash they were made for,
    # which is why the recomputation of build_hash is the check that carries the coverage proof.
    CRYPTO.append(v("coverage-%s-stale-everything" % name, "crypto", "build_hash_mismatch", ops, reauth="none", crypto="FAIL",
                    parts=("build_hash_mismatch", P, P)))
    # hash recomputed, nobody re-signed: both signatures are stale
    CRYPTO.append(v("coverage-%s-hash-recomputed-nobody-signed" % name, "crypto", "signature_invalid", ops, reauth="hash_only", crypto="FAIL",
                    parts=(P, "signature_invalid", "countersign_invalid")))
    # hash recomputed and release.sign valid, the counter-signature stale: only the counter-signature check fails
    CRYPTO.append(v("coverage-%s-countersign-stale" % name, "crypto", "countersign_invalid", ops, reauth="hash_sign", crypto="FAIL",
                    parts=(P, P, "countersign_invalid")))
    # hash recomputed and the counter-signature valid, release.sign stale: only the signature check fails
    CRYPTO.append(v("coverage-%s-signature-stale" % name, "crypto", "signature_invalid", ops, reauth="hash_countersign", crypto="FAIL",
                    parts=(P, "signature_invalid", P)))

# a record whose checks all pass (the second reading of the same defects: re-authenticated, the contract checks are what catch it) is covered by the ENVELOPE..SPECS lists

ALL_RECORD = ENVELOPE + SOURCE_COMMIT + ARTIFACTS + PATHS + DUPLICATES + ORDER + DIGESTS + SPECS

# the blob layer: the record is whole and re-authenticated, the git tree disagrees
BLOBS = [
    v("blob-digest-of-a-crlf-copy", "blobs", "artifact_digest_mismatch", [s("artifacts.files.0.digest", "$DIGEST_CRLF_A"), FIX],
      repo="golden", note="the digest of the CRLF copy of a.txt, not of the blob bytes"),
    v("blob-listed-path-absent-from-the-commit", "blobs", "artifact_absent",
      [{"op": "insert_item", "at": "artifacts.files", "i": 2, "value": {"path": "z.txt", "digest": DIG}}, FIX], repo="golden"),
    v("blob-path-below-a-symbolic-link", "blobs", "artifact_absent", files_only(("l/x", DIG)) + [s("provenance.source_commit", "$SPECIAL_COMMIT")], repo="special"),
    v("blob-path-is-a-directory", "blobs", "artifact_not_regular", files_only(("d", DIG)), repo="golden"),
    v("blob-path-is-a-symbolic-link", "blobs", "artifact_not_regular", files_only(("l", DIG)) + [s("provenance.source_commit", "$SPECIAL_COMMIT")], repo="special"),
    v("blob-path-is-a-submodule", "blobs", "artifact_not_regular", files_only(("m", DIG)) + [s("provenance.source_commit", "$SPECIAL_COMMIT")], repo="special"),
    v("blob-digest-of-another-file", "blobs", "artifact_digest_mismatch", [s("artifacts.files.0.digest", "$DIGEST_OF_B"), FIX], repo="golden"),
    v("blob-source-commit-points-at-another-tree", "blobs", "artifact_digest_mismatch", [s("provenance.source_commit", "$SPECIAL_COMMIT")], repo="special",
      note="the special tree holds a.txt with other bytes"),
]

# declaration vectors (section 6): (id, reason, project.yaml as parsed, tree name)
DECLARATIONS = [
    ("decl-ok", None, {"compiler_settings": {"release_artifacts": {"paths": ["a.txt", "d/b.txt"]}}}),
    ("decl-ok-reordered-input", None, {"compiler_settings": {"release_artifacts": {"paths": ["d/b.txt", "a.txt"]}}}),
    ("decl-compiler-settings-absent", "declaration_missing", {}),
    ("decl-release-artifacts-absent", "declaration_missing", {"compiler_settings": {}}),
    ("decl-release-artifacts-not-a-mapping", "declaration_missing", {"compiler_settings": {"release_artifacts": ["a.txt"]}}),
    ("decl-paths-absent", "declaration_missing", {"compiler_settings": {"release_artifacts": {}}}),
    ("decl-paths-not-a-list", "declaration_missing", {"compiler_settings": {"release_artifacts": {"paths": "a.txt"}}}),
    ("decl-paths-empty", "declaration_empty", {"compiler_settings": {"release_artifacts": {"paths": []}}}),
    ("decl-include", "declaration_unknown_key", {"compiler_settings": {"release_artifacts": {"include": ["*.txt"], "paths": ["a.txt"]}}}),
    ("decl-exclude", "declaration_unknown_key", {"compiler_settings": {"release_artifacts": {"exclude": ["x"], "paths": ["a.txt"]}}}),
    ("decl-include-without-paths", "declaration_unknown_key", {"compiler_settings": {"release_artifacts": {"include": ["*.txt"]}}}),
    ("decl-glob-is-only-a-name", "declared_path_absent", {"compiler_settings": {"release_artifacts": {"paths": ["*.txt"]}}}),
    ("decl-absolute", "declaration_path_form", {"compiler_settings": {"release_artifacts": {"paths": ["/a.txt"]}}}),
    ("decl-dot-dot", "declaration_path_form", {"compiler_settings": {"release_artifacts": {"paths": ["d/../a.txt"]}}}),
    ("decl-dot", "declaration_path_form", {"compiler_settings": {"release_artifacts": {"paths": ["./a.txt"]}}}),
    ("decl-backslash", "declaration_path_form", {"compiler_settings": {"release_artifacts": {"paths": ["d\\b.txt"]}}}),
    ("decl-line-feed", "declaration_path_form", {"compiler_settings": {"release_artifacts": {"paths": ["a<<U+000A>>b.txt"]}}}),
    ("decl-carriage-return", "declaration_path_form", {"compiler_settings": {"release_artifacts": {"paths": ["a<<U+000D>>b.txt"]}}}),
    ("decl-not-a-string", "declaration_path_form", {"compiler_settings": {"release_artifacts": {"paths": [3]}}}),
    ("decl-repeated", "declaration_path_duplicate", {"compiler_settings": {"release_artifacts": {"paths": ["a.txt", "d/b.txt", "a.txt"]}}}),
    ("decl-not-in-the-commit", "declared_path_absent", {"compiler_settings": {"release_artifacts": {"paths": ["a.txt", "missing.txt"]}}}),
    ("decl-below-a-symbolic-link", "declared_path_absent", {"compiler_settings": {"release_artifacts": {"paths": ["l/x"]}}}),
    ("decl-directory", "declared_path_not_regular", {"compiler_settings": {"release_artifacts": {"paths": ["d"]}}}),
    ("decl-symbolic-link", "declared_path_not_regular", {"compiler_settings": {"release_artifacts": {"paths": ["l"]}}}),
    ("decl-submodule", "declared_path_not_regular", {"compiler_settings": {"release_artifacts": {"paths": ["m"]}}}),
]
