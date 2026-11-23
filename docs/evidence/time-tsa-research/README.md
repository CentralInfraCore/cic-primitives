# T3 TSA research evidence

For `docs/en/T3-TSA-PROVIDER-RESEARCH.md`. **Read-only research: nothing here contacts a time-stamp authority, requests a token, uses a key or an account.**

| File | What it is |
|---|---|
| `check_tsa_research.py`, `results/check_tsa_research.txt` | derives each C-Q2-* condition from the findings (supported only if all findings support, one is decisive and from a primary source), re-verifies the DigiCert chain with OpenSSL against the pinned anchor, and checks the readiness record never marks a C-Q2-* condition verified without research support |
| `selftest_tsa_research.py`, `results/selftest-tsa-research-output.txt` | 17 checks: the real record valid, planted faults with the intended label (FAIL-EXPECT), a corrupted responder, a swapped anchor (measured: a chain check alone passes it on OpenSSL 3.5), infrastructure exit 2 |
| `digicert/` | the five certificates the DigiCert page links (the `.cer` root there is the CROSS-SIGNED root, not the anchor) |
| `SHA256SUMS` | digests of the files above |

Data: `docs/design/time-evidence/t3-tsa-research.yaml`. Run: `python3 check_tsa_research.py` (exit 0 valid, 1 detection, 2 infrastructure).
