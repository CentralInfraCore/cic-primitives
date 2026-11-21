# P7: the reason for an integer beyond 2^53 - 1 (decision preparation)

Status: **DECIDED (owner, 2026-11-21): option B.** Sections 1 to 6 are the preparation (#44, unchanged); section 7 records the decision and its effect. Normative decision and declaration only: **no implementation** (the reference verifier, the producer and the vectors are not changed).

## 1. The question

Under admission profile A the closed value domain is null, boolean, integer with absolute value at most 2^53 - 1 (9007199254740991), and string (`RELEASE-CONTRACT-GENERALIZATION-PLAN.md`, "Closed domain"; declaration requirement G02, over the **whole** value tree, opaque member contents included). An integer above the bound is outside the domain. The plan names the reason `value_type_unsupported` for "a float, a date, a timestamp, a binary or any other type", and names **no** reason for an integer of a supported type with an unsupported magnitude. G02 currently lists `value_type_unsupported` as a placeholder. Two options:

* **A. Keep `value_type_unsupported`** for both, and amend the plan sentence so that it says so ("a value outside the closed domain: another type, or an integer beyond the bound").
* **B. Introduce a separate reason** for the magnitude (working name `integer_out_of_range`; the name is itself part of the decision), keep `value_type_unsupported` for types.

## 2. Facts (measured or read; evidence in `docs/evidence/p7-integer-range-reason/`)

1. **Nothing emits or consumes the reason today.** `value_type_unsupported` occurs in no file of `tools/` or `tests/` (the reference verifier, its reason lists, its vectors, its tests) and not in the CIC_Relay worktree (`reason-usage.txt`). It occurs only in the generalization plan, the schema-set design, the conformance declaration and `check_declaration.py` (its closed set `A_REASONS`). Profile A is not implemented anywhere; G02 is `planned`.
2. **No signed record is affected.** The records of the tags `v0.1.4`, `v0.1.5`, `v0.2.0`, `v0.2.1` contain integers only as the envelope numbers (largest 3); no scanned fixture or probe record has an integer above 2^53 - 1 (`scan-output.txt`: the four required tag records, processed 4 of 4, plus the other release records of those tags and 38 fixture files, 0 findings). The scan is **fail-closed** (review #44 F1): a git error, a missing, empty or unreadable record, a required record not processed or no fixture found makes it exit 1 instead of printing a zero; its self-test plants 12 such cases and a mutation run shows the self-test goes red when the checks are removed (`scan-selftest-output.txt`, `scan-selftest-mutants-output.txt`; the layers overlap, so a single removed layer can be masked by another, which the mutation output says openly). A reason identifier is an output of the verifier, not a member of a record, so it is in no digest or signature.
3. **Historical records are outside the question.** The closed domain exists "under A only"; records verified under H are not subject to it (plan, same section). Neither option touches the H path.
4. **The readers disagree beyond the bound, which is why a bound exists.** PyYAML reads every tested integer exactly, up to 18446744073709551616 (`pyyaml-reading-output.txt`). The Forms (Rust and Go identical, `docs/evidence/forms-capability-measurement/`, case K06): 2^53 - 1 .. int64 max accepted, an integer beyond int64 refused at parse (`UNSUPPORTED_SYNTAX`). So between 2^53 and the int64 maximum the Forms accept what A refuses, and beyond int64 the Forms refuse earlier and with a different code than the verifier's reason: the verifier is the only layer that can state the bound, as G02 says, and the reason must therefore be its own.
5. **The vocabulary is already fine-grained where readers can differ.** The plan separates `key_not_string`, `duplicate_key`, `reading_key_differs`, `reading_structure_differs`, `reading_value_differs`. A magnitude reason would follow that style; a type reason covering a magnitude would be the exception.
6. **The Forms status does not depend on the answer.** The Form cannot evaluate G02 either way; the verifier is the named owner.

## 3. Backward compatibility

| Question | Option A | Option B |
|---|---|---|
| Existing records, signatures, digests | unchanged | unchanged |
| Reason vocabulary of the published contract (section 11 of `RELEASE-RECORD-CONTRACT.md`; the reference verifier's `RECORD_REASONS`) | unchanged: the reason is not in it | unchanged until profile A is implemented; then one identifier more |
| A consumer matching reasons exhaustively | cannot exist yet (no emitter); later it sees one reason for two causes | later it sees one more identifier; additive |
| H path (historical records) | untouched | untouched |
| Existing conformance vectors and tests | none uses the reason | none uses the reason |
| Reason inventory accounted by `check_declaration.py` (37 identifiers) | unchanged | 38; `A_REASONS`, the declaration, the self-test count change, in the decision PR |
| Plan text | one sentence amended (the type wording no longer fits a magnitude) | one reason added to the table of reasons of the parse stage |
| Later reversal | merging the two is a rename of an identifier that, once published, consumers may match | splitting later is a vocabulary extension after consumers exist: the more expensive change once profile A ships |

Neither option breaks anything that exists. The difference is what is cheap **now**, while nothing consumes the reason: a distinct identifier costs documentation only today; separating a merged reason later costs a compatibility question.

## 4. Recommendation (not a decision)

**Option B**, with the stated boundary (absolute value at most 2^53 - 1, so -(2^53 - 1) is in the domain and -2^53 is not), at the same check stage as `value_type_unsupported` (the raw parse, before any comparison). Reasons: the cause a producer must fix differs (a value that is the wrong type versus a number that is too large), the plan's own style separates causes readers can disagree on, and the cost is lowest now.

Open inside B, for the owner: the final identifier (`integer_out_of_range` is a working name), and whether the check lives in the verifier only (G02, as now) or also in a producer-side refusal like P01.

## 5. What each option would change (after the decision; not done here)

* Both: the plan section 5 sentence and the Hungarian plan; the G02 text and reasons in `contract-conformance.yaml` (the OPEN P7 note is removed); `RELEASE-SCHEMA-OPEN-POINTS.md` and the design doc section 7 (P7 closed).
* B only: `A_REASONS` in `check_declaration.py` and the inventory count, with the self-test planted defect "the new reason has no owner" refused.
* Vectors for the later implementation (planned, with the reference verifier): 2^53 - 1 accepted; 2^53 refused; -(2^53 - 1) accepted; -2^53 refused; an integer beyond int64 refused; the same values inside an opaque member and inside a list; a value one above the bound written in a non-decimal form is a separate question for the reader specification.

## 6. Not claimed

* No claim that any reader other than PyYAML, the Rust Form and the Go Form behaves in a given way beyond the bound (JavaScript and others are not measured).
* No claim about the plan's future text, or about reasons other than this one.
* The scan covers the four tagged records, `tests/fixtures` and the release-schema probe records; it does not cover records that exist only outside these repositories.

## 7. Decision (owner, 2026-11-21) and its effect

* **Reason:** `integer_out_of_range` (the identifier asked about in section 4 is final). A value of another type is refused with `value_type_unsupported`: a type error and a range error are two distinct events.
* **Range:** -(2^53-1) .. +(2^53-1), inclusive.
* **Where:** the producer refuses to emit such a record **and** the verifier refuses it; the verifier checks **independently** and never relies on the producer's result.
* **Scope:** the whole value tree, the contents of opaque members included.
* **Profile H:** unchanged.
* **Effect in the repository (this change):** the generalization plan, EN and HU (closed domain and the parse stage); `contract-conformance.yaml` (G02 names both reasons and states the independence; the new requirement P02 is the producer side; both `planned`); `check_declaration.py` (38 known reasons; the new notion of a shared reason: a reason with a verifier executor and a producer executor, both required; G02 must state the independence and name both reasons; P02 required); `selftest_declaration.py` (50 checks, 48 planted defects, 7 of them new); the open-points and design documents. Evidence: `docs/evidence/p7-integer-out-of-range-decision/`.
* **Not done:** the reference verifier does not make the profile A checks; the producer does not refuse; no vector exists. The five boundary vectors of section 5 remain to be written with the implementation. The reason is **not** added to the published contract table (section 11 of `RELEASE-RECORD-CONTRACT.md`), because the verifier does not emit it yet.
