# A primitív modell — miért létezik ez a réteg

## A probléma

Minden kezelt infrastruktúra objektumot — Kubernetes Pod, hálózati interfész,
adatbázis példány — le kell valahol írni: milyen mezői vannak, milyen műveletek
hajthatók rajta végre, miben tér el a kívánt állapot a mért állapottól.

Közös alap nélkül minden domain kitalálja a saját sémanyelvet. Eredmény:

- 50 domain repo, 50 inkompatibilis sémaformátum ugyanazokra a szemantikai
  fogalmakra
- a "config" mást jelent minden repóban
- a validációs logika copy-paste-elve csendben eltér
- nincs gépileg ellenőrizhető contract a séma és a felhasználói között

A primitív modell ezt akadályozza meg.

---

## Mi egy primitív?

Primitív = **irreducibilis szemantikai atom** — ami nem bontható tovább
anélkül, hogy infrastruktúra-menedzsment szemantikát veszítene.

Pontosan 8 atomi primitív van:

| Atom | Mit ragad meg |
|---|---|
| **Shape** | Adat struktúra — milyen mezők, milyen típusok |
| **Role** | Menedzsment szemantika — config? state? kulcs? referencia? |
| **Behavior** | Milyen műveletek hajthatók végre |
| **Contract** | Milyen kényszerfeltételeknek kell teljesülnie |
| **Address** | Hogyan érhető el az entitás |
| **Identity** | Mi az (típusazonosság, nem példányazonosság) |
| **Event** | Milyen aszinkron jelzéseket tud kibocsátani |
| **Access** | Ki olvashatja, ki írhatja — cert-alapú identity (D-011) |

Ezek nem YANG fogalmak, nem RESTCONF fogalmak — ezek az a szemantikai réteg,
amely *alatt* minden konkrét sémanyelv van.

---

## Két szint

```
atomi primitív   = irreducibilis szemantikai atom
                   → séma fragment generálható belőle

aggregate primitív = szemantikai kompozíció sealed/defaulted/required slotokkal
                   → ez a tényleges tervezési egység
```

Soha nem atomból indulunk. Aggregate-ből indulunk.

```
ManagedEntity =
  Identity + ConfigSurface + StateSurface +
  OperationSurface + NotificationSurface +
  CapabilitySurface + LifecycleSurface + BindingSurface
```

Egy domain objektum (KubernetesPod, NetworkInterface, DatabaseInstance) a
ManagedEntity **specializációja** — soha nem új találmány.

---

## A slot contract

Minden aggregate explicit módon definiálja a slotjait:

| Mód | Jelentés |
|---|---|
| `sealed` | Rögzített az aggregate-ben — domain specializáció nem írhatja felül |
| `defaulted` | Van alapértelmezése — domain specializáció felülírhatja |
| `required` | Kötelezően ki kell tölteni minden domain specializációban |

Ezt a `compiler.py` minden `make validate` futtatáskor gépileg ellenőrzi.

---

## A kompozíciós mechanizmus

Az öröklődés nem YAML override szabályok. Hanem git:

```
base-repo
  └─[remote: base]─► cic-primitives
                          └─[remote: base]─► domain repók
```

Egy domain repo a `cic-primitives@v0.1.0`-t git remote-ként mergeli.
A fájlstruktúra *maga* az interface contract. Merge konfliktus = sémasértés.

---

## A három kérdés

Minden primitív csak akkor lezárt, ha mindhárom megválaszolható:

1. **Ebből hogyan lesz YAML séma?** → `make validate` zöld
2. **Ebből hogyan lesz API?** → `derivation_chain.restconf` dokumentált
3. **Ebből hogyan lesz runtime viselkedés?** → `derivation_chain.runtime` dokumentált

Teljes példa: `schemas/examples/kubernetes-pod.yaml`
