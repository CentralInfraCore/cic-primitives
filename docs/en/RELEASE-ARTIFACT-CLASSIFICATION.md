# Release artifact list: classification of the files of cic-primitives (proposal)

Status: **a review table, not a decision.** Nothing here is in `project.yaml`, and nothing here is merged as the list. The owner approves the content after this survey; until then the real release path of this repository stops with `declaration_missing`. This document is a separate piece of work from the compiler change (cic-primitives #26) and does not depend on it.

State surveyed: `devel` at `d2d8ec7` (131 tracked files). The list that is approved applies to the **release source commit**, which is a commit on a release branch and not necessarily `devel`'s head (see "Pin and devel").

## The rule

The producer's published surface has a meaning of its own. It is not the file set of any one consumer, and it is not "every YAML".

> A file is in the list when its content determines the **contract, the interpretation or the reproducibility** of the released primitive package.

So: the released primitives and what validates and interprets them (meta-schemas, the record schema), the grammar and access model they are checked with and their golden data, the normative text, the licence, the dependency lock. Not: tests, CI and repository configuration, internal notes and plans, working papers, examples that must fail, historical records, tooling of the release process. Where the rule does not decide, the file is `REVIEW` with the question, not guessed.

The twelve files that `cic-primitive-forms` pins are a **checked subset**: the table marks them, and a test of the real declaration (when one exists) can require that all twelve are in the list. They do not define the list; the producer's rule does. The result happens to contain all twelve, which is a consequence and not the criterion.

Counts: **INCLUDE 29**, **REVIEW 10**, **EXCLUDE 92**.

## The table

`Forms pin` marks the twelve files of the grammar pin `cic-primitives-73ae469-6a188078`.

| Path | Bytes | Role | Forms pin | Proposal | Technical reason |
|---|---|---|---|---|---|
| `.github/workflows/gate.yml` | 3226 | repository, CI or editor configuration |  | **EXCLUDE** | not part of the published surface |
| `.gitignore` | 476 | repository, CI or editor configuration |  | **EXCLUDE** | not part of the published surface |
| `.mcp.json` | 113 | repository, CI or editor configuration |  | **EXCLUDE** | not part of the published surface |
| `CLAUDE.md` | 6265 | repository, CI or editor configuration |  | **EXCLUDE** | not part of the published surface |
| `Dockerfile` | 749 | repository, CI or editor configuration |  | **EXCLUDE** | not part of the published surface |
| `LICENSE.md` | 1364 | licence text | yes | **INCLUDE** | the terms the release is published under; pinned by Forms |
| `LICENSE.meta.yaml` | 506 | licence metadata |  | **REVIEW** | same as LICENSE.yaml |
| `LICENSE.yaml` | 506 | licence metadata |  | **REVIEW** | machine-readable licence metadata (imported from base-repo); decide whether the published surface carries it beside LICENSE.md |
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
| `project.schema.yaml` | 3682 | schema of project.yaml |  | **REVIEW** | imported from base-repo; describes the build configuration, not the primitives |
| `project.yaml` | 747 | project metadata and release settings |  | **REVIEW** | holds the declaration itself (so a digest of it ties the list to the record) but also operational settings (Vault key name and certificate path, owner e-mail); decide whether those belong to the published surface |
| `proposals/atom-grammar/P0-4-ACCESS-GRAMMAR.md` | 14867 | access grammar specification | yes | **INCLUDE** | pinned by Forms. Its own header says `Status: proposed`: including it publishes a proposal text as part of the surface |
| `proposals/atom-grammar/P0-4-MIGRATION.md` | 3765 | access migration note | yes | **INCLUDE** | pinned by Forms. Devel has moved on in this file since the pin (see "Pin and devel") |
| `proposals/atom-grammar/README.md` | 34260 | grammar documentation | yes | **INCLUDE** | describes the grammar the release applies (status `implemented`); pinned by Forms |
| `proposals/atom-grammar/access-vectors/expansion.yaml` | 16519 | access golden vectors |  | **INCLUDE** | same class as `resolution.yaml` (pinned by Forms): the other suites of the vectors that give the access model its meaning |
| `proposals/atom-grammar/access-vectors/migration.yaml` | 7341 | access golden vectors |  | **INCLUDE** | same class as `resolution.yaml` (pinned by Forms): the other suites of the vectors that give the access model its meaning |
| `proposals/atom-grammar/access-vectors/reading.yaml` | 12453 | access golden vectors |  | **INCLUDE** | same class as `resolution.yaml` (pinned by Forms): the other suites of the vectors that give the access model its meaning |
| `proposals/atom-grammar/access-vectors/resolution.yaml` | 60711 | access golden vectors | yes | **INCLUDE** | conformance data of the access model; pinned by Forms |
| `proposals/atom-grammar/access_policy.py` | 17807 | access model (reference) | yes | **INCLUDE** | the reference model of Access/PolicySurface resolution; pinned by Forms |
| `proposals/atom-grammar/check_access_vectors.py` | 22295 | runner of the access vectors |  | **REVIEW** | a tool that runs the vectors against the model; reproducibility, not contract. Include if the published surface should let a consumer re-run the vectors |
| `proposals/atom-grammar/check_grammar.py` | 57874 | grammar implementation | yes | **INCLUDE** | the instance grammar the release gate applies; already digested in `provenance.grammar_sha256`; pinned by Forms |
| `proposals/atom-grammar/instance-grammar.schema.yaml` | 10095 | grammar schema | yes | **INCLUDE** | the schema the grammar checks against; already digested in `provenance.grammar_schema_sha256`; pinned by Forms |
| `proposals/atom-grammar/p0-4-contradiction-matrix.md` | 5718 | working paper |  | **EXCLUDE** | its own header: "munkaanyag, nem normatív" |
| `proposals/schema-registry/README.md` | 17568 | design proposal |  | **EXCLUDE** | a plan and status note of another repository's layout; not the contract of the released primitives |
| `release.schema.yaml` | 6158 | schema of the release record |  | **INCLUDE** | the shape of the record a consumer reads; part of how the record is interpreted |
| `release/cic-primitives-v0.1.5.yaml` | 55002 | a historical release record |  | **EXCLUDE** | records are outputs, never inputs; a record does not carry another record |
| `renovate.json` | 268 | repository, CI or editor configuration |  | **EXCLUDE** | not part of the published surface |
| `requirements.in` | 398 | tool dependencies |  | **REVIEW** | imported from base-repo; reproducibility of the compiler environment, not of the primitives |
| `requirements.txt` | 2085 | locked tool dependencies |  | **REVIEW** | same as requirements.in |
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
| `schemas/examples/kubernetes-pod.yaml` | 12332 | example composition |  | **REVIEW** | not a spec and not normative, but the release grammar gate checks the compositions under `schemas/examples` ("compositions this release would ship"); decide whether the gate input is part of the published surface |
| `schemas/index.yaml` | 3287 | meta-schema of the primitives |  | **INCLUDE** | defines how every primitive is validated (`run_primitive_validation`); not a spec itself, so it is not in `specs[]` and nothing else digests it |
| `setup.cfg` | 121 | repository, CI or editor configuration |  | **EXCLUDE** | not part of the published surface |
| `tools/check_provenance.py` | 10906 | provenance gate |  | **EXCLUDE** | a gate of this repository's CI |
| `tools/compiler.py` | 56937 | the compiler |  | **REVIEW** | it made the record; `source_commit` already identifies it. Include if a consumer should be able to take the exact compiler from the release |
| `tools/git_hook_commit-msg.sh` | 2166 | release or developer tooling |  | **EXCLUDE** | signing and git hooks of the process; not the published surface |
| `tools/init-hooks.sh` | 1474 | release or developer tooling |  | **EXCLUDE** | signing and git hooks of the process; not the published surface |
| `tools/release.sh` | 296 | release or developer tooling |  | **EXCLUDE** | signing and git hooks of the process; not the published surface |
| `tools/release_candidate_precheck.py` | 18636 | pre-check tool (Forms pin) |  | **EXCLUDE** | a tool for the release process, not for consumers of the primitives |
| `tools/release_record_conformance.py` | 22989 | reference verifier of the record contract |  | **REVIEW** | the independent yardstick; include if a consumer should be able to check a record against the contract from the release alone |
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

## Questions for the owner (the `REVIEW` rows)

- `LICENSE.meta.yaml`
- `LICENSE.yaml`
- `project.schema.yaml`
- `project.yaml`
- `proposals/atom-grammar/check_access_vectors.py`
- `requirements.in`
- `requirements.txt`
- `schemas/examples/kubernetes-pod.yaml`
- `tools/compiler.py`
- `tools/release_record_conformance.py`

Each is a yes/no on whether the file belongs to the published surface; the reason column says what the choice means. A `REVIEW` row is not in the proposed list below.

## The proposed `paths` (INCLUDE only, sorted by UTF-8 bytes)

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

This block is a proposal text. It is **not** applied to `project.yaml`.

## Pin and devel

All twelve Forms-pinned files are in the proposal. The pin commit `73ae469` is an ancestor of `devel`'s head, and eleven of the twelve are byte-identical there; `proposals/atom-grammar/P0-4-MIGRATION.md` differs (`devel` moved on, 12 lines), and the working paper `p0-4-contradiction-matrix.md` also changed (not in the list). Including a file in the list does not make a release contain the pinned bytes: a release that meets the Forms pin has to be cut from a source commit that holds those exact blobs (the owner's decision of 2026-11-01: a new release from the pin). The pre-check (`tools/release_candidate_precheck.py`) is the tool that compares the two; it is not changed here.

## What the list does not do

* It does not make a consumer's requirement part of the producer: nothing here reads a consumer's pins.
* It is explicit: a new file is not in the release until it is added. A producer-side consistency check (every `specs[].source_path` is also in `artifacts.files`) would catch a forgotten schema file; it is not part of the contract and is not implemented. Offered as a follow-up, not decided.
* It is a list of paths in a commit; the approval of a list is not the authorization of a release. Signing and publication stay on hold.
