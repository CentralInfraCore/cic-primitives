#!/usr/bin/env python3
"""Verify that imported paths still match the upstream tag they claim.

`dependency.yaml` declares, per dependency, a source repository, a pinned tag,
and the paths merged in from it:

    - name: cic-primitives
      source: github.com/CentralInfraCore/cic-primitives
      tag: primitives/@v0.1.5
      mode: remote-merge
      imported_paths: [schemas/atomic/, schemas/aggregate/, ...]

Nothing has ever checked that claim. A repository whose product is a signed,
hashed, counter-signed bundle can therefore ship a file that lies about where
it came from — and that is a present-tense defect, not a future drift risk.

This checks it: fetch each declared source at its declared tag, and compare
every file under the declared paths.

    differs         a local file's bytes differ from the tag  -> FAILURE
    missing         declared upstream, absent locally         -> FAILURE
    extra           present locally, not upstream             -> reported, not a failure

`extra` is not a failure on purpose: remote-merge seeds a path, it does not
freeze it. A repository may add its own files there. What it may not do is
change an imported file while still claiming the tag as its origin.

Seeded is not pinned
--------------------
`mode: remote-merge` means "these paths were seeded from upstream", which is
not the same as "these paths must still equal upstream". base-repo's
imported_paths lists Makefile, tools/, project.yaml and README.md — files every
consuming repository is *supposed* to customise; project.yaml literally carries
the project's own name. Enforcing equality there would be wrong.

For cic-primitives' schemas/atomic/ the opposite holds: a faithful copy of the
released primitive set is exactly the point, and a local edit is the defect.

dependency.yaml cannot express that difference today, so --require carries it:
only the named dependencies decide the exit code; the rest are reported so the
drift stays visible without blocking. When the declaration format learns to say
"pinned copy" instead of "seeded from", this flag becomes unnecessary.

Usage:
    check_provenance.py [--dependency-file dependency.yaml] [--offline]
                        [--require NAME ...]

Exit codes:
    0  every required dependency matches its tag (or nothing is declared)
    1  a required dependency has a file that differs or is missing
    2  the check could not run (no network, tag not found, bad declaration)

--offline reports UNVERIFIED and exits 2 rather than passing quietly: a
provenance check that silently succeeds when it could not look is worse than
no check at all.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

CLONE_TIMEOUT = 180


class Result:
    def __init__(self, dep: str):
        self.dep = dep
        self.differs: list[str] = []
        self.missing: list[str] = []
        self.extra: list[str] = []
        self.error: str | None = None
        # Set by check(): does this dependency decide the exit code?
        self.enforced = True

    @property
    def failed(self) -> bool:
        return bool(self.error or self.differs or self.missing)


def clone_url(source: str) -> str:
    """dependency.yaml carries a bare host/path; make it fetchable.

    https, not ssh: CI has no key, and every source in this ecosystem that is
    declared as a dependency is public. A private source will fail loudly here
    rather than being skipped.
    """
    source = source.strip().rstrip("/")
    for prefix in ("https://", "http://", "git@"):
        if source.startswith(prefix):
            return source
    return f"https://{source}.git"


def fetch_tag(source: str, tag: str, dest: Path) -> str | None:
    """Shallow-fetch one tag. Returns an error string, or None on success."""
    url = clone_url(source)
    cmd = ["git", "clone", "--quiet", "--depth", "1", "--branch", tag, url, str(dest)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=CLONE_TIMEOUT)
    except subprocess.TimeoutExpired:
        return f"timed out fetching {url} at {tag}"
    except FileNotFoundError:
        return "git is not available"
    if proc.returncode != 0:
        detail = (proc.stderr or "").strip().splitlines()
        return f"cannot fetch {url} at {tag}: {detail[-1] if detail else proc.returncode}"
    return None


def files_under(root: Path, rel: str) -> set[str]:
    """Every file under a declared path, relative to the repository root."""
    target = root / rel
    if target.is_file():
        return {rel.rstrip("/")}
    if not target.is_dir():
        return set()
    return {
        str(p.relative_to(root))
        for p in target.rglob("*")
        if p.is_file() and ".git" not in p.parts
    }


def compare(local_root: Path, up_root: Path, paths: list[str], res: Result) -> None:
    for rel in paths:
        local = files_under(local_root, rel)
        upstream = files_under(up_root, rel)
        for f in sorted(upstream - local):
            res.missing.append(f)
        for f in sorted(local - upstream):
            res.extra.append(f)
        for f in sorted(local & upstream):
            if (local_root / f).read_bytes() != (up_root / f).read_bytes():
                res.differs.append(f)


def check(dep_file: Path, offline: bool,
          required: set[str] | None) -> tuple[int, list[Result]]:
    root = dep_file.parent.resolve()
    try:
        doc = yaml.safe_load(dep_file.read_text()) or {}
    except (OSError, yaml.YAMLError) as exc:
        print(f"cannot read {dep_file}: {exc}", file=sys.stderr)
        return 2, []

    deps = [d for d in (doc.get("dependencies") or []) if isinstance(d, dict)]
    checkable = [d for d in deps if d.get("imported_paths")]
    if not checkable:
        print("no dependency declares imported_paths — nothing to verify")
        return 0, []

    results: list[Result] = []
    for dep in checkable:
        res = Result(dep.get("name", "?"))
        source, tag = dep.get("source"), dep.get("tag")
        paths = [str(p) for p in dep["imported_paths"]]

        if not source or not tag:
            res.error = "declaration has no source or no tag"
            results.append(res)
            continue
        if offline:
            res.error = f"UNVERIFIED — offline, cannot reach {source} at {tag}"
            results.append(res)
            continue

        tmp = Path(tempfile.mkdtemp(prefix="provenance-"))
        try:
            err = fetch_tag(source, tag, tmp)
            if err:
                res.error = err
            else:
                compare(root, tmp, paths, res)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        results.append(res)

    status = 0
    for r in results:
        r.enforced = required is None or r.dep in required
        if not r.enforced:
            continue
        if r.error:
            status = max(status, 2)
        elif r.differs or r.missing:
            status = max(status, 1)
    return status, results


def report(results: list[Result]) -> None:
    for r in results:
        mark = "\033[91m✗\033[0m" if r.enforced else "\033[93m!\033[0m"
        tail = "" if r.enforced else "  (reported only, not required)"
        if r.error:
            print(f"{mark} {r.dep}: {r.error}{tail}")
            continue
        if not r.failed:
            extra = f", {len(r.extra)} local addition(s)" if r.extra else ""
            print(f"\033[92m✓\033[0m {r.dep}: every imported file matches its tag{extra}")
            continue
        print(f"{mark} {r.dep}: the declared tag is not what this tree carries{tail}")
        for f in r.differs:
            print(f"    differs   {f}")
        for f in r.missing:
            print(f"    missing   {f}")
        if r.extra:
            print(f"    ({len(r.extra)} local addition(s), not a failure)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dependency-file", type=Path, default=Path("dependency.yaml"))
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--require", action="append", metavar="NAME",
                    help="only these dependencies decide the exit code; "
                         "repeatable. Omit to require all of them.")
    args = ap.parse_args()

    status, results = check(args.dependency_file, args.offline,
                            set(args.require) if args.require else None)
    report(results)
    if status == 1:
        print("\nA file under an imported path was changed locally while the "
              "declaration still names the upstream tag as its origin. Either "
              "release the change upstream and bump the tag, or take the path "
              "out of imported_paths.")
    return status


if __name__ == "__main__":
    sys.exit(main())
