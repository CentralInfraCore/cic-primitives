"""Planted defects for the reference verifier: a small, deliberate break in its source, and the test that has to turn red because of it.

`old` must occur exactly once in tools/release_record_conformance.py; `kills` lists substrings of test ids, at least one of which must be among the failing tests
(a break that fails only an unrelated test does not count as detected). A mutant with `equivalent` set changes the source but not the behaviour any input can show;
it must survive, and the reason is written down instead of a vector being invented for it. If a listed equivalent mutant is ever killed, or a killing one survives,
tests/test_release_record_conformance_planted.py fails.
"""


def m(id, old, new, kills=(), equivalent=None):
    return {"id": id, "old": old, "new": new, "kills": list(kills), "equivalent": equivalent}


MUTANTS = [
    # envelope
    m("envelope-compare-loses-type", "return type(a) is type(b) and a == b", "return a == b", ["envelope-1-and-true", "envelope-3-and-float-3"]),
    m("envelope-int-check-accepts-bool", "if p is ABSENT or type(p) is not int:", "if p is ABSENT or not isinstance(p, int):", ["envelope-both-true"]),
    m("envelope-3-treated-as-too-old", "if p < SUPPORTED_ENVELOPE:", "if p <= SUPPORTED_ENVELOPE:", ["golden"]),
    m("envelope-3-treated-as-unsupported", "if p > SUPPORTED_ENVELOPE:", "if p >= SUPPORTED_ENVELOPE:", ["golden"]),
    m("envelope-mismatch-not-checked", "if not _same(p, r) and not (p is ABSENT and r is ABSENT):", "if False:", ["envelope-provenance-3-release-2"]),
    m("envelope-gate-of-the-crypto-layer-removed", "    gate = _check_envelope(bundle)\n    if gate:", "    gate = _check_envelope(bundle)\n    if False:", ["envelope-v2"]),
    m("legacy-needs-no-provenance", 'return ("provenance" not in bundle and isinstance(release, dict)', 'return (isinstance(release, dict)', ["envelope-not-legacy-with-an-empty-provenance", "envelope-both-absent"]),
    m("legacy-allows-a-release-envelope", 'and "envelope" not in release', "", ["envelope-not-legacy-release-states-an-envelope", "provenance-absent"]),
    m("legacy-needs-no-sign-or-build-hash", 'and all(isinstance(release.get(k), str) and release.get(k) for k in ("build_hash", "sign")))', ")",
      ["envelope-not-legacy-without-sign", "envelope-not-legacy-without-build-hash"]),
    m("legacy-accepts-empty-or-non-string-sign", 'isinstance(release.get(k), str) and release.get(k) for k', 'k in release for k', ["envelope-not-legacy-empty-sign", "envelope-not-legacy-build-hash-not-a-string"]),
    m("legacy-detection-removed", '    if is_legacy_envelope_1(bundle):\n        return "envelope_too_old", "a legacy envelope 1 record (no provenance, no envelope field)"\n', "",
      ["envelope-legacy-v1-no-provenance-no-envelope", "real_legacy"]),
    # source commit
    m("source-commit-empty-accepted-as-form", 'if value is None or value == "":', "if value is None:", ["source-commit-empty"]),
    m("source-commit-length-open", "[0-9a-f]{40}\\Z", "[0-9a-f]{40,}\\Z", ["source-commit-41-digits"]),
    m("source-commit-uppercase-allowed", 'COMMIT_RE = re.compile(r"^[0-9a-f]{40}\\Z")', 'COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}\\Z")', ["source-commit-uppercase"]),
    m("source-commit-end-not-anchored", 'COMMIT_RE = re.compile(r"^[0-9a-f]{40}\\Z")', 'COMMIT_RE = re.compile(r"^[0-9a-f]{40}")', ["source-commit-41-digits"]),
    # artifacts block
    m("artifacts-empty-list-accepted", "if not files:\n        return \"artifacts_missing\"", "if files is None:\n        return \"artifacts_missing\"", ["artifacts-files-empty"]),
    m("artifacts-non-list-accepted", "return files if isinstance(files, list) else None", "return files", ["artifacts-files-not-a-list"]),
    # paths
    m("path-control-characters-only-below-0x0b", "ord(c) < 0x20 or ord(c) == 0x7F", "ord(c) < 0x0B or ord(c) == 0x7F", ["path-carriage-return", "path-unit-separator"]),
    m("path-carriage-return-allowed", "ord(c) < 0x20 or ord(c) == 0x7F", "ord(c) < 0x0D or ord(c) == 0x7F", ["path-carriage-return", "path-unit-separator"]),
    m("path-del-allowed", "ord(c) < 0x20 or ord(c) == 0x7F", "ord(c) < 0x20", ["path-del"]),
    m("path-control-check-removed", "if any(ord(c) < 0x20 or ord(c) == 0x7F for c in path):", "if False:", ["path-nul", "path-line-feed"]),
    m("path-backslash-allowed", 'if "\\\\" in path:', "if False:", ["path-backslash"]),
    m("path-dot-allowed", 'if segment in (".", ".."):', 'if segment == "..":', ["path-dot"]),
    m("path-dot-dot-allowed", 'if segment in (".", ".."):', 'if segment == ".":', ["path-dot-dot"]),
    m("path-empty-segment-allowed", 'if segment == "":', "if False:", ["path-empty-segment"]),
    m("path-non-string-allowed", "if not isinstance(path, str) or not path:", "if not path:", ["path-a-number"]),
    m("path-utf8-check-removed", "    try:\n        path.encode(\"utf-8\")\n    except UnicodeEncodeError:\n        return \"not UTF-8\"\n", "", ["path-lone-surrogate"]),
    m("path-absolute-has-its-own-branch", 'if path.startswith("/"):', "if False:", equivalent="a leading slash also yields an empty first segment, which the segment loop refuses with the same reason; only the detail text differs"),
    m("path-trailing-slash-has-its-own-branch", 'if path.endswith("/"):', "if False:", equivalent="a trailing slash also yields an empty last segment, refused with the same reason; only the detail text differs"),
    m("path-empty-has-its-own-branch", "if not isinstance(path, str) or not path:", "if not isinstance(path, str):", equivalent="the empty string splits into one empty segment, refused with the same reason"),
    # duplicates and order
    m("duplicates-not-detected", 'if entry["path"] in seen:', "if False:", ["path-repeated"]),
    m("order-by-code-point-instead-of-utf8", "return path.encode(\"utf-8\")", "return path", equivalent="UTF-8 preserves code point order, so comparing code points and comparing UTF-8 bytes agree on every input"),
    m("order-by-utf16-instead-of-utf8", "return path.encode(\"utf-8\")", "return path.encode(\"utf-16-be\")", ["order-utf8-bytes-not-utf16-units", "order-utf16-order-is-refused"]),
    m("order-not-checked", "if not path_key(before[\"path\"]) < path_key(after[\"path\"]):", "if False:", ["order-swapped-first-two"]),
    m("order-descending-accepted-for-the-last-pair", "for before, after in zip(files, files[1:]):", "for before, after in zip(files, files[1:-1]):", ["order-code-point-vs-utf8-is-the-same-here"]),
    m("order-equal-allowed", "if not path_key(before[\"path\"]) < path_key(after[\"path\"]):", "if path_key(before[\"path\"]) > path_key(after[\"path\"]):",
      equivalent="equal neighbours are the duplicate check's, which runs first; with it in place the order check is never offered an equal pair"),
    # digests and manifest
    m("digest-prefix-optional", 'DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}\\Z")', 'DIGEST_RE = re.compile(r"^(sha256:)?[0-9a-f]{64}\\Z")', ["digest-no-prefix"]),
    m("digest-uppercase-allowed", 'DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}\\Z")', 'DIGEST_RE = re.compile(r"^sha256:[0-9a-fA-F]{64}\\Z")', ["digest-uppercase"]),
    m("digest-length-open-above", 'DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}\\Z")', 'DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64,}\\Z")', ["digest-65-digits"]),
    m("digest-length-open-below", 'DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}\\Z")', 'DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{63,64}\\Z")', ["digest-63-digits"]),
    m("digest-any-algorithm", 'DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}\\Z")', 'DIGEST_RE = re.compile(r"^sha[0-9]+:[0-9a-f]{64}\\Z")', ["digest-other-algorithm"]),
    m("digest-end-not-anchored", 'DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}\\Z")', 'DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}")', ["digest-65-digits"]),
    m("manifest-digest-form-not-checked", "if not isinstance(declared, str) or not DIGEST_RE.match(declared):", "if False:", ["manifest-digest-absent", "manifest-digest-no-prefix"]),
    m("manifest-digest-form-reported-as-the-file-reason", 'return "artifact_manifest_digest_form", "artifacts.manifest_digest is absent', 'return "artifact_digest_form", "artifacts.manifest_digest is absent', ["manifest-digest-absent", "manifest-digest-no-prefix"]),
    m("file-digest-form-reported-as-the-manifest-reason", 'return "artifact_digest_form", "files[%d].digest', 'return "artifact_manifest_digest_form", "files[%d].digest', ["digest-no-prefix", "file-digest-error-wins"]),
    m("manifest-mismatch-not-checked", 'if bundle["artifacts"]["manifest_digest"] != recomputed:', "if False:", ["manifest-digest-wrong"]),
    m("manifest-single-space", '"%s  %s\\n" % (f["digest"]', '"%s %s\\n" % (f["digest"]', ["golden", "manifest"]),
    m("manifest-no-trailing-line-feed", '"%s  %s\\n" % (f["digest"]', '"%s  %s" % (f["digest"]', ["golden", "manifest"]),
    m("manifest-digest-without-prefix", 'return "sha256:" + hashlib.sha256(manifest_text(files).encode("utf-8")).hexdigest()', 'return hashlib.sha256(manifest_text(files).encode("utf-8")).hexdigest()', ["golden"]),
    m("blob-digest-without-prefix", 'return "sha256:" + hashlib.sha256(data).hexdigest()', 'return hashlib.sha256(data).hexdigest()', ["golden", "blob"]),
    # specs
    m("spec-source-path-duplicates-allowed", "if path in seen:\n            return \"spec_source_path_duplicate\"", "if False:\n            return \"spec_source_path_duplicate\"", ["specs-share-a-source-path"]),
    # blobs
    m("blob-no-repository-is-not-a-gap", "    if repo is None:\n        return Result(NOT_RUN", "    if False:\n        return Result(NOT_RUN", ["not_run", "cli_without"]),
    m("blob-absent-path-not-reported", "        if found is None:\n            failures.append((\"artifact_absent\", path))\n            continue", "        if found is None:\n            continue", ["blob-listed-path-absent", "below-a-symbolic-link"]),
    m("blob-link-counted-regular", 'REGULAR_MODES = ("100644", "100755")', 'REGULAR_MODES = ("100644", "100755", "120000")', ["blob-path-is-a-symbolic-link", "decl-symbolic-link"]),
    m("blob-submodule-mode-counted-regular", 'REGULAR_MODES = ("100644", "100755")', 'REGULAR_MODES = ("100644", "100755", "160000")',
      equivalent="a submodule is a commit entry, and the type test (kind != blob) still refuses it; the mode and the type test each refuse it alone"),
    m("blob-only-directories-refused", 'if kind != "blob" or mode not in REGULAR_MODES:\n            failures', 'if mode == "040000":\n            failures',
      ["blob-path-is-a-symbolic-link", "blob-path-is-a-submodule", "blob-path-is-a-directory"]),
    m("blob-type-check-removed", 'if kind != "blob" or mode not in REGULAR_MODES:\n            failures', 'if mode not in REGULAR_MODES:\n            failures',
      equivalent="every non-blob tree entry (tree 040000, commit 160000) has a mode outside REGULAR_MODES, so the type test adds nothing the mode test does not already refuse"),
    m("blob-digest-not-compared", "elif blob_digest(data.stdout) != digest:", "elif False:", ["blob-digest-of-a-crlf-copy", "blob-digest-of-another-file"]),
    m("blob-trees-not-listed", '"ls-tree", "-r", "-t", "-z", "--full-tree"', '"ls-tree", "-r", "-z", "--full-tree"', ["blob-path-is-a-directory", "decl-directory"]),
    m("blob-only-first-failure-kept", "return Result(FAIL, failures[0][0], failures[0][1], failures)", "return Result(FAIL, failures[0][0], failures[0][1], failures[:1])", ["every_failing_blob"]),
    m("blob-full-tree-flag", '"-z", "--full-tree"', '"-z"', equivalent="git is run with -C at the repository root, where the listing is the whole tree with or without --full-tree"),
    # crypto
    m("crypto-build-hash-not-compared", "if recorded != recomputed:", "if False:", ["stale-everything"]),
    m("crypto-envelope-1-rule-for-the-hash", "compiler._release_hash_payload(bundle, 2)", "compiler._release_hash_payload(bundle, 1)", ["golden"]),
    m("crypto-signature-result-ignored", "    ok, why = compiler._verify_cert_signature(certificate, sign, recorded)\n    return Result(PASS) if ok else Result(FAIL, \"signature_invalid\", why)",
      "    ok, why = compiler._verify_cert_signature(certificate, sign, recorded)\n    return Result(PASS)", ["signature-stale", "nobody-signed"]),
    m("crypto-countersign-result-ignored", "    ok, why = compiler._verify_cert_signature(certificate, sign, recorded)\n    return Result(PASS) if ok else Result(FAIL, \"countersign_invalid\", why)",
      "    ok, why = compiler._verify_cert_signature(certificate, sign, recorded)\n    return Result(PASS)", ["countersign-stale", "nobody-signed"]),
    m("crypto-signature-over-the-recomputed-not-the-recorded-hash", "ok, why = compiler._verify_cert_signature(certificate, sign, recorded)\n    return Result(PASS) if ok else Result(FAIL, \"signature_invalid\", why)",
      "ok, why = compiler._verify_cert_signature(certificate, sign, compiler.get_sha256_b64(compiler.to_canonical_json(compiler._release_hash_payload(bundle, 2))))\n    return Result(PASS) if ok else Result(FAIL, \"signature_invalid\", why)",
      ["stale-everything"]),
    m("crypto-payload-name-not-checked", 'if countersign.get("signed_payload") != "build_hash":', "if False:", ["another_payload"]),
    m("crypto-absent-countersign-counts-as-pass", "elif all(s == PASS for s in statuses):", "elif True:", ["absent_countersignature"]),
    m("crypto-checks-stop-at-the-first-failure", 'parts = {"build_hash": check_build_hash(bundle, compiler), "signature": check_signature(bundle, compiler), "countersign": check_countersign(bundle, compiler)}',
      'parts = {"build_hash": check_build_hash(bundle, compiler)}\n    parts["signature"] = check_signature(bundle, compiler) if parts["build_hash"].status == PASS else Result(NOT_RUN)\n    parts["countersign"] = check_countersign(bundle, compiler) if parts["signature"].status == PASS else Result(NOT_RUN)',
      ["do_not_hide", "nobody-signed", "countersign-stale"]),
    # declaration
    m("declaration-unknown-key-accepted", "    if unknown:", "    if False:", ["decl-include", "decl-exclude"]),
    m("declaration-duplicate-accepted", "        if path in seen:\n            return \"declaration_path_duplicate\"", "        if False:\n            return \"declaration_path_duplicate\"", ["decl-repeated"]),
    m("declaration-absent-path-accepted", "        if path not in tree:", "        if False:", ["decl-not-in-the-commit"]),
    m("declaration-empty-accepted", "    if not paths:\n        return \"declaration_empty\"", "    if False:\n        return \"declaration_empty\"", ["decl-paths-empty"]),
    # command line
    m("cli-failing-layer-exits-zero", "    if any(s == FAIL for s in status.values()):\n        return 1", "    if False:\n        return 1", ["failing_layer_is_exit_status_one"]),
    m("cli-required-layer-not-enforced", "    if any(status[layer] != PASS for layer in required):\n        return 3", "    if False:\n        return 3", ["cli_without_a_repository", "required_layer_that_is_not_run"]),
    m("cli-incomplete-counts-as-pass", "    if any(status[layer] != PASS for layer in required):\n        return 3", "    if any(status[layer] in (FAIL, NOT_RUN) for layer in required):\n        return 3", ["incomplete"]),
    m("cli-not-run-counts-as-pass", "    if any(status[layer] != PASS for layer in required):\n        return 3", "    if any(status[layer] in (FAIL, INCOMPLETE) for layer in required):\n        return 3", ["required_layer_that_is_not_run", "cli_without_a_repository"]),
    m("cli-unknown-layer-accepted", "    elif not required or any(x not in LAYERS for x in required):", "    elif False:", ["unknown_layer"]),
    m("cli-require-none-without-meaning", '    if required == ["none"]:', "    if False:", ["require_none"]),
]
