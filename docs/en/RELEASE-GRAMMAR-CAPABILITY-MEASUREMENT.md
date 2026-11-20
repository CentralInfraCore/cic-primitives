# Release grammar capability measurement (step 1 and 2 of the generalization plan)

Status: **measurement and gap analysis, documentation and evidence only.** No schema is written here, no verifier or compiler is changed, no Form file is changed, no lint is implemented. It is a pull request of its own (steps 1 and 2 of section 11 of `docs/en/RELEASE-CONTRACT-GENERALIZATION-PLAN.md`); the normative schemas and the derived JSON Schema (steps 3 and 4) follow only after its review.

## 1. What was measured, on what

* **Form**: `cic-primitive-forms` `main` `2f02a75592a4b0894a3b76891e9ba3741479a7c5`, **unchanged**; the library (`compile_schema`, `parse`, `validate`) in Rust (`rustc 1.99.1`) and in Go (`go1.26.11`).
* **Grammar profile**: `cic-primitives-73ae469-6a188078`, the only profile the Forms carry (a development commit; the production pin is a separate work package).
* **Cases**: 34 capability cases, 128 documents, each case a schema plus `pos_` (conforming), `neg_` (the record contract needs it refused) and `inf_` (recorded, no expectation) documents. Source and output: `docs/evidence/forms-capability-measurement/`: the generator (`gen_cases.py`, with a machine inventory; the committed cases equal its output), both probe programs, the **two raw outputs kept apart** (`go-output.txt`, `rust-output.txt`), their full SHA-256 digests (`SHA256SUMS`), and the completeness verification (`verification.txt`) with its negative tests (`selftest.txt`).
* **Result of the comparison**: both raw outputs are 160 lines, 8309 bytes, SHA-256 `0ce05b45d7ec6b10b9a1cb7cb23b4f3395660c05ba287fa0b6de0d7e8843fdc7` each: **byte-identical**. There is no Rust-Go difference, so the STOP condition did not arise. This is **implementation parity, not evidence of correctness**: two implementations that agree can share the same gap, and several results below are exactly that.
* **Completeness accounting** (`verification.txt`, produced from the generator's inventory, for each output separately): 34 cases; the schema compiled in 33 and was **refused in 1** (`K08_max_items`, `SCHEMA_SHAPE_UNSUPPORTED@$.files.max_items`); of the 128 documents **126 were run and 2 were not run** because their schema was refused (the two documents of `K08_max_items`). Byte identity is necessary and not sufficient: two empty or identically incomplete outputs are byte-identical, so the verifier also requires every case and document of the inventory to be accounted for exactly once in each output. Its negative tests (`selftest.txt`: two empty outputs, identical truncation, a missing case or document in both, a duplicate, an unknown case, a document line for a refused schema, one-line and one-character differences, one empty output) are all refused, and the real pair is accepted.
* **Both probes** stop with exit status 2 when there is no case, or a compiled case has no document, and on a file they cannot read (Go explicitly; Rust by `unwrap`).
* **The pinned grammar** was read as well, not only the Form's documents: `cic-primitives` `73ae469` (`proposals/atom-grammar/instance-grammar.schema.yaml`, `schemas/atomic/contract.yaml`, `proposals/atom-grammar/README.md`). That reading changed the classification of the findings (section 4).

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
| K12, K12b | `enum` and `const` written as **node keys** | the Form accepts and ignores them (FG1); the pinned grammar forbids them as node keys | the schema compiles; `Other` accepted next to `PrimitiveRelease` |
| K13, K13b | `pattern` written as a **node key** | the Form accepts and ignores it (FG1); the pinned grammar forbids it as a node key | the schema compiles; no-prefix, upper-case and short digests accepted; an unconstrained string takes any text |
| K14 | opaque field | supported | map, list and scalar accepted; absent mandatory: `MISSING_MANDATORY` |
| K15 | a set of strings (unique scalars) | **not supported** (not enforced) | `[a, a]` accepted |
| K16 | parse level, before any tree | see section 3 | duplicate key, alias, merge key, tag and second document refused; byte order mark accepted; keys `yes`, `1`, `null` read as text |
| K18a-d | the grammar's own mechanism: a **`contract` entry** of type `pattern`, `enum`, `range`, `unique` | declared by the grammar; accepted by the Form and **listed as unevaluated, not enforced** | the schema compiles and `compile` lists the node in `unevaluated`; every negative (`sha256` form, `Other`, `2^53`, `-1`, a duplicate digest) is accepted |
| K18e-g | a malformed `contract` entry: a type outside the grammar's closed list, an empty list, an entry without `expression` | the Form accepts all three (the grammar forbids them) | the schemas compile; same class as FG1 |
| K19a, K19b | `ordered: true` and `ordered: false` on a list | declared by the grammar (whether the element order is meaningful); accepted by the Form | no effect observed: sorted and unsorted documents accepted either way |
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

The groups below follow the owner's request; the classification in 4.1 supersedes any shorter reading.

**Supported by the Form as it is** (usable in the normative schemas): mandatory and optional, nullable against absent, string, integer and boolean scalars (fail-closed at the positions that matter), `min_items`, refusal of unknown fields, list item identity by a key (including duplicate-key refusal), the composite and scalar boundary, opaque fields, and the parse-level refusal of duplicate keys, aliases, merge keys, tags and second documents.

**Declared by the grammar but not evaluated by the Form, so a named check of the verifier remains necessary**: a closed value set or constant (the record `kind`), a pattern (the `sha256:` and 64-hex form, the 40-hex `source_commit`), the integer range 2^53 - 1, uniqueness of a non-key value or of a set: the grammar has `contract` entries for `enum`, `pattern`, `range` and `unique`, and the Form passes them through unevaluated (K18). `max_items` is declared by the grammar and refused by the Form. Sorted order of a list by the UTF-8 bytes of the path is a release rule that the grammar does not declare (4.3). None of these is worked around in the schema, in Relay or in a second validator; each stays a named semantic check of the verifier, declared in the machine-checked declaration of the plan (section 7, part 4), until the Form evaluates the contract.

**Differently read, against the defining reader**: plain `yes` and dates and timestamps at string positions, and the keys `yes`, `1`, `null`. They are the cases interpretation identity exists for; the Form is not wrong, the two readers answer differently, and under the admission profile the comparison refuses them.

### 4.1 Classification of the findings

The Form's documents alone gave a partial picture; the **pinned grammar** changes it. The findings are kept apart:

| Finding | Classification | Where it belongs |
|---|---|---|
| `pattern`, `enum`, `const` as **direct node keys** (K12, K13) | not a grammar gap: the pinned grammar **forbids** them as node keys (`additionalProperties: false`) and offers `contract` for constraints | the test shape was wrong for the grammar; the observation that the Form accepts them is FG1 |
| `contract` entries of type `range`, `pattern`, `enum`, `unique`, `must`, `when`, `mandatory` (K18a-d) | **declared by the grammar**; the Form passes them through and lists them as unevaluated (ADR 0002: "passed through; not evaluated") | an **evaluation capability gap of the Form**, not a grammar gap |
| An unknown schema node key is accepted and ignored (K12, K13, K17) | **confirmed deviation from the pinned grammar** (FG1, HIGH) | the Forms; see 4.2 |
| A misspelled presence key (`mandatry`) is accepted and the field becomes mandatory (K17b) | the same deviation (FG1) | the Forms |
| A malformed `contract` entry is accepted: type outside the closed list, empty list, no `expression` (K18e-g) | the same deviation (FG1): the Form does not validate a node against the grammar | the Forms |
| `max_items` | declared by the grammar; the Form **refuses** it (fail-closed, #88) | an execution gap, handled fail-closed |
| `ordered` | declared by the grammar; accepted by the Form, no effect observed (K19) | see 4.3 |
| Rust and Go behave identically | implementation parity, not evidence of correctness | not a result in itself |
| A byte order mark is accepted at parse (K16) | an admission-profile question | the plan's `encoding_form` |
| PyYAML and the Form read some values and keys differently (K05c, K16) | an interpretation-identity question | the plan, section 5 |

### 4.2 FG1 against the pinned grammar and the Form's contract

FG1 is more serious than a missing capability: a schema that **compiles successfully** can look as if constraints are enforced that are not.

* **The normative grammar forbids it.** `proposals/atom-grammar/instance-grammar.schema.yaml` at `73ae469` (the pinned commit), lines 14 to 17: `type: object`, `required: [name, shape_type]`, `additionalProperties: false`. An unknown node key is not valid under the grammar the Form is pinned to. Under the same file a `contract` is an array of at least one entry, each with a `type` from `[range, pattern, must, when, enum, mandatory, unique]` and an `expression`; K18e-g are all invalid under it and all compile in the Form.
* **The Form pins the file and does not apply it.** `corpus/pins.yaml` pins `instance-grammar.schema.yaml` by SHA-256; `compile_schema` does not reject what the file rejects.
* **The Form's contract is silent on whose job it is.** ADR 0002 lists the per-node information and the required and forbidden companions per Shape type; `docs/P1-SUPPORTED-SUBSET.md` names a pass-through class of "descriptive members". Neither says whether the entry point **guarantees** the grammar's node rules or **presumes** an already validated schema (searched in those two documents; no such statement found). The Form's stated principle for a constraint it does not check is "refused rather than dropped" (`max_items`, #88 item 8), applied to that key and to the per-Shape forbidden companions only.
* **Issue search**: no issue in `cic-primitive-forms` that concerns unknown schema node keys in general was found (titles searched; the list was not read in full). #88 is open.

**Result.** The deviation from the pinned grammar is established. What stays open, and is for the Forms to decide, is **the responsibility of the schema-compilation entry point**: does `compile_schema` guarantee the grammar's node rules, or does it presume a schema validated elsewhere, and if so where and by what. Until the Forms decide, FG1 stays a documented finding; **no lint, no filter and no second check of the Form's schema acceptance is implemented in `cic-primitives`** (any such implementation is on HOLD): it would take over a responsibility that belongs to the Form and hide the finding. A draft of the upstream issue is prepared (not opened).

### 4.3 The other findings, split by kind

**FG2, FG3 (value constraints, integer range): an evaluation gap, not a grammar gap.** The grammar already has `contract` entries of type `pattern`, `enum`, `range` and `unique`. The Form does not evaluate them (listed as unevaluated; K18a-d negatives accepted). So the record contract can **declare** these constraints in the grammar's own mechanism, but nothing enforces them until the Form evaluates contracts. Until then the verifier's named semantic checks stay necessary, and nothing is reinvented in `cic-primitives` or Relay.

**FG4 (order, uniqueness, counts), split three ways:**

| Layer | Finding |
|---|---|
| Grammar (declared) | `ordered` (a boolean, whether the element order is meaningful, default false), `min_items`, `max_items`, `collection_variant: set`, a `unique` contract |
| Form execution | `min_items` evaluated; `max_items` refused (fail-closed); `ordered` accepted, no effect observed (K19); a set takes `[a, a]` (K15); `unique` not evaluated (K18d) |
| Release-specific semantics | "sorted by the UTF-8 bytes of the path" (contract section 8) is a release rule for one algorithm; it is **not** what `ordered` declares (that the order matters), so it stays the named check `artifact_order` regardless of what the Form evaluates |

**FG5 (byte order mark):** accepted at parse; refused before the readers (`encoding_form`, an admission-profile rule).

Mapping the Form's reasons to the contract's reasons is separate: for example `PATH_DUPLICATE_IDENTITY` (Form) is the structural counterpart of `artifact_path_duplicate` and `spec_source_path_duplicate` (contract), so those two duplicate checks are expressible with a list key; which reason identifier a verifier reports stays the contract's.

### 4.4 Field names of the real records against the grammar's name rule (measured, not decided)

The pinned grammar limits a node name to `^[a-z][a-z0-9_]*$` (`instance-grammar.schema.yaml` at `73ae469`, the `name` property). The field names of the real records (the record structure; the inline content of `specs[].spec` excluded), read with PyYAML from the four tagged records: `v0.1.4` has none outside the rule; `v0.1.5`, `v0.2.0` and `v0.2.1` each have **`createdBy`** (at `/createdBy` and at `/release/createdBy`), which has an upper-case letter and does not match. Every other record field name matches. Two consequences are recorded and **not** decided here: the record structure cannot be described by a node named `createdBy` under the grammar as pinned (the Form compiled such a node in the fit probe, which is the FG1 behavior again), and a rename or an automatic normalization is excluded, because the name is part of the bytes the hash covers and of the four records that must stay unchanged. How the normative schemas deal with it is a question for the review.

### 4.5 What this means for the normative schemas (not started)

The normative schemas are **not** written in this pull request, and the lint is on hold. The measurement changes the question: the grammar describes more than the Form evaluates, so a normative schema can declare constraints (as `contract` entries) that the Form does not yet enforce. Whether and how the schemas declare them is for the review of this measurement; the responsibilities (declaration in the grammar, evaluation in the Form, named checks in the verifier until then) are kept apart.

## 5. Not verified in this document

* The measurement covers the capabilities the record contract needs (34 cases); it is not a full survey of the Form.
* The Form's behavior under other commits and under another grammar profile.
* That the keys and values of the representative `ModuleRelease` and `PrimitiveRelease` schemas behave as the cases do (the schemas are step 3).
* Whether FG1 to FG5 are intended limits of the Form or defects; that is for the Forms, and no issue was opened here.
* No CI ran on this document at the time of writing.
