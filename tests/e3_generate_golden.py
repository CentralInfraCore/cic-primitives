"""Writes the committed golden fixtures of the envelope 3 conformance vectors. Not a test and not run in CI: the output is committed and reviewed, and the tests
read it. Certificates and ECDSA signatures are not reproducible byte for byte (the signatures carry a random nonce), which is why the result is committed
instead of regenerated; everything that is deterministic is checked against it by tests/test_release_record_conformance.py.

    python tests/e3_generate_golden.py
"""
import json
import pathlib
import sys
import tempfile

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import e3_fixtures as fx  # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as tmp:
        commit = fx.build_repo(pathlib.Path(tmp) / "golden", fx.GOLDEN_FILES)
    bundle = fx.assemble_golden(commit)
    canonical = fx.independent_canonical_bytes(bundle)
    files = bundle["artifacts"]["files"]
    expected = {
        "source_commit": commit,
        "files": files,
        "manifest_text": "".join("%s  %s\n" % (f["digest"][len("sha256:"):], f["path"]) for f in files),
        "manifest_digest": bundle["artifacts"]["manifest_digest"],
        "canonical_sha256_hex": fx.sha256_hex(canonical),
        "build_hash": bundle["release"]["build_hash"],
    }
    out = fx.FIXTURES
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "golden-record.yaml", "w", encoding="utf-8") as fh:
        yaml.dump(bundle, fh, sort_keys=False, indent=2, allow_unicode=True)
    (out / "golden.canonical.json").write_bytes(canonical)
    (out / "golden.expected.json").write_text(json.dumps(expected, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    print("source_commit", commit)
    print("manifest_digest", expected["manifest_digest"])
    print("build_hash", expected["build_hash"])


if __name__ == "__main__":
    main()
