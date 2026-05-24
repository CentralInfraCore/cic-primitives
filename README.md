# cic-primitives

> Ez nem klasszikus repo. Ez AI-operált primitive schema layer.
> Emberi belépő: ez a README. AI belépő: `ai/ONBOARDING.md`.

A CIC **meta-séma rétege** — az a szint, amelyből minden domain objektum
(switch interface, kubernetes pod, service, database, policy) schema-szinten levezethető.

Nem domain modell. Nem IaC tool. Nem YANG leíró.

---

## Két szint

| Szint | Mit képvisel | Hol van |
|---|---|---|
| **atomic primitive** | 8 irreducibilis atom — Shape, Role, Behavior, Contract, Address, Identity, Event, Access | `schemas/atomic/` |
| **aggregate primitive** | Kompozíció sealed/defaulted/required slot-okkal | `schemas/aggregate/` |

A domain objektum mindig következmény, soha nem kiindulópont.

---

## Gyors start

```bash
make validate    # séma validáció — ha ez nem zöld, semmi sem kész
make release     # signed artifact (Vault szükséges)
```

---

## AI belépési pontok

| Fájl | Mire való |
|---|---|
| `ai/ONBOARDING.md` | Boot protokoll — minden session elején |
| `ai/MAINTENANCE_CONTRACT.md` | Mit szabad, mit nem, mikor kell döntés |
| `ai/SYSTEM_CONTEXT.md` | Teljes architekturális kontextus |
| `ai/PROMPTMAP.yaml` | Task queue — mi a következő konkrét lépés |
| `ai/DECISIONS.md` | Döntési history — miért úgy van ahogy van |

---

## Aktuális állapot

| Réteg | Státusz | Megjegyzés |
|---|---|---|
| 8 atomic primitive YAML | **defined** | Shape · Role · Behavior · Contract · Address · Identity · Event · Access |
| 5 aggregate primitive YAML | **defined** | ManagedEntity, ConfigSurface, StateSurface, OperationSurface, PolicySurface |
| Primitive meta-schema validáció | **defined** | `schemas/index.yaml` + `compiler.py` — `make validate` zöld |
| sealed/required slot enforcement | **defined** | domain specializáció kompatibilitás ellenőrzött |
| KubernetesPod domain példa | **defined** | `schemas/examples/kubernetes-pod.yaml` |
| PrimitiveRelease bundle | **defined** | `release/<name>-vX.Y.Z.yaml` — inline specs[], content_hash, Vault sign |
| verify-release | **defined** | `make verify-release FILE=...` — schema + content_hash + meta_hash ellenőrzés |
| Vault signature verification | **concept** | ECDSA ellenőrzés Vault pubkey-jel — következő fázis |
| defaulted slot merge szemantika | **draft** | replace/deep_merge/append/union — D-008, első domain override-nál dől el |
| LifecycleSurface / CapabilitySurface / NotificationSurface | **concept** | Relay execution modell előfeltétel |
| ExecutionSurface aggregate | **concept** | D-009, Relay modell előfeltétel |
| Schema/API/runtime kódgenerálás | **not implemented** | a `semantic_mapping` mezők irányt adnak, de generator nincs |
| Teljes szemantikai típusellenőrzés | **not implemented** | a jelenlegi validator formai, nem szemantikai |
| Production trust-chain | **not implemented** | CIC-Relay + CIC-Schemas feladata |

---

## Kapcsolódó repók

| Repo | Kapcsolat |
|---|---|
| `base-repo` | upstream tooling (Makefile, CI, compiler) — `git merge base@0.5.0` |
| `CIC-Relay` | runtime — primitívekből épülő sémákat futtatja |
| domain repók | leszármazottak — `cic-primitives` a base-jük |

---
---

# cic-primitives (English)

> This is not a classic repo. It is an AI-operated primitive schema layer.
> Human entry point: this README. AI entry point: `ai/ONBOARDING.md`.

The CIC **meta-schema layer** — the level from which every domain object
(switch interface, kubernetes pod, service, database, policy) can be derived at the schema level.

Not a domain model. Not an IaC tool. Not a YANG descriptor.

---

## Two levels

| Level | What it represents | Location |
|---|---|---|
| **atomic primitive** | 8 irreducible atoms — Shape, Role, Behavior, Contract, Address, Identity, Event, Access | `schemas/atomic/` |
| **aggregate primitive** | Composition with sealed/defaulted/required slots | `schemas/aggregate/` |

The domain object is always a consequence, never a starting point.

---

## Quick start

```bash
make validate    # schema validation — if this is not green, nothing is done
make release     # signed artifact (Vault required)
```

---

## AI entry points

| File | Purpose |
|---|---|
| `ai/ONBOARDING.md` | Boot protocol — run at the start of every session |
| `ai/MAINTENANCE_CONTRACT.md` | What is allowed, what is not, when a decision is needed |
| `ai/SYSTEM_CONTEXT.md` | Full architectural context |
| `ai/PROMPTMAP.yaml` | Task queue — the next concrete step |
| `ai/DECISIONS.md` | Decision history — why things are the way they are |

---

## Current state

| Layer | Status | Notes |
|---|---|---|
| 8 atomic primitive YAMLs | **defined** | Shape · Role · Behavior · Contract · Address · Identity · Event · Access |
| 5 aggregate primitive YAMLs | **defined** | ManagedEntity, ConfigSurface, StateSurface, OperationSurface, PolicySurface |
| Primitive meta-schema validation | **defined** | `schemas/index.yaml` + `compiler.py` — `make validate` green |
| sealed/required slot enforcement | **defined** | domain specialization compatibility verified |
| KubernetesPod domain example | **defined** | `schemas/examples/kubernetes-pod.yaml` |
| PrimitiveRelease bundle | **defined** | `release/<name>-vX.Y.Z.yaml` — inline specs[], content_hash, Vault sign |
| verify-release | **defined** | `make verify-release FILE=...` — schema + content_hash + meta_hash check |
| Vault signature verification | **concept** | ECDSA verification with Vault pubkey — next phase |
| defaulted slot merge semantics | **draft** | replace/deep_merge/append/union — D-008, decided at first domain override |
| LifecycleSurface / CapabilitySurface / NotificationSurface | **concept** | Relay execution model prerequisite |
| ExecutionSurface aggregate | **concept** | D-009, Relay model prerequisite |
| Schema/API/runtime code generation | **not implemented** | `semantic_mapping` fields give direction, but no generator yet |
| Full semantic type checking | **not implemented** | current validator is structural, not semantic |
| Production trust-chain | **not implemented** | responsibility of CIC-Relay + CIC-Schemas |

---

## Related repos

| Repo | Relationship |
|---|---|
| `base-repo` | upstream tooling (Makefile, CI, compiler) — `git merge base@0.5.0` |
| `CIC-Relay` | runtime — executes schemas built from primitives |
| domain repos | derived repos — `cic-primitives` is their base |
