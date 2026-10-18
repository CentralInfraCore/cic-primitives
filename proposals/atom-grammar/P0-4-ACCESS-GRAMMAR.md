# P0.4 — Access and PolicySurface grammar (`access-policy/1`)

Status: **proposed**, for review in the P0.4 PR. Nothing here is an accepted rule until
that PR is reviewed and merged. Decision record: `ai/DECISIONS.md` D-018. Closes
`cic-primitives#17` only when that PR is merged and the issue's acceptance list is met.

Scope: the instance grammar of the six-field Access atom, the type of the three-state
`inherit`, and a deterministic resolution of an effective permission from the PolicySurface.
It does **not** change the recognition rule (`cic-primitive-forms` ADR 0001), the grammar
identity pinned downstream (ADR 0002), the Relay's runtime enforcement, or where
`conformance` lives.

Everything marked **design decision** below is a proposal made here. It is not a fact proven
by the earlier upstream text; the evidence column of the matrix
(`p0-4-contradiction-matrix.md`) says what the corpus does and does not show. In particular
the corpus contains **no** field-level `inherit` key and **no** `inherit_policy` other than
`true`; the `false`/`0` difference below is a design, tested by vectors, not a measurement.

Executable form: `access_policy.py`. Golden vectors: `access-vectors/`. Gate:
`check_access_vectors.py` (`make grammar.local`).

## 1. The Access atom

Six fields, unchanged: `value`, `access`, `modify`, `inherit`, `default_injection`,
`conformance`.

- **Short form** `key: value`. **Expanded form** has all six keys. Recognition is
  schema-driven and is exactly ADR 0001 (key set equal to the six = expanded; the six plus
  another key = `EXPANDED_WITH_EXTRA_KEY`; anything else = short). It looks at keys, never
  at values. Not changed here.
- A map with only some of the six keys is **short form**, i.e. data. At a scalar position it
  is `MAP_AT_SCALAR_POSITION`; at an opaque position it is the `value`. A partial expanded
  form is **never** a policy override.
- **Expansion fills symbolic defaults, not permissions**: `access: inherit`,
  `modify: inherit`, `inherit: <inherit mode>`, `default_injection: null`,
  `conformance: implemented`. Expansion never computes an effective permission.

### Value rules

| Field | Type | Default | Rules |
|---|---|---|---|
| `access`, `modify` | `list<CertPattern> \| inherit` | `inherit` | the symbol `inherit` = no field-level rule; `[]` = explicit empty set, nobody; `[inherit]` is a list with an invalid CertPattern (`INVALID_CERT_PATTERN`); `null`, other strings, maps are `INVALID_ACCESS_VALUE` |
| `inherit` | `InheritanceMode` | `inherit` | section 2 |
| `default_injection` | any | `null` | separate from the permission decision; never an input of resolution |
| `conformance` | `implemented \| not_implemented \| deprecated` | `implemented` | section 6 |

Absent key (which makes the node short), `null`, `[]` and the symbol `inherit` are four
different things and are never interchangeable.

**CertPattern.** A list element is one pattern: `attr=value` pairs joined by `,` with no
spaces (`OU=ops,O=acme`); pairs of one pattern are AND-ed, list elements are OR-ed; `*` in a
value is a wildcard. A bare `inherit` is not a pattern. Note the YAML hazard
(matrix, finding F2): the unquoted flow list `[OU=adapters, O=cic]` is **two** elements, OR.

## 2. `InheritanceMode`

`InheritanceMode = inherit | no-inherit | reset`, one concept at two scopes:

- `Access.inherit`: what a **field** passes to the sub-object it carries (the *carrier*).
- `PolicySurface.inherit_policy`: what an **object** takes from its ancestors' PolicySurface.

### Spelling and versions

| Grammar | `inherit` | `no-inherit` | `reset` |
|---|---|---|---|
| 1 (the existing grammar) | `true` | `false` | `0` |
| 2 | `inherit` | `no-inherit` | `reset` |

- The grammar version is bound as described in "Grammar version binding" below. **Existing
  documents are grammar 1 and are read exactly as before.**
- Within one bound version there is exactly one spelling set, for the whole document. The
  other is an error: `INHERIT_ENUM_IN_GRAMMAR_1`, `LEGACY_INHERIT_IN_GRAMMAR_2`. Nothing is
  coerced, and the first node of the wrong spelling fails the document.
- The grammar-1 spellings are told apart by YAML scalar type: boolean `true`, boolean
  `false`, integer `0`. Integer `1`, `0.0`, the strings `"true"`/`"0"`, `null` are
  `INVALID_INHERIT`. `false` and `0` are never equal.
- A round trip keeps the spelling (the mapping is a bijection per version).
- Moving a document from grammar 1 to 2 is an explicit, lossless migration (`migrate_mode`);
  see `P0-4-MIGRATION.md`.

### Grammar version binding

- The version is a property of the **pinned schema** (`schemas/atomic/access.yaml`,
  `spec.access_grammar.version`) and of the **processing context**. It is **not** a key of any
  document: the six-key Access representation and ADR 0001's recognition rule get no seventh key.
- The context supplies the version it expects; it must equal the pin's version
  (`bind_grammar`). Both are required: a missing one is `GRAMMAR_VERSION_MISSING` (there is no
  default to 1), a value that is not one of the supported integers `1`, `2` is
  `UNKNOWN_GRAMMAR_VERSION` (`"1"`, `true`, `3` are all unknown), a difference is
  `GRAMMAR_VERSION_CONFLICT`.
- The pin is what ties the version to the grammar identity downstream: the pinned commit and its
  manifest fix the schema file, so they fix the version. Changing the version is a new schema
  version and a new grammar identity (ADR 0002 of `cic-primitive-forms`), plus migration of every
  document, never a silent change.
- One context binds one version for the whole document (`read_document`), so a document cannot
  mix the two spellings. This schema pin declares **1**.

### Semantics (**design decision**, see D-018 for the conflict analysis)

| Mode | Access scope (carrier field) | PolicySurface scope (object) |
|---|---|---|
| `inherit` | the carrier's explicit `access`/`modify` list is passed to the sub-object, where the sub-object has no rule of its own | after the object's own explicit rules, the ancestors' PolicySurface rules are the fallback |
| `no-inherit` | the carrier's rule is **not** passed down; the sub-object's effective PolicySurface rules apply, **including** the ancestors' chain. The PolicySurface's own inheritance is not switched off | the ancestors' PolicySurface is not read; local declared rules and the documented system default apply |
| `reset` | the carrier's rule **and** the ancestors' PolicySurface rules **and** the system default are cut; the sub-object needs an explicit local rule for the operation | the same cut at object scope |

`reset` never yields an implicit allow: without an explicit local rule for the operation,
resolution denies (`RESET_NO_LOCAL_RULE`, fail closed). The order matters: an object-level
`reset` is applied **before** any carrier rule is used, so a rule passed down from above cannot
be turned into a decision by an object that declared `reset` (vectors
`resolution.object-reset-cuts-carrier-rule-g1/g2`). A carrier rule declared on the field of the
reset object itself still reaches that field's sub-object, and the target field's own explicit
rule (layer 1) and the object's own local rules (layers 2-3) are never cut.

The difference between `no-inherit` and `reset` is proven by vectors on one parent/child
pair (`resolution.diff-field-*`, `resolution.diff-policy-g2-*`): the carrier's rule `[O=partner]`,
the parent's `default_access: [O=acme]`, requestor `O=acme`:

| Carrier mode | Result |
|---|---|
| `inherit` | deny, layer `field_inherited` (the passed rule does not match) |
| `no-inherit` | **allow**, layer `policy_inherited` (the chain still applies) |
| `reset` | **deny**, `RESET_NO_LOCAL_RULE` (nothing local to compute from) |

## 3. PolicySurface types

| Slot | Type | Default |
|---|---|---|
| `default_access` | `list<CertPattern> \| open` | `open` (system layer) |
| `default_modify` | `list<CertPattern> \| owner` | `owner` (system layer) |
| `surface_rules` | `list<SurfaceRule>` | `[]` |
| `inherit_policy` | `InheritanceMode` | `inherit` |

`SurfaceRule = {surface: <name>, access?: list<CertPattern> | inherit, modify?: ...}`. A
missing or `inherit` member declares nothing. Two entries for the same `(surface, operation)`
are `SURFACE_RULE_CONFLICT`. Unknown keys are `UNKNOWN_POLICY_KEY`.

**The defaults `open` and `owner` belong to the system layer.** They are never materialized
into an instance by expansion, because that would shadow a rule an ancestor really declared.
Only an `open`/`owner` the author wrote is a declared rule (and then terminal).

- `open`: any **authenticated** requestor.
- `owner`: the requestor whose identity equals the object's owner identity, where that identity
  comes from a **trusted context supplied to the resolver**, not from the document. A missing or
  untrusted owner context grants nothing (`OWNER_NOT_TRUSTED`); a different trusted owner is
  `OWNER_MISMATCH`.
- The historical text "no PolicySurface: every field is accessible" is narrowed: reading stays
  open (authenticated), writing needs the trusted owner. That sentence contradicted the same
  schema's `default_modify: owner`.

## 4. Deterministic resolution

Input (all declared): the object tree (`parent`, `policy` = a PolicySurface, `absent` =
known to have none, or `unknown`; `carrier` = the Access of the parent field holding the
object), the target (`object`, `surface`, the field's Access), and the request (`op`,
requestor `{authenticated, subject, identity}`, trusted `owner`).

For one operation the first rule found wins, in this order:

1. the target field's explicit `access`/`modify`
2. the target object's `surface_rules` for the surface
3. the target object's declared `default_access`/`default_modify`
4. a. a rule passed down by carrier fields (nearest explicit list wins; a `no-inherit` carrier
      stops everything above it; a `reset` carrier stops field rules **and** the chain);
   b. the ancestors' PolicySurface (`surface_rules`, then declared defaults), walking up while
      each object's `inherit_policy` and each carrier permit it
5. the documented system default (`open` / `owner`), **not** after a `reset` barrier

Rules:

- A found list decides: allow if some pattern matches the authenticated subject, otherwise
  deny. There is no fallback to a more permissive layer.
- An explicit `[]` is terminal: `EXPLICIT_EMPTY`. A parent's `open` cannot rescue it.
- An unauthenticated requestor is denied everywhere (`UNAUTHENTICATED`).
- `owner` needs **two valid identities**: a non-empty string without surrounding whitespace for
  the trusted owner (`OWNER_IDENTITY_INVALID`) and for the requestor
  (`REQUESTOR_IDENTITY_INVALID`), and they must be equal (`OWNER_MISMATCH`). Missing, `null`,
  empty or non-string identities never match each other.
- A `policy: absent` object is transparent; a `policy: {}` (declared, empty) is too, and
  neither hides an ancestor's declared rule.
- Missing object, parent cycle, or an `unknown` policy the walk must read yields outcome
  `error` (`CONTEXT_INCOMPLETE`, `POLICY_CONTEXT_UNKNOWN`). The resolver never invents a
  permission. An unknown ancestor that a decided rule never reaches does not matter.
- Output: `{outcome: allow|deny|error, layer, code}`. Same input, same output; no clock, no I/O.

### Authority of the request context

`requestor.authenticated`, `requestor.subject`, `requestor.identity` and the `owner` record
(`trust`, `identity`) are **inputs from the processing context**: the authenticated channel (the
mTLS handshake result) and a trusted ownership binding. They are never read from the document
being resolved. A document cannot make itself authenticated, cannot produce trusted X.509
attributes and cannot mark its own owner data trusted. The resolver demands the shapes
(`authenticated` is a boolean; an authenticated `subject` is a concrete DN without wildcards;
`owner.trust` is `trusted` or `untrusted`; `op` is `access` or `modify`) and returns the outcome
`error`, code `INVALID_REQUEST_CONTEXT`, otherwise. Verifying the channel and the ownership
binding is Relay work; the contract that the resolver must be given them already is this one.

## 5. Compatibility

See `P0-4-MIGRATION.md`. In short: grammar 1 documents are read as before; new strictness
(`null`, `[inherit]`) rejects values that had no defined meaning; the narrowing of the
historical open write default is the one behavioral change, and it only matters to a
runtime that does not exist yet.

## 6. `conformance`

Stays in the six-field Access; moving it is a separate versioned decision. The authority
boundary is `cic-primitive-forms` ADR 0010, restated as `conformance_basis`:

| Input | Result |
|---|---|
| authored short | `implemented` default, basis `default` |
| authored long `implemented` | basis `authored_claim` (an unauthenticated claim) |
| authored long `not_implemented`/`deprecated` | `CONFORMANCE_NOT_AUTHORABLE` |
| materialized, position attested | any enum value, basis `binding_attested` |
| materialized, not attested | only `implemented` (basis `default`); otherwise `CONFORMANCE_NOT_AUTHORABLE` |

Values outside the closed enum, or of another type (`true`, `Implemented`), are
`INVALID_CONFORMANCE_VALUE`; an origin other than `authored`/`materialized` is `INVALID_ORIGIN`.
`implemented` never proves device support. A `binding_attested` position is never collapsed to
short form (ADR 0001 collapse law, ADR 0010). The Relay's actual rejection of a write to a
`not_implemented` field is later enforcement, not decided here. Schema-level derivation
(`access: {conformance: not_implemented}` in a specialization, D-017) is a different layer and
is untouched.

## 7. What the vectors prove

`make grammar.local` runs the golden vectors and the seeded faults: every model fault, every structural
rule and every schema-sync rule has a fault that turns the gate red, and the `no-inherit`
versus `reset` outcome difference is itself a gate rule. Properties checked across all
vectors: expansion is idempotent and deterministic; moving any resolve case between grammar 1
and 2 does not change its result; every error code of the model is exercised by a negative
vector.

Limit: model and vectors have one author. They prove the rules are consistent and executable,
not that they are right; the independent check is a second implementation (downstream Rust/Go).

## 8. Not decided

- The evaluation of `deprecated` at runtime and the Relay's enforcement of `not_implemented`.
- Where `conformance` finally lives (BindingSurface / CapabilitySurface).
- What exactly a "sub-object" is for list elements and choice cases (the carrier is modeled as
  the parent field of an object; ADR 0002 shapes are not re-specified).
- How the trusted owner identity is obtained and attested (Relay / binding work).
- Multi-parent composition (zero corpus occurrences).
