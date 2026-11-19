# Release grammar capability measurement (step 1 and 2 of the generalization plan)

Status: **measurement and gap analysis, documentation and evidence only.** No schema is written here, no verifier or compiler is changed, no Form file is changed. It is the first part of the pull request that continues with the normative schemas and the derived JSON Schema (section 11, steps 3 and 4 of `docs/en/RELEASE-CONTRACT-GENERALIZATION-PLAN.md`).

## 1. What was measured, on what

* **Form**: `cic-primitive-forms` `main` `2f02a75592a4b0894a3b76891e9ba3741479a7c5`, **unchanged**; the library (`compile_schema`, `parse`, `validate`) in Rust (`rustc 1.99.1`) and in Go (`go1.26.11`).
* **Grammar profile**: `cic-primitives-73ae469-6a188078`, the only profile the Forms carry (a development commit; the production pin is a separate work package).
* **Cases**: 25 capability cases, 106 documents, each case a schema plus `pos_` (conforming), `neg_` (the record contract needs it refused) and `inf_` (recorded, no expectation) documents. Source and output: `docs/evidence/forms-capability-measurement/` (generator, both probe programs, `expected-output.txt`, SHA-256 `285ce31a...5c7`).
* **Result of the comparison**: the Rust and the Go output are **byte-identical on all 129 lines**. There is no Rust-Go difference, so the STOP condition did not arise.

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

### 4.1 Candidate Form gaps (reported, not fixed, not worked around)

These are findings about **general** structural capability, to be decided in the Forms:

| # | Finding | Why it matters here |
|---|---|---|
| FG1 | A schema node key the Form does not know is **silently ignored** (`pattern`, `enum`, `const`, `unique_items`, `foo`); only `max_items` is refused. A misspelled presence key (`mandatry`) silently makes the field mandatory. | A schema author who writes a `pattern` or an `enum` gets a schema that compiles and enforces nothing. The normative set must contain **no** unsupported key, and until the Form refuses them this plan adds a stopgap lint on our own schema files (listed as a stopgap, to be removed when the Form fails closed). |
| FG2 | No value constraint: enum, constant, pattern. | The record `kind` and the digest forms stay named semantic checks. |
| FG3 | No integer range; only above int64 is refused. | The admission limit 2^53 - 1 stays a named check. |
| FG4 | No order constraint on a list and no uniqueness for a set (`[a, a]` accepted). | `artifact_order` stays a named check; path uniqueness is expressible through the list key. |
| FG5 | A byte order mark is accepted at parse. | Refused before the readers (`encoding_form`). |

Mapping the Form's reasons to the contract's reasons is separate: for example `PATH_DUPLICATE_IDENTITY` (Form) is the structural counterpart of `artifact_path_duplicate` and `spec_source_path_duplicate` (contract), so those two duplicate checks are expressible with a list key; which reason identifier a verifier reports stays the contract's.

## 5. Not verified in this document

* The measurement covers the capabilities the record contract needs (25 cases); it is not a full survey of the Form.
* The Form's behavior under other commits and under another grammar profile.
* That the keys and values of the representative `ModuleRelease` and `PrimitiveRelease` schemas behave as the cases do (the schemas are step 3).
* Whether FG1 to FG5 are intended limits of the Form or defects; that is for the Forms, and no issue was opened here.
* No CI ran on this document at the time of writing.
