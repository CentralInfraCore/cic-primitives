# Release schema set design (draft: parts, composition, contract declarations)

Status: **design draft, documentation and evidence only.** The schema parts in `docs/design/release-schemas/` are **drafts and are not finalized**: finalization is on hold until the grammar conformance of the node name `createdBy` is settled (decision D1, section 6). Not part of this pull request: the derived JSON Schema, any lint, any compiler or verifier refactor, any change of the Form, any change of the grammar.

Principle in force: **the current capabilities of a consumer must not rewrite the meaning of the normative contract.** The schemas say what must hold, whatever the Form can evaluate today.

## 1. Decisions in force

| # | Decision | Effect here |
|---|---|---|
| D1 | The grammar is to be changed (a versioned profile, a separate issue and pull request); no `createdBy` exception in the Form; no rename, no automatic normalization; the historical records stay unchanged | the schemas are drafted with the name `createdBy` and are **not final** until the name rule is settled; the draft carries no declared violation hidden from view: the checker reports it (section 5) |
| D2 | Native `contract` declarations; the evaluation status is **not** a field of the normative schema; it lives in a separate machine-checkable declaration | section 4 |
| D3 | Only keys the pinned grammar allows and the Form supports or explicitly passes through; an unknown key is forbidden; no local lint | the parts use only grammar keys; a `contract` is allowed though not evaluated |

## 2. The four layers

| Layer | Question | Where it lives |
|---|---|---|
| Normative schema | what must hold? | `common.yaml`, `primitive-release.yaml`, `module-release.yaml` (CIC grammar), composed by `composition.yaml` |
| Form | what can it evaluate? | measured: `docs/en/RELEASE-GRAMMAR-CAPABILITY-MEASUREMENT.md`, the probe of this pull request |
| Verifier | which further checks does it make? | the reason identifiers of `docs/en/RELEASE-RECORD-CONTRACT.md` section 11 and the generalization plan |
| Evidence | what shows the checks ran? | the conformance vectors (planned) and the declaration check |

A later Form that evaluates contracts changes a status in the declaration, never a schema.

## 3. The parts and their composition

* **`common.yaml`**: the members every record kind has: `kind`, `version`, `timestamp`, `validity`, `createdBy`, `provenance` (`envelope`, `source_commit`), `artifacts` (`manifest_digest`, `files[]` with `path` as the list key and `digest`), `release` (`envelope`, `createdBy`, `build_hash`, `sign`), and `cic_countersign`. `createdBy` and `validity` are common (decision O1). `cic_countersign` is **structurally optional** (`optional: true`): that a counter-signature is required for acceptance is the admission policy, not the schema.
* **`primitive-release.yaml`**: adds `provenance.{dependency_lock_sha256, grammar_sha256, grammar_schema_sha256}` (as in the existing schema, a string or null) and `specs[]` (`id`, `source_path` as the key, `meta_hash`, an opaque `spec`, at least one). A surface-level `must` contract states `kind = 'PrimitiveRelease'`.
* **`module-release.yaml`**: no new record members: the shipped descriptor and the WASM bytes are bound through `artifacts.files`. Three surface-level `must` contracts: the kind, and exactly one `artifacts/files` entry for `module/module.wasm` and for `project.yaml`. A `specs` member or a primitive provenance field is **unknown** to it and refused.
* **Composition** (`composition.yaml`, `compose.py`; the rules, not yet a production tool): a kind part **adds** members and never removes, relaxes or redefines a common one; a composite with the same name at the same path is merged by adding the kind's fields (this is how `provenance` takes the kind's fields); every other overlap is a collision, a composition-time error `schema_field_collision`, never a verification result; the surface-level `validation` entries are concatenated. The kind constant is declared by the kind part, not by the common part.
* Every part is itself a valid composition instance; the composed schema of each kind is generated, never edited.

## 4. Contract declarations and the conformance declaration

The parts declare **21** `contract` entries: 17 on nodes (patterns for `version`, `timestamp`, the dates, the commit, the digests, the hashes and the signatures; a `range` `3..3` for the two envelope numbers; an `enum` for `signed_payload`) and 4 at the surface (`must`). Patterns use only a plain syntax (no look-around), because the regular-expression flavor of the `pattern` type is not specified by the grammar (open point, section 7). Rules that a pattern could not carry stay named verifier checks (`artifact_path_form`, `artifact_order`, the recomputations, the signatures, the admission-profile checks), listed in `verifier_only`; none of them is a contract entry.

`contract-conformance.yaml` declares, for every contract entry: its place, type and expression; the **Form status** (`unevaluated` for node entries, `not_reported` for surface entries); the verifier reasons that cover it, or none with a note; and the planned vector class. `check_declaration.py` checks: (1) every contract of the parts is declared exactly once and the reverse; (2) the parts carry no evaluation status; (3) the Form status against the probe output: the nodes the Form lists as unevaluated are exactly the nodes that declare a contract (17 and 13 for the two kinds), and no surface entry is listed; (4) every verifier reason is one of the contract's or one the plan adds; (5) the verifier-only list is not empty. `selftest_declaration.py` (15 checks) accepts the real set, refuses 13 planted defects (ten in the declaration and the probe evidence, three composition collisions), each with its own reason, and shows a kind part adding a field to `provenance` being merged.

## 5. Evidence

* **Grammar conformance**: the pinned grammar's own checker (`check_grammar.py`, self-test 53/53) accepts `primitive-release.yaml` and `module-release.yaml` and finds in `common.yaml` and in both composed schemas **exactly three findings, all the node name `createdBy`**. Every other construct of the drafts (the contracts, `optional`, the list key, the opaque field, the surface-level `validation`, an empty `nodes` list in the module part) conforms to the grammar.
* **Form probe** (Forms `2f02a75`, profile `cic-primitives-73ae469-6a188078`; Rust and Go byte-identical; 4 cases, 26 documents, all accounted for): both composed schemas compile. Every conforming document is accepted: the sanitized published `v0.2.1` shape, one without the counter-signature, a `ModuleRelease` record. Every structural defect is refused: a missing `source_commit`, a missing `specs`, a missing grammar digest, an unknown top-level or provenance field, a duplicate artifact path (`PATH_DUPLICATE_IDENTITY`), an empty `files`, an envelope written as a string, a counter-signature without its authority, a `specs` member or a primitive provenance field on a `ModuleRelease`, a missing `kind`, a primitive record against the module schema and the reverse. The kind parts therefore do not mix.
* **What the Form does not evaluate** (recorded, `inf_` documents, accepted): a bad `version`, a bad `source_commit`, a `kind` of `Other`, a bad digest form, an envelope `4`, unsorted artifacts, a `ModuleRelease` that names the wrong kind or lacks `module/module.wasm` or `project.yaml`. These are exactly the contract entries and verifier checks of the declaration.
* **New finding, not decided here**: the Form lists the 17 node-level contracts as unevaluated but **neither evaluates nor lists the 4 surface-level `validation` entries** (the `must` contracts of the kind parts): it drops them silently. It is the same kind of finding as FG1 (a declared construct that has no visible effect) and belongs to the Forms; no issue was opened for it here.

## 6. D1: preparing the grammar change (not made here)

The pinned grammar limits a node name to `^[a-z][a-z0-9_]*$`; the records `v0.1.5`, `v0.2.0` and `v0.2.1` have `createdBy` (at `/createdBy` and `/release/createdBy`). By the decision, the rule is changed in the grammar, as a separate issue and pull request, through a **versioned grammar profile**; the Form gets no `createdBy` exception; the records, the field names and the hash input stay as they are. What the preparation fixes, before the issue is opened:

* the change is to the **general** name rule, not to one name; which new rule (for example admitting an upper-case letter after the first character) is the question of the grammar issue, with its consequences for every existing schema and for the Forms' pinned profile;
* the Forms carry the profile identifier `cic-primitives-73ae469-6a188078`; a new profile is a Forms work package of its own (the pin work package), not part of this one;
* until the rule is settled, `check_grammar.py` reports the three `createdBy` findings and is the **finalization gate** of the schemas: the drafts are final only when it reports none.

A draft of the grammar issue is prepared (not opened).

## 7. Open points

| # | Question |
|---|---|
| P1 | The regular-expression flavor of the `pattern` contract is unspecified (the `contract.yaml` atomic says "regex"); the drafts avoid look-around, but the flavor must be fixed before the patterns are final. |
| P2 | The expression dialect of the `must` contract is described as XPath or JPath; the drafts use XPath-style `count(...)` and `=`; no reader evaluates them yet. |
| P3 | The composition rule (a composite merged by path) is a rule of this draft, not of the grammar; where it is specified (the grammar, the contract or the composer) is open. |
| P4 | `timestamp` has a pattern here that is stricter than the `format: date-time` of the existing JSON Schema (an annotation); whether to declare it is a review question. |
| P5 | Whether the module part may stay without own members, or the module release plan adds descriptor or WASM pointers to the record. |
| P6 | The provenance grammar digests are mandatory-and-nullable in the primitive part (as the existing schema); whether an envelope 3 record may carry null there is a contract question. |

## 8. Not verified in this document

* The schemas were **not** run against the four real records in full (the probe uses the sanitized `v0.2.1` shape only; `v0.1.4`, `v0.1.5`, `v0.2.0` are envelope below 3 and are not meant to conform).
* The `pattern`, `range`, `enum` and `must` expressions were checked for grammar conformance only; no reader evaluates them.
* The Form's behavior under other commits or profiles; the effect of a new grammar profile.
* That the module part (no members) is what the module release plan needs (P5).
* No CI ran on this document at the time of writing.
