# Release record contract generalization (plan, draft for review)

Status: **draft for review, documentation only.** This document changes no contract text, no schema, no compiler, no verifier and creates no vector file. Implementation starts only after this plan is reviewed (section 11). The Forms grammar pin and the D4 trust policy are separate work packages and are not decided here.

Key words MUST, MUST NOT, SHOULD and MAY are used as in RFC 2119. The normative text of the envelope 3 contract stays `docs/en/RELEASE-RECORD-CONTRACT.md`; this plan says how that one contract is made to carry more than one record kind.

## 1. Purpose and fixed starting points

A second producer (the base-repo release emitter for WASM modules, planned in `CIC_Relay` `docs/en/concept/module-release-record-plan.md`) has to issue records of **the same contract**, not of a copy. The owner's acceptance conditions for this plan, in force:

1. One common envelope 3 contract; the hash mechanism is unchanged.
2. The type-specific schemas are built on the existing CIC grammar and the existing Form capabilities.
3. One normative structural description; no second, independently maintained schema.
4. A mandatory interpretation-identity condition, fail-closed, over the **whole typed value tree** (keys, structure, value types).
5. The records `v0.1.5`, `v0.2.0`, `v0.2.1` stay verifiable unchanged. Compatibility does not mean rewriting, re-canonicalizing or re-signing any of them; each stays verifiable under the rules of its own envelope version.
6. A plan of positive, negative and mutation conformance vectors.
7. Where a representation is derived from the single normative schema, an automatic conformance check is planned.

Out of scope: the Forms grammar pin (a development profile becoming a production release pin), the D4 trust policy, the emitter, any Relay change, any new Form capability, the trust gates of the contract (section 2 there).

## 2. Survey (what exists now)

Sources: `cic-primitives` `devel` at `01cb30b`, and the tags below, in a full clone with tags. Everything here was read or run; what was not is in section 12.

| Release | Tag commit | Record (blob SHA-256; the closed H list of section 6) | Generation |
|---|---|---|---|
| `v0.1.4` | `9d746ede` | `6963dc26a9b342d3455fcb1b24363c118b450184a886d3a89a68b3db33008016` | `release.content_hash` + `sign`, no `cic_countersign`, no envelope field |
| `v0.1.5` | `d59f7d6b` | `284e44bfcf62d79f782d6cae359c4c99ef2f5297f6f71dcea52a95d28b8c4456` | `release.build_hash` + `sign` + `cic_countersign`; no `provenance`, no envelope field: legacy envelope 1 |
| `v0.2.0` | `960ee0f0` | `955fab2d6d9638c773f29fbe97a3279f9f10b9539c4e3e79957df0acef9a57a6` | envelope 2 (`provenance` and `release` both `envelope: 2`) |
| `v0.2.1` | `5e8c3219` | `e5d8268aede0d24f02e60a151099a2fdc7615172ed3105b0a05b6b5d19addf63` | envelope 3 (`artifacts`, mandatory `source_commit`) |

Where the rules live today:

* **Hash payload per envelope**: one function, `_release_hash_payload(bundle, envelope_version)` in `tools/compiler.py`. Envelope 1 hashes four members; envelopes 2 and 3 hash the whole bundle except `release.sign`, `release.build_hash` and `cic_countersign`. The rule is already independent of the record kind: it never reads `kind`, `specs` or `artifacts` by name.
* **Record-only, blob and crypto checks of envelope 3**: `tools/release_record_conformance.py` (508 lines, layers `record`, `blobs`, `crypto`). It supports envelope 3 only (`SUPPORTED_ENVELOPE = 3`) and refuses lower ones with `envelope_too_old`; the verification of envelope 1 and 2 records is the compiler's own, unchanged.
* **Structure**: `release.schema.yaml` (JSON Schema). It is `PrimitiveRelease`-specific in three places: `kind` is a constant `PrimitiveRelease`, `specs` is required and non-empty, and `provenance` names the grammar digests. The common parts (`release`, `cic_countersign`, `artifacts`, `provenance.envelope`, `provenance.source_commit`) sit in the same file, not separated from them.
* **Prose**: `docs/en/RELEASE-RECORD-CONTRACT.md` (sections 4 to 12) restates the structure a third time.

So today the structure is described three times (JSON Schema, verifier code, contract prose) and the common and the primitive-specific parts are not separated. That is the situation the plan resolves.

Measured on the four real records, parsed with PyYAML 6.0.3 (`safe_load`): the value trees contain only strings, integers (envelope 2 and 3: 2 and 6 of them), booleans (32 to 34) and one null; no float, no date or datetime, one document each. This is **only the PyYAML side**; the Forms reading of the same files is not measured yet (section 12) and is the first vector of section 8.

Measured on the raw bytes of the four records: no anchor, alias, tag, merge key, comment, second document or non-string key. Measured on `compiler.py` and the reference verifier: the signature and counter-signature checks compare the **current UTC time** with the certificate validity (section 6), so the cryptographic verdict of a record depends on the verification instant.

## 3. One contract, two layers

The envelope 3 contract stays one contract. Its members are divided into a **common part** and a **kind part**. This is a classification of what is there, not a new design.

| Part | Members | Defined by |
|---|---|---|
| Common | `kind`, `version`, `timestamp`, `provenance.envelope`, `provenance.source_commit`, `artifacts` (`manifest_digest`, `files[]`), `release.{envelope, createdBy, build_hash, sign}`, `cic_countersign`; see O1 for `createdBy` and `validity` | the envelope 3 contract, unchanged |
| Kind part of `PrimitiveRelease` | `specs[]`, `provenance.{dependency_lock_sha256, grammar_sha256, grammar_schema_sha256}` | the type schema of `PrimitiveRelease` (the current content, moved, not changed) |
| Kind part of `ModuleRelease` | to be defined by the module release plan (descriptor and WASM binding, no `specs`) | the type schema of `ModuleRelease` |

Rules of the layering:

* The hash rule is unchanged, byte for byte. A kind part is inside the bundle, so `build_hash` covers it without any change; nothing in this plan edits `_release_hash_payload` or the canonicalization.
* A kind MUST NOT redefine, relax or omit a common member. A type schema adds members; it removes none.
* The verifier reads `kind` first. A `kind` that is absent, not a string, or has no type schema is refused (`kind_missing`, `kind_unsupported`); there is no default kind, because a default is a fallback.
* **Common checks and kind checks are separate lists.** `spec_source_path_duplicate` is **not** common: it belongs to the `PrimitiveRelease` kind, whose members include `specs`. Every other reason of the contract's section 11 table concerns the envelope and the common members and is common to all kinds. A kind's own checks, including the type schema (`kind_schema_violation`, naming the path), judge **the kind's members only**; they never re-judge a common member, which the common checks already refuse with their own reason.
* **One total order, run per layer, as the reference verifier runs it today** (`RECORD_CHECKS`, then the blob layer, then the crypto layer; the first refusal of a layer ends it). Nothing is reordered; the only new entries are marked:

| Layer | Order | Reasons |
|---|---|---|
| (under A only) parse | 0 | pre-tree rules, `key_not_string`, `value_type_unsupported`, `integer_out_of_range`, `reading_differs` (section 5): they run on the raw parse before the record layer; under H they do not exist |
| record | 1 to 3 | `envelope_mismatch`, `envelope_unsupported`, `envelope_too_old` |
| record | 4, 5 | `kind_missing`, `kind_unsupported` (**new**, after the envelope checks, so an old-envelope record is still refused as `envelope_too_old` first) |
| record | 6 to 14 | `source_commit_missing`, `source_commit_form`, `artifacts_missing`, `artifact_path_form`, `artifact_path_duplicate`, `artifact_order`, `artifact_digest_form`, `artifact_manifest_digest_form`, `artifact_manifest_mismatch` |
| record | 15 | the kind's own checks: for `PrimitiveRelease` `spec_source_path_duplicate`, at the position it has today (the last of the record layer); for other kinds `kind_schema_violation` and the kind's semantic checks |
| blobs | after the record layer | `artifact_absent`, `artifact_digest_mismatch`, `artifact_not_regular` |
| crypto | after the blob layer | `build_hash_mismatch`, `signature_invalid`, `countersign_invalid` |

  For a `PrimitiveRelease` record the sequence of checks and the reason of any refusal are exactly those of today; no existing verdict can change.
* **A kind never overrides the common rules**, and composing the common schema with a kind schema fails **at composition time** (`schema_field_collision`, a build error, never a verification result) when a kind member has the same path as a common member.
* **`cic_countersign` is a common member, and its structural status is not the admission policy.** Structurally it is an optional member whose absence a verifier reports as "not run" (contract section 11); that a counter-signature is *required* for acceptance is the admission policy of the trust package. This plan changes neither and must not be read as doing either.
* A kind is added only by a reviewed change to the type-schema set; who may *issue* a given kind is a countersigner-side check (module release plan, section 7), not a verifier-side structural fact.

## 4. One normative structural description

The normative description of the structure is **one set of schemas in the existing CIC grammar**: one for the common envelope and one per kind, each compiled with the existing Form capabilities (`compile_schema`, validation, normalization). The evidence that a representative `ModuleRelease` schema compiles and validates with identical Rust and Go results is `CIC_Relay` `docs/evidence/forms-fit-probe/` (10 cases). Nothing is added to the Forms for this plan.

Everything else that describes structure is **derived** from that set, never edited by hand:

| Representation | Role after this plan | Status |
|---|---|---|
| The CIC-grammar schemas | the only normative structure | new, written in the schema step (section 11, step 2) |
| `release.schema.yaml` (JSON Schema) | kept for existing consumers; **generated** from the normative set for envelope 3; for envelopes 1 and 2 its present content is frozen as the rule of those envelopes and not regenerated | to be derived |
| Prose tables in the contract | explanatory; where a table lists a structural rule it is generated or checked against the normative set | to be checked |
| Verifier code | implements the **non-structural** rules only (order, uniqueness across items, digest recomputation, signature checks) and calls the schema for the rest | to be refactored behind vectors |

A constraint that the grammar cannot express (a regular-expression pattern such as `^sha256:[0-9a-f]{64}$`, a constant, a cross-item uniqueness) is not added to the Forms by this plan and is not duplicated in a second structural description. It stays a **named semantic check** with a reason identifier (the contract already names them: `artifact_digest_form`, `artifact_order`, and so on), listed in the normative set as an index entry. Which constraints these are is measured in step 2; a constraint that is proven to be a missing *general* structural capability goes to the Forms through its own gap process, and is not built into the verifier.

Dependency to state: the schemas can be compiled only under the grammar profile the Forms accept today, `cic-primitives-73ae469-6a188078` (a development profile). The normative set therefore carries that profile identifier and is **provisional** until the pin work package settles a release profile. The plan neither chooses nor changes it.

## 5. Interpretation identity (mandatory for admission, fail-closed)

Two conformance profiles are kept apart throughout this plan (defined in section 6): **H**, the historical verification of a record under the rules of its own envelope, unchanged; and **A**, the **admission profile** for a new record under the generalized contract. Interpretation identity, the closed value domain and the pre-tree rules below belong to **A**. "Admission" here means conformance of the record to this contract; whether a signer is entitled, whether a counter-signature is required and whether the chain is trusted is the trust policy (D4, a separate package), and is not decided here.

The hash covers the tree that **the defining reader** derives from the record bytes (today the PyYAML tree of the compiler and the verifier, through the canonical JSON of the contract). Relay will read the same bytes with the Forms Go library. A record is admitted only if both readers derive **the same typed value tree**.

**Result of the check under A.**

| State | Result |
|---|---|
| Every required reader gives the same typed tree and no pre-tree rule fires | ADMIT (for this check) |
| The readings differ | REJECT |
| A required reader is not available | REJECT |
| The check did not run | REJECT |
| A value type outside the closed domain | REJECT |

`NOT_RUN` and `INCOMPLETE` exist only in a **diagnostic mode** of the verifier. They are never a successful admission, and under A there is no switch that makes the check optional: the `--require` mechanism of the reference verifier (which makes a caller state that a layer must hold) applies to diagnostic runs and to the existing optional layers; it is not how this check is made mandatory. The counter-signature stays what the contract says it is, a structurally optional member whose absence a verifier reports as not run; requiring it is the admission policy (section 3).

**Pre-tree rules (run on the raw parse, before any value tree is built).** Two equal trees do not prove that neither reader lost information, so these are refused first, each with its own reason:

* a duplicate key in any mapping (`duplicate_key`; PyYAML keeps the last one silently: measured);
* an anchor or an alias (`alias_forbidden`) and a merge key `<<` (`merge_key_forbidden`); PyYAML expands both: measured;
* an explicit tag (`tag_forbidden`);
* more than one YAML document in the file (`multiple_documents`);
* an encoding other than UTF-8 without a byte order mark (`encoding_form`).

**Keys are strings, and only strings** (`key_not_string`), judged on the type the reader gives the key before any conversion: the plain key `yes:` is a boolean to PyYAML (measured) and a string to the Forms, so it is refused, not compared.

**Type identity is explicit.** A value is compared as the pair (type, value), never by an equality that crosses types: in Python `True == 1` and `1 == 1.0` hold, and a boolean is not an integer for this contract.

**Definition.** For a record file `F`, let `T_def(F)` be the typed tree of the defining reader and `T_form(F)` the typed tree of the Forms reader (Rust and Go; they must also agree with each other). Interpretation identity holds when, node for node:

1. **Keys**: the same set of keys at every mapping, each a string with the same text.
2. **Structure**: the same node kind (mapping, sequence, scalar), the same sequence length and order, the same presence: an absent member, a null, an empty string and an empty collection are four different things.
3. **Value types and values**: the same type (null, boolean, integer, string) and the same value at every scalar.

A difference is refused with `reading_differs`, naming the dimension (`reading_key_differs`, `reading_structure_differs`, `reading_value_differs`) and the path of the first node that differs. The check runs on the bytes of the file as shipped, not on a re-serialization of the tree.

**Closed domain (A only).** The domain of a record under A is null, boolean, integer in the range -(2^53 - 1) .. +(2^53 - 1) inclusive, and string. A float, a date, a timestamp, a binary or any other type is refused (`value_type_unsupported`) before any comparison. **An integer outside the range is refused with its own reason, `integer_out_of_range`** (decision P7, owner, 2026-11-21: a type error and a range error are two distinct events). The check covers the **whole value tree**, the contents of opaque members included, not only the declared integer fields. It is made by the **producer** (it refuses to emit such a record) **and by the verifier**, and the verifier checks **independently**: it never relies on the producer's result. Decided, not implemented: the reference verifier does not yet make the profile A checks. The closed domain narrows what is compared; it does not replace the comparison (a boolean read as a string stays inside the domain and still differs), which was the finding of review F1 of the fit survey. Records verified under H are not subject to it.

**The existing records.** They are not rewritten. Their A-conformance is **measured and reported** (first vector of each, section 8); it never changes their H verdict. Measured so far on the raw bytes of the four: no anchor, alias, tag, merge key, comment, second document or non-string key; only strings, integers, booleans and one null (PyYAML side). If a measured real record differs under A, work stops and the owner decides; there is no automatic exception, and none is decided by an implementer (O2, accepted).
## 6. Backward compatibility and the two profiles

* **H, historical verification.** Every record of every generation stays verifiable under **its own rules**: the hash payload of its envelope (`_release_hash_payload` per envelope version) and the checks the verifier of that envelope runs. No record is edited, re-canonicalized, re-signed, migrated or "upgraded". The generalization adds a kind dimension and does not change the behavior of those functions for the existing records; a verifier change that alters an H verdict is a failing test.
* **A, admission profile.** What a *new* record must satisfy: the generalized envelope 3 contract plus section 5. A is stricter than what envelope 3 verification admitted. That the four existing records satisfy A (once measured) does **not** show that every envelope 3 document permitted before satisfies it; H keeps verifying those, A governs what is accepted from now on. The two are never merged and a record is never "upgraded" from H to A.
* **H is not a way around A (explicitly forbidden).**
  * Admission has exactly one path, A. The admission entry point has no H mode, and a failure under A is never retried, rescued or reported as acceptable under H.
  * H is selected by the **caller**, never by the record. It applies only to a record on a **closed list**, the four record digests of section 2; an addition to the list is a reviewed change of this contract. A new record that states envelope 1 or 2, or omits `provenance`, to look like a historical one is refused under A (`envelope_too_old`, `envelope_unsupported`); its content never chooses the profile.
  * An H verdict, a pass included, is not an admission result. A report always names its profile, and a consumer, the pre-check tool or a countersigner must not accept an H result in place of an A result.
  * The injectable verification time (below) exists in H only. Under A the certificate validity is always judged at the real current time; the time input cannot be used to get an expired certificate accepted.
  * A historical record from outside the list (for instance one issued by another repository) has no H status until the owner lists it.
* **Four identities, kept apart in every vector.** (1) the raw record bytes (the blob digest); (2) the canonical value tree (the tree the readers derive); (3) the integrity of the members that **the hash actually covers** (the table below); (4) the validity of the signature and the counter-signature. A change to (1) is not necessarily a change to (2): measured on `v0.2.1` with PyYAML, appending a YAML comment and re-spacing a key each change the raw digest and leave the parsed tree equal, so the hash input is unchanged and integrity still holds. "A one-byte change breaks integrity" is therefore **false in general**; and "a change of the tree breaks integrity" holds only for the members of the table.
* **What the hash covers, per envelope, and what detects a change outside it.** A mutation statement in a vector is valid only against this table:

| Envelope | Covered by `release.build_hash` | Not covered, and what detects a change |
|---|---|---|
| 1 (`v0.1.5`) | `createdBy`, `release.createdBy`, `specs`, `validity` | `kind`, `version`, `timestamp` and every other member: **nothing detects a change** (documented in `tools/compiler.py`: a relabelled version verified clean), so the H vector for such a change expects a pass and freezes it; `release.build_hash`: `build_hash_mismatch`; `release.sign`: `signature_invalid`; `cic_countersign`: `countersign_invalid` |
| 2 (`v0.2.0`), 3 (`v0.2.1`) | the whole bundle except `release.sign`, `release.build_hash` and `cic_countersign` | `release.build_hash`: `build_hash_mismatch` (the recorded value against the recomputed one); `release.sign`: `signature_invalid`; `cic_countersign`: `countersign_invalid` |
| `v0.1.4` | its own `content_hash` rule, not examined (section 12) | not stated |

* **The verdict depends on the verification time and on the verifier.** Measured: the signature check calls `compiler._verify_cert_signature` (`tools/release_record_conformance.py:350` and `:366`), which compares the **current UTC time** with the certificate validity (`tools/compiler.py:616-626`); a second function compares certificate and root validity with the current time (`tools/compiler.py:667-680`, its caller not traced). So the cryptographic verdict of every historical record changes at the first expiry although the bytes do not. Each golden vector therefore records the verifier (commit, Python, PyYAML and cryptography versions) and the verification instant it was taken at, plus a vector after the earliest expiry that shows the verdict change. The verifier does not accept an explicit verification time today; making it injectable is a verifier change for step 4, not done here. "Verifiable" under H means integrity and the signature mathematics at a stated instant; it does not mean trusted (the chain ends 2026-12-31 13:22:39 UTC at the earliest link; the trust gates are separate work packages).
* **Generations.** `v0.1.5` (envelope 1), `v0.2.0` (envelope 2), `v0.2.1` (envelope 3) as in the owner's list; `v0.1.4` as a generation of its own: it carries `content_hash` and `sign`, has **no counter-signature** and no envelope field. Its vectors state that the counter-signature layer does not exist for it (absent is not failed); its own verification path was not examined (section 12).
* Whether admission should additionally pin the raw bytes of the record file (the record is not inside its own `artifacts`) is a question for the publication check of the module release plan, not decided here.

## 7. Derived representations: automatic conformance check (planned)

The derived JSON Schema is **never a normative source**: where it and the normative validator disagree, the derived file is the defect. For every representation derived from the normative set (at least the generated JSON Schema, and any generated prose table or reason index), CI runs a check that fails the build, planned in five parts:

1. **Reproducibility**: regenerate from the normative set; the result is byte-identical to the committed file. A hand edit of a derived file is a red build, as is a stale one.
2. **Structural-semantics equality**, not only field sets and types. For every node the derived representation agrees with the normative schema on: mandatory or optional; nullable or absent (a null and a missing member are different); minimum item count; the handling of unknown fields (refused or kept); key identity (the key role of a list item); the boundary between composite objects and scalars. A path or type match with a different answer to any of these is red.
3. **Verdict equivalence**: the complete vector set (section 8) is judged by the normative validator and by each derived representation; every accept or reject agrees.
4. **Inexpressible conditions are declared, and the declaration is checked by a machine.** A condition the derived representation cannot express (a pattern, a constant, a cross-item uniqueness, an order) is listed in a declaration file of the normative set with: the rule, its reason identifier, the named check that enforces it, and the vectors that exercise it. CI fails when (a) a rule differs between normative and derived and is not declared, (b) a declared rule has no negative vector or no planted-defect run, or (c) a declared rule is one the normative grammar does express (it would be a second description). A condition is never left out silently.
5. **Planted defect**: for each representation, one rule is altered in the normative set and, separately, in the derived file; the check must turn red both times. A check that has never been shown to fail does not count (the blind-spot rule of this ecosystem).

If a *general* structural capability is missing from the Forms grammar, that is a Form gap, handled in the Forms; it is not a reason to introduce a Relay-specific or verifier-specific structural solution. The check lives next to the vectors and, like them, is frozen in the yardstick list (`FROZEN.sha256`, `AMENDMENTS.yaml`) when it is written, so it cannot move under the change it judges.

## 8. Conformance vector plan

All vectors are **planned here and written in a later step**. Each states: id, class, input bytes, the profile (H or A), the verification instant where the verdict can depend on it, expected reason (read, not only the exit status), and the readers that run it (PyYAML verifier, Forms Go, Forms Rust).

**What a mutation test means.** With the intact verifier, a defective record is REJECTED with the named reason. With a **deliberately weakened** verifier (the targeted check removed or neutered), the same record is let through by that check, and the test suite therefore fails. Both halves are part of each negative vector. Each check is also shown **in isolation**: the record is built, or the per-check entry point is used, so that only that check can fail; an earlier gate must not be able to mask the absence of the check under test.

| Class | Positive | Negative | Mutation |
|---|---|---|---|
| Existing records (H) | the four real records: blob digest, recomputed `build_hash`, own verdict at the recorded instant; `v0.1.4` with no counter-signature layer | a change to a member **inside** the hash payload of that envelope (table in section 6): `build_hash_mismatch`; a change **outside** it, with the expected result the table gives for that envelope (for `v0.1.5` a change of `kind`, `version` or `timestamp` is frozen as a pass); the same record at an instant after the earliest expiry (the verdict change of section 6) | **non-semantic** changes (comment, re-spacing; measured: tree equal): raw digest differs, tree equal, integrity holds, signature holds; and covered-member changes on the signed record without recomputation |
| Profile separation (A against H) | a record on the closed list verified under H, labelled H | a new record stating envelope 1 or 2, or omitting `provenance`: refused under A; an A failure never turned into a pass by an H retry; an H pass offered as an admission result: refused; the injectable time offered under A: ignored or refused | a planted defect that lets the admission path fall back to H turns the matching vectors green |
| Existing records (A, measured) | the A result of each record (section 5), frozen as measured | none until measured | none |
| Common envelope | the golden set of contract section 12, carried over unchanged, in the existing order and with the existing reason codes | every reason of the common table (section 3), one defect each | the signed-record mutations of contract section 12 (path, digest, entry added, removed, exchanged, `source_commit`) |
| Kind | a golden `PrimitiveRelease` and a golden `ModuleRelease` | `kind` absent, not a string, unknown; `specs` on a `ModuleRelease`; a required kind member absent; an unknown member; a kind member that collides with a common one (a composition error) | `kind` changed in a signed **envelope 3** record (`kind` is inside the hash payload there; integrity must fail) |
| Pre-tree rules and keys (A) | a record with only string keys, one document, no alias | a duplicate key; an anchor and an alias; a merge key; a tag; two documents; a BOM; the key `yes:`; the key `1:`; the key `null:`; a key that is a boolean and one that is an integer (`True` against `1`) | a defect planted in each pre-tree rule turns the matching vectors green |
| Interpretation identity (A) | records whose both readings agree on structure and values | **Structure**: absent against null against empty. **Values**: `yes`, `no`, `on`, `off`, `1_000`, `0x10`, `010` (measured: PyYAML reads 8), `1:30` (measured: 90), `1.0`, `1e3`, `.inf`, `~`, an unquoted date, an unquoted timestamp, an integer above 2^53; a boolean where an integer is expected and the reverse | a defect planted in each comparison (keys, structure, values) turns the matching vectors green |
| Derivation | regenerated file equal to the committed one | a hand-edited derived file; a stale one; an undeclared inexpressible rule; a declared rule without a vector | a planted rule change in the normative set and in the derived file (section 7) |

The scalar lines are the PyYAML side as measured in this survey (`PyYAML 6.0.3`). The expected result per row on the Forms side is **to be measured in the vector step** with the Rust and Go readers, not assumed; the fit survey's probe (10 cases, identical Rust and Go) is the starting point for the scalar rows.

## 9. What this plan asks of the later steps, and what it does not

* The vectors and the reference verifier extension exist, and fail where they must, **before** any compiler or verifier change (the sequence the contract already fixes, section 14).
* The type-schema set is written and measured against the grammar (which constraints are expressible) before the JSON Schema is derived.
* The emitter of the second producer is built only against the accepted vectors and the accepted type schema.

It does not ask for: a new Form capability, a Relay-owned structural validator, a change of the signing mechanism, a rewrite of an old record, a decision about the grammar pin or the trust policy.

## 10. Decisions on the open points

The review of the plan has decided O1 to O7 as architectural decisions, with the conditions below. O1 is treated as a semantic question, not only a structural one, and was decided on the whole document.

| # | Decision | Condition recorded |
|---|---|---|
| O1 | ACCEPT: `createdBy` and `validity` are common | their content is kind-neutral; a kind adds nothing to them |
| O2 | ACCEPT: if a real record differs under A, STOP and the owner decides | no automatic exception |
| O3 | ACCEPT: integers at most 2^53 - 1 in absolute value, floats forbidden | in the **admission profile A** only, not under H |
| O4 | ACCEPT: the grammar's capability is measured | a general gap is handled in the Forms, not in the verifier or Relay |
| O5 | ACCEPT: the development grammar profile is provisional | a release pin is required before production admission |
| O6 | ACCEPT: the `ModuleRelease` schema is normative in this repository | |
| O7 | ACCEPT: a new kind only by a reviewed contract change | the issuing entitlement is a separate trust policy |

## 11. Sequence

1. This plan is reviewed and accepted. **Implementation is on hold until then.**
2. The type-schema step: measure what the grammar can express; write the common and the per-kind schemas; derive the JSON Schema (documentation and tooling PR, no verifier change).
3. The vectors, the extended reference verifier of the record-only layers, the derivation check; the yardstick list is extended; the vectors are shown to fail and to pass.
4. The compiler and verifier refactor behind those vectors (separate PR).
5. The second producer's emitter (separate repository, its own plan).

## 12. Not verified in this document

* The Forms reading of the four real records (Rust and Go) is not measured; only the PyYAML side is.
* Which of the current structural constraints (patterns, constants, `additionalProperties`) the CIC grammar expresses is not measured; the probe covered enumerations, a minimum item count and a key role, not patterns.
* The verification path of `v0.1.4` (`content_hash`) was read for the field names only; whether the compiler verifies such a record today was not run.
* That `json.dumps(..., default=str)` is stable across Python and PyYAML versions (the hash depends on it) was not examined; the measurements here are PyYAML 6.0.3.
* The Hungarian summary is a summary; the English text is the normative source.
* No CI ran on this document at the time of writing.
* The caller of the second validity function (`tools/compiler.py:667-680`) was not traced, so which entry point applies it is not stated.
* Whether an injectable verification time can be added without changing any H verdict was not examined; it is a step 4 question.
* The Forms-side answer to the pre-tree rules (duplicate keys, aliases, merge keys, tags, multiple documents, encoding) was not measured: the Forms may refuse some of them already; the plan requires them of the record under A regardless of the reader.
* The closed H list holds the four records of this repository. Whether other repositories have records issued under envelope 1 or 2 that should be listed was not surveyed here.
