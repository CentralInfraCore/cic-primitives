"""Reproducible negative tests of the integrity tooling (owner conditions of 2026-11-22): can integrity_check.py and verify_unchanged.py FAIL, and for the right reason? Typed exits; infrastructure is never a
detection. The corruption is SIMULATED on copies in a temporary directory: every occurrence of the three bytes backslash, u and four hex digits is replaced by the character it names (the observed effect of the
faulty writing path). This source holds no escape text: the byte values are integers. The real files are never modified.
Exit: 0 all as expected, 1 a check did not behave as expected, 2 the self-test itself could not run."""
import hashlib, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
VEC = os.path.join(REPO, "docs", "design", "pattern-profile-vectors", "pattern-profile.yaml")
REF = os.path.join(HERE, "integrity-reference.json")
INTEG, UNCH = os.path.join(HERE, "integrity_check.py"), os.path.join(HERE, "verify_unchanged.py")
BS, U = 92, 117
HEX = set(b"0123456789abcdefABCDEF")
bad = 0


def corrupt_u_escapes(data):
    """the observed effect: backslash, u and four hex digits become the character they name"""
    out, i = bytearray(), 0
    while i < len(data):
        if data[i] == BS and i + 5 < len(data) and data[i + 1] == U and all(c in HEX for c in data[i + 2:i + 6]):
            out += chr(int(data[i + 2:i + 6].decode("ascii"), 16)).encode("utf-8"); i += 6
        else:
            out.append(data[i]); i += 1
    return bytes(out)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(script, args):
    r = subprocess.run([sys.executable, script] + args, capture_output=True, text=True, timeout=300, cwd=HERE)
    return r.returncode, r.stdout + r.stderr


def report(label, ok, extra=""):
    global bad
    print("%-84s %s %s" % (label, "OK" if ok else "FAIL", extra))
    bad += not ok


def named(o, needle):
    return any(l.startswith("FAIL-EXPECT") and needle in l for l in o.splitlines())


def main():
    good = open(VEC, "rb").read()
    ref = json.load(open(REF))["vector_file_sha256"]
    t = tempfile.mkdtemp()
    try:
        def w(name, data):
            p = os.path.join(t, name); open(p, "wb").write(data); return p
        rc, o = run(INTEG, [])
        report("I positive control (the real vector file, the repository reference)", rc == 0, "exit=%d" % rc)
        bad_all = corrupt_u_escapes(good)
        report("I the simulation changes the file (it is not a no-op)", bad_all != good and len(bad_all) < len(good))
        f1 = w("corrupt.yaml", bad_all); before = sha(bad_all)
        rc, o = run(INTEG, ["--file", f1])
        report("I the escape turned into a plain character: rejected by both mechanisms", rc == 1 and named(o, "canary.X-S146") and named(o, "sha256"), "exit=%d" % rc)
        report("I the checker did not repair the damaged file", sha(open(f1, "rb").read()) == before)
        rc, o = run(INTEG, ["--file", f1, "--no-sha"])
        report("I the canary alone rejects it", rc == 1 and named(o, "canary.X-S146") and not named(o, "sha256"), "exit=%d" % rc)
        rc, o = run(INTEG, ["--file", f1, "--no-canary"])
        report("I the SHA-256 alone rejects it", rc == 1 and named(o, "sha256") and not named(o, "canary"), "exit=%d" % rc)
        # damage at a place no canary covers: a backslash d in the vector X-K150 loses its backslash
        line = b"{id: X-K150, expr: '[" + bytes([BS, 100]) + b"]'"
        assert line in good
        f2 = w("other.yaml", good.replace(line, b"{id: X-K150, expr: '[d]'"))
        rc, o = run(INTEG, ["--file", f2])
        report("I damage outside the canaries: only the SHA-256 sees it", rc == 1 and named(o, "sha256") and not named(o, "canary"), "exit=%d" % rc)
        rc, o = run(INTEG, ["--file", f2, "--no-sha"])
        report("I damage outside the canaries: the canary alone misses it (the mechanisms differ)", rc == 0, "exit=%d" % rc)
        # the FORBIDDEN reference source: a hash computed from the already damaged file
        r3 = w("ref-from-written.json", json.dumps({"vector_file_sha256": sha(bad_all)}).encode())
        rc, o = run(INTEG, ["--file", f1, "--reference", r3])
        report("I a reference computed from the damaged file passes the SHA-256, the canary still rejects it", rc == 1 and named(o, "canary.X-S146") and not named(o, "sha256"), "exit=%d" % rc)
        r4 = w("ref-wrong.json", json.dumps({"vector_file_sha256": ref[:-1] + ("0" if ref[-1] != "0" else "1")}).encode())
        rc, o = run(INTEG, ["--reference", r4])
        report("I an intact file against a wrong reference value: rejected", rc == 1 and named(o, "sha256") and not named(o, "canary"), "exit=%d" % rc)
        # review F2 of #50: a run that selects no check must not succeed; each switch alone stays available (the tests above use them)
        rc, o = run(INTEG, ["--no-canary", "--no-sha"])
        report("F both switches together select no check: refused, exit 2 (INCOMPLETE), never a success", rc == 2 and "INCOMPLETE" in o and "all expectations held" not in o, "exit=%d" % rc)
        rc, o = run(INTEG, ["--file", f1, "--no-canary", "--no-sha"])
        report("F ... also on a damaged file: exit 2, not 0", rc == 2, "exit=%d" % rc)
        # review F1 of #50: verification is not authentication. The acceptance run takes an explicit value and refuses every other source
        rc, o = run(INTEG, ["--acceptance", "--expect-sha256", ref])
        report("A acceptance run with the explicit, independently approved value: passes and says so", rc == 0 and "ACCEPTANCE" in o and "command line" in o, "exit=%d" % rc)
        rc, o = run(INTEG, ["--acceptance"])
        report("A acceptance run without an explicit value: refused, exit 2", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)
        rc, o = run(INTEG, ["--acceptance", "--expect-sha256", ref, "--reference", REF])
        report("A acceptance run with a reference file as well: refused, exit 2", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)
        rc, o = run(INTEG, ["--acceptance", "--expect-sha256", ref, "--no-sha"])
        report("A acceptance run with a switch off: refused, exit 2", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)
        rc, o = run(INTEG, ["--acceptance", "--file", f1, "--expect-sha256", ref])
        report("A acceptance run on the damaged file with the approved value: rejected", rc == 1 and named(o, "sha256") and named(o, "canary.X-S146"), "exit=%d" % rc)
        rc, o = run(INTEG, ["--acceptance", "--file", f1, "--expect-sha256", sha(bad_all)])
        report("A acceptance run with a value taken from the damaged file: the tool cannot tell (SHA-256 passes), the canary still rejects it", rc == 1 and named(o, "canary.X-S146") and not named(o, "sha256"), "exit=%d" % rc)
        rc, o = run(INTEG, [])
        report("V default run states that the repository reference is verification only, not an independent basis", rc == 0 and "NOT an independent basis of trust" in o, "exit=%d" % rc)
        rc, o = run(INTEG, ["--file", os.path.join(t, "missing.yaml")])
        report("C infra: the file is missing (exit 2, not a detection)", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)
        rc, o = run(INTEG, ["--reference", os.path.join(t, "missing.json")])
        report("C infra: the reference is missing (exit 2, not a detection)", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)
        # the documents: the escape stated in prose must survive
        dd = os.path.join(t, "docs")
        for d in ("en", "hu"):
            os.makedirs(os.path.join(dd, d)); shutil.copy(os.path.join(REPO, "docs", d, "GRAMMAR-PATTERN-VECTORS.md"), os.path.join(dd, d))
        rc, o = run(INTEG, ["--docs", dd])
        report("D positive control: the documents state the escape sequence", rc == 0, "exit=%d" % rc)
        p = os.path.join(dd, "en", "GRAMMAR-PATTERN-VECTORS.md"); db = open(p, "rb").read(); open(p, "wb").write(corrupt_u_escapes(db))
        rc, o = run(INTEG, ["--docs", dd, "--no-sha"])
        report("D the escape in a document turned into a plain character: rejected", rc == 1 and named(o, "canary.doc.en"), "exit=%d" % rc)
        # verify_unchanged
        rc, o = run(UNCH, [])
        report("U positive control: the approved entries are unchanged, only the expected additions", rc == 0, "exit=%d" % rc)
        import yaml
        def variant(mut):
            d = yaml.safe_load(good); mut(d); return yaml.safe_dump(d, sort_keys=False, width=10000).encode()
        def chg_expect(d):
            for v in d["values"]:
                if v["id"] == "V-M001":
                    v["expect"] = "pattern_value_mismatch"
        def drop_vec(d):
            d["expressions"] = [v for v in d["expressions"] if v["id"] != "X-A001"]
        def chg_limit(d):
            d["limits"]["pi_max"] = 4096
        def extra_vec(d):
            d["schemas"].append(dict(d["schemas"][-1], id="S-021"))
        for label, mut, needle in (("an approved expectation changed", chg_expect, "vector.unchanged.V-M001"), ("an approved vector removed", drop_vec, "vector.unchanged.X-A001"),
                                   ("the approved limits changed", chg_limit, "metadata.unchanged.limits"), ("an unexpected extra vector", extra_vec, "vector.added")):
            f = w("v.yaml", variant(mut))
            rc, o = run(UNCH, ["--new", f])
            report("U planted: " + label, rc == 1 and named(o, needle), "exit=%d needle=%s" % (rc, needle))
        f = w("lines.yaml", good.replace(b"# Encoding (so that no reader", b"# Encoding (so that no reader  "))
        rc, o = run(UNCH, ["--new", f])
        report("U planted: an approved line rewritten (only a comment)", rc == 1 and named(o, "lines.subsequence"), "exit=%d" % rc)
        tb = w("tampered-base.yaml", subprocess.run(["git", "-C", REPO, "show", "9fe89b1c53eed142b53cea7449b36931b60d6573:docs/design/pattern-profile-vectors/pattern-profile.yaml"], capture_output=True, check=True).stdout + b"# x\n")
        rc, o = run(UNCH, ["--base-file", tb])
        report("U planted: the approved bytes do not match the reference of the PR description", rc == 1 and named(o, "base.sha256"), "exit=%d" % rc)
        rc, o = run(UNCH, ["--new", os.path.join(t, "missing.yaml")])
        report("C infra: the new file is missing (exit 2, not a detection)", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)
    finally:
        shutil.rmtree(t, ignore_errors=True)
    print("self-test: %s" % ("all as expected" if not bad else "%d problem(s)" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
