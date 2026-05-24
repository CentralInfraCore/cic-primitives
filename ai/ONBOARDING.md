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
