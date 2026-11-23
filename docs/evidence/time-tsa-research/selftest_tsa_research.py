#!/usr/bin/env python3
"""Self-test of check_tsa_research.py: the real record is valid; every planted fault is reported with the intended label (FAIL-EXPECT); the chain check is shown to fail
on a corrupted responder and on a swapped anchor; infrastructure errors are exit 2, never a detection."""
import copy, os, shutil, subprocess, sys, tempfile, yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_tsa_research as C

ANCHOR0 = C.ANCHOR
rec0 = yaml.safe_load(open(C.REC, encoding="utf-8")); ready0 = yaml.safe_load(open(C.READY, encoding="utf-8"))
bad = 0
def report(name, ok, extra=""):
    global bad
    print("%-110s %s %s" % (name, "OK" if ok else "FAIL", extra)); bad += 0 if ok else 1
def find(r, i): return next(f for f in r["findings"] if f["id"] == i)
def cond(r, i): return next(c for c in r["conditions"] if c["id"] == i)

errs = C.check_record(copy.deepcopy(rec0), copy.deepcopy(ready0))
report("A real record: valid, no detection", errs == [], str(errs)[:80])
out = []; C.check_record(copy.deepcopy(rec0), None, chain=False, out=out)
report("A derived: exactly C-Q2-1 supported, the other six open (nothing is promoted by inference)", [o for o in out if o.endswith("supported")] == ["C-Q2-1 supported"] and len(out) == 7, str(out))

def planted(name, mut, needle, ready=None, chain=False):
    r = copy.deepcopy(rec0); mut(r)
    e = C.check_record(r, copy.deepcopy(ready if ready is not None else ready0), chain=chain)
    report("B planted: %s" % name, any(needle in x for x in e), "FAIL-EXPECT %s" % needle if any(needle in x for x in e) else str(e)[:90])
planted("a finding from a search result supports", lambda r: find(r, "R-GS-04").update(source="S-GS-SEARCH", verdict="supports"), "finding.search-support.R-GS-04")
planted("a condition marked supported on silent findings", lambda r: cond(r, "C-Q2-3").update(status="supported"), "condition.status.C-Q2-3")
planted("C-Q2-1 marked open although its decisive primary finding supports", lambda r: cond(r, "C-Q2-1").update(status="open"), "condition.status.C-Q2-1")
planted("a marketing (non-decisive) finding promoted to decisive", lambda r: find(r, "R-GS-01").update(decisive=True) or cond(r, "C-Q2-4").update(status="open"), "condition.status.C-Q2-4")
planted("a finding of the primary DigiCert page turned silent, the condition left supported", lambda r: find(r, "R-DC-01").update(verdict="silent"), "condition.status.C-Q2-1")
planted("a finding with an unknown source", lambda r: find(r, "R-DC-03").update(source="S-NOPE"), "finding.source.R-DC-03")
planted("a finding with an unknown verdict", lambda r: find(r, "R-DC-03").update(verdict="probably"), "finding.verdict.R-DC-03")
planted("a finding without an excerpt", lambda r: find(r, "R-DC-03").update(excerpt=""), "finding.excerpt.R-DC-03")
planted("a condition naming an unknown finding", lambda r: cond(r, "C-Q2-3").update(findings=["R-XX"]), "condition.dangling.C-Q2-3")
planted("a source that is not https", lambda r: r["sources"]["S-DC-KB"].update(url="http://x"), "source.url.S-DC-KB")
planted("a duplicate finding id", lambda r: r["findings"].append(copy.deepcopy(find(r, "R-DC-03"))), "finding.dup.R-DC-03")
def ready_verified(i):
    r = copy.deepcopy(ready0); next(c for c in r["conditions"] if c["id"] == i)["status"] = "verified"; return r
planted("the readiness record marks C-Q2-3 verified while the research is silent", lambda r: None, "ready.unsupported.C-Q2-3", ready=ready_verified("C-Q2-3"))

# the chain check: a corrupted responder, a swapped anchor
tmp = tempfile.mkdtemp(); shutil.copytree(C.CHAIN, os.path.join(tmp, "digicert"))
f = os.path.join(tmp, "digicert", "DigiCertSHA256RSA4096TimestampResponder20261.cer"); b = bytearray(open(f, "rb").read()); b[600] ^= 1; open(f, "wb").write(bytes(b))
C.CHAIN = os.path.join(tmp, "digicert")
e = C.check_record(copy.deepcopy(rec0), None, chain=True)
report("C planted: a responder certificate with one flipped byte fails the chain check", any(x.startswith("chain.") and "SHA256" in x or "chain.parse.SHA256" in x or "chain.verify.SHA256" in x for x in e), "FAIL-EXPECT chain.*.SHA256" if e else "no detection")
shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), "digicert", "DigiCertSHA256RSA4096TimestampResponder20261.cer"), f)
C.ANCHOR = os.path.join(tmp, "digicert", "DigiCertTrustedG4TimeStampingRSA4096SHA2562025CA1.pem")   # a swapped anchor: the CA instead of the root
e = C.check_record(copy.deepcopy(rec0), None, chain=True)
report("C planted: an anchor that is not the self-signed root fails the chain check", any(x.startswith("chain.anchor-pin") for x in e), "FAIL-EXPECT chain.anchor-pin" if e else "no detection")
open(os.path.join(tmp, "digicert", "DigiCertSHA256RSA4096TimestampResponder20261.cer"), "wb").write(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "digicert", "DigiCertSHA256RSA4096TimestampResponder20261.cer"), "rb").read())
rootf = os.path.join(tmp, "digicert", "DigiCertTrustedRootG4.cer"); open(rootf, "w").write("not a certificate\n")
C.ANCHOR = ANCHOR0
e = C.check_record(copy.deepcopy(rec0), None, chain=True)
report("C planted: the page's root file unreadable is a detection, not a skipped rule", any(x.startswith("chain.cross-root") for x in e), "FAIL-EXPECT chain.cross-root" if e else "no detection")
shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), "digicert", "DigiCertTrustedRootG4.cer"), rootf)
shutil.rmtree(tmp)

# D: infrastructure is exit 2
env = dict(os.environ, PATH="/nonexistent")
r = subprocess.run(["/usr/bin/python3", os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_tsa_research.py")], env=env, capture_output=True, text=True)
report("D infra: no openssl on the PATH is exit 2, not a detection", r.returncode == 2 and "FAIL" not in r.stdout, "exit=%d" % r.returncode)
print("self-test: %s" % ("all as expected" if not bad else "%d problem(s)" % bad))
sys.exit(1 if bad else 0)
