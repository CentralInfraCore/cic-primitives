# Release candidate pre-check

`tools/release_candidate_precheck.py` answers one question before a release is cut, and again after: **does the release contain the grammar that a consumer pinned?**

The consumer (`cic-primitive-forms`, `corpus/pins.yaml`) pins a commit and the SHA-256 of the raw blob bytes of exactly twelve files. A receipt may name a release only if that release provably holds those twelve files. The tool proves or refutes that from git objects and, after the release, from the release record. It reads. It signs, tags and publishes nothing, and it does **not** verify a signature: that stays with `python tools/compiler.py verify-release <record> --trust-root <root.pem>`. Cryptographic origin and "the signed claim covers the pinned grammar" are two questions, and neither stands in for the other.

## Modes

```
release_candidate_precheck.py candidate --manifest PINS --pin NAME [--commit SHA] [--release-head SHA] [--devel REF] [--version X.Y.Z] [--release-date YYYY-MM-DD]
release_candidate_precheck.py record    --manifest PINS --pin NAME --record release/<name>-vX.Y.Z.yaml
```

**candidate** (before the release). The pinned commit exists and is on `devel`; the twelve files at it are byte-identical to the manifest; the manifest digest and the pin name recompute; the commit the release will actually run on (`--release-head`: the release branch head, or the merge commit on `main`) holds the same twelve files; the version is a valid next increment (the rule of `compiler.py`); the files in which `devel` has moved on since the pin are listed.

**record** (after the release). The record's `provenance.source_commit` holds the twelve files byte-identical to the manifest; and the record says which of them it digests itself (the schema sources in `specs`, and the two files of `provenance.grammar_*`) and which rest on the source commit alone.

Exit status 1 when a hard check fails. `OPEN` lines are gates the tool does not and cannot close; they never turn into a pass.

## What was measured (2026-11-01, against the pin `cic-primitives-73ae469-6a188078`)

* `candidate` on `73ae469` with `--release-head 73ae469`: all checks pass, 12 of 12 files byte-identical. `devel` (`d27173f`) **has moved on in `proposals/atom-grammar/P0-4-MIGRATION.md`**, a pinned file: **a release cut from the head of `devel` is not the pin.** The release has to run on a branch cut from `73ae469`, or the pin has to move.
* `candidate` with `--release-head` set to the head of `devel`: FAIL on that file.
* `record` on `release/cic-primitives-v0.2.0.yaml`: FAIL. Its `source_commit` (`9c67ea4`) lacks 4 of the 12 files and holds 5 others with different bytes; the record's own digests of `check_grammar.py`, `instance-grammar.schema.yaml`, `policy-surface.yaml` and `access.yaml` do not equal the pinned files. This is the refutation of `v0.2.0` as the release of the pin, now by a repeatable tool.
* In `v0.2.0` the record digests 2 of the 12 files itself (`role.yaml`, `shape.yaml`); 4 more are digested by name but with other bytes; 6 rest on the signed `source_commit` alone. For a new release the same split applies: **6 of 12 pinned files have no digest of their own in the record**, and are bound by the signed `source_commit` (a git SHA-1 object id) only. Whether that is enough, or the record should digest all twelve, is for the owner.

## Open gates (not checked by this tool)

1. A CIC root pinned **outside** the record (`verify-release --trust-root`).
2. Signer authority: the release issuer certificate is not chained to anything in the record; whether the countersignature alone authorizes a release is not decided.
3. Certificate validity at the release date (the certificates of `v0.2.0` expire 2026-12-31).
4. The digest encoding: the record writes base64, a receipt takes `sha256:` and hex. The tool re-encodes for its own comparison only; the contract and Rust/Go golden tests are a Forms unit.
5. Signing and publishing: on hold by the owner until the gates above are shown.

## Sequence this tool supports

1. Cut `primitives/releases/vX.Y.Z` from `73ae469` (not from the head of `devel`). Run `candidate` with `--release-head` on the head the release will run on, after the release preparation commit. Any pinned file in the difference is a stop.
2. Close the open gates.
3. After the release: `verify-release` with the pinned root, and `record` on the record. Only both together support a receipt that names the release.
