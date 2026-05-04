# Roadmap

## Phase 1 — Bootstrap

| # | Feladat | Státusz | Blokkoló |
|---|---|---|---|
| 1.1 | git init + `git merge base@0.5.0` | ✓ done | — |
| 1.2 | dependency.yaml (D-007) | ✓ done | 1.1 |
| 1.3 | project.yaml (`repo_type: primitive`) | ✓ done | 1.1 |
| 1.4 | schemas/ könyvtárstruktúra | ✓ done | 1.1 |
| 1.5 | make validate zöld | ✓ done | 1.1–1.4 |

## Phase 2 — Aggregate skeletons (D-002: aggregate-first)

Slot contract-ok sealed/defaulted/required módokkal. Atomic type referencia még TBD.

| # | Feladat | Státusz |
|---|---|---|
| 2.1 | ConfigSurface skeleton | ✓ done |
| 2.2 | StateSurface skeleton | ✓ done |
| 2.3 | OperationSurface skeleton | ✓ done |
| 2.4 | **ManagedEntity skeleton** | ✓ done |

## Phase 3 — Atomic layer

| # | Feladat | Státusz |
|---|---|---|
| 3.1 | Shape | ✓ done |
| 3.2 | Role | ✓ done |
| 3.3 | Behavior | ✓ done |
| 3.4 | Contract | ✓ done |
| 3.5 | Address | ✓ done |
| 3.6 | Identity | ✓ done |
| 3.7 | Event | ✓ done |

## Phase 4 — Aggregate completion (atomic ref-ek bekötése)

| # | Feladat | Státusz | Blokkoló |
|---|---|---|---|
| 4.1 | ConfigSurface complete | ✓ done | 2.1 + 3.1 + 3.4 |
| 4.2 | StateSurface complete | ✓ done | 2.2 + 3.1 + 3.2 |
| 4.3 | OperationSurface complete | ✓ done | 2.3 + 3.3 |
| 4.4 | NotificationSurface | concept | 3.7 |
| 4.5 | CapabilitySurface | concept | — |
| 4.6 | LifecycleSurface | concept | — |
| 4.7 | BindingSurface | concept | — |
| 4.8 | **ManagedEntity complete** | ✓ done | 4.1–4.7 |

## Phase 5 — Első domain példa (reality check)

| # | Feladat | Státusz |
|---|---|---|
| 5.1 | Kubernetes Pod kompozíció | ✓ done |
| 5.2 | VAGY Managed Switch Interface | concept |

## Phase 6 — Primitive YAML validáció (compiler bekötés)

D-008: compiler.py responsibility, nem primitive modell.
Töréspont: az első domain repo specializációja.

| # | Feladat | Státusz | Blokkoló |
|---|---|---|---|
| 6.1 | `schemas/index.yaml` → primitive meta-schema | concept | — |
| 6.2 | `compiler.py` primitive YAML validáció | concept | 6.1 |
| 6.3 | domain specializáció semantic compatibility check | concept | 6.2 |

## Phase 8 — Content-level permission system

Kiváltó: cic-compute tervezésekor ugyanaz a ComputeResource objektum különböző
láthatósággal és írhatósággal jelenik meg user / service / adapter szemszögéből.
Ez field-szintű jogosultság — nem schema különbség, hanem access context.

| # | Feladat | Státusz | Blokkoló |
|---|---|---|---|
| 8.1 | Primitive szintű design döntés (atomic vs aggregate, deklaratív vs runtime) | pending | 6.2 |
| 8.2 | PolicySurface / Access atomic implementáció | pending | 8.1 |

**Nyitott kérdések:**
- 8. atom-e (`Policy`/`Access`) vagy új aggregate (`PolicySurface`)?
- Owner fogalma: user \| service \| adapter — hogyan változhat lifecycle során?
- Viszony a `Role` atomhoz (config/state/operational)

## Phase 7 — Signed release

| # | Feladat | Státusz |
|---|---|---|
| 7.1 | make release VERSION=0.1.0 | concept — Vault setup szükséges |
| 7.2 | Artifact más repó dependencies/-be | concept |

---

## Nyitott döntések

| ID | Kérdés | Státusz |
|---|---|---|
| D-006 | repo_type: primitive | **LEZÁRVA** — `x-cic.repo_type: primitive` |

## Megjegyzés

- Phase 1–5: **defined** (YAML fájlok léteznek, make validate zöld)
- Phase 4.4–4.7 (NotificationSurface, CapabilitySurface, LifecycleSurface, BindingSurface): ManagedEntity-ben defaulted/sealed slot-ként dokumentálva, önálló aggregate séma még nincs
- Phase 6: Vault + signing pipeline szükséges
