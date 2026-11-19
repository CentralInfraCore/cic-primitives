# Release grammar capability measurement (step 1 and 2 of the generalization plan)

Status: **measurement and gap analysis, documentation and evidence only.** No schema is written here, no verifier or compiler is changed, no Form file is changed, no lint is implemented. It is a pull request of its own (steps 1 and 2 of section 11 of `docs/en/RELEASE-CONTRACT-GENERALIZATION-PLAN.md`); the normative schemas and the derived JSON Schema (steps 3 and 4) follow only after its review.

## 1. What was measured, on what

* **Form**: `cic-primitive-forms` `main` `2f02a75592a4b0894a3b76891e9ba3741479a7c5`, **unchanged**; the library (`compile_schema`, `parse`, `validate`) in Rust (`rustc 1.99.1`) and in Go (`go1.26.11`).
* **Grammar profile**: `cic-primitives-73ae469-6a188078`, the only profile the Forms carry (a development commit; the production pin is a separate work package).
* **Cases**: 25 capability cases, 106 documents, each case a schema plus `pos_` (conforming), `neg_` (the record contract needs it refused) and `inf_` (recorded, no expectation) documents. Source and output: `docs/evidence/forms-capability-measurement/` (generator, both probe programs, `expected-output.txt`, SHA-256 `285ce31a...5c7`).
* **Result of the comparison**: the Rust and the Go output are **byte-identical on all 129 lines**. There is no Rust-Go difference, so the STOP condition did not arise. This is **implementation parity, not evidence of correctness**: two implementations that agree can share the same gap, and several results below are exactly that.

Every result below is bound to those two identifiers. A different commit or profile needs the measurement repeated.

## 2. Capability table

Classes: **supported** (positives accepted, negatives refused, Rust = Go); **not supported, refused** (the Form refuses the schema construct: fail-closed); **not supported, silently ignored** (the Form accepts the construct and does not enforce it: fail-open); **differently read** (the Form's reading of a value differs from the defining reader's, PyYAML, which the hash covers; this is the subject of interpretation identity, not a Rust-Go difference).

| Case | Capability | Class | Measured |
|---|---|---|---|
| K01 | mandatory scalar | supported | absent: `MISSING_MANDATORY@$.a` |
| K02 | optional scalar; null refused unless nullable | supported | absent accepted; `null`: `NULL_NOT_ALLOWED` |
| K03, K04 | nullable, with mandatory and with optional | supported | `null` accepted where nullable; absent mandatory refused; a map at a scalar: `MAP_AT_SCALAR_POSITION` |
| K05 | integer scalar | supported, fail-closed | `5`, `-3`, `+7` accepted; `"5"`, `x`, `true`, `1.5`, `010`, `0x10`, `1e3`, `1_000`, `1:30` refused (`UNSUPPORTED_SYNTAX`, at parse or at validate) |
| K05b | boolean scalar | supported, fail-closed | `true`, `False` accepted; `"true"`, `1`, `yes`, `on` refused |
| K05c | string scalar | supported; **differently read** for some plain scalars | `x` and `"5"` accepted; a map: `MAP_AT_SCALAR_POSITION`; a list, a plain `5` and a plain `true` refused; **`yes`, `2026-05-25` and `2026-11-02T18:57:58+00:00` accepted as strings** (PyYAML reads a boolean, a date, a datetime) |
| K06 | integer range (the plan's admission limit 2^53 - 1) | **not supported, silently ignored** | `9007199254740992`, `9007199254740993` and `9223372036854775807` accepted; only above int64 refused at parse |
| K07 | `min_items` on a list | supported | `[]`: `MIN_ITEMS_NOT_MET`; absent mandatory list: `MISSING_MANDATORY` |
| K08 | `max_items` | **not supported, refused** | the schema is refused: `SCHEMA_SHAPE_UNSUPPORTED@$.files.max_items` |
| K09 | unknown fields refused | supported | `UNKNOWN_FIELD@$.c.y` (nested) and `UNKNOWN_FIELD@$.z` (top) |
| K10 | list item identity by a declared key | supported for identity | duplicate key: `PATH_DUPLICATE_IDENTITY@$.files[{path="a"}]`; missing key: `PATH_KEY_MISSING`; **sorted order, duplicate non-key values and keys differing by case are not constrained** (accepted) |
| K11 | composite against scalar boundary | supported | scalar or list at a composite position refused; `null`: `NULL_NOT_ALLOWED` |
| K12, K12b | a closed value set (`enum`), a constant (`const`) | **not supported, silently ignored** | the schema compiles; `Other` accepted next to `PrimitiveRelease` |
| K13, K13b | a pattern on a string | **not supported, silently ignored** | the schema compiles; `no prefix`, upper-case and short digests accepted; an unconstrained string takes any text |
| K14 | opaque field | supported | map, list and scalar accepted; absent mandatory: `MISSING_MANDATORY` |
| K15 | a set of strings (unique scalars) | **not supported** (not enforced) | `[a, a]` accepted |
| K16 | parse level, before any tree | see section 3 | duplicate key, alias, merge key, tag and second document refused; byte order mark accepted; keys `yes`, `1`, `null` read as text |
| K17a-d | an unknown key on a schema node | **silently ignored** | `foo`, `pattern`, `unique_items` ignored; the misspelled `mandatry` is ignored and the field becomes mandatory (neither presence key means mandatory); `max_items` is the one refused key |

## 3. Parse-level results (K16), against the pre-tree rules of the plan

| Document | Form (Rust = Go) | Plan rule (admission profile A) | Where it must be enforced |
|---|---|---|---|
| duplicate key | refused, `DUPLICATE_KEY` at parse | `duplicate_key` | already refused by the Form; the defining reader (PyYAML) keeps the last one silently, so it needs its own refusal |
| anchor and alias | refused, `UNSUPPORTED_SYNTAX` | `alias_forbidden` | the Form refuses; the defining reader expands them |
| merge key `<<` | refused, `UNSUPPORTED_SYNTAX` | `merge_key_forbidden` | the Form refuses; the defining reader expands |
| explicit tag | refused, `UNSUPPORTED_SYNTAX` | `tag_forbidden` | the Form refuses; the defining reader applies it |
| second document | refused, `UNSUPPORTED_SYNTAX` | `multiple_documents` | the Form refuses |
| byte order mark | **accepted** | `encoding_form` | **not refused by the Form**; must be refused before the readers |
| keys `yes:`, `1:`, `null:` | accepted, read as the **text** `yes`, `1`, `null` | `key_not_string` | **differently read**: PyYAML reads a boolean, an integer and a null; the refusal must come from the defining-reader side |
| comment, flow style, CRLF, leading `---` | accepted | not a defect | none |
| empty document | `NULL_NOT_ALLOWED` at the root | | none |

## 4. Gap analysis

Three groups, as the owner asked.

**Supported by the Form as it is** (usable in the normative schemas): mandatory and optional, nullable against absent, string, integer and boolean scalars (fail-closed at the positions that matter), `min_items`, refusal of unknown fields, list item identity by a key (including duplicate-key refusal), the composite and scalar boundary, opaque fields, and the parse-level refusal of duplicate keys, aliases, merge keys, tags and second documents.

**Not supported, to be handled as the plan says (named semantic check, declared)**: a closed value set or constant (the record `kind`), a pattern (the `sha256:` and 64-hex form, the 40-hex `source_commit`), the integer range 2^53 - 1, sorted order of a list, uniqueness of a non-key value or of a set, `max_items`. None of these is worked around in the schema, in Relay or in a second validator; each is a named semantic check of the verifier, declared in the machine-checked declaration of the plan (section 7, part 4).

**Differently read, against the defining reader**: plain `yes` and dates and timestamps at string positions, and the keys `yes`, `1`, `null`. They are the cases interpretation identity exists for; the Form is not wrong, the two readers answer differently, and under the admission profile the comparison refuses them.

### 4.1 Classification of the findings

The findings are of different kinds and are kept apart:

| Finding | Classification | Where it belongs |
|---|---|---|
| No `pattern`, `enum`, `const` in the grammar (K12, K13) | grammatical capability gap | the Forms and the grammar; the record contract keeps named semantic checks (section 4) |
| No integer range, no list order, no set uniqueness (K06, K10, K15) | grammatical capability gap | the same |
| An unknown schema node key is silently ignored (K12, K13, K17) | **potential Form defect** (FG1, preliminarily HIGH) | the Forms; see 4.2 |
| A misspelled presence key (`mandatry`) is accepted and the field becomes mandatory (K17b) | **potential Form defect** (FG1) | the Forms; see 4.2 |
| Rust and Go behave identically | implementation parity, not evidence of correctness | not a result in itself |
| A byte order mark is accepted at parse (K16) | an admission-profile question | the plan's `encoding_form`; not a Form claim |
| PyYAML and the Form read some values and keys differently (K05c, K16) | an interpretation-identity question | the plan, section 5 |

### 4.2 FG1 against the Form's normative contract

FG1 is more serious than a missing capability: a schema that **compiles successfully** can look as if constraints are enforced that are not (`pattern`, `enum`, `const`, `unique_items`, a misspelled presence key). Whether the behavior is **declared** or an **implementation defect** was checked against the Form's own documents at `2f02a75` (read, not run):

* **ADR 0002** (`docs/adr/0002-minimal-schema-contract.md`): lists the information the contract needs per node (`name`, `shape_type`, `role`, presence, `nullable`, `default`, `contract`), the required and forbidden companions per Shape type, and says `contract` is "passed through; not evaluated here". It says **nothing** about a node member that is not on the list: neither that it is ignored nor that it is refused.
* **`docs/P1-SUPPORTED-SUBSET.md`**: "Passed through, not evaluated: `contract`, `description`, `role`, `capability` and the other descriptive members". The class of "other descriptive members" is open-ended and not enumerated; `pattern`, `enum` and `const` are not descriptive members, they are constraint keywords.
* **The Form's own stated principle for a constraint it does not check**: the same document says a `max_items` is "refused rather than dropped" (`SCHEMA_SHAPE_UNSUPPORTED`, issue #88, item 8: "`max_items` is accepted and never checked" was treated as a defect and fixed: "a maximum the validator would not check is refused rather than dropped"). The implementation applies the principle to that one key; it applies the same refusal-by-name (`forbid`) only to a fixed set of keys per Shape type, and nothing else.
* **Issue search**: no open or closed issue in `cic-primitive-forms` that concerns unknown schema node keys in general was found (the search is of titles; the Form's issue list was not read in full). #88 is open.

**Result.** The behavior is **neither declared as intended nor specified**; it stands against a principle the Form states for one key. That is a specification gap and a potential implementation defect, **for the Forms to decide**; it is not decided here. Until the Forms decide, the following hold in this repository: FG1 stays a documented finding; **no lint, no filter and no second check of the Form's schema acceptance is implemented in `cic-primitives`** (the implementation of any such check is on HOLD), because that would take over a responsibility that belongs to the Form and would hide the finding the Form's owner has to see.

### 4.3 The other candidates (documented findings)

| # | Finding | Handling |
|---|---|---|
| FG2 | No value constraint: enum, constant, pattern. | named semantic checks of the verifier (the plan's section 7 declaration) |
| FG3 | No integer range; only above int64 is refused. | the admission limit 2^53 - 1 stays a named check |
| FG4 | No order constraint on a list; no uniqueness for a set (`[a, a]` accepted). | `artifact_order` stays a named check; path uniqueness is expressible through the list key |
| FG5 | A byte order mark is accepted at parse. | refused before the readers (`encoding_form`) |

Mapping the Form's reasons to the contract's reasons is separate: for example `PATH_DUPLICATE_IDENTITY` (Form) is the structural counterpart of `artifact_path_duplicate` and `spec_source_path_duplicate` (contract), so those two duplicate checks are expressible with a list key; which reason identifier a verifier reports stays the contract's.

### 4.4 What this means for the normative schemas (not started)

The normative schemas are **not** written in this pull request. The measurement showed that a schema in the current grammar cannot carry value constraints, and that the Form does not tell an author so. How the schemas are to be written in the presence of FG1 is a question for the review of this measurement, not an assumption of it.

## 5. Not verified in this document

* The measurement covers the capabilities the record contract needs (25 cases); it is not a full survey of the Form.
* The Form's behavior under other commits and under another grammar profile.
* That the keys and values of the representative `ModuleRelease` and `PrimitiveRelease` schemas behave as the cases do (the schemas are step 3).
* Whether FG1 to FG5 are intended limits of the Form or defects; that is for the Forms, and no issue was opened here.
* No CI ran on this document at the time of writing.
