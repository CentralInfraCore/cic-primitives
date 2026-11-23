"""Verify a canonical manifest (docs/en/T3-MANIFEST-CONTRACT.md) against git. READ-ONLY.
Checks (a failure is a FAIL-EXPECT line, exit 1; an unreadable input or a git failure is INCOMPLETE, exit 2, never a detection):
  form     the manifest is exactly the canonical byte form (header, count, sorted bytewise, 7 fields, no BOM, no CR, one final LF)
  records  for every line the bytes of the record at the recorded commit (read from the git object) have the recorded SHA-256 and size
  digest   with --sha256-file, the SHA-256 of the whole manifest equals the recorded digest
Usage: verify_manifest.py --manifest PATH --clones DIR [--sha256-file PATH]"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import manifestlib as M


def main(argv):
    arg = lambda n, d: argv[argv.index(n) + 1] if n in argv and argv.index(n) + 1 < len(argv) else d
    mp, clones, sf = arg("--manifest", None), arg("--clones", None), arg("--sha256-file", None)
    try:
        raw = open(mp, "rb").read(); assert clones and os.path.isdir(clones)
        recorded = open(sf, encoding="utf-8").read().split()[0] if sf else None
    except BaseException as e:
        print("INCOMPLETE: an input cannot be read: %r" % (e,)); return 2
    fails = []
    try:
        scope, count, entries = M.parse(raw)
    except M.ManifestError as e:
        print("FAIL-EXPECT form %s" % e); print("FAILED: 1 expectation(s)"); return 1
    if recorded is not None and recorded != M.digest(raw):
        fails.append("digest"); print("FAIL-EXPECT digest the recorded SHA-256 is %s, the manifest's is %s" % (recorded, M.digest(raw)))
    for rid, dg, size, repo, commit, ref, path in entries:
        try:
            data = M.git_bytes(os.path.join(clones, repo), "show", "%s:%s" % (commit, path))
        except M.ManifestError as e:
            print("INCOMPLETE: cannot read %s: %s" % (rid, e)); return 2             # git could not read: not a mismatch, never counted as a detection
        if M.digest(data) != dg or len(data) != size:
            fails.append(rid); print("FAIL-EXPECT records.%s the bytes at %s are %s (%d bytes), the manifest says %s (%d)" % (rid, commit[:12], M.digest(data), len(data), dg, size))
    print("manifest %s: %d records, %d verified against git, manifest SHA-256 %s" % ("ok" if not fails else "NOT ok", count, count - len([f for f in fails if f != "digest"]), M.digest(raw)))
    if fails:
        print("FAILED: %d expectation(s)" % len(fails)); return 1
    print("all expectations held"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
