# Evidence: the P7 decision is recorded consistently (2026-11-21)

Owner decision P7: option B. Final reason `integer_out_of_range`; range -(2^53-1) .. +(2^53-1) inclusive; checked by the producer and, independently, by the verifier; whole value tree, opaque contents included; profile H unchanged. **Normative decision and declaration only; no implementation.**

| File | What it shows |
|---|---|
| `declaration.diff` | the change of `contract-conformance.yaml` (G02 names both reasons and states the independence; the new requirement P02 is the producer side, `planned`) |
| `declaration-check.txt` | `check_declaration.py` against the probe output: CONSISTENT; 38 known reasons, all owned |
| `selftest-declaration.txt` | `selftest_declaration.py`: 63 of 63 checks as expected; 20 new planted defects, each refused with its own reason: 7 for the decision (the producer executor removed, the verifier executor removed, the type reason removed, the independence statement removed, a wrong owner, the producer check downgraded to not_implemented, the verifier executor handed to the producer) 7 for review #45 F1 and 6 for F1.1 (G02 moved to the other section, with and without a decoy, the independence and the 2^53 statements still checked after the move, G02 not_implemented, P02 moved to the other section). The F1 cases carry a `needle`: the self-test requires the refusal to name THIS requirement, not another problem |
| `red-initial-f1-against-43f3b70.txt` | the F1 cases run against the **previous** `check_declaration.py` (head `43f3b705`): the three P02 cases with a decoy producer entry are ACCEPTED (the gap the review named: another entry hides the damaged P02); the G02 cases were refused only by other layers, not by a check bound to G02 (UNEXPECTED because the needle is absent). 52 of 57 as expected before, 57 of 57 after |
| `red-initial-f1.1-against-b669496.txt` | the F1.1 cases run against the **previous** head `b669496`: moving G02 to `further_requirements` is ACCEPTED, also with the reason stripped, the independence statement removed or the 2^53 statement weakened (the section-dependent checks were skipped, the review's bypass); P02 moved to `global_requirements` is ACCEPTED; the G02 not_implemented case was refused only by another layer. 57 of 63 as expected before, 63 of 63 after |
| `untouched-paths-diffstat.txt` | empty: nothing changed under `tools/` (the reference verifier), `tests/`, `release/` (the historical records), `proposals/` (the grammar), `schemas/`, `.github/`, `Makefile`, `project.yaml` (the publication list), the schema parts and `compose.py` |
| `SHA256SUMS` | the current digests of the three design files this change edits |

The digests in `docs/evidence/release-schema-draft-probe/SHA256SUMS` record the state of #38; for `contract-conformance.yaml`, `check_declaration.py` and `selftest_declaration.py` they are **superseded** by this change on purpose (the schema parts, `composition.yaml` and `compose.py` are unchanged and still match).

## Not shown

No implementation: the reference verifier does not make the profile A checks, the producer does not refuse, no vector exists, and the reason is not in the published contract table (the verifier does not emit it yet). Profile H is untouched by construction (nothing under `tools/` changed), not by a test of profile A, which does not exist yet.
