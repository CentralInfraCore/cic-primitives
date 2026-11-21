# Release sémakészlet: állapot a D1 után és a nyitott döntési pontok

Az angol változat (`docs/en/RELEASE-SCHEMA-OPEN-POINTS.md`) a normatív forrás; ez az összefoglaló. Állapot: 2026-11-21. A sémák státusza: **DRAFT**.

**A grammatikai megfelelés bizonyítása nem azonos a szemantikai teljesség bizonyításával.**

| Tétel | Státusz |
|---|---|
| D1 (node-név grammatika) | **LEZÁRVA**: a komponált sémák V2 alatt 0, V1 alatt pontosan a 3 `createdBy` találatot adják |
| P1 a `pattern` regex-íze | **NYITOTT**: mérve, a 7 különböző minta mind elfogad egy záró sortörést Python `re.search` alatt |
| P2 a `must` kifejezés dialektusa | **NYITOTT** (placeholder) |
| P4 `timestamp` minta és `format: date-time` | **NYITOTT**: a minta csak alakot ellenőriz (a 13-as hónap illeszkedik) |
| P7 reason a 2^53-1 feletti egészre | **DÖNTVE** (tulajdonos, 2026-11-21): `integer_out_of_range`, tartomány -(2^53-1) .. +(2^53-1), producer és önállóan a verifier, teljes értékfa (opaque is), H változatlan; implementáció nincs |
| Forms #167 felületi `validation` láthatósága | **LEZÁRVA** (cic-primitive-forms #168): `unevaluated_surface_contracts`-ban listázva |
| Forms #167 felületi `validation` kiértékelése | **NYITOTT**, P2-függő |
| A sémák | **DRAFT**, bájtra változatlanok |

**Javasolt lezárási sorrend:** (1) kész: #167 láthatóság (#168) és P7 döntés; (2) P1, a #41 gépezetével (verziózott profil, vektorok); (3) P4 a P1 után; (4) P2 utoljára, mert a kiértékelő kijelöléséhez a #167 válasza kell; (5) véglegesítő PR csak a P1, P2, P4 döntése és a #167 kiértékelés kérdésének rendezése után.

Részletek (mi a nem eldöntött, mitől függ, mit blokkol, ajánlás) és a véglegesítési kritériumok az angol dokumentumban. Az ajánlás nem döntés.
