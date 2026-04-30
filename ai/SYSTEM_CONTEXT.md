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
tools/compiler.py     CLI: validate, release, get-name
tools/schemalib/      Schema pipeline
  ├── loader.py       YAML betöltés $ref feloldással
  ├── validator.py    Integritás ellenőrzés + jsonschema validálás
  └── artifact.py     Checksum, signing payload, artefaktum összeállítás
tools/releaselib/     Git/Vault service absztrakciók
mk/infra.mk           Makefile include
```

Signing mechanizmus (commit-msg hook):
1. `git write-tree` → staged tree snapshot
2. Determinisztikus tar stream → SHA256 digest
3. Vault Transit: ECDSA SHA256 aláírás
4. X.509 cert (CIC Root CA → fejlesztő)
5. `[signing-metadata]` → commit message

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

## Jelenlegi állapot (2026-04-30)

A repo git bootstrap **előtt** van.

- Nincs git init
- Nincs base remote
- Nincs project.yaml
- Nincs egyetlen séma fájl sem

Minden tartalom **concept** státuszban — tervezési döntések a `primitive.txt`
ChatGPT threadben és az `ai/DECISIONS.md`-ben.

---

## Fejlesztői bootstrap sorrend

```bash
# 1. Git init
git init
git remote add base git@github.com:CentralInfraCore/base-repo.git
git fetch base
git merge base@0.5.0 --allow-unrelated-histories

# 2. project.yaml létrehozása (repo_type: schema vagy primitive)

# 3. schemas/ struktúra

# 4. make validate

# 5. make release VERSION=0.1.0
```
