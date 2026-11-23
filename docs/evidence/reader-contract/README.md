# Evidence: the draft reader contract (OP-1), 2026-11-23

For `docs/en/GRAMMAR-PATTERN-READER-CONTRACT-DRAFT.md`. **A DRAFT specification, its draft test vectors and an isolated check: documentation and tooling only; nothing is accepted, published or implemented, and no gate is closed.** Data: `docs/design/pattern-profile-reader/reader-contract.yaml` (19 rules with their basis, the closed set of reader error kinds, 12 open questions) and `reader-vectors.yaml` (270 draft vectors). The approved vector file (SHA-256 `e7ece43a...`) and the 47 accepted extension cases are untouched.

| File | What it does |
|---|---|
| `reference_reader.py` | an executable reading of the RULES (not the implementation, not a conformant YAML 1.2 parser): it takes only the syntax (the event stream) from PyYAML and decides the typing, the tags, the key identity and the error order itself; `CIC_READER_PLANT` plants a defect for the self-test only |
| `check_reader_contract.py`, `results/check_reader_contract.txt` | the rule ids, error kinds and the coverage of the rules by vectors; the vectors are well-formed; the reference reading gives the expected result of all 270 vectors (0 differences); the 47 accepted extension cases agree with the contract at the reader level; the tables of the document equal the tables rendered from the data. Exit 0 ok, 1 a FAIL-EXPECT line, 2 infrastructure |
| `selftest_reader_contract.py`, `results/selftest-reader-contract-output.txt` | the check can fail, for the right reason: a positive control, 8 planted defects of the reference reading (each caught by the vectors that state the rule), 25 planted faults in the data and the document (including the decision table: a claimed effect the alternative does not have, an omitted one, a claim without a switchable alternative), an infrastructure control (exit 2): 35 checks |
| `measure_pyyaml.py`, `results/pyyaml-measurement.json` | AFTER the contract: where `yaml.safe_load` differs from the draft vectors (a measurement, not a source; the numbers depend on the PyYAML version, recorded) |
| `reference_reader.py` `CIC_READER_ALT` | switches ONE open question to its alternative answer, so that `check_reader_contract.py` COMPUTES which vectors the alternative would change and compares it with what each question claims |
| `SHA256SUMS` | the hashes of these files, the data and the document |

Run (from this directory): `python3 measure_pyyaml.py`, `python3 check_reader_contract.py > results/check_reader_contract.txt`, `python3 selftest_reader_contract.py > results/selftest-reader-contract-output.txt`. Python 3 with PyYAML.

## Not shown

That the rules are right (the author wrote the rules, the vectors and the reference reading; the independence test is the review and, later, an implementation by another author); the limits of the reader (OQ-3: no number is fixed); a conformance verdict on any parser; a full YAML 1.2 syntax conformance; the schema layer's errors.
