#!/usr/bin/env python3
"""Checks the read-only TSA research record (docs/design/time-evidence/t3-tsa-research.yaml). Nothing here contacts a time-stamp authority.
Rules: sources typed; every finding names a source and a verdict, has an excerpt; a search-result source can never support; a condition is `supported` only if
ALL its findings support and at least one is DECISIVE (`decisive: true`: it answers the condition itself, not a neighbouring question) and from a primary source (derived, compared with the record's status); the DigiCert chain files are re-verified with
openssl (responder -> CA -> self-signed root, purpose timestampsign) against the anchor kept on 2026-11-03; the readiness record may mark a C-Q2-* condition
`verified` only if the research says `supported`. Exit: 0 ok, 1 detection, 2 infrastructure."""
import os, subprocess, sys, yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REC = os.path.join(ROOT, "docs/design/time-evidence/t3-tsa-research.yaml")
READY = os.path.join(ROOT, "docs/design/time-evidence/t3-execution-prerequisites.yaml")
CHAIN = os.path.join(HERE, "digicert")
ANCHOR_FPR = "sha256 Fingerprint=55:2F:7B:DC:F1:A7:AF:9E:6C:E6:72:01:7F:4F:12:AB:F7:72:40:C7:8E:76:1A:C2:03:D1:D9:D2:0A:C8:99:88"   # DigiCert Trusted Root G4, the anchor kept on 2026-11-03
ANCHOR = os.path.join(ROOT, "evidence/time/digicert-2026-11-03/trust-anchor/DigiCert_Trusted_Root_G4.pem")
VERDICTS = {"supports", "contradicts", "silent", "unclear"}
TYPES = {"primary", "secondary", "search_result"}


class Infra(Exception):
    pass


def openssl(*a):
    try:
        return subprocess.run(["openssl"] + list(a), capture_output=True, text=True)
    except OSError as e:
        raise Infra("openssl unavailable: %s" % e)


def fpr(path, inform="PEM"):
    r = openssl("x509", "-inform", inform, "-in", path, "-noout", "-fingerprint", "-sha256")
    return r.stdout.strip() if r.returncode == 0 else None


def derive(cond, findings, sources):
    fs = [findings.get(i) for i in cond.get("findings", [])]
    if not fs or any(f is None for f in fs):
        return "open"
    if any(f["verdict"] != "supports" for f in fs):
        return "open"
    return "supported" if any(sources[f["source"]]["type"] == "primary" and f.get("decisive") is True for f in fs) else "open"


def check_record(rec, ready=None, chain=True, out=None):
    errs = []
    bad = lambda k, m: errs.append("%s: %s" % (k, m))
    srcs = rec.get("sources") or {}
    for i, s in srcs.items():
        if s.get("type") not in TYPES: bad("source.type.%s" % i, "unknown type %r" % s.get("type"))
        if not str(s.get("url", "")).startswith("https://"): bad("source.url.%s" % i, "not an https URL")
        if not str(s.get("sha256", "")).strip(): bad("source.sha256.%s" % i, "no digest")
    findings = {}
    for f in rec.get("findings") or []:
        if f.get("id") in findings: bad("finding.dup.%s" % f.get("id"), "duplicate id")
        findings[f.get("id")] = f
        if f.get("source") not in srcs: bad("finding.source.%s" % f.get("id"), "unknown source"); f["source"] = None
        if f.get("verdict") not in VERDICTS: bad("finding.verdict.%s" % f.get("id"), "unknown verdict")
        if not str(f.get("excerpt", "")).strip() or not str(f.get("limits", "")).strip(): bad("finding.excerpt.%s" % f.get("id"), "an excerpt and the limits are required")
        if f.get("source") and srcs[f["source"]].get("type") == "search_result" and f.get("verdict") == "supports":
            bad("finding.search-support.%s" % f.get("id"), "a search result cannot support a finding")
    ok_srcs = {k: v for k, v in srcs.items() if v.get("type") in TYPES}
    res = {}
    for c in rec.get("conditions") or []:
        if any(i not in findings for i in c.get("findings", [])): bad("condition.dangling.%s" % c["id"], "names an unknown finding"); continue
        if any(findings[i]["source"] is None for i in c.get("findings", [])): continue
        d = derive(c, findings, ok_srcs)
        res[c["id"]] = d
        if c.get("status") != d: bad("condition.status.%s" % c["id"], "record says %r, the evidence derives %r" % (c.get("status"), d))
    if chain:
        a = fpr(ANCHOR)
        if not a: bad("chain.anchor", "the kept anchor is unreadable")
        elif a != ANCHOR_FPR: bad("chain.anchor-pin", "the anchor is not the pinned DigiCert Trusted Root G4 (OpenSSL 3 accepts a non-self-signed CA as a trust anchor, so the pin is what makes the chain end in the root)")
        else:
            sj = openssl("x509", "-in", ANCHOR, "-noout", "-subject", "-issuer").stdout.split("\n")
            if len(sj) < 2 or sj[0].split("=", 1)[1:] != sj[1].split("=", 1)[1:]: bad("chain.anchor-selfsigned", "the anchor is not self-signed")
        ca = os.path.join(CHAIN, "DigiCertTrustedG4TimeStampingRSA4096SHA2562025CA1.pem")
        for n in ("SHA256", "SHA384", "SHA512"):
            resp = os.path.join(CHAIN, "DigiCert%sRSA4096TimestampResponder20261.cer" % n)
            pem = openssl("x509", "-inform", "DER", "-in", resp)
            if pem.returncode != 0: bad("chain.parse.%s" % n, "responder unreadable"); continue
            tmp = resp + ".tmp.pem"
            open(tmp, "w").write(pem.stdout)
            try:
                r = openssl("verify", "-purpose", "timestampsign", "-CAfile", ANCHOR, "-untrusted", ca, tmp)
            finally:
                os.remove(tmp)
            if r.returncode != 0 or ": OK" not in r.stdout: bad("chain.verify.%s" % n, (r.stdout + r.stderr).strip()[:100])
        cross = fpr(os.path.join(CHAIN, "DigiCertTrustedRootG4.cer"), "DER")
        if cross and a and cross == a: bad("chain.cross-root", "the page's root file equals the anchor: expected the cross-signed root")
    if ready is not None:
        for c in ready.get("conditions", []):
            if c["id"].startswith("C-Q2-") and c.get("status") == "verified" and res.get(c["id"]) != "supported":
                bad("ready.unsupported.%s" % c["id"], "verified in the readiness record, but the research does not support it")
    if out is not None:
        for k in sorted(res): out.append("%s %s" % (k, res[k]))
    return errs


def main():
    try:
        rec = yaml.safe_load(open(REC, encoding="utf-8")); ready = yaml.safe_load(open(READY, encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        print("infrastructure: %s" % e); return 2
    out = []
    try:
        errs = check_record(rec, ready, out=out)
    except Infra as e:
        print("infrastructure: %s" % e); return 2
    for l in out: print(l)
    for e in errs: print("FAIL " + e)
    print("T3 TSA research: %s" % ("INVALID" if errs else "valid (conditions derived above; a supported condition is not a satisfied one without the readiness record)"))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
