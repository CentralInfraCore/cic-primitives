# AI Karbantartási Kontraktus / AI Maintenance Contract

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

---
---

# AI Maintenance Contract — English

The AI operations handbook for the `cic-primitives` repo.

---

## Boot sequence (mandatory at the start of every session)

1. `mcp__cic-graph__kb_status` — is the KB fresh and available?
2. `ai/SYSTEM_CONTEXT.md` — full architectural context
3. `ai/PROMPTMAP.yaml` — what is the next concrete task?
4. `ai/DECISIONS.md` — read the relevant decisions

Until these four points are done, do not make factual claims about the repo state.

---

## What you can modify independently

- `schemas/atomic/*.yaml` — if `make validate` stays green
- `schemas/aggregate/*.yaml` — if `make validate` stays green
- `schemas/examples/*.yaml` — adding valid domain examples
- `ai/PROMPTMAP.yaml` — task status updates (pending → done)
- `ai/SYSTEM_CONTEXT.md` — state sync after a completed Phase

---

## What you MUST NOT modify without a decision

| Area | Why it is forbidden |
|---|---|
| `schemas/index.yaml` spec structure | meta-schema contract — can break all validation |
| Any slot `mode:` value in an aggregate | breaks downstream repos (D-005) |
| `tools/compiler.py` validation logic | D-008 — requires a design decision |
| `dependency.yaml` content | D-007 — pinned tags only, branches forbidden |
| `.github/workflows/` | comes from base-repo, do not modify |
| Existing decisions in `ai/DECISIONS.md` | decision history — deleting/overwriting is forbidden |

---

## When a `ai/DECISIONS.md` entry is required

- Changing a slot `mode:` (sealed/defaulted/required)
- Introducing a new aggregate primitive
- Touching the composition mechanism (D-001)
- Changing `compiler.py` validation logic (D-008)
- Finalizing any `TBD` type

## When updating only `PROMPTMAP.yaml` is sufficient

- Task status update (pending → in_progress → done)
- Adding a new task under an existing milestone
- Refining acceptance criteria

---

## Committing without validation is FORBIDDEN

```bash
make validate
```

If not green: do not commit. No exceptions.

---

## Status semantics

| Status | Meaning | Evidence |
|---|---|---|
| `defined` | YAML schema exists, `make validate` is green | file + green CI |
| `draft` | Design is written, schema does not exist yet | DECISIONS.md entry |
| `concept` | Discussed, not formally recorded | discussion / thread |

If you cannot back it up at the file level: do not call it `defined`.

---

## Most common mistakes

| Mistake | Consequence | Prevention |
|---|---|---|
| Overriding a sealed slot in DomainComposition | compiler.py catches it, but schema is inconsistent | Read D-005 |
| Committing without `make validate` | hidden schema breakage | hook + discipline |
| Introducing a new concept instead of using an existing one | fragmented model | D-003: 8 atoms are final |
| Starting from a domain object (Pod, Switch) | designing an instance instead of an aggregate | D-002 |
| Filling in a `TBD` type without a decision | D-008 merge strategy is open | ask first |

---

## Design-change workflow

1. Identify the relevant decision (`ai/DECISIONS.md`)
2. Articulate what would change and what would break
3. Request confirmation — do not proceed without it
4. Modify the schema
5. `make validate` — green?
6. PROMPTMAP task → done
7. Update `ai/DECISIONS.md` if a new decision was made

---

## Valid / invalid examples

Reference files, not to be validated:

```
schemas/examples/          valid domain compositions (make validate checks these)
schemas/examples/invalid/  intentionally invalid files — counterexamples
```

The compiler excludes files in the `invalid/` directory from validation.
Every invalid file contains a `why_invalid:` explanation.
