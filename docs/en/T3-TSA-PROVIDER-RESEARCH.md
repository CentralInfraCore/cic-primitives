# T3 time-stamp authorities: the read-only research of DigiCert and GlobalSign (2026-11-23)

**Scope and limits.** This is the one authorisation the owner's statement of 2026-11-23 gave: a **read-only** study of the providers' terms, RFC 3161 compatibility, trust anchors, TSA chains and access conditions. **Nothing was requested from either authority**: no time-stamp request, no account, no purchase, no contact, no key. The result is **not an automatic fulfilment of a condition**: where the evidence is missing, the condition stays `open`. The data are in `docs/design/time-evidence/t3-tsa-research.yaml`; the check is `docs/evidence/time-tsa-research/check_tsa_research.py` (self-test: `selftest_tsa_research.py`, 17 checks, results under `results/`).

**Method.** Each finding names a source (URL, retrieval date 2026-11-23, SHA-256 prefix of the retrieved bytes; the pages themselves are not stored, only short excerpts), a verdict (`supports`, `contradicts`, `silent`, `unclear`), the limits of what it shows, and whether it is **decisive** (answers the condition itself). A condition is `supported` only if **all** its findings support, **one is decisive and from a primary source** (the provider's own page); a search-engine summary can never support anything. The check derives the status and compares it with the record; the readiness record may mark a C-Q2-* condition `verified` only if the research says `supported`.

## 1. Result

| Condition | Result | Why |
|---|---|---|
| C-Q2-1 DigiCert RFC 3161 compatibility | **supported, verified in the readiness record** | DigiCert's own page documents an RFC 3161 server (`http://timestamp.digicert.com`); the three tokens of 2026-11-03 show the request form we use is accepted |
| C-Q2-2 DigiCert chain and independent anchor for the **new** tokens | **open** | the PUBLISHED chain verifies (below), but the condition is about the new tokens, which exist only after the GO; closed at the capture (C-CAP-1) |
| C-Q2-3 DigiCert terms and permission | **open** | the sources are **silent**: no terms of use, permission or limit for the public endpoint; the absence is neither permission nor prohibition |
| C-Q2-4 GlobalSign RFC 3161 compatibility | **open** | a marketing page and a reseller's reproduction of a notice; the request form was not tested |
| C-Q2-5 GlobalSign chain and anchor | **open** | the R45 time-stamping CA is named; no certificate or root was obtained |
| C-Q2-6 GlobalSign terms, eligibility, access | **open** | a commercial account/purchase flow; the terms of using the endpoint were not found |
| C-Q2-7 independence of the two | **open** | different names and hierarchies only; ownership and shared infrastructure not examined |

**One of seven conditions is closed by the research; six stay open.** That is the honest result: the research cannot show GlobalSign usable, and neither provider's permission for this use.

## 2. DigiCert

* **Endpoint.** The knowledge base page (INFO4231) documents the RFC 3161 server at `http://timestamp.digicert.com` and links five certificates: three responders (SHA-256, SHA-384, SHA-512, generation 2026), the time-stamping CA `DigiCert Trusted G4 TimeStamping RSA4096 SHA256 2025 CA1`, and a file called `DigiCertTrustedRootG4.cer`.
* **Chain, verified locally.** All five were downloaded and are kept in `docs/evidence/time-tsa-research/digicert/`. With OpenSSL the three responders verify for the purpose `timestampsign` through the CA to the **self-signed DigiCert Trusted Root G4**, the anchor kept on 2026-11-03 (SHA-256 `55:2F:7B:DC:…:C8:99:88`, pinned in the check). **A trap:** the file the page calls `DigiCertTrustedRootG4.cer` is the **cross-signed** root (issuer DigiCert Assured ID Root CA, valid only to 2031-11-09, a different fingerprint). It is not the anchor; the check pins the real one. **Measured weakness of the tool:** OpenSSL 3.5 accepts a non-self-signed CA as a trust anchor, so a chain check alone would pass with a swapped anchor; the self-test plants exactly that and the pin catches it.
* **Terms.** The page states no terms, permission or limit. DigiCert's CPS v6.01 is about certificates; it names time-stamp token requesters and verifiers as parties but contains no permission or restriction for the public endpoint. The DigiCert Europe Time-Stamp Policy v3.0 describes a **different** service (the DCEU-TSA, whose subscribers have an agreement with DigiCert Europe), not the public endpoint.
* **Access and lifetime.** No account, credential or fee is mentioned, and the tokens of 2026-11-03 needed none (past behaviour). Future availability and rate limits are not stated. The page says TSA certificates are renewed at least every 15 months while the 2026 responder certificates are valid 2026-08-05 to 2037-11-04: **not reconciled by the sources**, so the verification procedure must keep the responder certificate of each token.

## 3. GlobalSign

* **Product.** GlobalSign's page advertises an enterprise time-stamping service "built on RFC 3161", integrated by a REST API or, for code-signing customers, a secure URL; it is a purchase flow (an account, a price per year). A marketing claim, not decisive.
* **Endpoint.** A **reseller** (TBS CERTIFICATES) reproduces GlobalSign's December 2025 notice: the RFC 3161 URL is `http://timestamp.globalsign.com/tsa/r45standard`, issued by `GlobalSign Offline R45 Timestamping CA 2025`; from 2026-03-04 the older URLs (`…/tsa/r6advanced1`) redirect to it. **Secondary source**; GlobalSign's own page for the notice was not located; the endpoint was not contacted.
* **Chain and anchor.** Named, **not obtained**.
* **Terms.** The Subscriber Agreement for TimeStamping and TimeAuthority Certificates (v1.0, read) concerns **certificates issued to a subscriber**, not use of the time-stamp service. A web search showed terms of a Japanese accredited product that ask customers not to share the URL or credentials and set a request rate; that is a **search summary of a different product, not read and not relied on** (a search result can never support a finding). Whether a non-code-signing customer may use the endpoint for this purpose, at what cost and limit, is **unknown**.

## 4. What this does not show, and what comes next

* Nothing was asked of either provider; **permission, cost and limits remain unknown** for both. The sources being silent does not make the use allowed.
* The researched pages are **not archived** (their SHA-256 prefixes are recorded); the certificates are. A reviewer who repeats the retrieval may find changed pages.
* The independence of the authorities (C-Q2-7) is not examined beyond names and hierarchies.
* **To close the open conditions** an owner action is needed: contact the providers (or accept the use of the public endpoint without a written permission, a decision for the owner), and for GlobalSign obtain the R45 chain from GlobalSign's own repository. Those are outside the read-only authorisation and are **not started**.
* The storage decision (S3/S10) that the staged order requires before any GO is a separate piece of preparation; nothing is provisioned.
