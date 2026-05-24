# Onboarding (AI)

## 1 perc alatt

- **Mi ez:** CIC Primitives — a meta-séma réteg. Nem domain modell, nem IaC tool.
- **Két szint:** atomic (8 atom) + aggregate (szemantikai kompozíció)
- **Kompozíció:** git remote merge — nem YAML override rules
- **Státusz:** minden concept/draft, git bootstrap előtt
- **Mérce:** `make validate` — ha nem zöld, semmi sem kész

## Mielőtt bármit írsz

1. `mcp__cic-graph__kb_status` — KB elérhető?
2. Olvasd: `ai/SYSTEM_CONTEXT.md`
3. Nézd: `ai/PROMPTMAP.yaml` — mi a következő konkrét lépés

## A 8 atom (nem bontható tovább)

| Atom | Kérdés amire válaszol |
|---|---|
| Shape | Milyen mezők, milyen típusok? |
| Role | Config? State? Kulcs? Referencia? |
| Behavior | Milyen műveletek hajthatók végre? |
| Contract | Milyen feltételeknek kell teljesülnie? |
| Address | Hogyan érhető el? |
| Identity | Mi az (típus szinten)? |
| Event | Milyen async jelzést bocsát ki? |
| Access | Ki olvashatja, ki írhatja — cert-alapú identity? |

## Aggregate = kompozíció, nem örökség

```yaml
# Nem ez:
kind: Pod
extends: ManagedEntity

# Hanem ez:
kind: ManagedEntity
composes:
  - Identity
  - ConfigSurface
  - StateSurface
  - OperationSurface
slots:
  identity.naming: required
  config.nodes: required
  state.nodes: required
  lifecycle.core: sealed
```

## Ha gond van

Javasolj design-diffet (`ai/DECISIONS.md`-hez), ne térj el csendben.

---
---

# Onboarding (AI) — English

## In 1 minute

- **What this is:** CIC Primitives — the meta-schema layer. Not a domain model, not an IaC tool.
- **Two levels:** atomic (8 atoms) + aggregate (semantic composition)
- **Composition:** git remote merge — not YAML override rules
- **Status:** everything concept/draft before git bootstrap
- **Measure:** `make validate` — if not green, nothing is done

## Before you write anything

1. `mcp__cic-graph__kb_status` — is the KB available?
2. Read: `ai/SYSTEM_CONTEXT.md`
3. Check: `ai/PROMPTMAP.yaml` — what is the next concrete step

## The 8 atoms (cannot be decomposed further)

| Atom | Question it answers |
|---|---|
| Shape | What fields, what types? |
| Role | Config? State? Key? Reference? |
| Behavior | What operations can be executed? |
| Contract | What conditions must be satisfied? |
| Address | How is it reachable? |
| Identity | What is it (at the type level)? |
| Event | What async notifications does it emit? |
| Access | Who can read it, who can write it — cert-based identity? |

## Aggregate = composition, not inheritance

```yaml
# Not this:
kind: Pod
extends: ManagedEntity

# But this:
kind: ManagedEntity
composes:
  - Identity
  - ConfigSurface
  - StateSurface
  - OperationSurface
slots:
  identity.naming: required
  config.nodes: required
  state.nodes: required
  lifecycle.core: sealed
```

## If something is wrong

Propose a design-diff (to `ai/DECISIONS.md`), do not deviate silently.
