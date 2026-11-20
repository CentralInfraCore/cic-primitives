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
* **Composition** (`composition.yaml`, `compose.py`; the rules, not yet a production tool): a kind part **adds** members and never removes, relaxes or redefines a common one; a composite with the same name at the same path is merged by adding the kind's fields **only if every other attribute of the two composites is identical** (`mandatory`, `optional`, `nullable`, `contract`, ...; the kind part restates them, so nothing can be relaxed, added or dropped silently); a duplicate field name inside one part, a kind-part member outside `spec.identity` / `spec.config_surface`, an unknown `config_surface` key and a different `aggregate_ref` are errors too; every other overlap is a collision, a composition-time error `schema_field_collision`, never a verification result; the surface-level `validation` entries are concatenated. The kind constant is declared by the kind part, not by the common part.
* Every part is itself a valid composition instance; the composed schema of each kind is generated, never edited.

## 4. Contract declarations and the conformance declaration

The parts declare **21** `contract` entries: 17 on nodes (patterns for `version`, `timestamp`, the dates, the commit, the digests, the hashes and the signatures; a `range` `3..3` for the two envelope numbers; an `enum` for `signed_payload`) and 4 at the surface (`must`). Patterns use only a plain syntax (no look-around), because the regular-expression flavor of the `pattern` type is not specified by the grammar (open point, section 7). Rules that a pattern could not carry stay named verifier checks (`artifact_path_form`, `artifact_order`, the recomputations, the signatures, the admission-profile checks), listed in `verifier_only`; none of them is a contract entry.

`contract-conformance.yaml` declares, for every contract entry: its place, type and expression; the **Form status** (`unevaluated` for node entries, `not_reported` for surface entries); the **verifier status** with the reasons that cover it; and the planned vector class. **Every normative requirement has a named owner and an explicit status**: `implemented` (the reference verifier makes the check today: the reason is in the contract's section 11 table or the blob layer), `planned` (named by the generalization plan, no code), `implemented_draft` (the draft composer), or `not_implemented` (no executor; it needs a note, no reasons). The declaration also lists `further_requirements` (V01-V07: rules a schema cannot express, such as the path form, the order, the recomputations, the blob layer) and `global_requirements` (G01-G04): G01 interpretation identity, **G02 the closed value domain with the 2^53-1 integer bound over the whole value tree, opaque member contents included (not only the declared integer fields)**, G03 the pre-tree rules, G04 the composition rule. `check_declaration.py` checks: (1) every contract of the parts is declared exactly once and the reverse (a duplicate in the parts is an error, not an overwrite); (2) the parts carry no evaluation status; (3) the Form status against the probe output (17 and 13 listed nodes for the two kinds, no surface entry listed); (4) every requirement has an allowed status, `implemented` only for reasons the reference verifier makes, `planned` only for plan reasons, an `implemented` or `planned` entry has reasons, a `not_implemented` entry has a note and none; (5) **inventory accounting**: each of the 35 known reason identifiers (the contract table, the blob layer, the plan's kind, composition and admission-profile reasons) has at least one owner in the declaration, so removing an owner is an error, and G01-G03 and the 2^53-1 statement of G02 are present. `selftest_declaration.py` (30 checks) accepts the real set and refuses 28 planted defects, each with its own reason (18 in the declaration and the probe evidence: removed contract and owners, weakened G02, status misuse, a duplicated contract; 10 in the composition: collisions, attribute conflicts, duplicate names, an unknown key, a different aggregate_ref), and shows a kind part adding a field to `provenance` being merged.

## 5. Evidence

* **Grammar conformance**: the pinned grammar's own checker (`check_grammar.py`, self-test 53/53) accepts `primitive-release.yaml` and `module-release.yaml` and finds in `common.yaml` and in both composed schemas **exactly three findings, all the node name `createdBy`**. Every other construct of the drafts (the contracts, `optional`, the list key, the opaque field, the surface-level `validation`, an empty `nodes` list in the module part) conforms to the grammar.
* **Form probe** (Forms `2f02a75`, profile `cic-primitives-73ae469-6a188078`; Rust and Go byte-identical; 4 cases, 26 documents, all accounted for): both composed schemas compile. Every conforming document is accepted: the sanitized published `v0.2.1` shape, one without the counter-signature, a `ModuleRelease` record. Every structural defect is refused: a missing `source_commit`, a missing `specs`, a missing grammar digest, an unknown top-level or provenance field, a duplicate artifact path (`PATH_DUPLICATE_IDENTITY`), an empty `files`, an envelope written as a string, a counter-signature without its authority, a `specs` member or a primitive provenance field on a `ModuleRelease`, a missing `kind`, a primitive record against the module schema and the reverse. The kind parts therefore do not mix.
* **What the Form does not evaluate** (recorded, `inf_` documents, accepted): a bad `version`, a bad `source_commit`, a `kind` of `Other`, a bad digest form, an envelope `4`, unsorted artifacts, a `ModuleRelease` that names the wrong kind or lacks `module/module.wasm` or `project.yaml`. These are exactly the contract entries and verifier checks of the declaration.
* **New finding, not decided here**: the Form lists the 17 node-level contracts as unevaluated but **neither evaluates nor lists the 4 surface-level `validation` entries** (the `must` contracts of the kind parts): it drops them silently. It is the same kind of finding as FG1 (a declared construct that has no visible effect) and belongs to the Forms. Review decision on #38: the native declarations stay in the draft; a separate Forms issue is opened (draft prepared, `ISSUE-DRAFT-forms-surface-validation`); **finalization of the schemas stays on hold until the responsibility and the visibility of the surface-level checks are settled**; no local hidden second validator is added to work around it. Until then the declaration lists these four entries as `not_reported`, and each has a named verifier executor (`kind_missing`, `kind_unsupported`, `kind_schema_violation`) or is `planned`.

## 6. D1: preparing the grammar change (not made here)

The pinned grammar limits a node name to `^[a-z][a-z0-9_]*$`; the records `v0.1.5`, `v0.2.0` and `v0.2.1` have `createdBy` (at `/createdBy` and `/release/createdBy`). By the decision, the rule is changed in the grammar, as a separate issue and pull request, through a **versioned grammar profile**; the Form gets no `createdBy` exception; the records, the field names and the hash input stay as they are. What the preparation fixes, before the issue is opened:

* the change is to the **general** name rule, not to one name; which new rule (for example admitting an upper-case letter after the first character) is the question of the grammar issue, with its consequences for every existing schema and for the Forms' pinned profile;
* the Forms carry the profile identifier `cic-primitives-73ae469-6a188078`; a new profile is a Forms work package of its own (the pin work package), not part of this one;
* until the rule is settled, `check_grammar.py` reports the three `createdBy` findings and is the **finalization gate** of the schemas: the drafts are final only when it reports none.

A draft of the grammar issue is prepared (not opened).

## 7. Open points

| # | Question |
|---|---|
| P1 | The regular-expression flavor of the `pattern` contract is unspecified. **Review decision:** a versioned grammar decision with Rust-Go-Python conformance vectors; the patterns are not final before it. |
| P2 | The expression dialect of the `must` contract. **Review decision:** a separate grammar specification; no implicit XPath/JPath mixture. The draft expressions are placeholders until then. |
| P3 | Where the composition rule lives. **Review decision:** it is defined in the release contract; the composer only executes it. |
| P4 | `timestamp` pattern stricter than `format: date-time`. **Review decision:** not tightened silently; a separate A-profile decision. The draft pattern (C02) is marked provisional by this point. |
| P5 | The module part without members. **Review decision:** `artifacts.files` binding is enough for now, no redundant pointers; the draft must be compared with the module release plan (done below). |
| P6 | Nullable provenance digests. **Review decision:** stays as the current contract says; tightening is a separate decision. |
| P7 | New: the plan names no distinct reason for an integer beyond 2^53-1 under profile A; `value_type_unsupported` is used in G02 until the owner decides. |

**P5 comparison with the module release plan** (`CIC_Relay` `docs/en/concept/module-release-record-plan.md`, head `1bd2acd`, "Record members" and "Contract boundary"): consistent: `kind: ModuleRelease`, `validity`, `createdBy`, `provenance{envelope: 3, source_commit}`, `artifacts`, `release{envelope, createdBy, build_hash, sign}`, `cic_countersign`, no `specs`, per-kind schema sharing a common part. **Two differences, not decided here:** (1) the plan lists a top-level member **`name`**; the published `v0.2.1` record and the common part have **no** top-level `name` (only `createdBy.name`), so the draft schema would refuse a plan-conforming record as an unknown field; the plan or the contract needs the correction, and the owner decides which; (2) the plan keeps "`module/module.wasm` and `project.yaml` must be declared" as a **producer-side rule on the declaration, not on the record**, while the draft states it as two record-level `must` contracts on the module part (a verifier-side consequence the plan's open question asks about); the owner decides whether these stay as record contracts.

## 8. Not verified in this document

* The schemas were **not** run against the four real records in full (the probe uses the sanitized `v0.2.1` shape only; `v0.1.4`, `v0.1.5`, `v0.2.0` are envelope below 3 and are not meant to conform).
* The `pattern`, `range`, `enum` and `must` expressions were checked for grammar conformance only; no reader evaluates them.
* The Form's behavior under other commits or profiles; the effect of a new grammar profile.
* That the module part (no members) is what the module release plan needs: compared on paper only (P5 above); the two differences are open.
* That the 35 reason identifiers are the complete set of checks the contract needs: the inventory is the contract's section 11 table plus the plan's named reasons; a check no document names is not found by the accounting.
* No CI ran on this document at the time of writing.
