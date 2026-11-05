# T3 time evidence: the proposal for the decisions S3 (the store and its access), S5 (retention) and S9 (custody)

Status: **proposal for the owner's decision**, 2026-11-05. Documentation only. **Nothing is created, uploaded or paid for; no account exists; no provider is selected until the owner says so.** It completes `T3-EVIDENCE-STORAGE-AND-RESTORE-PLAN.md` (cic-primitives #33). The archive stays exactly as it is: no repacking, no new hash, no change of `verify.sh` (SHA-256 `e1795fcf8543be8d5ea6f379672f3a7ba7a2d2d42c674113ba994c24a8cddab5`, 721 205 bytes). The state of the second copy is **NOT BACKED UP**.

## 1. The proposal in one paragraph

**Online copy:** an S3-compatible object bucket at **Backblaze B2** with Object Lock in **compliance mode**, retention 3 000 days (the provider's maximum) plus a **legal hold**, extended before it runs out, with three separate identities (uploader, reader, administrator) and the account protected by two-factor verification. **Fallback if B2's checks in section 6 fail: Amazon S3** (best documented, also compliance mode). **Offline copy:** the archive on write-once or offline media in a second physical place, as the second class. **Custody (S9):** the approved hash, the custody log and the restore commands in four places, none of them only GitHub (section 5). Cost: practically nothing for the data (a few euros over ten years including the offline medium); the real costs and risks are the account, the payment method and the duty to extend the retention (section 4). Everything below says where a fact comes from and which ones must still be checked before approval.

## 2. The candidates, and how they were compared

Required (from the task): independent of GitHub; versioning; **real** WORM (a retention that nobody, the account owner included, can shorten or remove); separate read and write permissions.

| | Backblaze B2 | Amazon S3 | Scaleway Object Storage | Wasabi |
|---|---|---|---|---|
| Operator and failure boundary | Backblaze, Inc. (US) | Amazon (US) | Scaleway (Iliad, FR) | Wasabi (US) |
| Compliance mode (not removable) | **Yes.** "cannot be removed by any user"; retention can be extended, not shortened [B2-LOCK] | **Yes.** "can't be overwritten or deleted by any user, including the root user"; the only way before expiry is to delete the AWS account [S3-LOCK] | Yes per the provider's concepts text: version cannot be overwritten or deleted by any user; mode cannot change, period cannot be shortened; also ends on account deletion [SCW-SNIPPET] | Yes: the lock cannot be shortened in compliance mode [WAS-SNIPPET] |
| Retention limit | **1 to 3 000 days per setting** (about 8.2 years); extendable [B2-LOCK] | not stated on the page read; a bucket policy can set a limit; extendable by any identity with `s3:PutObjectRetention` [S3-LOCK] | not obtained | not stated in what was found |
| Legal hold (no expiry) | yes, per file, separate from retention [B2-LOCK] | yes, `s3:PutObjectLegalHold` [S3-LOCK] | not obtained | yes (retention stays after removal) [WAS-SNIPPET] |
| Versioning | not stated on the Object Lock page; must be checked (section 6) | required by Object Lock; versions are protected individually [S3-LOCK] | not obtained | not obtained |
| Separate read / write identities | **Yes.** Application keys limited to one bucket and a name prefix; capabilities include `readFiles`, `writeFiles`, `deleteFiles`, `readFileRetentions`, `writeFileRetentions`, `bypassGovernance`, `writeFileLegalHolds`; a "Read Only" and a "Write Only" type [B2-KEYS] | **Yes.** IAM, with the Object Lock actions as separate permissions [S3-LOCK] | IAM policies; not verified | not verified |
| MFA on the account | Backblaze supports authenticator-app verification; **confirmation for B2 accounts still needed** [B2-2FA] | yes (a well-known feature; not read in this proposal) | not obtained | not obtained |
| Price relevant to 721 KB | $6.95 per TB per month; the first 10 GB free; free egress up to 3x the stored data; "no minimum file size" and "no minimum storage duration" fees stated [B2-PRICE] | storage rates did not render on the page read; the first 100 GB of transfer out per month are free; no minimum duration for the Standard class [S3-PRICE] | EUR 0.0146 per GB per month (Multi-AZ), 75 GB egress free [SCW-PRICE-SNIPPET] | $7.99 per TB, **a minimum monthly charge tied to 1 TB**, a 90-day minimum storage duration [WAS-PRICE] |

**Reading of the table.** Wasabi is out for this purpose: a minimum charge for 1 TB (about $96 a year) for 721 KB is far more than the data needs (B2 would charge nothing for it). Scaleway is a reasonable European alternative, but its pages could not be read in full (access was refused), so every fact in its column is from search excerpts and must be verified before it could be approved. **B2 and S3 are the two candidates whose facts were read from the provider's own pages.** B2 is proposed first because its application keys are the most granular and its price for this data is zero; S3 is the fallback because it is the best documented; its maximum retention was not stated on the page read (V4).

## 3. The access model (S3)

Three identities, none of them the account's master credential, none of them shared:

| Identity | Purpose | Allowed | Explicitly not allowed |
|---|---|---|---|
| **Uploader** | the one-time upload of the archive and the small reference objects | write one bucket (and the name prefix `T3/`) | list other buckets, read, delete, any retention or legal-hold operation, bucket settings |
| **Reader** | read-back, restore drills, periodic checks | list and read the bucket (and read retention) | write, delete, retention, legal hold |
| **Administrator** | set the retention and the legal hold, extend the retention, review the settings | the retention and legal-hold capabilities for the bucket | day-to-day use; it is used only for the events of section 4, and its credentials are not kept on the machine that uploads |

* **The master credential is locked away** and not used for any of the three; the account holder is named; the account has two-factor verification with the recovery codes kept offline in a second place; the contact address of the account is a role mailbox that more than one person can read.
* **Compliance mode removes the need to trust the identities about deletion**: even the administrator cannot shorten the retention or delete before expiry. What an identity could still do is extend the retention (harmless) or close the account (see the risks); so the account itself, its payment method and its recovery codes are the real controls.
* **Upload, then lock, then prove.** The uploader writes; the administrator sets retention and legal hold; the reader reads back by version; a deliberate attempt to delete and to shorten, on a **throw-away object** in the same bucket, must be refused before the archive is trusted to the setup.
* **Provider choice is not made by this section**: the table is written for B2 (the proposal) and maps one to one to IAM users and policies for S3.

## 4. Retention (S5) and cost and risk

**Proposal: ten years, in two layers.** (1) Compliance-mode retention at upload. On B2 the longest single setting is 3 000 days (about 8.2 years), so ten years is reached by **extending the retention once, before it expires** (a calendar duty of the administrator, entered in the custody log; the lock can be extended, never shortened). (2) A **legal hold** on the object, which has no expiry and so bridges any gap, understanding that a legal hold can be removed by an identity that holds the legal-hold capability, so it is a safety net and not the WORM guarantee; the compliance retention is the guarantee. On S3 a single retain-until-date can be set to the end date directly (the maximum was not stated on the page read; verify before approval). Whatever is chosen, **the first extension date is a recorded commitment of the owner**, and the retention must outlast 2026-12-31 (the end of the signing chain) by the useful life of the claim, which the owner decides.

**What it costs.** The data is 721 KB, plus a few small reference objects. At B2's published prices that is inside the free 10 GB, a restore drill is inside the free egress, and the provider states no minimum-duration or minimum-size fee: the storage cost is zero or cents. At S3 it would be well under a cent a month (rates not read, the order of magnitude is from the size). An offline medium and its custody are a few euros. **The costs that matter are not the storage price**: a payment method that stays valid for ten years, the time of the periodic checks (about an hour a year), the one extension, the two-factor device and the recovery codes, and the person who does these things.

**Risks, in the order that matters.**
1. **The account is the weakest point.** The only way to remove a compliance-locked object early is to delete or close the account (both B2 and S3 say so). A lapsed payment, a closed account or a lost recovery code can end the copy. Mitigation: a funded payment method with alerts, a role mailbox, recovery codes in two places, and the **second copy of a different class** (the offline medium), so the account is not a single point of failure.
2. **Retention that expires unextended.** A calendar entry, the custody log and the periodic check include the days left to the retain-until date.
3. **The provider changes or ends the service.** The exit path is a standard S3 download of 721 KB; the periodic restore drill keeps it exercised; the second class is independent.
4. **Wrong lock.** A lock set too long cannot be undone (B2: "you must close your account"). The retention is therefore set once, deliberately, after the throw-away trial of section 3.
5. **Jurisdiction and terms.** The data is public, so residency is not a confidentiality matter; a change of terms is watched at each check. The open question of the DigiCert endpoint's terms (S8) is unaffected.

## 5. The custody model (S9)

The reference that makes a hash meaningful has to survive the loss of GitHub. Three artifacts: **A** the approved archive hash statement (the value in section 1 with the date), **B** the custody log (appended to at each step), **C** the restore commands and dependency list (section 6 of the plan). They are kept in four places:

1. **In the repository** (cic-primitives, version-controlled, append-only): the working copy of B, and the text of A and C.
2. **In the online store, as separate small objects** under `T3/reference/`, each with its own recorded SHA-256 and the same compliance lock: A, C and a copy of B at each step. B is a series of objects (a new object per step; an object is never replaced).
3. **On the offline medium**: A, B and C as files, and A written by hand on the label or sleeve with the date.
4. **In the owner's own records**, outside both: the hash of A and the identity of the copies.

A check compares these places with each other at each periodic check; a difference is an incident. The log rows carry no credential.

## 6. What must be verified before approval

| # | To verify | Why |
|---|---|---|
| V1 | B2 versioning with Object Lock: that overwriting or deleting a locked file name creates a version or fails, and that the locked version stays readable by version id | the Object Lock page did not say; the restore reads "by version id" |
| V2 | B2 account two-factor verification for **cloud storage accounts** (the sources found describe the consumer backup product), and whether it can be required | access control |
| V3 | The B2 procedure and capability to extend retention, and that the administrator key can hold `writeFileRetentions` without `deleteFiles` | the ten-year plan depends on it |
| V4 | The S3 maximum retain-until date and the storage prices (the page read did not render them) | the fallback |
| V5 | If Scaleway is to be considered: its Object Lock page, its retention limit, versioning and IAM, read from the provider's pages (they refused access here) | only search excerpts were seen |
| V6 | The terms of service of the chosen provider on account closure, payment lapse and data deletion | the account is the weakest point |

These are checks on the provider's own pages or a throw-away bucket; none needs the archive.

## 7. The decision asked

| # | Decision | Proposal |
|---|---|---|
| S3 | The provider, the identities and the settings of section 3 | B2 for the online copy, S3 as the fallback, if V1 to V3 and V6 pass; the offline medium as the second class |
| S5 | The retention | ten years in two layers (section 4), with the owner's recorded commitment to extend |
| S9 | The custody model | the four places of section 5 |
| S10 | Who is the account holder, the administrator and the successor, and which payment method and role mailbox are used | the owner names them; nothing is created before |

After the owner's decision, the order is: create the account and the identities, run the throw-away trial, upload, read back by version, restore drill, complete the custody log, and only then the state changes.

## 8. Sources (read on 2026-11-05)

* [B2-LOCK] Backblaze, Object Lock: https://www.backblaze.com/docs/cloud-storage-object-lock (read in full)
* [B2-KEYS] Backblaze, application keys: https://www.backblaze.com/docs/cloud-storage-application-keys (read in full)
* [B2-PRICE] Backblaze B2 pricing: https://www.backblaze.com/cloud-storage/pricing (read; the page shows no date)
* [B2-2FA] Backblaze two-factor verification (search result, consumer product): https://backblaze.com/computer-backup/docs/enable-and-disable-two-factor-verification
* [S3-LOCK] Amazon S3 Object Lock: https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html (read in full)
* [S3-PRICE] Amazon S3 pricing: https://aws.amazon.com/s3/pricing/ (the rate tables did not render)
* [SCW-SNIPPET] and [SCW-PRICE-SNIPPET] Scaleway Object Lock and storage pricing: https://www.scaleway.com/en/docs/object-storage/api-cli/object-lock/ and https://www.scaleway.com/en/pricing/storage (**only search excerpts**; the pages refused access)
* [WAS-SNIPPET] Wasabi Object Lock (search excerpts; the documentation pages were not reachable): https://docs.wasabi.com/docs/wasabi-object-lock
* [WAS-PRICE] Wasabi pricing: https://wasabi.com/cloud-storage-pricing (read)

## 9. Not claimed

That any provider is approved or any account exists; that the facts marked as search excerpts or not obtained are true; that the archive survives anything until section 7 is executed and a restore drill from the stored object has passed. Nothing here changes the archive, the verifier or the state **NOT BACKED UP**.
