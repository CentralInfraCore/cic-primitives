"""Scans every integer of the historical release records and of the fixtures for a magnitude above 2^53 - 1. FAIL-CLOSED (review #44 F1).

An incomplete scan is never a zero: a git command with a non-zero return code, a missing or empty record, an unreadable or non-mapping YAML
document, a required record not processed, or no fixture found at all makes the exit code 1 and prints why. Exit codes:
  0  complete scan, no integer beyond the bound     1  the scan is incomplete (what is wrong is printed)     3  complete scan, at least one finding
Usage: scan_integers.py [--repo DIR]        scan_integers.py --self-test
The four records the measurement requires are listed in REQUIRED; every other release/*.yaml of those tags is scanned too."""
import glob, os, subprocess, sys, tempfile, yaml

LIM = 2**53 - 1
REQUIRED = (("primitives/@v0.1.4", "release/cic-primitives-v0.1.4.yaml"), ("primitives/@v0.1.5", "release/cic-primitives-v0.1.5.yaml"),
            ("primitives/@v0.2.0", "release/cic-primitives-v0.2.0.yaml"), ("primitives/@v0.2.1", "release/cic-primitives-v0.2.1.yaml"))
FIXTURE_ROOTS = ("tests/fixtures", "docs/evidence/release-schema-draft-probe")


class Incomplete(Exception):
    pass


def ints(x, path="$"):
    if isinstance(x, bool):
        return
    if isinstance(x, int):
        yield path, x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from ints(v, path + "." + str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from ints(v, "%s[%d]" % (path, i))


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo] + list(args), capture_output=True)
    if r.returncode != 0:
        raise Incomplete("git %s failed (rc=%d): %s" % (" ".join(args), r.returncode, r.stderr.decode("utf-8", "replace").strip()))
    return r.stdout


def report(name, data, out):
    """Parses one file; returns the number of findings. Any problem raises Incomplete."""
    if not data.strip():
        raise Incomplete("%s is empty" % name)
    try:
        docs = list(yaml.safe_load_all(data.decode("utf-8") if isinstance(data, bytes) else data))
    except Exception as e:
        raise Incomplete("%s is not readable YAML (%s)" % (name, type(e).__name__))
    if not docs or not all(isinstance(d, (dict, list)) for d in docs):
        raise Incomplete("%s holds no mapping or list document" % name)
    allv = [(p, v) for d in docs for p, v in ints(d)]
    mx = max(allv, key=lambda t: abs(t[1])) if allv else None
    over = [t for t in allv if abs(t[1]) > LIM]
    out.append("%-62s integers=%d max_abs=%s beyond_2^53-1=%d" % (name, len(allv), (abs(mx[1]), mx[0]) if mx else "-", len(over)))
    return len(over)


def scan(repo, required=REQUIRED, roots=FIXTURE_ROOTS):
    out, findings, done = [], 0, set()
    tags = []
    for tag, _ in required:
        if tag not in tags:
            tags.append(tag)
    for tag in tags:
        names = git(repo, "ls-tree", "-r", "--name-only", tag, "--", "release").decode().split("\n")
        names = [n for n in names if n.endswith(".yaml")]
        need = [p for t, p in required if t == tag]
        for p in need:
            if p not in names:
                raise Incomplete("the required record %s is not in the tag %s" % (p, tag))
        for f in names:
            findings += report("%s:%s" % (tag, f), git(repo, "show", "%s:%s" % (tag, f)), out)
            done.add((tag, f))
    missing = [r for r in required if r not in done]
    if missing:
        raise Incomplete("required records not processed: %s" % missing)
    n = 0
    for root in roots:
        files = sorted(glob.glob(os.path.join(repo, root, "**", "*.yaml"), recursive=True))
        if not files:
            raise Incomplete("no fixture found under %s" % root)
        for f in files:
            with open(f, "rb") as fh:
                findings += report(os.path.relpath(f, repo), fh.read(), out)
            n += 1
    out.append("required records processed: %d of %d; fixture files scanned: %d; integers beyond 2^53-1 in all scanned files: %d" % (len(done & set(required)), len(required), n, findings))
    return out, findings


def main(repo):
    try:
        out, findings = scan(repo)
    except Incomplete as e:
        print("INCOMPLETE SCAN: %s" % e)
        return 1
    # every tag record is printed (also with no integer); only fixture lines with no integer are left out
    print("\n".join(l for l in out if l.startswith("primitives/@") or "integers=0 " not in l))
    return 3 if findings else 0


def self_test():
    """Plants the failures a scan must not turn into a zero, in a throw-away repository, and requires exit 1 (or 3 for a real finding)."""
    def sh(d, *a):
        subprocess.run(["git", "-C", d] + list(a), check=True, capture_output=True)

    def build(files, tags=("t1",)):
        d = tempfile.mkdtemp()
        sh(d, "init", "-q"); sh(d, "config", "user.email", "x@x"); sh(d, "config", "user.name", "x"); sh(d, "config", "commit.gpgsign", "false")
        for p, data in files.items():
            os.makedirs(os.path.dirname(os.path.join(d, p)), exist_ok=True)
            open(os.path.join(d, p), "wb").write(data)
        sh(d, "add", "-A"); sh(d, "commit", "-q", "-m", "x")
        for t in tags:
            sh(d, "tag", t)
        return d
    req = (("t1", "release/a.yaml"),)
    fx = {"fx/f.yaml": b"a: 1\n"}
    cases = [
        ("a complete scan with no finding", dict(fx, **{"release/a.yaml": b"envelope: 3\n"}), req, tuple(("fx",)), 0),
        ("a real finding (2^53)", dict(fx, **{"release/a.yaml": b"n: 9007199254740992\n"}), req, ("fx",), 3),
        ("a negative finding (-2^53)", dict(fx, **{"release/a.yaml": b"n: -9007199254740992\n"}), req, ("fx",), 3),
        ("the bound itself is no finding", dict(fx, **{"release/a.yaml": b"n: 9007199254740991\n"}), req, ("fx",), 0),
        ("the tag does not exist (git fails)", dict(fx, **{"release/a.yaml": b"a: 1\n"}), (("nope", "release/a.yaml"),), ("fx",), 1),
        ("the required record is absent from the tag", dict(fx, **{"release/b.yaml": b"a: 1\n"}), req, ("fx",), 1),
        ("the required record is empty", dict(fx, **{"release/a.yaml": b""}), req, ("fx",), 1),
        ("the required record is not YAML", dict(fx, **{"release/a.yaml": b"a: [1, 2\n"}), req, ("fx",), 1),
        ("the required record is a bare scalar", dict(fx, **{"release/a.yaml": b"just text\n"}), req, ("fx",), 1),
        ("no fixture is found", {"release/a.yaml": b"a: 1\n"}, req, ("fx",), 1),
        ("a fixture is unreadable YAML", dict({"fx/f.yaml": b"a: [1\n"}, **{"release/a.yaml": b"a: 1\n"}), req, ("fx",), 1),
        ("an incomplete scan hidden behind a finding elsewhere", dict(fx, **{"release/a.yaml": b"n: 9007199254740992\n"}), (("t1", "release/a.yaml"), ("t1", "release/gone.yaml")), ("fx",), 1),
    ]
    bad = 0
    for name, files, required, roots, want in cases:
        d = build(files)
        try:
            out, findings = scan(d, required, roots)
            got = 3 if findings else 0
        except Incomplete:
            got = 1
        print("%-60s expected %d got %d %s" % (name, want, got, "ok" if got == want else "WRONG"))
        bad += got != want
    print("%d of %d cases as expected" % (len(cases) - bad, len(cases)))
    return 1 if bad else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    repo = sys.argv[sys.argv.index("--repo") + 1] if "--repo" in sys.argv else "."
    sys.exit(main(repo))
