# Evidence: the pattern profile (P1), measurement and prototypes (2026-11-21)

For `docs/en/GRAMMAR-PATTERN-PROFILE-DESIGN.md`. **Measurement and prototypes only: no grammar, checker, Forms or verifier is changed.** Engines: Python 3.14.4 `re`, Go 1.26.11 `regexp`, Rust `regex` 1.13.2 (`runners/rust/Cargo.lock`).

| File | What it shows |
|---|---|
| `subset_check.py` | the candidate closed subset as a classifier (a prototype of the design, not production code) |
| `selftest_subset.py`, `selftest_subset-output.txt` | 111 vectors: what the classifier accepts and what it refuses, each refusal with its reason |
| `selftest_subset_mutants.py`, `selftest_subset_mutants-output.txt` | the vectors can fail: 16 planted classifier defects DETECTED; a 17th (an anchor in the middle) MASKED because the atom rule already refuses it (stated, not claimed) |
| `inventory.py`, `inventory-output.txt` | every `pattern` contract and JSON Schema `pattern` key of the measured trees (cic-primitives, the release schema drafts, cic-schema-registry at `6db77d4d`) with the classifier's verdict. Fail-closed (an unreadable file, a missing root or nothing found is exit 1) |
| `probe_engines.py`, `runners/go`, `runners/rust`, `probe-run-output.txt`, `results/probe-*.txt` | the 3 engines on 4 groups: **semantic** (9 contracts x 13 inputs = 117, independent expectation; all engines agree with it), **constructs** (84; 28 diverge, all outside the subset; the 24 in the subset agree), **limits** (38 compile-limit cases), **timing** (46, including the bounded-repeat cases of review F1; Python in killable child processes, one run, indicative). Exit 1 if an in-subset case disagrees with its expectation or a group is incomplete. A missing toolchain is an error with `CIC_PROBE_REQUIRE=1` |
| `gate_selftest.py`, `gate-selftest-output.txt` | the probe can fail: Python with `$` instead of `\Z` (10 cases flagged), and the SAME defect planted in BOTH the Go and the Rust runner (always `match`: 97 flagged; always `nomatch`: 20; the wrapper dropped: 93): 4 of 4 DETECTED |
| `compat_records.py`, `compat-records-output.txt`, `compat-records-selftest-output.txt` | on the real records (`v0.2.1`, the golden record, the probe base record): 127 pattern-constrained values, 0 with a line feed, 0 over 256 code points, 0 verdicts change between the legacy (`re.search`) and the WHOLE candidate profile (subset + 256 code points + full match). Fail-closed (a mandatory pattern node without a value, an expression outside the subset or too few values: exit 1); the self-test shows it sees a change (a trailing LF, an over-long value) and refuses an incomplete run |
| `compat_records_mutants.py`, `compat-records-mutants-output.txt` | the self-test can fail: 6 planted defects (limit, subset check, three refusals, the missing-node count), 6 DETECTED |

Run (repository root; PyYAML, Docker or local Go and Cargo): `inventory.py <label>=<root> ...`, `selftest_subset.py`, `CIC_PROBE_GO=... CIC_PROBE_CARGO=... probe_engines.py results`, `gate_selftest.py <python>`, `compat_records.py .`.

## Not shown

Other engine versions; strings that are not valid Unicode scalar values; the running times beyond one indicative run; that the candidate limits are optimal; any behavior of the Forms or a verifier (none evaluates a schema pattern today).
