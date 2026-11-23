"""Self-test of check_inventory.py: can it FAIL, and for the right reason? Typed exits; infrastructure is never a detection.
A: the package as it is (exit 0). C: planted faults in COPIES of the inventory, the document and the manifest, each counted only when the check exits 1 AND prints a FAIL-EXPECT line of the intended check.
D: an unreadable input exits 2. Exit: 0 all as expected, 1 a mutant was not detected or a control failed, 2 the self-test itself could not run."""
import copy, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
CHECK = os.path.join(HERE, "check_inventory.py")
INV = os.path.join(HERE, "results", "inventory.json")
DOC = os.path.join(REPO, "docs", "en", "T3-EXPIRY-RISK-ASSESSMENT-AND-DECISION-PLAN.md")
MANIFEST = os.path.join(REPO, "evidence", "time", "digicert-2026-11-03", "manifest.json")
bad = 0


def report(label, ok, extra=""):
    global bad
    print("%-104s %s %s" % (label, "OK" if ok else "FAIL", extra))
    bad += not ok


def run(args):
    r = subprocess.run([sys.executable, CHECK] + args, capture_output=True, text=True, timeout=300)
    return r.returncode, r.stdout + r.stderr


def sub(text, a, b):
    assert text.count(a) >= 1, a
    return text.replace(a, b, 1)


def main():
    inv = json.load(open(INV, encoding="utf-8")); doc = open(DOC, encoding="utf-8").read(); man = json.load(open(MANIFEST, encoding="utf-8"))
    rc, o = run([])
    report("A positive control (the package as it is)", rc == 0 and "all expectations held" in o, "exit=%d" % rc)

    def mut_inv(f):
        d = copy.deepcopy(inv); f(d); return d

    def anchor(d, label, lines):
        for a in d["anchors"]:
            if a["label"] == label:
                a["lines"] = lines

    def stamps(d):
        d["stamps"].append(dict(d["stamps"][0], release="v9.9.9"))

    faults = [
        ("the chain table of the document edited by hand (the Source CA end)", dict(doc=sub(doc, "| CIC Source CA | Dec 31 13:22:39 2026 GMT |", "| CIC Source CA | Dec 31 13:22:40 2026 GMT |")), "doc.table.chain"),
        ("the records table of the document edited by hand (90 records)", dict(doc=sub(doc, "| 90 | **none** |", "| 89 | **none** |")), "doc.table.records"),
        ("the verifier table of the document edited by hand (the registry verifier reads the clock)", dict(doc=sub(doc, "| `cic-schema-registry` `tools/registrylib/verify.py` | **no**:", "| `cic-schema-registry` `tools/registrylib/verify.py` | **yes**:")), "doc.table.verifiers"),
        ("the inventory says 89 registry records while the document says 90", dict(inv=mut_inv(lambda d: d["registry"].__setitem__("records", 89))), "doc.table.records"),
        ("the inventory's Source CA end differs from the kept certificate", dict(inv=mut_inv(lambda d: [c.__setitem__("not_after", "Dec 31 13:22:40 2026 GMT") for c in d["chain"] if c["file"] == "source-ca.pem"])), "chain.dates.source-ca.pem"),
        ("a registry record names a Source CA that ends at another time", dict(inv=mut_inv(lambda d: d["registry"].__setitem__("src_ca_not_after", {"Dec 31 13:22:40 2026 GMT": 90}))), "consistent.registry-source-ca"),
        ("the registry verifier gains a time word (the claim that it does not read the clock fails)", dict(inv=mut_inv(lambda d: anchor(d, "registry.verifier.time-words", [12]))), "verifiers.registry.time-agnostic"),
        ("the registry verifier starts to name ts (the claim that the countersign ts is not checked fails)", dict(inv=mut_inv(lambda d: anchor(d, "registry.verifier.ts-words", [3]))), "verifiers.registry.ts-unchecked"),
        ("the Relay chain verification gains a CurrentTime (the default-time claim fails)", dict(inv=mut_inv(lambda d: anchor(d, "relay.verifier.current-time", [5]))), "verifiers.relay.default-time"),
        ("the primitives verifier no longer reads the clock", dict(inv=mut_inv(lambda d: anchor(d, "primitives.verifier.now", []))), "verifiers.primitives.reads-clock"),
        ("the manifest stamps a release that is not a tag of the inventory", dict(man=(lambda m: (stamps(m), m)[1])(copy.deepcopy(man))), "consistent.stamped-tag.v9.9.9"),
        ("the document without the chain table markers", dict(doc=doc.replace("<!-- BEGIN CHAIN TABLE -->", "")), "doc.markers.chain"),
    ]
    for name, files, needle in faults:
        d = tempfile.mkdtemp()
        try:
            args = []
            for key, flag in (("inv", "--inventory"), ("doc", "--doc"), ("man", "--manifest")):
                if key in files:
                    f = os.path.join(d, key + ".dat"); data = files[key]
                    open(f, "w", encoding="utf-8").write(json.dumps(data) if key != "doc" else data); args += [flag, f]
            rc, o = run(args)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        named = [l for l in o.splitlines() if l.startswith("FAIL-EXPECT") and needle in l]
        report("C planted: " + name, rc == 1 and bool(named), "exit=%d needle=%s" % (rc, needle))
    rc, o = run(["--inventory", "/nonexistent/inventory.json"])
    report("D infra: the inventory is unreadable (exit 2, not a detection)", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)
    print("self-test: %s" % ("all as expected" if not bad else "%d problem(s)" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
