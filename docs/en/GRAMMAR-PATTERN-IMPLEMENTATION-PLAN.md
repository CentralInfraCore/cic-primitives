# The `pattern` profile: implementation plan (draft)

Status: **a plan, documentation and isolated tooling only. It is not an implementation and not permission to implement.** No module named here exists and none is created by this package; executing the plan needs a separate owner GO. Not in this package, all on hold: any implementation, the independent third implementation, the CI gate and its wiring, the normative publication of the vectors, the integration of the Forms (a separate work package), D7 and D8, P2, P4, Forms #166/#167, the schema finalization, the Relay #162 implementation.

It cuts the **27 obligations** of the implementation specification (`GRAMMAR-PATTERN-IMPLEMENTATION-SPEC.md`, #52) into implementation units, tests and acceptance gates, in the order of the owner's professional recommendation. **The 513 approved vectors stay the unchanged reference** (the SHA-256 of the vector file, `e7ece43a...`, is held by the check of this package). The 47 proposed extension cases are a separately reviewed extension (`GRAMMAR-PATTERN-EXTENSION-CASES-REVIEW.md`); the plan never counts them as part of the 513.

Machine-readable form: `docs/design/pattern-profile-plan/plan.yaml` (11 units, 14 gates, 7 milestones, 4 open points, 5 fallback tests); the tooling in `docs/evidence/pattern-impl-plan/`.

## 1. Choices proposed (for the owner)

| Question | Proposal | Reason |
|---|---|---|
| language | Python | the producer and verifier environment of the Primitives is Python; the Forms integration is a separate work package |
| repository | `cic-primitives` | the profile belongs to the Primitives |
| layout (a proposal) | package `tools/pattern_profile/`, tests in `tests/pattern_profile/` | no module exists yet |
| evaluator | the own automaton (E1) | decided in #47: linear time, never backtracking |
| native cross-check | Go `regexp` and Rust `regex`; google-re2 optional (E2) | decided in #47; they check value verdicts and the compilation of accepted expressions (rule D) and are never the classifier |
| run evidence | names the implementation that ran (E3) | decided in #47 |
| conformance base | the 513 approved vectors; the 47 extension cases reported separately; 560 only if all 47 are accepted unchanged | the approved set keeps its own integrity reference |
| independent implementation | another developer, another language, from the specification and the vectors only | the real independence test |

## 2. The milestones (the seven steps)

| Milestone | Step | Units | Gates | State |
|---|---|---|---|---|
| M0 owner prerequisites | 1 | none | G-0 | the owner confirms D1 to D6 |
| M1 the 47 extension cases | 2 | none | G-0 | accepted, rejected or deferred, in a separate pull request |
| M2 the implementation plan | 3 | none | none | this package |
| M3 the primary implementation (Python) | 4 | U-01 to U-07 and **U-10a, the standalone conformance harness** | G-1 to G-6, G-8, G-10 | **on hold** until the owner's GO |
| M4 the independent implementation and the comparison | 5 | none | G-11 | **on hold** |
| M5 producer and verifier integration | 6 | U-08, U-09 | G-7, G-9 | **on hold** |
| M6 the CI gate and the normative publication | 7 | U-10b, the CI integration of the harness | G-12, G-13 | **on hold** |

The check refuses a plan in which a milestone with units comes before the milestone of the owner's decisions, in which a unit sits earlier than a unit it comes after, in which the dependencies between units contain a cycle (see 3.1), and in which a gate is executed by a unit built in a later milestone than the gate (see 3.2).

## 3. The units: the 27 obligations cut into implementation units

| Unit | Implements | Module (proposal) | Milestone | After | Tests (approved vectors, extension group, plan item) | Needs decisions |
|---|---|---|---|---|---|---|
| U-01 typed document reader | O-RD-01, O-RD-02, O-RD-03, O-RD-04, O-RD-06 | `reader.py` | M3 | none | extension E-RDR, E-TRV, E-PIN; plan P-06, P-07, P-08 | D1, D4, D5, D6, **OP-1** |
| U-02 record value delivery | O-RD-05 | `values.py` | M3 | none | approved values; plan P-05 | none |
| U-03 pin resolution and identity | O-VA-01, O-VA-02 | `pin.py` | M3 | U-01 | approved schemas; extension E-PIN; plan P-07 | D1, D2, D3, **OP-1** |
| U-04 expression classifier | O-VA-03 to O-VA-08, O-VA-10 | `classifier.py` | M3 | none | approved expressions | none |
| U-05 evaluator (own automaton) | O-VA-11, O-VA-12, O-VA-13 | `evaluator.py` | M3 | U-04, U-02 | approved values; plan P-01, P-05 | none |
| U-06 schema validator | O-VA-09 | `validator.py` | M3 | U-01, U-03, U-04 | approved schemas; extension E-TRV; plan P-08 | D4 |
| U-07 evidence keys and run evidence | O-GT-02, O-VF-04 | `evidence.py` | M3 | U-03, U-06 | plan P-10, P-03 | none |
| U-08 producer checks | O-PR-01, O-PR-02 | `producer.py` | M5 | U-06, U-05 | plan P-02, P-11 | none |
| U-09 independent verifier | O-VF-01, O-VF-02, O-VF-03 | `verifier.py` | M5 | U-06, U-05 | plan P-02, P-07, P-04 | none |
| U-10a standalone conformance harness | O-GT-01 | `tests/pattern_profile/harness` | **M3** | none | plan P-01, P-03 | none |
| U-10b CI integration of the harness | O-GT-01 | `.github` (on hold) | M6 | U-10a, U-07, U-08, U-09 | plan P-01, P-03 | none |

What each unit does: **U-01** keeps mapping entries in source order, represents a pin value in a type-preserving tree (a host-language dictionary that merges `1`, `true` and `1.0` is not allowed), finds duplicate keys by the identity rule, requires string keys in the schema document, delivers the contracts in document order, and reports reader errors with no pattern code; **U-02** delivers the pattern-constrained values as code points and flags a lone surrogate; **U-03** resolves the pin (missing, conflict before unknown, identical as one, the exact int `1`) with the recursive type-sensitive identity, only when a pattern contract exists and before every expression; **U-04** classifies an expression (tier 1, the scan, the class and quantifier rules in order, the size PI on the whole tree, one code per refused expression); **U-05** is the own automaton with full match over code points, the value order and a work bound `c x (PI + 1) x (N + 1)`; **U-06** validates a delivered schema (the pin, then the first refused expression in the given order decides code and path; refused as a whole); **U-07** computes the typed canonical encoding, the component digests, the class key and the evidence identifier with their domain tags, within the scope of a successful document read, with the implementation identity and the conformance reference; **U-08** resolves and classifies at build time and refuses to emit a violating value; **U-09** repeats steps 0 to 3 independently with its own total work budget and its own code; **U-10a** is the standalone harness (no CI wiring) that runs the vectors against an implementation with typed exits and canaries and records the run evidence; it is the tool that executes gates G-2 to G-6, G-8 and G-10, so it is built in the **same milestone as the implementation it checks**; **U-10b** is its CI integration, which stays on hold (the split does not authorise the CI gate earlier).

### 3.1 The dependency graph (review F2 of #54)

The `after` relations between units must form a **DAG**: `check_impl_plan.py` refuses a unit that depends on itself and any cycle (also inside one milestone, and through three units), and it produces a **topological order** (`results/check_impl_plan.txt`: U-01 U-02 U-04 U-10a U-03 U-05 U-06 U-07 U-08 U-09 U-10b). Negative tests: a self-dependency, a cycle of two units, a cycle through three units.

### 3.2 The harness comes with the implementation (review F1 of #54)

An earlier version put the whole gate harness in M6, after the implementation milestone that already required gates G-2 to G-5: the tool needed to accept the implementation would have been built only after it. Now every gate may list the units that execute or enable it (`requires_units`), and the check refuses a plan in which such a unit is built in a **later** milestone than the gate (negative test: U-10a in M6).

### 3.3 Three levels of coverage, kept apart (review F4 of #54)

1. **Planned:** the tests that the units name, the extension cases included (92 (unit, requirement) pairs, all planned).
2. **Baseline:** what the **approved vectors and the plan items that do not depend on the extension** cover (87 of the 92 pairs). The extension cases, and the plan items whose status is "proposed extension" (P-07, P-08, P-09), are **not** baseline.
3. **Executed:** a check that has really been run against an implementation. **None: no implementation exists** (`execution.state: not_started`); the check refuses a claim of execution without an evidence reference.

The **5 pairs that the plan covers only through the extension** need a **fallback test independent of it**, to be authored with the implementation if the cases are rejected or deferred (OP-2): F-01 and F-03 (the pin: wrong types, conflict before unknown, identical declarations, the typed identity, the type-preserving reader), F-02 and F-04 (the traversal and the reader errors), F-05 (the verifier reports a bad pin before a bad expression). The check refuses a plan in which such a pair has no fallback. A deferred or rejected case therefore never silently counts as coverage.

**Traceability.** `check_impl_plan.py` refuses the plan if **any of the 27 obligations is not assigned to a unit**, if a unit has no tests, and, beyond a plan id that merely exists, if the tests of a unit **do not actually cover each requirement of its obligations** (an approved vector kind that has a vector naming the requirement, an extension group whose cases name it, or a plan item that lists it). `results/check_impl_plan.txt` prints the obligation-to-unit and the milestone-to-unit-and-gate matrices. This is **structural** traceability and internal consistency; it does not show that the tests, once written, give full semantic coverage.

## 4. The acceptance gates

| Gate | Criteria (short) | Evidence | Approval | Typed exits | Plan items |
|---|---|---|---|---|---|
| G-0 owner prerequisites | D1 to D6 confirmed; the 47 extension cases accepted, rejected or deferred | the owner's recorded decisions | owner | no | none |
| G-1 reader | every reader error has its kind and no pattern code; source order and the key types of a pin value are kept; the traversal cases pass | E-RDR, E-TRV and the reader tests | review | yes | P-06 |
| G-2 approved vector conformance | **all 513 approved vectors pass** (expression verdicts and PI, value verdicts, schema verdicts with the whole triple); 0 disagreements | a conformance run with typed exits (0 ok, 1 a DISAGREE line, 2 infrastructure, 3 a failed canary) | review | yes | none |
| G-3 extension conformance | the accepted extension cases pass, **reported separately** from G-2 | the same run over the extension file with its own integrity reference | review | yes | P-07, P-08 |
| G-4 native cross-check | Go and Rust agree on the value verdicts and every accepted expression with PI <= 2048 compiles in every engine | the native run with the canaries | review | yes | none |
| G-5 harness self-test | the conformance harness can fail for the right reason: planted defects detected with the intended line, infrastructure controls exit 2 | the self-test output | review | yes | none |
| G-6 work bound | the deterministic work is at most `c x (PI+1) x (N+1)` on the adversarial corpus, zero-size programs and the empty value included | the work counter per case | review | yes | P-01 |
| G-7 producer and verifier independence | a producer stub that reports success for violating input is refused by the verifier's own checks; the producer refuses exactly as the validator does | the refusals per stub and vector | review | yes | P-02, P-11 |
| G-8 evidence keys and run evidence | a changed pin never makes a result reusable; a component digest alone is never a reuse key; a refused document gets no key; the run evidence names the implementation | the key and property checks, the versions record | review | yes | P-10, P-03 |
| G-9 verifier budget | the verifier stops at its own budget with its own code; additive in contracts and values; a fixed cost per contract and per value | the budget code and the work spent | review | yes | P-04 |
| G-10 code points | a lone surrogate is decided before the conversion; the length is counted in code points in every language of the run | the harness verdicts | review | yes | P-05 |
| G-11 independent comparison | a second implementation by another developer, in another language, from the specification and the vectors only; every difference logged and decided, never auto-corrected | the comparison record | owner | yes | none |
| G-12 CI gate and publication | the gate wired with the required-run switches; the normative publication | the owner's approvals | owner | no | none |
| G-13 deferred work | the composition of schema parts and the order of several violating values specified and their cases reviewed (D7, D8) | the specification extension | owner | no | P-09 |

**The first implementation is accepted against the 513 approved vectors (G-2).** If the 47 extension cases are accepted unchanged, the acceptance extends to 560 (G-3), reported separately; the integrity of the original 513 stays a separate reference. **Every one of the 11 plan items (P-01 to P-11) is placed in at least one gate**; the check refuses a plan with an unplaced one.

## 5. Open points and risks (for the owner)

* **OP-1 the YAML scalar resolution rules, a PREREQUISITE of U-01 and U-03 (review F3 of #54).** The type class of a pin value depends on the resolver, and the specification says the reader delivers raw typed values but not which scalar schema. **Measured** (`op1_probe.py`, `results/op1_probe.txt`): PyYAML (YAML 1.1 rules) differs from the YAML 1.2 core schema on **12 of 42 scalars**: `010` is the int 8 (core schema: the decimal int 10), `0o10` a string (core: the int 8), `08` a string (core: the int 8), `1_000` the int 1000 (core: a string), `0b10` the int 2 (core: a string), `on`, `off`, `yes`, `no` are bools (core: strings), `1e3` a string (core: the float 1000.0), `1:30` the int 90 and `2001-01-01` a date (core: strings). PyYAML also accepts aliases and merge keys, honours the explicit tags `!!str` and `!!int`, rejects unknown tags, **silently keeps the last of two equal keys** (`a: 1` then `a: 2` gives 2) and **merges the keys `1` and `true` into one**. **Proposed fixation for the owner to decide:** the **YAML 1.2 core schema** (null `~`, `null`, `Null`, `NULL` and the empty value; bool only `true`, `True`, `TRUE`, `false`, `False`, `FALSE`; int `[-+]?[0-9]+` read as **decimal, so `010` is the int 10, not a string and not an octal**, `0o` octal, `0x` hexadecimal; float by the schema's expression with `.inf` and `.nan`; everything else a string); **explicit tags:** only the core tags `!!str`, `!!int`, `!!float`, `!!bool`, `!!null`, `!!seq`, `!!map` are honoured, any other tag is a reader error; **duplicate keys:** a reader error in the schema document and in a pin value; **aliases and merge keys:** a reader error (no shared structure, no expansion). **OP-1 is closed by the gate G-0 and is a recorded need of U-01 and U-03; the check refuses a plan in which the reader could start before it is closed.** The reference resolver of the probe is written from the schema's regular expressions and checked against a table of 42 hand-written cases (a planted resolver that reads `010` as octal, `on` as a bool or `1_000` as an int is caught).
* **OP-2** whether the 47 extension cases are accepted unchanged, in part or deferred (G-0); **OP-3** the constant `c` of the work bound and the counted operations, fixed in the measurement of G-6; **OP-4** whether the native cross-check runs in CI (toolchains) or only in the gate harness run.
* **RK-1** the Python evaluator is slower than the native engines (measured at PI 2048, cold: own 21 ms, Go 3 ms, Rust 61 ms); acceptable for release verification, but the verifier's budget must account for it. **RK-2** PyYAML resolves scalars by YAML 1.1 and merges equal keys of different types in a dictionary: a custom loader is required (OP-1). **RK-3** the specification, the vectors and the prototypes share an author: the independent implementation (G-11) is the real test.

## 6. Out of scope

The integration of the Forms (a separate work package); implementations in Go and Rust (they are the native cross-check only); the composition of schema parts and the order of several violating values (D7, D8); any change of the approved vector file, the schemas, the grammar or a checker of the repository.

## 7. Evidence of this package and what is not shown

`docs/evidence/pattern-impl-plan/` (typed exits: 0 ok, 1 a measured failure, 2 infrastructure): `check_impl_plan.py` (the approved vector file byte-identical; the counts 513, 47 and 560 equal the files; all 27 obligations assigned; the units' tests cover their requirements; the milestone, unit and gate order; the hold flags; all plan items placed; the text mentions every id) and `selftest_impl_plan.py` (32 checks; the check can fail, for the right reason: a positive control, 25 planted faults in copies of the plan, the document and the approved vector file (nine of them for the findings of #54: a harness built too late, three dependency cycles, an open point that no longer blocks its unit, a gate that no longer names it, a missing fallback, a fallback for an unknown unit, a claim of execution without evidence), 4 checks of the OP-1 probe (a positive control and three planted defects of the reference resolver) and 2 infrastructure controls that exit 2) and `op1_probe.py`.

**Not shown:** an implementation; any executed check (level 3 of the coverage is empty); that the tests, once written, give full semantic coverage; the owner's confirmation of D1 to D6; the decision on OP-1 to OP-4; the independent implementation. The plan is one author's cut of the obligations into units.
