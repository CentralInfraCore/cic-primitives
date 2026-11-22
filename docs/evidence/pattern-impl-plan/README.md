# Evidence: the implementation plan of the pattern profile (P1), 2026-11-22

For `docs/en/GRAMMAR-PATTERN-IMPLEMENTATION-PLAN.md`. **A plan: documentation and isolated tooling only; not an implementation and not permission to implement; no module named in the plan exists.** The approved vector file (513 vectors, SHA-256 `e7ece43a...`) is untouched and is the unchanged reference. Data: `docs/design/pattern-profile-plan/plan.yaml` (10 units, 14 gates, 7 milestones, 4 open points), built on `docs/design/pattern-profile-spec/obligations.yaml` (27 obligations).

| File | What it does |
|---|---|
| `check_impl_plan.py`, `results/check_impl_plan.txt` | the approved vector file is byte-identical and the counts 513, 47 and 560 equal the files; all 27 obligations are assigned to a unit; every unit has tests and its tests actually cover each requirement of its obligations (an approved vector kind with a vector naming it, an extension group whose cases name it, or a plan item that lists it); the milestone, unit and gate order (the owner's decisions G-0 before the first milestone with units, steps 1 to 7 in order); the hold flags of M3 to M6 and of G-11 to G-13; every plan item P-01 to P-11 is in a gate; the document mentions every id; prints the obligation-to-unit and milestone matrices; exit 0 ok, 1 a FAIL-EXPECT line, 2 an input is unreadable |
| `selftest_impl_plan.py`, `results/selftest-impl-plan-output.txt` | the check can fail, for the right reason: a positive control, 16 planted faults in copies of the plan, the document and the approved vector file, an infrastructure control (exit 2): 18 checks |

Run (from this directory): `python3 check_impl_plan.py > results/check_impl_plan.txt`, `python3 selftest_impl_plan.py > results/selftest-impl-plan-output.txt`.

## Not shown

An implementation of any unit; that the tests, once written, give full semantic coverage; the owner's confirmation of D1 to D6 and the decision on the open points OP-1 to OP-4; the independent implementation.
