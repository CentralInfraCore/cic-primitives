# Evidence: choosing the linear-time evaluator of the pattern profile (P1, O5), 2026-11-21

For `docs/en/GRAMMAR-PATTERN-ENGINE-SELECTION.md`. **Measurement and prototypes only: no grammar, checker, Forms or verifier is changed.** It builds on `docs/evidence/grammar-pattern-measurement/` (the closed-subset classifier `subset_check.py`, the Go and Rust drivers, the corpora of `probe_engines.py`).

| File | What it shows |
|---|---|
| `nfa_engine.py` | candidate D: a Thompson NFA for the closed subset only (204 lines, no dependency); parses only what `subset_check.parse` accepted; the epsilon closure is followed on the fly, O(P x N) |
| `engines.py`, `runner_py.py` | one adapter interface for `re`, `regex`, `re2g` (google-re2), `re2p` (pyre2, fallback OFF), `nfa`, and the child-process runner (verdicts; bench) |
| `nfa_closure_precomputed.py`, `closure_probe.py`, `results/closure.txt` | review F1: the superseded evaluator that precomputed every state's closure, and the measurement of what it cost (quadratic closure table, 100x compile cost on closure-heavy valid patterns) against the current one |
| `construct_expect.py` | review F3: independent hand-authored expected verdicts for the 24 accepted constructs, each with a counterpart (48 cases) |
| `fuzz_gen.py` | the seeded generator of in-subset patterns and inputs |
| `selection_probe.py`, `probe-run-output.txt`, `results/{parity,timing,bench,constructs}.txt` | the groups: `versions` (the engines that actually ran: versions, hashes, lock files); `parity` in four separate parts (A 165 hand-authored cases against an independent expectation, B the differential on 1500 generated patterns / 15000 cases, C the stdlib `re` as a bounded second opinion on them, D accepted patterns must compile everywhere); 53 timing cases; 18 compile/match/memory cases (one process per engine and case); the 84 constructs per engine, including pyre2 with its default fallback. Typed exits: 0 ok, 1 a measured failure, 3 a failed canary, 2 INCOMPLETE (infrastructure, never a detection) |
| `bench/go`, `bench/rust` | the bench runners (compile best of 5, match median of 7, peak memory above the start via `/proc/self/clear_refs`) |
| `selftest_harness.py`, `selftest-harness-output.txt` | the parity gate can fail, for the right reason: an unmodified positive control (exit 0), 10 planted defects (also the same defect in 2 and 3 engines at once), each run with and without the canaries and counted only when the planted engine is named by a measured failure: 10/10; and 3 infrastructure controls that must be exit 2 and not a detection: 3/3 |
| `red_initial_f2_f3.py`, `red-initial-f2-f3-against-d1e0b8c.txt` | RED-initial for F2 and F3 against the previous head: its probe exits non-zero on a missing interpreter (the previous harness called that a detection) and its decision rule passes an all-engine compile error on an accepted pattern |
| `supply_chain.py`, `supply-chain-output.txt` | the PyPI record of the Python-side candidates, dated 2026-11-21 (fail-closed on a network error) |

Setup (one interpreter per engine, because `google-re2` and `pyre2` both install the module `re2`): a venv each for `google-re2`, `pyre2` and `regex` (with `pyyaml`); the env of `selection_probe.py` names them: `CIC_ENGINE_PY_re`, `_nfa` (the system python), `_regex`, `_re2g`, `_re2p`, and `CIC_PROBE_GO`, `CIC_PROBE_CARGO` (Docker stand-ins are fine), `CIC_PROBE_REQUIRE=1`.
Run: `selection_probe.py results`, `closure_probe.py results/closure.txt`, `selftest_harness.py python3`, `red_initial_f2_f3.py`, `supply_chain.py`.

## Not shown

Other engine versions and platforms (only Linux x86_64 wheels were run); the RE2 version bundled in the wheels; fuzz beyond 15000 cases and the small alphabet; an independent expectation for the generated cases; one run on one machine (the times are indicative); the real-workload total is derived from per-value times.
