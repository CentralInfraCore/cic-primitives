# Evidence: the inventory of the 2026-12-31 chain expiry (2026-11-23)

For `docs/en/T3-EXPIRY-RISK-ASSESSMENT-AND-DECISION-PLAN.md`. **A read-only inventory and its check: no key is used, nothing is signed, stamped, renewed or published.**

| File | What it does |
|---|---|
| `inventory.py` | reads fresh clones (default branch, depth 1) of `cic-schema-registry`, `cic-primitives`, `CIC_Relay`, `base-repo`, `cic-yang`, fetches the release tags it lists (read-only), and records: the chain certificates, the countersigned records of the registry with every certificate they carry, the signature blocks at the release tags, the **boundary of each record class** (earliest certificate end and declared validity; UNKNOWN where not extractable), and the lines of the three verifiers that carry the time behaviour. **Every scope element has a typed status** (`ok`, `absent`, `not_found`, `fetch_error`, `parse_error`); exit 0 complete, 1 incomplete, 2 an unreadable input |
| `results/inventory.json` | the recorded inventory (clone heads: registry `3d493d591b86`, primitives `411ce8070445`, Relay `b1b4345e2c3a`, base-repo `71db9d354857`, cic-yang `b5e58d544285`; as of 2026-11-23) |
| `check_inventory.py`, `results/check_inventory.txt` | the inventory is COMPLETE (every scope element ok or absent; the complete flag follows from the statuses; the registry files that mention the blocks are all accounted for; every tag record, anchor and certificate has its scope element); the chain equals the kept certificates; the class states follow from the boundaries; the claims about the three verifiers rest on the recorded anchors; the five tables of the document equal the tables rendered from the data, and the boundary table answers NO for every class whose boundary has passed. Exit 0 ok, 1 a FAIL-EXPECT line, 2 infrastructure |
| `selftest_inventory.py`, `results/selftest-inventory-output.txt` | the tool and the check can fail, for the right reason: a positive control and isolated faults on fixture repositories (a tag that cannot be fetched, a tag that does not exist, an unparsable record file listed by path, an absent `project.yaml`, a `project.yaml` without a block, an unreadable certificate kept as UNKNOWN, a missing clone), the check on the package, 20 planted faults in the inventory, the document and the manifest, an infrastructure control: 32 checks. The old behaviour (a failed fetch read as absent, a parse error swallowed) was measured to fail these tests |
| `SHA256SUMS` | the hashes of these files and the document |

Run (from this directory): `python3 inventory.py --clones <dir with the clones> --out results/inventory.json` (needs the clones and network for the tag fetch), `python3 check_inventory.py > results/check_inventory.txt`, `python3 selftest_inventory.py > results/selftest-inventory-output.txt`. Python 3 with PyYAML, and `openssl`.

## Not shown

The behaviour of the verifiers (the check proves the anchors, the behaviour is read from the code; the primitives verifier was measured with a fixed clock in the T3 work); the verification of commit signatures; the Relay deployment's use of the chain; revocation; repositories that were not cloned; the terms of any time-stamp authority.
