"""Build the canonical manifest of the open records (docs/en/T3-MANIFEST-CONTRACT.md) from clones. READ-ONLY: it reads git OBJECTS, it signs, stamps and uploads nothing. A DRY RUN until the owner decides otherwise:
the manifest that is actually time-stamped is built at execution time from the then-current commits, and its digest is recorded then.
Records: every YAML file under the record areas of the registry clone's HEAD that parses as a record with a `cic_countersign` block (the same criterion as the expiry inventory), and the release record of each
named cic-yang tag. FAIL-CLOSED: a file that mentions the block and does not parse, a missing tag or a missing record file is an error, never a skipped record.
Usage: build_manifest.py --clones DIR --out MANIFEST [--scope-json PATH]   (scope-json: {"yang_tags": [...], "registry_dirs": [...]})
Writes MANIFEST and MANIFEST.sha256. Exit: 0 built, 1 the build is incomplete (an error line says which), 2 an input cannot be read (never a result)."""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import manifestlib as M

SCOPE = "the open records without external time evidence: the countersigned records of the cic-schema-registry and the cic-yang release records (docs/en/T3-EXPIRY-RISK-ASSESSMENT-AND-DECISION-PLAN.md)"
DEFAULT = {"yang_tags": ["yang/@v0.1.2", "yang/@v0.1.3"], "registry_dirs": ["standards", "general", "providers"]}


def main(argv):
    import yaml
    arg = lambda n, d: argv[argv.index(n) + 1] if n in argv and argv.index(n) + 1 < len(argv) else d
    clones, out = arg("--clones", None), arg("--out", None)
    try:
        assert clones and out and os.path.isdir(clones)
        cfg = dict(DEFAULT)
        if "--scope-json" in argv:
            cfg.update(json.load(open(arg("--scope-json", None), encoding="utf-8")))
        entries, errors = [], []
        reg = os.path.join(clones, "cic-schema-registry")
        head = M.git_bytes(reg, "rev-parse", "HEAD").decode().strip()
        branch = M.git_bytes(reg, "symbolic-ref", "--short", "HEAD").decode().strip()
        names = [n for n in M.git_bytes(reg, "ls-tree", "-r", "--name-only", "HEAD").decode("utf-8").split("\n") if n and n.split("/")[0] in cfg["registry_dirs"] and n.endswith((".yaml", ".yml"))]
        for path in names:
            data = M.git_bytes(reg, "show", "HEAD:%s" % path)
            if b"cic_countersign" not in data:
                continue
            try:
                d = yaml.safe_load(data.decode("utf-8"))
            except BaseException:
                errors.append("a file that mentions the block does not parse: cic-schema-registry:%s" % path); continue
            if isinstance(d, dict) and isinstance(d.get("cic_countersign"), dict):
                entries.append(M.record_line("cic-schema-registry", path, head, "branch:%s" % branch, data))
        yang = os.path.join(clones, "cic-yang")
        for tag in cfg["yang_tags"]:
            ver = (re.search(r"@(v\d+\.\d+\.\d+)$", tag) or [0, None])[1]
            commit = M.git_bytes(yang, "rev-parse", "%s^{commit}" % tag).decode().strip()
            path = "release/cic-yang-%s.yaml" % ver
            if path not in M.git_bytes(yang, "ls-tree", "-r", "--name-only", tag).decode("utf-8").split("\n"):
                errors.append("the tag %s has no %s" % (tag, path)); continue
            entries.append(M.record_line("cic-yang", path, commit, "tag:%s" % tag, M.git_bytes(yang, "show", "%s:%s" % (tag, path))))
        if errors:
            for e in errors:
                print("NOT COMPLETE: %s" % e)
            return 1
        raw = M.render(SCOPE, entries)
        open(out, "wb").write(raw); open(out + ".sha256", "w").write("%s  %s\n" % (M.digest(raw), os.path.basename(out)))
    except M.ManifestError as e:
        print("INCOMPLETE: %s" % e); return 2
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); return 2
    print("manifest: %d records, %d bytes, SHA-256 %s" % (len(entries), len(raw), M.digest(raw)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
