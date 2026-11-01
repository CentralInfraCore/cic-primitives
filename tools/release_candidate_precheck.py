#!/usr/bin/env python3
"""Pre-check of a release candidate against the grammar pin of a consumer (cic-primitive-forms, corpus/pins.yaml).

The consumer pins a COMMIT and the SHA-256 of the raw blob bytes of exactly twelve files. A receipt may name a release only if that release provably contains
those twelve files. This tool proves (or refutes) that, from git objects and, after the release, from the release record. It reads; it signs, tags and publishes
nothing, and it does not verify a signature: that stays with `python tools/compiler.py verify-release <record> --trust-root <root.pem>`. The two answer different
questions (cryptographic origin, and whether the signed claim covers the pinned grammar) and neither stands in for the other.

    release_candidate_precheck.py candidate --manifest PINS --pin NAME [--commit SHA] [--release-head SHA] [--devel REF] [--version X.Y.Z] [--release-date YYYY-MM-DD]
    release_candidate_precheck.py record    --manifest PINS --pin NAME --record release/<name>-vX.Y.Z.yaml

`candidate`  before the release: the pinned commit exists and is on devel; the twelve files at it are byte-identical to the manifest; the manifest digest and the
             pin name recompute; the commit that the release will actually be cut from (--release-head: the release branch head, or the merge commit on main) holds
             the same twelve files; the version is a valid next increment; the files in which devel has moved on are listed.
`record`     after the release: the record's `provenance.source_commit` holds the twelve files byte-identical to the manifest, AND the record carries its own digest of
             every one of the twelve (the owner's requirement: source_commit stays mandatory and does not stand in for the file digests). Where the record keeps them is
             the record contract; the places read here are the spec sources and the two grammar files, nothing is invented.

Exit status 1 when a hard check fails. Exit status 0 is NOT fitness for release: read `readiness` (also `--json`), which is never `ready` while an OPEN gate exists. `OPEN` lines are gates this tool does not and cannot close (a trust anchor pinned outside the record, certificate validity at
the release date, the digest-encoding contract, the signing itself); they never turn into a pass.
"""
import argparse
import base64
import datetime
import hashlib
import json
import re
import subprocess
import sys

import yaml

PASS, FAIL, OPEN, INFO = "PASS", "FAIL", "OPEN", "INFO"
# the two files that `provenance.grammar_sha256` and `grammar_schema_sha256` digest (tools/compiler.py, _collect_provenance)
PROVENANCE_FILES = {
    "grammar_sha256": "proposals/atom-grammar/check_grammar.py",
    "grammar_schema_sha256": "proposals/atom-grammar/instance-grammar.schema.yaml",
}
COMPONENT = "primitives/"
# The profile of the CIC grammar pin: EXACTLY these twelve distinct paths (cic-primitive-forms tools/grammar_identity.py GRAMMAR_FILES). It is fixed here and never read from
# the manifest it judges: a manifest that dropped, added or swapped a file would otherwise define its own acceptable set.
PROFILE_CIC_GRAMMAR_12 = (
    "LICENSE.md",
    "proposals/atom-grammar/P0-4-ACCESS-GRAMMAR.md",
    "proposals/atom-grammar/P0-4-MIGRATION.md",
    "proposals/atom-grammar/README.md",
    "proposals/atom-grammar/access-vectors/resolution.yaml",
    "proposals/atom-grammar/access_policy.py",
    "proposals/atom-grammar/check_grammar.py",
    "proposals/atom-grammar/instance-grammar.schema.yaml",
    "schemas/aggregate/policy-surface.yaml",
    "schemas/atomic/access.yaml",
    "schemas/atomic/role.yaml",
    "schemas/atomic/shape.yaml",
)
PROFILES = {"cic-grammar-12": PROFILE_CIC_GRAMMAR_12, "none": None}


class Report:
    def __init__(self):
        self.lines = []

    def add(self, status, check, detail=""):
        self.lines.append((status, check, detail))

    def failed(self):
        return any(s == FAIL for s, _, _ in self.lines)

    def readiness(self):
        """'failed' when a check failed; otherwise 'checks_passed_gates_open'. This tool never returns 'ready': an OPEN gate is not one it can close, and exit status 0 is
        never to be read as fitness for release."""
        if self.failed():
            return "failed"
        return "checks_passed_gates_open" if any(s == OPEN for s, _, _ in self.lines) else "checks_passed"

    def render(self):
        return "\n".join(f"{s:5} {c}" + (f": {d}" if d else "") for s, c, d in self.lines)


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.decode(errors='replace').strip()}")
    return r


def blob(repo, commit, path):
    """-> the raw bytes of `path` at `commit`, or None when it is not there."""
    r = git(repo, "show", f"{commit}:{path}", check=False)
    return r.stdout if r.returncode == 0 else None


def sorted_entries(entries):
    """The order of the manifest: the UTF-8 bytes of the PATH, not of the whole line."""
    return sorted(entries, key=lambda e: e[0].encode("utf-8"))


def manifest_digest(entries):
    text = "".join(f"{sha}  {path}\n" for path, sha in sorted_entries(entries))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_pin(manifest_path, name):
    with open(manifest_path, encoding="utf-8") as fh:
        pins = yaml.safe_load(fh)["grammar"]
    if name not in pins:
        raise SystemExit(f"the manifest has no pin {name!r} (it has {sorted(pins)})")
    return pins[name]


def b64_to_hex(b64):
    """The same 32 bytes in the other encoding. A re-encoding for this check only: it is NOT the contract of the receipt field (that is a separate unit)."""
    return base64.b64decode(b64, validate=True).hex()


def check_files(report, repo, commit, pin, label):
    """The twelve files at `commit` are the manifest's. -> the {path: sha256 hex} actually found (a path that is absent or differs is a FAIL)."""
    found, bad = {}, 0
    for f in pin["files"]:
        data = blob(repo, commit, f["path"])
        if data is None:
            report.add(FAIL, f"{label}: {f['path']}", "absent at the commit")
            bad += 1
            continue
        got = hashlib.sha256(data).hexdigest()
        found[f["path"]] = got
        if got != f["sha256"]:
            report.add(FAIL, f"{label}: {f['path']}", f"pinned {f['sha256'][:12]}..., at the commit {got[:12]}...")
            bad += 1
    if not bad:
        report.add(PASS, f"{label}: all {len(pin['files'])} files are byte-identical to the manifest")
    return found


def check_profile(report, pin, profile):
    """The pin set is the profile's set: exactly the listed paths, each once. 'none' is the general tool with no profile (a stated choice, not a default of silence)."""
    want = PROFILES[profile]
    paths = [f["path"] for f in pin["files"]]
    if want is None:
        report.add(INFO, "profile", "none: the manifest's own file set is accepted as it is")
        return
    problems = []
    dup = sorted({p for p in paths if paths.count(p) > 1})
    if dup:
        problems.append("repeated: " + ", ".join(dup))
    missing = [p for p in want if p not in paths]
    extra = sorted(p for p in set(paths) if p not in want)
    if missing:
        problems.append("missing: " + ", ".join(missing))
    if extra:
        problems.append("not in the profile: " + ", ".join(extra))
    if problems:
        report.add(FAIL, f"profile {profile}: the pin set is not the {len(want)} files of the profile", " | ".join(problems))
    else:
        report.add(PASS, f"profile {profile}: the pin set is exactly the {len(want)} files of the profile")


def check_manifest_arithmetic(report, pin, name):
    entries = [(f["path"], f["sha256"]) for f in pin["files"]]
    got = manifest_digest(entries)
    if got != pin["manifest_sha256"]:
        report.add(FAIL, "manifest digest", f"recomputed {got}, pinned {pin['manifest_sha256']}")
    else:
        report.add(PASS, "manifest digest recomputes from the twelve lines")
    want = f"cic-primitives-{pin['commit'][:7]}-{pin['manifest_sha256'][:8]}"
    if name != want:
        report.add(FAIL, "pin name", f"{name!r} is not <repo>-<commit7>-<manifest8> = {want!r}")
    else:
        report.add(PASS, "pin name carries the commit and the manifest digest")


def parse_version(text):
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", text)
    return tuple(int(x) for x in m.groups()) if m else None


def valid_next(new, tags):
    """The rule of tools/compiler.py: the next patch, minor (patch 0) or major (minor and patch 0) of the latest tag; any version when there is no tag."""
    latest = max((v for v in (parse_version(t.split("@v")[-1]) for t in tags) if v), default=None)
    if latest is None:
        return True, "no earlier tag"
    allowed = {(latest[0], latest[1], latest[2] + 1), (latest[0], latest[1] + 1, 0), (latest[0] + 1, 0, 0)}
    return new in allowed, "latest %d.%d.%d, allowed %s" % (*latest, ", ".join(".".join(map(str, a)) for a in sorted(allowed)))


def candidate(args, report):
    repo, pin = args.repo, load_pin(args.manifest, args.pin)
    commit = args.commit or pin["commit"]
    report.add(INFO, "candidate", f"{commit}")
    if commit != pin["commit"]:
        report.add(FAIL, "candidate commit", f"{commit} is not the pinned commit {pin['commit']}: a different commit is a different pin until the files are proved identical (--release-head)")
    check_profile(report, pin, args.profile)
    check_manifest_arithmetic(report, pin, args.pin)
    if git(repo, "cat-file", "-e", f"{commit}^{{commit}}", check=False).returncode != 0:
        report.add(FAIL, "candidate commit", "does not exist in this repository")
        return
    if git(repo, "merge-base", "--is-ancestor", commit, args.devel, check=False).returncode == 0:
        report.add(PASS, f"candidate commit is on {args.devel}")
    else:
        report.add(FAIL, f"candidate commit is on {args.devel}", "it is not an ancestor")
    check_files(report, repo, commit, pin, "candidate")

    # the release is not cut from the candidate commit itself: the record's source_commit is the head the release runs on (the merge commit of the release branch)
    if args.release_head:
        check_files(report, repo, args.release_head, pin, "release head")
        diff = git(repo, "diff", "--name-only", commit, args.release_head).stdout.decode().split()
        outside = [p for p in diff if p not in {f["path"] for f in pin["files"]}]
        report.add(INFO, "release head differs from the candidate in", ", ".join(outside) if outside else "nothing")
    else:
        report.add(OPEN, "release head", "not given: the source_commit of the record will be the head the release runs on, and the twelve files have to be proved there too")

    # devel has moved on: a release cut from its head would not be the pin
    moved = [f["path"] for f in pin["files"] if blob(repo, args.devel, f["path"]) != blob(repo, commit, f["path"])]
    if moved:
        report.add(INFO, f"{args.devel} has moved on in pinned files", ", ".join(moved) + ": a release cut from its head is NOT the pin")
    else:
        report.add(INFO, f"{args.devel} holds the pinned files unchanged")

    if args.version:
        new = parse_version(args.version)
        tags = git(repo, "tag", "--list", f"{COMPONENT}@v*.*.*").stdout.decode().split()
        if new is None:
            report.add(FAIL, "version", f"{args.version!r} is not X.Y.Z")
        else:
            ok, why = valid_next(new, tags)
            report.add(PASS if ok else FAIL, f"version {args.version} is a valid next increment", why)
            report.add(INFO, "release branch", f"{COMPONENT}releases/v{args.version}")
    else:
        report.add(OPEN, "version", "not given")
    gates(report, args.release_date)


def gates(report, release_date, record_mode=False):
    if not record_mode:
        report.add(OPEN, "record digest coverage", "the record has to carry its own digest of all 12 pinned files and the algorithm; the present compiler digests the schema sources and two "
                   "grammar files, so at most 6 of the 12 by construction. A record contract change, not decided or made here; until then no candidate is complete")
    report.add(OPEN, "manifest origin", "the recomputed manifest digest shows consistency, not that the manifest comes from the entitled consumer: that is not shown by this tool")
    report.add(OPEN, "trust anchor", "a CIC root pinned OUTSIDE the record (verify-release --trust-root) is not supplied by this tool")
    report.add(OPEN, "signer authority", "the release issuer certificate is not chained to anything in the record; whether the countersignature alone authorizes a release is not decided")
    if release_date:
        report.add(OPEN, "certificate validity", f"has to be shown for {release_date} (the certificates of v0.2.0 expire 2026-12-31)")
    else:
        report.add(OPEN, "certificate validity", "no --release-date given; the certificates of v0.2.0 expire 2026-12-31")
    report.add(OPEN, "digest encoding", "the base64 -> sha256:hex mapping of the record digests is not a contract yet (Forms unit with Rust/Go golden tests)")
    report.add(OPEN, "signing and publishing", "HOLD by the owner until the gates above are shown")


def record(args, report):
    repo, pin = args.repo, load_pin(args.manifest, args.pin)
    with open(args.record, encoding="utf-8") as fh:
        rec = yaml.safe_load(fh)
    if rec.get("kind") != "PrimitiveRelease":
        report.add(FAIL, "record", f"kind is {rec.get('kind')!r}, not PrimitiveRelease")
        return
    prov = rec.get("provenance") or {}
    commit = prov.get("source_commit")
    report.add(INFO, "record", f"version {rec.get('version')}, source_commit {commit}")
    check_profile(report, pin, args.profile)
    check_manifest_arithmetic(report, pin, args.pin)
    if not commit:
        report.add(FAIL, "source_commit", "the record carries none")
        return
    if git(repo, "cat-file", "-e", f"{commit}^{{commit}}", check=False).returncode != 0:
        report.add(FAIL, "source_commit", "does not exist in this repository")
        return
    found = check_files(report, repo, commit, pin, "source_commit")

    # what the record digests itself, and what rests on the source commit alone
    by_path = {f["path"]: f["sha256"] for f in pin["files"]}
    digested = {}
    for spec in rec.get("specs", []):
        digested[spec["source_path"]] = ("spec meta_hash", spec["meta_hash"])
    for key, path in PROVENANCE_FILES.items():
        if prov.get(key):
            digested[path] = (f"provenance.{key}", prov[key])
    covered, alone, wrong = [], [], []
    for path, hexsha in by_path.items():
        if path not in digested:
            alone.append(path)
            continue
        where, b64 = digested[path]
        try:
            same = b64_to_hex(b64) == hexsha
        except Exception:
            same = False
        if same:
            covered.append(f"{path} ({where})")
        else:
            wrong.append(path)
            report.add(FAIL, f"record digest of {path}", f"{where} does not equal the pinned file")
    report.add(INFO, f"files the record digests itself ({len(covered)} of {len(by_path)})", "; ".join(covered) or "none")
    # the owner's requirement: the record carries its own digest of EVERY pinned file; source_commit stays mandatory and does not stand in for them
    # coverage is PASS only when every pinned file has a digest in the record AND that digest equals the pinned bytes: a present but wrong digest is not coverage
    if alone or wrong:
        parts = []
        if alone:
            parts.append(f"{len(alone)} have no digest of their own in the record and rest on the source commit alone: " + "; ".join(alone))
        if wrong:
            parts.append(f"{len(wrong)} have a digest that is not the pinned file's: " + "; ".join(wrong))
        report.add(FAIL, f"record digest coverage: {len(covered)} of {len(by_path)} present and equal", " | ".join(parts))
    else:
        report.add(PASS, f"record digest coverage: all {len(by_path)} pinned files have a digest of their own in the record, and each equals the pinned file")
    gates(report, None, record_mode=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["candidate", "record"])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--manifest", required=True, help="the consumer's pins.yaml (cic-primitive-forms corpus/pins.yaml)")
    ap.add_argument("--pin", required=True, help="the pin name in the manifest")
    ap.add_argument("--commit", help="candidate commit (default: the pinned one)")
    ap.add_argument("--release-head", help="the commit the release will run on (the head of the release branch or the merge commit)")
    ap.add_argument("--devel", default="origin/devel")
    ap.add_argument("--version")
    ap.add_argument("--release-date", type=datetime.date.fromisoformat)
    ap.add_argument("--record")
    ap.add_argument("--profile", choices=sorted(PROFILES), default="cic-grammar-12", help="the pin set the manifest has to be exactly (default: the 12 files of the CIC grammar pin)")
    ap.add_argument("--json", action="store_true", help="print the result as JSON with a machine-readable readiness")
    args = ap.parse_args(argv)
    report = Report()
    try:
        if args.mode == "candidate":
            candidate(args, report)
        else:
            if not args.record:
                ap.error("record mode needs --record")
            record(args, report)
    except RuntimeError as e:
        report.add(FAIL, "git", str(e))
    report.add(INFO, "scope", "PASS lines prove byte-identity and consistency of the named files only; they do not prove the signer's authority, the release's authenticity "
               "or the trust anchor (the OPEN lines), and a 12 of 12 PASS is not a statement that a release is genuine")
    readiness = report.readiness()
    if args.json:
        print(json.dumps({"readiness": readiness, "failed": report.failed(), "open_gates": [c for st, c, _ in report.lines if st == OPEN],
                          "lines": [{"status": st, "check": c, "detail": d} for st, c, d in report.lines]}, ensure_ascii=False, indent=1))
    else:
        print(report.render())
        print(f"readiness: {readiness}")
    return 1 if report.failed() else 0


if __name__ == "__main__":
    sys.exit(main())
