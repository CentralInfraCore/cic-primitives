# Evidence: the D1 gate of the release schema set is met (2026-11-21)

Scope: **grammar conformance only.** This directory shows that the composed release schemas
have no node-name finding under the node-name grammar V2 (decision D1, merged in #41). It does **not**
show semantic completeness and it does **not** finalize the schemas: they stay DRAFT (see
`docs/en/RELEASE-SCHEMA-OPEN-POINTS.md`).

Base: `devel` at `4ae1b08` (after #42). The schema parts, `composition.yaml` and the declaration are byte-identical
to the ones of #38 (`git diff` of `docs/design/release-schemas/` is empty), so the digests of the probe evidence stay valid.

| File | What it shows |
|---|---|
| `composed-PrimitiveRelease.yaml`, `composed-ModuleRelease.yaml` | `compose.py . <kind>` output (the composed schemas that were checked) |
| `v2-PrimitiveRelease.txt`, `v2-ModuleRelease.txt` | `check_grammar.py --node-name-grammar 2`: both accepted, 0 findings (43 and 36 nodes) |
| `name-vector-gate.txt` | `check_name_vectors.py` with Go and Rust runners built and run, `CIC_REQUIRE_NAME_RUNNERS=1`, `CIC_REQUIRE_RELEASE_HISTORY=1`: 8/8; C5 = V1 regression from pinned git objects; C6 = the release schema set: 0 findings under V2 and exactly the 3 `createdBy` findings under pinned V1 |
| `declaration-check.txt`, `selftest-declaration.txt` | `check_declaration.py` CONSISTENT; `selftest_declaration.py` 43 of 43 |
| `p1-pattern-trailing-lf.txt`, `p1.py` | measurement for open point P1: the 7 distinct `pattern` expressions of the composed schemas under Python `re.search` (the jsonschema flavor) |

Also run: the whole test suite, 943 passed (full run, `-x`).

## What the P1 measurement says (and does not)

All 7 distinct `pattern` expressions end in `$`. Under Python `re.search` each accepts its valid sample **plus one trailing
line feed**; under a full match none does. It is the same defect class as the documented V1 `abc\n` case, now measured
on the release patterns. Go RE2 and Rust `regex` treat `$` as end of text (measured for the node-name rule in
`docs/evidence/grammar-node-name-measurement/`; **not re-measured here for these 7 expressions**). No reader evaluates these
patterns in production today; the measurement is input to decision P1, not a change.

## Not shown

* That the `pattern`, `must`, `range` or `enum` expressions mean what the owner intends (P1, P2, P4).
* Anything about the Forms' evaluation of the surface-level `validation` entries (#167).
* Behavior under any Forms commit other than the one of the probe (`2f02a75`).
