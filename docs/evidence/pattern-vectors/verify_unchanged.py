"""The existing vectors are unchanged (owner condition of 2026-11-22): every vector, requirement and metadata entry of the APPROVED vector file (the merged git object of #49) is, entry by entry, equal
in the new file, and the new file differs from it only by the listed additions. An ISOLATED check, read-only. The approved bytes come from the git object, never from a file written in this session; their
SHA-256 is compared with the value stated in the PR description first.
Exit: 0 unchanged + only the expected additions, 1 a FAIL-EXPECT line, 2 infrastructure (the git object or a file is missing).
Usage: verify_unchanged.py [--new PATH] [--base-file PATH-OF-THE-APPROVED-BYTES]"""
import hashlib, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REL = "docs/design/pattern-profile-vectors/pattern-profile.yaml"
BASE_COMMIT = "9fe89b1c53eed142b53cea7449b36931b60d6573"
BASE_SHA256 = "bea100d469b427f738af397451fcb92d9b262397b95cf2c7e88d9bb6aff69607"      # also in the PR description
EXPECT_NEW_IDS = {"S-017", "S-018", "S-019", "S-020"}
EXPECT_NEW_REQ = {"R-PIN-IDENTICAL"}
fails = []


def expect(label, cond, detail=""):
    if not cond:
        fails.append(label); print("FAIL-EXPECT %s %s" % (label, detail))


def main(argv):
    import yaml
    new_path = argv[argv.index("--new") + 1] if "--new" in argv else os.path.join(REPO, REL)
    try:
        if "--base-file" in argv:
            base = open(argv[argv.index("--base-file") + 1], "rb").read()
        else:
            base = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (BASE_COMMIT, REL)], capture_output=True, check=True).stdout
        new = open(new_path, "rb").read()
    except (OSError, subprocess.CalledProcessError) as e:
        print("INCOMPLETE: the approved object or the new file cannot be read: %r" % (e,)); return 2
    expect("base.sha256", hashlib.sha256(base).hexdigest() == BASE_SHA256, "the approved bytes do not match the reference of the PR description")
    old_d, new_d = yaml.safe_load(base), yaml.safe_load(new)
    newv = {v["id"]: v for k in ("expressions", "values", "schemas") for v in new_d[k]}
    n = 0
    for k in ("expressions", "values", "schemas"):
        for v in old_d[k]:
            n += 1
            expect("vector.unchanged.%s" % v["id"], newv.get(v["id"]) == v, "the vector is missing or differs from the approved one")
    added = set(newv) - {v["id"] for k in ("expressions", "values", "schemas") for v in old_d[k]}
    expect("vector.added", added == EXPECT_NEW_IDS, "added ids %s, expected %s" % (sorted(added), sorted(EXPECT_NEW_IDS)))
    old_req = {r["id"]: r for r in old_d["requirements"]}; new_req = {r["id"]: r for r in new_d["requirements"]}
    for i, r in old_req.items():
        expect("requirement.unchanged.%s" % i, new_req.get(i) == r)
    expect("requirement.added", set(new_req) - set(old_req) == EXPECT_NEW_REQ, "added %s" % sorted(set(new_req) - set(old_req)))
    for key in ("vectors_format", "profile", "limits", "codes", "not_testable_by_vectors"):
        expect("metadata.unchanged.%s" % key, new_d.get(key) == old_d.get(key))
    # raw bytes: the approved lines are an ordered subsequence of the new lines (nothing rewritten, only inserted)
    ol, nl = base.split(b"\n"), new.split(b"\n")
    j = 0
    for line in nl:
        if j < len(ol) and line == ol[j]:
            j += 1
    expect("lines.subsequence", j == len(ol), "only %d of %d approved lines are, in order, in the new file" % (j, len(ol)))
    print("approved entries checked: %d vectors, %d requirements; added vectors %s, added requirements %s; lines %d -> %d" % (n, len(old_req), sorted(added), sorted(set(new_req) - set(old_req)), len(ol), len(nl)))
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
