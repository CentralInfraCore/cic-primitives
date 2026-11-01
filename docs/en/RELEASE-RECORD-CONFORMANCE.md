# Release record contract, envelope 3: conformance vectors and reference verifier

Companion of `docs/en/RELEASE-RECORD-CONTRACT.md` (the contract, section numbers below are its). This change adds the yardstick; it changes **no** compiler, no pre-check, signs nothing and publishes nothing. When the compiler is changed, its output has to meet these vectors: the compiler does not get to say that its own output is right.

## What is here

| File | What |
|---|---|
| `tools/release_record_conformance.py` | the reference verifier. Read-only: it creates no record, signs nothing, publishes nothing, writes no source data; git is only asked to list and print objects |
| `tests/fixtures/envelope3/` | the golden record, its canonical bytes and the expected values |
| `tests/e3_fixtures.py`, `tests/e3_vectors.py` | test-only keys, a second implementation of the rules, the git fixtures, the vectors as data |
| `tests/test_release_record_conformance.py` | the golden and negative vectors, the signature coverage vectors, the layer tests, the command line |
| `tests/e3_mutants.py`, `tests/test_release_record_conformance_planted.py` | the planted-defect proof |

## Three layers, reported apart

`python tools/release_record_conformance.py RECORD [--repo PATH] [--require record,blobs,crypto] [--json]`

* **record**: the record alone (sections 4 to 8 and 11, the structural reasons). No git, no signature.
* **blobs**: each artifact digest against the git tree of `provenance.source_commit` in `--repo`. `NOT_RUN`, with the reason, when no repository is given or the commit is not in it (section 11: an addition to the record's own evidence, not a condition of it).
* **crypto**: the checks inherited from envelope 2, with the functions of `tools/compiler.py` itself (`_release_hash_payload`, `_verify_cert_signature`), not a model of them: `release.build_hash` recomputed over the whole bundle, `release.sign` and `cic_countersign` verified over it. The three are reported one by one, and all three are always run, so one failure does not hide another. The layer is `PASS` only when all three pass; an absent counter-signature makes it `INCOMPLETE`.

The success of one layer is never taken for the success of another, and there is no overall verdict: the output ends with what is **not** proven (who signed; authenticity; fitness to publish; the layers that did not run). Exit status 1 on any `FAIL`; `--require` makes a named layer that is not `PASS` exit with 3.

`validate_declaration(project, tree)` is the producer-side counterpart (section 6): a pure function over a parsed `project.yaml` and a tree listing; the rule the compiler has to agree with. It does not read the working directory.

## Where the expected values come from

Not from the code under test. The three artifact digests and the manifest digest are the worked example of the contract (recomputed with `sha256sum`); the canonical bytes of the golden record, its SHA-256 and `build_hash` were recomputed with `sha256sum` and `openssl dgst -sha256 -binary | base64`; the source commit of the worked example was recomputed with plain `git write-tree` and `git commit-tree` with a fixed author, date and message. `tests/e3_fixtures.py` holds a second implementation of the rules (`independent_*`) used to re-authenticate mutated records, and a test compares its canonical bytes with the compiler's.

The keys are test-only and derived from fixed labels, so the committed certificates and signatures belong to keys that can be re-derived in the tests (no private key file exists). The certificates are valid until 2125-12-31, so the date check inside the existing signature check never decides a vector.

## Signature coverage (section 12)

The series applies one defect at a time to the **signed** record: an artifact path, a digest, the count (one added, one removed), the order, `provenance.source_commit`, `artifacts.manifest_digest`, and a `specs[].meta_hash`; then:

1. nothing recomputed: `build_hash_mismatch` (the two signatures still verify over the stale hash they were made for, which is why the recomputation of `build_hash` is the check that carries the proof);
2. `build_hash` recomputed, nobody re-signed: `signature_invalid` and `countersign_invalid`;
3. `build_hash` recomputed and `release.sign` valid, counter-signature stale: only `countersign_invalid`;
4. `build_hash` recomputed and the counter-signature valid, `release.sign` stale: only `signature_invalid`.

The control of the series: the same defect, re-authenticated, is a validly signed record; the crypto layer cannot judge content, so the failures above are the staleness of the signature and nothing else. A further test lists the members whose change moves the hash and the three that must not.

## Planted defects

Two series, in `tests/test_release_record_conformance_planted.py`. (1) Each record check is switched off in turn, and each reason it owns must lose a vector; the same for the three crypto checks. (2) 68 small breaks, 8 of them documented as equivalent, in the verifier source (`tests/e3_mutants.py`): the targeted vector must be among the failing tests (a break that fails only an unrelated test does not count), and the mutants that cannot change behaviour are listed with the reason and **have to survive**. The equivalent ones: a leading or trailing slash and the empty string (the segment test refuses them with the same reason), code-point order against UTF-8 byte order (the same order), the order test against equal neighbours (the duplicate test runs first), the git object type against the mode, the submodule mode taken alone, `--full-tree`. UTF-16 order is not equivalent and has its own vector pair (U+FF5E and U+10000).

## Where the contract is silent or ambiguous (not changed here; for the next contract revision)

1. `artifacts.manifest_digest` absent or not of the form `sha256:` and 64 lowercase hexadecimal digits has no named reason. The verifier reads it as `artifact_digest_form`.
2. A real envelope 1 record omits the envelope fields (`release/cic-primitives-v0.1.5.yaml` has none; the envelope 2 verifier defaults to 1). Section 11 sends "both absent" to `envelope_unsupported`, so a real v1 record is `envelope_unsupported`, not `envelope_too_old`; only a record that states the envelope 1 reaches `envelope_too_old`.
3. An absent `cic_countersign` is not a refusal in the contract. The verifier reports `NOT_RUN` for that check and `INCOMPLETE` for the layer, never `PASS`.
4. Section 11 says a record that fails an earlier check "is not examined further". The verifier applies that inside the record layer and as the envelope gate of the crypto layer; the crypto layer is otherwise independent of the record layer (a record that fails `artifact_order` is still checked for `build_hash_mismatch`), which is what lets the coverage vectors show each cryptographic check alone.
5. `countersign_invalid` here is the signature over `build_hash`. The chain of the authority certificate to the root it carries, and the pinned root, are trust gates (section 2) and are not checked.

## Not in this change

The compiler change, the move of the pre-check to `artifacts.files`, the trust gates, signing and publication. The release candidate `73ae469` is untouched.
