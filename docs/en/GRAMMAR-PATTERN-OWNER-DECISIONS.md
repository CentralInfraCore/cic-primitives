# The `pattern` profile: the owner's decisions of 2026-11-23, recorded, and the check of gate G-0

**A decision record and an isolated check: documentation and tooling only.** It changes no approved file (the 513 approved vectors keep SHA-256 `e7ece43a9486187c16a482a96a86d22cf82407711be940920155f4e3abe277e0`), creates **no normative extension**, **closes no gate**, and is **not** permission to implement, to publish, to change the CI gate or to start the independent implementation: all of that stays on hold. Data: `docs/design/pattern-profile-plan/decisions.yaml`. Check: `docs/evidence/pattern-g0/check_g0.py`. Base: `cc6b614b5dedf0397e2f7b20952789394ec2c7f8` (#53 merged; #52, #54 and #53 are in `devel`).

## 1. Three things that are kept apart

| | What it is | Where it lives | Who can make it true |
|---|---|---|---|
| **Decision** | the owner's statement, recorded with its source and date | `decisions.yaml` (`source`, `decisions`) | the owner |
| **Evidence** | what backs the decision: the files it rests on, bound by SHA-256 to a base commit, and the artifacts the plan names | `decisions.yaml` (`bound_to`, `evidence_files`, `spec_text`) | files and hashes, checked by the tool |
| **Closure** | the state of the gate G-0 | a separate owner closure record (`g0-closure.yaml`), which names the digest of the decision record | the owner, separately; **none exists** |

The check never closes a gate: its best result is `READY_FOR_OWNER_CLOSURE`.

## 2. The recorded decisions

The source is the owner's statement of 2026-11-23 (a transcribed statement: **not signed and not verifiable by this repository**; the owner confirms it by reviewing this package). The verbatim table and sentence are in the record **as received, in UTF-8 with the accents, the en dashes and the bold markers** (the check normalises them only when it reads the statuses), and the check compares every structured status with that table.

| Id | Decision | Status | Closes at | What it does **not** mean |
|---|---|---|---|---|
| D1 to D6 | the semantics of the implementation specification (#52): a wrong-typed pin is `pattern_profile_unknown`; an explicit null is unknown; a schema without a pattern contract evaluates no pin; the traversal is source order; an expression that is not a string is a reader error; the schema layer's error vocabulary is a separate contract | confirmed | G-0 | not an implementation permission |
| OP-1 | the YAML 1.2 core schema, type preservation, strict reader rules | decided | G-0 | the owner's statement does not itemise the strict rules; the working basis is the plan's proposed fixation; **the specification text that fixes them is not yet written** |
| OP-2 | the content of **all 47** extension cases is accepted | accepted_content | G-0 | **not a normative conformance set**: no normative extension file exists, 560 is not claimed, the 513 are unchanged |
| OP-3 | the measurement method is accepted | partial | **G-6** | the constant `c` and the counted operations are **not fixed**; they must be fixed before the G-6 acceptance measurement, not adjusted to its results |
| OP-4 | a standalone harness and the Go/Rust cross-check | decided | G-4 | the gate G-4 still requires the executed cross-check |
| D7, D8 | composition of schema parts; the order of several violating values | hold | none | no case depends on them (checked) |

## 3. What G-0 requires, and what it does not

The merged plan names for G-0: D1 to D6 confirmed by the owner; OP-1 closed by a recorded specification decision (the evidence: *the owner's recorded decisions and the specification text that fixes OP-1*); the 47 cases accepted, rejected or deferred by the owner (OP-2). **That is all.** OP-3 closes at G-6 and OP-4 at G-4, so their state does not block G-0: the check evaluates them only for consistency (the plan says where they close; OP-3 records its precondition). A check that demanded the G-6 constant at G-0 would be wrong.

## 4. The result today

`python3 docs/evidence/pattern-g0/check_g0.py` (`results/check_g0.txt`): **`G-0: NOT_READY`, for exactly one reason.**

| Criterion | Decision | Evidence |
|---|---|---|
| D1 to D6 | confirmed | verified (the specification and the extension review bound by SHA-256) |
| OP-1 | decided | **unverified: the specification text that fixes OP-1 does not exist** |
| OP-2 | accepted_content | verified (the 47 cases and their review bound by SHA-256; every accepted case depends only on confirmed decisions; `normative: false`) |

**This is a finding, not a defect of the decision.** The plan asks of G-0 a specification text that fixes the YAML scalar schema, the tags, the duplicate keys, the aliases and the merge keys; the owner decided the direction but the text does not exist, and this package does not write it: it would be a normative text with details the owner's statement does not itemise. The ways forward are the owner's: (a) authorise the specification text of OP-1 (a separate documentation pull request, with the reader tests the plan names); (b) decide that the recorded decision suffices as evidence, in which case the plan's wording of the G-0 evidence has to be changed by its own reviewed pull request, not by this check.

## 5. What the check does and the tests that it can fail

`check_g0.py`: the record is well-formed with a source, a date, a channel, a reference and the verbatim statement; every bound file exists and has the recorded SHA-256 (a stale or wrong hash is `INVALID`); every decision of D1 to D8 and OP-1 to OP-4 is recorded once and its status equals the owner's verbatim table (a contradiction is `INVALID`); the plan's `closed_by` of each open point equals the record's; G-0 of the plan still names D1 to D6, OP-1 and OP-2 and **names no later open point**; per prerequisite the decision and the evidence are shown separately; OP-2 is not normative, counts 47 cases, and its accepted cases depend only on confirmed decisions and none on a decision on hold; the recorded specification text of OP-1 must exist, have the recorded SHA-256 and treat at least the topics of OP-1 (YAML 1.2, core schema, tags, duplicate keys, aliases, merge keys): **a lower bound on presence, not a judgement of the content, which only review can give**; a closure record is accepted only if it is an owner closure of G-0, names the digest of the decision record, and the prerequisites are all met, **so no closure record can turn a missing or stale OP-1 evidence into `CLOSED`** (it makes the verdict `INVALID`). Verdicts: `INVALID`, `NOT_READY`, `READY_FOR_OWNER_CLOSURE`, `CLOSED`; exit 0 only for the last two.

`selftest_g0.py` (29 checks): the real state (exactly one unmet item; OP-3 and OP-4 do not block); two positive controls in a temporary root with a **fixture** of the OP-1 text (a complete package is `READY_FOR_OWNER_CLOSURE`; with a valid closure record it is `CLOSED`); **24 planted faults**, each applied to the complete package and counted only when the verdict is not READY or CLOSED, the exit is 1, and the intended `FAIL-EXPECT` line is printed: a missing decision, a contradictory record, a record that disagrees with the owner's statement (two), missing provenance (two), a wrong SHA-256, a bound file changed after the decision, an unmet prerequisite, a changed OP-1 text, a prerequisite not confirmed, accepted cases that depend on a decision on hold (two), OP-2 treated as normative, a wrong case count, OP-3 closing at G-0, OP-3 without its precondition, a plan that demands a later open point at G-0, a plan that no longer names OP-2, an unknown decision, an OP-1 text that does not treat the aliases, and three closure faults (without evidence, wrong digest, not an owner closure); and an infrastructure control (exit 2).

## 6. Not shown, stated

* The owner's statement is transcribed; this repository cannot authenticate it.
* OP-1's strict reader rules are not itemised by the statement; the specification text is missing.
* The check shows that the record is consistent with its sources and bound files, not that the decisions are right.
* No normative extension exists; the 47 cases are accepted in content only.
* The coverage accounting of the merged plan (#54) still counts the extension through the requirement links, not the verifying cases: a separate follow-up, not done here.
* The proof-of-time chain (expiry 2026-12-31 13:22:39 UTC) is a separate decision branch, not part of this package.
