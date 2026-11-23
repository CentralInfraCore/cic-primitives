# T3 time-stamping: preparing the storage decision (S3, S10) for the owner

Status: **preparation of a proposal for the owner's decision**, 2026-11-23, under the limited GO "documentation only" (review of `a6272a8`). **Nothing is created, ordered, paid for or uploaded; no account exists; no provider is selected until the owner decides.** Choosing a provider in this document does not show that a store works or that a restore succeeds: only the evidence of the conditions below does. It builds on `T3-EVIDENCE-STORAGE-AND-RESTORE-PLAN.md` (#33) and `T3-EVIDENCE-STORAGE-DECISION-PROPOSAL.md` (#34, read 2026-11-05), whose facts are re-checked here where the provider's page could be read again (section 7).

## 1. Why this is the critical path

The owner chose the **staged** order (Q6a): before the execution GO, **two separate, verified storage locations** must exist (C-Q6-1 and C-Q6-2: provisioned, a dry-run package read back with its digest verified) and custody must be documented (C-Q6-5). Today **none of the three is met and nothing exists**; the other pre-conditions that remain open are the executor (C-Q3-1) and the Q2 provider permissions. The storage chain needs **people outside this repository**: an account holder, a payment method, two provider sign-ups, terms accepted. Those take calendar time that no check can shorten; that, not the readiness state machine, is the risk to the 2026-11-30 target (and to the internal latest date 2026-12-15; the signing chain ends 2026-12-31 13:22:39 UTC).

## 2. Acceptance criteria (primary: C-Q6-1, C-Q6-2, C-Q6-5)

A proposal is acceptable only if, for **each** location, the following can be **shown by evidence the readiness check reads**, not asserted:

| # | Criterion | Evidence that will show it (after the owner's GO to provision) |
|---|---|---|
| A1 | **Immutability:** compliance-type retention that nobody, the account owner included, can shorten or remove, of **at least 10 years** (a planning minimum) | the provider's own read-back of the object's retention mode and retain-until date, recorded with the version id; a refused delete/shorten on a throw-away trial object |
| A2 | **Versioning**, so an overwrite cannot replace the protected bytes | the trial object: an overwrite creates a new version, the locked one stays readable by version id |
| A3 | **Independence of the two locations:** different operator, different account, different billing, different credentials; not two regions of one provider | the account record (section 4), the named holder per location |
| A4 | **Read-back:** the dry-run package (the manifest, the verification procedure; NO real token) is read back from each location and its SHA-256 equals the local one (dry-run manifest digest `d7cb0f75...4dc4e38` is the current dry-run value only) | a digest-bound evidence file per location (no credential in it) |
| A5 | **Custody (C-Q6-5):** a named holder, **separate credentials per location and per role**, a recovery path, a successor | the custody record (section 4) |
| A6 | **No secret in the repository:** no key, token or account identifier that would grant access | the repository scan before every upload (plan #33, S1) |

C-Q6-3, C-Q6-4, C-Q6-6, C-Q6-7 (the third, offline copy; a dry-run package from each location; restore drills; the renewal mechanism) are **preserve-phase** under the chosen order and are not on the critical path to the GO; they are listed in section 6 so the proposal does not forget them.

## 3. The options

The online pair must satisfy A3, so the question is which two operators. Facts are from the providers' own pages unless marked.

| Option (A + B) | For | Against | State of the facts |
|---|---|---|---|
| **B2 + AWS S3** | both read from the providers' own documentation; two US operators, separate accounts and billing; B2's keys are the most granular, S3 is the best documented | both US-based (a jurisdiction-diversity argument is not made); B2's retention maximum is 3 000 days, so the 10 years need one extension; S3's maximum retention depends on a bucket policy (not stated on the page) | **read** 2026-11-23 (B2 lock page, S3 lock page); prices of 2026-11-05 |
| **B2 + Scaleway** (EU) | a second jurisdiction and operator | Scaleway's pages **refused access** (403 on 2026-11-23, as on 2026-11-05): every Scaleway fact is a search excerpt and **unverified** | **not verifiable now** |
| **AWS S3 + Scaleway** | one US, one EU | same Scaleway gap; S3 alone carries the retention-extension question differently | **not verifiable now** |

**Proposal (for decision, not a selection): B2 as location A and AWS S3 as location B**, because they are the two whose lock semantics were read from the providers' own pages, with Scaleway or another EU operator considered a later **third online** option only after its pages are read. The offline copy (C) stays the second class of the plan #33.

**Date arithmetic for the retention (computed):** a retention started on 2026-11-30 under B2's maximum 3 000 days ends **2035-02-16**; 10 years from then is **2036-11-30**. So B2 needs **one extension before 2035-02-16** (a dated duty of the administrator, entered in the custody log; the lock can be extended, never shortened). For S3, a retain-until date can be set to 2036-12-31 directly if the bucket policy permits it (verify V4). A retention set too long cannot be undone (B2: the only way out is closing the account), so the period is set once, deliberately, after the trial object.

## 4. Account and custody model (S10): what the owner must name

Nothing below is a person; the owner fills the roles (section 8, D-S10). **The roles are proposed; nobody is named and nothing is created.**

| Role | Duty | Constraint |
|---|---|---|
| **Account holder** per location | owns the account and its payment method | **different holders or at least different accounts, payment instruments and recovery mailboxes for A and B** (A3); a role mailbox that more than one person can read |
| **Administrator** | sets and extends the retention and the legal hold | credentials kept apart from the uploader's machine; used only for those events; **no delete capability** where the provider allows it |
| **Uploader** | writes the dry-run and the final package | write-only to one bucket and one prefix; no read, delete, retention operation |
| **Reader** | read-back and the yearly restore drill | read-only |
| **Successor** | takes over the roles if the holder is unavailable | named in the custody record; recovery codes in two physical places |

Controls that matter more than the storage price: a **funded payment method with alerts** for ten years, the **two-factor device and recovery codes**, the **dated extension duty**, the yearly restore drill (an hour a year), and the successor. **The account is the weakest point:** a compliance-locked object can be removed early only by closing or deleting the account, so a lapsed payment or a closed account ends the copy; the offline copy and the second online location are the mitigation, which is why A3 (independence) is a criterion and not a preference.

## 5. Cost and risk (honest limits)

* **Storage price:** the dry-run package is some tens of kilobytes; the final package (the records' bytes or a digest-verified source, the manifest, two raw tokens, chains, the frozen procedure) is small (the earlier archive of #33 is 721 KB). At the published prices (B2 2026-11-05: first 10 GB free, no minimum-duration fee; S3: rates not rendered on the page read) the data costs **cents**. A payment method is still **required** for both; that, not the price, is the barrier. **No price here was re-read today** except where stated.
* **Risk order:** (1) the account (closure, lapse, lost recovery); (2) a retention that expires unextended; (3) a provider ending or changing the service (exit: a standard S3-compatible download, exercised by the yearly drill); (4) a wrong lock; (5) terms (account closure, payment lapse, data deletion: **V6, not yet read for either provider**); (6) jurisdiction and sanctions (the data is public; residency is not a confidentiality matter; the owner decides if jurisdiction matters).
* **A provider's page can change:** the pages read are recorded here by date; the full-file archiving of the closing evidence package is the open low item of the research review.

## 6. Sequence after the owner's decision and GO (not started)

For each of A and B, in this order (the lock before the data, never after it): create the bucket with its **default compliance retention**; read the settings back; a **throw-away trial object** proves A1/A2; the **dry-run package** is uploaded by the uploader identity; read back by version id with the reader identity, digest compared (A4); evidence recorded (digest-bound, no credential); then the custody record (A5). Only after both pass is C-Q6-1/2/5 `verified` and, together with the other pre-conditions, may the record reach `PREPARED_FOR_OWNER_GO`. The **third copy, the restore drills and the renewal mechanism** follow in the preserve phase. If any step fails, stop and log it.

## 7. What was re-read on 2026-11-23, and what is still unverified

| Fact | State |
|---|---|
| B2 Object Lock: "between one and 3,000 days"; compliance and governance modes; a lock that is too long can only be undone by closing the account | **re-read**, consistent with 2026-11-05 |
| S3 Object Lock: compliance mode "can't be overwritten or deleted by any user, including the root user"; the retention cannot be shortened; **works only with S3 Versioning enabled**; minimum and maximum retention restrictable by a bucket-policy condition | **re-read**, consistent |
| Scaleway Object Lock and pricing | **not obtainable** (HTTP 403); search excerpts only |
| B2 cloud-storage two-factor verification | **not obtained** (the documentation URL tried returned 404) |
| V1 B2 versioning with Object Lock; V3 retention extension and key capabilities without delete; V4 S3 maximum retain-until and prices; V6 terms on closure, lapse, deletion | **open** (they need the providers' pages or a throw-away bucket; the throw-away bucket is **not authorised**) |

## 8. The decisions asked of the owner (none is taken here)

| # | Decision | Proposal |
|---|---|---|
| D-S3a | the provider pair for A and B | B2 (A) and AWS S3 (B), conditional on V1, V3, V4 and V6 being shown; the offline copy as the third |
| D-S3b | the retention commitment | at least 10 years (a planning minimum, not a legal obligation of the CIC), the B2 extension date **2035-02-16** recorded as a commitment, the yearly restore drill |
| D-S10 | the account holder(s), administrator, successor, the payment instrument and the role mailbox, per location | the owner names them; **held: nobody is named** |
| D-GO | permission to **create the accounts and the throw-away trial and dry-run objects** | **not requested by this document and not given**; today's HOLD stands |

## 9. Not claimed

That any provider is approved, that any account or store exists, that the unverified Scaleway or two-factor facts are true, that the prices are current, that a provider's terms permit this use, or that a restore works. This document changes no condition of the readiness record: C-Q6-1, C-Q6-2 and C-Q6-5 stay `open`.
