# The `pattern` contract: a closed regular-expression profile (P1, design and measurement)

Status: **design draft, documentation and evidence only; revised after the owner reviews of 2026-11-21 (F1 running time, F2 class operators and counts, F3 fail-closed compatibility measurement, F3.1 element-level completeness, F4 order of the resource checks).** Not part of this pull request: any change of the grammar, of a checker, of the Forms or of a verifier; the derived JSON Schema; P2, P4, #166; the finalization of the release schemas. Everything marked *candidate* is a proposal for the owner, not a decision.

Owner direction (2026-11-21), taken as the starting point: a closed, explicit RE2 subset (what is not allowed is forbidden); full match, with `^` and `$` allowed only at the outer boundary; `.` never matches LF and a `$` never lets a trailing LF through; ASCII classes, `.` is one Unicode code point except LF; an own, explicit pattern-profile pin with a life cycle independent of the node-name grammar; the seven existing expressions keep their text and their semantic compatibility is measured; one shared vector set for Python, Go and Rust with a mandatory CI gate. Added by the owner: **resource limits** (length, repetition, nesting, worst-case running time) and **fail-closed semantics** (an unsupported construct is refused at compile time, with no fallback to the full native engine). The name of the version field and the compatibility decision are to be settled by the measurements below.

## 1. What is undefined today

The atom `schemas/atomic/contract.yaml` declares the type as `pattern: regex`: **no flavor, no anchoring rule, no limits.** The expression is matched by whoever reads it. The only reader today is the Python `jsonschema` library inside the grammar checker (a *search*, as `re.search`); the Forms list contracts as unevaluated and evaluate none; the reference verifier does not evaluate schema patterns (its own digest and commit checks are hard-coded and end in `\Z`). The release schema set (the draft of cic-primitives #38) declares seven distinct `pattern` expressions.

## 2. Facts (measured; evidence in `docs/evidence/grammar-pattern-measurement/`)

Engines: Python 3.14.4 `re`; Go 1.26.11 `regexp` (RE2); Rust `regex` 1.13.2 (default limits). The matching rule under test is the one the owner directed: the expression with its outer `^` and `$` removed, matched as a **full match** (`\A(?:body)\Z` in Python, `\A(?:body)\z` in Go and Rust), no flags.

1. **Inventory** (`inventory-output.txt`). In the cic-primitives tree, the release schema drafts and the cic-schema-registry at its pinned commit there are **9 distinct `pattern` contracts** in 37 declarations (7 release, 1 in an example schema, 1 CIDR shape in the registry's network schemas). **All 9 are inside the candidate subset.** Their maxima: length 89, repetition count 64, group nesting 1, at most 3 unbounded quantifiers, none unbounded on a group. Separately, **9 distinct JSON Schema `pattern` keys** of the grammar's own meta-schemas and the registry's block schema (a different layer: only the Python `jsonschema` library evaluates them) fall outside it (`\d`, `\n`, a negated class, more than 3 unbounded quantifiers).
2. **Semantic parity inside the subset** (`results/probe-semantic.txt`). 117 cases (the 9 contracts times 13 inputs: valid, empty, trailing/leading/double LF, trailing CR, CRLF, NUL, U+2028, U+00E9, an astral character, truncated, one char more): **the three engines give the same verdict on all 117, and it equals an independently authored expectation.** `.` takes CR, NUL, U+2028, U+00E9 and an astral code point in all three, and refuses LF in all three.
3. **The legacy semantic differs in exactly one way.** Python `re.search` of the original expression accepts the valid value **plus one trailing LF** for all 9 contracts, and for `^vault:v1:.+$` also `...\r\n` (10 of the 117 cases). This is the node-name `abc\n` defect of the pinned grammar, now measured on the release patterns. Go and Rust never did.
4. **Real data** (`compat-records-output.txt`). The pattern-constrained values of the record `v0.2.1` (55), the golden record (17) and the probe base record (55): **0 contain a line feed, none is longer than 256 code points, 0 change their verdict** between the legacy reading and the **whole candidate profile** (expression inside the closed subset, value within 256 code points, full match). The measurement is fail-closed **at element level** (review F3.1): every element of every collection on the path of a pattern node is checked, and a mandatory key missing in ANY element, a null where the node is not nullable, a value or container of the wrong type, an expression outside the subset or too few values make it INCOMPLETE (exit 1). An earlier revision only noticed a node with no value at all, so one element lacking the field among others that had it went unnoticed. The self-test (24 checks), 11 planted defects (11 detected) and a RED-initial run against the previous head (`red-initial-f31-f4-against-7b16e34.txt`) show that it can see a changed verdict and refuse an incomplete run. (An earlier revision measured only the regex semantic and did not apply the length limit; the claim now covers the profile.)
5. **Constructs outside the subset diverge** (`results/probe-constructs.txt`, 84 constructs). **28 of the 84 give different results in the three engines**, for example `a{,3}` (Python a quantifier, Go a literal, Rust a compile error), `[a&&b]`, `[a-z--b]`, `[a~~b]` and `[+--]` (Rust reads a set intersection, difference or symmetric difference, Python and Go a set of literal characters; `[a--b]` is a compile error in Python and Go and a difference in Rust), `a{01}` (Go reads a literal, Python and Rust a count), `a++` (Python and Rust accept, Go refuses), `a++` (Python and Rust accept, Go refuses), `(?i)` and `(?s)` (Python refuses mid-expression use in this position, the others accept), `\p{L}`, `(?<n>a)`, `\Q..\E`, lookaround and back-references (Python only), `A`, `\101`. The 24 constructs of the subset that were probed (including `[a&b]`, `[a~b]` and `a{0}`) give the same result everywhere (no exception). A native fallback would therefore make the verdict depend on the engine.
6. **Compile limits differ** (`results/probe-limits.txt`): a repetition count above **1000** is refused by Go only; group nesting of **250** is refused by Rust (and 500 by Python); nested repetition with a product of 100 x 100 is refused by Go, 1000 x 1000 by Rust; an expression of 262144 characters and a class of 255 items compile everywhere. The syntactic subset alone does not give the three engines the same resource behavior.
7. **Running time** (`results/probe-timing.txt`, one run, indicative): Python's backtracking is **exponential** on `(a+)+$` (7.8 s at 28 characters, over 10 s at 32) and `(a|aa)+$` (1.8 s at 36), and **polynomial** on adjacent unbounded quantifiers: `a*a*a*$` takes 11 ms at 256 characters, 85 ms at 512, 660 ms at 1024, 4.8 s at 2000, over 10 s at 8000. Go and Rust stay under 0.5 ms on every case (linear time). The 9 existing contracts stay under 1.4 ms on 65536-character adversarial values in all three engines.
8. **The resource limits do not bound the Python worst case (review F1).** Three patterns that the prototype classifier ACCEPTS (a bounded repetition, no unbounded quantifier at all, length and nesting far inside the limits) are still exponential in Python: `^(a|aa){1,255}$` on `a`*n+`b` takes 0.04 s at n=28 and 0.27 s at 32 (about 7x per 4 characters; at 256 characters it is out of reach); `^(a?){n}a{n}$` takes 8.8 s at n=28 and exceeds 10 s at 32; the same without any group, `^` + `a?`*n + `a`*n + `$`, takes 6.9 s at n=28 and exceeds 10 s at 32 (194 characters of pattern at n=64 are accepted). Go and Rust answer every one of them in under 0.4 ms. The limits of 3.4 therefore bound the **size** of the compiled program, not the **time** of a backtracking engine, and no counting rule closes this: ambiguity is in the shape of the expression, not in a number.

## 3. The profile (candidate text)

**3.1 Matching.** The expression is matched against the **whole** value. The anchors `^` and `$` are allowed only at the outer boundary of the expression (an optional first `^`, an optional last unescaped `$`) and add nothing: `^a$` and `a` mean the same. An anchor anywhere else is refused. (Implementation note, not normative: remove the outer anchors, then match `\A(?:body)\z`.)

**3.2 Syntax (closed).** Everything not listed is refused.

```
expression := ['^'] alt ['$']
alt        := concat ('|' concat)*
concat     := repeat*
repeat     := atom [ '*' | '+' | '?' | '{' n '}' | '{' n ',' m '}' | '{' n ',' '}' ]      greedy only
atom       := literal | '.' | class | '(' alt ')'                                          a plain group, never '(?'
class      := '[' item+ ']'        item := char | char '-' char                            ASCII, never negated, no POSIX class
literal    := an ASCII printable character that is not one of  \ . [ ] ( ) * + ? { } | ^ $
            | '\' followed by one of  \ . [ ] ( ) * + ? { } | ^ $ -
```

The expression text is ASCII printable (0x20 to 0x7E) only. Refused, among others: `\d \w \s \b \n \t \x \u \A \z \Z \Q`, back-references, octal escapes, negated and POSIX classes, `(?...)` of any kind (flags, lookaround, named and non-capturing groups), lazy and possessive quantifiers, `{,m}` and a literal `{`, an empty expression, an empty class, a reversed range or bound.

Three rules close gaps found by the review (F2), each with refusal vectors and a measured cross-engine divergence:

* **No class set operators.** Inside a class the unescaped pairs `&&`, `--` and `~~` are refused (Rust reads them as intersection, difference and symmetric difference; Python and Go as literal characters or a range). A single `&`, `~` or `-` stays a literal (`[a&b]`, `[a~b]`, `[a-]`); an escaped one (`[a\-\-b]`) too. The check runs before the range rules, so another rule cannot hide it.
* **Repetition counts have no leading zero.** `{0}` and `{0,3}` are valid; `{01}`, `{00}`, `{1,02}` are refused (Go reads `a{01}` as a literal, Python and Rust as a count).
* **No empty alternative.** Every alternative, every group and the body must be non-empty: `a|`, `|a`, `a||b`, `(|a)`, `(a|)`, `()` and `^$` are refused (a missing branch is not a visible choice; it is not a feature to specify).

**3.3 Characters.** `.` matches **one Unicode code point except LF** (U+000A). It matches CR, NUL, U+2028, non-ASCII and astral code points (measured identical in the three engines). The classes are ASCII ranges and members. The value is a sequence of Unicode scalar values (a string the YAML reader produced); a lone surrogate is outside the profile.

**3.4 Resource rules (candidate values; the rules are decided here, the numbers from the data).** **Order (review F4):** the limits are enforced before and during the parse, never after it: the length is checked on the **whole original text** (anchors included, 256) before any syntactic processing; the nesting depth on entry of the recursion; repetition counts, their product and the number of unbounded quantifiers as they are read. A refusal never depends on how far an unbalanced or otherwise refused text could be parsed (vectors: a 300-character unbalanced text is refused for its length, a 10-deep unbalanced text for its depth).

| Rule | Candidate | Why this number |
|---|---|---|
| Expression length | at most 256 characters | the existing maximum is 89; every engine compiles far more |
| One repetition count (`n`, `m`) | at most 255 | Go refuses above 1000; the existing maximum is 64 |
| Group nesting depth | at most 4 | Rust refuses 250, Python 500; the existing maximum is 1 |
| Product of nested repetition counts | at most 1000 | Go refuses 100 x 100 = 10000; 30 x 30 compiles; the existing maximum is 9 |
| An unbounded quantifier (`*`, `+`, `{n,}`) | only on a single atom, **never on a group** | keeps the compiled program small and removes the plain nested-quantifier shapes; **it does not bound the running time** (fact 8) |
| Number of unbounded quantifiers | at most 3 | the existing maximum is 3; a size rule, not a time guarantee (fact 8) |
| Length of the value that is matched | at most 256 code points | the longest pattern-constrained value of an existing record is 105 characters (`release.sign`); a size rule, not a time guarantee (fact 8) |

A value longer than the limit **does not match** (a contract violation, not a crash). The limits are part of the profile and are the same for every engine, so a Go or Rust evaluator that could do more still refuses more. **Running time is a separate, normative requirement (review F1):** the evaluator of the profile MUST guarantee time linear in the product of the expression length and the value length in the worst case (a finite-automaton or RE2-class evaluator). A backtracking engine, Python `re` among them, is **not eligible**, whatever limits stand in front of it. Which concrete evaluator the Python side uses is a separate decision (section 7, O5). Go `regexp` and Rust `regex` meet the requirement.

**3.5 Fail-closed.** An expression outside the profile is **refused when the schema is read** (the producer and the verifier refuse the schema, not the value). There is no fallback to the native engine, no flag, no per-engine behavior, and no partial acceptance: a schema with one refused expression is refused as a whole. The refusal names the construct. (The reason identifiers are an open point; working names in section 7.)

## 4. Versioning and compatibility

**4.1 An own pin.** The profile is identified by its own explicit version, **independent of the node-name grammar version** (its own life cycle: either can move without the other). The binding rule follows the precedent of `access-policy/1` and of the node-name profile: the version is a property of the pinned schema and of the processing context, **never a document key**; no default; a missing, an unknown and a conflicting version are three distinct errors.

**4.2 Where it is declared (open, from the measurement).** The type `pattern` is declared in the atom `schemas/atomic/contract.yaml`; the node-name pin sits in `schemas/atomic/shape.yaml` (`spec.node_name_grammar.version`) because it constrains a Shape member. The measurement favors the same logic here: the pin sits with the atom that defines the contract type, as `spec.pattern_profile.version` in `contract.yaml` (candidate name). This is a recommendation, not a decision (section 7).

**4.3 Compatibility.** The text of all 9 distinct existing contracts is unchanged (all inside the subset; the three rules of 3.2 refuse none of them). The measured semantic differences between the legacy reading and the profile are exactly the values that end in LF (and `...\r\n` for `.+`) and values longer than 256 code points; **no value of any existing record is one of them** (127 values, 0 line feeds, 0 over the limit, 0 changes under the whole profile). Nothing evaluates schema patterns in production today. The profile is therefore **not** a breaking change of any existing record or schema; its first version is the first one anyone can pin (legacy = "no pin = no defined semantic", the state of section 1). The compatibility decision for the owner is only whether a schema that carries a `pattern` contract must declare the pin (recommended, in line with 4.1) or may rely on the profile being the default (not recommended: no default is the rule everywhere else).

## 5. Vectors and the gate (design; nothing is built here)

One shared vector set, in the style of the node-name vectors (`name-vectors/node-name.yaml`): per vector, the expression, the input, the **profile verdict** and the verdicts of the three engines; and **refusal vectors** (an expression outside the profile, with the construct that must be named). A gate builds and **runs** the Go and Rust runners on every CI run, with the required-run switches of the existing gates, plants identical defects in both runners (two outputs that agree prove nothing) and proves that the gate can fail. The prototype of this gate is the evidence of this pull request: `probe_engines.py` (3 engines, 4 groups: 117 semantic, 84 constructs, 38 limits, 46 timing cases) and `gate_selftest.py` (4 planted defects, 4 detected, including the same defect in both runners), `subset_check.py` with `selftest_subset.py` (118 vectors) with `selftest_subset_mutants.py` (16 planted defects of the classifier detected, a 17th masked by a second layer, stated), `compat_records.py` with its self-test and `compat_records_mutants.py` (11 planted defects detected), `red_initial_f31_f4.py` (the previous head shows every defect, the current one none).

## 6. Effect on the other points

* **P4** (the timestamp pattern) depends on this profile for the meaning of a pattern; whether a pattern may carry calendar validity is P4's own question and is not touched.
* **P2** (the `must` dialect) is independent.
* **Forms #166, #167:** unaffected; the Forms evaluate no contract. A Forms evaluator of patterns would implement the profile natively (the Go and Rust engines accept every construct of it).
* **Release schemas:** the seven expressions are unchanged; finalization stays on hold (P2, P4, #167 evaluation).
* **The grammar's own JSON Schema patterns** (9 distinct expressions outside the subset): see the scope point in section 7.

## 7. Open points (for the owner)

| # | Point | Recommendation | Owner decision (review of 2026-11-21) |
|---|---|---|---|
| O1 | Name and place of the version field | `spec.pattern_profile.version` in `schemas/atomic/contract.yaml` (candidate), with the three binding errors of 4.1 | **GO** |
| O2 | The limit values of 3.4 | the candidate values above; the data is in section 2 | acceptable starting points; **not final** until the running-time requirement (3.4, fact 8) is settled |
| O3 | Reason identifiers | working names, **not decided and not in any declaration**: `pattern_syntax_unsupported` (schema refused), `pattern_value_too_long` (value above the limit) | **HOLD** until the implementation specification |
| O4 | Scope | the profile covers the `pattern` **contract** only; the grammar's own JSON Schema `pattern` keys stay as they are | **GO** |
| O5 | The evaluator | a **linear-time** evaluator (3.4); Python `re` behind counting rules is withdrawn as a recommendation (fact 8) | linear-time evaluator accepted; the **choice of the concrete implementation is a separate decision** |
| O6 | A schema that carries a `pattern` contract must declare the pin | yes, explicit, no implicit default (4.3) | **GO** |

## 8. Not verified

* Engines other than Python 3.14.4 `re`, Go 1.26.11 and Rust `regex` 1.13.2; other versions may differ (the version of each is in the evidence).
* The running times are one run on one machine, indicative. That a linear-time Python evaluator exists that meets the profile and its cost: not built, not measured (O5).
* Whether the closed profile is free of every other cross-engine divergence beyond the 84 probed constructs: not proven; the gate of section 5 is the means to keep finding them.
* The values of the three engines on strings that are not valid Unicode scalar values.
* That the candidate limit values are the right ones; they are bounded by the data, not proven optimal.
* Any behavior of the Forms or of a verifier: none evaluates a schema pattern today.
