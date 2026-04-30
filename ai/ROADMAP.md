# Roadmap

## Phase 1 — Bootstrap

| # | Feladat | Státusz | Blokkoló |
|---|---|---|---|
| 1.1 | git init + `git merge base@0.5.0` | pending | — |
| 1.2 | dependency.yaml (D-007) | pending | 1.1 |
| 1.3 | project.yaml (`repo_type: primitive`) | pending | 1.1 |
| 1.4 | schemas/ könyvtárstruktúra | pending | 1.1 |
| 1.5 | make validate zöld | pending | 1.1–1.4 |

## Phase 2 — Aggregate skeletons (D-002: aggregate-first)

Slot contract-ok sealed/defaulted/required módokkal. Atomic type referencia még TBD.

| # | Feladat | Státusz |
|---|---|---|
| 2.1 | ConfigSurface skeleton | pending |
| 2.2 | StateSurface skeleton | pending |
| 2.3 | OperationSurface skeleton | pending |
| 2.4 | **ManagedEntity skeleton** | pending |

## Phase 3 — Atomic layer

| # | Feladat | Státusz |
|---|---|---|
| 3.1 | Shape | pending |
| 3.2 | Role | pending |
| 3.3 | Behavior | pending |
| 3.4 | Contract | pending |
| 3.5 | Address | pending |
| 3.6 | Identity | pending |
| 3.7 | Event | pending |

## Phase 4 — Aggregate completion (atomic ref-ek bekötése)

| # | Feladat | Státusz | Blokkoló |
|---|---|---|---|
| 4.1 | ConfigSurface complete | pending | 2.1 + 3.1 + 3.4 |
| 4.2 | StateSurface complete | pending | 2.2 + 3.1 + 3.2 |
| 4.3 | OperationSurface complete | pending | 2.3 + 3.3 |
| 4.4 | NotificationSurface | pending | 3.7 |
| 4.5 | CapabilitySurface | pending | — |
| 4.6 | LifecycleSurface | pending | — |
| 4.7 | BindingSurface | pending | — |
| 4.8 | **ManagedEntity complete** | pending | 4.1–4.7 |

## Phase 5 — Első domain példa (reality check)

| # | Feladat | Státusz |
|---|---|---|
| 5.1 | Kubernetes Pod kompozíció | pending |
| 5.2 | VAGY Managed Switch Interface | pending |

## Phase 6 — Signed release

| # | Feladat | Státusz |
|---|---|---|
| 6.1 | make release VERSION=0.1.0 | pending |
| 6.2 | Artifact más repó dependencies/-be | pending |

---

## Nyitott döntések

| ID | Kérdés | Státusz |
|---|---|---|
| D-006 | repo_type: primitive | **LEZÁRVA** |

## Időbecslés (AI-val)

- Phase 1: ~2 óra
- Phase 2: fél nap (skeleton-ok gyorsak)
- Phase 3: 1–2 nap
- Phase 4: 1–2 nap
- Phase 5: fél nap (reality check)
- Phase 6: fél nap
