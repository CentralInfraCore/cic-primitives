# The `pattern` profile: resource limits (O2) and normative error codes (O3), decision preparation

Status: **decision preparation, documentation and isolated measurement only.** Not in this pull request: any implementation of the profile, a normative vector set, a CI gate, a change of the grammar, of a checker, of a schema, of the Forms or of a verifier; P2, P4, Forms #166/#167 and the finalization of the release schemas stay on hold. Everything marked *proposal* is a recommendation to the owner, not a decision. The evidence is in `docs/evidence/pattern-limits-errors/`; it builds on the merged engine selection (`GRAMMAR-PATTERN-ENGINE-SELECTION.md`, #47: E1 own Thompson NFA, E2 optional google-re2 cross-check, E3 version evidence, all GO) and on the profile design (`GRAMMAR-PATTERN-PROFILE-DESIGN.md`, #46). **The own NFA is the accepted architectural direction; this prototype is not accepted as a production implementation.**

Measured values below are one run on one machine (Python 3.14 `nfa_engine.py`, Go and Rust through the existing runners). **They are measurements, not guaranteed running-time limits.** The only normative time statement is the asymptotic one (the evaluator is linear in program size times value length, never backtracking).

## 1. A correction first: the candidate limits do not bound the program

The profile design (3.4) says the limits "bound the size" of the compiled program, and the engine-selection document (2.7) called a 6376-state program "the largest valid program measured". **Both statements are wrong, and the 38.45 ms maximum handed to O2 is not a maximum of the limits.**

The repeat-product limit (1000) bounds the product of the *counts*, not what stands inside the repeated group. `((a x250){0,4}){0,250}` (256 characters, nesting 2, product 4 x 250 = 1000, no unbounded quantifier) is accepted by the classifier and expands to **241 250 NFA states** (dynamic programming over the repeat/group family, then built and verified: `results/limit_space.txt`, group *space*):

| Measured at the DP optimum | Value |
|---|---|
| program size | 241 251 states (P = 483 751) |
| compile | 194 ms, peak 66.5 MB |
| match of a 256-code-point value | 29 ms (a literal chain keeps few states alive) |

Time is not the same as size: the *match* time depends on how many states stay alive. A hill-climb on the real classifier and evaluator, maximizing the number of state visits for a 256-code-point value (group *worksearch*), found accepted expressions far slower than 38.45 ms. The search is a lower bound of the true worst case, not the worst case, and it is noisy (two runs of the cap-2048 search gave 87 ms and 50 ms):

| Cap on the program size PI | Worst match found | Compile | Expression length |
|---|---|---|---|
| 512 | 14 ms | 0.6 ms | 254 |
| 1024 | 21 ms | 1.0 ms | 256 |
| 2048 | 50 ms (earlier run 87 ms) | 1.9 ms | 242 |
| 4096 | 80 ms | 3.1 ms | 256 |
| 8192 | 207 ms | 6.1 ms | 250 |
| 30000 | 658 ms | 21 ms | 256 |

A second, deterministic view (group *cost*, a family of repeated `a{0,255}`, 256 x `a`): compile 0.4 / 0.8 / 1.5 / 3.1 / 6.1 / 13 ms and match 0.1 / 6.6 / 20 / 46 / 101 / 210 ms at 511 / 1021 / 2041 / 4081 / 8161 / 16321 states, peak memory 62 kB to 4.7 MB: linear in the program size, about 20 ns per (P x code point). The independent random search (4000 candidates) reached only 5944 states and so is a **weak** cross-check of the DP (it never came near the optimum, and it did not exceed it); the DP result rests on the exhaustive structure of the family and on the build that confirms its prediction (241 250 predicted, 241 251 states built, the accept state being the one more).

**What follows:** O2 needs a rule on the size of the whole program. The other limits stay as measured candidates.

## 2. O2: resource limits (proposal)

### 2.1 The size measure PI (normative text of the proposal)

`PI(expression)` is defined by recurrence on the expression text alone, so every implementation (Python, Go, Rust, a verifier) computes the same number without building an automaton:

| Node | PI |
|---|---|
| a literal, `.`, a class | 1 |
| a sequence | the sum of its items |
| an alternation | 1 + the sum of its branches |
| a bounded repeat `x{lo,hi}` (`?` is `{0,1}`, `{n}` is `{n,n}`) | lo x PI(x) + (hi - lo) x (1 + PI(x)) |
| an unbounded repeat (`*` is lo = 0, `+` is lo = 1, `{lo,}`) | 1 + (lo + 1) x PI(x) |

**Derivation (review F3 of #48).** The recurrence restates the construction of `nfa_engine.py` (`_Prog.build`), construct by construct; the accept state is one state more, so the NFA has PI + 1 states:

* a literal, `.` or a class: `build` makes one state with one consuming edge: 1;
* a sequence: the items are chained back to front and no state is created for the sequence itself: the sum;
* an alternation: one new state with an epsilon edge to each branch (all branches end in the same continuation): 1 + the sum of the branches;
* a bounded repeat: `lo` mandatory copies of the inner expression (lo x PI(x)) and `hi - lo` optional copies, each preceded by one optional state with an epsilon edge to the copy and one to the exit ((hi - lo) x (1 + PI(x)));
* an unbounded repeat: one loop state whose epsilon edges lead to one copy of the inner expression (which returns to the loop state) and to the exit, plus `lo` mandatory copies in front: 1 + (lo + 1) x PI(x).

The equality is not only observed: 20 constructs have a hand-derived PI (`codes_probe.txt`, group *PI per construct*: `a|b` 3, `a?` 2, `a+` 3, `a{2,5}` 8, `a{2,}` 4, `(a|b){0,2}` 8, `((a?){2}){3}` 12, `a{0,255}` 510, `a{0}b` 1, ...) and each is compared with the recurrence and with the state count of the NFA; the 151 patterns of `limit_space.txt` (group *size*: the DP optimum, the 9 contracts, random mutations) confirm it on larger shapes.

**Arithmetic (review F3).** For every expression that passed tiers 1 and 2 of section 3.2, **every sum and every product of a bottom-up evaluation of PI is at most 512 000 (= 256 x 2000)**; a signed 32-bit integer suffices and no saturation is needed. Argument: the repeat-product limit bounds, for every chain of enclosing brace quantifiers, the product of their counts (`?` counts 1) by 1000; `*`, `+` and `{lo,}` apply to a single atom only and multiply by at most lo + 1 <= 2 x max(lo, 1). So every atom, alternation node, repeat operator is counted at most 2000 times in the total, and each of them uses at least one of the at most 256 characters of the text. Measured: the largest intermediate value over the 3833 expressions that pass tiers 1 and 2 (also those above PI_MAX, among them the DP optimum) is 241 250 (`codes_probe.txt`, *PI bound*). The check is arithmetic on the parsed tree: no program is built before it.

**Zero repeats and early refusal (review F3).** A repeat with `hi = 0` contributes 0: `(a{0,255}a{0,255}a{0,255}a{0,255}a{0,255}){0}b` has PI 1 (2 NFA states) although the group alone would have 2550. A large sub-tree is therefore not a large final program. Rules: **PI is a function of the whole tree and is decided after tiers 1 and 2**; an implementation must not refuse on the size of a sub-expression before the multiplicity of its enclosing repeats is known. It *may* stop early only on the running sum of the completed items of the **outermost** sequence or alternation (depth 0): those contributions are final and can only grow. The probe has the zero-repeat case, and a planted defect that checks sub-trees early is detected by it (section 3.4).

### 2.2 The values

| Rule | Candidate of #46 | Proposal | Evidence |
|---|---|---|---|
| expression length (whole text, anchors included) | 256 | 256, unchanged | boundary 256/257 accepted/refused, anchors counted (`limit_space.txt` *boundary*; `codes_probe.txt` *length-counts-anchors*) |
| one repeat count | 255 | 255, unchanged | boundary 255/256 |
| group nesting depth | 4 | 4, unchanged | boundary 4/5 |
| product of nested repeat counts | 1000 | 1000, unchanged (it no longer has to bound the size) | boundary 1000/1001 (`(a{250}){4}`-shaped) |
| unbounded quantifiers | at most 3, never on a group | unchanged | boundary 3/4; `(a)*` refused |
| value length | 256 code points | 256, unchanged; an over-limit value is a violation and the matcher is not run | `codes_probe.txt` *value.boundary-256/257* |
| **program size PI** | none | **PI <= 2048, new** | sections 1 and 2.3 |

### 2.3 Why 2048 (and what else could be chosen)

* The largest of the 9 existing contracts has PI = 71 (72 states): the limit leaves a factor of 28 of room.
* At the cap, the worst match found is 50 to 87 ms and the compile at most 3 ms, memory below 1 MB: inside any budget of a release verification, for an evaluator that is written once and verified at release time. A cap of 1024 halves the worst match (21 ms) and still leaves a factor of 14; a cap of 4096 doubles the compile cost and leaves the worst match near 80 ms. **The number is the owner's choice; the data support 1024, 2048 and 4096 equally as inputs, and none is a guarantee.**
* The native engines are not faster on these shapes. Cold, one run (`engines_at_limit.txt`): at PI = 2048 Go 2.9 ms, Rust 61 ms, the own evaluator 21 ms (compile and match); at PI = 4096 Go 6.7 ms, Rust 135 ms, own 68 ms; on the 23 802-state expression Go 115 ms, Rust 886 ms, own 695 ms. A size limit therefore protects every engine, including the native ones, not only the own evaluator.
* All engines compile and agree on every accepted expression of the probe, including the 241 250-state optimum (Go, Rust and the own evaluator: `nomatch` on 256 x `a`; no compile error, so the size rule is not needed to avoid an engine refusal, it is needed for cost). Rule D of the engine selection (an accepted expression must compile everywhere) holds for PI <= 2048 by a hard check in the probe.

### 2.4 Where the check sits

It is the **last tier** of the refusal order (section 3.2): it runs only for an expression that passed every syntactic and counting rule, on the parsed tree. A refusal therefore never depends on how far an unparsable text could be read (the principle of F4 of #46 is kept), and a size violation never hides a syntax error.

### 2.5 The aggregate cost of many contracts, and the responsibility boundary (review F2 of #48)

PI limits **one expression**, the value limit **one value**. The cost of a whole document is a sum over many of them, measured in `results/aggregate_cost.txt`:

| What | Measured |
|---|---|
| the three real release records (55, 17, 55 pattern-constrained values; 7 distinct expressions; each distinct expression compiled once) | compile 0.37 ms and match 1.1 / 0.3 / 1.1 ms **per whole record** |
| K distinct contracts, each the slowest expression found under PI <= 2048, one 256-code-point value each | 46 / 91 / 190 / 396 / 819 / 1600 ms for K = 1 / 2 / 4 / 8 / 16 / 32: **additive**, 45 to 51 ms per contract (a factor of 1.13) |
| one such contract, M values of 256 code points | 48 ms each (M = 1, 10, 100), compile once 1.9 ms |

The model is additive: total = the sum over the distinct expressions of the compile cost + the sum over the values of the match cost. Each term is bounded by the profile; **the number of contracts of a schema and of pattern-constrained values of a record is not**. An extrapolation, not a measurement: 1000 worst-case contract-and-value pairs would take about 50 s.

Where the responsibility lies (a proposal; **no new normative limit is asked for**):

1. **The pattern profile bounds one expression and one value**, and says so; it does not bound a document. A statement that "the profile makes verification cost bounded" would be false.
2. **The number of pattern contracts in a schema and of values in a record belongs to the limits of the schema and the record layer** (the input limits of the producer and of the verifier), not to this profile. None is proposed here.
3. **A verifier that reads untrusted schemas or records applies its own total budget** and reports its exhaustion with its own code; the budget unit that carries no machine dependence is the work PI x code points, summed over the values (state visits, not milliseconds). A budget exhaustion is not a property of one expression or value, so **the pattern code set contains no budget code on purpose**. The producer builds schemas it trusts; the budget therefore lives with the verifier.
4. **Each distinct expression is compiled once** per verification (the real schemas have 7 distinct expressions for 55 values).

## 3. O3: normative error codes (proposal)

### 3.1 The codes

One refused expression gets exactly one code. The set is part of the pinned profile version (a code is never renamed or reused inside a version). 25 expression codes and 3 value codes were exercised by the prototype; the three pin codes of O1 (`spec.pattern_profile.version`) are listed for completeness and not exercised, since the prototype has no schema to read.

| Group | Code | Refuses |
|---|---|---|
| pin (O1, not exercised) | `pattern_profile_missing`, `pattern_profile_unknown`, `pattern_profile_conflict` | a schema with a pattern contract and no / an unknown / a conflicting pin |
| text | `pattern_empty` | the empty text |
| text | `pattern_too_long` | more than 256 characters (the whole text) |
| text | `pattern_not_ascii_printable` | a character outside 0x20..0x7E |
| syntax | `pattern_empty_branch` | an empty alternative, group or body (`a\|`, `()`, `^$`) |
| syntax | `pattern_unbalanced_group` | a missing or a stray `)` |
| syntax | `pattern_group_extension` | `(?` of any kind |
| syntax | `pattern_escape_unsupported` | an escape outside the list, in or out of a class |
| syntax | `pattern_metachar_unexpected` | a metacharacter where an atom is expected (`*a`, `{`) |
| syntax | `pattern_anchor_misplaced` | `^` or `$` anywhere but the outer boundary |
| syntax | `pattern_class_empty`, `pattern_class_negated`, `pattern_class_unterminated`, `pattern_class_range_order`, `pattern_class_nested_or_posix`, `pattern_class_set_operator` | the class errors named by the codes |
| syntax | `pattern_quantifier_malformed`, `pattern_quantifier_leading_zero`, `pattern_quantifier_bounds_order`, `pattern_quantifier_not_greedy` | a malformed count, a leading zero, `{3,2}`, a lazy / possessive / stacked quantifier |
| limit | `pattern_nesting_too_deep`, `pattern_repeat_count_too_large`, `pattern_repeat_product_too_large`, `pattern_unbounded_too_many`, `pattern_unbounded_on_group` | the counting rules of 2.2 |
| limit | `pattern_program_too_large` | PI > 2048 (new) |
| value | `pattern_value_not_unicode_scalar`, `pattern_value_too_long`, `pattern_value_mismatch` | a lone surrogate; more than 256 code points; no full match |

The working names of #46 (`pattern_syntax_unsupported`, `pattern_value_too_long`) are replaced: one umbrella code would not name the construct, and 3.5 of #46 requires the refusal to name it.

### 3.2 Deterministic precedence (specification text, review F1 of #48)

The text below is meant to be implementable **without the Python code**. It is checked in two ways (3.3): a second implementation written from this text only (`spec_classifier.py`, which imports neither the classifier nor the prototype) is compared with the prototype over 70 149 expressions, and the review's counter-examples are cases of the probe. One refused expression gets exactly one code: the first rule that fires, in the order below.

**Input.** The expression text `t`. Tier 1 looks at the whole text. The scan looks at the **body**: `t` without a leading `^` and without a trailing `$` that is preceded by an even number (zero included) of consecutive backslashes (`a\$` ends in an escaped dollar, a literal; `a\\$` ends in an anchor).

**Tier 1, whole text, in this order:** T1.1 the empty text: `pattern_empty`. T1.2 more than 256 characters (anchors included): `pattern_too_long`. T1.3 a character outside 0x20..0x7E: `pattern_not_ascii_printable`.

**Tier 2, one left-to-right scan of the body.** The first rule that fires ends the scan. Depth of the body is 0. A running count of unbounded quantifiers is kept over the whole scan.

* **S1** entering an alternation (the body, or the content of a group) at depth d: d > 4 is `pattern_nesting_too_deep`.
* **S2** a sequence ends at `|`, `)` or the end of the body; a sequence without any item is `pattern_empty_branch`, at the position where it ends.
* **S3** an atom, by its first character:
  * `(`: **first** `(?` is `pattern_group_extension`; only then S1 for the new group (so `(((((?:a)))))` is a group extension, not a nesting error); after the content, a missing `)` is `pattern_unbalanced_group`;
  * `[`: the class rules C1 to C4;
  * `.`: an atom;
  * `\`: the next character must exist and be one of `\ . [ ] ( ) { } * + ? | ^ $ -`, else `pattern_escape_unsupported`;
  * `^` or `$` (they can only stand here when misplaced): `pattern_anchor_misplaced`;
  * any of `* + ? { } ]`: `pattern_metachar_unexpected`;
  * any other character is a literal.
* **Classes**, entered at `[` (the class text runs to the first `]` that is not escaped, or to the end of the body if there is none):
  * **C1** in the class text, with every escaped pair (a backslash and the character after it) replaced by two neutral characters, the pairs `&&`, `--` or `~~`: `pattern_class_set_operator`. **This is a pre-check of the whole class text: it fires before any other class rule, wherever in the class the pair stands, also in an unterminated class.**
  * **C2** a first character `^`: `pattern_class_negated`.
  * **C3** then the items from left to right: end of the text before `]` is `pattern_class_unterminated`; `[` is `pattern_class_nested_or_posix`; a backslash must be followed by a character of the list of S3, else `pattern_escape_unsupported`; if an item is followed by `-` and then neither `]` nor the end, the range end is read by the same rules and a range end below its start is `pattern_class_range_order` (so `[z-\d]` is an escape error and `[z-a\d]` is a range-order error, the range being completed before the next item is read);
  * **C4** a class with no item (`[]...`) is `pattern_class_empty`.
* **Quantifiers**, after an atom (`?` is `{0,1}`):
  * **Q1** `*` or `+`: the count of unbounded quantifiers grows; above 3 is `pattern_unbounded_too_many`;
  * **Q2** then, if the atom is a group, `pattern_unbounded_on_group`;
  * `{`: the text must be `{n}`, `{n,m}` or `{n,}` with decimal digits, else `pattern_quantifier_malformed`; then in this order: **Q3** a number of two or more digits that starts with `0`: `pattern_quantifier_leading_zero`; **Q4** `{n,m}` with m < n: `pattern_quantifier_bounds_order`; **Q5** `{n,}`: the unbounded count grows (Q1), then Q2; **Q5b** a count above 255 (n, or m for `{n,m}`): `pattern_repeat_count_too_large`; **Q5c** the product of the counts of the enclosing and this repeat (a repeat counts max(m, 1), `{n,}` counts n, `?` `*` `+` count 1) above 1000: `pattern_repeat_product_too_large`;
  * **Q6** a quantifier character (`? * + {`) directly after a complete quantifier: `pattern_quantifier_not_greedy` (covers `a??`, `a*?`, `a++`, `a{2}{3}`).
* **S5** when the body is consumed by the scan and characters remain (only a stray `)` can): `pattern_unbalanced_group`. No other refusal exists in tier 2: the two post-scan anchor checks of the prototype classifier are unreachable and are **not** part of this specification.

**Tier 3:** `pattern_program_too_large` when PI > 2048, for an expression that passed tiers 1 and 2, decided on the whole tree (2.1).

**A schema with several expressions** is refused with the code of the **first refused expression in document order**; the refused node's path is the detail, further refusals may be listed but carry no normative weight. The three pin errors precede every expression check; a schema that cannot be read as YAML is a different, earlier error of the reader.

**A value** (after the expression was accepted): `pattern_value_not_unicode_scalar`, then `pattern_value_too_long` (the matcher is **not** run: no work is spent on an over-limit value), then match or `pattern_value_mismatch`.

Consequences worth stating: a product violation wins over a size violation wherever it stands; a stacked quantifier before the fourth unbounded quantifier wins over `pattern_unbounded_too_many`, which wins over a later stacked quantifier; a count above 255 in `{256,}` is reported as a count error (the unbounded count grows first but stays at 1).

### 3.3 What the probe shows

`codes_probe.txt` (typed exits: 0 ok, 1 a measured expectation failed, 2 the probe could not run, never a detection):

* **Precedence:** 65 hand-authored cases, each with the code the rules of 3.2 give (authored from the rule text before the classifier was consulted), among them the review's counter-examples `[^a&&b]` and `[z-a&&b]` and the class and repeat orders C1 to C4 and Q1 to Q6 with multi-defect texts; all hold. One expectation of mine was wrong in the first round (`...(` ends in an *empty group*, not an unbalanced one) and was corrected; the classifier was right.
* **The previous text was wrong (RED-initial, `red-initial-f1.txt`):** the previous 3.2 said that the first violation in reading order wins also inside a class. Its implementation disagrees with the prototype on both examples of the review (`[^a&&b]`: `pattern_class_negated` against `pattern_class_set_operator`; `[z-a&&b]`: `pattern_class_range_order` against `pattern_class_set_operator`). The prototype and the earlier design text (F2 of #46: the operator check runs before the range rules) agree; the text of 3.2 was corrected, not the prototype.
* **The text determines the verdict:** a second implementation written from the rules of 3.2 only is compared with the prototype over 70 149 expressions (the precedence cases, 30 000 seeded random texts, 40 000 generated multi-defect texts, the 84 constructs): **0 disagreements**, 25 distinct codes seen. It is by the same author and shares the language; the independence is of the code path, so this is evidence for the text, not a proof of it.
* **Boundary:** an expression of PI = 2048 is accepted, PI = 2049 is refused with `pattern_program_too_large`; PI + 1 equals the NFA state count; the zero-repeat case is accepted (PI 1).
* **PI per construct and arithmetic:** 20 hand-derived values hold; the largest intermediate value of a bottom-up evaluation over the 3833 expressions that pass tiers 1 and 2 is 241 250, below the bound of 512 000.
* **Value order:** 7 cases, including a 300-code-point value that does not match (still `pattern_value_too_long`) and a lone surrogate after an over-limit prefix.
* **Totality:** 30 187 texts (the 84 constructs, the limit cases, the precedence cases, 30 000 seeded random texts): 3732 accepted, 26 455 refused, **every refusal got exactly one code** (0 unmapped, 0 ambiguous); 25 distinct codes reached.
* **Coverage finding:** two rows of the mapping, the post-parse anchor checks of the existing classifier, are **never reached** (an inner `^` or `$` stops the scan earlier as `pattern_anchor_misplaced`); dead code of the prototype classifier, reported, not removed (no classifier is changed here).
* **Determinism:** the codes of 3000 random texts, the constructs and the precedence cases are identical under four different `PYTHONHASHSEED` values.

### 3.4 The probe can fail, for the right reason

`selftest-codes-output.txt`: an unmodified positive control (exit 0); **11 planted defects**, each counted only when the probe exits 1 **and** prints a `FAIL-EXPECT` line of the check meant to catch it. In the prototype: the charset check before the length check, an off-by-one in the size limit, the size tier missing, PI that forgets the extra state of optional copies, a mapping row removed (an unmapped refusal), a code chosen by the hash seed, the value matcher run before the length check, a size check on sub-trees before the repeat factor is known (refuses the zero-repeat case). In the implementation of the text: the class pre-check missing, the count check before the bounds-order check, the nesting check before the group-extension check (these three must show up as a disagreement of the differential): 11/11; and 2 infrastructure controls (the prototype module missing, crashing) that must exit 2 and are not detections: 2/2.

## 4. Producer and verifier responsibilities (proposal)

Following the shape of P7 (`integer_out_of_range`): **both sides check, each independently, and the verifier never relies on the producer's result.**

| What | Producer (building a release) | Verifier (reading a release) |
|---|---|---|
| the pin | declares `spec.pattern_profile.version` with the schema; refuses to build without it | refuses a schema with a missing, unknown or conflicting pin (three distinct codes) |
| every `pattern` expression | classifies it (tiers 1 to 3) when the schema is read; a schema with one refused expression is refused as a whole, no fallback to a native engine, no partial acceptance | the same classification, independently, before any value is evaluated; the code of the first refused expression in document order |
| every value of a pattern contract | refuses to emit a value that violates the contract (the three value codes) | evaluates the value with a linear-time evaluator; over-limit values are violations without running the matcher |
| the evaluator | any evaluator that meets the linear-time requirement and the shared vectors; the own NFA is the reference direction (E1); google-re2 may cross-check (E2); the version evidence names the implementation that ran (E3) | the same; it does not trust a producer-supplied verdict |
| the numbers (PI, limits) | computed from the expression text by the recurrence of 2.1 | the same recurrence: two implementations that disagree on PI disagree on acceptance, which is why the shared vectors (on hold) must contain PI boundary cases |

Nothing here makes the Forms or the reference verifier evaluate a schema pattern today; they evaluate none (3.4 and 6 of #46).

## 5. Effect on P2, P4 and Forms #166 / #167 (analysis, nothing changed)

* **P4 (`timestamp` pattern):** unaffected in meaning. The timestamp contract (`c1`) has PI = 32 and the date contracts 10, far below 2048; the profile still says nothing about calendar validity. The one new dependency: a P4 decision that replaced the pattern by a longer one must stay within PI <= 2048 and length 256, and any new expression is classified under the codes above.
* **P2 (`must` dialect):** independent. If the dialect ever offers a regular-expression function, it must reference this profile (pin, limits, codes) and not introduce a second flavor; this is a requirement on P2's grammar, not a change now.
* **Forms #166:** the Forms evaluate no contract and list pattern contracts as unevaluated; nothing changes. A future Forms pattern evaluator would implement the recurrence PI and the codes natively (Go `regexp` and Rust `regex` accept every expression of the profile, measured), and must not report an unevaluated contract as passed.
* **Forms #167 (visibility closed, evaluation open):** the evaluation of the surface-level `validation` waits for P2; this document adds nothing to it. The error codes are not a Forms status vocabulary.
* **Relay #162 / the release verifier:** the verifier-side column of section 4 is the future requirement for the module-artifact authentication work; no implementation is started.

## 6. Traceability: each proposal and its evidence

| Proposal | Evidence (file, group or case) |
|---|---|
| the candidate limits admit 241 250 states, 194 ms compile, 66 MB | `results/limit_space.txt` *space* |
| a 6376-state "largest program" and the 38.45 ms maximum are superseded | `results/limit_space.txt` *worksearch*, *space*; `engine-selection/results/closure.txt` (the earlier figure) |
| PI = NFA states - 1 | `limit_space.txt` *size* (151 patterns); `codes_probe.txt` *boundary* |
| PI <= 2048 and its costs | `limit_space.txt` *worksearch*, *cost*, *contracts*; `engines_at_limit.txt` |
| boundary values of the other limits | `limit_space.txt` *boundary* |
| every engine compiles the accepted programs | `engines_at_limit.txt` (rule D: a hard check for PI <= 2048) |
| the codes, their precedence and totality | `codes_probe.txt` (*precedence*, *value*, *totality*, *determinism*) |
| the probe can fail | `selftest-codes-output.txt` |
| the two dead classifier rows | `codes_probe.txt` *UNREACHED-ROW* |
| the class and repeat rule orders C1-C4, Q1-Q6; the previous text was wrong | `codes_probe.txt` *precedence* (class.*, repeat.*, group.*); `red-initial-f1.txt`; `codes_probe.txt` *differential* with `spec_classifier.py` |
| PI per construct, arithmetic bound, zero repeats | `codes_probe.txt` *PI per construct, zero repeats, bound* |
| aggregate cost and the responsibility boundary | `results/aggregate_cost.txt` (*real*, *synthetic*, *values*) |

## 7. Not verified

* The worst-case match time under the limits: the searches are lower bounds, noisy, and use two values (`a` x 256, `a` x 255 + `b`) on one machine; the true worst case of a size cap is not known. The asymptotic bound is the claim; milliseconds are not.
* The DP optimum is exact for the family it searches (atoms, `{0,h}`, groups, no alternation); an independent random search was too weak to cross-check it (section 1).
* Go and Rust: one cold run each, the match only; no repeated or warmed timing; the RE2 wheels (`google-re2`) were not run here.
* The pin errors (O1) and the document-order rule for several expressions: specified, **not exercised** (the prototype reads no schema).
* That the codes are the right granularity: 25 expression codes are a proposal; a coarser set (fewer codes plus a construct field) is possible and would not change the precedence.
* The second implementation (`spec_classifier.py`) is by the same author as the prototype: it shares the reading of the problem; a third reader, in another language, from the text only, is the real test and belongs to the (held) vector and gate work.
* The aggregate figures (2.5) are one machine, the own evaluator, one expression family; the 50 s for 1000 pairs is an extrapolation. No limit on the number of contracts or values exists anywhere yet.
* The bound of 512 000 for PI is an argument from the product rule, checked on 3833 expressions, not a machine-checked proof.
* Any behavior of the Forms or of a verifier: none evaluates a schema pattern today; no vectors, no gate, no implementation exist.

## 8. For the owner

The external review of 2026-11-22 recommends the decisions below (O2 and O3 stay the owner's; the review's F1 to F3 are answered in 2.1, 2.5 and 3.2):

| # | Point | Recommendation |
|---|---|---|
| O2 | PI ceiling | **2048** (1024 or 4096 are equally supported by the data) |
| O2 | the other limits | unchanged |
| O2 | PI is part of the profile version | GO |
| O3 | the 25 expression codes | GO, as a specification input |
| O3 | the 3 value codes | GO |
| O3 | precedence | the explicit order of 3.2 (after the correction of F1) |
| O3 | producer and verifier check independently | GO |
| aggregate | no new normative limit; the responsibility boundary of 2.5 documented | accept the boundary |
| follow-up | vectors for PI boundaries and for the code precedence; a third implementation from the text | a later, separate step (on hold) |

Everything not named here stays on hold: P2, P4, Forms #166/#167, the schema finalization, the Relay #162 implementation, an implementation of P1, the normative vectors, the CI gate.
