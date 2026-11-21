# Evidence: choosing the linear-time evaluator of the pattern profile (P1, O5), 2026-11-21

For `docs/en/GRAMMAR-PATTERN-ENGINE-SELECTION.md`. **Measurement and prototypes only: no grammar, checker, Forms or verifier is changed.** It builds on `docs/evidence/grammar-pattern-measurement/` (the closed-subset classifier `subset_check.py`, the Go and Rust drivers, the corpora of `probe_engines.py`).

| File | What it shows |
|---|---|
| `nfa_engine.py` | candidate D: a Thompson NFA for the closed subset only (191 lines, no dependency); parses only what `subset_check.parse` accepted |
| `engines.py`, `runner_py.py` | one adapter interface for `re`, `regex`, `re2g` (google-re2), `re2p` (pyre2, fallback OFF), `nfa`, and the child-process runner (verdicts; bench) |
| `fuzz_gen.py` | the seeded generator of in-subset patterns and inputs |
| `selection_probe.py`, `probe-run-output.txt`, `results/{parity,timing,bench,constructs}.txt` | the four groups: 141 hand-authored + 1500 generated patterns (15000 fuzz cases) on 7 engines; 53 timing cases; 18 compile/match/memory cases (one process per engine and case); the 84 constructs per engine, including pyre2 with its default fallback. Fail-closed: a missing interpreter or toolchain, a failed canary or an incomplete runner is exit 1 |
| `bench/go`, `bench/rust` | the bench runners (compile best of 5, match median of 7, peak memory above the start via `/proc/self/clear_refs`) |
| `selftest_harness.py`, `selftest-harness-output.txt` | the parity gate can fail: 8 planted defects (also the same defect in 2 and 3 engines at once), each run with and without the canaries: 8/8 detected both ways |
| `supply_chain.py`, `supply-chain-output.txt` | the PyPI record of the Python-side candidates, dated 2026-11-21 (fail-closed on a network error) |

Setup (one interpreter per engine, because `google-re2` and `pyre2` both install the module `re2`): a venv each for `google-re2`, `pyre2` and `regex` (with `pyyaml`); the env of `selection_probe.py` names them: `CIC_ENGINE_PY_re`, `_nfa` (the system python), `_regex`, `_re2g`, `_re2p`, and `CIC_PROBE_GO`, `CIC_PROBE_CARGO` (Docker stand-ins are fine), `CIC_PROBE_REQUIRE=1`.
Run: `selection_probe.py results`, `selftest_harness.py python3`, `supply_chain.py`.

## Not shown

Other engine versions and platforms (only Linux x86_64 wheels were run); the RE2 version bundled in the wheels; fuzz beyond 15000 cases and the small alphabet; one run on one machine (the times are indicative); the real-workload total is derived from per-value times.
