# The `pattern` profile: the normative vector set (draft), with requirement-to-vector traceability

Status: **a draft of the conformance reference, documentation and isolated measurement only.** Not in this pull request, all on hold: an implementation of the profile, the CI gate that would read the vectors, publication of the vector file (placing it under `proposals/`, adding it to the release list or to `project.yaml`), any schema, grammar, checker, Forms or verifier change; P2, P4, Forms #166/#167 and the release-schema finalization. The Primitives gain no functionality: the vectors only make the **already accepted** parameter semantics checkable (O1 to O6 decided in #46 to #48).

The vector file is `docs/design/pattern-profile-vectors/pattern-profile.yaml`. It lives under `docs/design/` on purpose: a file under `proposals/` would belong to the published artifact list, and publishing it is a separate decision. The tooling and the results are in `docs/evidence/pattern-vectors/`.

## 1. What the vectors are

Three kinds, one file (`vectors_format: 1`):

| Kind | A vector says | Count |
|---|---|---|
| `expressions` | an expression text is **accepted** (with its size PI) or **refused with exactly one code** | 278 (92 accepted, 186 refused) |
| `values` | for an accepted expression and a value: `match`, or the value code `pattern_value_mismatch`, `pattern_value_too_long`, `pattern_value_not_unicode_scalar` | 215 (93 match, 111 mismatch, 7 too long, 4 not a scalar value) |
| `schemas` | a pin state and the pattern contracts of a schema in document order: accepted, or refused with a code and the position of the refused contract | 20 (7 accepted, 13 refused) |

Total 513 vectors (the 509 approved in #49 and 4 identical-pin vectors), 66 requirements, 31 codes (25 expression, 3 value, 3 pin). Every vector names the requirements it exercises (`req`).

**Encoding.** No reader may depend on YAML escapes: an expression or a value is a plain string of printable ASCII, or `{seq: [...]}` whose elements are literal ASCII text or `[codepoint, count]` pairs (`[10, 1]` is one line feed, `[97, 256]` is 256 times `a`, `[55296, 1]` is a lone surrogate). The vector check refuses any other form.

**Authoring rule.** *Every expectation is authored by hand from the specification text* (`GRAMMAR-PATTERN-PROFILE-DESIGN.md` 3.1 to 3.5 and 4, `GRAMMAR-PATTERN-LIMITS-AND-ERRORS.md` 2.1, 2.2 and 3.2), never copied from the output of an implementation; the PI of each accepted expression is derived by hand from the recurrence. The implementations were run against the vectors **afterwards**, and a disagreement is logged (section 3), not corrected automatically. The only helper that formats text lines (the values of the nine existing contracts) takes the values and the verdicts from hand-written tables and computes nothing.

## 2. What is covered

The matrix of requirement to vector is printed by `check_vectors.py` (`results/check_vectors.txt`); every one of the 66 requirements has at least one vector, every one of the 31 codes has at least one vector that expects it, and every limit has an accepting and a refusing vector (the check refuses the file otherwise). By group:

| Group | Requirements (ids) | Vectors |
|---|---|---|
| matching semantics | `R-MATCH-*` (full match, anchors add nothing, dot, trailing LF, classes, alternation, quantifiers, groups, escapes, the empty value) | accepted expressions and 130 value vectors |
| the value rules | `R-VALUE-*`, `R-LIM-VALUE` (scalar value, 256 code points counted as code points, the order) | 14 value vectors, 256/257 boundaries |
| the text and its body | `R-T1-*`, `R-BODY-ANCHORS`, `R-LIM-LENGTH` | the order empty / too long / not ASCII; the parity rule of a trailing `$` (`a\$`, `a\\$`, `a\\\$`) |
| the scan | `R-S1`, `R-S2`, `R-S3-*` (depth, empty branch, group extension, unbalanced, escapes, anchors, metacharacters) | per code, several texts each |
| classes | `R-C1` to `R-C4`, `R-PREC-CLASS-ORDER` | the pre-check C1 against every other class rule, including the review counter-examples of #48 |
| quantifiers | `R-Q1` to `R-Q6`, `R-Q-MALFORMED`, `R-PREC-REPEAT-ORDER` | the order of the checks inside one quantifier |
| size | `R-T3-SIZE`, `R-LIM-PI`, `R-PI-RECURRENCE`, `R-PI-ZERO-REPEAT` | the boundary 2048 / 2049 in four shapes, the largest program of the limits (PI 241 250), hand-derived PI for 100 expressions (92 accepted, 8 size refusals), the zero repeat |
| limits | `R-LIM-*` | each limit at its edge: accepted and refused |
| precedence | `R-PREC-*`, `R-SCHEMA-ORDER` | multi-defect texts and schemas whose first refused expression is at a different tier than a later one |
| the pin | `R-PIN-*`, `R-SCHEMA-WHOLE` | missing, unknown, conflicting; the pin before every expression; no pin without a pattern contract |
| compatibility | `R-COMPAT-CONTRACTS` | the 9 existing expressions with their PI and 85 values (valid, empty, trailing LF, one more, one less, non-ASCII digits; **shape-only matches such as month 13 are matches by design**, P4 stays open) |

**Not testable by a verdict vector** (listed in the file, with where each must be tested instead): `R-LINEAR` (a timing gate on adversarial input), `R-INDEPENDENT-CHECK` (the implementations of the producer and the verifier), `R-VERSION-EVIDENCE` (the gate), `R-VERIFIER-BUDGET` (the verifier, outside this profile). The vectors do not claim to cover them.

## 3. How the vectors were checked, and what that does and does not prove

All of it is isolated measurement (`docs/evidence/pattern-vectors/`, typed exits: 0 ok, 1 a measured failure, 2 infrastructure, 3 a failed canary of a native runner; infrastructure is never a result):

* **Structure and coverage** (`check_vectors.py`): unique ids, known requirements and codes, the encoding, a PI on every accepted expression, the coverage rules above. Exit 0.
* **Conformance** (`conform.py`, `results/conform.txt`): the prototype (expression verdict, PI, value verdict, and the schema rule written there from the text), the second implementation written from the rule text (`spec_classifier.py`, expression verdicts), and **Go `regexp` and Rust `regex`** (the value verdicts of every value vector they can be given, and rule D: every accepted expression with PI <= 2048 must compile): 278 expression vectors, 215 value vectors, 20 schema vectors and 296 native cases, **0 disagreements**.
* **RED-initial against the legacy reading** (`red-initial-legacy.txt`): Python `re.search` of the original expression, what the schema library does today, disagrees with the vectors on **28 of the 204 match/mismatch vectors**, among them every trailing-line-feed vector of the nine existing contracts and the unanchored expressions that `search` accepts as a part: the vectors tell the profile from the legacy reading.
* **The tooling can fail, for the right reason** (`selftest-vectors-output.txt`, 43 checks): an unmodified positive control for the check and for the conformance run; **21 planted faults in a copy of the vector file** (a requirement or a code without a vector, an unknown requirement or code, a duplicate id, a non-ASCII expression, a limit without its refusing side, an accepted expression without a PI, a verdict of another kind, **a schema refusal without its position, a pin refusal that carries one, a position outside the schema, the declared pi_max, the declared length limit, the profile name, the code list or the known pin version changed, every PI-boundary vector moved away from pi_max, a declared pin with different versions, identical unknown declarations expected to be accepted**), each counted only with a `FAIL-EXPECT` line of the intended check; **13 planted defects in the implementations** (7 in the prototype, 3 in the implementation of the text, 3 in the schema rule: the last refused contract reported instead of the first, the pin checked after the expressions, identical pin declarations treated as a conflict), **2 vector files with a wrong position or a wrong declared limit** run through the conformance run, each counted only with `DISAGREE <implementation> <vector id>` for the intended vector; **2 planted defects in a copy of the Go runner**: one that matches any line feed, caught by the runner's own canary (exit 3, no result of that runner is used), and one that matches only a line feed after `abc`, which passes all four canaries and is caught only by the vectors (`DISAGREE G V-M021`); and 3 infrastructure controls (an unreadable vector file for both tools, a missing Go toolchain) that must exit 2 and are not detections.

**Review round 1 of #49 (F1, F2).** *F1, the position of a schema refusal:* the conformance run used to drop the position when a vector had none, and the check did not require it. Now a schema vector that is refused for an expression **must** carry `at` (1 up to the number of contracts), a pin refusal and an accepted schema **must not**, and the conformance run compares the whole triple (verdict, code, position) with nothing masked. *F2, the normative metadata:* the file declared the profile version and the seven limits, but nothing compared them with the decisions. `check_vectors.py` now holds the accepted decisions independently of the file (the seven limits of #46 and #48, the 25 + 3 + 3 codes, the profile name) and refuses any difference; it also ties the declared `pi_max`, `length` and `value_code_points` to the vectors' own boundaries (an accepted vector at the limit and a refused one just above it), and the known pin version of the schema vectors to the profile version; the conformance run compares the declared limits with the constants of the implementation. The profile version stays a working assumption (any positive integer, consistent inside the file).

**Authoring log (what the vectors found while they were written).** Before the first run, re-reading the text against my own entries corrected: the PI of `(a{10}b){0,3}` (99 -> 36), of `a{2,3}` x 4 (20 -> 16) and of `(a){2,3}` (5 -> 4); three size-boundary and four precedence vectors that used a group of `{0,255}` repeated `{0,4}`, which the **product rule refuses at tier 2** (255 x 4 = 1020 > 1000) before the size rule is reached (rebuilt with 250); the vector for the escape `\u0041`, whose backslash-u sequence was turned into a plain `A` on its way into the file by a tooling quirk (restored, and the encoding check now forbids anything but printable ASCII); and one vector removed because the text does not decide it (two identical pin declarations, section 5). **The first conformance run found no disagreement**; none of the corrections above came from running an implementation.

**What this does not prove.** The same author wrote the design text, the vectors and the prototypes; the independence of the vectors is the rule that every entry was derived from the text and re-read against it, not a different mind. 0 disagreements on the first run is also what a shared misreading of the text would produce; the RED-initial and the planted defects show that the vectors and the tooling *can* disagree, not that the text is right. The real test of the vectors is a third implementation by another author, in another language, from the text and the vectors only (on hold with the gate).

## 4. How an implementation reads a vector

* **Expression vector, `accept`:** the text passes tiers 1 to 3 and its PI equals `pi`. **`refuse`:** the result is *exactly* `code` (one code, by the precedence of limits doc 3.2); an expression refused at tier 1 or 2 has no PI to compare, and a tier-3 vector states the PI that caused it.
* **Value vector:** the expression is accepted; the verdict is `match` or exactly the stated value code, in the order scalar value, then too long (the matcher is not run), then match or mismatch.
* **Schema vector:** the three pin states are decided first and only when the schema has at least one pattern contract; then the first refused contract in document order decides the code and `at`; a refused schema is refused as a whole.
* The profile version in the file (`1`) is a working assumption of the vectors; the pin decision fixes it.

## 5. Open points found while authoring, with the review recommendation (owner decision pending)

The external review of #49 recommended the following; the points marked decided were decided by the owner (2026-11-22). A vector is added only for a decided point.

| Open point | Review recommendation | In the vectors |
|---|---|---|
| two identical pin declarations | **decided (owner, 2026-11-22):** identical declarations count as one declaration, not a conflict | `S-017` to `S-020` (pin state `declared`, a list of identical versions), requirement `R-PIN-IDENTICAL` |
| two different pins | refused | `S-004`, `S-007` |
| the same YAML key more than once | the responsibility of the document reader, not of the pattern profile | none, outside the profile |
| traversal order of nested contracts for "document order" | waits for the implementation specification; the pattern primitive must not own the document traversal | the schema vectors use a flat list |
| programs with PI 0 (`a{0}`, `(a{0}){255}`) | **allowed**; an expression that accepts the empty value is a valid rule, and no artificial restriction is introduced | `X-A021`, `X-A025`, `V-Q019`, `V-Q020` already record the accepted behavior |
| the concrete profile version identifier | waits for the pin decision | `1`, a working assumption |
| the two unreachable anchor rules of the prototype classifier | not part of the normative semantics | not in the vectors |

## 6. Traceability and evidence

| What | Where |
|---|---|
| the vectors | `docs/design/pattern-profile-vectors/pattern-profile.yaml` |
| the requirement-to-vector matrix, the code-to-vector counts | `docs/evidence/pattern-vectors/results/check_vectors.txt` |
| conformance of the implementations | `results/conform.txt` |
| the legacy reading is distinguished | `results/red-initial-legacy.txt` |
| the tooling can fail | `results/selftest-vectors-output.txt` |
| the files and their hashes | `docs/evidence/pattern-vectors/README.md`, `SHA256SUMS` |

## 6a. Integrity of the files the package writes (package of 2026-11-22)

A tooling quirk once turned the six-character sequence `\u0041` (backslash, u, 0041) into the plain character `A` on its way into a file. The result is printable ASCII and still valid, so an ASCII check cannot see it; it was found only by re-reading. The owner decided that the next package carries two mechanisms that cover **different** errors, with these conditions:

* **Byte-level canaries** (`integrity_check.py`): the raw bytes of the file, before any decoding, must contain the expected representation of every escape-shaped text (eight canaries in the vector file, plus the sentence of the two documents that states the sequence in prose). The expected bytes are held in the checker as **integer byte values**, so the checker itself holds no escape text that a faulty writer could change; the expectation does not depend on the writing mechanism.
* **A SHA-256 reference** (`integrity-reference.json`, and the same value in the PR description, where the review checks it): the reference is computed from the **intended bytes before they are written** (the approved bytes of the merged git object of #49 with the additions inserted, hashed in memory, then written and read back and compared). **Verification is not authentication.** The tool *verifies* that the file equals the reference; it cannot *authenticate* the reference, because it cannot establish when or from which bytes the value was computed (a value computed from a file that was already damaged passes the verification, and only the canary still sees the damage; that is why both mechanisms are kept). The authentication is a **procedure**: the value stated in the PR description, recomputed independently by the review from the git objects, and supplied **explicitly** in the acceptance run (`integrity_check.py --acceptance --expect-sha256 VALUE`, which refuses `--reference`, either switch off, and a missing value, exit 2). The repository reference file `integrity-reference.json` serves the default run only and is **not an independent basis of trust**; the default run says so in its output. That the reference was computed before the write is a statement of the author, documented here and in the PR description, which the final file's hash alone does not prove.
* **The checker never repairs a damaged file** (it opens files read-only; the self-test compares the bytes before and after), and it is **fail-closed**: `--no-canary` together with `--no-sha` selects no check and is refused (exit 2, INCOMPLETE), so a run that checks nothing cannot report success; each switch alone stays available, because the self-test needs them to show that the two mechanisms differ.
* **The existing vectors are unchanged** (`verify_unchanged.py`): each of the 509 approved vectors, each of the 65 approved requirements and the metadata equal the merged ones entry by entry, the approved lines are an ordered subsequence of the new file (nothing rewritten, only inserted), and the only differences are the four vectors `S-017` to `S-020` and the requirement `R-PIN-IDENTICAL`. The approved bytes come from the git object; their SHA-256 (`bea100d4...`) is also in the PR description.
* **Reproducible negative tests** (`selftest_integrity.py`, `results/selftest-integrity-output.txt`, 31 checks): the corruption is simulated on copies (backslash, u and four hex digits replaced by the character they name); the `\u0041` to `A` change is rejected by both mechanisms, by the canary alone and by the SHA-256 alone; damage at a place no canary covers is seen only by the SHA-256 (and missed by the canary alone), which shows that the two differ; a reference computed from the damaged file passes the SHA-256 and the canary still rejects it, which shows why the reference must come from before the write; an intact file against a wrong reference is rejected; the same for the sentence in a document; the checker leaves the damaged copy unchanged; six planted deviations of the unchanged-check are rejected; the two switches together are refused (exit 2, also on a damaged file); the acceptance run passes with the explicit approved value and says so, is refused without it, with a reference file or with a switch off (exit 2), rejects the damaged file, and cannot tell a value taken from the damaged file (the SHA-256 passes, the canary rejects it); the default run states that the repository reference is verification only; and the infrastructure controls (a missing file, reference or approved object) exit 2 and are not detections.

This is a check of the tool chain, not an extension of the Primitives semantics.

## 7. For the owner

| # | Point | Recommendation |
|---|---|---|
| V1 | the vector file as the draft conformance reference of the profile | accept as a draft; publication (placing under `proposals/`, the release list, `project.yaml`) is a separate step |
| V2 | the open points of section 5 | decide them (the review recommendation is in the table); only the identical-pin point would add a vector |
| V3 | a third implementation, by another author and in another language, from the text and the vectors only | the real independence test; belongs with the gate |
| V4 | the CI gate and the implementation | on hold; this document fixes what they must conform to |

Everything not named here stays on hold: P2, P4, Forms #166/#167, the schema finalization, the Relay #162 implementation, an implementation of P1, the CI gate.
