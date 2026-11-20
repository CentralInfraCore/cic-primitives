# Grammar node-name rule: design of a versioned profile (decision D1, issue #39)

Status: **design, documentation and evidence only.** Not changed here: `instance-grammar.schema.yaml`, `check_grammar.py`, `schemas/atomic/shape.yaml`, any schema of the release schema set, any grammar pin, the Forms, the compiler, the verifier, any release record. Nothing in this document is implemented, and the finalization of the release schemas stays on hold until the grammar change exists (cic-primitives #38, D1).

## 1. The decision and its conditions

D1 (owner, after #37): the grammar's **general** node-name rule is changed, as a separate issue and pull request, through a versioned grammar profile. No `createdBy` exception in the Form, no rename or normalization of the records, the historical records unchanged. Conditions for this design:

| # | Condition | Where met |
|---|---|---|
| C1 | a general grammar rule, not a `createdBy` exception | section 3 |
| C2 | the existing profile keeps its semantics, unchanged | section 5 |
| C3 | a new, explicit, versioned profile | section 4 |
| C4 | Go and Rust behavioral parity | section 6 |
| C5 | historical release records, hashes and signatures untouched | section 5 |
| C6 | positive and negative conformance vectors, designed | section 8 |
| C7 | impact on Forms #166 and #167 | section 7 |

## 2. What was measured

Evidence: `docs/evidence/grammar-node-name-measurement/` (`README.md`; the Forms commit `2f02a75`, unchanged; Rust and Go byte-identical; every case and document accounted for).

1. **One place defines the rule**: `proposals/atom-grammar/instance-grammar.schema.yaml`, property `name`: `type: string`, `minLength: 1`, `pattern: "^[a-z][a-z0-9_]*$"`. It is applied by `check_grammar.py` through the JSON Schema library, and by nothing else that was found: the compiler runs the grammar gate (`run_grammar_gate`, `tools/compiler.py`) and records the digests of both grammar files in the provenance of a new release (`grammar_sha256`, `grammar_schema_sha256`).
2. **The Form does not enforce the name pattern.** 15 schemas, each with one field named `a`, `created_by`, `createdBy`, `CreatedBy`, `A`, `1abc`, `_x`, `a-b`, `a b`, `a.b`, a name with U+00E9, a name with a trailing line feed, the empty name, a 300-character name, `aB_c9`, plus one schema with the case-distinct siblings `createdby` and `createdBy` (16 cases, 48 documents). Every schema compiles in Rust and Go and its documents are validated against the exact name; the siblings are distinct fields. **Only the empty name is refused** (`SCHEMA_INVALID`, the grammar's `minLength: 1`). The measurement started from the hypothesis that every case compiles; the empty name falsified it and is recorded as such in `gen_cases.py`. So the Form is **more permissive than the pinned grammar on names**: a gap of the same kind as FG1 (#166), not reported separately here.
3. **Only one real name violates the rule.** `cic-primitives` (292 node occurrences, 70 distinct names): `createdBy` in the release schema drafts, and a deliberate fixture `"1"` of the measurement. A local checkout of `cic-schema-registry` (head `c595080`, 2026-10-18, 7 uncommitted files at the time: possibly stale) has 1904 occurrences, 269 distinct names, **no violation** and no name with an upper-case letter.
4. **The pinned file set contradicts itself.** `schemas/atomic/shape.yaml:88` (in the pin manifest of the 12 files) says a field name is "CamelCase or snake_case, consistent within the namespace"; the instance grammar admits only lower-case snake_case. The change of D1 therefore also removes an existing inconsistency; "consistent within the namespace" is a cross-node rule that a per-node pattern cannot carry (section 3).
5. **The checker accepts a name with a trailing line feed.** With `jsonschema 4.19.2` (Python 3.14.4) `abc\n` passes `^[a-z][a-z0-9_]*$` (the library searches, and Python's `$` matches before a final line feed); Go's RE2 and the Rust `regex` crate reject it. The pinned checker accepts it (exit 0). This is a property of the regular-expression **flavor**, not of this rule: any `$`-anchored pattern behaves so. A guard that is identical in all three flavors exists (section 4).
6. **Precedent for a versioned grammar profile**: `access-policy/1` (`P0-4-ACCESS-GRAMMAR.md`, "Grammar version binding"): the version is a property of the **pinned schema** and of the **processing context**, never a key of a document; both are required (missing, unknown and conflicting versions are three distinct errors, no default); changing it is a new schema version, a new grammar identity and an explicit migration. The Forms keep a profile table keyed by the pin name (`go/schema.go`, `rust/src/schema.rs`: features `ItemChoice`, `AccessGrammar`).

## 3. The rule (the choice belongs to the owner)

| Option | Pattern | Admits | Consequence |
|---|---|---|---|
| **R1 (recommended)** | `^[a-z][a-zA-Z0-9_]*$` | lowerCamelCase and snake_case, always a lower-case initial | all names in use stay valid; `createdBy` becomes valid; the initial letter keeps the difference from the PascalCase Kind names (`cic:ns:Kind`) |
| R2 | `^[A-Za-z][A-Za-z0-9_]*$` | also PascalCase names | matches the widest reading of `shape.yaml` "CamelCase"; erodes the difference with Kind names |
| R3 | R1 plus a style rule "consistent within the namespace" | as R1 | the style rule is cross-node: it is a lint, not a pattern; the lint is on hold (owner decision) |

**Three things that must not be confused** (review F1 of #40). The word "widening" is true of the **normative** rule only:

| Name | V1 normative rule (full match) | V1 checker, as measured | V2 (R1 plus the line-feed guard) |
|---|---|---|---|
| `created_by` | accept | accept | accept |
| `createdBy` | refuse | refuse | **accept** (the added language) |
| `abc\n` | refuse | **accept** (a flavor defect of the checker) | **refuse** (a deliberate tightening, accepted as O3) |

* **(a) R1 widens the normative V1 rule.** Every name valid under the V1 rule (a full match of `^[a-z][a-z0-9_]*$`) is valid under V2. A bounded exhaustive check (alphabet `abZQ0_- \n` plus U+00E9, length 1 to 5: 111 110 strings) finds **no** name valid under the V1 rule and invalid under R1, and the 2 428 names that R1 adds **all contain an upper-case letter** (`name-rule-check.txt`; the check is mutation-tested: a rule that drops `_` and a rule that also admits `-` are both refused by `selftest_name_rule_check.py`).
* **(b) R1 is not a widening of the language the V1 checker actually accepts.** That language is the V1 rule plus **one line feed after a valid name** (`abc\n`; `abc\n\n` is refused: Python's `$` matches only before a final line feed). The same bounded check confirms this exactly (`name-rule-check.txt`, "the V1 checker's search language": 0 differences, 170 extra names in the bounded space; and no name the checker accepts is refused by V2 except those extra names), and it is mutation-tested too. V2 refuses those names.
* **(c) The erroneous acceptances that V2 removes** are exactly (b)'s extra names: valid-name-plus-one-line-feed. No other name accepted by the V1 checker is refused by V2.

**Case is identity.** Upper-case and lower-case letters make different names (`createdby` and `createdBy` are different fields and can be siblings: the Form already treats them so). **No normalization and no automatic renaming is allowed**, in the grammar, the checker, the Forms or any tool. Look-alike names are not prevented (a lint question; the lint is on hold).

## 4. The versioned profile (design)

**Mechanism M1 (recommended), following `access-policy/1`:**

* The version is a property of the **pinned grammar** (declared in the pinned `schemas/atomic/shape.yaml`, `spec.node_name_grammar.version`, because that atomic describes the field name) and of the **processing context**. It is never a key of a document. The context supplies the version it expects, it must equal the pin's; a missing one, an unknown one (`"2"`, `true`, `3`) and a difference are three distinct errors (names proposed: `NODE_NAME_GRAMMAR_VERSION_MISSING`, `..._UNKNOWN`, `..._CONFLICT`). No default.
* **Version 1** is the current rule, exactly as pinned at `73ae469`: its identity is the pin (`cic-primitives-73ae469-6a188078`, an immutable commit and manifest). Its files are not touched. The pin file set declares nothing about the version (it predates it): the Forms profile table assigns it explicitly **by pin name**, so no default exists inside any file.
* **Version 2** is the new rule (R1) with an **explicit full-match meaning**: the name matches the pattern as a whole and contains no line feed. In the JSON Schema: `pattern: "^[a-z][a-zA-Z0-9_]*$"` together with `not: {pattern: "\\n"}`. The pair equals a full match in Python's search, Python's `fullmatch`, Go and Rust for every listed name and for the whole bounded space; it makes the line-feed hazard of point 5 disappear for the new profile without the flavor having to be fixed. Version 2 exists only in a **new pin** (a new commit and manifest), which is the new grammar identity.
* The compiler's release provenance records the digests of the grammar files of the pin it released with: a release made after the change records the new digests; releases made before are not affected.

Alternatives rejected: **M2**, two coexisting schema files (a second copy of a large schema that every later structural change must follow); **M3**, the rule moved from the JSON Schema into the checker code (a declarative rule becomes code that other consumers of the schema file no longer see).

## 5. Compatibility: the existing profile, the historical records

* **The existing profile is unchanged by construction.** Its identity is an immutable commit and manifest; the new profile lives in a new pin. Evidence to be produced by the implementation: the old pin's file digests (`manifest_sha256 6a188078...`) stay as they are, and the old vectors pass under context version 1 against the old file.
* **Known divergence of version 1, recorded and not fixed (decision O3):** the V1 checker accepts a valid name followed by one line feed (point 5, section 3 (b)) while the rule's text and the Go and Rust regexes refuse it. Version 1 stays unchanged: the divergence is documented, and the evidence tool asserts it (a change of the checker's behavior on `abc\n` fails `name_rule_check.py` on purpose, so it can only change consciously). Version 2 closes it.
* **Historical release records, hashes and signatures are not touched.** The grammar governs **schemas** (compositions), not release records: no file under the records, no hash payload, no signature depends on the grammar; the field name `createdBy` stays as published. What changes is only the schema that describes the records (the release schema set, still draft). The release schemas under version 1 keep exactly three findings, all `createdBy` (recorded in cic-primitives #38); under version 2 they are expected to have none, which is the finalization gate.

## 6. Rust and Go parity

* **Today:** parity holds, trivially: Rust and Go compile 15 of the 16 cases and refuse the empty name identically (`verification.txt`, byte-identical outputs), because neither enforces the pattern. The regular-expression engines agree as well (`namepat-*-output.txt`: 24 names, 4 patterns, byte-identical), including on the line feed.
* **Under the new profile (V2): the parity of the actual name validation is mandatory.** The checker, a Go implementation and a Rust implementation must **actually validate names** (not only be shown to agree on a regular expression), and the same vector file gives the same verdict in all three. Whether the **Forms** validate names is a separate decision (they do not today); if they do, they validate **per profile** (a `NodeNameGrammar` feature of the profile table), never one rule for every pin. **Under V1 the Forms keep their current behavior** (they accept every non-empty name) **unless a separate, explicit compatibility decision says otherwise** (section 7). The Forms change, the new pin and the profile table entry are separate work packages (on hold).

## 7. Impact on Forms #166 and #167

* **#166 (schema node keys and contract entries silently ignored).** Independent of names as long as its fix is limited to unknown keys and malformed contract entries. If the fix evaluates the **whole** grammar schema (it is `additionalProperties: false` and holds the name pattern in the same file), it would, under the current pin, refuse `createdBy` and make the release schemas uncompilable. **Ordering consequence:** the fix of #166 must be profile-aware, or must not start before the new pin exists. Recommended as an added condition of #166.
  **Compatibility rule (review F2):** the fix of #166 must **not** start rejecting, under V1, names the Forms accept today (for example `a-b`, `1abc`, `Foo`). Rejecting them would be a compatibility change of the V1 behavior and must not happen unnoticed: it requires its own explicit decision, with the list of names that change verdict (the vector rows where the Forms' V1 verdict is accept and the V1 rule's verdict is refuse, section 8). The default is: the #166 fix does not enforce the name rule under V1.
* **#167 (surface-level `validation` neither evaluated nor listed).** Independent. One interaction: the expression dialect of `must` (open point P2 of #38) must accept the names of the new profile (an upper-case letter inside an identifier).
* Both need, when the new pin exists, a new entry in the Forms profile table and a `NodeNameGrammar` value for it; the pin change is on hold.
* **Not reported:** the Forms' acceptance of names the grammar forbids (point 2) has no issue; the owner decides whether it joins #166.

## 8. Conformance vectors (design, nothing is implemented)

One vector file is the **single source of verdicts**; each runner asserts it. A vector is `(name, v1_rule, v1_checker, v1_forms, v2)`: **four** verdicts, because the V1 behaviors differ and a single `v1` column would hide it. `v1_rule` is the normative V1 rule (a full match); `v1_checker` is the historical behavior of the pinned checker; `v1_forms` is the current behavior of the Forms (measured at `2f02a75`: every non-empty name is accepted); `v2` is the single, enforced verdict of the new profile (checker, Go and Rust alike).

| Class | Names | v1_rule | v1_checker | v1_forms | v2 |
|---|---|---|---|---|---|
| valid in all | `a`, `abc_1`, `a_`, `created_by` | accept | accept | accept | accept |
| valid in v2 only | `createdBy`, `aB_c9`, `a9B`, `aBC` | refuse | refuse | accept | accept |
| invalid in the rule, accepted by the Forms | `A`, `CreatedBy`, `1abc`, `_x`, `a-b`, `a b`, `a.b`, `ét` (U+00E9), a Cyrillic look-alike, `a` followed by NUL | refuse | refuse | **accept** | refuse |
| the empty name | (empty) | refuse | refuse | refuse | refuse |
| one line feed after a valid name | `abc\n` | refuse | **accept** | accept | refuse |
| other line feeds | `abc\n\n`, `a\nb`, `\nabc` | refuse | refuse | accept | refuse |
| long | 300 characters | accept | accept | accept | accept |

The rows where `v1_forms` is accept and `v1_rule` is refuse are the **list of names whose verdict would change if the Forms ever enforced the V1 rule**: that list is the content of the explicit compatibility decision of section 7. The two `v1_checker` / `v1_rule` differences (one row) are the documented divergence of O3.

Runners: (a) the Python checker (`check_grammar.py`) on a one-node composition per name, (b) a Go runner (RE2), (c) a Rust runner (`regex`), (d) later and only if decided, the Forms. Further vectors: **version binding** (missing, unknown `"2"`/`true`/`3`, conflict: three distinct errors; a document with a `node_name_grammar` key is refused as an unknown key); **widening** (every v1-valid name is v2-valid: the bounded exhaustive check becomes a vector); **release schema set** (the composed schemas have the three findings under v1 and none under v2). **Mutation tests** of the vectors: a narrowed pattern, a dropped line-feed guard, a missing version check, a default to version 1, each must turn at least one vector red. **Historical vectors**: the old pin's vectors pass under context version 1 against the old file (a CI job on the pinned commit); the four records and their verification results are not re-run by this package because nothing they depend on changes (to be shown by an unchanged reference-verifier run in the implementation pull request).

## 9. Sequence and holds

1. Owner decisions (section 10). 2. Implementation pull request in cic-primitives: the grammar change, the version binding in the checker, the vectors, the evidence (on hold until 1). 3. New grammar pin and Forms profile table entry, the Forms conformance (separate packages, on hold). 4. Only then: finalization of the release schemas, the derived JSON Schema (on hold).

## 10. Decisions (accepted by the owner in the review of #40)

| # | Decision |
|---|---|
| O1 | the rule is R1, `^[a-z][a-zA-Z0-9_]*$`, as a **full match** |
| O2 | the mechanism is M1: the version is bound to the pin and to the processing context |
| O3 | version 1 stays unchanged; the line-feed defect of the V1 checker is documented, not repaired; V2 refuses it (a deliberate tightening) |
| O4 | the version is declared as `spec.node_name_grammar.version` in `schemas/atomic/shape.yaml` |
| O5 | the Forms' acceptance of grammar-forbidden names is recorded in #166 |
| O6 | the fix of #166 must be profile-aware (mandatory) |
| | no `createdBy` exception; case is identity: no normalization, no automatic renaming |

## 11. Not verified

* The registry inventory is from a local checkout that may be stale (7 uncommitted files at the time); the claim "no violation" is for that checkout only.
* Python 3.14.4 and `jsonschema 4.19.2` only: the checker's behavior on a line feed was not measured with other versions of the library.
* The Forms' behavior was measured at `2f02a75` only; the Forms were not changed or run with a new profile (none exists).
* The error names of section 4 and the key `spec.node_name_grammar.version` are proposals.
* That nothing else consumes the name pattern (other repositories, the registry's own tools): searched in this repository and in the Forms checkout only.
* The bounded exhaustive check covers strings of length 1 to 5 over a 10-character alphabet; it is evidence for the widening property, not a proof for all strings (the patterns are simple character classes, so the property also follows from the classes: `[a-z0-9_]` is a subset of `[a-zA-Z0-9_]`).
* No CI ran on this document at the time of writing.
