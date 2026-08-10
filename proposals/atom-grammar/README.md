# Atom-grammatika — P0.1 / P0.2 / P0.5 lezárása

**Státusz:** javaslat (`concept`). Nincs bekötve egyetlen repo pipeline-jába sem.
**Készült:** 2026-08-10, orchestrátori munka.
**Hatókör:** a külső review P0-listájából az a három tétel, amihez a lezárt
`cic-object-model` nem ért hozzá:

| P0 | Tétel | Itt |
|---|---|---|
| 1 | Shape típusalgebra | §2 |
| 2 | Role kombinációs szabályok | §3 |
| 5 | Primitívek közötti constraintek | §4 |

**Nincs benne** (szándékosan): P0.3 (Contract typed payload), P0.4 (Access
policy-grammatika), P0.6 (teljes meta-séma csere). A P0.4 érdemi részét a
`cic-object-model` SPEC §6.4 már megírta; az a repo archivált, de a szöveg
kiemelhető. A P0.3 önálló munka.

---

## 1. Mit rögzít ez a dokumentum, és mit nem

A `schemas/atomic/*.yaml` fájlok **fogalomkatalógusok**: leírják, mi az a Shape
és mi az a Role. Amit nem írnak le: **hogyan néz ki egy konkrét példány**. Ez a
dokumentum a példányformát rögzíti, és csak azt.

A grammatika a **korpusz tényleges kódolására** épül, nem elméleti alakra. Mérve
2026-08-10, két élő kompozíción (`primitives/schemas/examples/kubernetes-pod.yaml`,
`cic-compute` `main:schemas/domain/compute-resource.yaml`), összesen 83 `shape_type`
és 32 `role` előfordulás.

Ez tudatos döntés: a korpusz prefix-kódolást használ (`shape_type:`,
`scalar_type:`, `collection_variant:`), nem csoportosat (`shape: {type: ...}`).
Az archivált objektummodell a csoportosat írta elő (INV-023 környéke), de az a
keret nem él. Egy grammatika, ami a meglévő 65+ előfordulást elsőre elutasítja,
nem grammatika, hanem migrációs teher. **A csoportos alak később, egy expliciten
verziózott lépésben jöhet — de akkor konverterrel, ne kézzel.**

### Amit a korpusz mérése kiderített

| Megfigyelés | Következmény |
|---|---|
| `role` **7 értéket** definiál, a korpusz **4-et használ**: `config` (12), `state` (7), `operational` (7), `key` (6) | a `reference`, `derived`, `volatile` **nulla** példánnyal van alátámasztva — §3 ezért nem egyenrangúként kezeli őket |
| a `reference` a korpuszban **nem** `shape_type`, hanem `scalar` + `semantic_type: cic-reference` + `reference_target` | §2.4 ezt teszi normatívvá, a `shape_type: reference`-t elavulttá |
| `mandatory:` (11) és `optional:` (21) egymás mellett élő, egymást átfedő jelölés | §2.5 egyetlen tengelyre teszi őket |
| `item_fields` (6) és `key_fields` (1) — a collection kulcsa létezik | §2.3 rögzíti, kötelezővé teszi `list` variánsnál |

---

## 2. Shape — típusalgebra (P0.1)

### 2.1 A típushalmaz zárt

```
shape_type ∈ { scalar, composite, collection, choice, opaque }
```

Öt érték, és **csak** ez az öt. A katalógus `reference` típusa megszűnik
(→ §2.4), az `opaque` új (→ §2.6).

Minden `shape_type`-hoz **pontosan egy** kötelező kísérőmező tartozik. Ez az,
ami ma hiányzik: a katalógus felsorolja a típusokat, de nem mondja meg, mi
teszi őket teljessé.

| `shape_type` | Kötelező kísérő | Tilos |
|---|---|---|
| `scalar` | `scalar_type` | `fields`, `item_fields`, `cases` |
| `composite` | `fields` (≥1 elem) | `scalar_type`, `item_fields`, `cases` |
| `collection` | `collection_variant` + (lásd §2.3) | `fields`, `cases` |
| `choice` | `cases` (≥2 elem) | `scalar_type`, `fields`, `item_fields` |
| `opaque` | — | minden szerkezeti kísérő |

### 2.2 `scalar`

```
scalar_type ∈ { string, integer, boolean, number, bytes }
```

A katalógus ezt így sorolja fel, és a korpusz csak `string`/`integer`-t használ.
A halmaz zárt marad; új skalártípus **verzió-inkrementum**.

Eldöntve: a `scalar_type` **külön mező**, nem a `shape_type` altípusa. A review
felveti, hogy lehetne `type: integer` közvetlenül. Nem lehet: a `shape_type`
a *szerkezeti arity* (skalár-e vagy összetett), a `scalar_type` az *érték
tartománya*. Összevonva a `composite`-nak nem lenne párja, és a korpusz 74
`scalar_type` előfordulását át kellene írni. Külön marad.

### 2.3 `collection`

```
collection_variant ∈ { list, set }
```

| | `list` | `set` |
|---|---|---|
| Elemleírás | `item_fields` (≥1) | `item_scalar_type` |
| Kulcs | lásd lent — **kötelező**, de nem mindig kiírva | tilos |
| Rendezettség | `ordered: bool` (default `false`) | mindig rendezetlen |
| Elemszám | `min_items` / `max_items` (opcionális, `0 ≤ min ≤ max`) | ua. |

**Minden listának van kulcsa.** Kulcs nélkül egy elem címe a pozíciója, és a
pozíció beszúráskor elmozdul. Egy rendszerben, ahol a bizonyíték állapotra
hivatkozik, a néma jelentésváltozás defektus. (Ez ugyanaz az érv, amivel az
archivált objektummodell az anonim Contract-listát elutasította — az érv
túléli a keretet.)

A kulcs **kétféleképpen** deklarálható, és a szabály feltételes:

| Eset | Szabály |
|---|---|
| pontosan egy `item_fields` elem visel `role: key`-t | a kulcs **levezethető**, nem kell kiírni |
| kettő vagy több visel | `item_key: [név, ...]` **KÖTELEZŐ** — az összetett kulcs **sorrendje** különben definiálatlan |
| egyik sem visel | hiba: a listának nincs kulcsa |

Ha az `item_key` ki van írva, minden eleme MUST szerepeljen az `item_fields`
között, és MUST `role`-ja `key` legyen (→ §4, C8).

> **Miért `item_key` és nem `key_fields`.** A `key_fields` név a korpuszban
> **már foglalt**, és mást jelent: a `binding_surface.addresses[].key_fields`
> az Address kulcskomponenseit sorolja fel `{name, type, values}` objektumként
> (`compute-resource.yaml:489`). A két fogalom nem ugyanaz és nem is azonos
> alakú. Az első változat ezt a nevet vitte el — a korpusz futtatása derítette
> ki, nem az átolvasás.

> **Mérés:** a két élő kompozíció mind a **6** listája egykulcsú, tehát ma
> egyik sem igényel `item_key`-t. A feltételes szabály tehát nem migrációs
> teher — a jövőbeli összetett kulcsot zárja le, amit ma semmi nem definiál.

### 2.4 `reference` — annotáció, nem típus

A katalógus a `reference`-t `shape_type` értékként sorolja fel. A korpusz nem
így írja:

```yaml
- name: network
  shape_type: scalar
  scalar_type: string
  semantic_type: cic-reference
  reference_target: "cic:network:NetworkInterface"
```

**A korpusz nyer.** Egy referencia a huzalon string; hogy referencia, az
szemantikai annotáció, nem szerkezeti arity. A `shape_type: reference` elavult,
és a grammatika elutasítja.

#### A referencia-nyelvtan (két külön dolog, ma összekeverve)

| | Mi | Alak | Hol |
|---|---|---|---|
| **Céltípus** | melyik Kind-ra mutat | `{namespace}:{Kind}` | `reference_target` |
| **Érték** | melyik példányra mutat | `cic:{domain}:{backend}:{provider}:{location}:{id}` | a mező futásidejű értéke |

A `namespace` **már tartalmazza** a `cic:` prefixet (`identity.yaml:81,87,93`:
`"cic:core"`, `"cic:network"`, `"cic:kubernetes"`).

**Defektus, amit ez javít:** a `shape.yaml:83` a céltípust
`cic:{namespace}:{Kind}` alakban dokumentálja. Behelyettesítve a saját
namespace-értékeit: `cic:cic:network:NetworkInterface`. A korpusz helyesen
`"cic:network:NetworkInterface"`-t ír, tehát `{namespace}:{Kind}`.
**A dokumentált formátum a hibás, nem a korpusz.** A `shape.yaml:83`
javítandó.

**Második defektus:** `identity.yaml:55` `base` példája `"cic:ManagedEntity"`
— két szegmens, namespace nélkül. Az ugyanennek a fájlnak a `:89`/`:95` példái
`"cic:core:ManagedEntity"`-t írnak. A kétszegmensű alak nem érvényes;
`identity.yaml:55` javítandó.

`semantic_type: cic-reference` és `reference_target` **együtt kötelezők**, egyik
sem állhat a másik nélkül (→ §4, C9).

### 2.5 `optional` / `mandatory` / `nullable` / `default`

Ma a `mandatory` (11 előfordulás) és az `optional` (21) egymás mellett él,
egymás tagadásaként — de semmi nem tiltja, hogy mindkettő `true` legyen.

**Egyetlen tengely, `presence`:**

```
presence ∈ { mandatory, optional }        default: mandatory
```

A `mandatory: true` és `optional: true` rövid alakok **megmaradnak**
(a korpusz ezeket írja), de:

- egyszerre legfeljebb az egyik jelenhet meg;
- `mandatory: false` és `optional: false` **tilos** — a tagadó alak nem
  fejez ki semmit, csak a másik mezőt tenné kétértelművé.

**Az érvényes kombinációk teljes mátrixa:**

| `presence` | `nullable` | `default` | Érvényes? | Jelentés |
|---|---|---|---|---|
| mandatory | false | — | ✔ | jelen kell lennie, értékkel |
| mandatory | true | — | ✔ | jelen kell lennie, lehet `null` |
| mandatory | — | van | ✘ | **kötelező mezőnek nincs értelme default** |
| optional | false | — | ✔ | hiányozhat; ha hiányzik, nincs érték |
| optional | false | van | ✔ | hiányozhat; ha hiányzik, a default lép be |
| optional | true | — | ✔ | hiányozhat vagy `null` — **két különböző állapot** |
| optional | true | `null` | ✘ | a default `null` nem különbözik a hiánytól |

Az utolsó két sor a lényeg: `optional + nullable` esetén a „hiányzik" és a
„`null`" **nem ugyanaz**, és aki ezt kihasználja, annak a Contract oldalon meg
kell mondania, melyik mit jelent. A `default: null` viszont a kettőt
összemossa, ezért tilos.

### 2.6 `opaque`

Új típus, mert a korpuszban ma nincs mód azt mondani, hogy „ez egy blob, a
séma nem néz bele". Enélkül ilyet vagy `composite`-nak hazudnak (és akkor a
validátor a belsejét is állítja tudni), vagy `string`-nek (és akkor elveszik,
hogy szerkezet van benne).

Az `opaque` **terminális**: nincs alatta séma-ismert gyermek, és a
validátor nem lép bele. A `contract` továbbra is alkalmazható rá
(pl. `pattern` a szerializált alakra), de a belső szerkezetére nem.

---

## 3. Role — kombinációs algebra (P0.2)

A review központi megfigyelése helyes: a hét felsorolt érték **nem egy
dimenzió**. Három tengely van, és a mai lapos lista összekeveri őket.

```
authority  ∈ { config, state, operational }     pontosan egy, KÖTELEZŐ
structural ⊆ { key, reference }                 nulla vagy több
lifecycle  ∈ { derived, volatile }              nulla vagy egy
```

### 3.1 Rövid és hosszú alak

A korpusz mind a 32 helyen rövid alakot ír (`role: config`, `role: key`). Ez
megmarad:

```yaml
role: config          # ⇔ role: { authority: config }
role: key             # ⇔ role: { authority: config, structural: [key] }
role: state           # ⇔ role: { authority: state }
```

Hosszú alak akkor kell, ha egynél több tengelyt akarsz megnevezni:

```yaml
role:
  authority: state
  structural: [reference]
  lifecycle: volatile
```

**A rövid alak feloldása kötött, nem ízlés kérdése:** a `key` `authority`-ja
`config`, mert a lista kulcsát a management plane adja meg létrehozáskor. A
`reference` `authority`-ja **nem** vezethető le — ezért a `role: reference`
rövid alak **tilos**, hosszú alakot kell írni. (A korpuszban nem is fordul elő.)

### 3.2 Az érvényes kombinációk

| Szabály | Indok |
|---|---|
| `authority` pontosan egy — kihagyva `config` | egy mező vagy kívánt állapot, vagy megfigyelt, vagy számított; a három kizárja egymást |
| `derived` **kizárja** a `config`-ot | számított értéket nem lehet kívánt állapotként beállítani |
| `volatile` **kizárja** a `config`-ot | nem perzisztens értéknek nincs kívánt állapota |
| `key` **megköveteli** a `config`-ot | a kulcsot a kérő adja meg |
| `key` **megköveteli** a `mandatory`-t | kulcs nem hiányozhat |
| `key` **csak** `collection.key_fields`-ben álló mezőn | máshol nincs mit azonosítania |
| `key` **kizárja** a `derived`-et és a `volatile`-t | a kulcs a létrehozás után nem változhat |
| `reference` **megköveteli** a `semantic_type: cic-reference`-t | különben nincs mire mutatnia |

**Ami így legális és ma leírhatatlan** — pont a review példája:

```yaml
role:
  authority: state
  structural: [reference]
  lifecycle: volatile
```

Megfigyelt, másik entitásra mutató, nem perzisztált érték. Ma ezt `role: state`-nek
kellene írni, és a másik két tulajdonság elveszne.

### 3.3 A három alátámasztatlan érték

A `reference`, `derived`, `volatile` **nulla** korpusz-példánnyal rendelkezik.
Nem törlöm őket — a `derived` és a `volatile` a `lifecycle` tengelyt hordozza,
és annak a hiánya valódi kifejezőerő-hiány lenne. De jelezni kell: ezek
`concept` státuszúak, és az első valódi használatuk fogja kideríteni, hogy a
fenti szabályok helyesek-e.

---

## 4. Primitívek közötti contractek (P0.5)

Ez az, amit ma **semmi** nem kényszerít ki, és amiért a nyolc atom nyolc
külön dokumentum marad ahelyett, hogy egy nyelv lenne.

| # | Szabály | Miért |
|---|---|---|
| **C1** | `authority ∈ {state, operational}` → `access.modify` csak adapter-mintát tartalmazhat | megfigyelt állapotot nem a felhasználó ír; ha mégis, az nem state, hanem config |
| **C2** | `lifecycle = derived` → `access.modify` üres | számított értékre az írás értelmezhetetlen |
| **C3** | `default` MUST kielégítse a node **összes** `contract` bejegyzését | ma egy `default: 0` és egy `range: "1..256"` békésen megfér egymás mellett |
| **C4** | `mandatory` és `default` együtt tilos | §2.5 mátrix |
| **C5** | `contract type: enum` → a `default` MUST az értéklistában legyen | a C3 speciális esete, külön nevesítve, mert ez a leggyakoribb |
| **C6** | `behavior.input` / `.output` MUST létező Shape-re oldódjon fel | ma bármilyen string állhat ott |
| **C7** | `event.payload` MUST létező Shape-re oldódjon fel | ua. |
| **C8** | minden listának van kulcsa; összetett kulcsnál `item_key` kötelező, és minden eleme `role: key`-es `item_fields` elem | §2.3 |
| **C9** | `semantic_type: cic-reference` ⇔ `reference_target` | egyik sem állhat a másik nélkül |
| **C10** | `reference_target` MUST `{namespace}:{Kind}` alakú legyen, és a `{namespace}` MUST `cic:`-vel kezdődjön | §2.4 |

### Amit szándékosan NEM zárok le

**A `capability` mechanizmus — és amit a `conformance`-ról elárul.**

A korpusz futtatása egy olyan mezőpárt talált, amit egyik atom sem ismer:

```yaml
- name: availability_zone
  shape_type: scalar
  scalar_type: string
  role: config
  optional: true
  capability: cloud            # ← csak cloud backenden létezik

- name: power_state
  capability_values:
    paused: hypervisor_suspend # ← ez az ÉRTÉK csak ezzel a capabilityvel áll elő
```

Mérve a `cic-compute` `main:schemas/domain/compute-resource.yaml`-ben:
**19 `capability`** és 1 `capability_values` előfordulás, mind mezőszinten.
Ezzel szemben:

- `grep -rn capability schemas/atomic/` → **0 találat**. Egyetlen atom sem ismeri.
- `managed-entity.yaml:105` — `capability_surface: {type: TBD, status: placeholder,
  blocked_by: "CapabilitySurface aggregate (no model yet)"}`.

Vagyis a `capability_surface` **placeholderként, blokkoltként** van deklarálva
az aggregate rétegben, miközben a mechanizmus a példány rétegben **már 19
helyen élesben fut**, séma és validáció nélkül.

Ez a `conformance`-kérdés harmadik, független bizonyítéka. A három együtt:

1. a külső review szerint a `conformance` szemantikailag kilóg az Accessből;
2. maga a D-012 szövege mondja: *„the adapter's runtime annotation"*;
3. a korpuszban **már van** egy adapter-feltételes mezőlétezés-mechanizmus
   (`capability`), csak nincs modellezve.

A `capability: cloud` (a mező csak bizonyos backenden létezik) és a
`conformance: not_implemented` (a mező ezen az eszközön nem létezik)
**ugyanaz a fogalom, két néven**. A grammatika ezért mindkettőt átengedi
ismert, de nem validált tagként — nem az én dolgom eldönteni, melyik marad.

**A `conformance` mező helye.** A `schemas/atomic/access.yaml` hordozza
(D-012, `574a1f1`), a `v0.1.0` release még nem tartalmazta, és maga a D-012
szövege mondja: *„conformance is the adapter's runtime annotation, not a
schema-level removal."* A külső review szerint szemantikailag kilóg az
Accessből. Egyetértek — de az, hogy hova tartozik (BindingSurface?
CapabilitySurface? önálló atom?), **döntés, nem levezetés**. Amíg nincs
eldöntve, a grammatika nem érinti.

**Az `access` belső nyelvtana (P0.4).** Az `inherit` háromállapotúsága
(`true` / `false` / `0`) booleanként nem stabil típus — a review-nak igaza van,
és az archivált objektummodell sem javította, szó szerint átvette. Valódi enum
kell (`inherit` / `no-inherit` / `reset`), de az `access` teljes
policy-grammatikájával együtt, nem külön.

**Az Address kontra ManagedEntity ellentmondás.** `address.yaml`: *„An entity
may exist without an address"*; `managed-entity.yaml` `binding_surface:
mode: required`. Ez a kettő nem fér meg. A feloldás valószínűleg az, hogy a
`binding_surface` `defaulted`, üres alapértékkel — de ez az aggregate réteg
döntése, nem az atomoké.

---

## 5. Hogyan ellenőrizhető

```
proposals/atom-grammar/
  instance-grammar.schema.yaml   ← JSON Schema: §2 szerkezeti szabályok
  check_grammar.py               ← séma + a §3/§4 keresztszabályok (amit JSON Schema nem tud)
```

Futtatás a két élő kompozíción:

```bash
python3 proposals/atom-grammar/check_grammar.py \
  ~/sync/git.partners/CentralInfraCore/primitives-group/primitives/schemas/examples/kubernetes-pod.yaml
```

A `check_grammar.py` **stdlib + PyYAML**, konténer nélkül fut, mert egy
grammatika, amit csak a saját pipeline-ja tud futtatni, nem ellenőrizhető
harmadik fél által.

**A kapu vakfoltja ellen:** a `check_grammar.py --self-test` szándékosan hibás
példányokat futtat át, és elhasal, ha bármelyiket átengedi. Egy validátor,
amiről nem mérted le, hogy tud bukni, nem validátor.
