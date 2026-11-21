# The `pattern` contract: choosing the linear-time evaluator (P1, O5)

Status: **decision preparation, documentation and isolated measurement only.** The final choice of the engine is the owner's. Not part of this pull request: any implementation of the profile, a normative vector set, a CI gate, a schema or grammar change, O2 (final limits) and O3 (reason identifiers), which follow in a separate pull request after this one is closed. Everything marked *recommendation* is a proposal.

Starting point (owner, 2026-11-21): the evaluator of the `pattern` contract must guarantee linear time in the worst case; a backtracking engine is not eligible (`GRAMMAR-PATTERN-PROFILE-DESIGN.md`, 3.4 and fact 8). Which concrete evaluator the Python side uses is the open decision. Go (`regexp`) and Rust (`regex`) already meet the requirement and are not in question; they are in the measurement as the cross-language reference.

## 1. The candidates

| Id | Candidate | What it is | Time guarantee |
|---|---|---|---|
| `re` | Python `re` (stdlib 3.14.4) | backtracking; the **baseline**, and the state the profile replaces | none |
| `regex` | PyPI `regex` 2026.11.19 | a backtracking superset of `re` (more features, optimizations) | none |
| `re2g` | PyPI `google-re2` 1.1.20251105 | the official RE2 Python bindings, a native extension | linear (RE2) |
| `re2p` | PyPI `pyre2` 0.3.14 | a third-party Cython wrapper of RE2, with a bundled `libre2` | linear (RE2), **but see 3.3: it falls back to `re` by default** |
| `nfa` | `nfa_engine.py` (191 lines, this evidence) | a Thompson NFA over code points for **the closed subset only**, no dependency; it parses only what the subset classifier has accepted | linear: O(states x value length) |
| `go` | Go 1.26.11 `regexp` | RE2 in Go | linear |
| `rust` | Rust `regex` 1.13.2 | finite-automata based | linear |

All Python-side candidates are measured with the same wrapper: the expression with its outer anchors removed, full match, no flags (the profile's rule); `.` is one code point except LF. The 256 code point cap on the value is the profile's wrapper and is applied by the runners, except in the timing group, which measures the engine itself on long values. Not measured, by reason: an RE2 binding in Python for other platforms than the wheels listed in 3.2; Hyperscan, PCRE2, `re2j` and similar (other languages or backtracking/non-RE2 semantics, no reason to widen the set).

## 2. What was measured (evidence in `docs/evidence/pattern-engine-selection/`)

Engines at the versions above, Docker stand-ins for Go and Cargo, one machine, one run: the times are indicative, the **orders of magnitude** and the **agreement** are the result.

### 2.1 Three-language parity (`results/parity.txt`)

* 141 hand-authored cases with an independent expectation (the 117 semantic cases of the profile probe: 9 contracts times 13 inputs including LF, CR, NUL, U+2028, U+00E9, an astral character; and the 24 in-subset constructs): **all 7 engines agree with the expectation on all 141**, the backtracking ones included (inside the subset they are correct, only slow).
* A seeded differential fuzz (seed 20261121): **1500 generated patterns, 15000 cases** (261 further generated texts were refused by the classifier and dropped, which also exercises the refusal side). Patterns are drawn from the grammar of the subset (literals, escapes, `.`, classes with ranges and the `&`, `~`, `-` literals, groups, alternation, all quantifier forms); inputs are a matching sample, near misses (one char more, one less, a leading or trailing LF) and random strings with LF, U+00E9 and an astral code point. **The five linear-time engines (`nfa`, `re2g`, `re2p`, `go`, `rust`) give the same verdict on all 15141 cases: 0 disagreements.**
* Limits of this claim: the fuzz alphabet is small (about 16 characters plus 5 extras); a longer-running or coverage-guided fuzz may find more; engines other than the versions above are not covered.

### 2.2 Running time (`results/timing.txt`, 53 cases)

The 46 timing cases of the profile probe, the review-F1 cases (a bounded repetition with no unbounded quantifier) and 7 cases at the profile's size limits (a 255-code-point value; `^(a|aa){1,255}$`, `^(a?){255}a{255}$`, 25 class runs of `{255}`):

| Engine | Worst match time over all 53 cases | Note |
|---|---|---|
| `re` | **> 10 s (killed) on 14 of 53 cases**; 8.8 s on the slowest that finished | exponential on `(a+)+`, `(a|aa)+`, `(a?){n}a{n}` |
| `regex` | **> 10 s (killed) on 1 of 53 cases**; 4.4 s on `(a|aa)+$` at 36 characters, 125 ms on `^(a?){255}a{255}$` | faster than `re` on some shapes (it passes `(a+)+$` in microseconds), still not linear |
| `re2g` | 2.4 ms | |
| `re2p` | 3.3 ms | |
| `nfa` | 25 ms (a 65536-character value, far beyond the 256 cap); **17 ms at the cap** (`^(a?){255}a{255}$`) | |
| `go` | 1.7 ms | |
| `rust` | 18.6 ms | |

Every engine other than `re` and `regex` stays at or below 25 ms on every case, on adversarial input, at and beyond the cap.

### 2.3 Compile cost and memory (`results/bench.txt`, 18 cases, one process per engine and case)

Compile time is the best of 5; the memory is the peak resident size above the size before the case (after a warm-up; the runtime and the imports are not counted; the noise floor is 0 to 70 kB for Python, 70 kB for Go, 200 kB for Rust).

| Workload | `re2g` | `re2p` | `nfa` | `go` | `rust` |
|---|---|---|---|---|---|
| the 9 existing contracts: compile | 5 to 9 us | 1.3 to 3 us | 21 to 102 us | 1.8 to 12.6 us | 9 to 35 us |
| the 9 existing contracts: match of a typical value | 2.7 to 5 us | 0.3 to 0.9 us | 2.4 to 44 us | 0.1 to 0.5 us | 0.04 to 0.14 us |
| worst compile at the limits (25 x `[a-z]{255}`, 6375 states) | 11 us | 7 us | **2.5 ms** | 0.3 ms | 0.7 ms |
| worst match at the cap (`^(a?){255}a{255}$`, 255 code points) | 1.0 ms | 1.1 ms | **17 ms** | 0.8 ms | 0.4 ms |
| peak memory at the limits (25 class runs) | 476 kB | 380 kB | **4.2 MB** | 4.5 MB | 2.0 MB |

For the real workload (127 pattern-constrained values in the three measured records) the own evaluator needs on the order of a few milliseconds in total (derived from the per-value match times above, not measured as a separate run). It is 10 to 100 times slower than the C++ and native engines and still inside any budget a release verification has; it is not a candidate for a hot path, and the profile has none.

### 2.4 Fail-closed behavior of the candidates (`results/constructs.txt`)

* Every engine refuses what it cannot compile (`compile_error`); the closed-subset classifier refuses the out-of-profile constructs **before** any engine sees them, so this is defense in depth.
* **`pyre2` with its default configuration silently accepts 5 constructs that RE2 itself refuses** (lookahead, negative lookahead, lookbehind, back-reference, possessive quantifier): it hands them to Python `re` (backtracking, different semantics) and returns a pattern object of the type `FallbackPattern`. This is the opposite of the profile's rule (no fallback to a native engine). It can be turned off, but only with a process-global setting (`set_fallback_notification(FALLBACK_EXCEPTION)`), which any other code in the process can change back.
* `google-re2` refuses them with an error and logs the reason on stderr through Abseil; no fallback exists.
* `nfa` accepts only what the classifier accepted; a text outside the subset raises a refusal at compile time and never reaches the matcher.

### 2.5 The measurement can fail (`selftest-harness-output.txt`)

Eight defects are planted, one at a time, into a copy of the Python-side files (`.` also matches LF; a prefix match instead of a full match; an exclusive class bound; a bounded repetition with one optional copy too few; an optional copy that cannot be skipped; a constant `re2g` engine; and the **same** defect in two engines and in three engines at once). The parity gate must exit 1: **8 of 8 detected**, and each defect is run twice, with the canaries (known-answer cases, which catch a constant or stale engine at once) and **with the canaries switched off**, so the parity layer alone is also shown to see it: 8 of 8 again. A defect that three engines share is still seen, because `go` and `rust` disagree with them.

### 2.6 Dependency and supply-chain record (`supply-chain-output.txt`, read from PyPI on 2026-11-21)

| | `google-re2` | `pyre2` | `regex` | own `nfa` | Go / Rust native |
|---|---|---|---|---|---|
| Source | RE2 authors (Google) | one third-party maintainer | one maintainer | this repository | standard library / the `regex` crate (already pinned in `Cargo.lock`) |
| Latest release | 2025-11-05 (**12 months old**) | 2026-09-25 | 2026-11-18 | n/a | n/a |
| Releases | 26 since 2019 | 8 since 2020 | 375 since 2010 | n/a | n/a |
| Wheels for Python 3.14 | 11 (Linux x86_64 and aarch64, macOS arm64 and x86_64) | 4 (Linux x86_64 and aarch64, macOS arm64, Windows) | 16 | none needed | n/a |
| License | BSD | BSD-3-Clause | Apache-2.0 and CNRI-Python | the repository's | n/a |
| New binary dependency | **yes** (a native extension, the bundled RE2 build) | **yes** (a native extension and a bundled `libre2`) | yes | **none** | already present |
| Fail-closed by default | yes | **no** (fallback to `re`) | n/a (not linear) | yes | yes |

The measured wheels have these sha256: `google_re2-1.1.20251105-1-cp314-...manylinux_2_28_x86_64.whl` `a7bfaa2c...c116`, `pyre2-0.3.14-cp314-...manylinux_2_17_x86_64.whl` `a1522bc9...be14e`. The RE2 library version bundled in either wheel was **not** established.

## 3. Assessment

**3.1 Not eligible.** `re` and `regex` (time: fact above). They are in the table because they are what a reader would try first.

**3.2 `google-re2`.** Correct (0 disagreements), the fastest Python-side option, official, fail-closed. Costs: a native binary dependency in every environment that evaluates a pattern (wheels exist for the common platforms; the last release is a year old at the time of this record); its stderr logging is noisy; a version bump of the dependency is a semantic event that must be re-measured, since the profile's meaning would then depend on a binary the project does not build.

**3.3 `pyre2`.** Correct once its fallback is turned off, and fast, but fail-open by default and only closeable by a global switch. A single maintainer. **Not recommended**: the profile's central rule is that nothing falls back.

**3.4 `nfa` (own evaluator).** Correct on every measured case (0 disagreements in 15141 fuzz and 141 hand-authored cases), no dependency, and the strongest property: the **text that runs is exactly the text the classifier accepted**, parsed by one grammar, so "the classifier accepts but the engine reads it differently" cannot happen on the Python side. The meaning of the profile is then *written down as code that anyone can read in 191 lines* rather than inherited from a library. Costs: 10 to 100 times slower than the native engines (17 ms worst at the cap, 2.5 ms worst compile at the limits, 4 MB peak: all inside any budget of a release verification); **the project owns the code**, and a bug in it is the project's bug. The mitigation is the gate, not trust: the evaluator is compared with Go, Rust and (optionally) RE2 on every vector and on a seeded fuzz in every CI run, and the self-test shows that the comparison sees a planted defect, even when three engines share it.

**3.5 Go and Rust.** Unchanged: the native engines of the two other implementations, already linear. Their agreement with `nfa` and with RE2 on 15141 cases is the cross-language parity result.

## 4. Recommendation

1. **The normative Python reference evaluator is the own `nfa` evaluator** (or an implementation of the same specification), behind the closed-subset classifier. It is the only candidate that adds no dependency, cannot fall back, and makes the profile's meaning executable in the repository.
2. **`google-re2` is admitted as an optional cross-check engine in the CI gate** (a development and CI dependency, not a runtime one): a third, independently written implementation raises the strength of the parity gate at no runtime cost.
3. **`pyre2`, `re` and `regex` are not used** by the profile (the first two for the reasons in 3.1 and 3.3).
4. Go and Rust keep their standard engines; the profile's limits (O2) and reason identifiers (O3) are decided in the next pull request, using the measured costs above (compile time, memory and the 17 ms worst case at the cap are inputs to O2).

The alternative, if the owner prefers no owned evaluator: `google-re2` as the runtime evaluator, with the same gate and the same classifier in front. Nothing in the measurement contradicts it; what changes is the dependency, not the semantics.

## 5. What the decision needs from the owner

| # | Decision | Options |
|---|---|---|
| E1 | The Python reference evaluator | **own `nfa` (recommended)** / `google-re2` as the runtime evaluator |
| E2 | `google-re2` as an optional CI cross-check | yes (recommended) / no |
| E3 | Whether an evaluator version belongs to the pin | the profile version (O1) pins the **semantics**; the evaluator is an implementation and is not pinned, its conformance is the gate (recommended) / pin it |

## 6. Not verified

* Engine versions other than those listed; other platforms than Linux x86_64 for the measured wheels; Windows and macOS were not run.
* The bundled RE2 version inside the `google-re2` and `pyre2` wheels.
* Fuzz coverage beyond 15000 cases and the small alphabet; strings that are not valid Unicode scalar values.
* The running times are one run on one machine with Docker stand-ins for Go and Rust; the **real-workload total** in 2.3 is derived, not measured as a run.
* The behavior of any Forms evaluator or verifier: none evaluates a schema pattern today, and none is changed here.
