# Evidence: P7, the reason for an integer beyond 2^53 - 1 (decision preparation)

For `docs/en/RELEASE-P7-INTEGER-RANGE-REASON.md`. Measurement only; no tool or plan is changed.

| File | What it shows |
|---|---|
| `reason-usage.txt` | `value_type_unsupported` occurs in no file of `tools/` or `tests/` and nowhere in the CIC_Relay worktree; the docs that name it |
| `scan_integers.py`, `scan-output.txt` | **fail-closed** scan (exit 0 complete and no finding, 1 incomplete, 3 finding) of every integer in the four required tagged release records (`primitives/@v0.1.4`, `@v0.1.5`, `@v0.2.0`, `@v0.2.1`; all release records of those tags are printed), `tests/fixtures` and the release-schema probe records (38 files): the largest integer is the envelope number 3; none is beyond 2^53 - 1; the last line states `required records processed: 4 of 4` and 0 findings. Fixture lines with no integer are left out |
| `scan-selftest-output.txt` | `scan_integers.py --self-test`: 12 planted cases in a throw-away repository (a missing tag, an absent, empty, non-YAML or bare-scalar record, no fixture, an unreadable fixture, an incomplete scan hidden behind a finding, a finding at +2^53 and at -2^53, and the bound itself as no finding) |
| `selftest_mutants.py`, `scan-selftest-mutants-output.txt` | the self-test can fail: the reviewed defect (a git or read error counted as zero) and the other planted defects are DETECTED; a single completeness layer removed alone is reported MASKED where another layer still refuses (defense in depth, stated, not claimed as detected) |
| `pyyaml_reading.py`, `pyyaml-reading-output.txt` | PyYAML reads integers up to 2^64 exactly (the reader that the reference verifier uses) |
| (cited, not repeated) | `docs/evidence/forms-capability-measurement/{rust,go}-output.txt`, case K06: the Forms accept up to int64 and refuse beyond int64 at parse |

Run from the repository root with PyYAML and the tags present: `python3 scan_integers.py` (and `--self-test`), `python3 selftest_mutants.py python3`, `python3 pyyaml_reading.py`.
