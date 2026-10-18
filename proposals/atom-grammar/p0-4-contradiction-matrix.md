# P0.4 — Access: ellentmondásmátrix (cic-primitives #17)

Állapot: **munkaanyag, nem normatív**. A #17 normatív lezárásának első lépése: mi van ma
deklarálva, mi van leírva, mi fordul elő a valós korpuszban, és mi a javasolt szabály.
Alap: `devel` (`5a26bd8`). A `main` és a `devel` között a releváns fájlokban
(`access.yaml`, `policy-surface.yaml`) **nincs eltérés**; eltérés csak a `managed-entity.yaml`
Address-leírásában (D-016) és a `DECISIONS.md`-ben van, ezek nem érintik az Access nyelvtant.
Az archivált `cic-object-model` SPEC §6.4 történeti forrás, nem elfogadott szerződés.

## Korpusz-mérés (cic-schema-registry, 21 aktuális séma + 33 verziózott példány)

| Minta | Előfordulás | Megjegyzés |
|---|---|---|
| mezőszintű `inherit:` kulcs értékkel | 0 | csak az `access.yaml` leírásában és egy objektummodell-fixture-ben él |
| mezőszintű `default_injection:` | 0 | ugyanígy |
| `inherit_policy: true` | 33 (verziózott) / 9 (aktuális) | az egyetlen valós használat; `false` és `0` **soha** |
| `policy_surface.surface_rules[].access/modify` | 9 / 18 lista | mindig `CertPattern` lista; szimbolikus `inherit` **soha**, üres lista **soha** |
| `access:` mint `conformance` hordozó | 1 sémában + a 3 OracleCloud specializációban (D-014) | nem jogosultsági használat |

Következmény: a `false` / `0` megkülönböztetésére és a mezőszintű `inherit` kulcsra **nincs
korpuszbizonyíték**. Bármely döntés tervezési döntés, nem mért szabály — ezt a normatív szövegben ki kell mondani.

## Mátrix

| # | Elem | Deklarált típus | Deklarált alapérték | Dokumentált viselkedés | Valós használat | Javasolt normatív szabály |
|---|---|---|---|---|---|---|
| 1 | `Access.access` | `list<CertPattern>` | `inherit` | üres lista = senki; alapérték = szülő PolicySurface szabálya | csak PolicySurface szintjén, listaként | típus: `list<CertPattern> \| inherit`; `[]` ≠ `inherit` ≠ hiányzó ≠ `null`; `[inherit]` érvénytelen CertPattern |
| 2 | `Access.modify` | `list<CertPattern>` | `inherit` | mint 1.; adapter cert state/operational mezőn | mint 1. | mint 1. |
| 3 | `Access.inherit` | `boolean \| 0` | `true` | `true` örököl; `false` nem örököl, saját default; `0` teljes reset | 0 | fogalmi típus `InheritanceMode`; a YAML-leképezés verziózott és típus-szigorú (lent) |
| 4 | `PolicySurface.inherit_policy` | `boolean` | `true` | leírása `0`-t is definiál | `true` ×33 | ugyanaz az `InheritanceMode`, de **objektum-hatókörben**; a `boolean` deklaráció javítandó |
| 5 | `Access.default_injection` | `any` | `null` | `null` = mező nem látszik; érték = beinjektált | 0 | külön marad a hozzáférési döntéstől; nem része az `InheritanceMode`-nak |
| 6 | `Access.conformance` | `enum` | `implemented` | eszköz-szintű státusz, D-012; a README szerint kilóg az Accessből | 5 mező (D-014) | tulajdonjoga külön döntés (ADR-0010 szerint származása nem íráson át); a hatmezős alakból **nem** vesszük ki hallgatólagosan |
| 7 | rövid/hosszú alak | — | — | `key: value` ↔ hatkulcsos hosszú alak (D-010/D-011) | rövid: minden | felismerés sémavezérelt, kulcshalmaz alapján (forms ADR-0001), nem heurisztika; részleges hosszú alak nem policy override |
| 8 | rövid alak kibontása | — | — | "fills in inherited rules" (`access.yaml`) | — | kibontás **szimbolikus** defaultokat ad (`inherit`, `inherit`, `true`, `null`, `implemented`), effektív jogosultságot nem |
| 9 | kiértékelési sorrend | — | — | mező-Access > `surface_rules` > `default_*` > szülő PolicySurface (ha `inherit_policy`) | — | rögzített, de csak P3-ban kiértékelt; a nyelvtan nem függ tőle |
| 10 | `default_access` / `default_modify` | `CertPattern[]` | `open` / `owner` | `open`, `owner` literálok | `open`, `owner` | **új ellentmondás**: a deklarált típus lista, az alapérték szimbolikus szó — ugyanaz a minta, mint az 1. sorban; ugyanazzal a unióval kezelendő |

## Új leletek a #17 szövegéhez képest

- A 10. sor a #17-ben és az ADR-0004-ben még nem szerepel: `default_access: open` és `default_modify: owner` szintén szimbólum egy `CertPattern[]` típusú kulcsban.
- A korpuszban a `surface_rules` bejegyzések `access`/`modify` listái sosem üresek és sosem szimbolikusak, tehát az `[]` ≠ `inherit` szabálynak ma nincs valós előfordulása.
- SPEC §6.4 (archivált) a `read`/`modify` műveleteket külön `inherit`-tel látta el és a feloldást szándékosan nem definiálta (INV-037, három nyitott kérdés). Ez a hatmezős Access-szal **nem azonos** alak; nem átvehető.

## Következő lépés

A 3–4. sor `false` vs `0` megkülönböztetése és a verziózott YAML-leképezés (`true`→`inherit`, `false`→`no-inherit`, `0`→`reset`) kidolgozása.
