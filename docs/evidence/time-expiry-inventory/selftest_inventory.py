"""Self-test of the expiry inventory: can the TOOL and the CHECK fail, and for the right reason? Typed exits; an infrastructure failure is never a detection.
T: tests of inventory.py on small FIXTURE repositories (git repositories built here from the kept certificates): a complete positive control and one isolated fault each (a tag that cannot be fetched, a tag that does
   not exist, an unparsable record file, a project.yaml that is absent, a project.yaml without a signature block, an unreadable certificate, a missing clone). Each fault is counted only when the status of exactly the
   intended scope element is the intended one, no other element changes, and the exit code is the intended one (1 for an incomplete inventory, 2 for an unreadable input).
A: the check on the package as it is (exit 0). C: planted faults in COPIES of the inventory, the document and the manifest, each counted only when the check exits 1 AND prints a FAIL-EXPECT line of the intended check.
D: an unreadable input of the check exits 2. Exit: 0 all as expected, 1 a mutant was not detected or a control failed, 2 the self-test itself could not run."""
import copy, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
CHECK = os.path.join(HERE, "check_inventory.py")
INVENTORY = os.path.join(HERE, "inventory.py")
INV = os.path.join(HERE, "results", "inventory.json")
DOC = os.path.join(REPO, "docs", "en", "T3-EXPIRY-RISK-ASSESSMENT-AND-DECISION-PLAN.md")
MANIFEST = os.path.join(REPO, "evidence", "time", "digicert-2026-11-03", "manifest.json")
CHAIN = os.path.join(REPO, "evidence", "time", "digicert-2026-11-03", "cic-chain")
bad = 0


def report(label, ok, extra=""):
    global bad
    print("%-118s %s %s" % (label, "OK" if ok else "FAIL", extra))
    bad += not ok


def run(cmd, args):
    r = subprocess.run([sys.executable, cmd] + args, capture_output=True, text=True, timeout=300)
    return r.returncode, r.stdout + r.stderr


def git(cwd, *a):
    return subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True)


def pem(name):
    return open(os.path.join(CHAIN, name), encoding="utf-8").read()


def record_yaml(dev=None, authority=None, root=None, extra=""):
    ind = lambda t: "\n".join("      " + l for l in t.rstrip().splitlines())
    return ("metadata: {name: x, version: v0.0.1}\nrelease:\n  createdBy:\n    name: n\n    certificate: |\n%s\n  build_hash: AAAA\n  sign: vault:v1:xx\ncic_countersign:\n  authority:\n    name: CIC Source CA\n    certificate: |\n%s\n"
            "    root_certificate: |\n%s\n  signed_payload: build_hash\n  sign: vault:v1:yy\n  workflow: wf\n  ts: '2026-09-06T19:31:23Z'\n%s") % (ind(dev if dev is not None else pem("developer.pem")), ind(authority if authority is not None else pem("source-ca.pem")), ind(root if root is not None else pem("root.pem")), extra)


STUB = {"cic-primitives": {"tools/compiler.py": "import datetime\nnow = datetime.datetime.now(datetime.timezone.utc)\nreturn False, 'expired on'\n"},
        "cic-schema-registry": {"tools/registrylib/verify.py": "# signed_payload embedded\n"},
        "CIC_Relay": {"core/cabinet/pki_verify.go": "x509.VerifyOptions{\n"}}


def make_fixture(root, registry_files=None, tags=None, no_origin=()):
    """five small git repositories; tags = {repo: {tag: {path: text}}}; every repo's origin is itself"""
    for repo in ("cic-schema-registry", "cic-primitives", "CIC_Relay", "base-repo", "cic-yang"):
        d = os.path.join(root, repo); os.makedirs(d)
        git(d, "init", "-q", "-b", "main"); git(d, "config", "user.email", "t@t"); git(d, "config", "user.name", "t"); git(d, "config", "commit.gpgsign", "false")
        files = dict(STUB.get(repo, {}))
        if repo == "cic-schema-registry":
            files.update(registry_files or {"standards/a.yaml": record_yaml()})
        if not files:
            files = {"README": "x"}
        for p, t in files.items():
            os.makedirs(os.path.dirname(os.path.join(d, p)) or d, exist_ok=True); open(os.path.join(d, p), "w", encoding="utf-8").write(t)
        git(d, "add", "-A"); git(d, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "init", "--no-verify")
        for tag, tfiles in (tags or {}).get(repo, {}).items():
            git(d, "checkout", "-q", "--detach", "main")
            for p, t in tfiles.items():
                os.makedirs(os.path.dirname(os.path.join(d, p)) or d, exist_ok=True); open(os.path.join(d, p), "w", encoding="utf-8").write(t)
            git(d, "add", "-A"); git(d, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", tag, "--no-verify"); git(d, "tag", tag); git(d, "checkout", "-q", "main")
        git(d, "remote", "add", "origin", "/nonexistent/remote.git" if repo in no_origin else d)


def inv_run(clones, scope, extra=()):
    out = os.path.join(clones, "out.json"); sj = os.path.join(clones, "scope.json"); json.dump(scope, open(sj, "w"))
    rc, o = run(INVENTORY, ["--clones", clones, "--out", out, "--chain", CHAIN, "--as-of", "2026-11-23", "--scope-json", sj] + list(extra))
    return rc, o, (json.load(open(out)) if os.path.exists(out) else None)


def statuses(inv):
    return {s["id"]: s["status"] for s in inv["scope"]}


def main():
    inv = json.load(open(INV, encoding="utf-8")); doc = open(DOC, encoding="utf-8").read(); man = json.load(open(MANIFEST, encoding="utf-8"))
    # ---- T: the tool on fixtures
    good_tags = {"cic-primitives": {"primitives/@v0.1.5": {"release/cic-primitives-v0.1.5.yaml": record_yaml()}}, "cic-yang": {"yang/@v0.1.2": {"release/cic-yang-v0.1.2.yaml": record_yaml()}},
                 "base-repo": {"base@0.6.0": {"project.yaml": "metadata:\n  sign: vault:v1:zz\n  validity: {from: '2025-12-08T17:09:32+00:00', until: '2026-12-08T17:09:32+00:00'}\n"},
                               "plain@0.1": {"project.yaml": "name: x\n"}, "nofile@0.1": {"other.txt": "x"}}}
    scope = {"cic-primitives": ["primitives/@v0.1.5"], "cic-yang": ["yang/@v0.1.2"], "base-repo": ["base@0.6.0", "plain@0.1", "nofile@0.1"]}
    base_status = None
    d = tempfile.mkdtemp()
    try:
        make_fixture(d, tags=good_tags)
        rc, o, j = inv_run(d, scope)
        st = statuses(j) if j else {}
        base_status = st
        report("T0 positive control: a complete fixture inventory (every element ok or absent), exit 0", rc == 0 and j["complete"] and st.get("tag:base-repo:plain@0.1") == "absent" and st.get("tag:base-repo:nofile@0.1") == "absent" and st.get("tag:cic-primitives:primitives/@v0.1.5") == "ok" and st.get("registry-scan") == "ok", "exit=%d" % rc)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    def isolated(label, build, expect_id, expect_status, expect_rc=1, scope_=scope, tags=good_tags, registry_files=None, no_origin=()):
        d = tempfile.mkdtemp()
        try:
            make_fixture(d, tags=tags, registry_files=registry_files, no_origin=no_origin)
            if build:
                build(d)
            rc, o, j = inv_run(d, scope_)
            st = statuses(j) if j else {}
            changed = {k: v for k, v in st.items() if base_status.get(k) != v}
            ok = rc == expect_rc and j is not None and st.get(expect_id) == expect_status and set(changed) <= {expect_id} and (j["complete"] == (expect_rc == 0))
            report("T fault: " + label, ok, "exit=%d %s=%s changed=%s" % (rc, expect_id, st.get(expect_id), sorted(changed)))
            return j
        finally:
            shutil.rmtree(d, ignore_errors=True)

    isolated("a tag cannot be fetched or listed (the remote of cic-yang is broken): fetch_error, not absent", None, "tag:cic-yang:yang/@v0.1.2", "fetch_error", no_origin=("cic-yang",))
    isolated("a tag the scope names does not exist in the remote: not_found, not absent", None, "tag:cic-primitives:primitives/@v9.9.9", "not_found", scope_={"cic-primitives": ["primitives/@v0.1.5", "primitives/@v9.9.9"], "cic-yang": ["yang/@v0.1.2"], "base-repo": ["base@0.6.0", "plain@0.1", "nofile@0.1"]})
    j = isolated("a registry file that mentions the signature blocks does not parse: registry-scan is a parse_error, the file is listed", None, "registry-scan", "parse_error",
                 registry_files={"standards/a.yaml": record_yaml(), "standards/broken.yaml": "cic_countersign: [unclosed\n  x: : :\n"})
    report("T fault: ...and the unparsable file is LISTED by path, not skipped", bool(j) and j["registry"]["parse_errors"] == ["standards/broken.yaml"] and j["registry"]["files_mentioning_blocks"] == j["registry"]["records"] + 1 + j["registry"]["not_a_record"], "listed=%s" % (j["registry"]["parse_errors"] if j else None))
    isolated("a tag without a project.yaml is ABSENT (a result), not an error and not a fetch failure", None, "tag:base-repo:nofile@0.1", "absent", expect_rc=0)
    isolated("a project.yaml without a signature block is ABSENT (a result)", None, "tag:base-repo:plain@0.1", "absent", expect_rc=0)
    j = isolated("a certificate in a form the tool cannot read is UNKNOWN downstream, never replaced by another date", None, "registry-scan", "ok", expect_rc=0,
                 registry_files={"standards/a.yaml": record_yaml(dev="-----BEGIN CERTIFICATE-----\nnot a certificate\n-----END CERTIFICATE-----\n")})
    reg = next((c for c in j["classes"] if c["id"] == "registry"), None) if j else None
    report("T fault: ...the class lists the unreadable certificate and its earliest end stays the one that WAS read", bool(reg) and reg["unknown_certs"] == {"developer": 1} and reg["earliest_cert_end"]["not_after"] == "2026-12-31T13:22:39Z" and reg["state_at_as_of"] == "UNKNOWN", "unknown=%s state=%s" % (reg and reg["unknown_certs"], reg and reg["state_at_as_of"]))
    rc, o = run(INVENTORY, ["--clones", "/nonexistent/clones", "--out", os.path.join(tempfile.gettempdir(), "x.json"), "--chain", CHAIN])
    report("T infra: the clones directory does not exist (exit 2, not a detection)", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)

    # ---- A and C: the check
    rc, o = run(CHECK, [])
    report("A positive control: the check on the package as it is", rc == 0 and "all expectations held" in o, "exit=%d" % rc)

    def mut(f):
        x = copy.deepcopy(inv); f(x); return x

    def stamps(m):
        m["stamps"].append(dict(m["stamps"][0], release="v9.9.9"))

    def setstatus(i, st):
        def f(x):
            for s in x["scope"]:
                if s["id"] == i:
                    s["status"] = st
        return f

    def cls(x, cid):
        return next(c for c in x["classes"] if c["id"] == cid)

    tpl = "tag:base-repo:base@0.6.0"
    faults = [
        ("a scope element is a fetch_error (the inventory is not complete)", dict(inv=mut(setstatus(tpl, "fetch_error"))), "complete.element.%s" % tpl),
        ("a scope element is a parse_error", dict(inv=mut(setstatus("registry-scan", "parse_error"))), "complete.element.registry-scan"),
        ("a scope element is not_found", dict(inv=mut(setstatus("tag:yang:x", "not_found") if False else setstatus("tag:cic-yang:yang/@v0.1.2", "not_found"))), "complete.element.tag:cic-yang:yang/@v0.1.2"),
        ("the complete flag says true while an element is an error", dict(inv=mut(lambda x: (setstatus(tpl, "fetch_error")(x), x.__setitem__("complete", True)))), "complete.flag"),
        ("a registry file that mentions the blocks is unaccounted for", dict(inv=mut(lambda x: x["registry"].__setitem__("files_mentioning_blocks", x["registry"]["files_mentioning_blocks"] + 1))), "complete.registry-accounting"),
        ("a tag record has no scope element", dict(inv=mut(lambda x: x["scope"].__delitem__(next(i for i, s in enumerate(x["scope"]) if s["id"] == "tag:cic-yang:yang/@v0.1.3")))), "complete.tag-scope.cic-yang:yang/@v0.1.3"),
        ("the state of a class does not follow from its boundary (an ended class declared open)", dict(inv=mut(lambda x: cls(x, "template:base@0.6.0").__setitem__("state_at_as_of", "open"))), "consistent.state.template:base@0.6.0"),
        ("the registry class's earliest certificate end differs from the kept Source CA", dict(inv=mut(lambda x: cls(x, "registry")["earliest_cert_end"].__setitem__("not_after", "2026-12-31T13:22:40Z"))), "consistent.registry-source-ca"),
        ("the inventory's Source CA end differs from the kept certificate", dict(inv=mut(lambda x: [c.__setitem__("not_after", "2026-12-31T13:22:40Z") for c in x["chain"] if c["file"] == "source-ca.pem"])), "chain.dates.source-ca.pem"),
        ("the registry verifier gains a time word", dict(inv=mut(lambda x: [a.__setitem__("lines", [12]) for a in x["anchors"] if a["label"] == "registry.verifier.time-words"])), "verifiers.registry.time-agnostic"),
        ("the registry verifier starts to name ts", dict(inv=mut(lambda x: [a.__setitem__("lines", [3]) for a in x["anchors"] if a["label"] == "registry.verifier.ts-words"])), "verifiers.registry.ts-unchecked"),
        ("the Relay chain verification gains a CurrentTime", dict(inv=mut(lambda x: [a.__setitem__("lines", [5]) for a in x["anchors"] if a["label"] == "relay.verifier.current-time"])), "verifiers.relay.default-time"),
        ("the manifest stamps a release that is not a tag of the inventory", dict(man=(lambda m: (stamps(m), m)[1])(copy.deepcopy(man))), "consistent.stamped-tag.v9.9.9"),
        ("the boundary table of the document says a stamp made now still helps an ended class", dict(doc=doc.replace("**NO**: the boundary has passed; a stamp made now shows only that the record existed no later than the stamp, not that it existed or was valid before the boundary", "yes, only if the stamp is made before the boundary", 1)), "doc.table.boundaries"),
        ("the boundary table of the document hides an UNKNOWN boundary", dict(doc=doc.replace("| none extracted |", "| 2026-12-31T13:22:39Z (authority: CIC Source CA) |", 1)), "doc.table.boundaries"),
        ("the evidence table of the document edited by hand (the primitives stamps)", dict(doc=doc.replace("**3 of 3** (DigiCert, 2026-11-03)", "**4 of 4** (DigiCert, 2026-11-03)", 1)), "doc.table.evidence"),
        ("the scope table of the document says the inventory is complete although it is not", dict(inv=mut(lambda x: (setstatus(tpl, "fetch_error")(x), x.__setitem__("complete", False)))), "doc.table.scope"),
        ("the chain table of the document edited by hand", dict(doc=doc.replace("| CIC Source CA | 2026-12-31T13:22:39Z |", "| CIC Source CA | 2026-12-31T13:22:40Z |", 1)), "doc.table.chain"),
        ("the document states another number of open records", dict(doc=doc.replace("**92 records are still open**", "**93 records are still open**", 1)), "doc.numbers.open"),
        ("the document without the boundary table markers", dict(doc=doc.replace("<!-- BEGIN BOUNDARIES TABLE -->", "")), "doc.markers.boundaries"),
    ]
    for name, files, needle in faults:
        d = tempfile.mkdtemp()
        try:
            args = []
            for key, flag in (("inv", "--inventory"), ("doc", "--doc"), ("man", "--manifest")):
                if key in files:
                    f = os.path.join(d, key + ".dat"); data = files[key]
                    open(f, "w", encoding="utf-8").write(json.dumps(data) if key != "doc" else data); args += [flag, f]
            rc, o = run(CHECK, args)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        named = [l for l in o.splitlines() if l.startswith("FAIL-EXPECT") and needle in l]
        report("C planted: " + name, rc == 1 and bool(named), "exit=%d needle=%s" % (rc, needle))
    rc, o = run(CHECK, ["--inventory", "/nonexistent/inventory.json"])
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
