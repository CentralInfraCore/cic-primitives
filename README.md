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

## Kapcsolódó repók

| Repo | Kapcsolat |
|---|---|
| `base-repo` | upstream tooling (Makefile, CI, compiler) — `git merge base@0.5.0` |
| `CIC-Relay` | runtime — primitívekből épülő sémákat futtatja |
| domain repók | leszármazottak — `cic-primitives` a base-jük |
