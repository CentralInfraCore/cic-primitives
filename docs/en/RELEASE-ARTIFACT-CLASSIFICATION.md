# Release artifact list: classification of the files of cic-primitives

Status: **the content decision of the owner is applied; this is still not the list.** The owner approved the 30-file set below as the *content* of the published surface (review of 2026-11-01). That is not a release authorization, and it is not applied to `project.yaml`: the declaration goes into `project.yaml` in a separate, targeted change, together with the compiler's check that every published schema is listed (cic-primitives #26). Until then the real release path of this repository stops with `declaration_missing`.

State surveyed: `devel` at `d2d8ec7` (131 tracked files). The list applies to the **release source commit**, which is a commit on a release branch and not necessarily `devel`'s head (see "Pin and devel").

## The rule

The producer's published surface has a meaning of its own. It is not the file set of any one consumer, it is not "every YAML", and it is not the whole toolchain that makes a release.

> A file is in the list when its content determines the **contract, the interpretation or the reproducibility** of the released primitive package.

So: the released primitives and what validates and interprets them (meta-schemas, the record schema), the grammar and access model they are checked with and their golden data, the normative text, the licence, the dependency lock. Not: tests, CI and repository configuration, internal notes and plans, working papers, examples, historical records, and the tooling that produces or checks a release.

The twelve files that `cic-primitive-forms` pins are a **checked subset**, marked in the table. They do not define the list; the producer's rule does. The result happens to contain all twelve, which is a consequence and not the criterion.

Counts: **INCLUDE 30**, **EXCLUDE 101**, REVIEW 0.

## The table

`Forms pin` marks the twelve files of the grammar pin `cic-primitives-73ae469-6a188078`. Rows whose reason begins "Owner decision" were `REVIEW` in the first survey and are decided.

| Path | Bytes | Role | Forms pin | Decision | Technical reason |
|---|---|---|---|---|---|
| `.github/workflows/gate.yml` | 3226 | repository, CI or editor configuration |  | **EXCLUDE** | not part of the published surface |
| `.gitignore` | 476 | repository, CI or editor configuration |  | **EXCLUDE** | not part of the published surface |
| `.mcp.json` | 113 | repository, CI or editor configuration |  | **EXCLUDE** | not part of the published surface |
| `CLAUDE.md` | 6265 | repository, CI or editor configuration |  | **EXCLUDE** | not part of the published surface |
| `Dockerfile` | 749 | repository, CI or editor configuration |  | **EXCLUDE** | not part of the published surface |
| `LICENSE.md` | 1364 | licence text | yes | **INCLUDE** | the terms the release is published under; pinned by Forms |
| `LICENSE.meta.yaml` | 506 | licence metadata |  | **EXCLUDE** | Owner decision (review of 2026-11-01): the licence text is the primary contract |
| `LICENSE.yaml` | 506 | licence metadata |  | **EXCLUDE** | Owner decision (review of 2026-11-01): no demonstrated consumer dependency |
| `Makefile` | 10247 | repository, CI or editor configuration |  | **EXCLUDE** | not part of the published surface |
| `README.hu.md` | 7636 | repository readme (hu) |  | **EXCLUDE** | same as README.md |
| `README.md` | 7829 | repository readme |  | **EXCLUDE** | describes the repository, not the released primitives (the grammar has its own README in the list) |
| `commitment.yaml` | 1224 | developer pledge |  | **EXCLUDE** | its content (validity, createdBy) is already inside the record; it changes with every pledge and says nothing about the primitives |
| `dependencies/.gitkeep` | 0 | placeholder |  | **EXCLUDE** | empty file |
| `dependencies/template-schema-v0.9.5_2025.yaml` | 9837 | vendored template |  | **EXCLUDE** | a template of base-repo; read by no tool of this repository |
| `dependency.yaml` | 610 | dependency lock |  | **INCLUDE** | what was imported from where; its digest is already in `provenance.dependency_lock_sha256` |
| `docker-compose.yml` | 1284 | repository, CI or editor configuration |  | **EXCLUDE** | not part of the published surface |
| `feature-list.md` | 965 | internal planning |  | **EXCLUDE** | not normative |
| `md.meta.schema.yaml` | 3907 | meta-schema of the schema metadata |  | **INCLUDE** | defines the metadata every spec must carry (`run_validation`); imported from base-repo (`dependency.yaml`), still part of how the release is interpreted |
| `project.schema.yaml` | 3682 | schema of project.yaml |  | **EXCLUDE** | Owner decision (review of 2026-11-01): it validates build configuration |
| `project.yaml` | 747 | project metadata and release settings |  | **EXCLUDE** | Owner decision (review of 2026-11-01): it also carries operational configuration (Vault key name and certificate path, owner e-mail); the declared set appears in the signed record itself |
| `proposals/atom-grammar/P0-4-ACCESS-GRAMMAR.md` | 14867 | access grammar specification | yes | **INCLUDE** | pinned by Forms. Its own header says `Status: proposed`: including it publishes a proposal text as part of the surface |
| `proposals/atom-grammar/P0-4-MIGRATION.md` | 3765 | access migration note | yes | **INCLUDE** | pinned by Forms. Devel has moved on in this file since the pin (see "Pin and devel") |
| `proposals/atom-grammar/README.md` | 34260 | grammar documentation | yes | **INCLUDE** | describes the grammar the release applies (status `implemented`); pinned by Forms |
| `proposals/atom-grammar/access-vectors/expansion.yaml` | 16519 | access golden vectors |  | **INCLUDE** | same class as `resolution.yaml` (pinned by Forms): the other suites of the vectors that give the access model its meaning |
| `proposals/atom-grammar/access-vectors/migration.yaml` | 7341 | access golden vectors |  | **INCLUDE** | same class as `resolution.yaml` (pinned by Forms): the other suites of the vectors that give the access model its meaning |
| `proposals/atom-grammar/access-vectors/reading.yaml` | 12453 | access golden vectors |  | **INCLUDE** | same class as `resolution.yaml` (pinned by Forms): the other suites of the vectors that give the access model its meaning |
| `proposals/atom-grammar/access-vectors/resolution.yaml` | 60711 | access golden vectors | yes | **INCLUDE** | conformance data of the access model; pinned by Forms |
| `proposals/atom-grammar/access_policy.py` | 17807 | access model (reference) | yes | **INCLUDE** | the reference model of Access/PolicySurface resolution; pinned by Forms |
| `proposals/atom-grammar/check_access_vectors.py` | 22295 | runner of the access vectors |  | **INCLUDE** | Owner decision (review of 2026-11-01): needed to run the reference behaviour of Access reproducibly; it runs, with its self-test, in a tree of only the listed files (see "Self-containment") |
| `proposals/atom-grammar/check_grammar.py` | 57874 | grammar implementation | yes | **INCLUDE** | the instance grammar the release gate applies; already digested in `provenance.grammar_sha256`; pinned by Forms |
| `proposals/atom-grammar/instance-grammar.schema.yaml` | 10095 | grammar schema | yes | **INCLUDE** | the schema the grammar checks against; already digested in `provenance.grammar_schema_sha256`; pinned by Forms |
| `proposals/atom-grammar/p0-4-contradiction-matrix.md` | 5718 | working paper |  | **EXCLUDE** | its own header: "munkaanyag, nem normatív" |
| `proposals/schema-registry/README.md` | 17568 | design proposal |  | **EXCLUDE** | a plan and status note of another repository's layout; not the contract of the released primitives |
| `release.schema.yaml` | 6158 | schema of the release record |  | **INCLUDE** | the shape of the record a consumer reads; part of how the record is interpreted |
| `release/cic-primitives-v0.1.5.yaml` | 55002 | a historical release record |  | **EXCLUDE** | records are outputs, never inputs; a record does not carry another record |
| `renovate.json` | 268 | repository, CI or editor configuration |  | **EXCLUDE** | not part of the published surface |
| `requirements.in` | 398 | tool dependencies |  | **EXCLUDE** | Owner decision (review of 2026-11-01): developer dependency description |
| `requirements.txt` | 2085 | locked tool dependencies |  | **EXCLUDE** | Owner decision (review of 2026-11-01): toolchain lock, not the contract of the primitives |
| `schemas/aggregate/.gitkeep` | 0 | placeholder |  | **EXCLUDE** | empty file |
| `schemas/aggregate/config-surface.yaml` | 2262 | released primitive (aggregate) |  | **INCLUDE** | a spec of the release: its content is in `specs[]` already; the artifact digest gives it the same sha256 form as every other released file |
| `schemas/aggregate/managed-entity.yaml` | 7209 | released primitive (aggregate) |  | **INCLUDE** | a spec of the release: its content is in `specs[]` already; the artifact digest gives it the same sha256 form as every other released file |
| `schemas/aggregate/operation-surface.yaml` | 2023 | released primitive (aggregate) |  | **INCLUDE** | a spec of the release: its content is in `specs[]` already; the artifact digest gives it the same sha256 form as every other released file |
| `schemas/aggregate/policy-surface.yaml` | 4978 | released primitive (aggregate) | yes | **INCLUDE** | a spec of the release: its content is in `specs[]` already; the artifact digest gives it the same sha256 form as every other released file |
| `schemas/aggregate/state-surface.yaml` | 2396 | released primitive (aggregate) |  | **INCLUDE** | a spec of the release: its content is in `specs[]` already; the artifact digest gives it the same sha256 form as every other released file |
| `schemas/atomic/.gitkeep` | 0 | placeholder |  | **EXCLUDE** | empty file |
| `schemas/atomic/access.yaml` | 9098 | released primitive (atomic) | yes | **INCLUDE** | a spec of the release: its content is in `specs[]` already; the artifact digest gives it the same sha256 form as every other released file |
| `schemas/atomic/address.yaml` | 5463 | released primitive (atomic) |  | **INCLUDE** | a spec of the release: its content is in `specs[]` already; the artifact digest gives it the same sha256 form as every other released file |
| `schemas/atomic/behavior.yaml` | 3295 | released primitive (atomic) |  | **INCLUDE** | a spec of the release: its content is in `specs[]` already; the artifact digest gives it the same sha256 form as every other released file |
| `schemas/atomic/contract.yaml` | 3329 | released primitive (atomic) |  | **INCLUDE** | a spec of the release: its content is in `specs[]` already; the artifact digest gives it the same sha256 form as every other released file |
| `schemas/atomic/event.yaml` | 3503 | released primitive (atomic) |  | **INCLUDE** | a spec of the release: its content is in `specs[]` already; the artifact digest gives it the same sha256 form as every other released file |
| `schemas/atomic/identity.yaml` | 3740 | released primitive (atomic) |  | **INCLUDE** | a spec of the release: its content is in `specs[]` already; the artifact digest gives it the same sha256 form as every other released file |
| `schemas/atomic/role.yaml` | 6179 | released primitive (atomic) | yes | **INCLUDE** | a spec of the release: its content is in `specs[]` already; the artifact digest gives it the same sha256 form as every other released file |
| `schemas/atomic/shape.yaml` | 7275 | released primitive (atomic) | yes | **INCLUDE** | a spec of the release: its content is in `specs[]` already; the artifact digest gives it the same sha256 form as every other released file |
| `schemas/examples/invalid/aggregate-invalid-slot-mode.yaml` | 785 | negative test fixture |  | **EXCLUDE** | must fail validation by design; used by the tests, read by no consumer |
| `schemas/examples/invalid/domain-sealed-override.yaml` | 1540 | negative test fixture |  | **EXCLUDE** | must fail validation by design; used by the tests, read by no consumer |
| `schemas/examples/invalid/missing-required-metadata.yaml` | 593 | negative test fixture |  | **EXCLUDE** | must fail validation by design; used by the tests, read by no consumer |
| `schemas/examples/kubernetes-pod.yaml` | 12332 | example composition |  | **EXCLUDE** | Owner decision (review of 2026-11-01): an example, not a normative primitive specification |
| `schemas/index.yaml` | 3287 | meta-schema of the primitives |  | **INCLUDE** | defines how every primitive is validated (`run_primitive_validation`); not a spec itself, so it is not in `specs[]` and nothing else digests it |
| `setup.cfg` | 121 | repository, CI or editor configuration |  | **EXCLUDE** | not part of the published surface |
| `tools/check_provenance.py` | 10906 | provenance gate |  | **EXCLUDE** | a gate of this repository's CI |
| `tools/compiler.py` | 56937 | the compiler |  | **EXCLUDE** | Owner decision (review of 2026-11-01): a release-producing tool, not the published surface |
| `tools/git_hook_commit-msg.sh` | 2166 | release or developer tooling |  | **EXCLUDE** | signing and git hooks of the process; not the published surface |
| `tools/init-hooks.sh` | 1474 | release or developer tooling |  | **EXCLUDE** | signing and git hooks of the process; not the published surface |
| `tools/release.sh` | 296 | release or developer tooling |  | **EXCLUDE** | signing and git hooks of the process; not the published surface |
| `tools/release_candidate_precheck.py` | 18636 | pre-check tool (Forms pin) |  | **EXCLUDE** | a tool for the release process, not for consumers of the primitives |
| `tools/release_record_conformance.py` | 22989 | reference verifier of the record contract |  | **EXCLUDE** | Owner decision (review of 2026-11-01): the tool that checks a release, not its content |
| `tools/vault-rootCA-sign-agent.sh` | 7681 | release or developer tooling |  | **EXCLUDE** | signing and git hooks of the process; not the published surface |
| `tools/vault-sign-agent.md` | 3606 | release or developer tooling |  | **EXCLUDE** | signing and git hooks of the process; not the published surface |
| `tools/vault-sign-agent.sh` | 4763 | release or developer tooling |  | **EXCLUDE** | signing and git hooks of the process; not the published surface |
| `ai/**` (7 files) | 122741 | internal working notes and decision log | | **EXCLUDE** | not normative for the released primitives; the decisions that matter are in the specs and the contract |
| `features/**` (2 files) | 4940 | feature specifications (internal) | | **EXCLUDE** | planning documents |
| `tests/**` (15 files) | 202174 | tests, fixtures, vectors of the conformance | | **EXCLUDE** | verification of this repository; the yardstick is represented by `tools/release_record_conformance.py` (REVIEW) and need not be duplicated here |
| `docs/en/concept/**` (16 files) | 28895 | concept documents | | **EXCLUDE** | explanatory, not normative |
| `docs/hu/concept/**` (16 files) | 29550 | concept documents (hu) | | **EXCLUDE** | explanatory, not normative |
| `docs/en/RELEASE-RECORD-CONTRACT.md` | 20350 | the record contract | | **INCLUDE** | the contract that gives the record its meaning; a consumer reading the record needs it |
| `docs/hu/RELEASE-RECORD-CONTRACT.md` | 6746 | record contract summary (hu) | | **EXCLUDE** | the English text is the normative one |
| `docs/**` (4 files) | 24211 | process documentation | | **EXCLUDE** | pre-check, conformance and compiler notes of the release process |

## The approved content: 30 paths (sorted by UTF-8 bytes)

```yaml
compiler_settings:
  release_artifacts:
    paths:
      - LICENSE.md
      - dependency.yaml
      - docs/en/RELEASE-RECORD-CONTRACT.md
      - md.meta.schema.yaml
      - proposals/atom-grammar/P0-4-ACCESS-GRAMMAR.md
      - proposals/atom-grammar/P0-4-MIGRATION.md
      - proposals/atom-grammar/README.md
      - proposals/atom-grammar/access-vectors/expansion.yaml
      - proposals/atom-grammar/access-vectors/migration.yaml
      - proposals/atom-grammar/access-vectors/reading.yaml
      - proposals/atom-grammar/access-vectors/resolution.yaml
      - proposals/atom-grammar/access_policy.py
      - proposals/atom-grammar/check_access_vectors.py
      - proposals/atom-grammar/check_grammar.py
      - proposals/atom-grammar/instance-grammar.schema.yaml
      - release.schema.yaml
      - schemas/aggregate/config-surface.yaml
      - schemas/aggregate/managed-entity.yaml
      - schemas/aggregate/operation-surface.yaml
      - schemas/aggregate/policy-surface.yaml
      - schemas/aggregate/state-surface.yaml
      - schemas/atomic/access.yaml
      - schemas/atomic/address.yaml
      - schemas/atomic/behavior.yaml
      - schemas/atomic/contract.yaml
      - schemas/atomic/event.yaml
      - schemas/atomic/identity.yaml
      - schemas/atomic/role.yaml
      - schemas/atomic/shape.yaml
      - schemas/index.yaml
```

This block is **text in this document**. It is not applied to `project.yaml` by this change.

## Self-containment of the access tools

Asked before the publication decision: do `access_policy.py` and `check_access_vectors.py` need anything outside the declared surface? Measured, not read: a directory with **only** the 30 listed files (nothing else from the repository), Python in isolated mode (`-I`):

| Command in that directory | Result |
|---|---|
| `python proposals/atom-grammar/check_access_vectors.py` | `187 cases, 0 failure(s)` |
| `python proposals/atom-grammar/check_access_vectors.py --self-test` | `50/50 seeded faults detected` |
| `python proposals/atom-grammar/check_grammar.py --self-test` | `53/53` |

The files they read are all in the list: the four vector suites, `access_policy.py`, `schemas/atomic/access.yaml`, `schemas/aggregate/policy-surface.yaml` (the access tools) and `instance-grammar.schema.yaml` (the grammar). What they need from outside the repository are Python packages, not files of it: `PyYAML` and `jsonschema` (the standard library otherwise). Those are not part of the published surface; a consumer that runs the tools installs them (the toolchain lock `requirements.txt` is excluded by decision). Running the grammar over compositions needs those compositions as input (the examples are excluded); its self-test does not.

## Pin and devel

All twelve Forms-pinned files are in the approved set. The pin commit `73ae469` is an ancestor of `devel`'s head, and eleven of the twelve are byte-identical there; `proposals/atom-grammar/P0-4-MIGRATION.md` differs (`devel` moved on, 12 lines). Listing a file does not make a release contain the pinned bytes.

**The approved list is not enough for a release from the historical pin.** The compiler reads the declaration from the `project.yaml` of the *source commit*. A release that starts from the state of `73ae469` therefore needs a new commit on a release branch that already contains the approved declaration and keeps the exact bytes of all twelve pinned files. That commit is not literally `73ae469`; the pre-check (`tools/release_candidate_precheck.py`), which compares the twelve digests, has to be run against it and not against `73ae469`. The pre-check is not changed here, and that release procedure stays on hold.

## What the list does not do

* It does not make a consumer's requirement part of the producer: nothing here reads a consumer's pins.
* It is explicit: a new file is not in the release until it is added. The compiler change (#26) refuses a release whose published schemas are not all listed (`spec_not_in_artifacts`), so a forgotten schema cannot be left out of the manifest; the other 17 files of the list have no such cross-check.
* It is a list of paths in a commit. The approval of its content is not the authorization of a release; signing and publication stay on hold.
