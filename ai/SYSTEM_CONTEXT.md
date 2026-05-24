# System Context (AI számára)

Olvasd el mielőtt bármit módosítasz.

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
