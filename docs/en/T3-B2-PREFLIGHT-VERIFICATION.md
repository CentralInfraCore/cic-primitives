# T3 time evidence: the Backblaze B2 preflight verification (V1, V2, V3, V6), documentation level

Status: **a verification record at documentation level**, 2026-11-05. Documentation only. **No account, bucket, key, test object or upload exists or was made.** It closes nothing by itself: it says, for each of the four checks V1, V2, V3 and V6 of `T3-EVIDENCE-STORAGE-DECISION-PROPOSAL.md` (cic-primitives #34), what the provider's own documentation establishes, what it does not establish, and what only a throw-away bucket can show. **A statement in documentation is not a passed deletion or permission test**, and none is recorded here as passed. The archive (SHA-256 `e1795fcf8543be8d5ea6f379672f3a7ba7a2d2d42c674113ba994c24a8cddab5`) is untouched; the second copy stays **NOT BACKED UP**; S10 (who holds the account) stays held.

**How the sources were read.** The pages were fetched on 2026-11-05 through a tool that returns an extract of the page for a question, not the page itself; quotations are as the tool returned them. A page marked "snippet" was seen only in a search result. Before an approval relies on any line of this record, the owner (or a reviewer) re-reads the cited page in a browser. Several provider pages refused automated access (403) or no longer exist (404); they are named.

## Summary

| Check | What documentation establishes | Not established by documentation | Needs a throw-away bucket |
|---|---|---|---|
| **V1** Object Lock and versions | Compliance retention cannot be removed by any user; a delete of a locked version is refused (HTTP 401 `access_denied` on the native API); buckets keep versions by default; a name-only upload adds a version; a version is addressable by File ID | that an overwrite or delete of a locked **name** leaves the locked version readable (stated by the official pages only indirectly); the S3-API error for a versioned delete of a locked version; what `bypassGovernance` does to a compliance version | all four, as a trial |
| **V2** Two-factor | An authenticator-app (TOTP) method with 10 backup codes, and SMS as a fallback after the first payment; the B2 product is an "Enabled Product" of the same Backblaze account | that the B2 account is covered by exactly these pages; any hardware key; a way to **require** it; what the recovery path is when both the device and the codes are lost; that application keys do not bypass it (they do not use it) | the enabling, the recovery-code use and the sign-in |
| **V3** Extending retention | Extending needs only the `writeFileRetentions` capability (no `deleteFiles`, `readFiles` or `writeFiles` is mentioned); compliance retention can be extended and cannot be removed; a bucket-restricted key may carry the retention capabilities | what a shortening attempt returns; whether finding the File ID needs `listFiles`; whether the S3 call needs the same capability set; that a key **without** `deleteFiles` really extends | the key and the extension |
| **V6** Account end | The Terms (effective 2026-04-16) allow Backblaze to suspend or terminate an account on non-payment "and may delete your data"; deleting an account removes access to its files; closing a B2 account requires removing all files, buckets and non-master keys first; the Terms set no deletion timelines and **never mention Object Lock** | what the provider does with compliance-locked data on non-payment or termination; the notice period; whether a locked bucket can be closed at all; the contents of the non-payment procedure | nothing (a written answer from the provider is needed) |

**Reading.** The documentation supports the central claim: a compliance-locked version cannot be shortened or deleted by the customer's identities. It does **not** establish that the provider will keep it, and it does not establish the opposite: the Terms give the provider a right to suspend, terminate and delete on non-payment and say nothing about Object Lock, so how the two relate is unclear. The documentation available does not establish whether compliance retention survives account suspension, termination, non-payment, or provider-initiated deletion. Until Backblaze confirms this in writing, provider-side preservation remains an unverified assumption. That is exactly the "account is the weakest point" risk of the proposal, and it is why the second copy of a different class, independent of the provider, is part of the plan and not an option. **B2 cannot be said to meet the T3 retention contract until V1 and V3 have passed on a throw-away bucket and a written answer on V6 is in the record.**

## V1: Object Lock and versions

**Documented.**
* Compliance mode: retention "cannot be removed by any user"; it can be extended; retention is one to 3 000 days; changes or deletions to a locked file fail until the period ends, and lifecycle settings that try to change or delete a locked file also fail. [B2-LOCK, read]
* Versions: "Backblaze B2 can track when a file is deleted"; uploading under an existing name adds a newer version ("there are now two versions in the list, with the newest one first"); a download by name returns the newest version; "you can find its File ID, and then download it" for an older one (`b2_download_file_by_id` "downloads a specific version of a file by the given file ID"); `b2_hide_file` adds a hide marker; `b2_delete_file_version` "permanently deletes the file version". [B2-VERSIONS, read]
* A delete refused by Object Lock: `b2_delete_file_version` returns HTTP **401**, code `access_denied`, "The delete was not allowed because Object Lock is enabled on the file". The call needs the `deleteFiles` capability; `bypassGovernance` is documented for **governance** retention only. [B2-DELETE-VERSION, read]
* The S3-compatible API: buckets are versioned; a delete without `versionId` inserts a delete marker (`x-amz-delete-marker: true`); a delete with a `versionId` removes that version permanently. The page is marked as stale. [S3-BUCKET-VERSIONS, snippet; S3-DELETE, read]

**Not established by what was read.**
* That an upload or a delete under the **same name** as a locked version leaves the locked version in place and readable by File ID. The official Object Lock page read did not say it; a forum post quoting the documentation did (that no mode prevents uploading a new version of a locked object, and that the lock is specific to the version). [FORUM-QUOTE, snippet, not authoritative]
* What the S3 API answers to a delete with a `versionId` of a locked version (the delete-object page says nothing about Object Lock, and is stale).
* What `bypassGovernance` does to a **compliance** version (the delete-version page documents it for governance only).

**Needs a throw-away bucket** (not run): in a bucket with default compliance retention of one day, with a key that has delete capability: (1) upload `t`, read its retention; (2) delete that version by File ID (native) and by `versionId` (S3): both must be refused; (3) upload `t` again: a second version must appear and the first must stay readable by File ID and by `versionId`; (4) delete `t` by name: a hide marker or delete marker, the locked version readable by File ID; (5) delete the version with `bypassGovernance` true: refused; (6) shorten the retention: refused; (7) after the day has passed, the version can be deleted. Record every status and error code. Each is "not run".

## V2: two-factor verification

**Documented** (the pages found are the Backblaze account pages for the backup product; the B2 console uses the same account: the B2 cancellation page speaks of "Enabled Products" under My Settings, B2 Cloud Storage among them). [B2-CANCEL, read; 2FA pages, snippets]
* An authenticator-app (TOTP) method (any compatible app), with SMS as an optional fallback; the SMS option appears only after the first payment has been processed.
* Backup codes: ten one-time codes, ten characters each, "use them only as a last resort"; a sign-in has a "Use Backup Code" link.
* Where: My Settings, Security, Sign In Settings.
* Two-factor verification is not available for accounts that use single sign-on.

**Not established.**
* That these are the pages for a B2-only account (they are the backup product's pages; likely the same account setting, not shown).
* Any hardware key or passkey method (none was found).
* A way to **require** two-factor for every sign-in of the account holder or other users (none was found).
* What the recovery path is when the device **and** the backup codes are lost (not documented in what was seen).
* The application keys do not use two-factor (an API key is a bearer credential); the protection of the keys is their capability limits and where they are kept.

**Needs the account** (not run, not possible before S10): enable TOTP, generate the codes, sign out and in with a code, and read the account's recovery description.

## V3: extending the retention without delete rights

**Documented.**
* `b2_update_file_retention`: "The token must have the writeFileRetentions capability." The page mentions no `readFiles`, `writeFiles` or `deleteFiles` requirement. Compliance retention "cannot removed by any user, but their retention dates can be extended by clients with appropriate application key capabilities." Request fields: `fileName`, `fileId`, `fileRetention` (`mode`, `retainUntilTimestamp`). A token without authority gets 403 `access_denied`; a bucket that is not Object Lock enabled gets 400 `bad_request`. [B2-UPDATE-RETENTION, read]
* The `fileId` comes from the upload response, `b2_list_file_names` or `b2_list_file_versions` (same page).
* A bucket-restricted key may carry exactly the capabilities `listFiles`, `readFiles`, `shareFiles`, `writeFiles`, `deleteFiles`, `readBucketRetentions`, `writeBucketRetentions`, `readFileRetentions`, `writeFileRetentions`, `bypassGovernance`, `readFileLegalHolds` and `writeFileLegalHolds`, and can be limited to one bucket and a name prefix. [B2-KEYS, read]
* The S3-compatible `PutObjectRetention` accepts an optional `versionId`; an example request uses `COMPLIANCE`. A reseller guide says the key "may need" `writeFileRetentions` and `readFileRetentions`. [S3-PUT-RETENTION, read; RESELLER-GUIDE, snippet]
* Bucket default retention is read and written with `readBucketRetentions` and `writeBucketRetentions`. [B2-LOCK, read]

**Not established.**
* What a **shortening** attempt in compliance mode returns (the pages say it cannot be removed and can be extended, not what the error is).
* Whether the administrator needs `listFiles` to obtain the File ID (the upload response supplies it once; the later extension needs it recorded or listed).
* Which capabilities the **S3** path needs for `PutObjectRetention` (the page does not say).
* That a key **without** `deleteFiles` really extends, and that the same key cannot delete.

**Needs a throw-away bucket** (not run): create an administrator key limited to the bucket with `listFiles`, `readFileRetentions`, `writeFileRetentions`, `readBucketRetentions`, `writeBucketRetentions` and without `deleteFiles`, `writeFiles`, `bypassGovernance`; with it: extend the retention of the trial version (must succeed), shorten it (must fail, record the code), delete the version (must fail), upload (must fail). Then the same extension through the S3 API with that key.

## V6: the end of an account

**Documented.** [TERMS, read: Backblaze Terms of Service, effective 2026-04-16; B2-CANCEL, read; AUP and non-payment article, snippets]
* §5: Backblaze may suspend or terminate an account, and "may delete your data", if the customer stops paying or violates the Terms; it may act immediately and without notice where it reasonably believes the use violates law, the Terms or the Acceptable Use Policy or to prevent harm.
* §5: "In our sole discretion, we may, at any time change, eliminate, or restrict access to our Service(s)", with commercially reasonable advance notice of a material change.
* §13: the customer can cancel and delete the account at any time (without a committed term); "When you delete your account, your account information ... will be removed from our active system" and access to "any Files that remain" is lost.
* Part A §13 / Part B §26: the Terms can be updated at Backblaze's sole discretion; for changes that substantially alter the customer's rights, notice "in accordance with applicable law".
* **The Terms set no deletion timelines and do not mention Object Lock or retention.**
* Closing a B2 account (the documentation, last updated 2024-06-05): first remove all files from the buckets, delete the buckets, delete all non-master application keys and all snapshots, then clear the B2 Cloud Storage checkbox. The page does not mention Object Lock or what applies to locked files.
* The Acceptable Use Policy lists failing to pay more than fifteen days past the due date as a violation, unless disputed in good faith; the help-center article on B2 non-payment describes a late phase in which the customer is warned that data "may be deleted at any moment". [snippets only; the article refused automated access]
* The Object Lock page says that to recover from a lock set for too long, the account must be closed. [B2-LOCK, read]

**Not established.**
* What happens to **compliance-locked** data when payment lapses or the account is terminated or closed: whether Backblaze deletes it, keeps it to the retain-until date, or refuses the closure.
* The notice period and the timeline of the non-payment phases (the article could not be read).
* How an account with locked files can be closed at all if the steps require removing all files, and the Object Lock page says closure is the way out of an over-long lock.
* Whether the lock constrains the provider as well as the customer's identities. The Terms give the provider a right to delete on non-payment and do not exempt locked data, and they do not say that they override the lock either; the relation is unclear, so neither "the provider may delete locked data" nor "the provider must keep it" follows from what was read.

**Needs a written answer from the provider** (no throw-away bucket can show it): the owner asks Backblaze in writing, and the answer is added to this record with its date. The questions: (1) is data under a compliance retention exempt from deletion on non-payment, suspension or termination, and until when; (2) the notice periods and phases before any deletion of an Object Lock bucket; (3) how an account with locked files is closed, and what happens to the files; (4) whether a prepaid or committed term (the pricing page offers one-to-five-year commitments billed at the start) changes any of this. Until the answer is in the record: *The available documentation does not establish whether compliance retention survives account suspension, termination, non-payment, or provider-initiated deletion. Until Backblaze confirms this in writing, provider-side preservation remains an unverified assumption.* Two things must not be equated: data that the **customer cannot delete**, and data that the **provider is committed to keep**. The first is what the documentation describes; the second is what is asked below. Appendix A is the draft of the inquiry (not sent).

## Appendix A: the draft of the written inquiry to Backblaze (NOT SENT)

Prepared for the owner. It is **not sent**: sending it needs an account or a contact address and the owner's name, which are the owner's (S10) to decide, and nothing is created for it. It contains no personal data, no account identifier and no secret. The data it concerns is public (721 KB, a time-stamp evidence archive).

> Subject: Object Lock (compliance mode): what happens to locked data on suspension, termination, non-payment and account closure?
>
> We intend to keep one small, public, long-lived archive (about 721 KB) in a B2 bucket with Object Lock in compliance mode, with a retention of about ten years (extended from the 3 000-day maximum before it expires). It is a time-stamp evidence archive; losing it cannot be undone. Before we do, please answer the following in writing. **For each answer, please state separately (A) what is technically possible or current practice, and (B) what is a contractual commitment, with the document, the clause and the version or date of the terms that contain it, and whether the commitment holds for the whole retention period.** If something is current practice and not a commitment, please say so. A general support answer is welcome, but please tell us whether it is binding.
>
> 1. Is data under a compliance-mode retention exempt from deletion by Backblaze on account suspension, termination, non-payment or provider-initiated deletion, and until when (the retain-until date, or not)? Your Terms of Service (effective 2026-04-16, section 5) say Backblaze "may delete your data" on non-payment; they do not mention Object Lock.
> 2. What are the phases and the notice periods before any deletion of an Object Lock bucket after a failed payment, and what warnings are sent, to which address?
> 3. How is an account with locked files closed? The cancellation procedure requires removing all files and buckets first, and the Object Lock documentation says closing the account is the way out of a lock set too long. What happens to files that cannot be deleted, and is there a case where Backblaze keeps them after the account is closed?
> 4. Does a prepaid or committed term (the pricing page describes one-to-five-year commitments billed at the start) change any of the answers to 1 to 3?
> 5. If the service or the Terms change (section 5 allows changes in Backblaze's sole discretion), is there a commitment about data already under a retention, and how are customers notified?
>
> Please reply in writing and quote the ticket or reference number. Thank you.

The answer is added to this record with its date, its form (a ticket, an email, a contract clause) and, for each question, whether it is a technical statement, a practice, or a commitment. **A technical statement or a practice does not close V6; only a commitment of the provider that holds for the retention period does.** If the answer is only a practice, V6 stays open and the second copy of a different class carries the guarantee.

## What this record changes

* It does not approve B2, create anything or change a state. S3 stays "a conditional go after V1 to V3 and V6".
* V1, V2 and V3 are **documentation-checked and test-open**: the tests above are written and each is "not run".
* V6 is **open and needs the provider's written answer**; the Terms read in full give the provider a right to delete on non-payment and are silent on Object Lock.
* The risk list of the proposal is confirmed and sharpened: the account is the weakest point, and the second copy of a different class is required.

## Sources (fetched 2026-11-05)

* [B2-LOCK] https://www.backblaze.com/docs/cloud-storage-object-lock (read)
* [B2-VERSIONS] https://www.backblaze.com/docs/cloud-storage-file-versions (read)
* [B2-DELETE-VERSION] https://www.backblaze.com/apidocs/b2-delete-file-version (read)
* [B2-UPDATE-RETENTION] https://www.backblaze.com/apidocs/b2-update-file-retention (read)
* [B2-KEYS] https://www.backblaze.com/docs/cloud-storage-application-keys (read)
* [S3-DELETE] https://www.backblaze.com/apidocs/s3-delete-object (read, marked stale)
* [S3-PUT-RETENTION] https://www.backblaze.com/apidocs/s3-put-object-retention (read)
* [S3-BUCKET-VERSIONS] https://www.backblaze.com/docs/cloud-storage-s3-compatible-api-bucket-versions (snippet)
* [B2-CANCEL] https://www.backblaze.com/docs/cloud-storage-delete-or-cancel-a-backblaze-b2-account (read)
* [TERMS] https://www.backblaze.com/terms (read; effective 2026-04-16)
* 2FA pages (snippets; the backup product's pages): https://help.backblaze.com/hc/en-us/articles/217666588 (refused, 403), https://backblaze.com/computer-backup/docs/enable-and-disable-two-factor-verification (404 when fetched; seen in a search result)
* Non-payment article (snippet; refused, 403): https://help.backblaze.com/hc/en-us/articles/219361957-B2-Non-payment-procedures
* [FORUM-QUOTE] a Veeam forum post quoting the Object Lock documentation: https://forums.veeam.com/viewtopic.php?p=521046 (snippet; not authoritative)
* [RESELLER-GUIDE] https://www.backblaze.com/docs/cloud-storage-configure-immutable-storage-for-reseller-and-msp-customers (snippet)
* [B2-PRICE] https://www.backblaze.com/cloud-storage/pricing (read)

## Not claimed

That any check passed; that a deletion, shortening, overwrite or permission test was run; that B2 meets the T3 retention contract; that the provider will keep locked data; that two-factor can be required; anything about an account, a payment method or a person (S10).
