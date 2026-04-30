# CIC Primitives — Claude kontextus

## Mi ez a rendszer

A `cic-primitives` a CentralInfraCore **meta-séma rétege** — az a szint, amelyből
minden domain objektum (switch interface, kubernetes pod, service, database, policy)
schema-szinten levezethető.

Nem domain modell. Nem IaC tool. Nem YANG leíró.

A primitívek azok az **irreducibilis szemantikai atomok és kompozícióik**, amelyekből
bármilyen menedzselt objektum strukturált, validálható, verziózott YAML sémává fordítható.

Részletes architektúra: `ai/SYSTEM_CONTEXT.md`
Következő konkrét feladatok: `ai/PROMPTMAP.yaml`
Tervezési döntések háttere: `ai/DECISIONS.md`

---

## Boot sequence — minden session elején

Mielőtt szakmai kérdésre válaszolsz, végezd el ezt a sorrendet:

1. `mcp__cic-graph__kb_status` — tudásbázis elérhető és friss?
2. Olvasd el: `ai/SYSTEM_CONTEXT.md`
3. Státusz térkép: mi **defined**, mi **draft**, mi **concept**
4. Bridge térkép: hol nincs még séma-szintű megfelelő a fogalomnak

Amíg ez a négy pont nincs meg, ne tegyél tényállításokat a primitive modell állapotáról.

---

## Háromszintű státusz — minden állításhoz kötelező

| Státusz | Jelentés |
|---|---|
| **defined** | YAML séma létezik, `make validate` zöld |
| **draft** | Design megvan írásban, séma még nincs |
| **concept** | Megbeszélt, de formálisan még nincs rögzítve |

Jelenleg **minden elem concept vagy draft** — a repo git bootstrap előtt van.

---

## Scaffold térkép (aktuális)

| Elem | Státusz | Előfeltétel |
|---|---|---|
| git repo bootstrap | **concept** | `git init` + `git merge base@0.5.0` |
| project.yaml | **concept** | repo_type döntés (schema vs. új típus) |
| atomic primitives YAML | **concept** | git bootstrap + schemas/ struktúra |
| aggregate primitives YAML | **concept** | atomic layer defined |
| `make validate` | **concept** | schemas/index.yaml + tooling örökítve |
| első signed release | **concept** | Vault + `make release VERSION=x` |

---

## A két szint

```
atomic primitive   = irreducibilis szemantikai atom
                     Shape · Role · Behavior · Contract · Address · Identity · Event
                   → ezekből schema fragment generálható

aggregate primitive = szemantikai kompozíció sealed/defaulted/required slot-okkal
                   → ezek adják a használható tervezési egységeket
                   → aggregate-ből indulunk, nem atomból
```

Az objektum mindig következmény, soha nem kiindulópont.

---

## A kompozíciós mechanizmus

**Git remote = öröklődési lánc.** Nem YAML override rules.

```
base-repo (upstream sablon)
    │  remote: base → git merge base@0.5.0
    └──► cic-primitives  (ez a repo)
              │  remote: base → git merge base@0.5.0
              └──► domain repók (cic-yang, cic-network, stb.)
```

A fájlstruktúra IS az interface contract. A merge konfliktus = séma sértés.

---

## Bridge térkép — hol szakad meg a lánc

```
concept/Shape atom        ──?──  schemas/atomic/shape.yaml
concept/ManagedEntity     ──?──  schemas/aggregate/managed-entity.yaml
concept/git-composition   ──?──  git remote + base@0.5.0 merge
design/project.yaml       ──?──  compiler tooling (repo_type döntés)
```

Ha egy kérdés ilyen pontra mutat: ne mondd, hogy "nincs" — mondd, hogy
**"a fogalom documented, de a séma-szintű megfelelője még nem létezik"**.

---

## Graph-first reasoning (MCP)

MCP kérdéseknél ne `search_query → snippet → válasz` sorrendben dolgozz.

Helyette:
1. Fogalom azonosítás → induló node-ok (`search_nodes`, `find_nodes`)
2. 1–2 hop szomszédok (`neighbors`, `guided_path`)
3. Státusz ellenőrzés (defined/draft/concept)
4. Bridge ellenőrzés (van-e séma-fájl megfelelő)
5. Csak ebből válasz

---

## Reasoning mód

Válasz előtt azonosítsd:

- **immersion**: fogalmak, relációk, a primitive modell logikájának befogadása — ne javasolj implementációt
- **design**: séma struktúra, slot definíciók, kompozíciós szabályok tervezése
- **implementation**: konkrét YAML, séma fájl, Makefile változás

Immersion módban tilos hiányt feltételezni ott, ahol scaffold szándékos.

---

## Kapcsolódó repók

| Repo | Remote | Mit ad |
|---|---|---|
| `base-repo` | `base` | tooling, signing hook, CI, Makefile, mk/infra.mk |
| `CIC-Schemas` | referencia | template-schema minta, séma pipeline, signing lánc |
| `CIC-Relay` | — | a runtime ami a primitívekből épülő sémákat futtatja |

---

## Mérce

```bash
make validate          # séma validáció — ha ez nem zöld, semmi sem kész
make release VERSION=  # signed artifact
```

Lezárási kritérium minden primitive-re:
1. Ebből hogyan lesz séma (YAML)?
2. Ebből hogyan lesz API (RESTCONF / OpenAPI)?
3. Ebből hogyan lesz runtime viselkedés?

Ha mind a három megválaszolható → lezárt.
