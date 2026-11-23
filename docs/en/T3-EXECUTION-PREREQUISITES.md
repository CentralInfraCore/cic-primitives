# The T3 time-stamping: the proposed resolutions and what must be verified before it may be performed

**A record and a checklist: documentation and isolated tooling only.** It performs **nothing**: no time stamp is requested, no key used, nothing signed, uploaded, renewed or published. It keeps three things apart: the **decisions** (the requirements that become binding when the owner confirms them), the **conditions** that still have to be **verified** (provider terms, access, trust anchors, storage, restore drills), and the **GO** to perform the time-stamping, which is a separate owner act and can never be recorded in this file. Data: `docs/design/time-evidence/t3-execution-prerequisites.yaml`; check: `docs/evidence/time-execution-prereq/check_t3_readiness.py`; the manifest: `docs/en/T3-MANIFEST-CONTRACT.md`.

## 1. What is proposed, and what it is not

The five resolutions below are a **reviewer's recommendation of 2026-11-23** that the owner passed into the working session. **They are not owner decisions: every one is `proposed`.** A decision becomes `confirmed` only with a recorded confirmation by the owner (a date and a reference), and the check refuses a confirmation that is not by the owner. The requirements of a decision are the **approved-if-confirmed** part; the conditions (section 3) are what must still be **shown to be true** and cannot be settled by a decision.

## 2. The five proposed resolutions

<!-- BEGIN DECISIONS TABLE -->
| Decision | Topic | Status | Requirements that become binding if the owner confirms |
|---|---|---|---|
| Q1a | scope and the manifest | **proposed** | (1) All 92 open records are in scope (the 90 countersigned records of the cic-schema-registry and the 2 cic-yang release records). (2) One canonical manifest: for each record its identifier, the SHA-256 of the EXACT record bytes, the repository and the commit and tag references (docs/en/T3-MANIFEST-CONTRACT.md). (3) The digest of the manifest's WHOLE byte stream is what is time-stamped. |
| Q1b | the ended and the unknown template releases | **proposed** | (1) The three ended template releases (base@0.5.0, base@0.6.0, golang@0.6.0) are kept as HISTORICAL evidence; their earlier validity is NOT regarded as proved. (2) Re-signing or retirement of them only by a separate owner decision. (3) The UNKNOWN state of schema-registry@0.1.0 is settled by a separate investigation. |
| Q2 | the time-stamp authorities | **proposed** | (1) FINAL requirement: two organisationally INDEPENDENT RFC 3161 time-stamp authorities, both tied to the same canonical digest. (2) CONDITIONAL choice: the primary candidate is DigiCert, the second candidate GlobalSign; the final selection only after the terms of service, access and the verification chain of each are verified (the conditions C-Q2-*). |
| Q3 | the schedule | **proposed** | (1) Execution target: 2026-11-30. Internal latest date: 2026-12-15. (2) The certificate end of 2026-12-31 13:22:39 UTC is not used as a planned execution time. |
| Q6 | custody and preservation | **proposed** | (1) The manifest, the records, the RFC 3161 tokens, the TSA certificates and the verification aids in at least THREE copies in at least TWO independent storage failure domains: one in immutable object storage, one at a second independent provider, one offline or isolated archive. (2) The preserved package holds the record bytes (or a digest-verified restorable source), the canonical manifest, the RAW token of each authority, the certificate chains and the frozen version of the verification procedure. (3) Retention at least 10 years (a PLANNING minimum, not a statement of a legal obligation of the CIC), a restore and cryptographic check every year, and a planned evidence-renewal mechanism for the weakening of hash algorithms and TSA chains. Q6 is settled BEFORE the time-stamping is performed. |
<!-- END DECISIONS TABLE -->

## 3. The conditions to verify before the time-stamping

A condition is `open` until it names **evidence that the check can read**: a file of the repository and a text that the file must contain, with a date. A condition that names evidence the file does not hold, or an open condition that claims evidence, makes the record **invalid**. A constraint is a standing rule that is satisfied by being written down.

<!-- BEGIN CONDITIONS TABLE -->
| Condition | Decision | Kind | Status | Condition to verify before the time-stamping | Evidence |
|---|---|---|---|---|---|
| C-Q1a-1 | Q1a | condition | **open** | the canonical manifest contract is reviewed and accepted | none |
| C-Q1a-2 | Q1a | condition | **verified** | the manifest builder and verifier are tested and shown to fail for the right reasons (22 checks, the mutations are caught) | `docs/evidence/time-manifest/results/selftest-manifest-output.txt` contains 'self-test: all as expected' (verified 2026-11-23) |
| C-Q1a-3 | Q1a | condition | **verified** | a dry run over the clones builds a manifest of exactly the 92 open records and the verifier confirms every record against git | `docs/evidence/time-manifest/results/DRYRUN-manifest.txt` contains 'count: 92' (verified 2026-11-23) |
| C-Q1a-4 | Q1a | condition | **open** | the manifest that is time-stamped is built at EXECUTION time from the then-current commits, verified, and its digest recorded | none |
| C-Q1b-1 | Q1b | condition | **open** | the bytes of the three ended template releases are in the preserved package | none |
| C-Q1b-2 | Q1b | condition | **open** | an investigation settles the UNKNOWN state of schema-registry@0.1.0 (no certificate, a validity of TBD) | none |
| C-Q1b-3 | Q1b | constraint | **verified** | no re-signing and no retirement of the ended template releases without a separate owner decision | `docs/design/time-evidence/t3-execution-prerequisites.yaml` contains 'only by a separate owner decision' (verified 2026-11-23) |
| C-Q2-1 | Q2 | condition | **open** | DigiCert: RFC 3161 compatibility of its service for the request form used (a documented endpoint; the three tokens of 2026-11-03 are evidence of past behaviour, not of the terms) | none |
| C-Q2-2 | Q2 | condition | **open** | DigiCert: the TSA certificate chain and a trust anchor from an independent source are obtained and checked for the new tokens | none |
| C-Q2-3 | Q2 | condition | **open** | DigiCert: the terms of use of the endpoint and the permission to use it are verified (none were found on 2026-11-03) | none |
| C-Q2-4 | Q2 | condition | **open** | GlobalSign: RFC 3161 compatibility, the digest-based API and the request form are verified | none |
| C-Q2-5 | Q2 | condition | **open** | GlobalSign: the TSA certificate chain and a trust anchor from an independent source are obtained and checked | none |
| C-Q2-6 | Q2 | condition | **open** | GlobalSign: the terms of service, the eligibility and the access (an account, credentials) are verified | none |
| C-Q2-7 | Q2 | condition | **open** | the two authorities are shown to be organisationally independent (different operators and different trust roots) | none |
| C-Q3-1 | Q3 | condition | **open** | the executor of the time-stamping is named by the owner | none |
| C-Q6-1 | Q6 | condition | **open** | copy 1: immutable object storage with versioning and compliance retention of at least 10 years is provisioned, and a test object read back (the storage decision S3 and the account S10 are still open; nothing exists) | none |
| C-Q6-2 | Q6 | condition | **open** | copy 2: a second, independent provider holds the package | none |
| C-Q6-3 | Q6 | condition | **open** | copy 3: an offline or isolated archive holds the package | none |
| C-Q6-4 | Q6 | condition | **open** | the preserved package has the contents the contract names (record bytes or a digest-verified source, the manifest, both raw tokens, the certificate chains, the frozen verification procedure) | none |
| C-Q6-5 | Q6 | condition | **open** | custody and access are documented: a named holder, separate credentials, recovery, a successor (S10) | none |
| C-Q6-6 | Q6 | condition | **open** | a restore drill from EACH copy with a cryptographic check has passed, and the yearly schedule is recorded | none |
| C-Q6-7 | Q6 | condition | **open** | an evidence-renewal mechanism is planned (re-time-stamping before a hash algorithm or a TSA chain weakens) | none |
<!-- END CONDITIONS TABLE -->

## 4. The result today

`python3 docs/evidence/time-execution-prereq/check_t3_readiness.py` (`results/check_t3_readiness.txt`, exit 1): **`T3 time-stamping: NOT_READY`**, and **valid**: no condition is claimed that has no evidence. Of the 22 conditions **3 are verified** (the manifest builder and verifier are tested; a dry run builds exactly the 92 records and verifies them; the standing rule for the template releases), and **19 are open**; all five decisions are `proposed`. At best the check can say `READY_FOR_OWNER_GO`: that is still **not** the GO.

## 5. A tension the owner has to decide (not decided here)

The target of resolution Q3 is **2026-11-30**, seven days after this was written, and resolution Q6 says the preservation is settled **before** the time-stamping is performed, with three copies in two independent failure domains (immutable object storage, a second provider, an offline archive). The first copy needs the storage decision S3 (a provider, an account, payment, a holder: S10), which is **still open**, and nothing exists. **Both cannot be met unless the storage is provisioned within the week.** The irreversible, deadline-bound step is **obtaining the tokens**; the preservation can be completed afterwards, if the tokens are held safely in the meantime. The question for the owner is therefore whether Q6 is a **strict order** (no time-stamping before all three copies exist, which puts the target date at risk) or a **staged** requirement (time-stamp by the target date, hold the tokens and the package in the existing places (the repository history and an offline archive) as interim copies, and complete the three-copy preservation and the restore drills afterwards, still before the internal latest date of 2026-12-15). The recommendation of the review is the strict reading; **this record states the tension and does not choose**.

## 6. The preserved package and the preservation requirements (resolution Q6)

* **Contents** (the condition C-Q6-4): the record bytes, or a **digest-verified restorable source** (the git objects at the recorded commits, with the bundle that restores them); the canonical manifest and its digest; the **raw token of each authority** (not a summary); the TSA certificate chains and the independently obtained trust anchors; the **frozen version** of the verification procedure and of the tools that built and verified the manifest.
* **Copies** (C-Q6-1 to C-Q6-3): at least three, in at least two independent failure domains: immutable object storage (versioning and compliance retention), a second independent provider, an offline or isolated archive. **Putting files in a bucket is not the evidence:** a restore drill from **each** copy with a cryptographic check (C-Q6-6) is.
* **Time:** a **planning minimum of 10 years**, with a restore and cryptographic check every year; the ten years are a design minimum, **not a statement of a legal obligation** of the CIC.
* **Renewal** (C-Q6-7): the hash algorithm and the TSA chains weaken with time; a mechanism to renew the evidence (re-time-stamping before the weakening) has to be **planned**; it is not implemented here.
* **Custody** (C-Q6-5): a named holder, separate credentials, recovery and a successor. Nothing is backed up today (the T3 storage documents: **NOT BACKED UP**).

## 7. The sequence at the GO (a procedure to be frozen, not performed)

1. The owner's GO to perform the time-stamping is recorded **separately** (not in this file), after every decision is confirmed and every condition verified.
2. The manifest is built from the then-current commits and verified (`build_manifest.py`, `verify_manifest.py`); its digest is recorded.
3. One request per authority is made for **the same digest**; each raw token is verified **offline** at its own signed time against an independently obtained trust anchor.
4. The package of section 6 is assembled and its digest recorded.
5. The package is preserved in the copies of Q6 and each copy is read back and cryptographically checked.
6. The evidence of each step is recorded; the records of this file are updated by their own reviewed changes.

## 8. What this does not show

* **The decisions are not confirmed**, and nothing here says that the owner has accepted them.
* **No provider's terms, access or trust chain was verified**: the statements about DigiCert and GlobalSign are the reviewer's reading of their public documentation, not checked here; the public DigiCert endpoint's terms of use were not found on 2026-11-03.
* **The check proves the structure and the evidence links**, not that a condition is true in the world: a verified condition is as strong as the evidence file it names.
* The dry-run manifest digest is not the manifest that will be time-stamped.
* **The exact proof depends on the 92 records being all that matters**; the template releases and the three stamped releases are outside it, and the ended template releases cannot be repaired by any stamp (the expiry assessment).
