# Release record contract, envelope 3 (normative draft)

Status: **draft for review, specification only.** No compiler change is made by this document. Implementation starts only after this contract is fixed, and conformance vectors (section 12) exist before the compiler changes.

Key words MUST, MUST NOT, SHOULD and MAY are used as in RFC 2119.

## 1. Why

A consumer that pins a set of files needs to check, from a release record alone, that the release contains exactly those bytes. Today (envelope 2) the record digests the schema sources (`specs[].meta_hash`, base64) and two grammar files (`provenance.grammar_*`, base64); everything else rests on `provenance.source_commit`, which may even be written as `null`. Measured on `primitives/@v0.2.0` (see `docs/en/RELEASE-CANDIDATE-PRECHECK.md`): 2 of the 12 pinned files are digested and equal, 6 have no digest. The owner's decision of 2026-11-01: the record carries its own digest of every artifact, with the algorithm; `source_commit` stays mandatory but does not replace the digests; a proof must not depend on a git object being reachable later.

## 2. Scope and non-goals

In scope: what a `PrimitiveRelease` record states about the files it releases, how those statements are encoded, and when a verifier MUST refuse the record.

Out of scope, kept as separate, later work (the trust gates): the external trust anchor, the signer's authority and the countersignature's authorization, certificate validity on the release day, the origin of a consumer's manifest, and whether any release is genuine. This contract changes **no** signing mechanism: `release.sign`, `release.build_hash` and `cic_countersign` are produced and verified as in envelope 2. A record that satisfies this contract is not thereby authentic.

**The compiler MUST NOT learn what to digest from a consumer.** The record describes, on its own, an artifact set that is the producer's declared published surface (section 6). A consumer verifies its own requirement against that set (section 10). No consumer path, pin name or manifest appears in the compiler or in the record.

## 3. Terms

* **Source commit**: the git commit the release is made from, `provenance.source_commit`.
* **Artifact**: a file, identified by its path in the tree of the source commit, that the record releases.
* **Blob bytes**: the content of the git blob at that path in the source commit, exactly as stored (no filter, no line-ending conversion, no normalization).
* **Digest**: `sha256:` followed by 64 lowercase hexadecimal digits, the SHA-256 of the blob bytes. This is the form of the receipt fields (`primitive_build_hash`, `grammar_sha256`), so a consumer needs no re-encoding for the new fields. The algorithm is carried in the value itself.

## 4. Envelope 3

`provenance.envelope` and `release.envelope` are `3`. What `build_hash` covers is the rule of envelope 2: the whole bundle except `release.sign`, `release.build_hash` and `cic_countersign`. The new members below are therefore covered by the existing signature without any change to it; **the new version number is what lets a verifier tell a record that meets this contract from one that does not.**

```yaml
provenance:
  envelope: 3
  source_commit: <40 lowercase hex>        # REQUIRED, never null
  dependency_lock_sha256: ...              # unchanged, legacy base64
  grammar_sha256: ...                      # unchanged, legacy base64
  grammar_schema_sha256: ...               # unchanged, legacy base64
artifacts:                                 # REQUIRED
  manifest_digest: sha256:<64 hex>         # section 8
  files:                                   # REQUIRED, non-empty
    - {path: <path>, digest: sha256:<64 hex>}
```

`specs[].meta_hash` and the legacy `provenance` digests keep their meaning (base64 SHA-256 of the same raw bytes) and are not artifact digests; a verifier MUST NOT accept them in place of `artifacts.files`.

## 5. Source commit

* `provenance.source_commit` MUST be 40 lowercase hexadecimal digits and MUST name the commit the artifacts were read from.
* The compiler MUST refuse to create the release when it cannot determine it. Writing `null` or omitting it (what envelope 2 allows) is non-conforming in envelope 3.
* It identifies and retrieves the source state. It is a git SHA-1 object identifier and MUST NOT be treated as evidence of the artifacts' bytes; the digests are.

## 6. The artifact set

* Declared by the producer in `project.yaml`: `compiler_settings.release_artifacts` with `include` (a non-empty list of path patterns) and optional `exclude`. The declared set is the producer's published surface; the compiler MUST NOT derive it from anything a consumer supplies.
* The compiler resolves the patterns against the **tree of the source commit** (`git ls-tree -r`), never against the working directory, so the digests are of what the commit holds.
* Every selected entry MUST be a regular file (mode 100644 or 100755). A symbolic link, a submodule or any other entry in the selected set is an error, not a skip. An empty set is an error.
* The pattern dialect (shell-style globs, `**` for directories) MUST be fixed in the implementation change and covered by golden vectors; it is not part of the record.

## 7. Paths

A path MUST be a UTF-8 string that is exactly the path in the git tree, `/`-separated, relative, with no empty, `.` or `..` segment, no leading or trailing `/`, no backslash and no NUL. Paths are compared byte by byte; no Unicode normalization and no case folding is applied. `artifacts.files[].path` MUST be unique. `specs[].source_path` MUST be unique as well; a verifier MUST reject a duplicate and MUST NOT let a later entry overwrite an earlier one.

## 8. Order and the manifest digest

`artifacts.files` MUST be sorted by the UTF-8 bytes of `path`, ascending, with no duplicate. A verifier MUST reject an unsorted list; it MUST NOT sort it silently, because an order a verifier repairs is an order nobody signed.

`artifacts.manifest_digest` is `sha256:` and the SHA-256 of this text, LF line ends, no other whitespace: for each file in order, the 64 hex digits of its digest, two spaces, its path, LF (the `sha256sum` format). The same definition as the manifest of a consumer's pin, so lines can be compared.

Worked example (reproducible with `git show <commit>:<path> | sha256sum` on three files, `a.txt` containing `alpha` and LF, `d/b.txt` containing `beta` and LF, and a file named with the single character U+00E9 followed by `.txt` containing U+00E9 and LF):

```
b6a98d9ce9a2d9149288fa3df42d377c3e42737afdcdaf714e33c0a100b51060  a.txt
f2c82decdd7181cf98945929a62598db7e6b477e11f6e0eb0ae97020eff151ad  d/b.txt
edd3a863872a04239eb29ad4bc12fc892b3d4ae57cc7e786a3697816f8e141c2  <U+00E9>.txt
```

manifest digest `sha256:39e022575a650d2c2cf04a4d65ae8744e04d0ccb3699fb417db9c4c160b2ec53`. Byte order puts `d/b.txt` before the file whose name starts with U+00E9 (0xC3 is greater than `d`).

## 9. Old records

* Envelope 1 and 2 records stay verifiable for what they are (integrity, signature, countersignature). They MUST NOT be rewritten, re-signed or "upgraded".
* A verifier that is asked for conformance to this contract MUST refuse envelope 1 and 2 with the reason `envelope_too_old`. `primitives/@v0.2.0` therefore stays what it is: a valid envelope 2 record that does not contain the pinned grammar, and it stays a negative case for the pre-check.
* Nothing in this contract makes an earlier release retroactively valid.

## 10. How a consumer uses the record (informative)

The consumer has its own requirement: a set of paths with digests (for `cic-primitive-forms`, 12 files). It is satisfied by a record when, for every one of its paths, the path is in `artifacts.files` and the digest is equal, and the record is envelope 3. The consumer recomputes its own manifest digest over its own subset. The pre-check tool (`tools/release_candidate_precheck.py`, `record` mode) changes from reading `specs` and two grammar fields to reading `artifacts.files`; its `record digest coverage` gate closes only for an envelope 3 record. The consumer, not the compiler, decides whether the record's `source_commit` must also equal a pinned commit.

## 11. Verifier obligations and reason identifiers

A verifier of this contract MUST check, and refuse with the reason named, in this order:

| Reason | Refused when |
|---|---|
| `envelope_too_old` | the envelope is below 3 |
| `source_commit_missing` | `provenance.source_commit` is absent, `null` or empty |
| `source_commit_form` | it is not 40 lowercase hexadecimal digits |
| `artifacts_missing` | `artifacts` or `artifacts.files` is absent or empty |
| `artifact_path_form` | a path breaks section 7 |
| `artifact_path_duplicate` | a path is repeated |
| `artifact_order` | the list is not sorted by path bytes |
| `artifact_digest_form` | a digest is not `sha256:` and 64 lowercase hexadecimal digits (an unknown algorithm included) |
| `artifact_manifest_mismatch` | `manifest_digest` is not the recomputed one |
| `spec_source_path_duplicate` | two `specs` entries share a `source_path` |

and, when the source commit is available to it, additionally: `artifact_absent` (a listed path is not in the commit), `artifact_digest_mismatch` (the digest is not the SHA-256 of the blob bytes), `artifact_not_regular` (the entry is a link or submodule). Availability of the commit is an addition to the record's own evidence, not a condition of it: a verifier without the commit still performs every record-only check and reports that the blob checks were not made.

## 12. Conformance vectors (to exist before the compiler changes)

Golden: the worked example above (digests and manifest digest); a record built from it with a fixed bundle whose canonical bytes and `build_hash` are fixed in the vector; the same bundle with the artifacts listed in a different input order producing the same output order.

Negative, one defect each, reading the reason and not only the exit status: a v2 record (`envelope_too_old`), a v3 record with `source_commit` null, absent, uppercase, short, or non-hex; `artifacts` absent and empty; a path with `..`, `.`, an empty segment, a leading `/`, a backslash, a NUL; a repeated path; an unsorted list; a digest without the prefix, in uppercase, 63 digits long, and with another algorithm name; a wrong manifest digest; two `specs` with one `source_path`; a listed path absent from the commit; a digest of a normalized (CRLF) copy instead of the blob bytes; a symbolic link in the selected set; an empty selected set. And a **record-level swap**: an artifact digest replaced by that of another file with the same `build_hash` field left unchanged is refused by the signature check, not by this contract (stated, so that nobody expects this contract to detect it).

Each negative vector MUST be shown to be refused by a planted-defect run of the verifier (the vector turns green when the check is removed), as for the other contracts of this ecosystem.

## 13. Not decided here

The glob dialect (section 6); the exact `project.yaml` key names beyond `release_artifacts.include` and `exclude`; whether the producer's declared set may be larger than a consumer's need (it may); how long envelope 2 verification is kept; and every trust gate listed in section 2. The base64 representation of the legacy fields is not changed.

## 14. Sequence

1. This contract is reviewed and fixed.
2. The conformance vectors and a reference verifier of the record-only checks are written and shown to fail (negative) and pass (golden) before any compiler change.
3. The compiler change, as a separate pull request, against those vectors.
4. The pre-check tool moves to `artifacts.files` for envelope 3.
5. Trust gates, separately. The release candidate `73ae469` stays untouched; signing and publication stay on hold.
