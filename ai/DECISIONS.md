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

## D-011 — Access: a 8. atom (2026-05-04)

**Döntés:** Az Access a 8. irreducibilis szemantikai atom — nem aggregate, nem PolicySurface.

**Miért atomic és nem aggregate:**
A permission wrapper VALUE szinten él, minden Shape példányon. A `key: 4` és a
`key: {value: 4, access: [...], modify: [...], inherit: true, default_injection: null}`
szemantikailag ekvivalens — a compiler normalizálja. Ez nem rárakott réteg, hanem
a Shape belső struktúrája. Aggregálni nem lehet tovább.

**Viszony a Role atomhoz:** ortogonális.
- `role` = mit jelent a mező a management modellben (config/state/operational)
- `access` = ki érheti el — cert-alapú identity
- Példa: `role: state` + `modify: [OU=adapters,O=cic]` → az adapter írja, user csak olvassa

**Access atom struktúrája:**
```
value:             a tényleges adat (Shape típusa határozza meg)
access:            ki olvashatja — CertPattern lista (OR szemantika)
modify:            ki írhatja — CertPattern lista (OR szemantika)
inherit:           true | false | 0
                   true = sub-objektum örökli
                   false = nem örökli, sub-objektum default szabályait kapja
                   0 = teljes reset, újraszámol
default_injection: mit kap a kérező ha nincs access joga (null = mező nem látható)
```

**CertPattern nyelv:**
X.509 Subject field alapú, wildcard `*` támogatással. Lista = OR szemantika.
- `O=acme` — bármely acme-corp cert
- `OU=ops,O=acme` — acme operátorok
- `CN=*,O=partner-a` — partner-a bármely user-je
Identity forrás: cert PEM mTLS kérésből — DN, SAN, vagy custom extension (implementációs részletkérdés).

**PolicySurface aggregate** (Phase 4.x, külön feladat):
Objektum-szintű default szabályok — az Access atom `inherit: true` esetén innen veszi
az alapértéket. Ez aggregate, nem atomic. Blokkolt az Access atom implementációjától.

**Következmény:** `schemas/atomic/access.yaml` létrehozandó (Phase 8.2).
A Shape atom leírása kiegészítendő: minden Shape érték Access atomba ágyazott.
Compiler: rövid forma → hosszú forma normalizálás.
Runtime: mTLS cert kiértékelés az Access szabályok ellen.

---

## D-012 — Access atom: conformance dimenzió (2026-05-06)

**Döntés:** Az Access atom `conformance` mezővel bővül, amely az eszköz-szintű
implementációs státuszt hordozza — elkülönítve a jogosultság-alapú láthatóságtól.

**Két alapvetően különböző eset:**

| | Jogosultság hiány | Nem implementált |
|---|---|---|
| Olvasás | null / mező nem látszik | null / mező nem látszik |
| Írás | PERMISSION DENIED | HARD REJECT — "not implemented on device X" |
| Jelentés | a mező létezik, te nem férsz hozzá | a mező NEM LÉTEZIK az eszközön |

**Miért nem ugyanaz:** Ha egy write csendes elfogadás helyett hard reject nélkül elveszik,
az operátor azt hiheti a konfig alkalmazva lett — miközben az eszközön semmi sem történt.
Példa: `dhcp_enabled: true` beírva egy DHCP-t nem támogató switch-re → silent failure →
az operátor DHCP-t feltételez ahol nincs.

**A `conformance` mező értékei:**
```
implemented      (default) — mező létezik és kezelhető az eszközön
not_implemented  — mező NEM létezik az eszközön, write HARD REJECT-tel zár
deprecated       — mező létezik de kerülendő, write WARNING + elfogadás
```

**Runtime enforcement `not_implemented` esetén:**
- Olvasás: `default_injection` értéke (tipikusan null → mező nem látszik)
- Írás: hard error, NEM permission denied — "field 'X' is not implemented on device Y"
- Csendes elfogadás: TILOS — a Relay nem droppolhatja a write-ot

**Hol jelenik meg:** Az adapter binding deklarálja device-szinten melyik mezők
`not_implemented`. A séma (RFC-derivált) teljes mezőlistát tartalmaz — a conformance
az adapter runtime annotációja, nem séma-szintű eltávolítás.

**Következmény:** `schemas/atomic/access.yaml` kiegészítendő `conformance` mezővel.
A Relay runtime enforcelja: `not_implemented` mezőre érkező write-ot nem droppolja,
hanem explicit hibával visszadobja a kérőnek.

---

## D-010 — Shape atom: permission-aware value wrapper (2026-05-04)

**Döntés:** Minden Shape értéknek két szintaktikailag ekvivalens reprezentációja van:

```yaml
# Rövid forma (syntactic sugar):
cpu_cores: 4

# Hosszú forma (ekvivalens, kibontott):
cpu_cores:
  value: 4
  access: [...]          # ki olvashatja — cert-alapú identity
  modify: [...]          # ki írhatja
  inherit: true          # sub-objektumok öröklik-e ezt a szabályt (false = nem, 0 = reset)
  default_injection: null  # mit kapjon a kérező ha nincs access joga
```

**Miért:** Az adat és a jogosultság elválaszthatatlan — nem kell külön policy fájl,
path referencia vagy szinkronizáció. A permission szabály az értékkel együtt utazik.
`default_injection` megakadályozza az információ-szivárgást és a null/error hibákat.

**Identity anchor:** X.509 cert PEM — az mTLS kérésben már ott van, nincs külön lookup.
Az `access`/`modify` listában cert-alapú identitás szerepel (DN, SAN, vagy custom extension
— implementációs részletkérdés, a cert PEM az alap).

**Normalizálás:** A compiler a rövid formát mindig kibontja hosszúvá az örökölt/default
szabályok alapján. A runtime mindig a kibontott formán dolgozik. A schema-k rövid formában
írhatók — csak ott kell long form ahol permission override szükséges.

**Öröklés:**
- `inherit: true` → sub-objektum örökli a szülő permission szabályait erre a mezőre
- `inherit: false` → nem örökli, sub-objektum default szabályait kapja
- `inherit: 0` → teljes reset, a sub-objektum teljesen újraszámolja

**Következmény:** A Shape atom belső struktúrája ez — nem két különböző típus.
A Phase 8 implementáció ezt a struktúrát dolgozza ki részletesen (atomic szintű spec,
compiler normalizáció, runtime kiértékelés).
