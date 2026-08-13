# Release 0.2.0 — what changes, and what breaks

`0.1.5 → 0.2.0`, a **minor** bump, because this release changes the language in
ways a `0.1.6` would have hidden. Composition files written against `0.1.5` are
not all valid under `0.2.0`.

## Breaking: the language

### Role is three axes, not a flat list

The seven values were never one dimension. They are now stated as they always
were, and the difference is enforceable rather than descriptive:

```yaml
authority  ∈ { config, state, operational }   exactly one, from the surface if omitted
structural ⊆ { key, reference }               zero or more
lifecycle  ∈ { derived, volatile }            zero or one
```

Short forms are unchanged and still valid (`role: config`, `role: key`,
`role: state`, `role: derived`, `role: volatile`). **`role: reference` is no
longer a valid short form** — a reference's authority cannot be derived, so it
requires the long form.

What this buys: a node that is observed, points at another entity, and is not
persisted can finally be written. Flat, it had to be called `state` and the
other two properties were lost.

### `reference` is an annotation, not a Shape type

`shape_type: reference` is retired. Every composition already wrote it the new
way; the catalogue was the thing that was wrong.

```yaml
shape_type: scalar
scalar_type: string
semantic_type: cic-reference
reference_target: "cic:network:NetworkInterface"     # {namespace}:{Kind}
```

`shape.yaml` documented the target as `cic:{namespace}:{Kind}`, which expands to
`cic:cic:network:X` because the namespace already carries the prefix. The
documented format was wrong; the corpus was right.

### `type` on a field descriptor is `shape_type`

The catalogue called it `type`. No composition has ever written that.

### Defaults are no longer uniform

The schema may not supply a default for a value it does not own:

| Role | defaultable? |
|---|---|
| `authority: config` | yes |
| `authority: state` / `operational` | **no** |
| `lifecycle: derived` / `volatile` | **no** |
| `structural: key` | **no** |

`missing`, `unknown`, `not_observed`, `not_implemented` and a defaulted value
are five different statements. An adapter that could not read `power_state`
does not produce `power_state: running` because that is the schema default.

### A node may not contradict its surface

`config_surface` admits `authority: config`; `state_surface` admits `state` or
`operational`. Nested `fields` and `item_fields` inherit the parent's surface,
and a node that omits `role` takes the surface's authority — omitting a member
is not a way out of a rule.

### Presence is one axis

`mandatory` and `optional` may not both appear, and neither may be written as
`false`. `mandatory` with a `default` is invalid.

### Lists state their key

Every list has a key. A single `role: key` item field is enough; two or more
require an explicit `item_key` so the composite key's order is defined.

## Breaking: the release artifact

**Envelope v2.** `build_hash` now covers the whole bundle except
`release.sign`, `release.build_hash` and `cic_countersign`. Under v1 it covered
four members, leaving `kind`, `version` and `timestamp` unsigned — a bundle
relabelled `0.1.5 → 9.9.9` with a 2099 timestamp verified clean.

v1 artifacts keep verifying; `release.envelope` says which applies, and its
absence means 1. Recorded as **D-015**, which amends D-013.

The bundle gains a `provenance` block — source commit, dependency lock digest,
grammar digest — signed automatically under v2.

## Verification: what it now proves, and what it refuses to claim

- the counter-signature is **verified**, and the authority certificate is
  checked against the root the bundle carries. Before, the schema described the
  block and the verifier ignored it: a countersign replaced with garbage still
  reported success.
- the developer pledge's hash is **recomputed** and its signature **verified**.
  Before, only `kind` and the date window were checked, so a hand-written
  commitment with invented fields passed.
- `verify-release` no longer prints "integrity OK" after admitting it could not
  check the chain. It lists what is proven and what is not, and says
  *"Internally consistent — signed by the certificate this artifact carries.
  That is not the same as trusted."*
- `--trust-root <pem>` pins the root out of band. Without it, every certificate
  in the artifact is self-asserted, and the output says so.

## Migration

Compositions written for 0.1.5 need, at most:

1. `role: reference` → the long form with an explicit authority;
2. `shape_type: reference` → `scalar` + `semantic_type` + `reference_target`;
3. any `default` on an observed, derived, volatile or key node removed;
4. any node whose authority contradicts its surface moved or relabelled;
5. `mandatory: false` / `optional: false` → omit the member;
6. lists with two or more key fields → add `item_key`.

Measured on the live corpus before release: `kubernetes-pod.yaml`,
`network-interface.yaml` and `compute-resource.yaml` need **none** of these.
The rules were written from the corpus, not against it.

## Gates this release runs through

`make release` refuses to build if the grammar rejects a composition it would
ship, and runs the grammar's own self-test first — a checker that can no longer
fail proves nothing about what it approves.

```
self-test        40/40 fixtures, 19 of them deliberately broken
tests            153
coverage         89%, ratchet at 88
mutation         990 mutants on compiler.py; the trust-critical survivors killed
```
