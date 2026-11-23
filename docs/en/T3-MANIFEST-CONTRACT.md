# The canonical manifest of the open records (the contract, DRAFT for review)

**A contract and its tools: documentation and isolated tooling only.** Nothing here signs, time-stamps, uploads or publishes anything. The manifest below is the object whose digest is to be time-stamped if the owner confirms the T3 resolutions (`docs/en/T3-EXECUTION-PREREQUISITES.md`); the time-stamping itself is **on hold**. Data and tools: `docs/evidence/time-manifest/`.

## 1. Why a contract

A time stamp proves that **a digest** existed no later than a time. What the digest stands for must therefore be reproducible byte for byte years later, by someone who was not here, without agreeing on a serialisation library. So the manifest is **line-oriented and byte-exact**: there is nothing to canonicalise except the bytes themselves.

## 2. The form

```
CIC-T3-MANIFEST/1
scope: <one line of text, no tab>
count: <n>
---
<record_id> TAB <sha256 hex of the EXACT record bytes> TAB <size in bytes> TAB <repo> TAB <commit, 40 hex> TAB <ref> TAB <path>
...   (n lines, sorted bytewise by record_id)
```

UTF-8, **no byte order mark, LF only, exactly one final LF**, no other line. `record_id` is `<repo>:<path>`; `ref` is `tag:<name>` or `branch:<name>`. **The digest that is time-stamped is the SHA-256 of the whole manifest byte stream.** The verifier refuses everything else: a BOM, a carriage return, a missing or extra final newline, a count that is not the number of lines, lines not sorted bytewise, a duplicate id, a record id that is not `repo:path`, a malformed digest, commit or size.

## 3. What a line stands for

* **The exact record bytes**, not the `build_hash` field: the SHA-256 is of the bytes of the file as stored in the git **object** at the recorded commit (`git show <commit>:<path>`), never of a working tree. A later commit or an uncommitted change does not change what the line says (tested).
* **The records of the scope** (resolution Q1a): every YAML file under the record areas of the registry's `HEAD` that parses as a record with a `cic_countersign` block, and the release record of each named `cic-yang` tag. **Fail-closed:** a file that mentions the block and does not parse, a named tag that does not exist, or a tag without its record file is an error and no manifest is written; the builder never produces a smaller manifest silently.
* **Deterministic:** the same git objects give the same bytes (two builds are byte-identical, tested); the manifest holds no time and no host name.

## 4. The tools and the dry run

`build_manifest.py` builds the manifest from clones, `verify_manifest.py` checks one against git (the form, every record's bytes at its recorded commit, and the recorded digest of the manifest); both are read-only. An infrastructure failure (git cannot read an object) is exit 2 and is **never counted as a detection**. The self-test (22 checks) builds fixture repositories and plants the faults of section 2 and the failures of section 3, and **the mutations that read the working tree instead of the object, or skip an unparsable file, are measured to fail it**.

**Dry run (2026-11-23, not for time-stamping):** over the clones of the expiry inventory the builder produced a manifest of **exactly 92 records** (90 registry records at `cic-schema-registry` `3d493d591b86`, 2 yang release records), 28 347 bytes, SHA-256 `d7cb0f754f5c275837aaa252377d3e6da866560a68baa317eb1060bdc8dc4e38`, and the verifier confirmed every record against git (`results/DRYRUN-manifest.txt`). **This digest is a dry-run value.** The manifest that is time-stamped is built at **execution time** from the then-current commits, verified, and **its** digest recorded (condition C-Q1a-4); the registry moves, and a different `HEAD` gives a different manifest.

## 5. Not shown

* That the 92 are all the records that matter: the scope follows the expiry inventory (`docs/en/T3-EXPIRY-RISK-ASSESSMENT-AND-DECISION-PLAN.md`); records outside the cloned repositories are not in it.
* That a record is authentic or authorised: the manifest says which bytes existed, not who signed them or whether the release is genuine.
* The template releases and the three already stamped primitives releases are **not** in this manifest (they are outside resolution Q1a's 92).
* A manifest does not preserve anything: the preservation of the records, the manifest and the tokens is resolution Q6, and nothing is preserved yet.
