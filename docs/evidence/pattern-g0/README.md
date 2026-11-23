# Evidence: the owner's decisions and the G-0 check of the pattern profile (P1), 2026-11-23

For `docs/en/GRAMMAR-PATTERN-OWNER-DECISIONS.md`. **A decision record and an isolated check: documentation and tooling only; it closes no gate, creates no normative extension and is not permission to implement.** Data: `docs/design/pattern-profile-plan/decisions.yaml` (the decisions D1 to D8 and OP-1 to OP-4 as recorded from the owner's statement of 2026-11-23, with source, date, verbatim table and the files they are bound to by SHA-256). The approved vector file (SHA-256 `e7ece43a...`) is untouched.

| File | What it does |
|---|---|
| `check_g0.py`, `results/check_g0.txt` | evaluates the prerequisites that gate G-0 of the plan names (D1 to D6, OP-1, OP-2) and nothing later (OP-3 closes at G-6, OP-4 at G-4); keeps the decision, the evidence and the closure apart; verdicts INVALID, NOT_READY, READY_FOR_OWNER_CLOSURE, CLOSED; exit 0 only for the last two, 1 otherwise (FAIL-EXPECT lines), 2 an unreadable input. **The recorded result today is NOT_READY for one reason: the specification text that fixes OP-1 does not exist** |
| `selftest_g0.py`, `results/selftest-g0-output.txt` | the check can fail, for the right reason: the real state, two positive controls in a temporary root with a FIXTURE of the OP-1 text, 24 planted faults (missing decision, contradiction, a record that disagrees with the owner's statement, missing provenance, a wrong SHA-256, a changed bound file, an unmet prerequisite, a changed OP-1 text, OP-2 normative, a wrong count, a case that depends on a decision on hold, OP-3 closing at G-0, a plan that demands a later open point, closure faults and more), an infrastructure control (exit 2): 29 checks |
| `SHA256SUMS` | the hashes of the files of this evidence, the record and the document |

Run (from this directory): `python3 check_g0.py > results/check_g0.txt` (exit 1 today, by design), `python3 selftest_g0.py > results/selftest-g0-output.txt`. Python 3 with PyYAML.

## Not shown

The authenticity of the owner's statement (a transcribed statement, not signed); the correctness of the decisions; the specification text of OP-1 (missing); a normative extension (none exists); the closure of G-0 (a separate owner decision).
