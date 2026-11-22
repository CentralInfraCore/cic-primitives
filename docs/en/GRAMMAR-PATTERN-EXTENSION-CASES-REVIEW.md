# The `pattern` profile: review package of the 47 proposed extension cases

Status: **a review package, documentation and isolated tooling only.** It asks the owner and the reviewers to decide whether the 47 cases proposed in the implementation specification (`GRAMMAR-PATTERN-IMPLEMENTATION-SPEC.md`, #52) become conformance cases. **It adds no case to the approved vector file.** The 513 approved vectors stay the unchanged reference (SHA-256 `e7ece43a...`, held by the check of this package); nothing here is an implementation, a gate, a publication, or an owner decision. All earlier HOLDs stay on hold.

Companions: `docs/design/pattern-profile-spec/extension-cases.yaml` (the 47 cases), `docs/design/pattern-profile-spec/extension-review.yaml` (the review data: the derivation, the rule and the decision dependencies of each case) and the tooling in `docs/evidence/pattern-extension-review/`.

## 1. What is being reviewed

The 47 cases are in three groups. Each expected result is **derived by hand from the text of the specification** (the derivation is in the table of section 3, step by step); the executable reading `spec_model.py` evaluates them (it delegates the classification of an expression to the existing prototype); neither is an implementation of the profile.

| Group | Cases | What the cases test | Decisions the cases depend on |
|---|---|---|---|
| `E-PIN` | 34 | pin resolution: wrong types, conflict before unknown, identical declarations, the type-sensitive identity of declared values, the type-preserving reader, no pin evaluation without a pattern contract, the pin before every expression | D1, D2, D3, D6 |
| `E-TRV` | 7 | the document-order traversal of nested contracts: the first refused contract in source order decides code and path | D4 |
| `E-RDR` | 6 | the reader boundary: errors that never reach the validator and carry no pattern code | D5, D6 |

## 2. The decisions the cases depend on

The cases make sense only under the decisions that the implementation specification records as professional recommendations and that the owner has to confirm **separately**: D1 a wrong-typed pin is `pattern_profile_unknown`, no new code; D2 an explicit `null` declaration is unknown; D3 a schema without a pattern contract evaluates no pin; D4 the traversal is source order; D5 an expression that is not a string is a reader error; D6 the schema layer's own error vocabulary is a separate contract. **No case depends on D7 (the composition of schema parts) or D8 (the order of several violating values), which are on hold**; the check refuses a review entry that does.

| Decision | Cases that need it |
|---|---|
| D1 | 29 (all wrong-typed, conflicting and identical pins, the identity rule, the typed reader) |
| D2 | 1 (`E-PIN-04`) |
| D3 | 2 (`E-PIN-14`, `E-PIN-15`) |
| D4 | 7 (all `E-TRV`) |
| D5 | 4 (`E-RDR-02`, `E-RDR-03`, `E-RDR-04`, `E-RDR-06`) |
| D6 | 9 (the reader-error cases) |

**Consequence for the order of work:** a case may be accepted only after the decision it depends on is confirmed. If a decision is changed by the owner, the cases that depend on it are re-derived, not silently kept.

## 3. The cases: input, expected result, derivation, rule, dependencies

The table is **rendered from the data** by `check_extension_review.py --render` (the check compares the table below with a fresh rendering; nothing is hand-edited into it). A "pin (YAML text)" is YAML text read by the type-preserving reader, because the case file itself is loaded by a host-language parser that would merge the keys `1`, `true` and `1.0`. A schema shown without a "schema" part is the one-contract schema `a: {contract: [{type: pattern, expression: '^a$'}]}`.

<!-- BEGIN CASE TABLE -->
| Case | Input | Expected | Derivation from the text | Rule | Depends on |
|---|---|---|---|---|---|
| E-PIN-01 | pin `[true]` | refuse `pattern_profile_unknown` | one declaration, the value true; not the int 1 (a bool is not an int); so the single value is unknown | O-VA-01 step 3 | D1 |
| E-PIN-02 | pin `[1.0]` | refuse `pattern_profile_unknown` | one declaration, 1.0; a float is not the int 1; unknown | O-VA-01 step 3 | D1 |
| E-PIN-03 | pin `['1']` | refuse `pattern_profile_unknown` | one declaration, the text 1; a string is not the int 1; unknown | O-VA-01 step 3 | D1 |
| E-PIN-04 | pin `[null]` | refuse `pattern_profile_unknown` | one declaration whose value is null (the key is present, so it is a declaration, not a missing pin); null is not the int 1; unknown | O-VA-01 step 3, O-RD-04 | D1, D2 |
| E-PIN-05 | pin `[0]` | refuse `pattern_profile_unknown` | one declaration, the int 0; an int but not 1; unknown | O-VA-01 step 3 | D1 |
| E-PIN-06 | pin `[-1]` | refuse `pattern_profile_unknown` | one declaration, the int -1; unknown | O-VA-01 step 3 | D1 |
| E-PIN-07 | pin `[[1]]` | refuse `pattern_profile_unknown` | one declaration, a list; not the int 1; unknown | O-VA-01 step 3 | D1 |
| E-PIN-08 | pin `[{version: 1}]` | refuse `pattern_profile_unknown` | one declaration, a mapping; not the int 1; unknown | O-VA-01 step 3 | D1 |
| E-PIN-09 | pin `[1, true]` | refuse `pattern_profile_conflict` | declarations 1 and true: different type classes (a bool is not an int), so not identical; conflict (step 2 precedes step 3) | O-VA-01 step 2, identity table | D1 |
| E-PIN-10 | pin `[1, '1']` | refuse `pattern_profile_conflict` | declarations 1 and the text 1: different type classes; conflict | O-VA-01 step 2, identity table | D1 |
| E-PIN-11 | pin `[1, 99]` | refuse `pattern_profile_conflict` | declarations 1 and 99: both ints but different values, so not identical; conflict, although 99 alone would be unknown (conflict precedes unknown) | O-VA-01 step 2 | D1 |
| E-PIN-12 | pin `[true, true]` | refuse `pattern_profile_unknown` | declarations true and true: identical (same type class, same truth value), count as one; the single value true is not the int 1; unknown | O-VA-01 step 3 | D1 |
| E-PIN-13 | pin `[]` | refuse `pattern_profile_missing` | no declaration while the schema has a pattern contract; missing | O-VA-01 step 1 | none |
| E-PIN-14 | pin `[99]`; schema `a: {type: string}` | accept | the schema has no pattern contract, so the pin is not evaluated whatever it is (99 would be unknown); accepted | O-VA-02 | D3 |
| E-PIN-15 | pin `[1, 2]`; schema `a: {type: string}` | accept | no pattern contract, so declarations 1 and 2 (a conflict if evaluated) are not evaluated; accepted | O-VA-02 | D3 |
| E-PIN-16 | pin `[1, 1, 1]` | accept | three declarations 1 are identical, count as one declaration, the int 1; the pin resolves; the contract is accepted | O-VA-01 step 3 (identical declarations count as one) | none |
| E-PIN-17 | pin `[true]`; schema `a: {contract: [{type: pattern, expression: '(?i)a'}]}` | refuse `pattern_profile_unknown` | the pin true is unknown; the expression (?i)a would be pattern_group_extension, but the pin is evaluated before every expression; the schema is refused with the pin code | O-VA-02 (before every expression) | D1 |
| E-PIN-18 | pin `[{1: a}, {'1': a}]` | refuse `pattern_profile_conflict` | two mappings, one with the int key 1 and one with the text key 1: the key's type class counts, so they differ; conflict | section 3 identity (mapping) | D1 |
| E-PIN-19 | pin `[{1: a}, {1: a}]` | refuse `pattern_profile_unknown` | two identical mappings count as one; a mapping is not the int 1; unknown | section 3 identity (mapping), O-VA-01 step 3 | D1 |
| E-PIN-20 | pin `[{a: 1, b: 2}, {a: 1, b: 2}]` | refuse `pattern_profile_unknown` | the same two entries in another order are identical; one value, a mapping; unknown | section 3 identity (mapping order irrelevant) | D1 |
| E-PIN-21 | pin `[[1, 2], [2, 1]]` | refuse `pattern_profile_conflict` | the lists 1,2 and 2,1 differ at the first position; not identical; conflict | section 3 identity (list order relevant) | D1 |
| E-PIN-22 | pin `[1, 1.0]` | refuse `pattern_profile_conflict` | 1 and 1.0: a float is never identical to an int; conflict | section 3 identity (float versus int) | D1 |
| E-PIN-23 | pin `[{1: a, x: b}, {x: b, 1: a}]` | refuse `pattern_profile_unknown` | mappings with an int key and a text key in two entry orders: the same set of typed entries; identical; one value, a mapping; unknown (the comparison needs no sort of mixed keys) | section 3 identity (mixed key types, order irrelevant) | D1 |
| E-PIN-24 | pin `[.nan, .nan]` | refuse `pattern_profile_unknown` | all NaN are identical to each other; one value, a float; unknown | section 3 identity (NaN) | D1 |
| E-PIN-25 | pin `[0.0, -0.0]` | refuse `pattern_profile_conflict` | 0.0 and -0.0 have different binary64 bit patterns; not identical; conflict | section 3 identity (floats by bit pattern) | D1 |
| E-PIN-26 | pin `[[1, [2, {3: a}]], [1, [2, {3: a}]]]` | refuse `pattern_profile_unknown` | two equal nested lists with a nested mapping, compared recursively: identical; one value, a list; unknown | section 3 identity (nested) | D1 |
| E-PIN-27 | pin `[[1, [2, {3: a}]], [1, [2, {'3': a}]]]` | refuse `pattern_profile_conflict` | the nested mappings differ in the type class of one key (int 3 against text 3); not identical; conflict | section 3 identity (nested key type) | D1 |
| E-PIN-28 | pin (YAML text) `[{1: a, true: b, 1.0: c}]` | refuse `pattern_profile_unknown` | one mapping with the keys 1, true and 1.0: three keys of three type classes, so no duplicate and no reader error; one value, a mapping; unknown | O-RD-04 (type-preserving representation), section 3 | D1 |
| E-PIN-29 | pin (YAML text) `[{1: a, 1: b}]` | reader error `duplicate_key` | the key 1 twice is a real duplicate (same type class, same value): a reader error, no pattern code | O-RD-04 (duplicate key by the identity rule) | D1, D6 |
| E-PIN-30 | pin (YAML text) `[{0.0: a, -0.0: b}]` | refuse `pattern_profile_unknown` | the keys 0.0 and -0.0 are two keys: no duplicate; one value, a mapping; unknown | O-RD-04, section 3 identity (floats by bit pattern) | D1 |
| E-PIN-31 | pin (YAML text) `[{1: a, true: b, 1.0: c}, {1.0: c, true: b, 1: a}]` | refuse `pattern_profile_unknown` | two mappings with the same typed entries in different orders are identical; one value; unknown | O-RD-04, section 3 identity (mapping order irrelevant) | D1 |
| E-PIN-32 | pin (YAML text) `[{1: a, true: b}, {1: a, 1.0: b}]` | refuse `pattern_profile_conflict` | the mapping with the keys 1 and true against the mapping with the keys 1 and 1.0: the second key differs in its type class; not identical; conflict | O-RD-04, section 3 identity (key types) | D1 |
| E-PIN-33 | pin `[1]`; schema `a: {1: x, contract: [{type: pattern, expression: '^a$'}]}` | reader error `non_string_key` | a mapping key of the SCHEMA document is the int 1, not a string: a reader error (non_string_key) | O-RD-06 | D6 |
| E-PIN-34 | pin (YAML text) `[{? [1, 2] : a}]` | reader error `non_scalar_key` | the key of a mapping inside a pin value is a list: a reader error (non_scalar_key), no pattern code | O-RD-04 (a non-scalar mapping key is a reader error) | D1, D6 |
| E-TRV-01 | pin `[1]`; schema `n: contract: [{type: pattern, expression: '(?i)a'}] fields: - {name: x, contract: [{type: pattern, expression: 'c{300}'}]}` | refuse `pattern_group_extension` at `n/contract/0` | in source order the node's own contract comes before its fields; the own contract (?i)a is the first refused (group extension); path n/contract/0 | O-RD-03 | D4 |
| E-TRV-02 | pin `[1]`; schema `n: fields: - {name: x, contract: [{type: pattern, expression: 'c{300}'}]} contract: [{type: pattern, expression: '(?i)a'}]` | refuse `pattern_repeat_count_too_large` at `n/fields/0/contract/0` | the key fields stands before contract in the source, so the child contract c{300} is delivered first and is the first refused (count above 255); path n/fields/0/contract/0 | O-RD-03 | D4 |
| E-TRV-03 | pin `[1]`; schema `n: item_fields: - {name: y, contract: [{type: pattern, expression: '[z-a]'}]} fields: - {name: x, contract: [{type: pattern, expression: '(a'}]}` | refuse `pattern_class_range_order` at `n/item_fields/0/contract/0` | item_fields stands before fields: the item_fields contract [z-a] (class range order) is delivered before the fields contract (a (unbalanced); path n/item_fields/0/contract/0 | O-RD-03 | D4 |
| E-TRV-04 | pin `[1]`; schema `n: fields: - {name: x, contract: [{type: pattern, expression: '^a$'}, {type: pattern, expression: '(a'}]} - {name: y, contract: [{type: pattern, expression: '[z-a]'}]}` | refuse `pattern_unbalanced_group` at `n/fields/0/contract/1` | in the first field the first contract is accepted and the second (a is unbalanced; the second field is not reached; path n/fields/0/contract/1 | O-RD-03 (sequence items by index) | D4 |
| E-TRV-05 | pin `[1]`; schema `a: b: c: contract: [{type: pattern, expression: '^a$'}] d: contract: [{type: pattern, expression: '^b$'}, {type: pattern, expression: 'a{01}'}]` | refuse `pattern_quantifier_leading_zero` at `a/d/contract/1` | depth first: a/b/c accepted, then a/d with the contracts ^b$ accepted and a{01} refused (leading zero); path a/d/contract/1; the schema is refused as a whole | O-RD-03, O-VA-09 | D4 |
| E-TRV-06 | pin `[1]`; schema `n: contract: [{type: pattern, expression: '^a$'}, {type: string}, {type: pattern, expression: '(?i)a'}]` | refuse `pattern_group_extension` at `n/contract/2` | the contract at index 1 is not of type pattern and is skipped; the contract at index 2, (?i)a, is the first refused; its path keeps the sequence index 2 | O-RD-03 (a non-pattern contract is skipped) | D4 |
| E-TRV-07 | pin `[1]`; schema `n: contract: [{type: pattern, expression: '^a$'}] fields: - {name: x, contract: [{type: pattern, expression: '^b$'}]}` | accept | every delivered contract is accepted (^a$ and ^b$) and the pin resolves; the schema is accepted | O-RD-03, O-VA-09 | D4 |
| E-RDR-01 | pin `[1]`; schema `a: {contract: [{type: pattern, expression: '^a$'}], contract: [{type: pattern, expression: '(?i)a'}]}` | reader error `duplicate_key` | the key contract appears twice in one mapping: a duplicate key is a reader error before the validator runs; no pattern code | O-RD-02 | D6 |
| E-RDR-02 | pin `[1]`; schema `a: {contract: [{type: pattern, expression: 5}]}` | reader error `expression_not_a_string` | the expression is the int 5, not a string: a reader error (expression_not_a_string); the validator never receives it | O-RD-02 | D5, D6 |
| E-RDR-03 | pin `[1]`; schema `a: {contract: [{type: pattern}]}` | reader error `expression_not_a_string` | a pattern contract without an expression: absent is not a string; a reader error | O-RD-02 | D5, D6 |
| E-RDR-04 | pin `[1]`; schema `a: {contract: [{type: pattern, expression: null}]}` | reader error `expression_not_a_string` | an expression whose value is null is not a string; a reader error | O-RD-02 | D5, D6 |
| E-RDR-05 | pin `[1]`; schema `a: [` | reader error `yaml_syntax` | the YAML does not parse: a syntax error is a reader error | O-RD-02 | D6 |
| E-RDR-06 | pin `[true]`; schema `a: {contract: [{type: pattern, expression: 5}]}` | reader error `expression_not_a_string` | the pin true would be unknown, but the reader fails first on an expression that is not a string; step 0 precedes step 1, so the outcome is the reader error | section 4 (step 0 before step 1) | D5, D6 |
<!-- END CASE TABLE -->

## 4. How the expected results were obtained, and what that does and does not show

Each derivation names the rule of the specification it uses (an obligation and a step, or a section) and goes from the input to the result in steps; the cases were written **from those steps**, and the executable reading was run afterwards. The check shows that the reading gives the expected result for every case (**0 differences**), that every case has a review entry and every entry a case, that every derivation names a known obligation or a section, that the dependencies stay inside D1 to D6, and that every requirement a case names exists in the approved set. **It does not show that the derivations are right independently of their author**: the same author wrote the specification, the cases, the derivations and the reading; the independence test is the review of this package, and later a third implementation by another author from the specification and the accepted cases alone (on hold).

## 5. Proposed adoption (not a decision)

1. **Order:** (a) the owner confirms D1 to D6; (b) the reviewers go through the table; (c) the cases that survive become an **extension** of their own, never edits of the approved file.
2. **Where and how:** a separate extension file (it keeps the format of `extension-cases.yaml`, with the typed pins as YAML text; the format of the approved file cannot carry typed pins or nested schema documents), with **its own SHA-256 reference stated in the pull request that adds it** and checked by the integrity tooling of #50 (byte-level canaries for escape-shaped text, an acceptance run with an explicit value, the unchanged-check against the approved file); the identifiers `E-*` stay.
3. **The counts:** 513 approved vectors plus the accepted extension cases (560 if all 47 are accepted unchanged); the approved 513 keep their separate integrity reference and are **never** merged into a new file. A first implementation is accepted against the approved set and, once accepted, against the extension too; the two results are reported separately.
4. **What the extension adds to the traceability:** it gives vectors to requirements that the approved set covers only through flat schemas (`R-SCHEMA-ORDER` with nesting, the reader boundary of `R-SCHEMA-WHOLE`, the typed pins of `R-PIN-*`). The requirement list itself does not change.

## 6. Not verified, and open points

* The derivations are by one author; the executable reading is by the same author and delegates the classification of an expression to the existing prototype.
* The cases test the rules of the specification, not an implementation: no implementation exists.
* The decisions D1 to D6 are not owner-confirmed; D7 and D8 are on hold and untouched.
* Whether the extension keeps its own format or the approved format is extended (a new `vectors_format`) is open; this package proposes the former so that the approved file stays unchanged.
