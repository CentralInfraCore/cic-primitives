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
| a bounded repeat `x{lo,hi}` (`?` is `{0,1}`) | lo x PI(x) + (hi - lo) x (1 + PI(x)) |
| an unbounded repeat (`*`, `+`, `{lo,}`) | 1 + (lo + 1) x PI(x) |

For the reference construction of `nfa_engine.py` the number of NFA states is exactly PI + 1 (the accept state): confirmed on all 151 patterns of group *size* (the DP optimum, the 9 contracts, random mutations) and on the two boundary expressions of the probe. PI is arithmetic on the parsed tree; **no program is built before the check**, and the numbers stay small because the existing limits (length 256, count 255, product 1000) bound every term.

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

### 3.2 Deterministic precedence

1. **Tier 1, whole text, fixed order:** `pattern_empty`, `pattern_too_long`, `pattern_not_ascii_printable`.
2. **Tier 2, one left-to-right scan:** the first rule violated **in reading order** wins; the limits counted as the text is read (nesting on entry of a group, a repeat count, the product, the number of unbounded quantifiers) belong here and fire where they are read; at one position the fixed order of the rules of the scan decides. A product violation therefore wins over a size violation wherever it stands, and a stacked quantifier before the fourth unbounded quantifier wins over `pattern_unbounded_too_many`, which in turn wins over a later stacked quantifier.
3. **Tier 3, program size:** `pattern_program_too_large`, only for an expression that passed tiers 1 and 2.
4. **A schema with several expressions** is refused with the code of the **first refused expression in document order**; the refused node's path is the detail, further refusals may be listed but carry no normative weight. The three pin errors precede every expression check; a schema that cannot be read as YAML is a different, earlier error of the reader.
5. **A value** (after the expression was accepted): `pattern_value_not_unicode_scalar`, then `pattern_value_too_long` (the matcher is **not** run: no work is spent on an over-limit value), then match or `pattern_value_mismatch`.

### 3.3 What the probe shows

`codes_probe.txt` (typed exits: 0 ok, 1 a measured expectation failed, 2 the probe could not run, never a detection):

* **Precedence:** 32 hand-authored multi-defect expressions, each with the code the tier rule gives (authored from the rule text before the classifier was consulted); all hold. One expectation of mine was wrong (`...(` ends in an *empty group*, not an unbalanced one) and was corrected; the classifier was right.
* **Boundary:** an expression of PI = 2048 is accepted, PI = 2049 is refused with `pattern_program_too_large`; PI + 1 equals the NFA state count.
* **Value order:** 7 cases, including a 300-code-point value that does not match (still `pattern_value_too_long`) and a lone surrogate after an over-limit prefix.
* **Totality:** 30 154 texts (the 84 constructs, the limit cases, the precedence cases, 30 000 seeded random texts): 3727 accepted, 26 427 refused, **every refusal got exactly one code** (0 unmapped, 0 ambiguous); 25 distinct codes reached.
* **Coverage finding:** two rows of the mapping, the post-parse checks `'^' is allowed only at the outer start` and `'$' ... end` of the existing classifier, are **never reached**: an inner `^` or `$` already stops the scan as an unexpected metacharacter, which the mapping names `pattern_anchor_misplaced`. The two checks are dead code of the prototype classifier (reported, not removed; no classifier is changed here).
* **Determinism:** the codes of 3000 random texts, the constructs and the precedence cases are identical under four different `PYTHONHASHSEED` values.

### 3.4 The probe can fail, for the right reason

`selftest-codes-output.txt`: an unmodified positive control (exit 0); 7 planted defects, each counted only when the probe exits 1 **and** prints a `FAIL-EXPECT` line of the check meant to catch it: charset check before the length check, an off-by-one in the size limit, the size tier missing, PI that forgets the extra state of optional copies, a mapping row removed (an unmapped refusal), a code chosen by the hash seed, the value matcher run before the length check: 7/7; and 2 infrastructure controls (the prototype module missing, crashing) that must exit 2 and are not detections: 2/2.

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

## 7. Not verified

* The worst-case match time under the limits: the searches are lower bounds, noisy, and use two values (`a` x 256, `a` x 255 + `b`) on one machine; the true worst case of a size cap is not known. The asymptotic bound is the claim; milliseconds are not.
* The DP optimum is exact for the family it searches (atoms, `{0,h}`, groups, no alternation); an independent random search was too weak to cross-check it (section 1).
* Go and Rust: one cold run each, the match only; no repeated or warmed timing; the RE2 wheels (`google-re2`) were not run here.
* The pin errors (O1) and the document-order rule for several expressions: specified, **not exercised** (the prototype reads no schema).
* That the codes are the right granularity: 25 expression codes are a proposal; a coarser set (fewer codes plus a construct field) is possible and would not change the precedence.
* Any behavior of the Forms or of a verifier: none evaluates a schema pattern today; no vectors, no gate, no implementation exist.

## 8. For the owner

| # | Point | Recommendation |
|---|---|---|
| O2 | add the rule PI <= N; the other limits unchanged | N = 2048 (1024 or 4096 are equally supported by the data); decide the number and whether PI is part of the first pinned version |
| O3 | the code set, tier order, document-order rule for a schema, the value-time order | accept the set of 3.1 and the order of 3.2 as the specification input; the working names of #46 are replaced |
| O5 follow-up | none: E1 to E3 are decided in #47 | the vectors for PI boundaries and for the code precedence are a later, separate step (on hold) |

Everything not named here stays on hold: P2, P4, Forms #166/#167, the schema finalization, the Relay #162 implementation, an implementation of P1, the normative vectors, the CI gate.
