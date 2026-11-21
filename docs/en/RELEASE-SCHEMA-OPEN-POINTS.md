# Release schema set: status after D1 and the open decision points

Status date: 2026-11-21. Status of the schemas: **DRAFT**.

Grammatical conformance is not semantic completeness. This document records the first and lists what is missing for the second.

## 1. Status

| Item | Status | Basis |
|---|---|---|
| D1 (node-name grammar) | **CLOSED** | #41, #42; the composed schemas have 0 findings under V2, the 3 `createdBy` findings under V1 (`docs/evidence/release-schema-d1-gate-closed/`) |
| P1 regular-expression flavor of `pattern` | **OPEN** | design doc section 7 |
| P2 expression dialect of `must` | **OPEN** | design doc section 7 |
| P4 `timestamp` pattern against `format: date-time` | **OPEN** | design doc section 7 |
| P7 reason for an integer beyond 2^53-1 | **OPEN** | design doc section 7, declaration G02 |
| Forms #167 surface-level `validation` is neither evaluated nor listed | **OPEN** | the four `must` entries are declared `not_reported` |
| The schemas (`common`, `primitive-release`, `module-release`, `composition`, declaration) | **DRAFT** | unchanged byte for byte; `final` is not given while P1, P2, P4, P7 and #167 are open |

The sentence "D1 blocks finalization" in the header of `common.yaml` and in section 6 of the design doc is **stale**: D1 no longer blocks, but D1 was never the only blocker (section 7 of the design doc says so for P1, P2, P4). The header is not edited here: the probe evidence digests bind the file bytes, and a status-only comment change is not worth invalidating them. The next change of the part files (the finalization pull request) fixes the header.

## 2. Decision list

For each point: what is undecided, what depends on it, what it blocks, and what I recommend. A recommendation is not a decision.

### #167 (Forms): responsibility and visibility of surface-level `validation`

* **Undecided:** who evaluates the four surface-level `must` entries (1 in `PrimitiveRelease`, 3 in `ModuleRelease`), and whether the Form must at least list them as unevaluated, as it does for node-level contracts today. Now it drops them silently (same class as FG1, #166).
* **Depends on:** nothing in this repository. The principle "the consumer's capability must not rewrite the contract" is already decided, so the schema text does not change with the answer.
* **Blocks:** the declaration's Form status for those entries (`not_reported` today); V09 and the kind checks have the verifier as named owner regardless.
* **Recommendation:** decide visibility first (list as unevaluated, like node-level entries; cheap, no dialect needed), evaluation later with P2.

### P7: reason for an out-of-range integer

* **Undecided:** the plan names no reason for an integer with absolute value above 2^53-1; `value_type_unsupported` is used.
* **Depends on:** the reason inventory of the generalization plan and of the Relay module release plan (37 identifiers are accounted for by `check_declaration.py`).
* **Blocks:** G02 text; a new identifier would add one to the inventory and to the Relay plan.
* **Recommendation:** an owner decision only, no tooling; either keep `value_type_unsupported` explicitly or name a new reason in the plan first.

### P1: regular-expression flavor of `pattern`

* **Undecided:** which flavor and which anchoring the `pattern` contract means. Measured (`p1-pattern-trailing-lf.txt`): all 7 distinct patterns of the composed schemas accept a trailing line feed under Python `re.search`.
* **Depends on:** nothing decided; the machinery exists (the versioned profile, the binding, the Rust-Go-Python vectors and the C8 build-and-run gate of #41).
* **Blocks:** the pattern contracts of all release fields (version, timestamps, digests, `vault:v1:` signatures); P4 (a timestamp is a pattern); every second reader of the contract (Go, Rust verifier).
* **Recommendation:** follow the precedent of D1/O1: full-match semantics, a versioned and pinned profile, vectors for the 7 expressions in the four-verdict form. Whether this is one more profile of the grammar or a new grammar field is the question of that issue.

### P4: `timestamp` pattern against `format: date-time`

* **Undecided:** the draft pattern (C02) is stricter than `date-time` in one direction (no lower-case `t`, no space) and looser in the other: it checks the shape only, so a calendar-invalid value such as month `13` matches. Which one is the contract is an A-profile decision.
* **Depends on:** P1 (the pattern semantic) and the record contract's own wording of the timestamp.
* **Blocks:** C02 and the two `release.*` date fields; any verifier check of time order (the expiry time-evidence decision is separate).
* **Recommendation:** after P1; decide the A-profile timestamp as a contract sentence with golden and negative vectors, not by tightening the pattern silently.

### P2: expression dialect of `must`

* **Undecided:** the `must` expressions (`kind = '...'`, `count(artifacts/files[path = '...']) = 1`) mix path and function syntax without a specified dialect. They are placeholders.
* **Depends on:** #167 (who evaluates) and the grammar specification of the dialect; the verifier check V09 states the same rule independently (so the rule has an owner even while the text is a placeholder).
* **Blocks:** the finalization of the three `ModuleRelease` and one `PrimitiveRelease` surface entries; V09 and kind checks in the Relay implementation; any Form evaluation of surface `validation`.
* **Recommendation:** last and largest: a separate grammar specification with its own vectors; no implicit path-language mixture.

### Also noticed, not asserted as blockers

* The reason `module_identity_mismatch` (V08) is a proposal of the draft; the Relay plan does not name it yet.
* The `name` member of `ModuleRelease` has no format contract (none is invented). With D1 settled it would follow the node-name or an identity rule; unspecified.

## 3. Dependencies and proposed order

```
#167 visibility ──┐
                  ├──> P2 dialect ──┐
P7 (owner)  ──────┘                 │
P1 flavor ──> P4 timestamp ─────────┴──> finalization PR
```

1. **#167 visibility** and **P7**: small, independent, owner decisions plus an issue.
2. **P1**: the largest tooling reuse; unlocks P4.
3. **P4** after P1.
4. **P2** last; it needs #167's answer for the evaluator.
5. **Finalization PR** only when all five are closed.

## 4. Finalization criteria (for the later pull request)

1. D1, P1, P2, P4, P7 closed by recorded decisions and #167 closed or explicitly accepted with its status.
2. Every placeholder or provisional marker removed from the parts and the declaration text, by the decisions, with the semantics of each decision stated.
3. `check_grammar.py` 0 findings under the then-current pinned profile for every composed schema.
4. `check_declaration.py` CONSISTENT and `selftest_declaration.py` accepting, with owners and statuses updated only where a decision changed them.
5. The historical-record regression protection unchanged and green.
6. The header of every part states the status; the probe evidence digests regenerated in the same change and shown.
