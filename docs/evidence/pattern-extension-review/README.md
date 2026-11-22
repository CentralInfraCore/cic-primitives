# Evidence: the review package of the 47 proposed extension cases (P1), 2026-11-22

For `docs/en/GRAMMAR-PATTERN-EXTENSION-CASES-REVIEW.md`. **A review package: documentation and isolated tooling only; no case is added to the approved vector file** (513 vectors, SHA-256 `e7ece43a...`, held by the check). Data: `docs/design/pattern-profile-spec/extension-cases.yaml` (the 47 cases, from #52) and `docs/design/pattern-profile-spec/extension-review.yaml` (per case: the derivation from the text, the rule, the decisions D1 to D6 it depends on, the status).

| File | What it does |
|---|---|
| `check_extension_review.py`, `results/check_extension_review.txt` | the approved vector file is byte-identical to the approved one; every case has exactly one review entry and vice versa; every derivation is present and names a known obligation or a section; the dependencies stay inside D1 to D6 and inside the group's set (no case depends on D7 or D8); every requirement a case names exists in the approved set; the executable reading (`../pattern-spec-trace/spec_model.py`) gives the expected result of every case; the case table, the decision table and the group table of the document equal what the data renders (`--render` prints the table); exit 0 ok, 1 a FAIL-EXPECT line, 2 an input is unreadable |
| `selftest_extension_review.py`, `results/selftest-extension-review-output.txt` | the check can fail, for the right reason: a positive control, 11 planted faults in copies of the data, the cases, the document and the approved vector file, 1 planted defect of the executable reading, an infrastructure control (exit 2): 14 checks |

Run (from this directory): `python3 check_extension_review.py > results/check_extension_review.txt`, `python3 selftest_extension_review.py > results/selftest-extension-review-output.txt`. The check imports `../pattern-spec-trace/spec_model.py` (and through it the prototype of `pattern-limits-errors/`); nothing is installed or changed.

## Not shown

A third, independent derivation of the expected results (the derivations and the executable reading are by the author of the specification); an implementation; the owner's confirmation of D1 to D6; the decision whether the extension keeps its own format.
