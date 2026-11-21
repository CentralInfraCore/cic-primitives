# Release sémakészlet: állapot a D1 után és a nyitott döntési pontok

Az angol változat (`docs/en/RELEASE-SCHEMA-OPEN-POINTS.md`) a normatív forrás; ez az összefoglaló. Állapot: 2026-11-21. A sémák státusza: **DRAFT**.

**A grammatikai megfelelés bizonyítása nem azonos a szemantikai teljesség bizonyításával.**

| Tétel | Státusz |
|---|---|
| D1 (node-név grammatika) | **LEZÁRVA**: a komponált sémák V2 alatt 0, V1 alatt pontosan a 3 `createdBy` találatot adják |
| P1 a `pattern` regex-íze | **NYITOTT**: mérve, a 7 különböző minta mind elfogad egy záró sortörést Python `re.search` alatt |
| P2 a `must` kifejezés dialektusa | **NYITOTT** (placeholder) |
| P4 `timestamp` minta és `format: date-time` | **NYITOTT**: a minta csak alakot ellenőriz (a 13-as hónap illeszkedik) |
| P7 reason a 2^53-1 feletti egészre | **NYITOTT**: most `value_type_unsupported` |
| Forms #167 felületi `validation` | **NYITOTT**: sem kiértékelve, sem listázva |
| A sémák | **DRAFT**, bájtra változatlanok |

**Javasolt lezárási sorrend:** (1) #167 láthatóság és P7, kicsi, független tulajdonosi döntések; (2) P1, a #41 gépezetével (verziózott profil, vektorok); (3) P4 a P1 után; (4) P2 utoljára, mert a kiértékelő kijelöléséhez a #167 válasza kell; (5) véglegesítő PR csak mind az öt lezárása után.

Részletek (mi a nem eldöntött, mitől függ, mit blokkol, ajánlás) és a véglegesítési kritériumok az angol dokumentumban. Az ajánlás nem döntés.
