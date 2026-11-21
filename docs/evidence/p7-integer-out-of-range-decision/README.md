# Evidence: the P7 decision is recorded consistently (2026-11-21)

Owner decision P7: option B. Final reason `integer_out_of_range`; range -(2^53-1) .. +(2^53-1) inclusive; checked by the producer and, independently, by the verifier; whole value tree, opaque contents included; profile H unchanged. **Normative decision and declaration only; no implementation.**

| File | What it shows |
|---|---|
| `declaration.diff` | the change of `contract-conformance.yaml` (G02 names both reasons and states the independence; the new requirement P02 is the producer side, `planned`) |
| `declaration-check.txt` | `check_declaration.py` against the probe output: CONSISTENT; 38 known reasons, all owned |
| `selftest-declaration.txt` | `selftest_declaration.py`: 50 of 50 checks as expected; 7 new planted defects (the producer executor removed, the verifier executor removed, the type reason removed, the independence statement removed, a wrong owner, the producer check downgraded to not_implemented, the verifier executor handed to the producer), each refused with its own reason |
| `untouched-paths-diffstat.txt` | empty: nothing changed under `tools/` (the reference verifier), `tests/`, `release/` (the historical records), `proposals/` (the grammar), `schemas/`, `.github/`, `Makefile`, `project.yaml` (the publication list), the schema parts and `compose.py` |
| `SHA256SUMS` | the current digests of the three design files this change edits |

The digests in `docs/evidence/release-schema-draft-probe/SHA256SUMS` record the state of #38; for `contract-conformance.yaml`, `check_declaration.py` and `selftest_declaration.py` they are **superseded** by this change on purpose (the schema parts, `composition.yaml` and `compose.py` are unchanged and still match).

## Not shown

No implementation: the reference verifier does not make the profile A checks, the producer does not refuse, no vector exists, and the reason is not in the published contract table (the verifier does not emit it yet). Profile H is untouched by construction (nothing under `tools/` changed), not by a test of profile A, which does not exist yet.
