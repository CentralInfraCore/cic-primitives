# Release candidate pre-check

`tools/release_candidate_precheck.py` answers one question before a release is cut, and again after: **does the release contain the grammar that a consumer pinned?**

The consumer (`cic-primitive-forms`, `corpus/pins.yaml`) pins a commit and the SHA-256 of the raw blob bytes of exactly twelve files. A receipt may name a release only if that release provably holds those twelve files. The tool proves or refutes that from git objects and, after the release, from the release record. It reads. It signs, tags and publishes nothing, and it does **not** verify a signature: that stays with `python tools/compiler.py verify-release <record> --trust-root <root.pem>`. Cryptographic origin and "the signed claim covers the pinned grammar" are two questions, and neither stands in for the other.

## Modes

```
release_candidate_precheck.py candidate --manifest PINS --pin NAME [--commit SHA] [--release-head SHA] [--devel REF] [--version X.Y.Z] [--release-date YYYY-MM-DD]
release_candidate_precheck.py record    --manifest PINS --pin NAME --record release/<name>-vX.Y.Z.yaml
```

**candidate** (before the release). The pinned commit exists and is on `devel`; the twelve files at it are byte-identical to the manifest; the manifest digest and the pin name recompute; the commit the release will actually run on (`--release-head`: the release branch head, or the merge commit on `main`) holds the same twelve files; the version is a valid next increment (the rule of `compiler.py`); the files in which `devel` has moved on since the pin are listed.

**record** (after the release). The record's `provenance.source_commit` holds the twelve files byte-identical to the manifest, **and** the record carries its own digest of every one of the twelve. The second is a release requirement (decision of 2026-11-01): `source_commit` identifies and retrieves the source state and stays mandatory, but it does not replace the file digests; the record has to carry the digest values and their algorithm itself, so that verifying the twelve files does not depend on a git object being reachable later. Where the record keeps them is the record contract, which is not decided here; the tool reads the places that exist (the schema sources in `specs`, the two files of `provenance.grammar_*`) and invents no field.

Exit status 1 when a hard check fails. `OPEN` lines are gates the tool does not and cannot close; they never turn into a pass.

## What was measured (2026-11-01, against the pin `cic-primitives-73ae469-6a188078`)

* `candidate` on `73ae469` with `--release-head 73ae469`: all checks pass, 12 of 12 files byte-identical. `devel` (`d27173f`) **has moved on in `proposals/atom-grammar/P0-4-MIGRATION.md`**, a pinned file: **a release cut from the head of `devel` is not the pin.** The release has to run on a branch cut from `73ae469`, or the pin has to move.
* `candidate` with `--release-head` set to the head of `devel`: FAIL on that file.
* `record` on `release/cic-primitives-v0.2.0.yaml`: FAIL. Its `source_commit` (`9c67ea4`) lacks 4 of the 12 files and holds 5 others with different bytes; the record's own digests of `check_grammar.py`, `instance-grammar.schema.yaml`, `policy-surface.yaml` and `access.yaml` do not equal the pinned files. This is the refutation of `v0.2.0` as the release of the pin, now by a repeatable tool.
* In `v0.2.0` the record digests 2 of the 12 files itself and equal (`role.yaml`, `shape.yaml`); 4 more are digested by name but with other bytes; 6 have no digest in it. With the present compiler a record can digest **at most 6 of the 12 by construction** (the schema sources and the two grammar files), so a new release cannot meet the 12-of-12 requirement until the record contract changes. That is why `candidate` keeps `record digest coverage` as an OPEN gate and `record` fails a record below 12 of 12.
* The negative evidence on `v0.2.0` is frozen and reproducible: `tests/fixtures/forms-pin-73ae469.yaml` is a copy of the consumer's pin, and `test_release_v020_does_not_hold_the_pinned_grammar` asserts the 4 absent files, the 5 files with other bytes, the 4 wrong record digests and the 2-of-12 coverage (it needs the full history and the tag `primitives/@v0.2.0`; in a shallow checkout it is skipped, not passed). Nothing about `v0.2.0` is corrected or hidden by this tool.

## Profile, readiness and exit status

* **Profile.** `--profile cic-grammar-12` (the default) requires the pin set to be exactly the 12 distinct paths of the CIC grammar pin, fixed in the tool and never read from the manifest it judges; a dropped, added, swapped or repeated file fails, whatever the count. `--profile none` is the general tool and is a stated choice. A recomputed manifest digest shows consistency, not that the manifest comes from the entitled consumer; `manifest origin` is an OPEN gate.
* **Coverage is presence and agreement.** `record digest coverage` is PASS only when every pinned file has a digest in the record **and** each equals the pinned bytes; a present but wrong digest is not coverage and the report never shows a PASS next to it.
* **Readiness.** Exit status 0 is **not** fitness for release. Every run ends with `readiness: failed` or `readiness: checks_passed_gates_open` (also `--json`: `readiness`, `failed`, `open_gates`, `lines`). The tool never returns `ready` while an OPEN gate exists, and none of its OPEN gates is one it can close.
* **Fail-closed history.** Where the gate sets `CIC_REQUIRE_RELEASE_HISTORY=1`, a missing commit, a missing tag and a moved tag are three separate failures with their own messages; only outside that mode is the evidence test skipped.

## What a PASS means, and what it does not

The tool proves, from git objects and the record: the pinned commit exists and is on `devel`; the twelve files are byte-identical to the manifest at the commit the release runs on; the manifest digest and the pin name recompute; the version is a valid increment; and (record mode) the record carries its own digest of each of the twelve and they equal the pinned bytes.

A `12/12 PASS` is **not** a statement that a release is genuine. It does not show who may sign, that the countersignature authorizes a release, that the certificates are trusted or valid on the release day, or that the digest encoding is the receipt's. Those are the open gates below; they are printed as `OPEN` on every run and cannot be turned into a pass by this tool. Every run also ends with a `scope` line saying so.

## The candidate `73ae469` is not the head of `devel`

The candidate is the pinned commit `73ae469`. `devel` has moved on since (`d27173f`, and `P0-4-MIGRATION.md`, a pinned file, differs there). A pull request that targets `devel`, such as the one that adds this tool, gives no authority to cut the release from the current head of `devel`: a release cut there is not the pin, and `candidate --release-head <that head>` fails on the changed file. The release runs on a branch cut from `73ae469`, or the pin moves; the former is the owner's chosen direction.

## Open gates (not checked by this tool)

0. **Record digest coverage:** the record carries its own digest of all 12 pinned files and the algorithm (see above); open until the record contract meets it.
1. A CIC root pinned **outside** the record (`verify-release --trust-root`).
2. Signer authority: the release issuer certificate is not chained to anything in the record; whether the countersignature alone authorizes a release is not decided.
3. Certificate validity at the release date (the certificates of `v0.2.0` expire 2026-12-31).
4. The digest encoding: the record writes base64, a receipt takes `sha256:` and hex. The tool re-encodes for its own comparison only; the contract and Rust/Go golden tests are a Forms unit.
5. Signing and publishing: on hold by the owner until the gates above are shown.

## Sequence this tool supports

1. Cut `primitives/releases/vX.Y.Z` from `73ae469` (not from the head of `devel`). Run `candidate` with `--release-head` on the head the release will run on, after the release preparation commit. Any pinned file in the difference is a stop.
2. Close the open gates.
3. After the release: `verify-release` with the pinned root, and `record` on the record. Only both together support a receipt that names the release.
