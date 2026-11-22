# Evidence: the normative vector set of the pattern profile (P1, PR3), 2026-11-22

For `docs/en/GRAMMAR-PATTERN-VECTORS.md`. The vectors: `docs/design/pattern-profile-vectors/pattern-profile.yaml`. **Isolated tooling only: no CI gate, no implementation, no grammar, checker, schema, Forms or verifier change.** It builds on `docs/evidence/pattern-limits-errors/` (the prototype and the implementation of the rule text) and on `docs/evidence/pattern-engine-selection/` and `grammar-pattern-measurement/` (the Go and Rust runners and their canaries).

| File | What it does |
|---|---|
| `vectors_lib.py` | reads the vector file and decodes `{seq: [...]}`; imports no implementation |
| `check_vectors.py`, `results/check_vectors.txt` | structure and coverage (unique ids, known requirements and codes, the encoding, a PI on accepted expressions, every requirement and code covered, every limit with an accepting and a refusing vector), the position `at` of a schema refusal (required for an expression refusal, forbidden for a pin refusal), the declared metadata against the accepted decisions (the seven limits, the code sets, the profile name) and against the vectors' own boundaries, and the printed requirement-to-vector matrix; exit 0 ok, 1 a FAIL-EXPECT line, 2 the file cannot be read |
| `conform.py`, `results/conform.txt` | the conformance run: P (the prototype: expressions, PI, values, and the schema rule written there from the text), S (the implementation of the rule text), G and R (Go `regexp` and Rust `regex`: value verdicts and "an accepted expression compiles"); `--no-native` skips G and R; `--legacy` runs the legacy reading (Python `re.search`) as a RED-initial; the whole schema triple (verdict, code, position) is compared and the declared limits are compared with the implementation's constants (`CIC_CONFORM_PLANT` plants a defect of the schema rule for the self-test). Exit 0 all agree, 1 a DISAGREE line, 2 infrastructure, 3 a failed canary |
| `results/red-initial-legacy.txt` | the legacy reading disagrees on 28 of 204 match/mismatch vectors, among them every trailing-line-feed vector |
| `selftest_vectors.py`, `results/selftest-vectors-output.txt` | the tooling can fail, for the right reason: positive controls, 19 planted faults in a copy of the vector file, 12 planted defects in the implementations, 2 vector files with a wrong position or declared limit, 2 in a copy of the Go runner (one caught by the runner's canary, one only by the vectors), 3 infrastructure controls that must exit 2: 40 checks |

Run (from this directory; Go and Rust through the env of the engine-selection evidence: `CIC_PROBE_GO`, `CIC_PROBE_CARGO`, `CIC_PROBE_REQUIRE=1`): `python3 check_vectors.py > results/check_vectors.txt`, `python3 conform.py > results/conform.txt`, `python3 conform.py --legacy --no-native > results/red-initial-legacy.txt`, `python3 selftest_vectors.py > results/selftest-vectors-output.txt`. `CIC_VECTORS` points the tools at another vector file (the self-test uses it).

## Not shown

A third implementation by another author in another language from the text and the vectors only; the timing requirement; warmed or repeated native timings; the pin version number (a working assumption of the vectors); one run on one machine.
