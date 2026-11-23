"""Self-test of build_manifest.py and verify_manifest.py: can they FAIL, and for the right reason? Typed exits; an infrastructure failure (git cannot read) is never a detection.
Everything runs on FIXTURE git repositories built here. B: the builder (a complete build, deterministic bytes, a file that mentions the block and does not parse, a missing tag, a tag without the record file).
V: the verifier on a good manifest (the bytes are read from the git OBJECT: a later commit and an uncommitted change do not matter) and on planted faults in COPIES of it, each counted only when the verifier exits 1 AND
prints a FAIL-EXPECT line of the intended check; two git failures exit 2. Exit: 0 all as expected, 1 a control failed or a fault was not detected, 2 the self-test itself could not run."""
import hashlib, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD, VERIFY = os.path.join(HERE, "build_manifest.py"), os.path.join(HERE, "verify_manifest.py")
bad = 0


def report(label, ok, extra=""):
    global bad
    print("%-112s %s %s" % (label, "OK" if ok else "FAIL", extra))
    bad += not ok


def run(cmd, args):
    r = subprocess.run([sys.executable, cmd] + args, capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout + r.stderr


def git(cwd, *a):
    return subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True)


REC = "metadata: {name: %s}\nrelease: {build_hash: AAAA}\ncic_countersign:\n  signed_payload: build_hash\n  ts: '2026-09-06T19:31:23Z'\n"


def fixture(root, registry=None, yang_tag=True, yang_file=True):
    for repo in ("cic-schema-registry", "cic-yang"):
        d = os.path.join(root, repo); os.makedirs(d)
        git(d, "init", "-q", "-b", "main"); git(d, "config", "user.email", "t@t"); git(d, "config", "user.name", "t"); git(d, "config", "commit.gpgsign", "false")
        files = {"README": "x\n"}
        if repo == "cic-schema-registry":
            files.update(registry or {"standards/a/a.v0.1.0.yaml": REC % "a", "standards/b/b.v0.1.0.yaml": REC % "b", "general/c/c.yaml": "name: c\nnote: cic_countersign mentioned only\n", "docs/skip.yaml": REC % "outside the record areas"})
        for p, t in files.items():
            os.makedirs(os.path.dirname(os.path.join(d, p)) or d, exist_ok=True); open(os.path.join(d, p), "w", encoding="utf-8").write(t)
        git(d, "add", "-A"); git(d, "commit", "-q", "-m", "init", "--no-verify")
        if repo == "cic-yang" and yang_tag:
            if yang_file:
                os.makedirs(os.path.join(d, "release"), exist_ok=True); open(os.path.join(d, "release", "cic-yang-v0.1.2.yaml"), "w").write(REC % "yang")
                git(d, "add", "-A"); git(d, "commit", "-q", "-m", "rel", "--no-verify")
            git(d, "tag", "yang/@v0.1.2")


def main():
    # ---- B: the builder
    d = tempfile.mkdtemp()
    try:
        fixture(d)
        out = os.path.join(d, "m.txt"); out2 = os.path.join(d, "m2.txt")
        sj = os.path.join(d, "scope.json"); open(sj, "w").write('{"yang_tags": ["yang/@v0.1.2"]}')
        rc, o = run(BUILD, ["--clones", d, "--out", out, "--scope-json", sj]); rc2, _ = run(BUILD, ["--clones", d, "--out", out2, "--scope-json", sj])
        raw = open(out, "rb").read() if os.path.exists(out) else b""
        report("B0 a complete build: 3 records (2 registry, 1 yang), the mention-only file and the file outside the record areas are not records", rc == 0 and b"count: 3\n" in raw and raw.count(b"\n") == 7 and b"outside the record areas" not in raw and b"general/c/c.yaml" not in raw, "exit=%d" % rc)
        report("B1 the build is deterministic: two builds are byte-identical, and the .sha256 file is the digest of the bytes", raw == open(out2, "rb").read() and open(out + ".sha256").read().split()[0] == hashlib.sha256(raw).hexdigest())
        report("B2 the records are sorted bytewise and carry the exact record bytes' SHA-256", [l.split("\t")[0] for l in raw.decode().splitlines()[4:]] == sorted(l.split("\t")[0] for l in raw.decode().splitlines()[4:]) and hashlib.sha256((REC % "a").encode()).hexdigest() in raw.decode())
        rc, o = run(VERIFY, ["--manifest", out, "--clones", d, "--sha256-file", out + ".sha256"])
        report("V0 positive control: the verifier accepts the good manifest", rc == 0 and "all expectations held" in o, "exit=%d" % rc)
        # the bytes come from the git OBJECT at the recorded commit: a later commit and an uncommitted change do not matter
        reg = os.path.join(d, "cic-schema-registry")
        open(os.path.join(reg, "standards/a/a.v0.1.0.yaml"), "w").write("changed in a later commit\n"); git(reg, "add", "-A"); git(reg, "commit", "-q", "-m", "later", "--no-verify")
        open(os.path.join(reg, "standards/b/b.v0.1.0.yaml"), "w").write("changed but not committed\n")
        rc, o = run(VERIFY, ["--manifest", out, "--clones", d])
        report("V1 the verifier reads the git object at the recorded commit, not the working tree: a later commit and an uncommitted change do not change the result", rc == 0, "exit=%d" % rc)
        lines = raw.decode().split("\n")

        def planted(name, new_text, needle, args_extra=(), expect_rc=1, sha=None):
            p = os.path.join(d, "p.txt"); open(p, "wb").write(new_text if isinstance(new_text, bytes) else new_text.encode("utf-8"))
            args = ["--manifest", p, "--clones", d] + list(args_extra)
            rc, o = run(VERIFY, args)
            named = [l for l in o.splitlines() if (l.startswith("FAIL-EXPECT") and needle in l) or (expect_rc == 2 and needle in l)]
            report("V fault: " + name, rc == expect_rc and bool(named), "exit=%d needle=%s" % (rc, needle))
        f4 = lines[4].split("\t")
        planted("a SHA-256 of a record is altered", "\n".join(lines[:4] + ["\t".join([f4[0], "0" * 64] + f4[2:])] + lines[5:]), "records.%s" % f4[0])
        planted("a size of a record is altered", "\n".join(lines[:4] + ["\t".join(f4[:2] + ["1"] + f4[3:])] + lines[5:]), "records.%s" % f4[0])
        planted("two record lines swapped (not sorted bytewise)", "\n".join(lines[:4] + [lines[5], lines[4]] + lines[6:]), "form")
        planted("the count does not match the lines", raw.decode().replace("count: 3", "count: 4", 1), "form")
        planted("a record line repeated (a duplicate id)", "\n".join(lines[:4] + [lines[4], lines[4]] + lines[5:]).replace("count: 3", "count: 4", 1), "form")
        planted("CRLF line ends", raw.decode().replace("\n", "\r\n"), "form")
        planted("a byte order mark", b"\xef\xbb\xbf" + raw, "form")
        planted("no final LF", raw[:-1], "form")
        planted("an extra blank line at the end", raw + b"\n", "form")
        planted("a record id that is not repo:path", raw.decode().replace(f4[0], "x:" + f4[0], 1), "form")
        open(out + ".bad", "w").write("%s  m.txt\n" % ("1" * 64))
        planted("a recorded manifest digest that is not the manifest's", raw, "digest", args_extra=("--sha256-file", out + ".bad"))
        planted("a commit that is not in the repository: git cannot read it, an infrastructure result (exit 2), not a detection", "\n".join(lines[:4] + ["\t".join(f4[:4] + ["2" * 40] + f4[5:])] + lines[5:]), "cannot read", expect_rc=2)
        git(os.path.join(d, "cic-yang"), "config", "log.date", "bogus")
        planted("git cannot show the bytes (an invalid git setting): exit 2, not a detection", raw, "cannot read", expect_rc=2)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    # ---- B: the fail-closed builds
    d = tempfile.mkdtemp()
    try:
        fixture(d, registry={"standards/a/a.v0.1.0.yaml": REC % "a", "standards/broken.yaml": "cic_countersign: [unclosed\n x: : :\n"})
        out = os.path.join(d, "m.txt"); sj = os.path.join(d, "scope.json"); open(sj, "w").write('{"yang_tags": ["yang/@v0.1.2"]}')
        rc, o = run(BUILD, ["--clones", d, "--out", out, "--scope-json", sj])
        report("B3 a file that mentions the block and does not parse: the build is NOT complete (exit 1), no manifest is written, the file is named", rc == 1 and "standards/broken.yaml" in o and not os.path.exists(out), "exit=%d" % rc)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    d = tempfile.mkdtemp()
    try:
        fixture(d, yang_tag=False)
        sj = os.path.join(d, "scope.json"); open(sj, "w").write('{"yang_tags": ["yang/@v0.1.2"]}')
        rc, o = run(BUILD, ["--clones", d, "--out", os.path.join(d, "m.txt"), "--scope-json", sj])
        report("B4 a named tag that does not exist: an input error (exit 2), not a smaller manifest", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    d = tempfile.mkdtemp()
    try:
        fixture(d, yang_file=False)
        sj = os.path.join(d, "scope.json"); open(sj, "w").write('{"yang_tags": ["yang/@v0.1.2"]}')
        rc, o = run(BUILD, ["--clones", d, "--out", os.path.join(d, "m.txt"), "--scope-json", sj])
        report("B5 a tag without its record file: the build is NOT complete (exit 1)", rc == 1 and "has no release/cic-yang-v0.1.2.yaml" in o, "exit=%d" % rc)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    rc, o = run(VERIFY, ["--manifest", "/nonexistent/m.txt", "--clones", "/nonexistent"])
    report("D infra: the manifest is unreadable (exit 2, not a detection)", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)
    print("self-test: %s" % ("all as expected" if not bad else "%d problem(s)" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
