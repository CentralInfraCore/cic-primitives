# Evidence: resource limits (O2) and error codes (O3) of the pattern profile (P1, PR2), 2026-11-22

For `docs/en/GRAMMAR-PATTERN-LIMITS-AND-ERRORS.md`. **Measurement and prototypes only: no grammar, checker, schema, Forms or verifier is changed.** It builds on `docs/evidence/grammar-pattern-measurement/` (the classifier `subset_check.py`, the corpora of `probe_engines.py`) and on `docs/evidence/pattern-engine-selection/` (the own evaluator `nfa_engine.py`, the Go and Rust runners).

| File | What it shows |
|---|---|
| `limit_space.py`, `results/limit_space.txt` | groups `boundary` (each candidate limit at its edge), `contracts` (program size of the 9 existing contracts), `space` (the largest NFA program the candidate limits admit, by DP, then built), `size` (PI + 1 equals the NFA state count), `search` (an independent random search, a weak cross-check), `worksearch` (the slowest accepted expression for caps on PI, by state visits and time), `cost` (compile, match and memory against the program size) |
| `engines_at_limit.py`, `results/engines_at_limit.txt` | the own evaluator, Go and Rust on the boundary expressions, the slow expression and the DP optimum; rule D (an accepted expression must compile everywhere) is a hard check for PI <= 2048; typed exits: 0 ok, 1 a measured failure, 2 infrastructure (a toolchain missing), 3 a failed canary |
| `pattern_codes.py` | the O3 reference prototype: the mapping from the classifier's refusals to the proposed codes, the three tiers, the PI rule, the value-time order. The environment variable `CIC_CODES_PLANT` switches on a planted defect for the self-test only |
| `codes_probe.py`, `results/codes_probe.txt` | precedence (32 hand-authored cases), the PI boundary, the value order, totality and coverage over 30 154 texts, determinism over four hash seeds; exit 0 ok, 1 a measured expectation failed, 2 the probe could not run (never a detection) |
| `selftest_codes.py`, `results/selftest-codes-output.txt` | the probe can fail for the right reason: an unmodified positive control, 7 planted defects (each counted only with a `FAIL-EXPECT` line of the intended check), 2 infrastructure controls that must exit 2 |

Run (from this directory; Go and Rust through the env of the engine-selection evidence: `CIC_PROBE_GO`, `CIC_PROBE_CARGO`, `CIC_PROBE_REQUIRE=1`): `python3 limit_space.py > results/limit_space.txt`, `python3 engines_at_limit.py > results/engines_at_limit.txt`, `python3 codes_probe.py > results/codes_probe.txt`, `python3 selftest_codes.py > results/selftest-codes-output.txt`. The probes import `probe_engines.py`, which reads `argv[1]` as an output directory at import; the new scripts give it a scratch directory that is removed again.

## Not shown

The true worst-case match time under a size cap (the searches are lower bounds and noisy); an independent check of the DP beyond the family it searches; the RE2 wheels and other engine versions; warm or repeated Go and Rust timings; the pin errors and the document-order rule (the prototype reads no schema); one run on one machine.
