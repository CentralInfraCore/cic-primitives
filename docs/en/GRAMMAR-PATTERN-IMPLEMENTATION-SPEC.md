# The `pattern` profile: implementation specification (draft)

Status: **a draft specification, documentation and isolated tooling only. This is not permission to implement.** Executing it (writing a validator, a producer or a verifier, a gate, publishing the vectors) needs a separate owner GO. Not in this package, all on hold: any implementation, the CI gate, normative publication of the vectors, changes of schemas, the Forms, the grammar or any checker, P2, P4, Forms #166/#167, the release-schema finalization, the Relay #162 implementation.

It builds on what is decided and merged: the profile (`GRAMMAR-PATTERN-PROFILE-DESIGN.md`, #46), the evaluator direction (`GRAMMAR-PATTERN-ENGINE-SELECTION.md`, #47: E1 own automaton, E2 optional google-re2 cross-check, E3 version evidence), the limits and codes (`GRAMMAR-PATTERN-LIMITS-AND-ERRORS.md`, #48), the 513 vectors (`GRAMMAR-PATTERN-VECTORS.md`, #49 to #51) and the profile version `1`. **The 513 approved vectors stay the unchanged reference** (the SHA-256 of the vector file, `e7ece43a...`, is held by the check of this package). New cases appear only as a **separately reviewed extension** (section 10); none is added to the approved file.

The machine-readable companions: `docs/design/pattern-profile-spec/obligations.yaml` (26 obligations and 11 plan items, traced to the requirements), `docs/design/pattern-profile-spec/extension-cases.yaml` (40 proposed cases), and the tooling in `docs/evidence/pattern-spec-trace/`.

## 1. Roles and the boundary between them

The Primitives define **the deterministic semantics of the processing parameters that belong to a key:value pair's key**; they do not own the traversal of a document. Five roles:

| Role | Owns | Does not own |
|---|---|---|
| **document reader** | the YAML and its syntax, duplicate keys, the composition of the schema parts, the structure (a pattern contract has a string expression), the **order** in which contracts and values are delivered, the raw typed pin declarations, the extraction of the record values to be checked | any verdict about an expression, a pin value or a value |
| **pattern validator** | the pin resolution, the classification of an expression (accept with its size PI, or refuse with one code), the evaluation of a value, the rule "the first refused contract in the order given decides" | where a contract or a value comes from, in which order the document is walked, YAML, the type of a node |
| **producer** | building a release: resolving the pin, classifying every expression, refusing a build on any refusal, refusing to emit a violating value | trusting anything a verifier says |
| **verifier** | repeating all of it **independently**, never relying on the producer; its own total budget | the producer's code, verdicts or versions |
| **gate** (on hold) | running the vectors and the extension cases against every implementation, recording the run evidence | the semantics |

**The interface of the pattern validator** (language-neutral; the names are descriptive, not an API decision):

* `resolve_pin(declarations) -> ok | pattern_profile_missing | pattern_profile_conflict | pattern_profile_unknown`, where `declarations` is the list of raw typed values the reader found, in document order;
* `classify(expression: string) -> accept(PI) | refuse(code)`, with the 25 expression codes;
* `check_value(expression, value: sequence of code points) -> match | pattern_value_mismatch | pattern_value_too_long | pattern_value_not_unicode_scalar`;
* `validate_schema(declarations, contracts: ordered list of (path, expression)) -> accept | refuse(code, path)`.

The validator never receives a document, a YAML node or a non-string.

## 2. The document reader (obligations O-RD-01 to O-RD-05)

* **O-RD-01 Source order.** A mapping's entries are exposed in **source order** and a sequence's items by index. An implementation language whose default map loses the order (a Go `map`, an unordered hash map) must use an order-preserving representation (a YAML node API, an insertion-ordered map).
* **O-RD-02 Reader errors.** A duplicate mapping key, a YAML syntax error, and a pattern contract whose `expression` is absent or not a string are **reader errors**: they happen before the validator runs, they have **no pattern code**, and the validator never sees them. (The duplicate key is the reader's responsibility by the owner decision of 2026-11-22.) The vocabulary of the schema layer's own errors is not specified here (section 12).
* **O-RD-03 Document order of the contracts.** The pattern contracts of the composed schema are delivered to the validator in **document order**: a depth-first, pre-order walk of the composed schema; mapping entries in source order; sequence items by index. A *pattern contract* is a mapping with `type: pattern` that is an element of a `contract` sequence (other contracts are skipped); it is visited **where its key `contract` stands among its siblings**, so a node whose `fields` stand before its `contract` in the source has its children's contracts delivered first. The order is the reader's rule, not a property of the pattern validator, and not a fixed order of schema keys (the release schemas are still DRAFT). Examples: `E-TRV-01` to `E-TRV-07`.
* **O-RD-04 Raw typed pin declarations.** The pin (`spec.pattern_profile.version`, O1) is delivered as the **raw typed value** of each declaration, in document order, with no coercion: `1`, the text `1`, `1.0`, `true` and `null` are five different values. A declaration whose value is `null` is a declaration; an absent key is no declaration. The pin is a property of the schema and of the processing context, **never a document (record) key**.
* **O-RD-05 Record values.** The values of a record that are checked against a pattern contract are extracted by the record layer, in the record's own document order. A value that is not a string is not a verdict of the pattern profile; the type contract of the node decides. A string is delivered as a **sequence of Unicode code points**; a lone surrogate is flagged, never silently replaced (Go and Rust strings cannot hold one, so the reader decides before the conversion: plan item P-05).

## 3. The pin: resolution and wrong types (obligations O-VA-01, O-VA-02)

The profile version identifier is the positive integer `1` (decision of 2026-11-22); the current profile knows only `1`; there is no implicit default; an unknown version is refused.

**O-VA-01 Resolution**, over the declarations in document order, **in this order**:

1. no declaration: `pattern_profile_missing`;
2. the declarations are not all **identical** (the identity rule below): `pattern_profile_conflict` (this precedes unknown: `[1, 99]` is a conflict);
3. identical declarations count as **one** declaration; the single value that is not exactly the **int `1`** (type `int`, value `1`) is `pattern_profile_unknown`.

**The identity of declared values (review F1 of #52).** The identity is a rule of this specification, **not** a property of any serialisation (a JSON or `str` rendering would let a mapping with the key `1` and one with the text key `1` look alike, differ in their sort behavior on mixed key types, or turn different types into the same text). Two values are identical iff they have the **same type class** and:

| Type class | Identical when |
|---|---|
| null | both are null |
| bool | the same truth value (a bool is **not** an int: `true` and `1` are different) |
| int | the same integer |
| float | the same IEEE-754 binary64 bit pattern; **all NaN are identical to each other**; `0.0` and `-0.0` are different; a float is never identical to an int (`1.0` and `1` differ) |
| string | the same sequence of Unicode code points |
| list | the same length and pairwise identical items **in the same order** |
| mapping | the same number of entries and every entry of one has an entry of the other with an **identical key (the key's type class counts: the int `1` and the text `1` are different keys)** and an identical value; **the order of the entries is irrelevant** |

The rule is recursive. A mapping key that is not a scalar is a **reader error** (outside the pattern codes). The resolution depends only on the **set** of the declarations, not on their order. Examples: `E-PIN-18` to `E-PIN-27` (a `1` key against a text `1` key is a conflict; the same mapping in another entry order is identical; `[1, 2]` against `[2, 1]` is a conflict; `1` against `1.0` is a conflict; NaN with NaN is identical; `0.0` against `-0.0` is a conflict; nested values).

**A wrong-typed pin** (`true`, `1.0`, the text `1`, `null`, `0`, a negative number, a list, a mapping) is therefore **`pattern_profile_unknown`**: it is a value that is not a member of the set of known versions `{1}`, and **no new code is introduced** (a new code would change the version-1 code set, which needs a new profile version). Two identical wrong-typed declarations are unknown; two different ones are a conflict. Examples: `E-PIN-01` to `E-PIN-13`, `E-PIN-16`, `E-PIN-18` to `E-PIN-27`.

**O-VA-02 When.** The pin is evaluated **only when the schema has at least one pattern contract**, and **before every expression** (a bad pin is reported even when an expression is also bad: `E-PIN-17`). A schema without a pattern contract needs no pin; its declarations, whatever they are, are not evaluated (`E-PIN-14`, `E-PIN-15`; this reading of the existing vectors `S-008`, `S-009` is one of the points for the owner in section 12).

## 4. The validation order and the error precedence

| Step | Layer | What | Errors (and where they are defined) |
|---|---|---|---|
| 0 | document reader | syntax, duplicate keys, composition, structure, order, extraction | reader errors, **no pattern code** (O-RD-02) |
| 1 | pattern validator | the pin, only if at least one pattern contract exists | `pattern_profile_missing`, `_conflict`, `_unknown` (O-VA-01, O-VA-02) |
| 2 | pattern validator | each expression, in the order the reader delivers them: tier 1, the scan, tier 3; the **first refused expression** decides code and path; the schema is refused **as a whole** | the 25 expression codes (O-VA-03 to O-VA-09; the rule order of limits doc 3.2) |
| 3 | producer and verifier | each record value: scalar value, then length, then match | the 3 value codes (O-VA-11, O-VA-12) |

* An error of an earlier step is reported before any later step runs. **A schema refused at step 0, 1 or 2 means that no value is evaluated against it** (O-VF-02).
* Within step 2 the precedence across expressions is the **document order**, whatever the tier of each refusal (a tier-3 refusal of an earlier contract wins over a syntax error of a later one: vector `S-012`, `S-013`).
* Within one expression the order is that of limits doc 3.2 (O-VA-03 to O-VA-08, already covered by the 513 vectors).
* Within step 3 the first violating value in the record reader's order decides; a verifier may collect more, with no normative weight.

### 4.1 Binding a result to its input: the delivery digest (review F2 of #52, obligation O-GT-02)

Which refusal is reported first depends on the **delivery order**, which for a source-order traversal depends on the **source order** of the document. A canonical representation that sorts the keys would erase exactly that difference, so its hash alone cannot identify the input of a validation **result**. The specification separates two things:

* **the class of the verdict** (accepted or refused) does **not** depend on the delivery order (a schema is accepted iff every expression is accepted and the pin resolves; the pin resolution depends only on the set of the declarations). A result may therefore be reused **for the class** by the **content digest** (the order-erasing digest of the contracts);
* **the reported code and path** depend on the delivery order. A result is reused **for the code and the path only by the delivery digest**: SHA-256 over a **length-prefixed** encoding of the **ordered** list of `(path, expression)` pairs as the reader delivered them (each path as typed segments, an index or a text; each expression as UTF-8; no serialisation library is part of the definition).

The evidence of a validation result names the **delivery digest**, the profile version identifier and the implementation that ran (E3). Two documents with the same canonical content and a different source order have the same content digest, **different delivery digests**, the same class and, where the first refusals differ, a different code (`E-TRV-01` against `E-TRV-02`). The rule of the composition (how schema parts are merged and in which order) stays on hold (D7); what is fixed here is that **whatever order the reader delivers is part of the input identity of the result**. Property test: plan item P-10, `check_spec_trace.py` (section 9).

## 5. Producer and verifier obligations

**Producer** (O-PR-01, O-PR-02): when building a release, resolve the pin of the composed schema and classify every expression in document order, **refuse the build** on a pin error or a refused expression (no fallback to a native engine, no partial acceptance); check every pattern-constrained value it emits and **refuse to emit a violating one**, checking it itself.

**Verifier** (O-VF-01 to O-VF-04):

* **O-VF-01** repeat steps 0 to 3 **independently**, **the document reader included**: never rely on a producer-supplied verdict, version, classification or delivery order;
* **O-VF-02** a refused schema is refused before any value is evaluated;
* **O-VF-03** a verifier of untrusted input applies **its own total work budget** (the unit `PI x code points`, summed over the values; not milliseconds), reported with **its own code, not a pattern code**; each distinct expression is compiled once; the profile bounds one expression and one value, not a document (limits doc 2.5);
* **O-VF-04** (producer too) the run evidence names the implementation that actually ran (name, version, hash of the evaluator source) and earlier conformance evidence is not inherited (E3).

The review remark that a verifier's total budget must not rest only on `PI x value length` (an empty value and a zero-size program also cost something) is taken as a requirement on the verifier's budget design: a fixed cost per contract and per value is part of it (plan item P-04).

## 6. The evaluator (obligation O-VA-13) and language notes

**O-VA-13** The evaluator is **linear** in the program size times the value length and **never backtracks** (an automaton or an RE2-class evaluator; a backtracking engine is not eligible). Its **deterministic work** `W` (a count of state visits, not milliseconds) is bounded by

`W <= c x (PI + 1) x (N + 1)`

and **not** by `c x PI x N` (review F3 of #52): the latter allows zero work for a zero-size program (`PI = 0`, accepted by the profile: `a{0}`) and for the empty value (`N = 0`), and both cost something (the start state is entered and the accept state is checked). `work_bound.py` measures it on a corpus that includes the zero-size programs and the empty value (95 pairs, 27 of them with `PI = 0` or `N = 0`): the largest observed ratio `W / ((PI+1)(N+1))` is 1.36, the provisional constant 8 holds on every pair, and the first form is refuted by measurement for every `c` by those 27 pairs. The exact constant and the counted operations are fixed in the implementation measurement plan; a measured ratio is not a guarantee. Informative notes that the vectors cannot express:

* a length is counted in **code points**: Go's `len` and Rust's `len` count bytes, UTF-16 languages count units (O-VA-12);
* the native Go `regexp` and Rust `regex` take the translated body (`\A(?:body)\z`) only **after** the expression was accepted by the validator's own classification; they are never the classifier (the vectors compare them, rule D);
* an expression that the classifier accepts must compile in every engine of the run.

## 7. Traceability: the 66 requirements and the obligations

**What this table and the check prove, and what not (review F4 of #52):** the check shows **structural traceability** (every requirement is named by an obligation, every cited plan item exists) **and** that each requirement of an obligation is actually *covered* by what the obligation cites (the approved vectors that name it, or a cited plan item whose own requirement list includes it), and that the text and the machine-readable contract agree where an obligation carries a must-contain phrase (for example O-VF-01: steps 0 to 3). It does **not** show that the plan items, once executed, give full **semantic** coverage; that is what the plan's evidence is for.

`obligations.yaml` names, for each of the 26 obligations, its roles, its requirements and how it is verified (the approved vectors, a plan item, or both); `check_spec_trace.py` refuses the package if **any** of the 66 requirements, or any of the 4 that a verdict vector cannot test, is not named by an obligation (`results/check_spec_trace.txt` prints the matrix both ways). In groups:

| Obligations | Requirements | Verified by |
|---|---|---|
| O-RD-01, O-RD-02, O-RD-03 | `R-SCHEMA-ORDER`, `R-SCHEMA-WHOLE` | plan P-06, P-08, P-09 |
| O-RD-04, O-VA-01, O-VA-02 | `R-PIN-*` | the vectors `S-002` to `S-009`, `S-017` to `S-020`, and plan P-07 |
| O-RD-05, O-VA-12 | `R-VALUE-*`, `R-LIM-VALUE` | the vectors, and plan P-05 |
| O-VA-03 | `R-T1-*`, `R-BODY-ANCHORS`, `R-LIM-LENGTH` | the vectors |
| O-VA-04 | `R-S1`, `R-S2`, `R-S3-*`, `R-LIM-DEPTH`, `R-PREC-GROUP-EXT-DEPTH` | the vectors |
| O-VA-05 | `R-C1` to `R-C4`, `R-PREC-CLASS-ORDER` | the vectors |
| O-VA-06 | `R-Q*`, `R-LIM-COUNT`, `R-LIM-PRODUCT`, `R-LIM-UNBOUNDED`, `R-PREC-REPEAT-ORDER` | the vectors |
| O-VA-07 | `R-T3-SIZE`, `R-PI-*`, `R-LIM-PI` | the vectors |
| O-VA-08, O-VA-09 | `R-PREC-TIER`, `R-PREC-READING-ORDER`, `R-SCHEMA-ORDER`, `R-SCHEMA-WHOLE` | the vectors, and plan P-08 |
| O-VA-10 | `R-COMPAT-CONTRACTS` | the vectors |
| O-VA-11 | `R-MATCH-*` | the vectors |
| O-VA-13, O-GT-01 | `R-LINEAR` | plan P-01 |
| O-PR-01, O-PR-02, O-VF-01, O-VF-02 | `R-INDEPENDENT-CHECK`, `R-PIN-FIRST`, `R-PREC-TIER`, `R-PIN-MISSING`, `R-SCHEMA-*`, `R-VALUE-ORDER` | plan P-02, P-07, P-11 |
| O-GT-02 | `R-SCHEMA-ORDER`, `R-VERSION-EVIDENCE` | plan P-10, P-03 |
| O-VF-03 | `R-VERIFIER-BUDGET` | plan P-04 |
| O-VF-04, O-GT-01 | `R-VERSION-EVIDENCE` | plan P-03 |

## 8. The verification plan for what the vectors do not cover

| Item | Covers | Kind | Method (short) |
|---|---|---|---|
| P-01 | `R-LINEAR` | non-vector test | a timing gate on the adversarial corpus of #47 and #48, zero-size programs and the empty value included, with a deterministic work counter bounded by `c x (PI + 1) x (N + 1)` (measured in `work_bound.py`), and a generous wall-time bound where counting is not possible |
| P-02 | `R-INDEPENDENT-CHECK`, `R-PREC-TIER` | non-vector test | a producer stub that reports success for violating values and refused expressions; the verifier must refuse them; a verifier fed a disagreeing producer verdict; a refused schema with violating values must be reported as a schema refusal with no value evaluated |
| P-03 | `R-VERSION-EVIDENCE` | non-vector test | the run evidence lists interpreter or toolchain, package versions, the hash of the evaluator source and the lock files; a run without it is INCOMPLETE |
| P-04 | `R-VERIFIER-BUDGET` | non-vector test | synthetic schemas of K worst-case contracts and records of M worst-case values; the verifier stops at its budget with its own code; a fixed cost per contract and per value is included |
| P-05 | `R-VALUE-SCALAR`, `R-VALUE-LENGTH`, `R-LIM-VALUE` | non-vector test | a per-language harness that passes a value as code points (a lone surrogate cannot be a Go or Rust string) and counts code points, not bytes |
| P-06 | `R-SCHEMA-WHOLE`, `R-SCHEMA-ORDER` | reader test | a duplicate key, a syntax error, an expression that is not a string are reader errors with no pattern code; source order is kept in every implementation language |
| P-07 | the pin requirements | proposed extension | `E-PIN-01` to `E-PIN-27` (the identity rule included) |
| P-08 | `R-SCHEMA-ORDER`, `R-SCHEMA-WHOLE` | proposed extension | `E-TRV-01` to `E-TRV-07` |
| P-09 | `R-SCHEMA-ORDER` | proposed extension (open) | after the composition of the release schemas is specified: pin declarations from different parts, the order of several violating values in one record |
| P-10 | `R-SCHEMA-ORDER`, `R-VERSION-EVIDENCE` | non-vector test | the class is invariant under every permutation of the delivery order, the code and path are not; the content digest ties, the delivery digest tells two delivery orders apart; the evidence names the delivery digest |
| P-11 | `R-PIN-MISSING`, `R-SCHEMA-WHOLE`, `R-SCHEMA-ORDER`, `R-VALUE-ORDER` | non-vector test | the approved schema vectors and the extension cases through the producer's build entry point, the value vectors through its emit check: it must refuse exactly as the validator does |

## 9. Evidence of this package

`docs/evidence/pattern-spec-trace/` (typed exits: 0 ok, 1 a measured failure, 2 infrastructure):

* `check_spec_trace.py`, `results/check_spec_trace.txt`: the approved vector file is byte-identical to the approved one; every one of the 66 + 4 requirements is named by an obligation and **actually covered** by what the obligation cites (the approved vectors, or a cited plan item that lists it); an obligation that names a requirement without a verdict vector has a plan item; an obligation verified by vectors names only requirements that have vectors; every role and every plan item is used; the text mentions every obligation and plan id; and **the executable reading** `spec_model.py` evaluates the 40 extension cases (0 differences) and reproduces the verdicts and the positions of the **20 schema vectors of the approved set** under the new rules (reader, pin, traversal): 0 differences.
* the **property and digest checks** of `check_spec_trace.py` (review F2): the accept/refuse class of every multi-contract schema (the approved schema vectors and the traversal cases) is invariant under **every permutation** of the delivery order, while the reported code and path are not (at least one case shows it); the content digest of `E-TRV-01` and `E-TRV-02` is equal and their delivery digests differ.
* `work_bound.py`, `results/work_bound.txt` (review F3): the deterministic work of the own evaluator on 95 (expression, value) pairs, 27 of them with `PI = 0` or `N = 0`: the largest observed ratio `W / ((PI+1)(N+1))` is 1.36, the provisional constant 8 holds on every pair, and the first form `c x PI x N` is refuted by those 27 pairs. Typed exits.
* `selftest_spec_trace.py`, `results/selftest-spec-trace-output.txt` (26 checks): the tooling can fail, for the right reason: a positive control; **14 planted faults** in copies of the obligations, the text, the cases and the vector file (a requirement without an obligation, an unknown requirement, an obligation without verification, an unused plan item, a missing mention, a no-vector requirement claimed as verified by vectors, a role without an obligation, a duplicate id, a case expectation that no longer follows the rules, a case group without a plan item, the approved vector file modified, and, for review F4, **a plan item that does not list the requirement an obligation relies on it for, an obligation text that names fewer steps than the specification, a specification that no longer says steps 0 to 3**); **6 planted defects of the model** (the version compared by Python equality, which accepts `true` and `1.0`; the own contract visited after the children; **identity by a serialisation, which treats a `1` key and a text `1` key alike and crashes on mixed key types, caught both as a wrong verdict and as a model that raised; a verdict class that depends on the delivery order; a delivery digest that erases the order**); **4 checks of the work bound** (the positive control, a planted quadratic evaluator, a constant that is too small, a corpus without a zero-size program or an empty value); and an infrastructure control that exits 2. Each is counted only with the intended `FAIL-EXPECT` line, or the intended exit code.

## 10. The proposed extension cases

`extension-cases.yaml` has 40 cases in three groups: the pin (`E-PIN-*`, 27), the traversal (`E-TRV-*`, 7) and the reader boundary (`E-RDR-*`, 6). Their expected results are derived from the text and evaluated by the executable reading, **not** by an implementation of the profile. **They are not part of the approved vector file.** The path to the normative set: this specification is accepted; the owner decides which cases become vectors; the extension is a package of its own with its own review, a separate file or a version-1 addition decided then, with the same integrity checks; the 513 vectors and their expectations stay as they are.

## 11. Not verified

* No implementation exists; every statement of sections 1 to 6 is a requirement, not a measured behavior. The model is an executable reading of the new rules (it delegates the classification of an expression to the existing prototype), written by the same author as the rules.
* Whether the traversal rule (source order) is the order the owner wants for the release schemas (section 12), and the composition of schema parts into one document, which is not specified.
* The timing, independence, evidence and budget requirements are plans (P-01 to P-04), not tests.
* A third, independent implementation from the text and the vectors alone: on hold.

## 12. Points for the owner

| # | Point | Recommendation in this draft |
|---|---|---|
| D1 | a wrong-typed pin | `pattern_profile_unknown`, no new code (a new code would need a new profile version) |
| D2 | a declaration with the value `null` | a declaration with a non-int value: unknown (an absent key is missing) |
| D3 | a schema without a pattern contract | its pin declarations are not evaluated, whatever they are (the existing vectors cover only missing and ok) |
| D4 | the traversal rule | depth-first pre-order in **source order**, which needs an order-preserving reader; the alternative is a fixed order of the schema keys (`contract`, `fields`, `item_fields`), which ties the profile to a DRAFT schema layout |
| D5 | an expression that is not a string | a reader error with no pattern code |
| D6 | the schema layer's own error vocabulary | not specified here |
| D7 | the composition of schema parts and the order of their pin declarations | open (plan item P-09) |
| D8 | the order of several violating values in one record | the record reader's order; open for the extension (P-09) |

Everything not named here stays on hold: the implementation, the CI gate, the normative publication of the vectors, P2, P4, Forms #166/#167, the schema finalization, the Relay #162 implementation.
