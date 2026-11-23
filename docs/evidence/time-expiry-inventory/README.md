# Evidence: the inventory of the 2026-12-31 chain expiry (2026-11-23)

For `docs/en/T3-EXPIRY-RISK-ASSESSMENT-AND-DECISION-PLAN.md`. **A read-only inventory and its check: no key is used, nothing is signed, stamped, renewed or published.**

| File | What it does |
|---|---|
| `inventory.py` | reads fresh clones (default branch, depth 1) of `cic-schema-registry`, `cic-primitives`, `CIC_Relay`, `base-repo`, `cic-yang`, fetches the release tags it lists (read-only), and records: the chain certificates, the countersigned records of the registry, the signature blocks at the release tags, and the lines of the three verifiers that carry the time behaviour. Output `results/inventory.json` records the clone commits: the inventory is about THOSE commits. Exit 0, or 2 for an unreadable input |
| `results/inventory.json` | the recorded inventory (clone heads: registry `3d493d591b86`, primitives `411ce8070445`, Relay `b1b4345e2c3a`, base-repo `71db9d354857`, cic-yang `b5e58d544285`) |
| `check_inventory.py`, `results/check_inventory.txt` | the chain of the inventory equals the kept certificates (openssl reads them again); the registry records name the kept Source CA; the manifest's stamped releases are tags of the inventory; the claims about the three verifiers rest on the recorded anchors (the registry verifier has 0 lines with a time word and 0 naming `ts`; the Relay verification builds `x509.VerifyOptions` without `CurrentTime`; the primitives verifier reads the clock); the three tables of the document equal the tables rendered from the data. Exit 0 ok, 1 a FAIL-EXPECT line, 2 infrastructure |
| `selftest_inventory.py`, `results/selftest-inventory-output.txt` | the check can fail, for the right reason: a positive control, 12 planted faults (three hand-edited tables, a changed inventory, a changed certificate date, a registry record of another Source CA, four changed verifier anchors, a manifest stamp without a tag, a document without markers), an infrastructure control (exit 2): 14 checks |
| `SHA256SUMS` | the hashes of these files and the document |

Run (from this directory): `python3 inventory.py --clones <dir with the clones> --out results/inventory.json` (needs the clones and network for the tag fetch), `python3 check_inventory.py > results/check_inventory.txt`, `python3 selftest_inventory.py > results/selftest-inventory-output.txt`. Python 3 with PyYAML, and `openssl`.

## Not shown

The behaviour of the verifiers (the check proves the anchors, the behaviour is read from the code; the primitives verifier was measured with a fixed clock in the T3 work); the verification of commit signatures; the Relay deployment's use of the chain; revocation; repositories that were not cloned; the terms of any time-stamp authority.
