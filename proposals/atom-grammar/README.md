# Atom-grammatika — P0.1 / P0.2 / P0.5 lezárása

**Státusz:** `implemented` — a `make grammar` a `make validate` **előfeltétele**,
tehát valódi kapu, nem dokumentum. Mérve: egy injektált defekt (`replicas`
default 1 → 0 a saját `range: "1..1000"` contractja ellen) `make validate`-et
`Error 1`-gyel elhasította, és a compiler el sem indult.
A `proposals/` alatti hely szándékos: a `compiler.py` egyik globja sem szedi
fel, tehát a grammatika **kapuz, de nem kerül a release-bundle-be** és nem lesz
aláírt séma-artifact. Ha ez megváltozik, az külön döntés.
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

#### `item_choice` — collection-elem diszkriminált unió (cic-primitives#8)

A fenti modell egyetlen feltevésre épül: **egy lista minden eleme azonos
mezőszerkezetű.** A `cic-schema-registry` `network-interface.yaml`
`vlans`/`vxlans` listája ezt cáfolta: minden elem VAGY `{ref}` (egy megosztott
VLAN-definícióra mutat), VAGY egy inline definíció (`{vlan_id, vlan_mode,
allowed_vlans, dhcp_service}`) — `ref` és `vlan_id` **alternatívák**, nem
együtt kötelezők. A fenti szabállyal ez csak úgy volt kifejezhető, hogy
`vlan_id`-t `role: key, mandatory: true`-vá tették — ami kielégíti a "van
kulcs" követelményt, de emellett **azt is megköveteli, hogy `vlan_id` akkor
is jelen legyen, amikor `ref`-et használnak** — egy redundáns identitás-
állítás (`dereference(ref).vlan_id == vlan_id`) semmilyen konzisztencia-
garancia nélkül. Részletek: `cic-schema-registry` `theads/thead10.txt`.

A helyes megoldás **nem** a kulcs-mező optionallá tétele — az visszahozná a
pozicionális identitás hibáját, amit a fenti szabály pont kizár. A cél:
**minden elem pontosan egy stabil identitásra oldódjon fel, de az, hogy
MELYIK mező(k) alkotják ezt az identitást, elem-variánsonként eltérhessen.**

**Pontosítás egy külső review után:** ez a mondat CÉL, nem a mechanizmus
által GARANTÁLT tulajdonság — `item_choice` séma-szinten (típusalgebra)
ellenőriz, nem futásidejű adatpéldányokon. A "pontosan egy case illeszkedik"
tényleges biztosítéka a séma-szerző felelőssége: a case-eket úgy kell
megírni, hogy mezőik alapján kölcsönösen megkülönböztethetők legyenek. A
grammatika ezt NEM bizonyítja általánosságban (ehhez explicit
diszkriminátor kellene — lásd lent, miért nem azt választottam), de **C17**
elkap egy konkrét, gyakori hibaosztályt: ha két case UGYANAZT a
kulcs-mezőhalmazt oldja fel (pl. mindkettő kulcsa `id`), egy csak azokat a
mezőket hordozó elem mindkettőre illeszkedne — ez most hiba. A `vlans`
mintában ez nem probléma, mert a `referenced`/`inline` case kulcsa
(`ref` vs. `vlan_id`) eleve különbözik.

```yaml
item_choice:
  cases:
    - name: <case-név>
      key: [<mezőnév>, ...]     # opcionális — ua. levezetési szabály, mint item_key, de case-lokális
      fields: [...]              # a variáns saját, teljes mezőhalmaza
```

`item_fields` **helyett** áll (kölcsönösen kizáróak, `list` variánson
pontosan az egyik kötelező; `set`-en egyik sem megengedett). Minden `case`
egy önálló, teljes mezőhalmazt ír le, **saját** kulccsal — a kulcs-levezetés
szabálya (pontosan egy `role: key` mező ⇒ levezethető; kettő vagy több ⇒
`key:` kötelező; egyik sem ⇒ hiba) case-enként, egymástól függetlenül fut.

```yaml
- name: vlans
  shape_type: collection
  collection_variant: list
  role: config
  optional: true
  item_choice:
    cases:
      - name: referenced
        key: [ref]
        fields:
          - name: ref
            shape_type: scalar
            scalar_type: string
            semantic_type: cic-reference
            reference_target: "cic:network:Vlan"
            role: key
            mandatory: true
      - name: inline
        key: [vlan_id]
        fields:
          - name: vlan_id
            shape_type: scalar
            scalar_type: integer
            role: key
            mandatory: true
          - name: vlan_mode
            shape_type: scalar
            scalar_type: string
            role: config
            mandatory: true
            contract:
              - type: enum
                expression: [access, trunk]
```

A `referenced` case-ben **csak** `ref` szerepel, az `inline` case-ben
**csak** `vlan_id` (+ a többi inline mező) — nincs redundáns kettős
állítás, mert a két mező sosem szerepel egyazon elemen.

**Diszkrimináció: implicit, mezőjelenlét alapján** — ugyanaz az elv, mint a
meglévő `shape_type: choice`/`cases` mechanizmusnál (§2.1), ami szintén nem
használ explicit diszkriminátor-mezőt. Nem vezetek be új elvet csak erre a
pozícióra: melyik `case` illik egy konkrét elemre, az a jelenlévő mezők
halmazából derül ki, nem egy külön "melyik variáns" jelző mezőből.

**Amit ez MÉG mindig nem old meg** (tudott korlátozás, nem blokkoló, C17
után is): a C17 csak a LEGGYAKORIBB, legközvetlenebb ütközést kapja el
(azonos kulcs-mezőhalmaz két case közt) — nem bizonyítja általánosságban,
hogy két case kölcsönösen kizárja egymást (pl. két eltérő nevű, de
egyaránt opcionális mezőkészlet elméletileg átfedhet egy olyan elemen,
ami egyik case egyetlen mandatory mezőjét sem tölti ki). Egy TELJES
garanciához explicit diszkriminátor kellene:

```yaml
item_choice:
  discriminator: kind
  cases:
    - name: referenced
      when: "kind == referenced"
      ...
```

Ezt SZÁNDÉKOSAN nem vezettem be: új nyelvi elem lenne, a `vlans`/`vxlans`
motiváló esetben a mezőjelenlét már önmagában egyértelmű (nincs rá
szükség), és a meglévő sima `choice` sem használ ilyet — konzisztencia
mellett döntöttem az erősebb garancia helyett. Ha egy jövőbeli eset
ténylegesen megköveteli az explicit diszkriminátort, az külön döntés.

Egy mező-szintű feltételes Contract (pl. egy `key_fields` elem érvényes
értékkészlete egy szomszédos `key_fields` elem értékétől függ — lásd
`cic-schema-registry` `theads/thead12.txt`, `StorageResourceOracleCloud`
`binding_surface.addresses[].key_fields.provider`) **más** probléma: ott a
mezőhalmaz fix, csak egy mező Contract-ja feltételes — `item_choice` erre
nem alkalmazható, külön kérdés marad.

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

### 2.7 Address `key_fields` — formalizálva

A `binding_surface.addresses[].key_fields` a corpuson eddig `{name, type,
values}` objektumként élt (`compute-resource.yaml:489`, és minden más
domain-objektum ugyanígy) — nem Shape, nem validált, nincs Contract-algebrája.
Ez a hiány külön issue-ként lett rögzítve
(cic-schema-registry-oldalon: `cic-primitives#5`, "Address atom does not
formalize keyed binding"), miután egy konkrét provider-specializáció
(`StorageResourceOracleCloud`) megpróbálta kifejezni a `backend`/`provider`
szűkítését, és nem tudta — nem a specializáció mechanizmusa hiányzott
(`identity.base` már működik), hanem maga a `key_fields` fogalom nem volt
Shape-ként deklarálva, amin a szűkítést el lehetett volna végezni.

**A formalizáció**: a `key_fields` minden eleme egy rendes Shape-node,
`role: key`-vel — ugyanaz a primitívkészlet (Shape/Role/Contract), amit
minden más mező is használ, nem új mechanizmus. A `schemas/atomic/
address.yaml` `fields.properties.key_fields` hordozza (`type: list<Shape>`).

```yaml
binding_surface:
  addresses:
    - namespace: "cic:storage"
      key_fields:
        - name: backend
          shape_type: scalar
          scalar_type: string
          role: key
          mandatory: true
          contract:
            - type: enum
              expression: [hypervisor, san, cloud]
        - name: provider
          shape_type: scalar
          scalar_type: string
          role: key
          mandatory: true
        - name: location
          shape_type: scalar
          scalar_type: string
          role: key
          mandatory: true
        - name: id
          shape_type: scalar
          scalar_type: string
          role: key
          mandatory: true
```

**Miért nem `item_key`.** A §2.3 jegyzete a fordítottját magyarázza (miért
kapott a Shape-collection összetett kulcsa `item_key` nevet) — ugyanaz a
válasz erről az oldalról nézve: a `key_fields` egy ENTITÁST azonosít a
saját Address-én keresztül, az `item_key` egy ELEMET egyetlen entitás
collection-mezőjén belül. A két fogalom nem esik egybe, csak a nevük
kollidált volna.

**Grammatikai kezelés** (`check_grammar.py`): a `key_fields` felkerült a
`NODE_CONTAINERS`-re, tehát minden eleme rendes Shape-node-ként validálódik
(S2, a JSON Schema réteg). Az `item_fields`-től eltérően — ahol csak
NÉHÁNY elem kulcs, és az `item_key`/egyetlen-`role:key` levezetés dönti el,
melyik — a `key_fields` MINDEN eleme kulcs a definíciójából adódóan, tehát
nincs "levezetés": minden elemnek EXPLICIT `role: key`-t kell hordoznia
(**C16**), és a hiányzó `role` itt hiba, nem levezethető alapértelmezés.

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
role: state           # ⇔ role: { authority: state }
role: operational     # ⇔ role: { authority: operational }
role: key             # ⇔ role: { authority: <az övező surface-é>, structural: [key] }
role: derived         # ⇔ role: { authority: state, lifecycle: derived }
role: volatile        # ⇔ role: { authority: state, lifecycle: volatile }
```

Hosszú alak akkor kell, ha egynél több tengelyt akarsz megnevezni:

```yaml
role:
  authority: state
  structural: [reference]
  lifecycle: volatile
```

**A rövid alak feloldása kötött, nem ízlés kérdése:**

- a `key` **nem** rögzíti az `authority`-t: a `structural: [key]` tengelyt adja
  hozzá, az `authority` az övező surface-ből öröklődik (`config_surface` alatt
  `config`, `state_surface` alatt `operational`) — lásd a korrekciót lent;
- a `derived` és a `volatile` `authority`-ja `state`, mert mindkettő kizárja a
  `config`-ot (tehát az alapértelmezés nem alkalmazható rájuk), a `role.yaml`
  mindkettőt `config false` / GET-only alakra képezi, és a korpuszban mindkettő
  `state_surface`-en áll. Aki `operational`-t akar velük, hosszú alakot ír;
- a `reference` `authority`-ja **nem** vezethető le — ezért a `role: reference`
  rövid alak **tilos**, hosszú alakot kell írni.

> **Korrekció (a fanout mérése).** Korábban azt írtam ide, hogy a `derived`,
> `volatile` és `reference` **nulla** korpusz-példánnyal rendelkezik. Ez két
> kompozíció mérésén alapult, és a `derived`/`volatile` esetében **téves**: a
> `cic-network` `schemas/examples/network-interface.yaml`-ja mindkettőt rövid
> alakban írja, pontosan a `role.yaml` saját példáival (`effective_state`,
> `last_seen`). A grammatika első változata ezért elutasította volna egy létező,
> helyes kompozíciót. A `reference`-re az állítás továbbra is áll: 0 előfordulás.

> **Korrekció (a `key` `authority`-ja, cic-primitive-engine review útján
> elkapva).** Ez a bekezdés korábban azt állította, hogy a `key` `authority`-ja
> mindig `config`, "mert a lista kulcsát a management plane adja meg
> létrehozáskor." A `check_grammar.py` saját, már korábban javított kódja (és
> `check_role_algebra`'s "No authority constraint" kommentje) ennek az
> ellenkezőjét mondja ki, és egy konkrét korpusz-hibát is megnevez okként:
> `container_statuses[].name` egy olyan lista kulcsa, amit az adapter FIGYEL
> MEG, nem a kérő ad meg — a kulcs a megfigyelés része, nem egy kívánt állapot.
> Ha a `key` `authority`-ja mindig `config` lenne, ez a korpusz-eset
> hibásan elutasításra kerülne. A kód ezt már korrigálta (surface-derivált
> authority); ez a bekezdés csak most követi.

### 3.2 Az érvényes kombinációk

| Szabály | Indok |
|---|---|
| `authority` pontosan egy — kihagyva `config` | egy mező vagy kívánt állapot, vagy megfigyelt, vagy számított; a három kizárja egymást |
| `derived` **kizárja** a `config`-ot | számított értéket nem lehet kívánt állapotként beállítani |
| `volatile` **kizárja** a `config`-ot | nem perzisztens értéknek nincs kívánt állapota |
| `key`-re **nincs `authority`-megkötés** | a kulcs az övező surface authority-ját veszi fel (`check_role_algebra`: "No authority constraint") — egy `state_surface`-en megfigyelt lista kulcsa (pl. `container_statuses[].name`) is `key`, de nem `config` |
| `key` **megköveteli** a `mandatory`-t | kulcs nem hiányozhat |
| `key` **csak** `item_key`-ben megnevezett/egyetlen-kulcsos `item_fields` mezőn, VAGY egy Address `key_fields` elemén | máshol nincs mit azonosítania. (Ez a sor korábban `collection.key_fields`-et mondott — a §2.3 döntés, ami az `item_key` nevet választotta pont azért, hogy ne ütközzön a §2.7-ben formalizált Address `key_fields`-szel, itt nem lett átvezetve. Javítva, amikor a §2.7 megszületett.) |
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
| **C8** | minden listának van kulcsa; összetett kulcsnál `item_key` kötelező, és minden eleme `role: key`-es `item_fields` elem. `item_choice` esetén ugyanez a szabály case-enként, függetlenül fut | §2.3 |
| **C9** | `semantic_type: cic-reference` ⇔ `reference_target` | egyik sem állhat a másik nélkül |
| **C10** | `reference_target` MUST `{namespace}:{Kind}` alakú legyen, és a `{namespace}` MUST `cic:`-vel kezdődjön | §2.4 |
| **C16** | Address `key_fields` minden eleme MUST `role: key`-t hordozzon explicit | §2.7 — nincs "levezetés", mert nincs nem-kulcs elem, amitől meg kéne különböztetni |
| **C17** | `choice`/`item_choice` két case-e MUST NOT azonos nevű legyen; `item_choice` két case-e MUST NOT azonos kulcs-mezőhalmazra oldódjon fel | §2.3 — külső review találta: a `cases` nem `NODE_CONTAINER`, tehát C15 sosem nézett bele; a kulcs-ütközés ellenőrzés szükséges, de nem elégséges feltétele annak, hogy a case-ek kölcsönösen kizárják egymást (lásd §2.3 "Amit ez MÉG mindig nem old meg") |

(C11–C15 a kódban léteznek — `check_role_algebra`/`check_default_against_role`/
`check_role_against_surface`/`check_duplicate_names` — de sosem kerültek be
ebbe a táblázatba. Nem ez a szál pótolja őket; a C16-ot azért a valódi
következő szabad szám alá vettem fel, nem C11 alá, hogy ne ütközzön velük.)

### `derivation_chain` — lezárva: schema-provenance, nem domain-object szemantika (cic-primitives#6)

Három `DomainComposition` séma (`cic-schema-registry` `storage-resource`,
`compute-resource`, `network-interface`) hordoz egy `derivation_chain`
blokkot, mindhárom UGYANAZZAL a hármas struktúrával: `yang` (a séma
YANG-modul-alakja, `status: specification-only` — dokumentáció, nem
futtatott), `restconf` (a kanonikus REST végpontok), `runtime` (a
reconcile-loop szabad szöveges leírása). A kernel bundle-ben NINCS
`derivation`/`provenance`-alakú atom — az egyetlen `provenance:` kulcs a
bundle saját release-signing metaadata, más fogalom.

**A kérdés:** ez a domain-object SÉMA RÉSZE-e (amit egy specializációnak
explicit restate-elnie/szűkítenie kellene, mint bármelyik surface-öt), vagy
a séma-provenance dokumentálása (hogyan realizálódik a séma más
rétegekben) — ami inkább KOMPONÁLANDÓ (bázis realizáció + provider-
specifikus realizáció), nem örökölt mezőlista.

**Válasz: séma-provenance, nem domain-object szemantika.** Indoklás:

1. Mindhárom előfordulás arról szól, HOGYAN van a séma LEKÉPEZVE egy
   technológiai rétegre (YANG/RESTCONF/futásidejű viselkedés) — egyik
   sem "amit egy kliens beállíthat", ellentétben a config_surface bármely
   mezőjével.
2. NEM univerzális minta: a session során létrehozott újabb domain-
   objektumok (`kubernetes-cluster`, `dhcp-service`, `network-space`,
   `subnet`, `dhcp-options`) egyike sem hordoz `derivation_chain`-t — ez
   egy opcionális dokumentációs blokk a YANG-eredetű sémákon, nem egy
   kötelező surface, amit minden domain-objektumnak explicit
   restate-elnie kellene.
3. `tools/registrylib/coverage.py`'s `_NODE_LIST_KEYS` (cic-schema-
   registry) MÁR MOST nem ellenőrzi (`config_surface`/`state_surface`/
   `operation_surface`/`notification_surface`-re korlátozódik) — ez a
   viselkedés a fenti indoklás mellett HELYES, nem vakfolt, csak eddig
   nem volt kimondva, hogy SZÁNDÉKOS.

**Következmény:** `derivation_chain` marad KÍVÜL a Shape/Access primitíveken
— nem erőltetjük bele a `config_surface`-stílusú explicit-restatement
modellbe, nincs rá szükség formális Shape/Role/Contract tipizálásra.

**Megfigyelés, NEM eldöntött kérdés:** a `StorageResourceOracleCloud`
`spec.provider_resources` mezője (`[core.Volume, core.VolumeAttachment,
monitoring.Metric]`) ugyanazt a kérdést válaszolja meg, mint
`derivation_chain.restconf` — "milyen valós rendszer-objektumok ellen
realizálódik ez" —, csak PROVIDER-SPECIFIKUS szinten, a kanonikus szint
helyett. A két mező fogalmilag rokon, de ma szerkezetileg elkülönített és
NINCS egyesítve — a pontos forma (közös struktúra, elnevezés, hova
kerüljön egy specializáción) külön tervezést igényelne, ha valaha egy
második provider-specializáció ezt ténylegesen indokolja. Nem ez a szál
dönti el.

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

**Kapuként** (ez fut a `make validate` előtt):

```bash
make grammar          # self-test, majd a repo kompozíciói
make validate         # a grammar az előfeltétele
```

**Közvetlenül**, konténer nélkül — ez a fontosabb futtatási mód:

```bash
python3 proposals/atom-grammar/check_grammar.py --self-test
python3 proposals/atom-grammar/check_grammar.py schemas/examples/kubernetes-pod.yaml
```

A `check_grammar.py` **PyYAML + jsonschema**, konténer nélkül fut, mert egy
grammatika, amit csak a saját pipeline-ja tud futtatni, nem ellenőrizhető
harmadik fél által. Többdokumentumos (`---`) bemenetre is felkészült, és
szintaktikailag hibás YAML-on leletet ad, nem tracebacket — a repo saját
negatív fixture-jei ilyenek.

**A kapu vakfoltja ellen:** a `check_grammar.py --self-test` szándékosan hibás
példányokat futtat át, és elhasal, ha bármelyiket átengedi. Egy validátor,
amiről nem mérted le, hogy tud bukni, nem validátor.
