# Ütemterv / Roadmap

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
| 6.1 | `schemas/index.yaml` → primitive meta-schema | ✓ done | — |
| 6.2 | `compiler.py` primitive YAML validáció | ✓ done | 6.1 |
| 6.3 | domain specializáció semantic compatibility check | ✓ done | 6.2 |

## Phase 8 — Content-level permission system

Kiváltó: cic-compute tervezésekor ugyanaz a ComputeResource objektum különböző
láthatósággal és írhatósággal jelenik meg user / service / adapter szemszögéből.
Ez field-szintű jogosultság — nem schema különbség, hanem access context.

| # | Feladat | Státusz | Blokkoló |
|---|---|---|---|
| 8.1 | Primitive szintű design döntés (atomic vs aggregate, deklaratív vs runtime) | ✓ done — D-012 | — |
| 8.2 | Access atom implementáció (8. atom) | ✓ done — `schemas/atomic/access.yaml` | 8.1 |
| 8.3 | PolicySurface aggregate | concept | Relay execution modell |

## Phase 7 — Signed release

| # | Feladat | Státusz |
|---|---|---|
| 7.1 | PrimitiveRelease bundle model | ✓ done — `compiler.py release` → `release/<name>-vX.Y.Z.yaml` |
| 7.2 | `verify-release` parancs | ✓ done — content_hash + meta_hash ellenőrzés |
| 7.3 | Vault signature verification | concept — Vault public key / cert-alapú ECDSA ellenőrzés |
| 7.4 | Artifact más repó `dependencies/`-be | concept |

---

## Nyitott döntések

| ID | Kérdés | Státusz |
|---|---|---|
| D-006 | repo_type: primitive | **LEZÁRVA** — `x-cic.repo_type: primitive` |
| D-013 | build_hash vs source_hash | **LEZÁRVA** — nincs build_hash, csak content_hash |

## Megjegyzés

- Phase 1–6: **defined** (YAML fájlok léteznek, make validate zöld)
- Phase 4.4–4.7 (NotificationSurface, CapabilitySurface, LifecycleSurface, BindingSurface): ManagedEntity-ben defaulted/sealed slot-ként dokumentálva, önálló aggregate séma még nincs
- Phase 7: bundle modell kész, Vault signature verification következő lépés

---
---

# Roadmap — English

## Phase 1 — Bootstrap

| # | Task | Status | Blocker |
|---|---|---|---|
| 1.1 | git init + `git merge base@0.5.0` | ✓ done | — |
| 1.2 | dependency.yaml (D-007) | ✓ done | 1.1 |
| 1.3 | project.yaml (`repo_type: primitive`) | ✓ done | 1.1 |
| 1.4 | schemas/ directory structure | ✓ done | 1.1 |
| 1.5 | make validate green | ✓ done | 1.1–1.4 |

## Phase 2 — Aggregate skeletons (D-002: aggregate-first)

Slot contracts with sealed/defaulted/required modes. Atomic type references still TBD.

| # | Task | Status |
|---|---|---|
| 2.1 | ConfigSurface skeleton | ✓ done |
| 2.2 | StateSurface skeleton | ✓ done |
| 2.3 | OperationSurface skeleton | ✓ done |
| 2.4 | **ManagedEntity skeleton** | ✓ done |

## Phase 3 — Atomic layer

| # | Task | Status |
|---|---|---|
| 3.1 | Shape | ✓ done |
| 3.2 | Role | ✓ done |
| 3.3 | Behavior | ✓ done |
| 3.4 | Contract | ✓ done |
| 3.5 | Address | ✓ done |
| 3.6 | Identity | ✓ done |
| 3.7 | Event | ✓ done |

## Phase 4 — Aggregate completion (wiring in atomic refs)

| # | Task | Status | Blocker |
|---|---|---|---|
| 4.1 | ConfigSurface complete | ✓ done | 2.1 + 3.1 + 3.4 |
| 4.2 | StateSurface complete | ✓ done | 2.2 + 3.1 + 3.2 |
| 4.3 | OperationSurface complete | ✓ done | 2.3 + 3.3 |
| 4.4 | NotificationSurface | concept | 3.7 |
| 4.5 | CapabilitySurface | concept | — |
| 4.6 | LifecycleSurface | concept | — |
| 4.7 | BindingSurface | concept | — |
| 4.8 | **ManagedEntity complete** | ✓ done | 4.1–4.7 |

## Phase 5 — First domain example (reality check)

| # | Task | Status |
|---|---|---|
| 5.1 | Kubernetes Pod composition | ✓ done |
| 5.2 | OR Managed Switch Interface | concept |

## Phase 6 — Primitive YAML validation (compiler integration)

D-008: compiler.py responsibility, not the primitive model.
Breaking point: the first domain repo specialization.

| # | Task | Status | Blocker |
|---|---|---|---|
| 6.1 | `schemas/index.yaml` → primitive meta-schema | ✓ done | — |
| 6.2 | `compiler.py` primitive YAML validation | ✓ done | 6.1 |
| 6.3 | domain specialization semantic compatibility check | ✓ done | 6.2 |

## Phase 8 — Content-level permission system

Trigger: when designing cic-compute, the same ComputeResource object appeared with
different visibility and writability from user / service / adapter perspectives.
This is field-level access control — not a schema difference, but an access context.

| # | Task | Status | Blocker |
|---|---|---|---|
| 8.1 | Primitive-level design decision (atomic vs aggregate, declarative vs runtime) | ✓ done — D-012 | — |
| 8.2 | Access atom implementation (8th atom) | ✓ done — `schemas/atomic/access.yaml` | 8.1 |
| 8.3 | PolicySurface aggregate | concept | Relay execution model |

## Phase 7 — Signed release

| # | Task | Status |
|---|---|---|
| 7.1 | PrimitiveRelease bundle model | ✓ done — `compiler.py release` → `release/<name>-vX.Y.Z.yaml` |
| 7.2 | `verify-release` command | ✓ done — content_hash + meta_hash verification |
| 7.3 | Vault signature verification | concept — Vault public key / cert-based ECDSA verification |
| 7.4 | Artifact into another repo's `dependencies/` | concept |

---

## Open decisions

| ID | Question | Status |
|---|---|---|
| D-006 | repo_type: primitive | **CLOSED** — `x-cic.repo_type: primitive` |
| D-013 | build_hash vs source_hash | **CLOSED** — no build_hash, only content_hash |

## Notes

- Phase 1–6: **defined** (YAML files exist, make validate green)
- Phase 4.4–4.7 (NotificationSurface, CapabilitySurface, LifecycleSurface, BindingSurface): documented as defaulted/sealed slots in ManagedEntity, standalone aggregate schema not yet created
- Phase 7: bundle model done, Vault signature verification is the next step
