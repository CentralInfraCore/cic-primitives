# Rendszer Kontextus / System Context

Olvasd el mielőtt bármit módosítasz. / Read before modifying anything.

---

## Mi ez a rendszer?

A `cic-primitives` a CentralInfraCore **meta-séma rétege**.

Nem domain modell, nem IaC tool, nem YANG leíró — hanem az a szint,
amelyből minden domain objektum schema-szinten levezethető.

A primitívek két szinten léteznek:

**Atomic primitive** — irreducibilis szemantikai atom. Nem bontható tovább
anélkül, hogy menedzsment-szemantikát veszítene.

| Atom | Mit képvisel |
|---|---|
| Shape | Adat struktúrája — milyen mezők, milyen típusok |
| Role | Mit jelent menedzsment szempontból (config? state? kulcs? referencia?) |
| Behavior | Milyen műveletek hajthatók végre |
| Contract | Milyen feltételeknek kell teljesülnie (kényszer, validáció) |
| Address | Hogyan érhetjük el, hol lakik a rendszerben |
| Identity | Mi az (típusazonosság, nem példányazonosság) |
| Event | Milyen aszinkron jelzéseket képes kibocsátani |

**Aggregate primitive** — szemantikai kompozíció sealed/defaulted/required slot-okkal.
Nem csak atomok listája — kompozíciós objektum contracttal, override pontokkal.

```
ManagedEntity =
  Identity + ConfigSurface + StateSurface +
  OperationSurface + NotificationSurface +
  CapabilitySurface + LifecycleSurface + BindingSurface
```

---

## A kompozíciós mechanizmus

**Git remote = öröklődési lánc.** Ez nem metafora — ez a tényleges megvalósítás.

```
base-repo
  └─[remote: base]─► cic-primitives
                          └─[remote: base]─► domain repók
```

A fájlstruktúra IS az interface contract. Ha a leszármazott repo eltér a
sablon struktúrájától, a `git merge base@0.5.0` konfliktusba megy.
Ez a kényszerítő mechanizmus — nem kell külön validátor.

Választott mechanizmus (döntés: 2026-04-30):
- ✅ Git remote + merge
- ❌ YAML override-rules.yaml (felesleges absztrakciós réteg)

---

## A séma infrastruktúra (örökölt base-repo-ból)

A `base-repo` merge után elérhetők:

```
tools/compiler.py     CLI: validate | release | verify-release <artifact>
tools/release.sh      DEPRECATED — fatálisan kilép, ne használd
mk/infra.mk           Makefile include
```

Release pipeline:
1. `compiler.py release` → per-schema `meta_hash` (raw bytes SHA256)
2. `specs[]` canonical JSON → `content_hash` (SHA256 base64)
3. Vault Transit: ECDSA SHA256 aláírás (`prehashed=true`)
4. X.509 cert (Vault KV v2, `VAULT_CERT_PATH` vagy `VAULT_CERT` env)
5. `release/<project-name>-vX.Y.Z.yaml` kiírva (PrimitiveRelease bundle)

---

## Tervezett könyvtárstruktúra (concept)

```
schemas/
  atomic/
    shape.yaml
    role.yaml
    behavior.yaml
    contract.yaml
    address.yaml
    identity.yaml
    event.yaml
  aggregate/
    managed-entity.yaml
    config-surface.yaml
    state-surface.yaml
    operation-surface.yaml
    notification-surface.yaml
    capability-surface.yaml
    lifecycle-surface.yaml
    binding-surface.yaml
  index.yaml              ← meta-meta-séma (mint CIC-Schemas)
dependencies/             ← signed upstream sémák (template-schema)
source/                   ← ha generált tartalom kell
```

---

## Séma artifact struktúra (template-schema mintára)

Minden primitive YAML fájl:

```yaml
metadata:
  name: <primitive-name>
  version: v0.1.dev
  description: ...
  owner: Gabor Zoltan Sinko
  tags: [primitive, atomic|aggregate]
  validatedBy:
    name: template-schema
    version: v0.9.5_2025

spec:
  # JSON Schema a primitive struktúrájára
  type: object
  required: [...]
  properties:
    ...
```

---

## Kapcsolat más CIC repókkal

| Repo | Kapcsolat | Irány |
|---|---|---|
| `base-repo` | git remote `base` | upstream → cic-primitives |
| `CIC-Schemas` | referencia minta | signing lánc minta |
| `CIC-Relay` | consumer | primitívekből épülő sémák futtatása |
| domain repók (tervezett) | git remote `base` | cic-primitives → domain |

---

## Jelenlegi állapot (2026-05-01)

Phase 1–7 végrehajtva. A repo első signed release-szel lezárt.

| Elem | Státusz |
|---|---|
| git init + `git merge base@0.5.0` | **defined** |
| `dependency.yaml` (D-007) | **defined** |
| `project.yaml` | **defined** |
| `schemas/` struktúra | **defined** |
| aggregate skeletonök (4 db) | **defined** |
| atomic layer (8 atom) | **defined** |
| aggregate completion (atomic ref-ek) | **defined** |
| domain példa (`schemas/examples/kubernetes-pod.yaml`) | **defined** |
| `make validate` zöld | **defined** |
| primitive YAML validáció (`schemas/index.yaml` + compiler.py) | **defined** — Phase 6.1+6.2 |
| domain specializáció semantic check | **defined** — Phase 6.3, sealed/required enforcement |
| AI governance (README, MAINTENANCE_CONTRACT, invalid examples) | **defined** |
| első signed release (`primitives/@v0.1.0`) | **defined** — Phase 7 |
| ExecutionSurface aggregate | **concept** — D-009, Relay modell után |
| PrimitiveRelease bundle (`compiler.py release`) | **defined** — `release/<name>-vX.Y.Z.yaml` |
| `verify-release` parancs | **defined** — content_hash + meta_hash ellenőrzés |
| Vault signature verification (`verify-release`) | **concept** — ECDSA ellenőrzés Vault pubkey-jel |
| build_hash tényleges build env-vel | **n/a** — D-013 lezárva, content_hash váltja fel |
| `make release` yq PATH fix | **defined** — yq telepítve a Dockerfile-ban |

---

## Release folyamat (PrimitiveRelease bundle modell)

```bash
# 1. Release ágra váltás
git checkout -b primitives/releases/vX.Y.Z

# 2. Vault env
export VAULT_ADDR="https://127.0.0.1:18200"
export VAULT_TOKEN=$(cat $XDG_RUNTIME_DIR/vault/sign-token)
export VAULT_CACERT=/path/to/ca.pem          # vagy VAULT_SKIP_VERIFY=1 dev módban
export VAULT_CERT_PATH="secret/cic-cert/pem" # KV v2 mount/secret/key formátum

# 3. Release bundle generálás
make release
# → validál → specs[] összeáll → content_hash → Vault sign → release/cic-primitives-vX.Y.Z.yaml

# 4. Commit + tag
git add release/cic-primitives-vX.Y.Z.yaml
git commit -m "release: X.Y.Z"
git tag -a "primitives/@vX.Y.Z" -m "release: X.Y.Z"

# 5. Ellenőrzés
python tools/compiler.py verify-release release/cic-primitives-vX.Y.Z.yaml
```

Dockerfile követelmény: `git`, `curl`, `jq`, `yq` + `safe.directory /app`.

---
---

# System Context — English

Read before modifying anything.

---

## What is this system?

`cic-primitives` is the CentralInfraCore **meta-schema layer**.

Not a domain model, not an IaC tool, not a YANG descriptor — it is the level
from which every domain object can be derived at the schema level.

Primitives exist at two levels:

**Atomic primitive** — an irreducible semantic atom. Cannot be decomposed further
without losing management semantics.

| Atom | What it represents |
|---|---|
| Shape | Data structure — what fields, what types |
| Role | What it means from a management perspective (config? state? key? reference?) |
| Behavior | What operations can be executed |
| Contract | What conditions must be satisfied (constraints, validation) |
| Address | How to reach it, where it lives in the system |
| Identity | What it is (type identity, not instance identity) |
| Event | What asynchronous notifications it can emit |

**Aggregate primitive** — semantic composition with sealed/defaulted/required slots.
Not just a list of atoms — a compositional object with a contract and override points.

```
ManagedEntity =
  Identity + ConfigSurface + StateSurface +
  OperationSurface + NotificationSurface +
  CapabilitySurface + LifecycleSurface + BindingSurface
```

---

## The composition mechanism

**Git remote = inheritance chain.** This is not a metaphor — it is the actual implementation.

```
base-repo
  └─[remote: base]─► cic-primitives
                          └─[remote: base]─► domain repos
```

The file structure IS the interface contract. If a derived repo deviates from the
template structure, `git merge base@0.5.0` results in a conflict.
This is the enforcement mechanism — no separate validator needed.

Chosen mechanism (decision: 2026-04-30):
- ✅ Git remote + merge
- ❌ YAML override-rules.yaml (unnecessary abstraction layer)

---

## The schema infrastructure (inherited from base-repo)

After the `base-repo` merge, these are available:

```
tools/compiler.py     CLI: validate | release | verify-release <artifact>
tools/release.sh      DEPRECATED — exits fatally, do not use
mk/infra.mk           Makefile include
```

Release pipeline:
1. `compiler.py release` → per-schema `meta_hash` (raw bytes SHA256)
2. `specs[]` canonical JSON → `content_hash` (SHA256 base64)
3. Vault Transit: ECDSA SHA256 signature (`prehashed=true`)
4. X.509 cert (Vault KV v2, `VAULT_CERT_PATH` or `VAULT_CERT` env)
5. Write `release/<project-name>-vX.Y.Z.yaml` (PrimitiveRelease bundle)

---

## Planned directory structure (concept)

```
schemas/
  atomic/
    shape.yaml
    role.yaml
    behavior.yaml
    contract.yaml
    address.yaml
    identity.yaml
    event.yaml
  aggregate/
    managed-entity.yaml
    config-surface.yaml
    state-surface.yaml
    operation-surface.yaml
    notification-surface.yaml
    capability-surface.yaml
    lifecycle-surface.yaml
    binding-surface.yaml
  index.yaml              ← meta-meta-schema (like CIC-Schemas)
dependencies/             ← signed upstream schemas (template-schema)
source/                   ← if generated content is needed
```

---

## Schema artifact structure (template-schema pattern)

Every primitive YAML file:

```yaml
metadata:
  name: <primitive-name>
  version: v0.1.dev
  description: ...
  owner: Gabor Zoltan Sinko
  tags: [primitive, atomic|aggregate]
  validatedBy:
    name: template-schema
    version: v0.9.5_2025

spec:
  # JSON Schema for the primitive structure
  type: object
  required: [...]
  properties:
    ...
```

---

## Relationship with other CIC repos

| Repo | Relationship | Direction |
|---|---|---|
| `base-repo` | git remote `base` | upstream → cic-primitives |
| `CIC-Schemas` | reference pattern | signing chain pattern |
| `CIC-Relay` | consumer | runs schemas built from primitives |
| domain repos (planned) | git remote `base` | cic-primitives → domain |

---

## Current state (2026-05-01)

Phases 1–7 executed. The repo is closed with its first signed release.

| Item | Status |
|---|---|
| git init + `git merge base@0.5.0` | **defined** |
| `dependency.yaml` (D-007) | **defined** |
| `project.yaml` | **defined** |
| `schemas/` structure | **defined** |
| aggregate skeletons (4 pcs) | **defined** |
| atomic layer (8 atoms) | **defined** |
| aggregate completion (atomic refs wired) | **defined** |
| domain example (`schemas/examples/kubernetes-pod.yaml`) | **defined** |
| `make validate` green | **defined** |
| primitive YAML validation (`schemas/index.yaml` + compiler.py) | **defined** — Phase 6.1+6.2 |
| domain specialization semantic check | **defined** — Phase 6.3, sealed/required enforcement |
| AI governance (README, MAINTENANCE_CONTRACT, invalid examples) | **defined** |
| first signed release (`primitives/@v0.1.0`) | **defined** — Phase 7 |
| ExecutionSurface aggregate | **concept** — D-009, after Relay model |
| PrimitiveRelease bundle (`compiler.py release`) | **defined** — `release/<name>-vX.Y.Z.yaml` |
| `verify-release` command | **defined** — content_hash + meta_hash verification |
| Vault signature verification (`verify-release`) | **concept** — ECDSA verification with Vault pubkey |
| build_hash with actual build env | **n/a** — D-013 closed, replaced by content_hash |
| `make release` yq PATH fix | **defined** — yq installed in Dockerfile |

---

## Release process (PrimitiveRelease bundle model)

```bash
# 1. Switch to release branch
git checkout -b primitives/releases/vX.Y.Z

# 2. Vault env
export VAULT_ADDR="https://127.0.0.1:18200"
export VAULT_TOKEN=$(cat $XDG_RUNTIME_DIR/vault/sign-token)
export VAULT_CACERT=/path/to/ca.pem          # or VAULT_SKIP_VERIFY=1 in dev mode
export VAULT_CERT_PATH="secret/cic-cert/pem" # KV v2 mount/secret/key format

# 3. Generate release bundle
make release
# → validates → assembles specs[] → content_hash → Vault sign → release/cic-primitives-vX.Y.Z.yaml

# 4. Commit + tag
git add release/cic-primitives-vX.Y.Z.yaml
git commit -m "release: X.Y.Z"
git tag -a "primitives/@vX.Y.Z" -m "release: X.Y.Z"

# 5. Verify
python tools/compiler.py verify-release release/cic-primitives-vX.Y.Z.yaml
```

Dockerfile requirements: `git`, `curl`, `jq`, `yq` + `safe.directory /app`.
