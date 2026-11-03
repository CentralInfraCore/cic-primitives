# Time evidence for three signed cic-primitives release records (2026-11-03)

RFC 3161 time-stamp tokens from the DigiCert public time-stamp authority over the SHA-256 of the three signed release records `v0.2.1`, `v0.2.0` and `v0.1.5`, obtained on 2026-11-03.

**Why now.** Every certificate of the signing chain of these records (Developer CA, Source CA, the developer's certificate; the root a few hours later) ends on 2026-12-31 around 13:22 UTC, and the present verifier judges validity at the moment of checking, so from 2027-01-01 it refuses these records. Evidence that a record existed *before* the chain ended has to be made *before* it ends; a token obtained in 2027 would only show a date after the end. See `docs/P5-TRUST-MODEL-PLAN.md` of cic-primitive-forms (section 4).

| Release | Record SHA-256 | Time stamp (UTC) |
|---|---|---|
| v0.2.1 | `e5d8268aede0d24f02e60a151099a2fdc7615172ed3105b0a05b6b5d19addf63` | 2026-11-03 22:07:48 |
| v0.2.0 | `955fab2d6d9638c773f29fbe97a3279f9f10b9539c4e3e79957df0acef9a57a6` | 2026-11-03 22:09:44 |
| v0.1.5 | `284e44bfcf62d79f782d6cae359c4c99ef2f5297f6f71dcea52a95d28b8c4456` | 2026-11-03 22:09:45 |

## Check it

From a clone of cic-primitives that has the full history (the records are read from git at their release commits):

```
bash evidence/time/digicert-2026-11-03/verify.sh --selftest
```

It reads the time of each stamp **from the token** (the signed time; the manifest value is only compared with it) and runs **every** token check at that time, so a later end of the TSA chain, or the clock of the machine, changes nothing. It checks the trust anchor and the kept CIC certificates against the figures in `manifest.json`, the record against its digest, the token against the request and against the record file, and **that the stamp lies inside the validity of the developer certificate, the Developer CA, the Source CA and the root of the CIC chain**, twice (`openssl verify -attime` over both chains, and plain arithmetic on the dates), and that the kept CIC certificates are the ones the records carry. With `--selftest` it also shows that a record changed by one byte, a wrong anchor, a stamp after the end of the CIC chain, a stamp before it began, a stamp when only some of the CIC certificates are still valid, and a wrong issuer of the developer certificate are all refused. It needs `openssl`, `git` and `python3` with PyYAML, and no network. Exit status 0 only if every check holds.

## What is here

* `manifest.json`: for each release the record (commit, path, SHA-256), the request (SHA-256, nonce), the response (SHA-256, status, serial, policy, time, nonce), and the trust anchor with the sources it was checked against.
* `<release>/request.tsq`, `response.tsr`, `tsa-chain.pem`: the request that was sent (70 bytes: algorithm, digest, nonce, "send the TSA certificate"), the reply, and the three certificates the reply carries.
* `cic-chain/`: the four public certificates of the CIC chain that signed the records: developer, Developer CA (**not carried by any record**), Source CA, root. With their validity they are what shows that the stamp was made while the chain was valid.
* `trust-anchor/DigiCert_Trusted_Root_G4.pem`: the **self-signed** DigiCert Trusted Root G4, SHA-256 `55:2F:7B:DC:F1:A7:AF:9E:6C:E6:72:01:7F:4F:12:AB:F7:72:40:C7:8E:76:1A:C2:03:D1:D9:D2:0A:C8:99:88`, valid to 2038-01-15. It was taken from the operating system store (an independent source) and its SHA-256, SHA-1 and serial equal those DigiCert publishes. The reply also carries a *cross-signed* copy of this root (valid to 2031); that one is not used as the anchor.

## What it proves, and what it does not

It proves that each digest existed **no later than** the stated time, according to the DigiCert time-stamp authority, and that the token is bound to the request that was sent (nonce) and to the exact bytes of the record.

It does **not** prove who signed the record, that the signature was valid on that day, that the signer was allowed to sign, that the countersignature authorizes anything, that the release is genuine, or that the records were *signed* at that time rather than only existing. It does not replace a trust anchor for the release chain, a revocation rule or a policy (`docs/P5-TRUST-MODEL-PLAN.md`, conditions C1 to C6); it supplies the one piece that could not be made late: independent evidence of existence before the end of the chain.

## Limits to keep in view

* The trust in the time rests on DigiCert and on the self-signed root above; the trust anchor was checked against the operating system store and against the publisher's page, not against a third independent party.
* No terms of use for the public endpoint were found (the documentation describes it for code signing and states neither permission nor restriction for other use). Only digests were sent. Another authority needs a new decision.
* The requests were made over plain HTTP (port 443 did not answer from that machine); the replies are signed, so this does not weaken the check.
* OpenSSL `ts -verify` was used; the tokens and the anchor are kept so any other RFC 3161 verifier can be applied later.
* **A second, independent copy of this directory is required by the decision and does not exist yet.** The GitHub repository is one copy; where the second lives is for the owner to name, and it is not recorded here until it exists.
