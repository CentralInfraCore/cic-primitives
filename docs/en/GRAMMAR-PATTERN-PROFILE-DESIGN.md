# The `pattern` contract: a closed regular-expression profile (P1, design and measurement)

Status: **design draft, documentation and evidence only.** Not part of this pull request: any change of the grammar, of a checker, of the Forms or of a verifier; the derived JSON Schema; P2, P4, #166; the finalization of the release schemas. Everything marked *candidate* is a proposal for the owner, not a decision.

Owner direction (2026-11-21), taken as the starting point: a closed, explicit RE2 subset (what is not allowed is forbidden); full match, with `^` and `$` allowed only at the outer boundary; `.` never matches LF and a `$` never lets a trailing LF through; ASCII classes, `.` is one Unicode code point except LF; an own, explicit pattern-profile pin with a life cycle independent of the node-name grammar; the seven existing expressions keep their text and their semantic compatibility is measured; one shared vector set for Python, Go and Rust with a mandatory CI gate. Added by the owner: **resource limits** (length, repetition, nesting, worst-case running time) and **fail-closed semantics** (an unsupported construct is refused at compile time, with no fallback to the full native engine). The name of the version field and the compatibility decision are to be settled by the measurements below.

## 1. What is undefined today

The atom `schemas/atomic/contract.yaml` declares the type as `pattern: regex`: **no flavor, no anchoring rule, no limits.** The expression is matched by whoever reads it. The only reader today is the Python `jsonschema` library inside the grammar checker (a *search*, as `re.search`); the Forms list contracts as unevaluated and evaluate none; the reference verifier does not evaluate schema patterns (its own digest and commit checks are hard-coded and end in `\Z`). The release schema set (the draft of cic-primitives #38) declares seven distinct `pattern` expressions.

## 2. Facts (measured; evidence in `docs/evidence/grammar-pattern-measurement/`)

Engines: Python 3.14.4 `re`; Go 1.26.11 `regexp` (RE2); Rust `regex` 1.13.2 (default limits). The matching rule under test is the one the owner directed: the expression with its outer `^` and `$` removed, matched as a **full match** (`\A(?:body)\Z` in Python, `\A(?:body)\z` in Go and Rust), no flags.

1. **Inventory** (`inventory-output.txt`). In the cic-primitives tree, the release schema drafts and the cic-schema-registry at its pinned commit there are **9 distinct `pattern` contracts** in 37 declarations (7 release, 1 in an example schema, 1 CIDR shape in the registry's network schemas). **All 9 are inside the candidate subset.** Their maxima: length 89, repetition count 64, group nesting 1, at most 3 unbounded quantifiers, none unbounded on a group. Separately, **9 distinct JSON Schema `pattern` keys** of the grammar's own meta-schemas and the registry's block schema (a different layer: only the Python `jsonschema` library evaluates them) fall outside it (`\d`, `\n`, a negated class, more than 3 unbounded quantifiers).
2. **Semantic parity inside the subset** (`results/probe-semantic.txt`). 117 cases (the 9 contracts times 13 inputs: valid, empty, trailing/leading/double LF, trailing CR, CRLF, NUL, U+2028, U+00E9, an astral character, truncated, one char more): **the three engines give the same verdict on all 117, and it equals an independently authored expectation.** `.` takes CR, NUL, U+2028, U+00E9 and an astral code point in all three, and refuses LF in all three.
3. **The legacy semantic differs in exactly one way.** Python `re.search` of the original expression accepts the valid value **plus one trailing LF** for all 9 contracts, and for `^vault:v1:.+$` also `...\r\n` (10 of the 117 cases). This is the node-name `abc\n` defect of the pinned grammar, now measured on the release patterns. Go and Rust never did.
4. **Real data** (`compat-records-output.txt`). The pattern-constrained values of the record `v0.2.1` (55), the golden record (17) and the probe base record (55): **0 contain a line feed, 0 change their verdict** between the legacy and the candidate semantic.
5. **Constructs outside the subset diverge** (`results/probe-constructs.txt`, 70 constructs). **20 of the 70 give different results in the three engines**, for example `a{,3}` (Python a quantifier, Go a literal, Rust a compile error), `[a-z&&[^b]]` (Rust reads a set intersection, the others a set followed by a literal `]`), `a++` (Python and Rust accept, Go refuses), `(?i)` and `(?s)` (Python refuses mid-expression use in this position, the others accept), `\p{L}`, `(?<n>a)`, `\Q..\E`, lookaround and back-references (Python only), `A`, `\101`. The 23 constructs of the subset that were probed give the same result everywhere (no exception). A native fallback would therefore make the verdict depend on the engine.
6. **Compile limits differ** (`results/probe-limits.txt`): a repetition count above **1000** is refused by Go only; group nesting of **250** is refused by Rust (and 500 by Python); nested repetition with a product of 100 x 100 is refused by Go, 1000 x 1000 by Rust; an expression of 262144 characters and a class of 255 items compile everywhere. The syntactic subset alone does not give the three engines the same resource behavior.
7. **Running time** (`results/probe-timing.txt`, one run, indicative): Python's backtracking is **exponential** on `(a+)+$` (7.8 s at 28 characters, over 10 s at 32) and `(a|aa)+$` (1.8 s at 36), and **polynomial** on adjacent unbounded quantifiers: `a*a*a*$` takes 11 ms at 256 characters, 85 ms at 512, 660 ms at 1024, 4.8 s at 2000, over 10 s at 8000. Go and Rust stay under 0.5 ms on every case (linear time). The 9 existing contracts stay under 1.4 ms on 65536-character adversarial values in all three engines.

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

**3.3 Characters.** `.` matches **one Unicode code point except LF** (U+000A). It matches CR, NUL, U+2028, non-ASCII and astral code points (measured identical in the three engines). The classes are ASCII ranges and members. The value is a sequence of Unicode scalar values (a string the YAML reader produced); a lone surrogate is outside the profile.

**3.4 Resource rules (candidate values; the rules are decided here, the numbers from the data).**

| Rule | Candidate | Why this number |
|---|---|---|
| Expression length | at most 256 characters | the existing maximum is 89; every engine compiles far more |
| One repetition count (`n`, `m`) | at most 255 | Go refuses above 1000; the existing maximum is 64 |
| Group nesting depth | at most 4 | Rust refuses 250, Python 500; the existing maximum is 1 |
| Product of nested repetition counts | at most 1000 | Go refuses 100 x 100 = 10000; 30 x 30 compiles; the existing maximum is 9 |
| An unbounded quantifier (`*`, `+`, `{n,}`) | only on a single atom, **never on a group** | `(a+)+$` and `(a|aa)+$` are exponential in Python |
| Number of unbounded quantifiers | at most 3 | adjacent ones are polynomial in Python; the existing maximum is 3 |
| Length of the value that is matched | at most 256 code points | with 3 unbounded quantifiers the Python worst case at 256 is 11 ms, at 1024 it is 660 ms; the longest pattern-constrained value of an existing record is 105 characters (`release.sign`) |

A value longer than the limit **does not match** (a contract violation, not a crash). The limits are part of the profile and are the same for every engine, so a Go or Rust evaluator that could do more still refuses more. The Python reference evaluator may use `re` only behind these rules, or a linear-time engine; which of the two is an open point (section 7).

**3.5 Fail-closed.** An expression outside the profile is **refused when the schema is read** (the producer and the verifier refuse the schema, not the value). There is no fallback to the native engine, no flag, no per-engine behavior, and no partial acceptance: a schema with one refused expression is refused as a whole. The refusal names the construct. (The reason identifiers are an open point; working names in section 7.)

## 4. Versioning and compatibility

**4.1 An own pin.** The profile is identified by its own explicit version, **independent of the node-name grammar version** (its own life cycle: either can move without the other). The binding rule follows the precedent of `access-policy/1` and of the node-name profile: the version is a property of the pinned schema and of the processing context, **never a document key**; no default; a missing, an unknown and a conflicting version are three distinct errors.

**4.2 Where it is declared (open, from the measurement).** The type `pattern` is declared in the atom `schemas/atomic/contract.yaml`; the node-name pin sits in `schemas/atomic/shape.yaml` (`spec.node_name_grammar.version`) because it constrains a Shape member. The measurement favors the same logic here: the pin sits with the atom that defines the contract type, as `spec.pattern_profile.version` in `contract.yaml` (candidate name). This is a recommendation, not a decision (section 7).

**4.3 Compatibility.** The text of all 9 distinct existing contracts is unchanged (all inside the subset). The measured semantic differences between the legacy reading and the profile are exactly the values that end in LF (and `...\r\n` for `.+`); **no value of any existing record has one** (127 values, 0 line feeds, 0 changes). Nothing evaluates schema patterns in production today. The profile is therefore **not** a breaking change of any existing record or schema; its first version is the first one anyone can pin (legacy = "no pin = no defined semantic", the state of section 1). The compatibility decision for the owner is only whether a schema that carries a `pattern` contract must declare the pin (recommended, in line with 4.1) or may rely on the profile being the default (not recommended: no default is the rule everywhere else).

## 5. Vectors and the gate (design; nothing is built here)

One shared vector set, in the style of the node-name vectors (`name-vectors/node-name.yaml`): per vector, the expression, the input, the **profile verdict** and the verdicts of the three engines; and **refusal vectors** (an expression outside the profile, with the construct that must be named). A gate builds and **runs** the Go and Rust runners on every CI run, with the required-run switches of the existing gates, plants identical defects in both runners (two outputs that agree prove nothing) and proves that the gate can fail. The prototype of this gate is the evidence of this pull request: `probe_engines.py` (3 engines, 4 groups) and `gate_selftest.py` (4 planted defects, 4 detected, including the same defect in both runners), `subset_check.py` with `selftest_subset.py` (83 vectors) with `selftest_subset_mutants.py` (12 planted defects of the classifier detected, a 13th masked by a second layer, stated), `compat_records.py` with its self-test.

## 6. Effect on the other points

* **P4** (the timestamp pattern) depends on this profile for the meaning of a pattern; whether a pattern may carry calendar validity is P4's own question and is not touched.
* **P2** (the `must` dialect) is independent.
* **Forms #166, #167:** unaffected; the Forms evaluate no contract. A Forms evaluator of patterns would implement the profile natively (the Go and Rust engines accept every construct of it).
* **Release schemas:** the seven expressions are unchanged; finalization stays on hold (P2, P4, #167 evaluation).
* **The grammar's own JSON Schema patterns** (9 distinct expressions outside the subset): see the scope point in section 7.

## 7. Open points (for the owner)

| # | Point | Recommendation |
|---|---|---|
| O1 | Name and place of the version field | `spec.pattern_profile.version` in `schemas/atomic/contract.yaml` (candidate), with the three binding errors of 4.1 |
| O2 | The limit values of 3.4 | the candidate values above; the data is in section 2 |
| O3 | Reason identifiers | working names, **not decided and not in any declaration**: `pattern_syntax_unsupported` (schema refused), `pattern_value_too_long` (value above the limit); decided with the reason inventory when the implementation is approved |
| O4 | Scope | the profile covers the `pattern` **contract**; the grammar's own JSON Schema `pattern` keys stay as they are (the node-name rule already carries its guard); a later, separate decision whether they join |
| O5 | The Python reference evaluator | the rules of 3.4 in front of `re`, or a linear-time engine; recommended: the rules (no new dependency; the measurement shows they bound the worst case) |
| O6 | A schema that carries a `pattern` contract must declare the pin | recommended yes (4.3) |

## 8. Not verified

* Engines other than Python 3.14.4 `re`, Go 1.26.11 and Rust `regex` 1.13.2; other versions may differ (the version of each is in the evidence).
* The running times are one run on one machine, indicative.
* The values of the three engines on strings that are not valid Unicode scalar values.
* That the candidate limit values are the right ones; they are bounded by the data, not proven optimal.
* Any behavior of the Forms or of a verifier: none evaluates a schema pattern today.
