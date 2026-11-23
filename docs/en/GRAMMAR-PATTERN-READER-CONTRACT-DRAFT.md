# The `pattern` profile: the reader contract (OP-1), DRAFT 1 for review

**A draft specification and its draft test vectors: documentation and isolated tooling only.** It is **not accepted**, **not a publication**, **not a normative vector set** and **not an implementation**; it does not close G-0, change the CI, change an approved file or start the reader. The 513 approved vectors (SHA-256 `e7ece43a9486187c16a482a96a86d22cf82407711be940920155f4e3abe277e0`) and the 47 accepted extension cases are untouched. Data: `docs/design/pattern-profile-reader/reader-contract.yaml` (the rules) and `reader-vectors.yaml` (the draft vectors); check: `docs/evidence/reader-contract/`. Base: `devel` at `530066e0b06442f0f5d5857494d17e98f9d4a1a3`.

## 1. What this is for

The owner decided on 2026-11-23 that the reader of the pattern profile follows **the YAML 1.2 Core Schema, preserves types and applies strict reader rules** (record `docs/design/pattern-profile-plan/decisions.yaml`, OP-1). The plan asks, as evidence of gate G-0, *the specification text that fixes OP-1*. This draft is that text, in draft: the **meaning** of reading a document into a typed tree, written down **before** any implementation and **not derived from the behaviour of any parser**. The implementation specification (#52) states what the reader delivers (O-RD-01 to O-RD-06: source order, reader errors, raw typed pins, string keys of the schema document); this draft states how a document becomes that typed tree: how a scalar gets its type, which tags exist, what a key is, when two keys are the same, what is refused and in which order.

## 2. What is decided, what is recommended, what is proposed

Every rule carries its **basis**: `owner_decision` (stated in the owner's decision of 2026-11-23 or an earlier one: the Core Schema, type preservation, strict rules, the duplicate key as a reader error), `review_recommendation` (the review of 2026-11-23: the exact set of explicit tags, no aliases and no merge keys), or `proposal` (the author's proposal: **the owner has not decided it**). Where an alternative exists the point is also an **open question** (section 8). The draft does not claim more than that: a rule of basis `proposal` is a candidate.

## 3. The model and the rules

The tree has null, bool, int (arbitrary precision), float (IEEE binary64 with NaN and the infinities), str (a sequence of Unicode code points), seq (ordered) and map (an **ordered** list of (key, value) entries). The rules:

<!-- BEGIN RULES TABLE -->
| Rule | Basis | Topic | Rule text | Error kinds |
|---|---|---|---|---|
| RC-01 | proposal | encoding | The input is UTF-8 text. Bytes that are not valid UTF-8 (including an encoded lone surrogate), a UTF-8 byte order mark and any UTF-16 or UTF-32 input are the reader error `encoding`. Valid UTF-8 is read as a sequence of Unicode code points, with no normalisation. | `encoding` |
| RC-02 | proposal | documents | The input holds exactly one YAML document. No document (an empty input, or only comments or document markers) is `empty_document`; more than one document is `multiple_documents`. A single document may be written with the markers `---` and `...`. | `empty_document`, `multiple_documents` |
| RC-03 | proposal | directives | Any directive (`%YAML`, `%TAG`, a reserved one) is the reader error `directive_not_allowed`: the contract is for one fixed reading and a directive changes it. | `directive_not_allowed` |
| RC-04 | owner_decision | syntax | The input is YAML 1.2 (block and flow styles). Input that is not well-formed YAML 1.2 is `yaml_syntax`. A syntax error takes precedence over every other reader error (RC-17), whatever precedes or follows it. | `yaml_syntax` |
| RC-05 | owner_decision | scalar-resolution | A PLAIN (unquoted) scalar is resolved by the YAML 1.2 Core Schema and by nothing else, in this order: null (`~`, `null`, `Null`, `NULL`, and the empty plain scalar), bool (`true`, `True`, `TRUE`, `false`, `False`, `FALSE`), int (RC-07), float (RC-08); every other plain scalar is a str. No other implicit type exists: no timestamp, no binary, no set, no sexagesimal number, no `y`/`n`/`yes`/`no`/`on`/`off` booleans. | none |
| RC-06 | owner_decision | scalar-resolution | A quoted (single or double) scalar and a block scalar (`/`, `>`) is always a str, whatever its text looks like (`'1'`, `"true"`, `'~'`, `''` are strs). | none |
| RC-07 | owner_decision | scalar-resolution | An int is `[-+]?[0-9]+` (base 10; leading zeros do not make an octal: `010` is the int 10), `0o[0-7]+` (octal) or `0x[0-9a-fA-F]+` (hexadecimal, lower-case `0x`). Its value is an arbitrary-precision integer with no overflow. `-0` is the int 0. No other form is an int: no `_` separator, no `0b`, no `0`-prefixed octal, no `,`. | none |
| RC-08 | owner_decision | scalar-resolution | A float is `[-+]?(\.[0-9]+/[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?`, or an infinity `[-+]?\.(inf/Inf/INF)`, or a not-a-number `\.(nan/NaN/NAN)` (unsigned). The value is the IEEE binary64 nearest to the decimal (ties to even); `-0.0` is a negative zero. A float that rounds to an infinity without being written as an infinity is the reader error `float_overflow`; a float that underflows is rounded (a subnormal or a zero) and accepted. | `float_overflow` |
| RC-09 | owner_decision | scalar-resolution | Booleans and nulls have exactly the spellings of RC-05. `tRUE`, `NULl`, `yes` and `~~` are strs. | none |
| RC-10 | owner_decision | type-preservation | Type preservation. The reader delivers the type class the rules give (null, bool, int, float, str, seq, map) and never coerces one to another: `1`, `true`, `1.0`, `'1'` and `null` are five different values. A host-language representation that treats two of them as equal (a Python dict that merges the keys 1, True and 1.0) is not an allowed representation. | none |
| RC-11 | review_recommendation | tags | Explicit tags. Exactly seven tags are honoured, written `!!name` or `!<tag:yaml.org,2002:name>`: `str`, `int`, `float`, `bool`, `null`, `seq`, `map`. A tag fixes the type class and the value is read by the rule of that type on the node's text, quoted or not: `!!str` makes the text a str, `!!int` needs the int syntax of RC-07, `!!float` the float syntax of RC-08 (digits alone are a float syntax), `!!bool` and `!!null` their spellings; `!!seq` needs a sequence node and `!!map` a mapping node. A tag that does not fit its node is `tag_mismatch`. Every other tag (the non-specific `!`, a local `!x`, any other global tag, `!!set`, `!!omap`, `!!binary`, `!!timestamp`, `!!merge`, `!!python/...`, a verbatim tag of another name) is `tag_not_allowed`; that check comes before the fit check. | `tag_not_allowed`, `tag_mismatch` |
| RC-12 | review_recommendation | aliases | No anchor (`&a`), no alias (`*a`, defined or not) and no merge key: an anchor is `anchor_not_allowed`, an alias `alias_not_allowed`, and a mapping key whose str value is `<<`, in any quoting, is `merge_key_not_allowed`. The tree has no shared structure and no expansion. | `anchor_not_allowed`, `alias_not_allowed`, `merge_key_not_allowed` |
| RC-13 | owner_decision | keys | A mapping key is a scalar of any type class (a null key is a key); a sequence or a mapping used as a key is `non_scalar_key`. In `schema` mode every key must be a str, else `non_string_key` (O-RD-06). | `non_scalar_key`, `non_string_key` |
| RC-14 | owner_decision | keys | Two keys of one mapping that are identical by RC-15 are the reader error `duplicate_key` (reported at the second). Keys of different type classes are different keys (`1`, `true`, `1.0`, `'1'` can stand in one mapping). The rule applies at every depth; keys of different mappings never clash. | `duplicate_key` |
| RC-15 | owner_decision | identity | Identity of scalars: the type class first; null equals null; bools by value; ints by mathematical value (`010`, `10` and `0xA` are one int); floats by the IEEE binary64 bit pattern, with every NaN identical to every other NaN and `0.0` different from `-0.0`; strs by code point sequence, case-sensitive, no normalisation (a plain and a quoted spelling of the same text are one str). Seqs are identical element by element in order, maps as sets of entries (a map is identical to another when the same keys carry identical values, in any order). | none |
| RC-16 | owner_decision | order | Mapping entries are exposed in SOURCE order and sequence items by index (O-RD-01); the tree is an ordered list of entries, and the order is part of what a conformance vector states. | none |
| RC-17 | proposal | precedence | Precedence of the reader errors: `encoding`, then `yaml_syntax`, then `directive_not_allowed`, then `empty_document` and `multiple_documents`, then the semantic errors in SOURCE order of the offending node (depth-first, pre-order; for a duplicate key the second key). Within one node: `anchor_not_allowed`, `tag_not_allowed`, `tag_mismatch`, `float_overflow`, and for a key `merge_key_not_allowed`, `non_scalar_key`, `non_string_key`, `duplicate_key`. Exactly one error is reported. | none |
| RC-18 | owner_decision | boundary | The reader's result is a typed tree or one reader error, nothing else. A reader error has no pattern code and the pattern validator never sees the document (O-RD-02). The errors of the schema layer (`expression_not_a_string`, D5) are decided by the layer that knows the schema and are outside this contract's scalar reader; the specification's tree-level rules (O-RD-03 document order of contracts, O-RD-04 raw typed pins) take this tree as their input. | none |
| RC-19 | owner_decision | independence | Independence of parsers. The meaning of a document is these rules. The implicit typing of a host YAML library is not a source of truth: an implementation shows it conforms by the vectors, and any parser that disagrees is wrong for this contract, not the contract for the parser. | none |
<!-- END RULES TABLE -->

**Why a contract of its own and not "what PyYAML does".** The two differ on many scalars (`010` is the int 10 here and the int 8 in YAML 1.1; `on`, `off`, `yes`, `no` are strs here and bools in YAML 1.1; `1_000`, `0b10`, `1:30`, `2001-01-01` are strs here), and a Python dictionary merges the keys `1`, `true` and `1.0`, which this contract keeps apart (RC-10, RC-14). A normative meaning that follows one parser is a meaning that changes with that parser (RC-19).

## 4. The boundary with the rest of the specification

* **Reader error versus pattern verdict (RC-18).** The reader returns a typed tree or **one** reader error. A reader error has no pattern code and the pattern validator never sees the document. The error kinds of this contract are the reader's own vocabulary (decision D6); five of them already exist in the specification (`yaml_syntax`, `duplicate_key`, `non_scalar_key`, `non_string_key`, and `expression_not_a_string`, which belongs to the schema layer and is never produced by the scalar reader).
* **How the specification's obligations use this tree.** O-RD-01 (source order) is RC-16; O-RD-02 (syntax errors and duplicate keys as reader errors) is RC-04 and RC-14; O-RD-04 (raw typed pins in a type-preserving representation, no host dictionary that merges keys) is RC-10, RC-13, RC-14 and RC-15; O-RD-06 (string keys of the schema document) is RC-13 in `schema` mode. O-RD-03 (the document order of the contracts) and O-RD-05 (record values) take the tree as their input and are not changed.
* **Precedence (RC-17).** `encoding`, then `yaml_syntax`, then `directive_not_allowed`, then the document count, then the semantic errors in source order, one error only.

## 5. The draft vectors

270 draft vectors, written **from the rules** (the scalar forms of RC-05 to RC-09 one by one, the tags, the keys and their identity, the aliases and merge keys, the directives, the documents, the syntax errors, the encodings, the precedence), each with its rule, its class (positive, negative, boundary) and its expected typed tree or error kind. The coverage per rule:

<!-- BEGIN COVERAGE TABLE -->
| Rule | Positive | Negative | Boundary | Vectors |
|---|---|---|---|---|
| RC-01 | 4 | 7 | 0 | 11 (V-UN-001 .. V-EN-010) |
| RC-02 | 3 | 7 | 0 | 10 (V-DC-001 .. V-DC-010) |
| RC-03 | 0 | 4 | 0 | 4 (V-DR-001 .. V-DR-004) |
| RC-04 | 0 | 13 | 0 | 13 (V-SY-001 .. V-SY-013) |
| RC-05 | 10 | 19 | 1 | 30 (V-SC-001 .. V-SC-104) |
| RC-06 | 12 | 0 | 1 | 13 (V-SC-107 .. V-BL-003) |
| RC-07 | 8 | 14 | 10 | 32 (V-SC-029 .. V-SC-060) |
| RC-08 | 20 | 13 | 6 | 39 (V-SC-061 .. V-SC-106) |
| RC-09 | 0 | 5 | 0 | 5 (V-SC-006 .. V-SC-010) |
| RC-10 | 4 | 0 | 0 | 4 (V-KY-016 .. V-KY-020) |
| RC-11 | 18 | 27 | 0 | 45 (V-TG-001 .. V-TG-045) |
| RC-12 | 3 | 11 | 0 | 14 (V-AL-001 .. V-AL-014) |
| RC-13 | 3 | 9 | 0 | 12 (V-KY-021 .. V-KY-033) |
| RC-14 | 1 | 6 | 0 | 7 (V-KY-001 .. V-KY-037) |
| RC-15 | 1 | 10 | 2 | 13 (V-UN-002 .. V-KY-017) |
| RC-16 | 3 | 0 | 0 | 3 (V-KY-034 .. V-KY-036) |
| RC-17 | 0 | 15 | 0 | 15 (V-PR-001 .. V-PR-015) |
| RC-18 | 0 | 0 | 0 | none (a meta rule) |
| RC-19 | 0 | 0 | 0 | none (a meta rule) |
<!-- END COVERAGE TABLE -->

The typed notation is language-neutral: a float is its 16 hex digits of the IEEE binary64 bit pattern (so that `0.0` and `-0.0`, NaN and the infinities are exact), an int is its decimal text, a map is an ordered list of entries. Two rules have no vector, and say why: RC-18 (the boundary) and RC-19 (independence from parsers) are statements about how the contract is used, not about a document.

## 6. How the draft was checked

`check_reader_contract.py` (exit 0, `results/check_reader_contract.txt`): the rule ids are unique; every error kind of the contract is produced by a negative vector, and every kind a rule names by a vector **of that rule**; every rule except the two meta rules has vectors; the vectors are well-formed; **a reference reading of the rules** gives the expected result of every one of the 270 vectors (0 differences); **the 47 accepted extension cases agree with the contract at the reader level** (a case that expects a reader error of the scalar reader is refused with that kind, in the pin text or in the schema document; every other case is read without a reader error); the tables of this document equal the tables rendered from the data.

The **reference reading** (`reference_reader.py`) is an executable reading of the rules and **not** the implementation and **not** a conformant YAML 1.2 parser: it takes from PyYAML only the **syntax** (the event stream) and decides everything else itself; PyYAML's implicit typing and constructors are never used. Where PyYAML's syntax differs from YAML 1.2 the vectors avoid the construct (OQ-7).

`selftest_reader_contract.py` shows that the check can fail, for the right reason: the reference reading carries planted defects (the YAML 1.1 booleans, octal and underscore integers; duplicate keys found by the host language's equality; aliases accepted; merge keys accepted; any tag accepted; an overflowing float read as an infinity; a byte order mark accepted; a duplicate key ignored), and each is caught by the vectors that state the rule; it also plants faults in the data and in the document.

## 7. A measurement made AFTER the contract: PyYAML

<!-- BEGIN MEASUREMENT TABLE -->
| PyYAML 6.0.3 over 270 draft vectors | Vectors |
|---|---|
| agrees with the contract | 178 |
| reads a value that differs from the contract | 35 |
| accepts a document the contract rejects | 56 |
| rejects a document the contract reads | 1 |
<!-- END MEASUREMENT TABLE -->

This is a measurement of one parser against the draft, **not a source of the contract** and not a conformance verdict on the profile. What it says is where an implementation built on `yaml.safe_load` would have to differ from its default: it types the YAML 1.1 scalars, merges keys of different types, expands aliases and merge keys, and honours tags the contract refuses. `results/pyyaml-measurement.json` lists the vector ids by class; the numbers depend on the PyYAML version (recorded).

## 8. Open questions for the owner

The questions below are **not decided**; the draft answer is what the vectors currently encode. **This is the decision table for the owner**: for each question the draft answer, the alternative, **the vectors that would change if the alternative were chosen, and what the owner has to provide**. The list of changing vectors is **computed**, not claimed: the reference reading is switched to the alternative answer (`CIC_READER_ALT`) and every vector whose result changes is listed; the check fails if a question claims another set. Two questions are answered with numbers or with a reference and not with the switch of a rule (OQ-3, OQ-7): no vector changes until they are answered.

Two observations from the computation: the question about explicit tags (OQ-4) is the widest (33 vectors change if every tag is forbidden: the whole tag group, a document with a tagged root and one precedence vector), and **some answers change more than the rule suggests** (the `%YAML 1.2` directive, OQ-10, also changes two precedence vectors; a tag on a quoted scalar, OQ-9, also changes a null-tag vector; the null key, OQ-12, four vectors).

<!-- BEGIN QUESTIONS TABLE -->
| Question | Rules | Question text | Draft answer | Alternative | Vectors that change if the alternative is chosen (computed) | The owner provides |
|---|---|---|---|---|---|---|
| OQ-1 | RC-01 | A UTF-8 byte order mark: reject (the draft) or accept and ignore? | reject | accept a leading UTF-8 byte order mark and ignore it | 1: V-EN-005 | choose the draft or the alternative |
| OQ-2 | RC-02 | An empty input or only comments: the reader error `empty_document` (the draft) or a document whose value is null? | reader error | an empty input, or only comments, is a document whose value is null | 4: V-DC-001, V-DC-002, V-DC-003, V-DC-004 | choose the draft or the alternative |
| OQ-3 | RC-04 | Limits of the reader (document size, nesting depth, node count, scalar length) are NOT fixed: a fail-closed reader needs them, and no number is chosen here. Which values, and as a reader error of which kind? | open; no vector | none: a number or a reference, not a switch of a rule | none: the question is answered with numbers or a reference, not with a switch of a rule; no vector changes until it is answered | the LIMITS (maximum document size, nesting depth, node count, scalar length) and the reader error kind for exceeding them (a new kind, for example `limit_exceeded`); no number is proposed here; the vectors at n and n+1 are written after that |
| OQ-4 | RC-11 | May explicit tags be used at all? The draft honours the seven core tags; the stricter alternative forbids every tag (every tag is `tag_not_allowed`), which is simpler to implement and to check. | seven core tags | forbid every explicit tag (every tag is `tag_not_allowed`): simpler to implement and to check | 33: V-TG-001, V-TG-002, V-TG-003, V-TG-004, V-TG-005, V-TG-006, V-TG-007, V-TG-008, V-TG-009, V-TG-010, V-TG-011, V-TG-012, V-TG-013, V-TG-014, V-TG-015, V-TG-016, V-TG-017, V-TG-018, V-TG-019, V-TG-020, V-TG-021, V-TG-022, V-TG-023, V-TG-024, V-TG-025, V-TG-038, V-TG-039, V-TG-040, V-TG-041, V-TG-042, V-TG-043, V-DC-010, V-PR-010 | choose the draft (seven core tags) or the stricter alternative |
| OQ-5 | RC-08 | A float that overflows (`1e999`): the reader error `float_overflow` (the draft) or an infinity? | reader error | an overflowing float is the infinity | 3: V-SC-105, V-SC-106, V-PR-011 | choose the draft or the alternative |
| OQ-6 | RC-12 | A quoted key `"<<"`: rejected as a merge key in any quoting (the draft, because parsers disagree on the plain form) or allowed as an ordinary string key? | rejected | only the plain spelling `<<` is a merge key; a quoted `"<<"` is an ordinary str key | 2: V-AL-009, V-AL-010 | choose the draft or the alternative |
| OQ-7 | RC-04 | Syntax strictness beyond YAML 1.2 (tabs as indentation, duplicate or odd directives, very exotic plain scalars) is decided by the parser; the vectors state only clear cases. Is a named syntax reference (the YAML 1.2.2 grammar) enough, or must an accepted parser be named? | the YAML 1.2.2 grammar; vectors for clear cases only | none: a number or a reference, not a switch of a rule | none: the question is answered with numbers or a reference, not with a switch of a rule; no vector changes until it is answered | the reference of syntax conformance: the YAML 1.2.2 grammar (the draft) or a named parser together with a YAML test suite; no vector can state this |
| OQ-8 | RC-11 | `!!float 1` (digits only) is a float 1.0 by the Core Schema float expression: confirm. | float | `!!float 1` is `tag_mismatch` (a float needs a dot or an exponent) | 1: V-TG-008 | choose the draft or the alternative |
| OQ-9 | RC-11 | An explicit tag on a quoted scalar (`!!int "10"`) reads the text by the tag: confirm (the draft) or make it an error? | read by the tag | a tag other than `!!str` on a quoted scalar is `tag_mismatch` | 2: V-TG-007, V-TG-014 | choose the draft or the alternative |
| OQ-10 | RC-03 | Is even `%YAML 1.2` refused? The draft refuses every directive. | refuse all | `%YAML 1.2` is accepted, every other directive is refused | 3: V-DR-001, V-PR-002, V-PR-003 | choose the draft or the alternative |
| OQ-11 | RC-08, RC-15 | All NaNs identical (the draft, as in the specification's identity of pin values) and no payload is distinguished: confirm. | identical | NaN is not identical to NaN (two NaN keys are not a duplicate) | 2: V-KY-009, V-KY-010 | choose the draft or the alternative |
| OQ-12 | RC-13, RC-15 | A null key in a pin value mapping is a key (the draft, consistent with section 3 of the specification): confirm. | a key | a null key is refused (a new error kind `null_key`) | 4: V-KY-011, V-KY-019, V-KY-021, V-KY-029 | choose the draft or the alternative |
<!-- END QUESTIONS TABLE -->

## 9. Not shown, and what comes next

* **Not accepted:** nothing here is accepted by a review or by the owner; the basis `proposal` rules are candidates.
* **The vectors are written by the author of the rules**, and the reference reading too: the independence test is the review, and later an implementation by another author in another language from the rules and the vectors alone (on hold).
* **Limits of the reader are not fixed** (OQ-3): a fail-closed reader needs a maximum size, depth and node count; no number is chosen, so no vector states one.
* **The reference reading is not a YAML 1.2 parser.** Syntax questions beyond clear cases (tabs, exotic plain scalars) are left to a named grammar (OQ-7); a full conformance claim needs a YAML 1.2 test suite, which is not part of this draft.
* **The schema layer's errors** (for example a pattern contract whose expression is not a string) are decided by the layer that knows the schema (RC-18, D5); this draft does not specify them.
* **G-0:** this text is the *kind* of evidence the plan asks of G-0 for OP-1, but **nothing has been recorded**: recording a specification text in the decision record, and the review of this draft, are separate steps and the owner's. The G-0 check still reports `NOT_READY` until then.
* **Next, if the owner so decides:** the review of the draft; the owner's answers to the open questions; the reader-test vectors become a separately reviewed extension; only then a reader implementation (on hold, with all the other holds: the implementation, the CI, the normative publication).
