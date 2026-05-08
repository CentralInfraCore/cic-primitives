# Tervezési döntések

A fogalmak kialakulásának history-ja. Ha egy döntés eredetét keresed,
itt keresd először. Részletes thread: `primitive.txt`.

---

## D-001 — Git remote mint kompozíciós mechanizmus (2026-04-30, frissítve 2026-04-30)

**Döntés:** A primitive öröklődés git remote + pinnelt tag merge, nem YAML override-rules.yaml.

**Pontosítás (D-007-tel együtt):** Csak pinnelt tagre mergelhető (pl. `base@0.5.0`) — branch-re
(pl. `base/main`) nem. A tag rögzíti a composition boundary-t. A fogadó repo minden
remote-merge dependency-t `dependency.yaml`-ban dokumentál (ld. D-007).

**Miért:** A fájlstruktúra IS az interface contract. A merge konfliktus = séma sértés.
A pinnelt tag + dependency.yaml együtt ad determinisztikus, reprodukálható composition-t —
`git merge base/main` nem determinisztikus, bármikor változhat.

**Következmény:** Minden leszármazott repo-nak ugyanazt a fájl-topológiát kell követnie
mint az upstream. A `base-repo` remote a tooling + struktúra single source of truth.
Merge parancs: `git merge base@0.5.0`, nem `git merge base/main`.

---

## D-002 — Aggregate-first, nem atomic-first (2026-04-30)

**Döntés:** Az első definiálandók az aggregate primitive-ek, nem az atomok.

**Miért:** Ha atomic-kal kezdünk, túl hamar YANG-szintű technikai részletekbe ragadunk.
Az aggregate adja a rendszer jelentését. Az atomic csak a backend részlet.

**Következmény:** `schemas/aggregate/` épül ki először, `schemas/atomic/` utána.

---

## D-003 — 7 atom mint irreducibilis szint (2026-04-30)

**Döntés:** Shape, Role, Behavior, Contract, Address, Identity, Event — ez a 7 atom.

**Miért:** Ezek nem YANG fogalmak, nem RESTCONF fogalmak — ezek a menedzsment-szemantika
irreducibilis atomjai. YANG, RESTCONF, OpenAPI mind ezek egyik kifejezési módja.
A CIC primitívek ebből generálhatnak bármilyen target formátumot.

**Következmény:** A primitive rendszer nem kötődik egyetlen szabványhoz sem.
YANG mapping, RESTCONF YAML mapping, saját CIC runtime contract egyaránt levezethetők.

---

## D-004 — YANG inspiráció, nem YANG kötöttség (2026-04-30)

**Döntés:** A YANG mint menedzsment-szemantikai referencia, nem mint kötelező szintaxis.

**Miért:** A YANG config/state szétválasztása, rpc/action/notification modellje jó
szemantikai alap — de a CIC primitívek nem YANG modulokat írnak le, hanem az alattuk
lévő fogalmi szintet.

**Következmény:** A primitive séma YAML-ban él (nem `.yang` fájlban), de a YANG
fogalomkészlete (config tree, state tree, operation, notification, identity, feature)
irányadó az aggregate-ek tervezésekor.

---

## D-005 — Sealed / defaulted / required slot rendszer (2026-04-30)

**Döntés:** Minden aggregate primitive-nek három kategóriájú slot-jai vannak.

| Kategória | Jelentés |
|---|---|
| `sealed` | Nem módosítható leszármazottban |
| `defaulted` | Van alapértelmezés, felülírható |
| `required` | Kötelezően specializálandó |

**Miért:** Nélküle a schema-generálás nem deterministikus és minden speciális eset
kézzel drótozott kivétel lesz.

**Következmény:** Minden aggregate YAML definíciónak tartalmaznia kell
explicit slot listát kategóriával.

---

## D-006 — repo_type döntés (LEZÁRVA: primitive — jövőbeli kiterjesztés)

**Döntés:** Szemantikailag `repo_type: primitive`, de ez a mező jelenleg **nem létezik**
a `project.schema.yaml`-ban és a `compiler.py`-ban.

**Jelenlegi állapot:** A `repo_type` nem `compiler_settings` alatt van — a compiler még
nem ismeri. A szándék `x-cic.repo_type: primitive`-ként dokumentálva a `project.yaml`-ban.

**Miért nem schema:** A cic-primitives nem egyszerű schema repo — schema-képző primitive
repo. Ha `schema` típus kerülne be, szemantikailag torzítaná a toolingot.

**Következmény:** A `compiler.py` és `project.schema.yaml` kiterjesztése a base-repo-ban
szükséges. Addig: `x-cic.repo_type: primitive` a szándék hordozója, `compiler_settings`-ben
nem szerepel.

---

## D-007 — dependency.yaml mint composition lock (2026-04-30)

**Döntés:** Minden repo, amely `git merge <remote>/<tag>` composition-t végez,
kötelezően vezet egy `dependency.yaml` fájlt a gyökerében.

**Struktúra:**
```yaml
schema_version: "1"
dependencies:
  - name: base-repo
    source: github.com/CentralInfraCore/base-repo
    tag: base@0.5.0
    mode: remote-merge
    purpose: repository-contract
    imported_paths:
      - .github/
      - Makefile
      - mk/
      - tools/
```

**Szabályok:**
- Csak pinnelt tag kerülhet be — branch referencia (pl. `main`) tiltott
- Minden `git merge <remote>/<tag>` után frissítendő
- A `dependency.yaml` az egyetlen forrása annak, hogy mi honnan érkezett

**Miért:** Reprodukálhatóság + audit trail. A git history megmutatja _mit_ mergeltek,
a dependency.yaml megmutatja _szándékosan mit_ kellett behozni és miért.

**Következmény:** A `git-bootstrap` task után azonnal jön a `dependency-yaml` task
(PROMPTMAP Phase 1, priority 2).

---

## D-008 — Semantic validate = compiler responsibility, nem primitive modell (2026-04-30)

**Döntés:** A primitive YAML contract marad tisztán deklaratív (sealed/defaulted/required).
A séma-kompatibilitás ellenőrzése — hogy egy domain specializáció kompatibilis-e az upstream
primitive-vel — a `compiler.py validate` feladata, nem beépített override-szabály.

**Nyitott rész (merge stratégia):** Ha egy leszármazott `defaulted` slotot felülír, mi a
merge policy? `replace | deep_merge | append | union` — ez még nincs döntve.
Lezárási feltétel: az első domain repó ténylegesen override-ol egy slotot.

**Miért:** A primitive modell leírja _mit_ jelent egy kezelt objektum. A compiler mondja ki,
hogy egy specializáció _kompatibilis-e_. Ez clean separation of concerns — a primitive nem
tartalmaz futtatási logikát.

**Következmény:** A következő konkrét tooling lépés:
1. `schemas/index.yaml` → primitive meta-schema (mi egy érvényes atomic/aggregate YAML)
2. `compiler.py` → primitive YAML fájlokat is validálja (nem csak `*.meta.yaml`)
3. Semantic compatibility check domain repo specializációra → Phase 6 tooling

---

## D-009 — ExecutionSurface szándékosan hiányzik (2026-04-30)

**Döntés:** Az `ExecutionSurface` aggregate (triggers, dependencies, reconciliation,
failure_policy, ownership, graph_edges) **nem kerül be most**.

**Miért:** Ha a Relay valós graph execution modellje nélkül definiáljuk, spekulatív lesz
és valószínűleg újra kell írni. A helyes sorrend:
1. CIC-Relay valós futtatási modell (mi vált ki, mi a desired→actual átmenet, mi történik hibánál)
2. Abból visszavezetni az ExecutionSurface slot-jait
3. Nem fordítva

**Következmény:** Az ExecutionSurface nyitott bridge marad amíg a Relay modell nincs.
Ha valaki ExecutionSurface-t igényel, először a Relay execution modelljét kell definiálni.

---

## D-013 — build_hash és source_hash szétválasztása (2026-05-08)

**Státusz:** nyitott — döntés szükséges (BACKLOG B-005)

**Helyzet:**
A `compiler.py` `run_release()` függvényében:
```python
build_hash = source_hash  # egyelőre — tényleges build env nincs még
```
A két hash mindig azonos. A signed release-ben mindkettő szerepel, de tartalmilag redundáns.

**Döntés:**
Ha a CIC pipeline valaha schema fordítási lépést kap (pyang compile, OpenAPI generátor,
code gen), a `build_hash` a build artifact hash-e lesz — nem a forrásé.
Addig a placeholder elfogadható, de explicit KNOWN_LIMITATION státusszal kell jelölni.

**Azonnali teendő:**
A `project.yaml` release blokkjában dokumentálni:
```yaml
release:
  _known_limitation: build_hash == source_hash (no separate build step yet)
```
Így a signed artifact önleíró marad.

---

## D-014 — Cross-domain referenciák típuskezelése (2026-05-08)

**Státusz:** nyitott — döntés szükséges (BACKLOG B-008)

**Helyzet:**
CIC objektumok közötti hivatkozások (pl. StorageResource → ComputeResource, KubernetesNode → KubernetesCluster)
jelenleg plain `string` típusú mezők. A `logical_id` formátum (`cic:{domain}:{...}`) dokumentált,
de schema szinten nincs kényszerítve.

**Döntés opciók:**
1. **Szemantikus típus a Shape atomban:** `type: cic-reference` — a compiler ellenőrzi a formátumot,
   a runtime (Relay) ellenőrzi a target létezését. Ez a legtisztább megoldás.
2. **Pattern constraint:** a meglévő string mezőhöz `contract: [{type: pattern, expression: "^cic:[a-z]+:"}]`
   — minimális változás, de nem ad domain-specifikus információt.
3. **Elfogadás:** a cross-domain referencia runtime constraint, nem schema constraint.
   A Relay validálja, a schema nem.

**Ajánlott:** opció 1 — a CIC modell értéke részben a tipizált referencia láncon múlik.
Ha ez csak string, a schema-driven tooling nem tudja feloldani a dependency gráfot.
