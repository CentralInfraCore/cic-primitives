# The signing-chain expiry of 2026-12-31: what it touches, what stays verifiable, and the options (a risk assessment and a decision plan)

**A read-only assessment and a decision plan: documentation and an isolated inventory tool only.** It uses **no production key**, makes **no signature, no time stamp, no certificate change, no release and no publication**, and it **selects nothing**: the options of section 7 are for the owner to decide. It does not change any approved file or the CI. Written 2026-11-23 and revised after review (findings T3-F1 and T3-F2), **38 calendar days before** the first certificate of the main chain ends. Base: `devel` at `530066e0b06442f0f5d5857494d17e98f9d4a1a3`. Inventory data: `docs/evidence/time-expiry-inventory/results/inventory.json`, checked by `check_inventory.py`.

It builds on the existing T3 work and does not repeat it: the three RFC 3161 stamps of 2026-11-03 (`evidence/time/digicert-2026-11-03/`), the storage and restore plan, the storage decision proposal and the B2 preflight (`docs/en/T3-*.md`). What is new here is the **inventory of everything else the expiry touches** and the **options for the part that is still uncovered**.

## 1. The question, in one paragraph

The signing chain of the CIC records ends in 2026. The signatures themselves do not become mathematically wrong (the keys do not change). What changes is **what a verifier can conclude**: a verifier that judges certificate validity at the moment of checking refuses a record whose chain has ended, and a record that carries no **independent** evidence of when it existed cannot be shown to have been made while its chain was valid. **A stamp obtained after a record's boundary proves only a date after that boundary, and it cannot be made to prove more.** Different record classes have **different boundaries**: this document keeps them apart and never applies the main chain's date to a class whose own date is earlier, later or unknown.

## 2. The main chain and its ends

<!-- BEGIN CHAIN TABLE -->
| Certificate | Subject | Not after (UTC) | SHA-256 fingerprint |
|---|---|---|---|
| `developer-ca.pem` | CIC Developer CA | 2026-12-31T13:22:46Z | `D3:59:D1:47:8F:E9:15:89:FA:02:B7:8A:EC:E3:98:37:DC:0D:60:27:24:B2:6E:0F:4E:4F:86:4B:40:76:F6:6A` |
| `developer.pem` | Gabor Zoltan Sinko | 2026-12-31T13:22:59Z | `5E:F7:39:DC:91:CF:87:6D:3E:E9:29:DB:94:60:6A:60:A5:80:46:D7:C6:0C:25:EC:93:10:70:83:E9:28:93:03` |
| `root.pem` | CIC Root CA | 2026-12-31T23:59:59Z | `7A:87:3A:BB:99:D7:20:D9:77:96:B4:A9:82:30:C4:3A:31:99:3B:7E:67:E3:30:2B:B5:7F:AE:9C:4F:5F:D1:A3` |
| `source-ca.pem` | CIC Source CA | 2026-12-31T13:22:39Z | `27:2B:B9:73:EA:68:4C:C0:00:D6:DF:3E:77:21:25:2C:3C:48:85:BF:93:4E:9A:57:C5:CF:D0:E1:BE:C8:BC:20` |
<!-- END CHAIN TABLE -->

The earliest end of the **main chain** is the Source CA (13:22:39 UTC, the Developer CA seven seconds later, the developer certificate at :59, the Root at 23:59:59). Two further certificates of the same names and issuer exist in the local CA directory with an end in March 2031 (different keys from the 2026 ones, for the Source CA and the Developer CA; the same Root); they are **not** what the records carry, and a chain ends where its earliest certificate ends: the Root that issued them ends on 2026-12-31, so they extend nothing. The Platform CA and the License CA of the 2026 generation also end on 2026-12-31 (13:22:55 and 13:22:51); they were read from the local CA directory, which is **not** in the repository, and no record of the inventory carries them.

## 3. The boundaries, class by class (review T3-F1)

Each class has its **own proved boundary**: the earliest end among the certificates the records themselves carry, and the validity the record declares for itself. Where a boundary could not be extracted the class says **UNKNOWN**; nothing is filled in from the main chain.

<!-- BEGIN BOUNDARIES TABLE -->
| Class | Records | Earliest proved certificate end | Declared record validity | State at 2026-11-23T16:14:41Z | Can a stamp made now still show existence before the boundary? |
|---|---|---|---|---|---|
| cic-schema-registry countersigned records | 90 | 2026-12-31T13:22:39Z (authority: CIC Source CA) | none declared | **open** | yes, only if the stamp is made before the boundary |
| cic-primitives release records (the tags' own records) | 3 | 2026-12-31T13:22:39Z (authority: CIC Source CA) | none declared | **open** | yes, only if the stamp is made before the boundary |
| cic-yang release records (the tags' own records) | 2 | 2026-12-31T13:22:39Z (authority: CIC Source CA) | none declared | **open** | yes, only if the stamp is made before the boundary |
| template release base@0.5.0 | 1 | 2026-10-05T20:23:22Z (cert) | none declared | **ended** | **NO**: the boundary has passed; a stamp made now shows only that the record existed no later than the stamp, not that it existed or was valid before the boundary |
| template release base@0.6.0 | 1 | 2026-08-06T06:05:02Z (cicSignedCA.certificate) | 2026-12-08T17:09:32Z | **ended** | **NO**: the boundary has passed; a stamp made now shows only that the record existed no later than the stamp, not that it existed or was valid before the boundary |
| template release golang@0.6.0 | 1 | 2026-08-06T06:05:02Z (cicSignedCA.certificate) | 2026-12-08T17:09:32Z | **ended** | **NO**: the boundary has passed; a stamp made now shows only that the record existed no later than the stamp, not that it existed or was valid before the boundary |
| template release schema-registry@0.1.0 | 1 | none extracted | none declared | **UNKNOWN** | **UNKNOWN**: no boundary could be extracted |
<!-- END BOUNDARIES TABLE -->

* **92 records are still open** (the 90 countersigned records of the registry and the 2 yang release records): their boundary is the main chain's, 2026-12-31 13:22:39 UTC, and **none of them has external time evidence**. This is the time-critical set.
* **Three template releases have already ended** (`base@0.5.0`, `base@0.6.0`, `golang@0.6.0`): their certificates ended on 2026-10-05 (the developer certificate) and, for the two `0.6.0` releases, the Root they carry ended on **2026-08-06**, before the record's own declared validity ends (2026-12-08) and before this document was written. **No time stamp can repair these**: it can show only that the record existed no later than the stamp. They are a **separate risk category**: the decision about them is not "stamp them in time" but whether to retire them, re-sign them with a renewed chain, or accept that they cannot be shown valid at any time.
* **One template release has an UNKNOWN boundary** (`schema-registry@0.1.0` carries a placeholder: no certificate, a validity of `TBD`), and `schemas@v0.9.0` has no signature block at all (explicitly `absent`, not a failure).
* **The three primitives releases are open and stamped** (section 4).

## 4. What is signed, and what time evidence exists

<!-- BEGIN EVIDENCE TABLE -->
| Class | Records | RFC 3161 time evidence of the record's existence | Evidence that the chain was valid at an earlier time | Note |
|---|---|---|---|---|
| cic-schema-registry countersigned records (main @ `3d493d591b86`) | 90 | **none** | **none** | countersign `ts` 2026-09-06T19:31:23Z to 2026-09-28T22:00:31Z: the countersigning service's own clock, covered by no signature; 90 distinct build hashes |
| cic-primitives release records (the tags' own records) | 3 | **3 of 3** (DigiCert, 2026-11-03) | for the 3 stamped: the stamp time lies inside all four windows of the kept chain; no revocation information exists | tags `primitives/@v0.1.5`, `primitives/@v0.2.0`, `primitives/@v0.2.1` |
| cic-yang release records (the tags' own records) | 2 | **none** | **none** | tags `yang/@v0.1.2`, `yang/@v0.1.3` |
| template releases (base-repo `project.yaml`) | 4 with a signature block | **none** | **none** | `base@0.5.0` boundary 2026-10-05T20:23:22Z; `base@0.6.0` boundary 2026-08-06T06:05:02Z; `golang@0.6.0` boundary 2026-08-06T06:05:02Z; `schema-registry@0.1.0` boundary UNKNOWN |
<!-- END EVIDENCE TABLE -->

* **The countersign `ts` is not evidence of time.** The countersignature is over the `build_hash` (`signed_payload: build_hash`); the `ts` next to it is written by the countersigning service from its own clock and is **covered by no signature** (the registry verifier checks `signed_payload`, and the file has no line that names `ts`, section 5). Anyone who can edit the file can change it without breaking a signature.
* **Two different things must not be mixed:** the **existence** of a record at a time (an RFC 3161 token over its digest shows that it existed no later than the token's time) and **the validity of its chain at an earlier time** (that needs the stamp time to lie inside every certificate's window, plus information about revocation, which does not exist in any verifier of the inventory). The first column of the table is the first, the second column the second; for the 3 stamped releases the stamp time lies inside all four windows of the kept chain.
* **The git history and GitHub carry times too**, but they are claims of the committer or of the platform: GitHub's push, merge and workflow-run times are the platform's assertion, retrievable only while the platform and the account exist, not a token that can be checked offline. They are corroboration, not proof.
* The 10 records under `CIC_Relay/docs/evidence/forms-fit-probe/docs/` and the `TEST ONLY` golden record of the primitives tests are **fixtures**, not releases, and are not counted.

## 5. The verifiers: what the expiry does to each

<!-- BEGIN VERIFIERS TABLE -->
| Verifier | Reads the clock? | Evidence (recorded anchor lines at the pinned commit) |
|---|---|---|
| `cic-primitives` `tools/compiler.py` | **yes**, the validity of the certificate and of the root is judged at the moment of checking | `now = datetime.now(UTC)` at lines 364, 415, 578; `expired`/`not valid` refusals at lines 374, 424 (commit `411ce8070445`) |
| `cic-schema-registry` `tools/registrylib/verify.py` | **no**: the file has 0 lines with a time word (`not_valid`, `not_before`, `not_after`, `datetime`, `expire`); the chain is checked by signature only, against the root **embedded in the record** (lines 17, 24, 54, 160) | `signed_payload` is `build_hash` (lines 20, 254, 256) and the file has 0 lines naming `ts`: the countersign `ts` is neither signed nor checked (commit `3d493d591b86`) |
| `CIC_Relay` `core/cabinet/pki_verify.go` | **yes** (by default): `x509.VerifyOptions{` at line 155 with 0 lines naming `CurrentTime`, so Go checks the chain at the current time | commit `b1b4345e2c3a` |
<!-- END VERIFIERS TABLE -->

* **After a chain has ended**, the primitives verifier and the Relay chain verification refuse it: the first, for every record (measured earlier with a fixed clock, see the T3 work) and for any **new** signature as well, because the signing certificate is no longer valid; the second wherever it is given a certificate under that chain (read from the code and **not measured**; whether a Relay deployment uses this chain today is outside this inventory).
* **The registry verifier is not affected**, because it does not look at validity at all. That is not a strength: it also accepts a certificate that has already ended, and it checks the chain against the **Root embedded in the record itself**, not against a pinned anchor.
* No verifier checks revocation in the inventory's scope (the T3 work found none).

## 6. What stays verifiable after the expiry, and how the inventory is known to be complete

| Claim | Without further evidence | With the stamps of 2026-11-03 | With the options below |
|---|---|---|---|
| The signature over `build_hash` is mathematically valid | yes, for ever (the keys do not change) | yes | yes |
| The record's bytes are those that were signed | yes | yes | yes |
| The registry verifier accepts the record | yes (it ignores validity) | yes | yes |
| The primitives verifier or the Relay chain check accepts the record | **no** after its chain ends | no (the verifiers have no "as of" mode) | only with an "as of" mode (option E) or a renewed chain used for verification (option B) |
| The record existed no later than a stated time, by a third party | **no** | yes, for the 3 stamped primitives releases; **no** for the other classes | yes, for the records stamped **before their boundary** (option A) |
| The record existed or was valid **before a boundary that has already passed** | **no** | no | **no, by no option here** (the 3 ended template releases) |
| The chain was valid when the record existed | no | yes for the 3 stamped (no revocation information exists) | yes for those stamped in time |
| The signer was authorised to sign, the release is genuine | not shown by any of this | not shown | not shown (a separate question, see the T3 work) |

**Completeness of the inventory (review T3-F2).** Every element of the declared scope has a **typed status**, and the inventory is complete only if none is an error:

<!-- BEGIN SCOPE TABLE -->
| Scope element kind | Elements | Statuses |
|---|---|---|
| chain-certificate | 4 | ok 4 |
| registry-record-scan | 1 | ok 1 |
| release-tag | 10 | absent 1, ok 9 |
| verifier-anchor | 8 | ok 8 |
| **complete** | 23 | **yes** (every element `ok` or `absent`) |
| `absent`: tag:base-repo:schemas@v0.9.0 | 1 | no signed record file and no project.yaml at the tag |
| registry files that mention the signature blocks | 114 | 90 records, 0 parse errors, 24 not a record; 30 top-level entries not scanned (outside the record areas) |
<!-- END SCOPE TABLE -->

The statuses are `ok` (read and understood), `absent` (looked for, explicitly not there: a result), and the errors `not_found` (a tag the scope names is not in the remote), `fetch_error` (a tag could not be fetched: **never mixed with `absent`**), `parse_error` (a file that mentions the signature blocks could not be parsed: **listed by path, never skipped**) and `read_error` (git itself failed to read the tag's content: `git grep` with an exit code other than 0 (a match) or 1 (no match), a failing `git show` or `git ls-tree`: **never read as "no match" or as "absent"**; a `project.yaml` is `absent` only when `git ls-tree` says it is not in the tree). A fact that could not be extracted is `unknown` and reaches the tables as **UNKNOWN**, not as another date. `check_inventory.py` fails if any element is an error, if the `complete` flag does not follow from the statuses, and if the registry files that mention the signature blocks are not all accounted for (**114 files mention them: 90 records, 0 parse errors, 24 that are not records**); `inventory.py` exits 1 when it produced an incomplete inventory. The self-test plants an unfetchable tag, a tag that does not exist, an unparsable record file, a missing `project.yaml`, a `git grep` that fails, a `git show` that fails for a record file while `git grep` works, and a `git show` that fails for a `project.yaml` that is in the tree, each in a fixture repository by one invalid git setting, and each is caught for its own reason. **Not covered:** a failing `git ls-tree` on its own (every setting that breaks it breaks `git grep` first, which is caught earlier).

**The clock (review F2b).** The state of a class is judged at the **full UTC instant** of the inventory (`as_of`, recorded to the second), never at a day: a boundary is the last second a certificate is valid, so a class is `ended` only when the instant is **after** it. The self-test runs the registry class at boundary minus one second (`open`), at the boundary second itself (`open`), at boundary plus one second (`ended`) and at 14:00 UTC on 2026-12-31 (`ended`, the case a day-granularity clock called `open`), and refuses a day-only `--as-of`; the check recomputes every class's state from its boundary and the instant.

## 7. The options (none is selected here)

| Option | What it gives | What it needs and trusts | What it does **not** give | Time-critical? |
|---|---|---|---|---|
| **A. RFC 3161 stamps for the open records that have none**, preferably one stamp over a signed or hashed manifest of the record digests (and the release tags and commits that matter), from **at least two independent time-stamp authorities** | the evidence that the records existed no later than the stamp time, checkable offline by anyone with the tokens and the anchors | the authority and its root (the public DigiCert endpoint's terms of use were **not found**; a second authority needs its own terms check); the custody of the tokens (the second-copy decision S3/S10 is still open); a verifier or a written procedure that validates "as of" the stamp time | that the signer was authorised; revocation; **anything about a boundary that has already passed**; anything after the stamp | **yes: before the class's boundary** (for the 92 open records, 2026-12-31 13:22:39 UTC). A stamp made in 2027 proves only 2027 |
| **B. Chain renewal** (re-issue the CA and developer certificates, with the same keys or new ones; a new Root if the Root is renewed) | a chain that verifiers which read the clock accept again; the **only** way to sign **new** records after the main chain ends | the use of the Root key and of the Developer and Source CA keys (**production key use, on hold**); a way for a verifier to find the renewed certificate for a key that an old record embeds (or re-countersigning the old records, which creates new signatures) | **evidence about the past**: with B alone a record is "valid now" and still cannot be shown to have existed in 2026 | needed from the day the main chain ends; it does not replace A |
| **C. A public append-only transparency log** (inclusion proofs and signed tree heads) | time evidence that does not depend on the CA's validity window, with a public audit trail | a log operator and witnesses to trust; a tool and a verifier that checks inclusion; the records are public already | the signer's authority; a boundary that has passed | no hard date, but the entry must exist before the claim is needed |
| **D. The countersign service signs `{build_hash, ts}`** for **new** records (the "E1" of the trust plan) | a `ts` that is under a signature | a change of the countersign service and of every verifier | the past records; the service's own clock is still the only source of the time | no; useful together with A for new records |
| **E. An "as of" mode of the verifiers** (validate the chain at the time of a stamp, not at the moment of checking) | the use of A or C by a machine | the implementation (**on hold**) and its review; the rule of which time is accepted | without A or C there is no time to be "as of" | the mode is not needed before the chain ends, the evidence is |

**Reading of the table.** A is the only option that is **time-critical and cheap to start**: it needs no production key, no change of any verifier, and it creates the one thing that cannot be made later, **for the classes whose boundary is still ahead**. For the classes whose boundary has passed, **no option creates that evidence**: only B (re-signing under a renewed chain) or retirement changes their position, and neither makes them valid in the past.

## 8. A proposal, and the decision points for the owner

**Review recommendations of 2026-11-23 (recommendations, not owner decisions).** Q1a: keep each of the 92 open records in one canonical, complete **record-digest manifest** with separate record identifiers and repo, commit and tag references; the manifest holds the digest of the **exact record bytes**, not only the `build_hash` field, so that a later check can reproduce which records were in the proved set. Q1b: handle the three ended template releases and the UNKNOWN `schema-registry@0.1.0` separately; the original gap in evidence is **not** treated as repaired; their further use is a separate decision. Q2: two **independent** RFC 3161 authorities with verified terms of use and trust anchors; the DigiCert experience may be used but does not replace checking its terms; both stamps tied to the **same canonical digest**. Q3: execution within a week of the decision, an internal latest date of 2026-12-15; the cryptographic boundary is 2026-12-31 13:22:39 UTC and **must not be what the schedule is built on**. Q6 (custody of the tokens, the certificates and the manifest) has to be settled **before** the stamping is performed.

**Proposal (not a decision):** **do not wait until December.** Decide the scope of A and the authorities as soon as possible, perform A within a week of the decision, and treat **2026-12-15** only as the **latest** acceptable date (16 days of margin before the main chain's first end), not as the target. Design E and the renewal B as separate work items, and use D for new records from the next release. The classes whose boundary has passed are decided separately (Q1b). The preservation of the tokens stays the existing storage plan (still **not backed up**).

| # | Decision | Why it is the owner's |
|---|---|---|
| Q1a | The **scope** of A: the 92 open records (90 registry records and 2 yang releases), in one manifest or per record, with the release tags and commits that matter | it fixes what the claim after the expiry can cover; the three primitives releases are already stamped |
| Q1b | What to do with the **classes whose boundary has passed** (`base@0.5.0`, `base@0.6.0`, `golang@0.6.0`) and with the **UNKNOWN** one (`schema-registry@0.1.0`): retire, re-sign under a renewed chain, or accept as ended; and what to extract to settle the UNKNOWN | **no stamp can show their existence or validity before their boundary**; claiming otherwise would be false |
| Q2 | The **time-stamp authorities**: keep DigiCert's public endpoint (terms not found) and add a second one; or choose authorities with stated terms | a stamp is an outward act with a third party |
| Q3 | The **last acceptable date** per class (for the 92: before 2026-12-31 13:22:39 UTC; the proposal is 2026-12-15 at the latest, and in practice within a week of the decision) and who performs it | a stamp can be made once; the margin is for failures |
| Q4 | The **"as of" verification**: only a written procedure (`verify.sh`) or also the verifiers (E) | E is an implementation and on hold |
| Q5 | **Forward signing** after the main chain ends (B): same keys or new, renew the Root or roll over | it needs production key use and is a different risk from the past evidence |
| Q6 | **Custody** of the new tokens and the manifest | the S3/S10 decisions are open; nothing is backed up |
| Q7 | Whether **D** (a signed `ts`) is a requirement for the next release | it changes the countersign service and every verifier |

## 9. What this does not show

* The inventory is a statement about **the commits it records** (`inventory.json`, `clones`), taken from fresh clones on 2026-11-23; the repositories move.
* **Not examined:** the verification of commit signatures (the commit-msg hook's Vault signature) and any verifier of them; the Forms and the engine receipts; the Relay deployment's use of the chain; Vault key custody and the Root key store; revocation and OCSP; GitHub Actions attestations; the countersign service's own clock source; the records of repositories that were not cloned (archived and private ones); the top-level entries of the registry outside the record areas (listed in the inventory, 30 of them: documentation, tests, tools, configuration).
* The boundary of a class is the **earliest end among the certificates the records carry and the validity they declare**; it is not an assertion about the date a record was signed, which is exactly what the missing time evidence would have shown.
* The statements about the Relay and primitives verifiers are **read from the code** at the recorded lines (the primitives behaviour was measured with a fixed clock in the T3 work); the check proves the anchors, not the behaviour.
* The options A and C depend on third parties whose terms and long-term behaviour this document did not verify.
* This is a plan and a set of options. **No time stamp was requested, no key was used, nothing was signed, uploaded, renewed or published.**
