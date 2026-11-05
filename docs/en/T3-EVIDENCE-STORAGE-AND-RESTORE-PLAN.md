# T3 time evidence: the storage and restore plan for the independent copy

Status: **plan only**, 2026-11-05. Documentation only. **Nothing is uploaded, no provider, account, region, bucket or permission is chosen or approved, and no secret or credential appears here.** The state of the second copy is, and stays, **NOT BACKED UP** until the conditions of section 8 are met. This plan does not touch the evidence directory it protects (`evidence/time/digicert-2026-11-03/`, merged in #32), so the archive of it stays what it was built from.

## 1. What is to be protected, and why it cannot be redone

The RFC 3161 time stamps of three signed release records (v0.2.1, v0.2.0, v0.1.5), obtained on 2026-11-03 before the signing chain ends on 2026-12-31 around 13:22 UTC. They prove that each record's digest existed no later than the stated time. The proof **cannot be made again** after the chain has ended: a stamp obtained later says nothing about the record's existence on 2026-11-03. Losing the evidence, or being unable to show that it was not altered, loses that claim.

**The artifact.** `cic-primitives-t3-evidence-2026-11-03.tar.gz`, 721 205 bytes, SHA-256 `e1795fcf8543be8d5ea6f379672f3a7ba7a2d2d42c674113ba994c24a8cddab5`. It holds the evidence directory as merged (`manifest.json`, the requests and replies, the TSA chains, the four public CIC certificates, the DigiCert trust anchor, `verify.sh`, `README.md`), a git bundle of the repository history that `verify.sh` reads the records from (`cic-primitives-t3.bundle`, SHA-256 beginning `ddb0b6132b87`), and `ARCHIVE-VERIFY-MANIFEST.json` with the original release commits. It was verified locally, offline, in a fresh directory (`verify.sh --selftest`, every negative control caught). **That local archive lives under a temporary directory of one machine and is not a backup.**

**Data classification.** Everything in it is public: the repository `CentralInfraCore/cic-primitives` is public, the certificates and the time-stamp replies are public, and a pattern scan for tokens and private keys (Vault, GitHub, Anthropic and AWS key shapes, PEM private-key blocks, bearer tokens, password assignments) of the unpacked text files and of all 167 commits of the git bundle, run on 2026-11-05, found nothing. A pattern scan is not proof of absence; it is repeated before each upload (section 6). The requirement is therefore **integrity, availability and provenance** (that the bytes are the ones that were verified, that they survive, and that this can be shown), not confidentiality. The owner confirms this classification before the first upload (decision S1).

## 2. What it has to survive

| Failure | Why it is realistic |
|---|---|
| Loss, suspension or force-push of the GitHub repository or account | the repository is the only copy today |
| Loss of the machine that holds the verified archive | one machine, a temporary directory |
| Accidental deletion or overwrite in the new place | the usual way a backup is lost |
| Malicious or mistaken replacement of the archive with another | an altered archive that still unpacks |
| Silent bit rot in storage | years of retention |
| The provider's account closed, billing lapsed, the service withdrawn | a copy at one provider is one failure boundary |
| Tools obsolete or unavailable when it is needed (a different OpenSSL, no network, no original environment) | the claim may be checked years from now, offline |
| The knowledge of how to restore is lost | people change |

## 3. Requirements on the place (from the review of 2026-11-05)

1. **A failure boundary independent of GitHub**: a different organisation and different infrastructure from the one that hosts the repository.
2. **Encryption in transit and at rest**, and **controlled access**: named principals, least privilege, multi-factor authentication, a write identity that is separate from the read identity, and a recorded owner of the account. Since the data is public (section 1), client-side encryption is optional (decision S4); the access path and the immutability below are what protect the integrity.
3. **Protection against accidental deletion and unauthorised overwrite**: object versioning, and an immutability setting (write-once retention, compliance mode if the provider has it) for a retention period that covers the claim's useful life. A place that allows the archive to be replaced silently does not qualify.
4. **SHA-256 checked before and after the upload** against the recorded value, from the stored object and not from the local file.
5. **A documented recovery**, written down so that someone who was not here can do it (section 6).
6. **A restore drill** that proves the archive can be recovered from the place itself, not only uploaded (section 7).
7. **An exit path**: the data can be taken out in a standard form if the provider is left.

## 4. Candidate classes (no selection is made here)

| Class | Meets | Weakness |
|---|---|---|
| An S3-compatible object store of another provider, with versioning and Object Lock | 1, 3, 4, 5, 7; encryption; access control | one provider; billing and account risk; the retention period must be chosen |
| Offline media in another physical place (a write-once disc or a disk kept offline) | independent of every online service; immutable if write-once | the place and its custody are physical; the restore needs a person; ageing of the medium |
| A mirror in a second git forge | cheap; independent of GitHub | no immutability; history can be rewritten; a different failure boundary only if it is another operator |

**The recommended shape is two copies of two different classes** (an immutable object store and an offline medium), so that no single provider, account or process is a single point of failure. Which providers, accounts, regions, media and custodians: not decided and not approved. The facts the owner must supply are in section 9.

## 5. Chain of custody: what is recorded for each copy

A custody log (a table in the repository, kept next to this plan once a copy exists; no credential in it) with one row per copy and per verification:

| Field | Content |
|---|---|
| copy id | a stable label, for example `T3-COPY-A` |
| class and place | the class of section 4, the provider or place by name, the region, the account owner (no credential) |
| date and by whom | UTC, who performed it |
| archive SHA-256 | the value recorded in section 1, checked at this step |
| object identifier | the version id or the medium's identifier |
| retention and immutability | the retention period and the setting that enforces it |
| step | `uploaded`, `read back`, `restore drill`, `periodic check` |
| result | `pass` or `fail`, with the evidence |

A row is added at each step; a row is never edited, a correction is a new row.

## 6. The procedures (for the owner or a successor)

**Before the upload.** (1) Compute the SHA-256 of the archive and compare it with section 1. (2) Unpack it into an empty directory and run `bash evidence/time/digicert-2026-11-03/verify.sh --selftest` offline; it must end with every check holding and every negative control caught. (3) Scan it again for secrets. (4) Record the OpenSSL, tar and git versions used. Stop at the first failure.

**The upload.** (1) Use the write identity only. (2) Send the archive with an integrity header that carries its SHA-256 where the provider supports one. (3) Record the object identifier (the version id). (4) Set the retention and immutability; confirm that a delete and an overwrite are refused (a deliberate trial on a throw-away object, not on the archive).

**The read-back.** (1) With the **read** identity, fetch the stored object **by its version id** into a new, empty directory. (2) Compute its SHA-256 and compare it with section 1. (3) Compare the size. (4) Stop at the first difference and record the failure.

**The restore** (from the stored object only; in a directory and a user not used for the build). The commands below were run once in a clean directory on the build machine, with a minimal `PATH`, as a **dry run of the procedure**; that is not a restore drill from storage, because nothing is stored. The order matters, and the Git history is part of it, because the verifier reads the old release commits with `git cat-file` and `git show`.

```
 1. sha256sum -c cic-primitives-t3-evidence-2026-11-03.tar.gz.sha256       # the archive is the recorded one (also compare the value with section 1)
 2. mkdir unpacked && tar xzf cic-primitives-t3-evidence-2026-11-03.tar.gz -C unpacked
 3. check every file against unpacked/ARCHIVE-VERIFY-MANIFEST.json ("files_sha256": 18 entries, the bundle included)
 4. git init -q repo && cd repo                                            # a repository must exist before a bundle can be verified
 5. git bundle verify ../unpacked/cic-primitives-t3.bundle                 # "okay": the bundle is complete and self-consistent
 6. git fetch -q ../unpacked/cic-primitives-t3.bundle 'refs/*:refs/*'       # the local Git environment: refs/remotes/origin/devel and the three release tags
 7. for each of the three commits in ARCHIVE-VERIFY-MANIFEST.json:  git cat-file -e <commit>^{commit}     # reachable
    and  git show <commit>:<record_path> | sha256sum   equals "record_sha256" of the manifest
 8. bash ../unpacked/evidence/time/digicert-2026-11-03/verify.sh --selftest # run from inside repo/: it must end with "ALL CHECKS HOLD" and exit 0
```

The dry run: the archive hash matched, all 18 files matched the manifest, the bundle verified (SHA-1 object format), the three commits were reachable, the record `v0.2.1` read from Git had the SHA-256 the manifest names, and `verify.sh --selftest` ended with `ALL CHECKS HOLD`.

**The dependencies of the verifier, taken from `verify.sh` itself** (not only OpenSSL): `bash`; `openssl` (`ts -verify`, `verify -attime`, certificate reading; 3.0.13 was used); `git` (`init`, `fetch`, `bundle verify`, `cat-file`, `show`; 2.43.0); `python3` **with PyYAML** (it reads the certificates out of the record and the JSON manifest; 3.12.3 and PyYAML 6.0.1); **GNU** `date -d`, `sha256sum`, `mktemp`, `cut`, `cat`, `cp`, `rm`, `printf`, `sed`, `env`, `dirname` (coreutils 9.4; a BSD `date` does not accept `-d`), `find` (findutils) and `cmp` (diffutils); `tar` and `gzip` for unpacking (tar 1.35). `verify.sh` contains no network command (read in full: no `curl`, `wget` or the like) and takes the time from the token, not from the machine's clock. The exact versions used are written into the custody log at each restore. A different version that fails is a finding to record, not a reason to edit the archive. Because the dependencies are several tools, a fresh machine needs all of them, and the successor has to be told so.

**The knowledge must not live only in the repository.** A copy of this section (the commands and the dependency list) is stored **beside the archive as a separate small object** with its own recorded SHA-256, so that someone with nothing but the store can restore. The archive itself is not modified.

**The reference must not live only in the repository either.** The SHA-256 proves that the stored bytes equal the recorded bytes; where the recorded value comes from is a separate question. If the approved archive hash and the custody log lived only in the GitHub repository, a loss of that repository would take the reference with it. So the approved hash (section 1), the custody log and this section are also kept in **at least one independent, protected place**: as a separate versioned object in the store, and in the label or sleeve of the offline medium (the hash and the date, written by hand). The independent copy of the log is appended to at each step like the log itself (decision S9).

## 7. The restore drill and the periodic check

* **The first drill** is part of acceptance (section 8): it is done by a person other than the one who uploaded, or at least on a different machine and account, from the stored object only.
* **The periodic check**: the SHA-256 of the stored object by version id every six months, a full restore every twelve months, and one full restore before 2026-12-31 and again at the first working day after the chain's end, because the claim matters most when the chain has ended. Each check is a row of the custody log. A failed check is handled as an incident: the other copy is read, the failed one is replaced from it, and the cause is recorded.
* **Staleness.** A copy whose last passed restore drill is older than the interval is `BACKED UP (stale)`, not `BACKED UP`.

## 8. The states, and when the copy counts as backed up

| State | Meaning |
|---|---|
| `NOT BACKED UP` | no independent copy exists, or none has passed a restore drill from the stored object (**today**) |
| `UPLOADED (unverified)` | an object exists in the place; the read-back has not passed |
| `BACKED UP` | one independent copy has passed the read-back and a restore drill from the stored object, its custody log is complete, and the drill is not stale |
| `BACKED UP (stale)` | as above, with a restore drill older than the interval |
| `BACKED UP (two classes)` | two copies of different classes each in the state `BACKED UP` (the recommended end state) |

The second copy required by the decision of 2026-11-03 is satisfied by `BACKED UP`, and a stronger claim is made only for `BACKED UP (two classes)`.

## 9. Decisions asked of the owner (none is taken here)

| # | Decision |
|---|---|
| S1 | Confirm the classification of section 1: the archive holds only public data; integrity, availability and provenance are the requirements, confidentiality is not |
| S2 | The class or classes of section 4, and the recommended shape of two copies of two classes |
| S3 | The concrete place: provider or medium, region, account owner, who may write and who may read, the multi-factor setting, and the budget. **No provider, account or permission is approved by this plan.** |
| S4 | Client-side encryption of the archive: yes or no, and if yes who holds the key and how a lost key is survived (a lost key is a new failure mode for data that is public) |
| S5 | The retention period and the immutability setting |
| S6 | The checking cadence of section 7 and who performs it |
| S7 | The custody log: version-controlled, append-only (the position taken in the review); who may add rows |
| S9 | How the independent copy of the approved hash, the custody log and the restore commands is kept (section 6): where, who may append, and how it is checked against the repository copy |
| S8 | The open question of the DigiCert public endpoint's terms of use (recorded in the evidence README) is unaffected by this plan and stays open |

**Positions recorded in the review of #33.** S1: accepted in principle, with a new scan before every upload. S2: accepted (an immutable object store and an offline copy). S3: HOLD, nothing is selected. S4: client-side encryption is not mandatory for this public archive. S5: durable multi-year retention; the concrete immutability period is still to be decided. S6: accepted (hash every six months, restore every year, extra drills around the chain's end). S7: accepted (version-controlled, append-only), the way an independent copy of the log is kept still to be fixed (S9). S8: open, not solved by a backup. None of this selects a provider, approves access, or allows an upload.

## 10. Not claimed

That any copy exists beyond the repository and the temporary local archive; that any provider, account or place is approved; that the archive survives the failures of section 2; the authenticity of any release, the trust anchor, or the signer's authority (the evidence proves existence no later than a time, nothing more). Until section 8 is met the state of the second copy is **NOT BACKED UP**.
