# Konszolidált séma-registry — tervezet

**Státusz:** `implemented (részleges)` — a `cic-schema-registry` repó valóban
létrejött (`github.com/CentralInfraCore/cic-schema-registry`), a `tools/
registrylib` mechanizmus (§4) valós teszttel fedve, és a `cic-primitives`
kernel (§3.1) valódi, aláírt tartalommal migrálva. A domain-repók (compute,
storage, kubernetes, yang) tartalma MÉG NINCS migrálva. Ez a dokumentum nem
kapu, nem hivatkozik rá `make validate` — a tényleges állapotot a
`cic-schema-registry` repó saját `CLAUDE.md`-je ("Jelenlegi, valódi állapot")
mondja ki.
**Készült:** 2026-09-09, orchestrátori beszélgetésből, folyamatosan frissítve.
**Kiváltó ok:** a `primitives-group` öt domain-repójának (`cic-network`,
`cic-compute`, `cic-kubernetes`, `cic-storage`, `cic-yang`) és a `CIC-Schemas`
repónak az auditja során mért tény: egy `cic-storage`-szerű repó **97 trackelt
fájlt** hordoz, amiből **1 db (386 sor)** a tényleges, domain-specifikus
tartalom — a többi mind ismétlődő scaffold (Makefile, `mk/`, `tools/`,
Dockerfile, CI, docs, license). Ez a scaffold **6 repóban 6x létezik**,
egymástól függetlenül tud driftelni — ami ténylegesen meg is történt: 3 az 5
domain-repó közül hónapokig `project.yaml: name: cic-primitives`-t hordozott
(sosem lett testreszabítva), és a valódi, kész domain-munka (`StorageResource`,
`KubernetesCluster` + adapterek, IETF YANG-fragmentek) **soha nem lett
mergelve** a domain-repók `devel` ágára — egy párhuzamos, `<domain>/main`
nevű ágon élt, észrevétlenül.

---

## 1. Mit nem old meg ez a dokumentum

Nem dönt a `tools/compiler.py` (`cic-primitives`) vs. `base-repo`
`ReleaseManager` divergenciáról — az külön, korábban lezárt kérdés (nem
egyeztetendő, lásd a `cic-primitives` architektúra-döntését). Nem foglalkozik
azzal, hogy a WASM provider-modulok (`cic-module-oracle-cloud` és jövőbeli
társai) kódja hova kerül — az a kódjuk, nem a séma-leírásuk, marad a saját
repójukban.

---

## 2. Repó-modell

Egy **új, konszolidált séma-registry repó leváltja** a jelenlegi hat
séma-hordozó repót (`cic-network`, `cic-compute`, `cic-kubernetes`,
`cic-storage`, `cic-yang`, `CIC-Schemas`). A régi repók **archiválásra**
kerülnek — de csak azután, hogy a tartalmuk (séma-leírások) igazoltan átkerült
az új registry-be. A kód (adapter-implementációk, WASM modulok) NEM ebbe a
repóba kerül, marad a saját repójában.

A tooling (validate/sign) **egyszer**, az új repóban él — ez szünteti meg a
6x-ös scaffold-duplikációt.

---

## 3. Könyvtárszerkezet — három réteg

```
general/<domain>/<schema-name>/
standards/<forrás>/<schema-name>/
providers/<szolgáltató>/<schema-name>/
```

| Réteg | Mit jelent | Példa a ma megismert valós tartalomból |
|---|---|---|
| `general/` | Provider-független, absztrakt fogalom — MIT akarunk | `general/storage/storage-resource/`, `general/compute/compute-resource/`, `general/primitives/atomic/shape/` |
| `standards/` | Külső szabvány/kvázi-szabvány szerinti séma | `standards/yang/ietf-interfaces-base/`, `standards/postgresql/postgresql-conf/` |
| `providers/` | Konkrét szolgáltató/implementáció leképezése | `providers/oracle-cloud/object-storage-bucket/` |

A YANG-alapú tartalom (`cic-yang`) tudatosan a `standards/` rétegbe kerül —
sem nem "general" (egy valós külső szabványra épül, nem CIC-saját absztrakció),
sem nem "provider" (nem egy konkrét szolgáltató saját API-ja).

Minden séma **saját könyvtárat** kap, a könyvtár neve a kanonikus,
kereshető azonosító:

```
general/storage/storage-resource/
  README.md                                    # egy, folyamatosan frissülő emberi doksi
  storage-resource.v1.0.0-src2026.yaml
  storage-resource.v1.0.0-src2027.yaml         # újra-aláírva, TARTALOM változatlan
  storage-resource.v1.1.0-src2027.yaml         # valódi tartalmi verzió-lépés
```

Nincs külön index/katalógus fájl — a könyvtárlistázás maga a keresés.
`README.md` **nem verziónkénti**: a fogalom teljes történetét/indoklását
hordozza, git-history-val, nem kriptográfiailag hitelesített kontraktus.

### Fájlnév-konvenció

`<schema-name>.vMAJOR.MINOR.PATCH-src<év>.yaml`

- `vMAJOR.MINOR.PATCH` — tartalmi verzió (semver)
- `-src<év>` — az aláíró root CA évjárata (lásd §6) — NEM tartalmi élettartam

---

### 3.1 Kernel vs. laza-kapcsolt tartalom — mikor egy bundle-fájl, mikor sok

**Kiváltó hiba:** az első migrációs kísérlet a `cic-primitives` release-t
13 külön fájlra bontotta (`general/primitives/atomic/shape/`, `.../
aggregate/managed-entity/`, stb.) — ezt vissza kellett vonni (lásd
`cic-schema-registry` PR #2/#3 revert + PR #6). Utána a `cic-compute` és
`cic-storage` release bundle-jét is megnézve kiderült: **egyik forrás-repó
release bundle-je sem hordoz domain-tudatos szemantikát** — a compiler
tooling minden repóban ugyanazt a generikus `kind: PrimitiveRelease`
wrappert adja ki, mechanikusan összecsomagolva bármit, ami a `schemas/`
alatt volt build-időben. A "release bundle" tehát ÖNMAGÁBAN nem support arra,
hogy eldöntsük, egy vagy több fájlként kerüljön-e be a registry-be — ezt a
BELSŐ hivatkozási mintából kell megállapítani, esetenként.

**A tényleges szabály — nézd meg, HOGYAN hivatkoznak egymásra a bundle
darabjai:**

| Hivatkozás típusa | Jel | Következmény | Példa |
|---|---|---|---|
| **Szoros, struktúrális** | típus-beágyazás `aggregate_ref`/`atomic_ref`-fel — a hivatkozó séma maga a hivatkozott típusból épül fel | Egy egybefüggő "kernel" — **egy bundle-fájl**, byte-azonos a valódi release-szel, itt nem szerkesztendő (a forrás-repó saját issue/PR folyamata a szerkesztés helye) | `cic-primitives`: `ManagedEntity` szó szerint `ConfigSurface`/`StateSurface`-ot ágyaz be `aggregate_ref`-fel → `general/primitives/cic-primitives/cic-primitives.v0.2.0-src2026.yaml` |
| **Laza, név-alapú** | egy string-mező (pl. `binding_surface.adapter: storage-adapter`) mutat egy másik dokumentumra, típus-beágyazás nélkül | Független dokumentumok — **külön fájl mindegyiknek** | `cic-compute`: `compute-resource.yaml` csak `provider` routing-kulccsal hivatkozik az adapterekre → 4 külön fájl (`compute-resource` + 3 adapter); `cic-storage`: `storage-resource.yaml` → `adapter: storage-adapter` → 2 külön fájl |

Ellenőrzési lépés minden jövőbeli migrációnál: nyisd meg a release bundle-t,
keresd meg a domain-specifikus specs között a kereszthivatkozásokat, és nézd
meg, típus-beágyazás-e vagy csak egy string. Ne feltételezd egyik irányt sem
alapértelmezésként.

**Nyitva maradt, nem eldöntött kérdés:** az `adapter-contract` taggel jelölt
fájlok (pl. `storage-adapter`, `cloud-provider-adapter`) a `general/<domain>/`
alá kerüljenek-e (mint eddig), vagy kapjanak egy külön, negyedik csoportot
(pl. `general/<domain>/adapters/`), megkülönböztetve a `domain-composition`
taggel jelölt fájloktól? Ezt még nem zártuk le.

---

## 4. Származtatás és felüldefiniálás

**Nincs új primitívre szükség.** A meglévő `Identity.base` (típus-öröklési
lánc, formátum `{namespace}:{Kind}`) és az `Access.conformance`
(`implemented`/`not_implemented`/`deprecated`, D-012) mechanizmus együtt
teljesen lefedi a problémát:

- `identity.base` explicit, PONTOS tartalmi verzióra pin-el:
  `base: "cic:storage:StorageResource@v1.0.0"` (a `-src` évet a feloldás
  automatikusan a legfrissebb érvényes aláírásra követi — lásd §8).
- **Kötelező teljes mező-lefedettség**: minden mező, ami a pin-elt szülő-
  verzióban létezik, a leszármazottban is meg kell jelenjen — vagy
  implementálva, vagy explicit `conformance: not_implemented` csonkként.
  Ha egy szülő-mező **hiányzik** a leszármazottból (se implementálva, se
  lezárva), az **compile-time hiba**.
- Ugyanez a mechanizmus (a compiler-diff kiterjesztve) érvényesíti a
  `reference_target`-et is (`cic-reference` szemantikus típus) — ez is
  explicit tartalmi verzióra pin-el, szimmetrikusan a `base`-szel.

Ez **kiterjeszti**, nem hatálytalanítja a `cic-primitives` D-001 döntését
("git remote = öröklődési lánc, nem YAML override rules") — az a döntés a
**repók közötti** származtatásra vonatkozott, ahol a git-merge kényszerítette
ki a konzisztenciát. Egy közös registry-repóban nincs mit merge-elni két fájl
között, ezért ott a fenti, tényleges compiler-ellenőrzés lép a helyébe.

### Verzió-evolúciós szabályok

| Eset | Ugyanazon MAJOR verzión belül | MAJOR verzió-váltáskor |
|---|---|---|
| Mező törlése | **Tilos** — csak `conformance: deprecated`, a mezőnév örökre foglalt marad, nem hasznosítható újra | Megengedett |
| Meglévő mező `shape_type`/`scalar_type`/`contract` módosítása helyben | **Tilos** — új mezőnév kell az új jelentésnek | Megengedett |
| Új mező hozzáadása | Megengedett, ha nem `mandatory`/`sealed` | Megengedett bármilyen módban |

---

## 5. Aláírási modell

**Nincs bundle, nincs release-esemény, nincs fájlok közötti csoportosítás.**
Minden fájl a saját, önálló, aláírt egysége — logikailag olyan, mintha minden
séma a saját repója lenne.

Ellenőrizve egy valós, kiadott release (`cic-storage-v0.1.2.yaml`, GHCR-ről
letöltve) tényleges szerkezetén: ott minden beágyazott séma kapott egy saját
`meta_hash`-t, de az aláírás (`release.sign`, Vault Transit ECDSA +
`cic_countersign`, CICSourceCA) a teljes bundle egyetlen `build_hash`-én
történt. Az új modellben ez a `meta_hash` **előlép a fájl saját
`build_hash`-évé**, és minden fájl **saját** `release`/`cic_countersign`
blokkot kap, közvetlenül a fájlban — nincs külön `release/*.yaml` bundle.

---

## 6. A `-src<év>` komponens — kriptográfiai horgony, nem tartalmi élettartam

A CIC Root CA **naptári évhez kötötten rotálódik** (ellenőrizve valós
tanúsítványokon):

```
rootCA2025:  notBefore = 2025-08-06   notAfter = 2026-08-06
rootCA2026:  notBefore = 2026-03-19   notAfter = 2026-12-31 23:59:59
```

A két CA kb. 5 hónapig egyszerre érvényes — ez ad ablakot az újra-aláírásra
a régi CA teljes lejárta előtt. A `-src<év>` a fájlnévben azt rögzíti,
**melyik évi CA írta alá** — ha a tartalom változatlan, de a CA lejár, egy
ÚJ fájl készül azonos tartalommal, új `-src` évvel (§3 táblázata szerint ez
nem számít tartalmi verzió-lépésnek).

---

## 7. Fejlesztési munkafolyamat

Nincs fájlonkénti branch. A meglévő git-flow (feature branch → PR → review →
merge → branch törlés) közvetlenül alkalmazható, csak az egység most "egy
séma egy új verziója", nem "egy kódváltoztatás":

```
issue: "storage-resource: v1.2.0 — replication_factor mező hozzáadása"
  → ideiglenes branch, egy célra
     → iterálás, make validate, review a PR-ban
     → merge a közös ágra
        → EZ a pillanat váltja ki: build_hash számítás + Vault-aláírás +
          CICSourceCA-ellenjegyzés, közvetlenül az új fájlba
     → branch törölve
```

A közös ág (`devel`/`main`) **sosem tartalmaz draftot** — a munkaközbeni
állapot kizárólag a még nem mergelt branch-en él, ami a referencia-feloldók
számára eleve láthatatlan.

---

## 8. Elévülés kezelése

Két, egymástól független elévülés-fogalom:

| Típus | Mit jelent | Sürgősség | Mechanizmus |
|---|---|---|---|
| **Tartalmi elévülés** | Egy pin sok verzióval le van maradva a legfrissebb elérhető tartalmi verziótól | Nem sürgős, csak láthatóság | Nem-blokkoló riport |
| **Kriptográfiai elévülés** | A pin-elt fájl mögötti root CA lejár (naptári határidő) | Sürgős, kemény határidős | Automatikus issue + PR |

**Mindkettőre ugyanaz a meglévő eszköz használható: Renovate** (már jelen van
az ökoszisztémában több `renovate.json` formájában, eddig csak sima
package-dependency-kre konfigurálva).

- Minden aláírt séma-fájl-verzió kap egy könnyű **git tag**-et is
  (`storage-resource@v1.0.0-src2026`) — ez Renovate beépített `git-tags`
  datasource-ának elég, semmilyen külön API/index szerver nem kell.
- Egy **custom manager** (regex-alapú) ismeri fel a `base:`/`reference_target:`
  mintát mint "dependency", és Renovate natívan nyitja a bump-PR-t, amikor
  újabb tag jelenik meg — akár tartalmi bump, akár újra-aláírási bump esetén.
- A kriptográfiai elévülés ÉSZLELÉSE (mikor kell egyáltalán újra-aláírni)
  külön, ütemezett job feladata, ami a legfrissebb `-src<év>` fájl mögötti CA
  `notAfter`-jét figyeli egy küszöb alatt (pl. 60 nap) — ez hozza létre az új
  `-src` fájlt és tag-et, amit utána Renovate már a megszokott útján terjeszt.

**Referencia-feloldás:** egy pin (`base: "...@v1.0.0"`) sosem hivatkozik
explicit `-src` évre — mindig a pin-elt tartalmi verzióhoz tartozó
LEGFRISSEBB, még érvényes aláírású fájlra oldódik fel automatikusan. Ez azt
jelenti, hogy egy tisztán kriptográfiai újra-aláírás sosem kényszerít bump-ot
egyetlen leszármazott pin-jén sem.

---

## 9. Nyitva maradt kérdés

A tartalmi elévülés-riport (`make check-staleness` vagy hasonló) pontos
formája és futási gyakorisága nincs eldöntve — nem blokkoló, később
pontosítható.

---

## 10. Migrációs sorrend — tényleges állapot

1. ✅ `cic-schema-registry` repó létrehozva (publikus), `base-repo`
   `schema-registry/main` flavor-ból bootstrap-olva.
2. ✅ `tools/registrylib` (base-chain coverage + verzió-evolúció) megírva,
   tesztelve — de a §3.1 bundle-eset (`_is_bundle`) csak explicit SKIP-et ad,
   a bundle `specs[]`-ébe való tényleges feloldás (pl.
   `cic:core:ManagedEntity@v0.2.0`) még nincs megírva.
3. ✅ `cic-primitives` kernel migrálva, §3.1 szerint EGY bundle-fájlként
   (`general/primitives/cic-primitives/cic-primitives.v0.2.0-src2026.yaml`).
4. ⏳ `cic-compute` (`ComputeResource` + 3 adapter) és `cic-storage`
   (`StorageResource` + `StorageAdapter`) migrálása §3.1 szerint, KÜLÖN
   fájlonként — a `cic-storage` esetében a valódi tartalom a `storage/main`/
   `storage/releases/v0.1.0` ágon van, sosem lett mergelve a `devel`-re,
   onnan kell hozni. Folyamatban.
5. ⏳ `cic-kubernetes` (`KubernetesCluster`+`KubernetesNode` + 5 adapter) és
   `cic-yang` (8 IETF YANG-fragment) migrálása — nincs elkezdve.
6. ⏳ Régi repók archiválása — csak a fentiek után.

A pontos ütemezés/becslés továbbra sincs rögzítve — ez a lista a haladást
követi, nem commitmentet ad határidőre.
