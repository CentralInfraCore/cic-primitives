# AI Maintenance Contract

A `cic-primitives` repo AI üzemeltetési kézikönyve.

---

## Boot sorrend (minden session elején kötelező)

1. `mcp__cic-graph__kb_status` — KB friss és elérhető?
2. `ai/SYSTEM_CONTEXT.md` — teljes architekturális kontextus
3. `ai/PROMPTMAP.yaml` — mi a következő konkrét task?
4. `ai/DECISIONS.md` — érintett döntések elolvasása

Amíg ez a négy pont nincs meg, ne tégy tényállításokat a repo állapotáról.

---

## Mit módosíthatsz önállóan

- `schemas/atomic/*.yaml` — ha `make validate` zöld marad
- `schemas/aggregate/*.yaml` — ha `make validate` zöld marad
- `schemas/examples/*.yaml` — valid domain példák hozzáadása
- `ai/PROMPTMAP.yaml` — task státusz frissítés (pending → done)
- `ai/SYSTEM_CONTEXT.md` — állapot szinkronizáció elvégzett Phase után

---

## Mit NEM módosíthatsz döntés nélkül

| Terület | Miért tiltott |
|---|---|
| `schemas/index.yaml` spec struktúrája | meta-schema contract — törhet minden validáció |
| Bármely slot `mode:` értéke aggregate-ben | downstream repókat töri (D-005) |
| `tools/compiler.py` validációs logika | D-008 — design döntés kell hozzá |
| `dependency.yaml` tartalma | D-007 — csak pinnelt tag, branch tiltott |
| `.github/workflows/` | base-repo-ból érkezett, ne módosítsd |
| `ai/DECISIONS.md` meglévő döntései | döntési history — törölni/felülírni tilos |

---

## Mikor kell `ai/DECISIONS.md`-be bejegyzés

- Slot `mode:` megváltoztatása (sealed/defaulted/required)
- Új aggregate primitive bevezetése
- Kompozíciós mechanizmus érintése (D-001)
- `compiler.py` validációs logikájának változtatása (D-008)
- Bármely `TBD` típus véglegesítése

## Mikor elég csak `PROMPTMAP.yaml`-t frissíteni

- Task státusz frissítés (pending → in_progress → done)
- Új task hozzáadása meglévő milestone alá
- Accept criteria pontosítása

---

## Validáció nélkül TILOS commitolni

```bash
make validate
```

Ha nem zöld: ne commitolj. Nincs kivétel.

---

## Státusz szemantika

| Státusz | Jelentés | Bizonyíték |
|---|---|---|
| `defined` | YAML séma létezik, `make validate` zöld | fájl + zöld CI |
| `draft` | Design megvan írásban, séma még nincs | DECISIONS.md bejegyzés |
| `concept` | Megbeszélt, formálisan nem rögzítve | megbeszélés / thread |

Ha nem tudod fájl-szinten alátámasztani: ne mondd `defined`-nak.

---

## A leggyakoribb hibák

| Hiba | Következmény | Megelőzés |
|---|---|---|
| Sealed slot felülírása DomainComposition-ben | compiler.py elkapja, de séma inkonzisztens | D-005 olvasása |
| `make validate` nélküli commit | rejtett séma törés | hook + fegyelem |
| Új fogalom bevezetése meglévő helyett | fragmentált modell | D-003: 8 atom végleges |
| Domain objektumból kiindulás (Pod, Switch) | aggregate helyett instance-t tervezel | D-002 |
| `TBD` típus döntés nélküli kitöltése | D-008 merge stratégia nyitott | megkérdezni |

---

## Design-change workflow

1. Azonosítsd az érintett döntést (`ai/DECISIONS.md`)
2. Fogalmazd meg mi változna és mi törne
3. Kérj megerősítést — ne lépj tovább nélküle
4. Módosítsd a sémát
5. `make validate` — zöld?
6. PROMPTMAP task → done
7. `ai/DECISIONS.md` frissítés ha új döntés született

---

## Érvényes / érvénytelen példák

Referenciaként, nem validálandó fájlok:

```
schemas/examples/          valid domain kompozíciók (make validate ellenőrzi)
schemas/examples/invalid/  szándékosan érvénytelen fájlok — counterexample-ök
```

Az `invalid/` könyvtár fájljait a compiler kizárja a validációból.
Minden invalid fájl tartalmaz `why_invalid:` magyarázatot.
