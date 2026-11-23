"""Check of the expiry inventory against the review document and the evidence that is in THIS repository. An ISOLATED check, not a CI gate; it changes nothing, stamps nothing, signs nothing.
Checks (a failure is a FAIL-EXPECT line, exit 1; an unreadable input is INCOMPLETE, exit 2, never a result):
  chain       the four chain certificates of the inventory equal, by dates and fingerprint, the certificates kept in evidence/time/digicert-2026-11-03/cic-chain (openssl reads them again)
  consistent  every registry record names the Source CA whose end is the end of the kept Source CA; the three stamped releases of the manifest are tags of the inventory
  verifiers   the claims about the three verifiers rest on the recorded anchors: the registry verifier has NO time word (0 lines), the primitives verifier reads the clock (lines recorded), the Relay chain
              verification builds x509.VerifyOptions WITHOUT CurrentTime; a changed anchor changes the claim and fails here
  doc         the tables of the review document are exactly the tables rendered from the inventory and the manifest (nothing is hand-edited into them)
Usage: check_inventory.py [--render] [--inventory PATH] [--doc PATH] [--manifest PATH] [--chain DIR]"""
import json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
INV = os.path.join(HERE, "results", "inventory.json")
DOC = os.path.join(REPO, "docs", "en", "T3-EXPIRY-RISK-ASSESSMENT-AND-DECISION-PLAN.md")
MANIFEST = os.path.join(REPO, "evidence", "time", "digicert-2026-11-03", "manifest.json")
CHAIN = os.path.join(REPO, "evidence", "time", "digicert-2026-11-03", "cic-chain")
MARK = {"chain": ("<!-- BEGIN CHAIN TABLE -->", "<!-- END CHAIN TABLE -->"), "records": ("<!-- BEGIN RECORDS TABLE -->", "<!-- END RECORDS TABLE -->"), "verifiers": ("<!-- BEGIN VERIFIER TABLE -->", "<!-- END VERIFIER TABLE -->")}
fails = []


def expect(label, cond, detail=""):
    if not cond:
        fails.append(label); print("FAIL-EXPECT %s %s" % (label, detail))


def arg(argv, name, default):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else default


def cert_dates(path):
    r = subprocess.run(["openssl", "x509", "-in", path, "-noout", "-enddate", "-startdate", "-fingerprint", "-sha256"], capture_output=True, text=True)
    g = lambda k: (re.search(k + r"=\s*(.*)", r.stdout) or [None, None])[1]
    return g("notBefore"), g("notAfter"), g("sha256 Fingerprint")


def stamped_releases(manifest):
    return sorted(s["release"] for s in manifest["stamps"])


def classify(inv, manifest):
    """each tag record -> (class, stamped?)"""
    stamps = set(stamped_releases(manifest))
    rows = []
    for t in inv["tag_records"]:
        f = t.get("file") or ""
        if "tests/fixtures" in f:
            continue                                                             # a TEST ONLY fixture, not a release
        m = re.search(r"cic-primitives-(v\d+\.\d+\.\d+)\.yaml$", f)
        rel_of_tag = re.search(r"@(v\d+\.\d+\.\d+)$", t["tag"])
        own = bool(m and rel_of_tag and m.group(1) == rel_of_tag.group(1) and t["repo"] == "cic-primitives")      # the record the tag itself releases (not a copy carried along)
        if t["repo"] == "cic-primitives" and own:
            rows.append((t, "primitives release record", m.group(1) in stamps))
        elif t["repo"] == "cic-yang" and re.search(r"cic-yang-v", f):
            rows.append((t, "cic-yang release record", False))
        elif t["repo"] == "base-repo":
            rows.append((t, "template release (project.yaml)", False))
    return rows


def render(inv, manifest):
    chain = ["| Certificate | Subject | Not after (UTC) | SHA-256 fingerprint |", "|---|---|---|---|"]
    for c in sorted(inv["chain"], key=lambda c: c["file"]):
        chain.append("| `%s` | %s | %s | `%s` |" % (c["file"], c["subject_cn"], c["not_after"], c["sha256"]))
    reg = inv["registry"]; cls = classify(inv, manifest)
    rec = ["| Class | Records | External time evidence (RFC 3161) | Note |", "|---|---|---|---|",
           "| cic-schema-registry (main @ `%s`), countersigned records | %d | **none** | countersign `ts` %s to %s (the countersigning service's own clock, not covered by any signature); %d distinct build hashes |" % (inv["clones"]["cic-schema-registry"]["head"][:12], reg["records"], reg["ts_min"], reg["ts_max"], reg["unique_build_hash"])]
    for (cname, ) in (("primitives release record",), ("cic-yang release record",), ("template release (project.yaml)",)):
        rows = [r for r in cls if r[1] == cname]
        if cname == "template release (project.yaml)":
            for t, _, st in rows:
                rec.append("| template release `%s` | 1 | none | %s |" % (t["tag"], "signature block under project.yaml; build timestamp %s; declared validity until %s; developer certificate end: %s" % (t.get("ts") or "none", t.get("declared_validity_until") or "none declared", t.get("developer_not_after") or "not extracted by the inventory") if t["format"] == "template-project-yaml" else "no signature block found by the inventory"))
            continue
        stamped = [r for r in rows if r[2]]
        rec.append("| %s (%s) | %d | %s | tags %s |" % (cname, rows[0][0]["repo"] if rows else "-", len(rows), ("**%d of %d** (DigiCert, 2026-11-03)" % (len(stamped), len(rows))) if stamped else "**none**", ", ".join("`%s`" % r[0]["tag"] for r in rows)))
    ver = ["| Verifier | Reads the clock? | Evidence (recorded anchor lines at the pinned commit) |", "|---|---|---|"]
    an = {a["label"]: a for a in inv["anchors"]}
    pc = an["primitives.verifier.now"]; pe = an["primitives.verifier.expired"]
    ver.append("| `cic-primitives` `tools/compiler.py` | **yes**, the validity of the certificate and of the root is judged at the moment of checking | `now = datetime.now(UTC)` at lines %s; `expired`/`not valid` refusals at lines %s (commit `%s`) |" % (", ".join(map(str, pc["lines"])), ", ".join(map(str, pe["lines"])), pc["commit"][:12]))
    rt = an["registry.verifier.time-words"]; rs = an["registry.verifier.signed-payload"]; re_ = an["registry.verifier.embedded-root"]
    ver.append("| `cic-schema-registry` `tools/registrylib/verify.py` | **no**: the file has %d lines with a time word (`not_valid`, `not_before`, `not_after`, `datetime`, `expire`); the chain is checked by signature only, against the root **embedded in the record** (lines %s) | `signed_payload` is `build_hash` (lines %s) and the file has %d lines naming `ts`: the countersign `ts` is neither signed nor checked (commit `%s`) |" % (len(rt["lines"]), ", ".join(map(str, re_["lines"][:4])), ", ".join(map(str, rs["lines"][:3])), len(an["registry.verifier.ts-words"]["lines"]), rt["commit"][:12]))
    vo = an["relay.verifier.verify-options"]; ct = an["relay.verifier.current-time"]
    ver.append("| `CIC_Relay` `core/cabinet/pki_verify.go` | **yes** (by default): `x509.VerifyOptions{` at line %s with %d lines naming `CurrentTime`, so Go checks the chain at the current time | commit `%s` |" % (", ".join(map(str, vo["lines"])), len(ct["lines"]), vo["commit"][:12]))
    return {"chain": "\n".join(chain), "records": "\n".join(rec), "verifiers": "\n".join(ver)}


def main(argv):
    try:
        inv = json.load(open(arg(argv, "--inventory", INV), encoding="utf-8")); manifest = json.load(open(arg(argv, "--manifest", MANIFEST), encoding="utf-8"))
        chain_dir = arg(argv, "--chain", CHAIN)
        doc = open(arg(argv, "--doc", DOC), encoding="utf-8").read() if "--render" not in argv else ""
        tables = render(inv, manifest)
    except BaseException as e:
        print("INCOMPLETE: an input cannot be read: %r" % (e,)); return 2
    if "--render" in argv:
        for k, v in tables.items():
            print("## %s\n%s\n" % (k, v));
        return 0
    # chain
    for c in inv["chain"]:
        try:
            nb, na, fp = cert_dates(os.path.join(chain_dir, c["file"]))
        except BaseException as e:
            print("INCOMPLETE: %r" % (e,)); return 2
        expect("chain.dates.%s" % c["file"], na == c["not_after"] and nb == c["not_before"] and fp == c["sha256"], "the inventory says %s / %s, the kept certificate %s / %s" % (c["not_before"], c["not_after"], nb, na))
    src = next(c for c in inv["chain"] if c["file"] == "source-ca.pem")
    # consistent
    expect("consistent.registry-source-ca", set(inv["registry"]["src_ca_not_after"]) == {src["not_after"]}, "registry records name a Source CA that ends %s, the kept Source CA ends %s" % (inv["registry"]["src_ca_not_after"], src["not_after"]))
    tags = {t["tag"] for t in inv["tag_records"]}
    for r in stamped_releases(manifest):
        expect("consistent.stamped-tag.%s" % r, "primitives/@%s" % r in tags, "the manifest stamps %s but the inventory has no such tag" % r)
    # verifiers
    an = {a["label"]: a for a in inv["anchors"]}
    expect("verifiers.registry.time-agnostic", an["registry.verifier.time-words"]["lines"] == [], "the registry verifier now has time words at %s: the claim that it does not read the clock is no longer true" % an["registry.verifier.time-words"]["lines"])
    expect("verifiers.primitives.reads-clock", bool(an["primitives.verifier.now"]["lines"]) and bool(an["primitives.verifier.expired"]["lines"]), "no clock reading or expiry refusal recorded for the primitives verifier")
    expect("verifiers.relay.default-time", bool(an["relay.verifier.verify-options"]["lines"]) and an["relay.verifier.current-time"]["lines"] == [], "the Relay chain verification no longer builds VerifyOptions without CurrentTime")
    expect("verifiers.registry.ts-unsigned", bool(an["registry.verifier.signed-payload"]["lines"]), "no signed_payload anchor recorded: the claim that the countersign ts is not signed is unsupported")
    expect("verifiers.registry.ts-unchecked", an["registry.verifier.ts-words"]["lines"] == [], "the registry verifier now names ts at %s: the claim that the countersign ts is not checked is no longer true" % an["registry.verifier.ts-words"]["lines"])
    # doc
    for k, (b, e) in MARK.items():
        if b in doc and e in doc:
            expect("doc.table.%s" % k, doc.split(b, 1)[1].split(e, 1)[0].strip() == tables[k].strip(), "the %s table of the document differs from the table rendered from the inventory" % k)
        else:
            expect("doc.markers.%s" % k, False, "the document has no %s table markers" % k)
    cls = classify(inv, manifest)
    n_unstamped = sum(1 for r in cls if not r[2]) + inv["registry"]["records"]
    print("registry records %d, tag records classified %d, stamped %d; records without external time evidence %d" % (inv["registry"]["records"], len(cls), sum(1 for r in cls if r[2]), n_unstamped))
    if fails:
        print("FAILED: %d expectation(s)" % len(fails)); return 1
    print("all expectations held"); return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
