# The signing-chain expiry of 2026-12-31: what it touches, what stays verifiable, and the options (a risk assessment and a decision plan)

**A read-only assessment and a decision plan: documentation and an isolated inventory tool only.** It uses **no production key**, makes **no signature, no time stamp, no certificate change, no release and no publication**, and it **selects nothing**: the options of section 6 are for the owner to decide. It does not change any approved file or the CI. Written 2026-11-23, **38 calendar days before** the first certificate of the chain ends. Base: `devel` at `530066e0b06442f0f5d5857494d17e98f9d4a1a3`. Inventory data: `docs/evidence/time-expiry-inventory/results/inventory.json`, checked by `check_inventory.py`.

It builds on the existing T3 work and does not repeat it: the three RFC 3161 stamps of 2026-11-03 (`evidence/time/digicert-2026-11-03/`), the storage and restore plan, the storage decision proposal and the B2 preflight (`docs/en/T3-*.md`). What is new here is the **inventory of everything else the expiry touches** and the **options for the part that is still uncovered**.

## 1. The question, in one paragraph

The signing chain of the CIC records ends in 2026: the Source CA at 13:22:39 UTC, the Developer CA seven seconds later, the developer certificate at 13:22:59 and the Root at 23:59:59 on 2026-12-31. The signatures themselves do not become mathematically wrong (the keys do not change). What changes is **what a verifier can conclude**: a verifier that judges certificate validity at the moment of checking refuses every record from 2027-01-01, and a record that carries no **independent** evidence of when it existed cannot be shown to have been made while the chain was valid. A stamp obtained after the chain has ended proves only a date after it. The time to create that evidence is **before** 2026-12-31 13:22:39 UTC.

## 2. The chain and its ends

<!-- BEGIN CHAIN TABLE -->
| Certificate | Subject | Not after (UTC) | SHA-256 fingerprint |
|---|---|---|---|
| `developer-ca.pem` | CIC Developer CA | Dec 31 13:22:46 2026 GMT | `D3:59:D1:47:8F:E9:15:89:FA:02:B7:8A:EC:E3:98:37:DC:0D:60:27:24:B2:6E:0F:4E:4F:86:4B:40:76:F6:6A` |
| `developer.pem` | Gabor Zoltan Sinko | Dec 31 13:22:59 2026 GMT | `5E:F7:39:DC:91:CF:87:6D:3E:E9:29:DB:94:60:6A:60:A5:80:46:D7:C6:0C:25:EC:93:10:70:83:E9:28:93:03` |
| `root.pem` | CIC Root CA | Dec 31 23:59:59 2026 GMT | `7A:87:3A:BB:99:D7:20:D9:77:96:B4:A9:82:30:C4:3A:31:99:3B:7E:67:E3:30:2B:B5:7F:AE:9C:4F:5F:D1:A3` |
| `source-ca.pem` | CIC Source CA | Dec 31 13:22:39 2026 GMT | `27:2B:B9:73:EA:68:4C:C0:00:D6:DF:3E:77:21:25:2C:3C:48:85:BF:93:4E:9A:57:C5:CF:D0:E1:BE:C8:BC:20` |
<!-- END CHAIN TABLE -->

The earliest end is the Source CA (13:22:39 UTC), so **that** is the deadline for any evidence that must lie inside all four windows. Two further certificates of the same names and issuer exist in the local CA directory with an end in March 2031 (different keys from the 2026 ones, for the Source CA and the Developer CA; the same Root). They are **not** what the records carry, and a chain ends where its earliest certificate ends: the Root that issued them ends on 2026-12-31, so they do not extend anything. The Platform CA and the License CA of the 2026 generation also end on 2026-12-31 (13:22:55 and 13:22:51); they were read from the local CA directory, which is **not** in the repository, and no record of the inventory carries them. **Already ended:** the 2025 Root (2026-08-06) and the developer certificate of `base@0.5.0` (2026-10-05): the oldest records are already refused by a verifier that reads the clock.

## 3. What is signed, and what time evidence exists

<!-- BEGIN RECORDS TABLE -->
| Class | Records | External time evidence (RFC 3161) | Note |
|---|---|---|---|
| cic-schema-registry (main @ `3d493d591b86`), countersigned records | 90 | **none** | countersign `ts` 2026-09-06T19:31:23Z to 2026-09-28T22:00:31Z (the countersigning service's own clock, not covered by any signature); 90 distinct build hashes |
| primitives release record (cic-primitives) | 3 | **3 of 3** (DigiCert, 2026-11-03) | tags `primitives/@v0.1.5`, `primitives/@v0.2.0`, `primitives/@v0.2.1` |
| cic-yang release record (cic-yang) | 2 | **none** | tags `yang/@v0.1.2`, `yang/@v0.1.3` |
| template release `base@0.5.0` | 1 | none | signature block under project.yaml; build timestamp 2025-10-18T20:04:37.092582+00:00; declared validity until none declared; developer certificate end: Oct  5 20:23:22 2026 GMT |
| template release `base@0.6.0` | 1 | none | signature block under project.yaml; build timestamp 2025-12-08T17:09:32.315677+00:00; declared validity until 2026-12-08T17:09:32.315693+00:00; developer certificate end: not extracted by the inventory |
| template release `golang@0.6.0` | 1 | none | signature block under project.yaml; build timestamp 2025-12-08T17:09:32.315677+00:00; declared validity until 2026-12-08T17:09:32.315693+00:00; developer certificate end: not extracted by the inventory |
| template release `schema-registry@0.1.0` | 1 | none | signature block under project.yaml; build timestamp TBD; declared validity until TBD; developer certificate end: not extracted by the inventory |
| template release `schemas@v0.9.0` | 1 | none | no signature block found by the inventory |
<!-- END RECORDS TABLE -->

* **The countersign `ts` is not evidence of time.** The countersignature is over the `build_hash` (`signed_payload: build_hash`); the `ts` next to it is written by the countersigning service from its own clock and is **covered by no signature** (the registry verifier checks `signed_payload`, and the file has no line that names `ts`, section 4). Anyone who can edit the file can change it without breaking a signature.
* **The git history and GitHub carry times too**, but they are claims of the committer or of the platform: a commit date is set by the committer; GitHub's push, merge and workflow-run times are the platform's assertion, retrievable only while the platform and the account exist, and not a token that can be checked offline. They are corroboration, not proof that a third party can verify without GitHub.
* **What does exist as proof:** three DigiCert RFC 3161 tokens over the records of `primitives/@v0.1.5`, `v0.2.0`, `v0.2.1` (2026-11-03 22:07 to 22:09 UTC), verifiable offline at the token's own time, inside all four certificate windows. **Everything else in the table has none.**
* The 10 records under `CIC_Relay/docs/evidence/forms-fit-probe/docs/` and the `TEST ONLY` golden record of the primitives tests are **fixtures**, not releases, and are not counted.

## 4. The verifiers: what the expiry does to each

<!-- BEGIN VERIFIER TABLE -->
| Verifier | Reads the clock? | Evidence (recorded anchor lines at the pinned commit) |
|---|---|---|
| `cic-primitives` `tools/compiler.py` | **yes**, the validity of the certificate and of the root is judged at the moment of checking | `now = datetime.now(UTC)` at lines 364, 415, 578; `expired`/`not valid` refusals at lines 374, 424 (commit `411ce8070445`) |
| `cic-schema-registry` `tools/registrylib/verify.py` | **no**: the file has 0 lines with a time word (`not_valid`, `not_before`, `not_after`, `datetime`, `expire`); the chain is checked by signature only, against the root **embedded in the record** (lines 17, 24, 54, 160) | `signed_payload` is `build_hash` (lines 20, 254, 256) and the file has 0 lines naming `ts`: the countersign `ts` is neither signed nor checked (commit `3d493d591b86`) |
| `CIC_Relay` `core/cabinet/pki_verify.go` | **yes** (by default): `x509.VerifyOptions{` at line 155 with 0 lines naming `CurrentTime`, so Go checks the chain at the current time | commit `b1b4345e2c3a` |
<!-- END VERIFIER TABLE -->

* **After the Source CA ends**, the primitives verifier and the Relay chain verification refuse the chain: the first, for every record (measured earlier with a fixed clock, see the T3 work) and for any **new** signature as well, because the signing certificate is no longer valid; the second wherever it is given a certificate under this Root (this is read from the code and **not measured**; whether a Relay deployment uses this chain today is outside this inventory).
* **The registry verifier is not affected**, because it does not look at validity at all. That is not a strength: it also accepts a certificate that has already ended, and it checks the chain against the **Root embedded in the record itself**, not against a pinned anchor. After the expiry the registry records will "verify" exactly as before, and for the same reason they would verify if the certificate had ended long ago.
* No verifier checks revocation in the inventory's scope (the T3 work found none).

## 5. What stays verifiable after the expiry

| Claim | Without further evidence | With the stamps of 2026-11-03 | With the options below |
|---|---|---|---|
| The signature over `build_hash` is mathematically valid | yes, for ever (the keys do not change) | yes | yes |
| The record's bytes are those that were signed | yes | yes | yes |
| The registry verifier accepts the record | yes (it ignores validity) | yes | yes |
| The primitives verifier or the Relay chain check accepts the record | **no** from 2026-12-31 13:22:39 UTC | no (the verifiers have no "as of" mode) | only with an "as of" mode (option E) or a renewed chain used for verification (option B) |
| The record existed no later than a stated time, by a third party | **no** | yes, for the 3 stamped primitives releases; **no** for the other 92 records and the 5 template releases | yes, for the records stamped in time (option A) |
| The chain was valid when the record existed | no | yes for the 3 (the stamp time lies inside all four windows; no revocation information exists) | yes for the stamped ones |
| The signer was authorised to sign, the release is genuine | not shown by any of this | not shown | not shown (a separate question, see the T3 work) |

## 6. The options (none is selected here)

| Option | What it gives | What it needs and trusts | What it does **not** give | Time-critical? |
|---|---|---|---|---|
| **A. RFC 3161 stamps for the records that have none**, preferably one stamp over a signed or hashed manifest of the record digests (and the release tags and commits that matter), from **at least two independent time-stamp authorities** | the evidence that the records existed no later than the stamp time, checkable offline by anyone with the tokens and the anchors | the authority and its root (the public DigiCert endpoint's terms of use were **not found**; a second authority needs its own terms check); the custody of the tokens (the second-copy decision S3/S10 is still open); a verifier or a written procedure that validates "as of" the stamp time | that the signer was authorised; revocation; anything after the stamp | **yes: before 2026-12-31 13:22:39 UTC.** A stamp made in 2027 proves only 2027 |
| **B. Chain renewal** (re-issue the CA and developer certificates, with the same keys or new ones; a new Root if the Root is renewed) | a chain that verifiers which read the clock accept again; the **only** way to sign **new** records after 2026-12-31 | the use of the Root key and of the Developer and Source CA keys (**production key use, on hold**); a way for a verifier to find the renewed certificate for a key that an old record embeds (or re-countersigning the old records, which creates new signatures) | **evidence about the past**: with B alone a record is "valid now" and still cannot be shown to have existed in 2026 | the renewal for new signing is needed from 2027-01-01; it does not replace A |
| **C. A public append-only transparency log** (inclusion proofs and signed tree heads) | time evidence that does not depend on the CA's validity window, with a public audit trail | a log operator and witnesses to trust; a tool and a verifier that checks inclusion; the records are public already (no confidentiality cost) | the signer's authority; a log entry is not a stamp that is checkable without the log's keys and consistency checks | no hard date, but the entry must exist before the claim is needed |
| **D. The countersign service signs `{build_hash, ts}`** for **new** records (the "E1" of the trust plan) | a `ts` that is under a signature | a change of the countersign service and of every verifier | the past records; **and** the service's own clock is still the only source of the time: D alone does not make the time independent | no; useful together with A for new records |
| **E. An "as of" mode of the verifiers** (validate the chain at the time of a stamp, not at the moment of checking) | the use of A or C by a machine; the primitives verifier and the Relay check could accept the stamped records after the expiry | the implementation (**on hold**) and its review; the rule of which time is accepted | without A or C there is no time to be "as of" | the mode is not needed before 2027-01-01, the evidence is |

**Reading of the table.** A is the only option that is **time-critical and cheap to start**: it needs no production key, no change of any verifier, and it creates the one thing that cannot be made later. B is needed for forward operation and cannot repair the past. E turns A into something a machine can use. C is a supplement. D fixes a weakness of new records. The options are not exclusive; the choice of the owner is how many of them and in which order.

## 7. A proposal, and the decision points for the owner

**Proposal (not a decision):** decide the scope of A and the authorities this week, perform A well before the deadline (the proposal: finished by **2026-12-15**, 16 days of margin), design E and the renewal B as separate work items, and use D for new records from the next release. The preservation of the tokens stays the existing storage plan (still **not backed up**).

| # | Decision | Why it is the owner's |
|---|---|---|
| Q1 | The **scope** of A: the 90 registry records, the 2 yang records, the template releases (which of them), the release tags and commits, in one manifest or per record | it fixes what the claim after the expiry can cover; the template releases carry their own validity (`2026-12-08`, earlier than the chain) and some already-ended certificates |
| Q2 | The **time-stamp authorities**: keep DigiCert's public endpoint (terms not found) and add a second one; or choose authorities with stated terms | a stamp is an outward act with a third party; the terms and the trust roots are a decision |
| Q3 | The **last safe date** for A (proposal 2026-12-15) and who performs it | a stamp can be made once; the margin is for failures |
| Q4 | The **"as of" verification**: only a written procedure (`verify.sh`) or also the verifiers (E) | E is an implementation and on hold |
| Q5 | **Forward signing** after 2026-12-31 (B): same keys or new, renew the Root or roll over | it needs production key use and is a different risk from the past evidence |
| Q6 | **Custody** of the new tokens and the manifest | the S3/S10 decisions are open; nothing is backed up |
| Q7 | Whether **D** (a signed `ts`) is a requirement for the next release | it changes the countersign service and every verifier |

## 8. What this does not show

* The inventory is a statement about **the commits it records** (`inventory.json`, `clones`), taken from fresh clones on 2026-11-23; the repositories move.
* **Not examined:** the verification of commit signatures (the commit-msg hook's Vault signature) and any verifier of them; the Forms and the engine receipts; the Relay deployment's use of the chain; Vault key custody and the Root key store; revocation and OCSP; GitHub Actions attestations; the countersign service's own clock source; the records of repositories that were not cloned (archived and private ones).
* The template releases (`base@0.5.0`, `0.6.0`, `golang@0.6.0`, `schema-registry@0.1.0`, `schemas@v0.9.0`) are listed by what the inventory could read; their certificates were not all extracted, and `schemas@v0.9.0` had no signature block the inventory recognises.
* The statements about the Relay and primitives verifiers are **read from the code** at the recorded lines (the primitives behaviour was measured with a fixed clock in the T3 work); the check proves the anchors, not the behaviour.
* The two options A and C depend on third parties whose terms and long-term behaviour this document did not verify.
* This is a plan and a set of options. **No time stamp was requested, no key was used, nothing was signed, uploaded, renewed or published.**
