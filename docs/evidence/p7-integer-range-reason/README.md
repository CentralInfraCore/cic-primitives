# Evidence: P7, the reason for an integer beyond 2^53 - 1 (decision preparation)

For `docs/en/RELEASE-P7-INTEGER-RANGE-REASON.md`. Measurement only; no tool or plan is changed.

| File | What it shows |
|---|---|
| `reason-usage.txt` | `value_type_unsupported` occurs in no file of `tools/` or `tests/` and nowhere in the CIC_Relay worktree; the docs that name it |
| `scan_integers.py`, `scan-output.txt` | every integer in the four tagged release records (`primitives/@v0.1.4`, `@v0.1.5`, `@v0.2.0`, `@v0.2.1`), `tests/fixtures` and the release-schema probe records (38 files): the largest is the envelope number 3; none is beyond 2^53 - 1 (the last line: 0). Lines with no integer are filtered out |
| `pyyaml_reading.py`, `pyyaml-reading-output.txt` | PyYAML reads integers up to 2^64 exactly (the reader that the reference verifier uses) |
| (cited, not repeated) | `docs/evidence/forms-capability-measurement/{rust,go}-output.txt`, case K06: the Forms accept up to int64 and refuse beyond int64 at parse |

Run: `python3 scan_integers.py` from the repository root with PyYAML and the tags present; `python3 pyyaml_reading.py`.
