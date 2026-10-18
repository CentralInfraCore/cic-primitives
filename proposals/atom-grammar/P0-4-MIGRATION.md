# P0.4 — compatibility and migration (`access-policy/1`)

Companion to `P0-4-ACCESS-GRAMMAR.md` and D-018.

## What changes, and what does not

| Item | Before | After | Breaking? |
|---|---|---|---|
| `inherit` spelling `true`/`false`/`0` | accepted, type `boolean \| 0` | accepted as grammar 1, same meaning, type `InheritanceMode` | no |
| `inherit` enum `inherit`/`no-inherit`/`reset` | not a grammar value | grammar 2 only | no (new) |
| mixing the two spellings in one document | unspecified | error in either direction | new strictness |
| `inherit_policy: 0` | contradicted the declared `boolean` | valid (`reset`) | no (documented meaning wins) |
| `access`/`modify` type | `list<CertPattern>` with default `inherit` | `list<CertPattern> \| inherit` | no (the default was already the symbol) |
| `access: null`, `access: [inherit]` | unspecified | `INVALID_ACCESS_VALUE`, `INVALID_CERT_PATTERN` | new strictness, no known corpus use |
| `default_access: open`, `default_modify: owner` | untyped defaults in list-typed slots | union types; defaults are system-layer, never materialized | no |
| `surface_rules` default | the word `empty` | `[]` | no |
| unconfigured write | "every field accessible" in prose, `owner` in the slot | write needs a trusted owner; read stays open (authenticated) | **behavioral narrowing**, only for a runtime that does not exist yet |
| `no-inherit` vs `reset` | described without separation | separated (section 2 of the spec) | no corpus use of either exists |

## Version rule

A document declares `access-grammar: 1|2` (absent = 1). The migration 1 → 2 maps
`true→inherit`, `false→no-inherit`, `0→reset` for every `Access.inherit` and
`PolicySurface.inherit_policy`, and changes the declared version in the same step. The inverse
exists. The mapping is a bijection and is covered by `migration.*` vectors and by the gate
property that no resolve case changes its result across the two grammars. There is no
automatic upgrade: a grammar-1 reader does not accept enum names, a grammar-2 reader does not
accept legacy scalars, so a half-migrated document fails loudly.

## Downstream consequences

1. `cic-primitive-forms` pins an immutable seven-file grammar identity (ADR 0002). **This
   change does not propagate by itself.** Adopting it needs a new grammar pin and manifest, a
   corpus update (the `inherit` suite, `INVALID_ACCESS_VALUE` / `INVALID_CERT_PATTERN` /
   `INVALID_INHERIT` leave provisional status), and an ADR 0004 compatibility check. Until
   then the library keeps reading grammar 1.
2. `cic-primitive-engine` needs the same pin change; its Normalize stage can use the symbolic
   defaults of section 1 unchanged.
3. **`cic-schema-registry` has a real defect this work exposed** (matrix F2): nine current
   schemas (34 occurrences including versioned ones) write `modify: [OU=adapters, O=cic]`, which
   YAML parses as two patterns in OR. Any certificate with `O=cic` would match, not only
   adapters. The intended value is the single pattern `"OU=adapters,O=cic"`. That repository
   is outside this PR; it needs its own fix.
4. No `PolicySurface` runtime exists in `cic-relay` today; the resolution here is the contract
   for it, not a change to it.
