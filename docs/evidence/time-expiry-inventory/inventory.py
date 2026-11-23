"""Inventory of what the signing-chain expiry of 2026-12-31 touches: the signed records, their certificates and boundaries, the verifiers, the time evidence that exists. READ-ONLY: it reads clones and
certificates, it signs, stamps and changes nothing. It produces results/inventory.json, which check_inventory.py checks against the review document.

It needs fresh clones (default branch, depth 1 is enough) of the repositories named in REPOS, in one directory, and fetches the release TAGS it lists (read-only `git fetch`). The clone commits are recorded in
the output: the inventory is a statement about THOSE commits.

COMPLETENESS (review F2 of the T3 package). Every element of the declared scope gets a TYPED status, and the inventory is `complete` only if no element is an error:
  ok                  read and understood
  absent              looked for, explicitly not there (a tag without a signature block, a file that does not exist at a tag): a result, not a failure
  not_found           a tag the scope names does not exist in the remote: an error (the scope claims it)
  fetch_error         the tag exists (or could not be listed) but could not be fetched: an error, never mixed with `absent`
  parse_error         a file that mentions the signature blocks could not be parsed (YAML, certificate): an error, listed by path, never skipped
  read_error          git itself failed to read the tag's content (`git grep` with an exit code other than 0 or 1, `git show` or `git ls-tree` failing): an error, never read as "no match" or "absent"
  unknown             a fact that could not be extracted (a certificate in a form the tool cannot read): reported as UNKNOWN downstream, never replaced by another date
Exit: 0 the inventory is complete, 1 it was produced but is NOT complete (a scope element is an error; the output says which), 2 an input cannot be read (never a result).
THE CLOCK (review F2b): the state of a class is judged at a full UTC INSTANT (`--as-of YYYY-MM-DDTHH:MM:SSZ`, default now), not at a day: a boundary is the last second a certificate is valid, so a class is `ended` only when the
instant is AFTER its boundary (the boundary second itself is still `open`).
Usage: inventory.py --clones DIR --out results/inventory.json [--chain DIR] [--as-of YYYY-MM-DDTHH:MM:SSZ] [--scope-json PATH]"""
import collections, datetime, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
CHAIN_DEFAULT = os.path.join(REPO_ROOT, "evidence", "time", "digicert-2026-11-03", "cic-chain")
REGISTRY_RECORD_DIRS = ["standards", "general", "providers"]
REPOS = ("cic-schema-registry", "cic-primitives", "CIC_Relay", "base-repo", "cic-yang")
TAGS = {"cic-primitives": ["primitives/@v0.1.5", "primitives/@v0.2.0", "primitives/@v0.2.1"],
        "cic-yang": ["yang/@v0.1.2", "yang/@v0.1.3"],
        "base-repo": ["base@0.5.0", "base@0.6.0", "golang@0.6.0", "schema-registry@0.1.0", "schemas@v0.9.0"]}
ANCHORS = [("cic-primitives", "tools/compiler.py", "primitives.verifier.now", r"now\s*=\s*datetime\.datetime\.now\(datetime\.timezone\.utc\)"),
           ("cic-primitives", "tools/compiler.py", "primitives.verifier.expired", r"expired on|Certificate not valid"),
           ("cic-schema-registry", "tools/registrylib/verify.py", "registry.verifier.time-words", r"not_valid|not_before|not_after|datetime|expire|time\.time|utcnow"),
           ("cic-schema-registry", "tools/registrylib/verify.py", "registry.verifier.signed-payload", r"signed_payload"),
           ("cic-schema-registry", "tools/registrylib/verify.py", "registry.verifier.embedded-root", r"embedded"),
           ("cic-schema-registry", "tools/registrylib/verify.py", "registry.verifier.ts-words", r"\bts\b"),
           ("CIC_Relay", "core/cabinet/pki_verify.go", "relay.verifier.verify-options", r"x509\.VerifyOptions\{"),
           ("CIC_Relay", "core/cabinet/pki_verify.go", "relay.verifier.current-time", r"CurrentTime")]
OK_STATUSES = {"ok", "absent"}
MONTHS = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def sh(args, cwd=None):
    return subprocess.run(args, capture_output=True, text=True, cwd=cwd)


def parse_gmt(text):
    """'Dec 31 13:22:39 2026 GMT' -> 'YYYY-MM-DDTHH:MM:SSZ' or None"""
    m = re.search(r"([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d\d):(\d\d):(\d\d)\s+(\d{4})", text or "")
    if not m or m.group(1) not in MONTHS:
        return None
    return "%s-%02d-%02dT%s:%s:%sZ" % (m.group(6), MONTHS[m.group(1)], int(m.group(2)), m.group(3), m.group(4), m.group(5))


def cert_info(text):
    """a certificate in PEM or in the openssl text dump -> {subject_cn, issuer_cn, not_after (ISO UTC), sha256?} or None (UNKNOWN)"""
    if not isinstance(text, str):
        return None
    cn = lambda line: (re.search(r"CN\s*=\s*([^,\n]+)", line or "") or [None, None])[1]
    if "BEGIN CERTIFICATE" in text:
        f = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False); f.write(text); f.close()
        try:
            r = sh(["openssl", "x509", "-in", f.name, "-noout", "-subject", "-issuer", "-enddate", "-fingerprint", "-sha256"])
        finally:
            os.unlink(f.name)
        if r.returncode == 0:
            g = lambda k: (re.search(k + r"=\s*(.*)", r.stdout) or [None, None])[1]
            end = parse_gmt(g("notAfter"))
            if end:
                return {"subject_cn": cn(g("subject")), "issuer_cn": cn(g("issuer")), "not_after": end, "sha256": g("sha256 Fingerprint")}
    m = re.search(r"Not After\s*:\s*(.*)", text)                            # the openssl text dump kept in some records
    s, i = re.search(r"Subject:\s*(.*)", text), re.search(r"Issuer:\s*(.*)", text)
    end = parse_gmt(m.group(1)) if m else None
    if end:
        return {"subject_cn": cn(s.group(1) if s else ""), "issuer_cn": cn(i.group(1) if i else ""), "not_after": end, "sha256": None}
    return None


def walk_certs(obj, path=""):
    """every string of a parsed document that looks like a certificate, with its path"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_certs(v, path + "." + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_certs(v, path + "[%d]" % i)
    elif isinstance(obj, str) and ("BEGIN CERTIFICATE" in obj or "Certificate:\n" in obj):
        yield path, obj


def record_certs(d):
    """the certificates a record carries: [{role, info or None}] by role (developer, authority, root, other)"""
    out = []
    rel = d.get("release") or {}; cs = d.get("cic_countersign") or {}
    for role, text in (("developer", (rel.get("createdBy") or {}).get("certificate")), ("authority", (cs.get("authority") or {}).get("certificate")), ("root", (cs.get("authority") or {}).get("root_certificate"))):
        if text is not None:
            out.append({"role": role, "info": cert_info(text)})
    return out


def class_summary(cid, label, items, as_of):
    """items: [{certs: [{role, info}], declared_until: ISO or None}] -> the boundaries of a class, with UNKNOWN kept apart"""
    ends, unknown, declared = [], [], []
    for it in items:
        for c in it["certs"]:
            if c["info"]:
                ends.append((c["info"]["not_after"], c["role"], c["info"]["subject_cn"]))
            else:
                unknown.append(c["role"])
        if it.get("declared_until"):
            declared.append(it["declared_until"])
    earliest = min(ends) if ends else None
    d_min = min(declared) if declared else None
    cands = [x for x in ([earliest[0]] if earliest else []) + ([d_min] if d_min else [])]
    boundary = min(cands) if cands else None
    ended = bool(boundary) and boundary < as_of                         # both are full UTC instants of the same format; the boundary second itself is still valid
    state = "ended" if ended else ("UNKNOWN" if (unknown or not cands) else "open")
    return {"id": cid, "label": label, "records": len(items), "earliest_cert_end": ({"not_after": earliest[0], "role": earliest[1], "subject_cn": earliest[2]} if earliest else None),
            "declared_validity_until_min": d_min, "boundary": boundary, "unknown_certs": dict(collections.Counter(unknown)), "state_at_as_of": state}


def main(argv):
    import yaml
    arg = lambda n, d: argv[argv.index(n) + 1] if n in argv and argv.index(n) + 1 < len(argv) else d
    clones, out, chain = arg("--clones", None), arg("--out", os.path.join(HERE, "results", "inventory.json")), arg("--chain", CHAIN_DEFAULT)
    as_of = arg("--as-of", datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    tags = TAGS
    try:
        assert clones and os.path.isdir(clones) and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", as_of)
        if "--scope-json" in argv:
            tags = json.load(open(arg("--scope-json", None), encoding="utf-8"))
        inv = {"inventory_format": 2, "as_of": as_of, "clones": {}, "chain": [], "scope": [], "registry": {}, "classes": [], "tag_records": [], "anchors": []}
        scope = lambda i, kind, status, detail="": inv["scope"].append({"id": i, "kind": kind, "status": status, "detail": detail})
        for r in REPOS:
            cl = os.path.join(clones, r)
            head = sh(["git", "rev-parse", "HEAD"], cl).stdout.strip()
            assert len(head) == 40, "no clone of %s" % r
            inv["clones"][r] = {"head": head, "branch": sh(["git", "symbolic-ref", "--short", "HEAD"], cl).stdout.strip()}
        for name in ("root.pem", "source-ca.pem", "developer-ca.pem", "developer.pem"):
            ci = cert_info(open(os.path.join(chain, name), encoding="utf-8").read())
            scope("chain:" + name, "chain-certificate", "ok" if ci else "parse_error", name)
            if ci:
                ci["file"] = name; inv["chain"].append(ci)
        # ---- the registry: every file of the record areas that mentions the signature blocks is parsed, a parse error or explicitly not a record
        base = os.path.join(clones, "cic-schema-registry")
        reg_items, parse_errors, mention_files, not_records = [], [], 0, 0
        for top in REGISTRY_RECORD_DIRS:
            for dp, dn, fn in os.walk(os.path.join(base, top)):
                for f in sorted(fn):
                    if not f.endswith((".yaml", ".yml")):
                        continue
                    p = os.path.join(dp, f)
                    try:
                        t = open(p, encoding="utf-8").read()
                    except BaseException:
                        parse_errors.append(os.path.relpath(p, base)); mention_files += 1; continue
                    if "cic_countersign" not in t:
                        continue
                    mention_files += 1
                    try:
                        d = yaml.safe_load(t)
                    except BaseException:
                        parse_errors.append(os.path.relpath(p, base)); continue
                    if isinstance(d, dict) and isinstance(d.get("cic_countersign"), dict):
                        cs = d["cic_countersign"]; rel = d.get("release") or {}
                        reg_items.append({"path": os.path.relpath(p, base), "ts": cs.get("ts"), "workflow": cs.get("workflow"), "build_hash": rel.get("build_hash"), "certs": record_certs(d), "declared_until": None})
                    else:
                        not_records += 1
        outside = sorted(e for e in os.listdir(base) if e not in REGISTRY_RECORD_DIRS and not e.startswith("."))
        ts = sorted(r["ts"] for r in reg_items if r["ts"])
        inv["registry"] = {"records": len(reg_items), "with_ts": len(ts), "ts_min": ts[0] if ts else None, "ts_max": ts[-1] if ts else None, "unique_build_hash": len({r["build_hash"] for r in reg_items if r["build_hash"]}),
                           "workflows": dict(collections.Counter(r["workflow"] for r in reg_items)), "files_mentioning_blocks": mention_files, "parse_errors": parse_errors, "not_a_record": not_records,
                           "scanned_dirs": REGISTRY_RECORD_DIRS, "not_scanned_top_level": outside,
                           "not_scanned_reason": "outside the record areas (documentation, tests, tools, configuration, caches); the signed records live under the scanned directories"}
        scope("registry-scan", "registry-record-scan", "ok" if not parse_errors else "parse_error", "%d files mention the blocks: %d records, %d parse errors, %d not records" % (mention_files, len(reg_items), len(parse_errors), not_records))
        inv["classes"].append(class_summary("registry", "cic-schema-registry countersigned records", [{"certs": r["certs"], "declared_until": None} for r in reg_items], as_of))
        reg_head, reg_branch = inv["clones"]["cic-schema-registry"]["head"], inv["clones"]["cic-schema-registry"]["branch"]
        inv["open_records"] = [{"id": "cic-schema-registry:" + r["path"], "repo": "cic-schema-registry", "path": r["path"], "ref": "branch:" + reg_branch, "commit": reg_head} for r in sorted(reg_items, key=lambda r: r["path"].encode("utf-8"))]
        # ---- the release records at the tags: a typed status per tag
        cls_items = {"primitives": [], "yang": []}; tpl = []
        for repo, tlist in tags.items():
            cl = os.path.join(clones, repo)
            for t in tlist:
                sid = "tag:%s:%s" % (repo, t)
                ls = sh(["git", "ls-remote", "--tags", "origin", "refs/tags/%s" % t], cl)
                if ls.returncode != 0:
                    scope(sid, "release-tag", "fetch_error", "git ls-remote failed: %s" % ls.stderr.strip()[:120]); continue
                if not ls.stdout.strip():
                    scope(sid, "release-tag", "not_found", "the tag is not in the remote"); continue
                fe = sh(["git", "fetch", "--depth", "1", "-q", "origin", "refs/tags/%s:refs/tags/%s" % (t, t)], cl)
                if fe.returncode != 0:
                    scope(sid, "release-tag", "fetch_error", "git fetch failed: %s" % fe.stderr.strip()[:120]); continue
                g = sh(["git", "grep", "-l", "cic_countersign", t, "--", "*.yaml", "*.yml"], cl)
                if g.returncode not in (0, 1):                                   # 0 a match, 1 no match, anything else git could not read the tag's content
                    scope(sid, "release-tag", "read_error", "git grep failed (exit %d): %s" % (g.returncode, g.stderr.strip()[:120])); continue
                files = [x.split(":", 1)[1] for x in g.stdout.split() if ":" in x]
                excluded = [f for f in files if "schema.yaml" in f or "/tests/" in f or ".mypy_cache" in f]
                files = [f for f in files if f not in excluded]
                found, perr, rerr = 0, [], []
                for f in files:
                    sw = sh(["git", "show", "%s:%s" % (t, f)], cl)
                    if sw.returncode != 0:
                        rerr.append(f); continue
                    try:
                        d = yaml.safe_load(sw.stdout)
                    except BaseException:
                        perr.append(f); continue
                    if not isinstance(d, dict) or not isinstance(d.get("cic_countersign"), dict):
                        continue
                    cs = d["cic_countersign"]; found += 1
                    own = bool(re.search(r"%s-v\d+\.\d+\.\d+\.yaml$" % ("cic-primitives" if repo == "cic-primitives" else "cic-yang"), f)) and (re.search(r"@(v\d+\.\d+\.\d+)$", t) or [0, ""])[1] in f
                    inv["tag_records"].append({"repo": repo, "tag": t, "file": f, "format": "yaml-record", "ts": cs.get("ts"), "own_release_record": own, "certs": [{"role": c["role"], "not_after": (c["info"] or {}).get("not_after"), "subject_cn": (c["info"] or {}).get("subject_cn")} for c in record_certs(d)]})
                    if own:
                        cls_items["primitives" if repo == "cic-primitives" else "yang"].append({"certs": record_certs(d), "declared_until": None})
                        if repo == "cic-yang":                                   # the expected set of the open records: the release record of each yang tag, at the tag's commit
                            inv["open_records"].append({"id": "%s:%s" % (repo, f), "repo": repo, "path": f, "ref": "tag:" + t, "commit": sh(["git", "rev-parse", "%s^{commit}" % t], cl).stdout.strip()})
                if rerr:
                    scope(sid, "release-tag", "read_error", "git show failed for: %s" % ", ".join(rerr)); continue
                if perr:
                    scope(sid, "release-tag", "parse_error", "unparsable: %s" % ", ".join(perr)); continue
                if found:
                    scope(sid, "release-tag", "ok", "%d signed record file(s); %d excluded (schema or test files)" % (found, len(excluded))); continue
                lt = sh(["git", "ls-tree", "--name-only", t, "--", "project.yaml"], cl)
                if lt.returncode != 0:
                    scope(sid, "release-tag", "read_error", "git ls-tree failed (exit %d): %s" % (lt.returncode, lt.stderr.strip()[:120])); continue
                if not lt.stdout.strip():
                    scope(sid, "release-tag", "absent", "no signed record file and no project.yaml at the tag"); continue      # looked for and explicitly not there
                pr = sh(["git", "show", "%s:project.yaml" % t], cl)
                if pr.returncode != 0:
                    scope(sid, "release-tag", "read_error", "git show project.yaml failed (exit %d): %s" % (pr.returncode, pr.stderr.strip()[:120])); continue
                try:
                    py = yaml.safe_load(pr.stdout) or {}
                except BaseException:
                    scope(sid, "release-tag", "parse_error", "project.yaml does not parse"); continue
                blk = next((py[k] for k in ("metadata", "release") if isinstance(py.get(k), dict) and any(x in py[k] for x in ("buildHash", "cicSign", "sign", "cert"))), None)
                if blk is None:
                    scope(sid, "release-tag", "absent", "project.yaml has no signature block"); continue
                certs = [{"role": p, "info": cert_info(txt)} for p, txt in walk_certs(blk)]
                until = (blk.get("validity") or {}).get("until") if isinstance(blk.get("validity"), dict) else None
                inv["tag_records"].append({"repo": repo, "tag": t, "file": "project.yaml", "format": "template-project-yaml", "ts": blk.get("build_timestamp") or blk.get("timestamp"), "declared_validity_until": until,
                                           "certs": [{"role": c["role"], "not_after": (c["info"] or {}).get("not_after"), "subject_cn": (c["info"] or {}).get("subject_cn")} for c in certs]})
                tpl.append((t, {"certs": certs, "declared_until": (re.match(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d", until).group(0) + "Z") if isinstance(until, str) and re.match(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d", until) else None}))
                scope(sid, "release-tag", "ok", "signature block under project.yaml; %d certificate(s), %d unreadable" % (len(certs), sum(1 for c in certs if not c["info"])))
        inv["classes"].append(class_summary("primitives", "cic-primitives release records (the tags' own records)", cls_items["primitives"], as_of))
        inv["classes"].append(class_summary("yang", "cic-yang release records (the tags' own records)", cls_items["yang"], as_of))
        for t, it in tpl:                                                         # a template release is its own class: the three that carry a block differ in their boundaries
            inv["classes"].append(class_summary("template:" + t, "template release " + t, [it], as_of))
        # ---- the verifier anchors
        for repo, path, label, rx in ANCHORS:
            p = os.path.join(clones, repo, path)
            if not os.path.isfile(p):
                scope("anchor:" + label, "verifier-anchor", "not_found", "%s/%s is not in the clone" % (repo, path)); continue
            lines = [i + 1 for i, l in enumerate(open(p, encoding="utf-8").read().splitlines()) if re.search(rx, l)]
            inv["anchors"].append({"repo": repo, "path": path, "label": label, "regex": rx, "lines": lines, "commit": inv["clones"][repo]["head"]})
            scope("anchor:" + label, "verifier-anchor", "ok", "%d line(s)" % len(lines))
        inv["open_records"].sort(key=lambda r: r["id"].encode("utf-8"))
        inv["complete"] = all(s["status"] in OK_STATUSES for s in inv["scope"])
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump(inv, open(out, "w", encoding="utf-8"), indent=1, sort_keys=True); open(out, "a").write("\n")
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); return 2
    errs = [s for s in inv["scope"] if s["status"] not in OK_STATUSES]
    print("scope elements %d (%s); registry records %d; tag records %d; complete: %s" % (len(inv["scope"]), ", ".join("%s %d" % kv for kv in sorted(collections.Counter(s["status"] for s in inv["scope"]).items())), inv["registry"]["records"], len(inv["tag_records"]), inv["complete"]))
    for s in errs:
        print("NOT COMPLETE: %s %s: %s" % (s["id"], s["status"], s["detail"]))
    return 0 if inv["complete"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
