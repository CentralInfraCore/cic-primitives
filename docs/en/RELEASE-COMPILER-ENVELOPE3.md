# The compiler writes envelope 3

`python tools/compiler.py release` writes a `PrimitiveRelease` record of **envelope 3** (docs/en/RELEASE-RECORD-CONTRACT.md) and nothing else. Envelope 1 and 2 records are not written any more, and are not touched: `verify-release` still reads them exactly as before, and the real records `release/cic-primitives-v0.1.5.yaml` (envelope 1) and `release/cic-primitives-v0.2.0.yaml` (envelope 2) are test cases. No record is rewritten, re-signed or migrated.

## What changes in a release

1. `provenance.source_commit` is mandatory: `git rev-parse HEAD`, 40 lowercase hexadecimal digits. If git cannot say, the compiler stops; it no longer records `null`.
2. The producer declares the files it publishes in `project.yaml`:

   ```yaml
   compiler_settings:
     release_artifacts:
       paths:            # explicit, relative to the repository root; no glob, no include, no exclude
         - LICENSE.md
         - schemas/atomic/shape.yaml
   ```

   The declaration is read from **the source commit** (`project.yaml` as that commit holds it), and the paths are resolved against **the git tree of that commit**: not the working directory, not a checkout with its line-end filters, not a consumer's pin manifest. A path that is a directory, a symbolic link or a submodule is refused, as is an absolute path, a `..` or `.` segment, a control character, a repeated path, a missing path, an empty list, a key other than `paths`. The compiler stops with the reason (`declaration_missing`, `declaration_empty`, `declaration_unknown_key`, `declaration_path_form`, `declaration_path_duplicate`, `declared_path_absent`, `declared_path_not_regular`) **before** it asks Vault for anything.
3. `artifacts` is written: for each declared path `sha256:` and the hex SHA-256 of the blob bytes at the source commit, sorted by the UTF-8 bytes of the path, and `manifest_digest` over the sha256sum-format lines. `specs[].source_path` must be unique.
4. `build_hash`, `release.sign` and (outside the compiler) `cic_countersign` are the existing mechanism: `build_hash` covers the whole bundle except `release.sign`, `release.build_hash` and `cic_countersign`, so `artifacts` and `source_commit` are covered without any change to it.

A repository whose `project.yaml` has no `release_artifacts` cannot cut a release: it stops with `declaration_missing`. Which files a repository publishes is the producer's decision and is made in `project.yaml`, in a change of its own.

## The rest of the record is the source commit's too

`artifacts` is read from the git tree. The rest of the record is not made from the tree: `specs` (their content and `meta_hash`) come from the schema files, the three legacy provenance digests from `dependency.yaml` and the two grammar files, the issuer and the validity from `project.yaml` and `commitment.yaml`. `validate_release_prerequisites` asks `git status --porcelain`, and a clean status does **not** make those the commit's bytes: an ignored file, a file marked assume-unchanged or skip-worktree, a line-end filter or a sparse checkout all leave it clean (each is a test, with the premise that the status is clean asserted first).

So `run_release` compares, before it asks Vault for anything, every one of those inputs with the blob of the source commit, and the schema files it found with the selection made on the commit's tree. A difference (`worktree_differs_from_source_commit`, with the file and what differs) stops the release: a record made of two states of the source would contradict itself without anyone having lied.

What this does not cover: the validation gates (`run_validation`, `run_primitive_validation`, the grammar gate) read the working directory too. Their verdict can concern a file that is not part of the record (an ignored example, for instance) and is not about the commit for such files; it does not enter the record. A release should be cut from a fresh clone of the commit.

## How the output is held to the contract

The compiler does not say that its own output is right.

* The record it writes is read back by the reference verifier (`tools/release_record_conformance.py`), which does not import the compiler's new functions (and the compiler does not import it): `record`, `blobs` and `crypto` layers, and the `artifacts` block is compared with values recomputed outside this code base (`tests/fixtures/envelope3`).
* The 32 signature coverage vectors of the contract run on the record the compiler wrote, not only on the golden record; the structural vectors too.
* The declaration vectors run on the compiler's own functions, and on the reference's, and the two must agree.
* The yardstick of PR #25 (the reference verifier, the golden fixtures, the vectors, the planted-defect proof) is frozen at its merge commit: `tests/test_conformance_frozen.py` fails if any of it changes together with the compiler.
* 72 planted defects in `tools/compiler.py` (`tests/e3_compiler_mutants.py`): 63 have to turn one of the tests that target them red, 9 cannot change behaviour, are listed with the reason and have to survive.

## `verify-release`

Accepts envelope 3 (build hash, signature, counter-signature, as for envelope 2) and says what it leaves to the conformance check: the artifact list is **not** checked there. The two are separate: `verify-release` is the cryptographic verification, `tools/release_record_conformance.py` is the check against the envelope 3 contract. A release policy may require both; neither imports the other.

## The counter-signature service

Read-only audit of `cic-countersign` (`internal/countersign/handler.go`, `devel` 8ce2427): the service takes `build_hash` as an opaque, already computed digest ("trusted as given, never recomputed") and verifies the author's signature over it. The submitted `document` is carried through for the audit log only (`kind` and `version` are logged) and is not hashed or canonicalized. It reads nothing of the envelope or of `artifacts`. Nothing there depends on this change; the service was not modified.
