# Evidence: the readiness check of the T3 time-stamping (2026-11-23)

For `docs/en/T3-EXECUTION-PREREQUISITES.md`. **A record and a check: nothing is performed, no time stamp requested, and the check can never give the GO.** Data: `docs/design/time-evidence/t3-execution-prerequisites.yaml` (six decisions, all `proposed`; 26 conditions in three phases; `execution_go: null`).

| File | What it does |
|---|---|
| `check_t3_readiness.py`, `results/check_t3_readiness.txt` | the STATE MACHINE (NOT_PREPARED, PREPARED_FOR_OWNER_GO, GO_RECORDED, EVIDENCE_CAPTURED, PRESERVATION_COMPLETE; none is an authorisation): decisions (proposed, or a RECORDED, NOT authenticated owner statement), conditions in phases (pre, capture, preserve; a later phase can be verified only after a valid separate GO record, and the preserve phase only after the capture), the preservation order (staged or strict) moving the strict conditions into the pre phase, the GO record bound to the prepared state by a digest, the dates ordered (target < internal latest < the chain boundary), the dry-run manifest equal to the inventory's EXPECTED SET of records identifier by identifier with commit and ref, the tables and counts of the document equal the record. Exit 0 for PREPARED_FOR_OWNER_GO or later, 1 for NOT_PREPARED or INVALID. **Today: NOT_PREPARED and valid** |
| `selftest_t3_readiness.py`, `results/selftest-t3-readiness-output.txt` | the check can fail, for the right reason: the real record, the whole state machine in both orders, valid NOT_PREPARED cases, 41 planted faults in the record, the GO record and the manifest set (a swapped record with the count unchanged, a missing, an extra, a wrong-commit record), 4 in the document, an infrastructure control: 58 checks; four mutations (later-phase evidence without a GO, missing records not reported, the GO digest unchecked, the order without effect) are measured to fail it |
| `SHA256SUMS` | the hashes of these files, the record and the document |

Run (from this directory): `python3 check_t3_readiness.py --doc ../../en/T3-EXECUTION-PREREQUISITES.md > results/check_t3_readiness.txt` (exit 1 today, by design), `python3 selftest_t3_readiness.py > results/selftest-t3-readiness-output.txt`. Python 3 with PyYAML.

## Not shown

That any condition is true in the world (a verified condition is as strong as the evidence file it names); any provider's terms, access or trust chain; the owner's confirmation of any decision.
