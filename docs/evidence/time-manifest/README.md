# Evidence: the canonical manifest of the open records (T3), 2026-11-23

For `docs/en/T3-MANIFEST-CONTRACT.md`. **Tools for a manifest whose digest is to be time-stamped, if the owner so decides: read-only, nothing is signed, time-stamped, uploaded or published.**

| File | What it does |
|---|---|
| `manifestlib.py` | the canonical form: render (sorted bytewise, exact bytes), parse (refuses a BOM, a CR, a wrong final newline, a wrong count, unsorted or duplicate lines, a malformed field), the digest of the whole byte stream |
| `build_manifest.py` | builds the manifest from clones, reading git OBJECTS (never a working tree); FAIL-CLOSED (an unparsable file that mentions the block, a missing tag or a tag without its record file is an error and no manifest is written); exit 0, 1 incomplete, 2 an unreadable input |
| `verify_manifest.py` | the form, every record's bytes at its recorded commit (SHA-256 and size), and the recorded digest of the manifest; an infrastructure failure (git cannot read) is exit 2 and never a detection |
| `selftest_manifest.py`, `results/selftest-manifest-output.txt` | fixture repositories: a complete build, determinism, the object-not-working-tree rule, 11 planted faults in the manifest (altered digest and size, swapped lines, count, duplicate, CRLF, BOM, final newline, extra blank line, record id, recorded digest), two infrastructure failures (exit 2), three fail-closed builds, an unreadable input: 22 checks; the mutations that read the working tree or skip an unparsable file are measured to fail it |
| `results/DRYRUN-manifest.txt`, `results/DRYRUN-manifest.txt.sha256` | a DRY RUN over the expiry inventory's clones: exactly 92 records, 28 347 bytes, SHA-256 `d7cb0f754f5c275837aaa252377d3e6da866560a68baa317eb1060bdc8dc4e38`. NOT the manifest to be time-stamped: that one is built at execution time from the then-current commits |
| `SHA256SUMS` | the hashes of these files and the document |

Run (from this directory): `python3 build_manifest.py --clones <dir> --out results/DRYRUN-manifest.txt`, `python3 verify_manifest.py --manifest results/DRYRUN-manifest.txt --clones <dir> --sha256-file results/DRYRUN-manifest.txt.sha256`, `python3 selftest_manifest.py > results/selftest-manifest-output.txt`. Python 3 with PyYAML, and git.

## Not shown

That the 92 records are all that matter; that a record is authentic or authorised; any preservation of the manifest or the tokens (nothing is preserved).
