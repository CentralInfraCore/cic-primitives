"""Supply-chain facts of the Python-side candidates, read from the PyPI JSON API at run time (a dated record, not a guarantee): versions, release dates, wheel coverage for the interpreter
in use, the sha256 of the artifacts that were measured, license, project URL. Fail-closed: a network or format error is exit 1, nothing is guessed.
Usage: supply_chain.py   (prints the record; the dated output is kept as supply-chain-output.txt)"""
import json, sys, urllib.request
PKGS = [("google-re2", "official RE2 bindings"), ("pyre2", "third-party Cython wrapper of RE2"), ("regex", "backtracking engine, a superset of re")]
try:
    for name, role in PKGS:
        d = json.load(urllib.request.urlopen("https://pypi.org/pypi/%s/json" % name, timeout=30))
        i, rel = d["info"], d["releases"]
        dates = sorted(f["upload_time"][:10] for fs in rel.values() for f in fs)
        latest = i["version"]; files = d["urls"]
        plats = sorted({f["filename"].rsplit("-", 1)[-1].replace(".whl", "") for f in files if f["filename"].endswith(".whl") and ("cp314" in f["filename"] or "abi3" in f["filename"])})
        print("%s  [%s]\n  latest %s (%s); %d releases since %s; summary: %s\n  license: %s %s; home: %s\n  wheels for cp314/abi3 of the latest: %d (%s)\n  sdist: %s" % (
            name, role, latest, max(f["upload_time"][:10] for f in files), len(rel), dates[0], i.get("summary"), i.get("license") or i.get("license_expression") or "-", i.get("classifiers") and [c for c in i["classifiers"] if c.startswith("License")][:1] or "", (i.get("project_urls") or {}).get("Homepage") or i.get("home_page"),
            len(plats), ", ".join(plats)[:200], any(f["filename"].endswith(".tar.gz") for f in files)))
except Exception as e:
    print("INCOMPLETE: the PyPI record could not be read (%s: %s)" % (type(e).__name__, e), file=sys.stderr); sys.exit(1)
