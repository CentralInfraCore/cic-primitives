# Evidence: the implementation specification of the pattern profile (P1), 2026-11-22

For `docs/en/GRAMMAR-PATTERN-IMPLEMENTATION-SPEC.md`. **A draft specification: documentation and isolated tooling only, not permission to implement.** The approved vector file (513 vectors, SHA-256 `e7ece43a...`) is untouched and is the unchanged reference. Companions in `docs/design/pattern-profile-spec/`: `obligations.yaml` (26 obligations, 11 plan items, the traceability) and `extension-cases.yaml` (40 PROPOSED cases, not part of the approved set).

| File | What it does |
|---|---|
| `spec_model.py` | an executable reading of the NEW rules: pin resolution by exact type with the recursive type-sensitive identity of declared values, the document-order traversal of nested contracts, the reader/validator boundary, the validation order, the delivery digest and the content digest; it delegates the classification of an expression to the existing prototype (`pattern_codes.classify`); not an implementation |
| `check_spec_trace.py`, `results/check_spec_trace.txt` | the approved vector file is byte-identical to the approved one; every one of the 66 requirements and the 4 that a verdict vector cannot test is named by an obligation; structure and coverage rules; the text mentions every obligation and plan id; each requirement of an obligation is covered by what it cites (vectors, or a cited plan item that lists it) and the text and the contract agree (must-contain phrases); the accept/refuse class is invariant under every permutation of the delivery order and the delivery digest tells two orders apart; the 40 extension cases agree with the model; the model reproduces the 20 schema vectors of the approved set; prints the requirement-to-obligation and plan-to-obligation matrices; exit 0 ok, 1 a FAIL-EXPECT line, 2 an input is unreadable |
| `work_bound.py`, `results/work_bound.txt` | the deterministic work bound W <= c x (PI+1) x (N+1) on 95 pairs including 27 with PI = 0 or N = 0; the first form c x PI x N is refuted by measurement |
| `selftest_spec_trace.py`, `results/selftest-spec-trace-output.txt` | the tooling can fail, for the right reason: a positive control, 14 planted faults in copies of the package, 6 planted defects of the model, 4 checks of the work bound, an infrastructure control (exit 2): 26 checks |

Run (from this directory): `python3 check_spec_trace.py > results/check_spec_trace.txt`, `python3 work_bound.py > results/work_bound.txt`, `python3 selftest_spec_trace.py > results/selftest-spec-trace-output.txt`. The check imports `docs/evidence/pattern-vectors/vectors_lib.py` and the prototype of `pattern-limits-errors/`; nothing is installed or changed.

## Not shown

An implementation of any role; a third independent implementation; the timing, independence, evidence and budget plans as tests; the composition of schema parts; whether the source-order traversal is the order the owner wants.
