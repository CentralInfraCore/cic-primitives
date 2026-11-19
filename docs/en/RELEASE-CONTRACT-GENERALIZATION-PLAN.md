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

| Release | Tag commit | Record (blob SHA-256) | Generation |
|---|---|---|---|
| `v0.1.4` | `9d746ede` | `6963dc26...8016` | `release.content_hash` + `sign`, no `cic_countersign`, no envelope field |
| `v0.1.5` | `d59f7d6b` | `284e44bf...4456` | `release.build_hash` + `sign` + `cic_countersign`; no `provenance`, no envelope field: legacy envelope 1 |
| `v0.2.0` | `960ee0f0` | `955fab2d...a57a` | envelope 2 (`provenance` and `release` both `envelope: 2`) |
| `v0.2.1` | `5e8c3219` | `e5d8268a...df63` | envelope 3 (`artifacts`, mandatory `source_commit`) |

Where the rules live today:

* **Hash payload per envelope**: one function, `_release_hash_payload(bundle, envelope_version)` in `tools/compiler.py`. Envelope 1 hashes four members; envelopes 2 and 3 hash the whole bundle except `release.sign`, `release.build_hash` and `cic_countersign`. The rule is already independent of the record kind: it never reads `kind`, `specs` or `artifacts` by name.
* **Record-only, blob and crypto checks of envelope 3**: `tools/release_record_conformance.py` (508 lines, layers `record`, `blobs`, `crypto`). It supports envelope 3 only (`SUPPORTED_ENVELOPE = 3`) and refuses lower ones with `envelope_too_old`; the verification of envelope 1 and 2 records is the compiler's own, unchanged.
* **Structure**: `release.schema.yaml` (JSON Schema). It is `PrimitiveRelease`-specific in three places: `kind` is a constant `PrimitiveRelease`, `specs` is required and non-empty, and `provenance` names the grammar digests. The common parts (`release`, `cic_countersign`, `artifacts`, `provenance.envelope`, `provenance.source_commit`) sit in the same file, not separated from them.
* **Prose**: `docs/en/RELEASE-RECORD-CONTRACT.md` (sections 4 to 12) restates the structure a third time.

So today the structure is described three times (JSON Schema, verifier code, contract prose) and the common and the primitive-specific parts are not separated. That is the situation the plan resolves.

Measured on the four real records, parsed with PyYAML 6.0.3 (`safe_load`): the value trees contain only strings, integers (envelope 2 and 3: 2 and 6 of them), booleans (32 to 34) and one null; no float, no date or datetime, one document each. This is **only the PyYAML side**; the Forms reading of the same files is not measured yet (section 12) and is the first vector of section 8.

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
* The common checks (the table of section 11 of the contract) are run for every kind, in the same order. The type schema is then applied (`kind_schema_violation`, naming the path), and the semantic checks that a schema cannot express stay named verifier checks of the kind.
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

## 5. Interpretation identity (mandatory, fail-closed)

The hash covers the tree that **the defining reader** derives from the record bytes (today the PyYAML tree of the compiler and the verifier, through the canonical JSON of the contract). Relay will read the same bytes with the Forms Go library. A record is admissible only if both readers derive **the same typed value tree**.

**Definition.** For a record file `F`, let `T_def(F)` be the typed tree of the defining reader and `T_form(F)` the typed tree of the Forms reader (Rust and Go; they must also agree with each other). Interpretation identity holds when, node for node:

1. **Keys**: the same set of keys at every mapping, the same key **type** and text (the key `yes` read as a boolean is a different key from the string `yes`; `1` and `"1"` differ; a duplicate key is a defect in itself, because a reader that keeps the last one derives a different tree from one that refuses).
2. **Structure**: the same node kind (mapping, sequence, scalar), the same sequence length and order, the same presence: an absent member, a null, an empty string and an empty collection are four different things; no aliases, merge keys, tags or extra documents that one reader expands and the other does not.
3. **Value types and values**: the same type (null, boolean, integer, string) and the same value at every scalar.

**Closed domain as well.** The domain of a record is closed to null, boolean, integer (absolute value at most 2^53 - 1) and string. A float, a date, a timestamp, a binary or any other type is refused (`value_type_unsupported`) before any comparison. The closed domain narrows what is compared; it does not replace the comparison (a boolean read as a string stays inside the domain and still differs), which was the finding of review F1 of the fit survey.

**Fail-closed.**

* A difference is refused with `reading_differs`, naming the dimension (`reading_key_differs`, `reading_structure_differs`, `reading_value_differs`) and the path of the first node that differs.
* A reader that is not available is not a pass: the layer is reported **not run** and the result incomplete, and a caller that needs the layer says so explicitly (the reference verifier's `--require`, as for the counter-signature). There is no mode in which the condition is skipped silently.
* The check runs on the bytes of the file as shipped, not on a re-serialization of the tree.

**Effect on existing records.** The records `v0.1.5`, `v0.2.0` and `v0.2.1` are not rewritten, so their identity is whatever the bytes give. The decision rule is fixed in advance, so that it cannot be bent after the measurement:

* The first conformance vector of each existing record measures `T_def` against `T_form` and freezes the result and the expected verdict of the record's **own** verifier.
* If all measured records satisfy the condition, it becomes part of the contract for envelope 3, for every kind.
* If a real record does not satisfy it, work stops and the owner decides between a frozen, record-bound exception (exact paths, bound to the record's blob digest) and a new envelope number. It is not decided here and it is not decided silently by an implementer.

## 6. Backward compatibility

* No record of any generation is edited, re-canonicalized, re-signed, migrated or "upgraded". A verifier change that alters the verdict of one of them is a failing test.
* Each generation stays verifiable under **its own rules**: the hash payload of its envelope (`_release_hash_payload` per envelope version), the checks that verifier of that envelope runs. The generalization adds a kind dimension and does not touch those functions' behavior for the existing records.
* A **frozen golden vector per existing record** is part of the vector plan (section 8): the record's blob digest (table in section 2), the recomputed `build_hash` equal to the recorded one, and the verdict of its own verifier, taken from the tag, not from a copy. `v0.1.4` is included as a generation of its own even though it is not in the owner's list, because the survey found it; its own verification path is listed in section 12 as not examined.
* "Verifiable" means integrity, signature and counter-signature as those verifiers define them. It does not mean trusted: certificate validity (the chain ends on 2026-12-31 13:22:39 UTC at the earliest link) and every trust gate stay with their own work packages.

## 7. Derived representations: automatic conformance check (planned)

For every representation derived from the normative set (at least the generated JSON Schema, and any generated prose table or reason index), CI runs a check that fails the build, planned as four parts:

1. **Reproducibility**: regenerate from the normative set; the result is byte-identical to the committed file. A hand edit of a derived file is a red build, as is a stale one.
2. **Field-set equality**: the set of paths and their types in the derived representation equals the set in the normative schema, in both directions (nothing missing, nothing extra).
3. **Verdict equivalence**: the complete vector set (section 8) is judged by the normative validator and by each derived representation; every accept or reject agrees. Where a representation cannot give the same verdict (for example a constraint only a named semantic check enforces), the vector is marked and the difference is listed, not hidden.
4. **Planted defect**: for each representation, one rule is altered in the normative set and, separately, in the derived file; the check must turn red both times. A check that has never been shown to fail does not count (the blind-spot rule of this ecosystem).

The check lives next to the vectors and, like them, is frozen in the yardstick list (`FROZEN.sha256`, `AMENDMENTS.yaml`) when it is written, so it cannot move under the change it judges.

## 8. Conformance vector plan

All vectors are **planned here and written in a later step**. Each states: id, class, input bytes, expected reason (read, not only the exit status), and the readers that run it (PyYAML verifier, Forms Go, Forms Rust). Each negative vector is also shown refused by a planted-defect run (the vector turns green when the check is removed).

| Class | Positive | Negative | Mutation |
|---|---|---|---|
| Existing records | the four real records: blob digest, recomputed `build_hash`, own verdict (section 6) | a one-byte change to each record (fails integrity under its own envelope) | the same one-byte changes on the signed record without recomputation |
| Common envelope | the golden set of contract section 12, carried over unchanged | every reason of contract section 11, one defect each | the signed-record mutations of contract section 12 (path, digest, entry added, removed, exchanged, `source_commit`) |
| Kind | a golden `PrimitiveRelease` and a golden `ModuleRelease` | `kind` absent, not a string, unknown; `specs` on a `ModuleRelease`; a required kind member absent; an unknown member | `kind` changed in the signed record (integrity must fail) |
| Interpretation identity | records whose both readings agree on keys, structure and values | **keys**: `yes:`, `1:`, `null:` as keys; a duplicate key (PyYAML keeps the last: measured). **Structure**: anchor and alias, merge key `<<` (measured: PyYAML expands both), a tag such as `!!str`, two documents, a BOM, absent versus null versus empty. **Values**: `yes`, `no`, `on`, `off`, `1_000`, `0x10`, `010` (measured: PyYAML reads 8), `1:30` (measured: 90), `1.0`, `1e3`, `.inf`, `~`, an unquoted date, an unquoted timestamp, an integer above 2^53 | a defect planted in each comparison (keys, structure, values) turns the matching vectors green |
| Derivation | regenerated file equal to the committed one | a hand-edited derived file; a stale one | a planted rule change in the normative set and in the derived file (section 7) |

The scalar lines above are the PyYAML side as measured in this survey (`PyYAML 6.0.3`). The expected result per row on the Forms side is **to be measured in the vector step** with the Rust and Go readers, not assumed; the fit survey's probe (10 cases, identical Rust and Go) is the starting point for the scalar rows.

## 9. What this plan asks of the later steps, and what it does not

* The vectors and the reference verifier extension exist, and fail where they must, **before** any compiler or verifier change (the sequence the contract already fixes, section 14).
* The type-schema set is written and measured against the grammar (which constraints are expressible) before the JSON Schema is derived.
* The emitter of the second producer is built only against the accepted vectors and the accepted type schema.

It does not ask for: a new Form capability, a Relay-owned structural validator, a change of the signing mechanism, a rewrite of an old record, a decision about the grammar pin or the trust policy.

## 10. Open points for the review

| # | Question | Recommendation |
|---|---|---|
| O1 | Are `createdBy` (developer identity block) and `validity` common members? | `createdBy` common (the certificate is bound in `build_hash` for every kind); `validity` common as a block, its content kind-neutral. A review decision, because changing it later changes the common part. |
| O2 | The rule if a real record fails interpretation identity (section 5) | stop and ask the owner; never decided in the implementation. |
| O3 | The integer limit 2^53 - 1 and the ban on floats | accept; no real record uses a float; a later kind that needs one needs a reviewed extension. |
| O4 | Which current structural constraints the grammar cannot express | measured in step 2 before the schema is written; a missing *general* capability goes to the Forms gap process. |
| O5 | The profile dependency (section 4) | the normative set is marked provisional; settling the pin is the separate work package. |
| O6 | Where the `ModuleRelease` type schema lives | in this repository, in the same normative set, so one contract has one home; its content comes from the module release plan. |
| O7 | Who may add a kind | a reviewed change of the type-schema set; the issuing entitlement is checked by the countersigner, not here. |

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
