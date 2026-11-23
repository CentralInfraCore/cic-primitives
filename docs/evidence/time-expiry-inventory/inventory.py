"""Inventory of what the signing-chain expiry of 2026-12-31 touches: the signed records, the verifiers, the time evidence that exists. READ-ONLY: it reads clones and certificates, it signs, stamps and
changes nothing. It produces results/inventory.json, which check_inventory.py checks against the review document.

It needs fresh clones (default branch, depth 1 is enough) of the repositories named in REPOS, in one directory, and fetches the release TAGS it lists (read-only `git fetch`). The clone commits are recorded in
the output: the inventory is a statement about THOSE commits, not about whatever the repositories say later.
Usage: inventory.py --clones DIR --out results/inventory.json [--chain DIR]
Exit: 0 ok, 2 an input cannot be read (never a result)."""
import collections, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
CHAIN_DEFAULT = os.path.join(REPO_ROOT, "evidence", "time", "digicert-2026-11-03", "cic-chain")
REGISTRY_RECORD_DIRS = ["standards", "general", "providers"]
TAGS = {"cic-primitives": ["primitives/@v0.1.5", "primitives/@v0.2.0", "primitives/@v0.2.1"],
        "cic-yang": ["yang/@v0.1.2", "yang/@v0.1.3"],
        "base-repo": ["base@0.5.0", "base@0.6.0", "golang@0.6.0", "schema-registry@0.1.0", "schemas@v0.9.0"]}
# (repo, path, label, regex, what the inventory records: every matching line number)
ANCHORS = [("cic-primitives", "tools/compiler.py", "primitives.verifier.now", r"now\s*=\s*datetime\.datetime\.now\(datetime\.timezone\.utc\)"),
           ("cic-primitives", "tools/compiler.py", "primitives.verifier.expired", r"expired on|Certificate not valid"),
           ("cic-schema-registry", "tools/registrylib/verify.py", "registry.verifier.time-words", r"not_valid|not_before|not_after|datetime|expire|time\.time|utcnow"),
           ("cic-schema-registry", "tools/registrylib/verify.py", "registry.verifier.signed-payload", r"signed_payload"),
           ("cic-schema-registry", "tools/registrylib/verify.py", "registry.verifier.embedded-root", r"embedded"),
           ("cic-schema-registry", "tools/registrylib/verify.py", "registry.verifier.ts-words", r"\bts\b"),
           ("CIC_Relay", "core/cabinet/pki_verify.go", "relay.verifier.verify-options", r"x509\.VerifyOptions\{"),
           ("CIC_Relay", "core/cabinet/pki_verify.go", "relay.verifier.current-time", r"CurrentTime")]


def sh(args, cwd=None):
    return subprocess.run(args, capture_output=True, text=True, cwd=cwd)


def cert_info(pem):
    f = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False); f.write(pem); f.close()
    try:
        r = sh(["openssl", "x509", "-in", f.name, "-noout", "-subject", "-issuer", "-dates", "-fingerprint", "-sha256"])
    finally:
        os.unlink(f.name)
    if r.returncode != 0:
        return None
    g = lambda k: (re.search(k + r"=\s*(.*)", r.stdout) or [None, None])[1]
    cn = lambda line: (re.search(r"CN\s*=\s*([^,\n]+)", line or "") or [None, None])[1]
    return {"subject_cn": cn(g("subject")), "issuer_cn": cn(g("issuer")), "not_before": g("notBefore"), "not_after": g("notAfter"), "sha256": g("sha256 Fingerprint")}


def main(argv):
    import yaml
    arg = lambda n, d: argv[argv.index(n) + 1] if n in argv and argv.index(n) + 1 < len(argv) else d
    clones, out, chain = arg("--clones", None), arg("--out", os.path.join(HERE, "results", "inventory.json")), arg("--chain", CHAIN_DEFAULT)
    try:
        assert clones and os.path.isdir(clones)
        inv = {"inventory_format": 1, "clones": {}, "chain": [], "registry": {}, "tag_records": [], "anchors": []}
        for r in ("cic-schema-registry", "cic-primitives", "CIC_Relay", "base-repo", "cic-yang"):
            inv["clones"][r] = {"head": sh(["git", "rev-parse", "HEAD"], os.path.join(clones, r)).stdout.strip(), "branch": sh(["git", "symbolic-ref", "--short", "HEAD"], os.path.join(clones, r)).stdout.strip()}
            assert len(inv["clones"][r]["head"]) == 40
        for name in ("root.pem", "source-ca.pem", "developer-ca.pem", "developer.pem"):
            ci = cert_info(open(os.path.join(chain, name), encoding="utf-8").read()); assert ci
            ci["file"] = name; inv["chain"].append(ci)
        # the records of the registry (committed, parsed, not mentions)
        rows = []
        base = os.path.join(clones, "cic-schema-registry")
        for top in REGISTRY_RECORD_DIRS:
            for dp, dn, fn in os.walk(os.path.join(base, top)):
                for f in fn:
                    if not f.endswith((".yaml", ".yml")):
                        continue
                    p = os.path.join(dp, f); t = open(p, encoding="utf-8", errors="replace").read()
                    if "cic_countersign" not in t:
                        continue
                    try:
                        d = yaml.safe_load(t)
                    except Exception:
                        continue
                    if isinstance(d, dict) and isinstance(d.get("cic_countersign"), dict):
                        cs = d["cic_countersign"]; rel = d.get("release") or {}
                        rows.append({"path": os.path.relpath(p, base), "ts": cs.get("ts"), "workflow": cs.get("workflow"), "build_hash": rel.get("build_hash"),
                                     "src_ca_not_after": (cert_info((cs.get("authority") or {}).get("certificate", "")) or {}).get("not_after")})
        ts = sorted(r["ts"] for r in rows if r["ts"])
        inv["registry"] = {"records": len(rows), "with_ts": len(ts), "ts_min": ts[0] if ts else None, "ts_max": ts[-1] if ts else None, "unique_build_hash": len({r["build_hash"] for r in rows if r["build_hash"]}),
                           "workflows": dict(collections.Counter(r["workflow"] for r in rows)), "src_ca_not_after": dict(collections.Counter(r["src_ca_not_after"] for r in rows))}
        # the release records at the tags
        for repo, tags in TAGS.items():
            cl = os.path.join(clones, repo)
            for t in tags:
                sh(["git", "fetch", "--depth", "1", "-q", "origin", "refs/tags/%s:refs/tags/%s" % (t, t)], cl)
                g = sh(["git", "grep", "-l", "cic_countersign", t, "--", "*.yaml", "*.yml"], cl)
                files = [x.split(":", 1)[1] for x in g.stdout.split() if ":" in x]
                files = [f for f in files if "schema.yaml" not in f and "/tests/" not in f and ".mypy_cache" not in f]
                found = False
                for f in files:
                    try:
                        d = yaml.safe_load(sh(["git", "show", "%s:%s" % (t, f)], cl).stdout)
                    except Exception:
                        continue
                    if not isinstance(d, dict) or not isinstance(d.get("cic_countersign"), dict):
                        continue
                    cs = d["cic_countersign"]; cb = (d.get("release") or {}).get("createdBy") or {}
                    ci = cert_info((cs.get("authority") or {}).get("certificate", "")) or {}
                    di = cert_info(cb.get("certificate", "")) or {}
                    inv["tag_records"].append({"repo": repo, "tag": t, "file": f, "format": "yaml-record", "ts": cs.get("ts"), "src_ca_not_after": ci.get("not_after"), "developer_not_after": di.get("not_after")})
                    found = True
                if not found:
                    pr = sh(["git", "show", "%s:project.yaml" % t], cl).stdout
                    try:
                        py = yaml.safe_load(pr) or {}
                        md = {}
                        for key in ("metadata", "release"):                      # the template releases keep the signature block under `metadata` (0.6.0) or `release` (0.5.0)
                            blk = py.get(key)
                            if isinstance(blk, dict) and ("buildHash" in blk or "cicSign" in blk or "sign" in blk or "cert" in blk):
                                md = blk; break
                        has = bool(md)
                    except Exception:
                        md, has = {}, False
                    cert = md.get("cert") if isinstance(md, dict) else None
                    ci = cert_info(cert) if isinstance(cert, str) and "BEGIN CERT" in cert else None
                    inv["tag_records"].append({"repo": repo, "tag": t, "file": "project.yaml" if has else None, "format": "template-project-yaml" if has else "none-found",
                                               "ts": (md.get("build_timestamp") or md.get("timestamp") if isinstance(md, dict) else None), "declared_validity_until": ((md.get("validity") or {}).get("until") if isinstance(md, dict) else None),
                                               "developer_not_after": (ci or {}).get("not_after")})
        # the verifier anchors: lines of the pinned commits that carry the time behaviour
        for repo, path, label, rx in ANCHORS:
            p = os.path.join(clones, repo, path)
            lines = [i + 1 for i, l in enumerate(open(p, encoding="utf-8").read().splitlines()) if re.search(rx, l)]
            inv["anchors"].append({"repo": repo, "path": path, "label": label, "regex": rx, "lines": lines, "commit": inv["clones"][repo]["head"]})
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump(inv, open(out, "w", encoding="utf-8"), indent=1, sort_keys=True); open(out, "a").write("\n")
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); return 2
    print("records in the registry: %d (ts %s .. %s); tag records: %d; anchors: %d" % (inv["registry"]["records"], inv["registry"]["ts_min"], inv["registry"]["ts_max"], len(inv["tag_records"]), len(inv["anchors"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
