"""Check of the expiry inventory against the review document and the evidence that is in THIS repository. An ISOLATED check, not a CI gate; it changes nothing, stamps nothing, signs nothing.
Checks (a failure is a FAIL-EXPECT line, exit 1; an unreadable input is INCOMPLETE, exit 2, never a result):
  complete    the inventory is COMPLETE (review F2 of the T3 package): every element of its declared scope has a status of `ok` or `absent`; a `parse_error`, `fetch_error`, `not_found` fails; the `complete`
              flag equals what the scope says; the registry files that mention the signature blocks are all accounted for (parsed, a parse error or explicitly not a record); every tag record, anchor and chain
              certificate has its scope element
  chain       the four chain certificates of the inventory equal, by end and fingerprint, the certificates kept in evidence/time/digicert-2026-11-03/cic-chain (openssl reads them again)
  consistent  the registry class names the kept Source CA as its earliest certificate end; the three stamped releases of the manifest are tags of the inventory; a class's state follows from its boundary
              AT THE FULL UTC INSTANT of the inventory (ended only when the instant is after the boundary second)
  verifiers   the claims about the three verifiers rest on the recorded anchors (the registry verifier has NO time word and names no `ts`, the primitives verifier reads the clock, the Relay chain
              verification builds x509.VerifyOptions WITHOUT CurrentTime)
  doc         the tables of the review document (chain, boundaries, evidence, scope, verifiers) are exactly the tables rendered from the inventory and the manifest (nothing is hand-edited into them); the
              boundary table answers "can a stamp made now still show existence before the boundary" NO for every class whose boundary has passed, and UNKNOWN where a boundary could not be extracted
Usage: check_inventory.py [--render] [--inventory PATH] [--doc PATH] [--manifest PATH] [--chain DIR]"""
import collections, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
INV = os.path.join(HERE, "results", "inventory.json")
DOC = os.path.join(REPO, "docs", "en", "T3-EXPIRY-RISK-ASSESSMENT-AND-DECISION-PLAN.md")
MANIFEST = os.path.join(REPO, "evidence", "time", "digicert-2026-11-03", "manifest.json")
CHAIN = os.path.join(REPO, "evidence", "time", "digicert-2026-11-03", "cic-chain")
MARK = {k: ("<!-- BEGIN %s TABLE -->" % k.upper(), "<!-- END %s TABLE -->" % k.upper()) for k in ("chain", "boundaries", "evidence", "scope", "verifiers")}
OK = {"ok", "absent"}
MONTHS = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
fails = []


def expect(label, cond, detail=""):
    if not cond:
        fails.append(label); print("FAIL-EXPECT %s %s" % (label, detail))


def arg(argv, name, default):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else default


def parse_gmt(text):
    m = re.search(r"([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d\d):(\d\d):(\d\d)\s+(\d{4})", text or "")
    return ("%s-%02d-%02dT%s:%s:%sZ" % (m.group(6), MONTHS[m.group(1)], int(m.group(2)), m.group(3), m.group(4), m.group(5))) if m and m.group(1) in MONTHS else None


def cert_end(path):
    r = subprocess.run(["openssl", "x509", "-in", path, "-noout", "-enddate", "-fingerprint", "-sha256"], capture_output=True, text=True)
    g = lambda k: (re.search(k + r"=\s*(.*)", r.stdout) or [None, None])[1]
    return parse_gmt(g("notAfter")), g("sha256 Fingerprint")


def stamped_releases(manifest):
    return sorted(s["release"] for s in manifest["stamps"])


def own_records(inv, repo):
    return [t for t in inv["tag_records"] if t["repo"] == repo and t.get("own_release_record")]


def answer(c):
    if c["state_at_as_of"] == "ended":
        return "**NO**: the boundary has passed; a stamp made now shows only that the record existed no later than the stamp, not that it existed or was valid before the boundary"
    if c["state_at_as_of"] == "open":
        return "yes, only if the stamp is made before the boundary"
    return "**UNKNOWN**: no boundary could be extracted"


def render(inv, manifest):
    chain = ["| Certificate | Subject | Not after (UTC) | SHA-256 fingerprint |", "|---|---|---|---|"]
    for c in sorted(inv["chain"], key=lambda c: c["file"]):
        chain.append("| `%s` | %s | %s | `%s` |" % (c["file"], c["subject_cn"], c["not_after"], c["sha256"]))
    bt = ["| Class | Records | Earliest proved certificate end | Declared record validity | State at %s | Can a stamp made now still show existence before the boundary? |" % inv["as_of"], "|---|---|---|---|---|---|"]
    for c in inv["classes"]:
        e = c["earliest_cert_end"]
        unk = (" (UNKNOWN certificates: %s)" % ", ".join("%s %d" % kv for kv in sorted(c["unknown_certs"].items()))) if c["unknown_certs"] else ""
        bt.append("| %s | %d | %s%s | %s | **%s** | %s |" % (c["label"], c["records"], ("%s (%s)" % (e["not_after"], e["role"].lstrip(".") if e["role"].startswith(".") else "%s: %s" % (e["role"], e["subject_cn"]))) if e else "none extracted", unk, c["declared_validity_until_min"] or "none declared", c["state_at_as_of"], answer(c)))
    reg = inv["registry"]; stamps = set(stamped_releases(manifest))
    prim = own_records(inv, "cic-primitives"); yang = own_records(inv, "cic-yang"); tpl = [c for c in inv["classes"] if c["id"].startswith("template:")]
    n_stamped = sum(1 for t in prim if (re.search(r"(v\d+\.\d+\.\d+)\.yaml$", t["file"]) or [0, ""])[1] in stamps)
    ev = ["| Class | Records | RFC 3161 time evidence of the record's existence | Evidence that the chain was valid at an earlier time | Note |", "|---|---|---|---|---|",
          "| cic-schema-registry countersigned records (main @ `%s`) | %d | **none** | **none** | countersign `ts` %s to %s: the countersigning service's own clock, covered by no signature; %d distinct build hashes |" % (inv["clones"]["cic-schema-registry"]["head"][:12], reg["records"], reg["ts_min"], reg["ts_max"], reg["unique_build_hash"]),
          "| cic-primitives release records (%s) | %d | **%d of %d** (DigiCert, 2026-11-03) | for the %d stamped: the stamp time lies inside all four windows of the kept chain; no revocation information exists | tags %s |" % ("the tags' own records", len(prim), n_stamped, len(prim), n_stamped, ", ".join("`%s`" % t["tag"] for t in prim)),
          "| cic-yang release records (the tags' own records) | %d | **none** | **none** | tags %s |" % (len(yang), ", ".join("`%s`" % t["tag"] for t in yang)),
          "| template releases (base-repo `project.yaml`) | %d with a signature block | **none** | **none** | %s |" % (len(tpl), "; ".join("`%s` boundary %s" % (c["label"].replace("template release ", ""), c["boundary"] or "UNKNOWN") for c in tpl))]
    sc = inv["scope"]; kinds = collections.OrderedDict()
    for s in sc:
        kinds.setdefault(s["kind"], collections.Counter())[s["status"]] += 1
    st = ["| Scope element kind | Elements | Statuses |", "|---|---|---|"]
    for k, cnt in kinds.items():
        st.append("| %s | %d | %s |" % (k, sum(cnt.values()), ", ".join("%s %d" % kv for kv in sorted(cnt.items()))))
    st.append("| **complete** | %d | **%s** (every element `ok` or `absent`) |" % (len(sc), "yes" if inv["complete"] else "NO"))
    for s in sc:
        if s["status"] == "absent":
            st.append("| `absent`: %s | 1 | %s |" % (s["id"], s["detail"]))
    st.append("| registry files that mention the signature blocks | %d | %d records, %d parse errors, %d not a record; %d top-level entries not scanned (%s) |" % (reg["files_mentioning_blocks"], reg["records"], len(reg["parse_errors"]), reg["not_a_record"], len(reg["not_scanned_top_level"]), "outside the record areas"))
    ver = ["| Verifier | Reads the clock? | Evidence (recorded anchor lines at the pinned commit) |", "|---|---|---|"]
    an = {a["label"]: a for a in inv["anchors"]}
    pc = an["primitives.verifier.now"]; pe = an["primitives.verifier.expired"]
    ver.append("| `cic-primitives` `tools/compiler.py` | **yes**, the validity of the certificate and of the root is judged at the moment of checking | `now = datetime.now(UTC)` at lines %s; `expired`/`not valid` refusals at lines %s (commit `%s`) |" % (", ".join(map(str, pc["lines"])), ", ".join(map(str, pe["lines"])), pc["commit"][:12]))
    rt = an["registry.verifier.time-words"]; rs = an["registry.verifier.signed-payload"]; re_ = an["registry.verifier.embedded-root"]
    ver.append("| `cic-schema-registry` `tools/registrylib/verify.py` | **no**: the file has %d lines with a time word (`not_valid`, `not_before`, `not_after`, `datetime`, `expire`); the chain is checked by signature only, against the root **embedded in the record** (lines %s) | `signed_payload` is `build_hash` (lines %s) and the file has %d lines naming `ts`: the countersign `ts` is neither signed nor checked (commit `%s`) |" % (len(rt["lines"]), ", ".join(map(str, re_["lines"][:4])), ", ".join(map(str, rs["lines"][:3])), len(an["registry.verifier.ts-words"]["lines"]), rt["commit"][:12]))
    vo = an["relay.verifier.verify-options"]; ct = an["relay.verifier.current-time"]
    ver.append("| `CIC_Relay` `core/cabinet/pki_verify.go` | **yes** (by default): `x509.VerifyOptions{` at line %s with %d lines naming `CurrentTime`, so Go checks the chain at the current time | commit `%s` |" % (", ".join(map(str, vo["lines"])), len(ct["lines"]), vo["commit"][:12]))
    return {"chain": "\n".join(chain), "boundaries": "\n".join(bt), "evidence": "\n".join(ev), "scope": "\n".join(st), "verifiers": "\n".join(ver)}


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
            print("## %s\n%s\n" % (k, v))
        return 0
    # complete
    scope = inv["scope"]
    for s in scope:
        expect("complete.element.%s" % s["id"], s["status"] in OK, "the scope element %s has the status %s (%s): the inventory is not complete" % (s["id"], s["status"], s["detail"]))
    expect("complete.flag", inv.get("complete") == all(s["status"] in OK for s in scope), "the complete flag says %s but the scope says %s" % (inv.get("complete"), all(s["status"] in OK for s in scope)))
    reg = inv["registry"]
    expect("complete.registry-accounting", reg["files_mentioning_blocks"] == reg["records"] + len(reg["parse_errors"]) + reg["not_a_record"], "%d files mention the blocks but %d records + %d parse errors + %d not-a-record are accounted for" % (reg["files_mentioning_blocks"], reg["records"], len(reg["parse_errors"]), reg["not_a_record"]))
    ids = {s["id"] for s in scope}
    for t in inv["tag_records"]:
        expect("complete.tag-scope.%s:%s" % (t["repo"], t["tag"]), "tag:%s:%s" % (t["repo"], t["tag"]) in ids, "a tag record without its scope element")
    for a in inv["anchors"]:
        expect("complete.anchor-scope.%s" % a["label"], "anchor:%s" % a["label"] in ids)
    for c in inv["chain"]:
        expect("complete.chain-scope.%s" % c["file"], "chain:%s" % c["file"] in ids)
    for c in inv["classes"]:
        expect("consistent.state.%s" % c["id"], c["state_at_as_of"] == ("ended" if c["boundary"] and c["boundary"] < inv["as_of"] else ("UNKNOWN" if (c["unknown_certs"] or not c["boundary"]) else "open")), "the state of the class does not follow from its boundary")
    # chain
    for c in inv["chain"]:
        try:
            na, fp = cert_end(os.path.join(chain_dir, c["file"]))
        except BaseException as e:
            print("INCOMPLETE: %r" % (e,)); return 2
        expect("chain.dates.%s" % c["file"], na == c["not_after"] and fp == c["sha256"], "the inventory says %s, the kept certificate %s" % (c["not_after"], na))
    src = next(c for c in inv["chain"] if c["file"] == "source-ca.pem")
    reg_cls = next(c for c in inv["classes"] if c["id"] == "registry")
    expect("consistent.registry-source-ca", (reg_cls["earliest_cert_end"] or {}).get("not_after") == src["not_after"], "the registry class's earliest certificate end is %s, the kept Source CA ends %s" % ((reg_cls["earliest_cert_end"] or {}).get("not_after"), src["not_after"]))
    ors = inv.get("open_records", [])
    expect("consistent.open-records", len(ors) == reg["records"] + len(own_records(inv, "cic-yang")) and len({r["id"] for r in ors}) == len(ors) and all(r["id"] == "%s:%s" % (r["repo"], r["path"]) and len(r["commit"]) == 40 for r in ors), "the expected set of open records (%d) is not the %d registry records plus the %d yang release records, or has a duplicate or malformed entry" % (len(ors), reg["records"], len(own_records(inv, "cic-yang"))))
    tags = {t["tag"] for t in inv["tag_records"]}
    for r in stamped_releases(manifest):
        expect("consistent.stamped-tag.%s" % r, "primitives/@%s" % r in tags, "the manifest stamps %s but the inventory has no such tag" % r)
    # verifiers
    an = {a["label"]: a for a in inv["anchors"]}
    expect("verifiers.registry.time-agnostic", an["registry.verifier.time-words"]["lines"] == [], "the registry verifier now has time words at %s" % an["registry.verifier.time-words"]["lines"])
    expect("verifiers.primitives.reads-clock", bool(an["primitives.verifier.now"]["lines"]) and bool(an["primitives.verifier.expired"]["lines"]), "no clock reading or expiry refusal recorded for the primitives verifier")
    expect("verifiers.relay.default-time", bool(an["relay.verifier.verify-options"]["lines"]) and an["relay.verifier.current-time"]["lines"] == [], "the Relay chain verification no longer builds VerifyOptions without CurrentTime")
    expect("verifiers.registry.ts-unsigned", bool(an["registry.verifier.signed-payload"]["lines"]), "no signed_payload anchor recorded")
    expect("verifiers.registry.ts-unchecked", an["registry.verifier.ts-words"]["lines"] == [], "the registry verifier now names ts at %s" % an["registry.verifier.ts-words"]["lines"])
    # doc
    for k, (b, e) in MARK.items():
        if b in doc and e in doc:
            expect("doc.table.%s" % k, doc.split(b, 1)[1].split(e, 1)[0].strip() == tables[k].strip(), "the %s table of the document differs from the table rendered from the inventory" % k)
        else:
            expect("doc.markers.%s" % k, False, "the document has no %s table markers" % k)
    stamped = sum(1 for t in own_records(inv, "cic-primitives") if (re.search(r"(v\d+\.\d+\.\d+)\.yaml$", t["file"]) or [0, ""])[1] in set(stamped_releases(manifest)))
    without = reg["records"] + len(own_records(inv, "cic-yang")) + len([c for c in inv["classes"] if c["id"].startswith("template:")]) + (len(own_records(inv, "cic-primitives")) - stamped)
    if doc:
        open_wo = sum(c["records"] for c in inv["classes"] if c["state_at_as_of"] == "open") - stamped
        for label, needle in (("open", "**%d records are still open**" % open_wo), ("accounting", "%d files mention them: %d records, %d parse errors, %d that are not records" % (reg["files_mentioning_blocks"], reg["records"], len(reg["parse_errors"]), reg["not_a_record"])), ("not-scanned", "%d of them" % len(reg["not_scanned_top_level"]))):
            expect("doc.numbers.%s" % label, needle in doc, "the document does not say %r" % needle)
    print("scope elements %d, complete %s; registry records %d; classes %d; stamped %d; records without external time evidence %d; classes whose boundary has passed: %s" % (len(scope), inv.get("complete"), reg["records"], len(inv["classes"]), stamped, without, ", ".join(c["id"] for c in inv["classes"] if c["state_at_as_of"] == "ended")))
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
