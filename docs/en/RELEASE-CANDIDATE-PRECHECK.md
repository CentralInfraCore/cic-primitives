# Release candidate pre-check

`tools/release_candidate_precheck.py` answers one question before a release is cut, and again after: **does the release contain the grammar that a consumer pinned?**

The consumer (`cic-primitive-forms`, `corpus/pins.yaml`) pins a commit and the SHA-256 of the raw blob bytes of exactly twelve files. A receipt may name a release only if that release provably holds those twelve files. The tool proves or refutes that from git objects and, after the release, from the release record. It reads. It signs, tags and publishes nothing, and it does **not** verify a signature: that stays with `python tools/compiler.py verify-release <record> --trust-root <root.pem>`. Cryptographic origin and "the signed claim covers the pinned grammar" are two questions, and neither stands in for the other.

## Modes

```
release_candidate_precheck.py candidate --manifest PINS --pin NAME [--commit SHA] [--release-head SHA] [--devel REF] [--version X.Y.Z] [--release-date YYYY-MM-DD]
release_candidate_precheck.py record    --manifest PINS --pin NAME --record release/<name>-vX.Y.Z.yaml
```

**candidate** (before the release). The pinned commit exists and is on `devel`; the twelve files at it are byte-identical to the manifest; the manifest digest and the pin name recompute; the commit the release will actually run on (`--release-head`: the release branch head, or the merge commit on `main`) holds the same twelve files; the version is a valid next increment (the rule of `compiler.py`); the files in which `devel` has moved on since the pin are listed. With `--release-head` it also reads `compiler_settings.release_artifacts.paths` from the `project.yaml` **at that head** (the declaration an envelope 3 record is written from): all twelve pinned paths must be declared, spelled exactly, or the run fails, because a record written from that head cannot carry the digest of a file that is not declared. A head with no declaration (a head of an earlier release) is not a failure; the record coverage then stays the open gate it was.

**record** (after the release). The record's `provenance.source_commit` holds the twelve files byte-identical to the manifest, **and** the record carries its own digest of every one of the twelve. The second is a release requirement (decision of 2026-11-01): `source_commit` identifies and retrieves the source state and stays mandatory, but it does not replace the file digests; the record has to carry the digest values and their algorithm itself, so that verifying the twelve files does not depend on a git object being reachable later. Where the record keeps them is the record contract (`RELEASE-RECORD-CONTRACT.md`): an **envelope 3** record keeps them in `artifacts.files`, as `sha256:` and 64 lowercase hex digits of the raw git blob bytes, and the tool reads only there. A record of an earlier envelope (1, 2) or with none keeps at most the schema sources in `specs` and the two files of `provenance.grammar_*`; those are read as before, and `artifacts` is not read for them. A digest in any other form (uppercase hex, no `sha256:` prefix, base64, a wrong length, a trailing newline, not a string), a path listed twice, an unknown `release.envelope` (including `3.0` and `true`), or an envelope 3 record with no `artifacts.files` list is a failure and never coverage. The tool does **not** check the artifacts block itself (order, uniqueness, `manifest_digest`, signatures): that is `tools/release_record_conformance.py`, and it says so on every envelope 3 run.

Exit status 1 when a hard check fails. `OPEN` lines are gates the tool does not and cannot close; they never turn into a pass.

## What was measured (2026-11-01, against the pin `cic-primitives-73ae469-6a188078`)

* `candidate` on `73ae469` with `--release-head 73ae469`: all checks pass, 12 of 12 files byte-identical. `devel` (`d27173f`) **has moved on in `proposals/atom-grammar/P0-4-MIGRATION.md`**, a pinned file: **a release cut from the head of `devel` is not the pin.** The release has to run on a branch cut from `73ae469`, or the pin has to move.
* `candidate` with `--release-head` set to the head of `devel`: FAIL on that file.
* `record` on `release/cic-primitives-v0.2.0.yaml`: FAIL. Its `source_commit` (`9c67ea4`) lacks 4 of the 12 files and holds 5 others with different bytes; the record's own digests of `check_grammar.py`, `instance-grammar.schema.yaml`, `policy-surface.yaml` and `access.yaml` do not equal the pinned files. This is the refutation of `v0.2.0` as the release of the pin, now by a repeatable tool.
* In `v0.2.0` the record digests 2 of the 12 files itself and equal (`role.yaml`, `shape.yaml`); 4 more are digested by name but with other bytes; 6 have no digest in it. A record of envelope 2 can digest **at most 6 of the 12 by construction** (the schema sources and the two grammar files); that is why `record` fails a record below 12 of 12, and why `candidate` kept `record digest coverage` as an OPEN gate. The envelope 3 contract, the compiler that writes it and the 30-path declaration (`RELEASE-RECORD-CONTRACT.md`, `RELEASE-COMPILER-ENVELOPE3.md`, `RELEASE-ARTIFACT-CLASSIFICATION.md`) remove that limit, and this tool now reads an envelope 3 record.
* The negative evidence on `v0.2.0` is frozen and reproducible: `tests/fixtures/forms-pin-73ae469.yaml` is a copy of the consumer's pin, and `test_release_v020_does_not_hold_the_pinned_grammar` asserts the 4 absent files, the 5 files with other bytes, the 4 wrong record digests and the 2-of-12 coverage (it needs the full history and the tag `primitives/@v0.2.0`; in a shallow checkout it is skipped, not passed). Nothing about `v0.2.0` is corrected or hidden by this tool.
* **2026-11-02, `v0.2.1`** (release commit `5e8c3219b52399e3e764b0b0bb27de710f5445a4`, source commit `106965b8cea7cce2081beb77008753af21e68b46`, cut from `73ae469` on `primitives/releases/v0.2.1`): `record` on `release/cic-primitives-v0.2.1.yaml` (SHA-256 `e5d8268a...cf63`): all 12 files byte-identical at `source_commit`, `files the record digests itself (12 of 12)`, `PASS record digest coverage`, `readiness: checks_passed_gates_open`, exit 0. The record layer, blobs layer and signatures of the same record were checked by `tools/release_record_conformance.py --require record,blobs,crypto` (exit 0) and `compiler.py verify-release`, not by this tool. `candidate` with `--release-head` set to the release commit reports the declaration PASS (12 pinned among 30 release artifacts); its `version` check fails there because the tag `primitives/@v0.2.1` exists, as it must after the release. This frozen record is `test_release_v021_holds_the_pinned_grammar_twelve_of_twelve` (commit id and record digest, not the tag; skipped without the full history, a failure where `CIC_REQUIRE_RELEASE_HISTORY=1`).
## Profile, readiness and exit status

* **Profile.** `--profile cic-grammar-12` (the default) requires the pin set to be exactly the 12 distinct paths of the CIC grammar pin, fixed in the tool and never read from the manifest it judges; a dropped, added, swapped or repeated file fails, whatever the count. `--profile none` is the general tool and is a stated choice. A recomputed manifest digest shows consistency, not that the manifest comes from the entitled consumer; `manifest origin` is an OPEN gate.
* **Coverage is presence and agreement.** `record digest coverage` is PASS only when every pinned file has a digest in the record **and** each equals the pinned bytes; a present but wrong digest is not coverage and the report never shows a PASS next to it.
* **Readiness.** Exit status 0 is **not** fitness for release. Every run ends with `readiness: failed` or `readiness: checks_passed_gates_open` (also `--json`: `readiness`, `failed`, `open_gates`, `lines`). The tool never returns `ready` while an OPEN gate exists, and none of its OPEN gates is one it can close.
* **Fail-closed history.** Where the gate sets `CIC_REQUIRE_RELEASE_HISTORY=1`, a missing commit, a missing tag and a moved tag are three separate failures with their own messages; only outside that mode is the evidence test skipped.

## What a PASS means, and what it does not

The tool proves, from git objects and the record: the pinned commit exists and is on `devel`; the twelve files are byte-identical to the manifest at the commit the release runs on; the manifest digest and the pin name recompute; the version is a valid increment; and (record mode) the record carries its own digest of each of the twelve and they equal the pinned bytes.

A `12/12 PASS` is **not** a statement that a release is genuine. It does not show who may sign, that the countersignature authorizes a release, that the certificates are trusted or valid on the release day, or that the digest encoding is the receipt's. Those are the open gates below; they are printed as `OPEN` on every run and cannot be turned into a pass by this tool. Every run also ends with a `scope` line saying so.

## The candidate `73ae469` is not the head of `devel`

The candidate is the pinned commit `73ae469`. `devel` has moved on since (`d27173f`, and `P0-4-MIGRATION.md`, a pinned file, differs there). A pull request that targets `devel`, such as the one that adds this tool, gives no authority to cut the release from the current head of `devel`: a release cut there is not the pin, and `candidate --release-head <that head>` fails on the changed file. The release runs on a branch cut from `73ae469`, or the pin moves; the former is the owner's chosen direction, and it is what `v0.2.1` was: a branch cut from `73ae469`, the six squash commits that carry the envelope 3 infrastructure cherry-picked onto it, and `devel` unchanged.

## Open gates (not checked by this tool)

0. **Record digest coverage** (`candidate` only): the head's declaration says what the compiler will digest; that the record carries its own digest of all 12 pinned files is shown by `record` mode on the record after the release, not before. Where the head declares nothing, the gate keeps its old reason (an earlier record digests at most 6 of the 12).
1. A CIC root pinned **outside** the record (`verify-release --trust-root`).
2. Signer authority: the release issuer certificate is not chained to anything in the record; whether the countersignature alone authorizes a release is not decided.
3. Certificate validity at the release date (the certificates of `v0.2.0` expire 2026-12-31).
4. The digest encoding: an envelope 3 record writes `sha256:<hex>` (a contract on the record side; an earlier record wrote base64), a receipt takes `sha256:` and hex. Whether the receipt's own contract takes the record's values as they are, and the Rust/Go golden tests, are a Forms unit; the gate stays OPEN with the reworded reason.
5. Signing and publishing: on hold by the owner until the gates above are shown.

## Sequence this tool supports

1. Cut `primitives/releases/vX.Y.Z` from `73ae469` (not from the head of `devel`). Run `candidate` with `--release-head` on the head the release will run on, after the release preparation commit. Any pinned file in the difference is a stop.
2. Close the open gates.
3. After the release: `verify-release` with the pinned root, `release_record_conformance.py --repo <repo> --require record,blobs,crypto` on the record, and `record` on the record. Only these together support a receipt that names the release; none of them closes the open gates.
