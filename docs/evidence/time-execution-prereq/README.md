# Evidence: the readiness check of the T3 time-stamping (2026-11-23)

For `docs/en/T3-EXECUTION-PREREQUISITES.md`. **A record and a check: nothing is performed, no time stamp requested, and the check can never give the GO.** Data: `docs/design/time-evidence/t3-execution-prerequisites.yaml` (five decisions, all `proposed`; 22 conditions; `execution_go: null`).

| File | What it does |
|---|---|
| `check_t3_readiness.py`, `results/check_t3_readiness.txt` | keeps the decisions (proposed, confirmed only with an owner confirmation), the conditions (open, or verified WITH evidence the check reads: an existing repository file that contains a stated text) and the GO (never recorded in the file) apart; the dates are ordered (target < internal latest < the chain boundary of the inventory); the dry-run manifest holds exactly the open records of the inventory; the tables and counts of the document equal the record. Verdicts INVALID, NOT_READY, READY_FOR_OWNER_GO; exit 0 only for the last. **Today: NOT_READY and valid** |
| `selftest_t3_readiness.py`, `results/selftest-t3-readiness-output.txt` | the check can fail, for the right reason: the real record, the real record with the document, a complete fixture package (READY_FOR_OWNER_GO and still no GO), two valid NOT_READY cases, 21 planted faults in the record, 4 in the document, an infrastructure control: 31 checks; three mutations (a confirmation not required, the evidence text not read, a GO recordable) are measured to fail it |
| `SHA256SUMS` | the hashes of these files, the record and the document |

Run (from this directory): `python3 check_t3_readiness.py --doc ../../en/T3-EXECUTION-PREREQUISITES.md > results/check_t3_readiness.txt` (exit 1 today, by design), `python3 selftest_t3_readiness.py > results/selftest-t3-readiness-output.txt`. Python 3 with PyYAML.

## Not shown

That any condition is true in the world (a verified condition is as strong as the evidence file it names); any provider's terms, access or trust chain; the owner's confirmation of any decision.
