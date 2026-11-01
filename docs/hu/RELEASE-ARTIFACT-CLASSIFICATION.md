# Release artifact-lista: a cic-primitives fájljainak osztályozása (javaslat)

Állapot: **review-tábla, nem döntés.** Semmi nem kerül a `project.yaml`-ba, és semmi nem mergelődik listaként; a tartalmat a tulajdonos hagyja jóvá a felmérés után. Addig a repó valódi release-útja `declaration_missing`-gel áll meg. A compiler-változástól (cic-primitives #26) különálló munka. Az angol változat (`docs/en/RELEASE-ARTIFACT-CLASSIFICATION.md`) a teljes tábla; ez az összefoglaló.

* **Szabály:** egy fájl akkor kerül a listába, ha a tartalma a kiadott primitive-csomag **szerződését, értelmezését vagy reprodukálhatóságát** határozza meg. Nem „minden YAML”, és nem egy fogyasztó fájlkészlete. Ahol a szabály nem dönt, a fájl `REVIEW` a kérdéssel együtt.
* **A Forms 12 fájlja ellenőrzött részhalmaz**, nem a kritérium. Mind a 12 benne van a javaslatban, ez következmény.
* **Darabszám** (a `devel` `d2d8ec7` állapotán, 131 követett fájl): **INCLUDE 29**, **REVIEW 10**, **EXCLUDE 92**.
* **INCLUDE:** a 13 séma (atomic és aggregate), a `schemas/index.yaml`, az `md.meta.schema.yaml`, a `release.schema.yaml`, a grammar (`check_grammar.py`, séma, `access_policy.py`, a négy access-vektor), a grammar README, a két P0-4 dokumentum, a `LICENSE.md`, a `dependency.yaml`, a record-szerződés angol szövege.
* **REVIEW (tulajdonosi igen/nem):** `LICENSE.meta.yaml`, `LICENSE.yaml`, `project.schema.yaml`, `project.yaml`, `proposals/atom-grammar/check_access_vectors.py`, `requirements.in`, `requirements.txt`, `schemas/examples/kubernetes-pod.yaml`, `tools/compiler.py`, `tools/release_record_conformance.py`.
* **EXCLUDE:** tesztek, CI és konfiguráció, belső jegyzetek és tervek (`ai/`, `features/`), munkaanyag (`p0-4-contradiction-matrix.md`), a hibás példák, a korábbi release-rekord, a release-folyamat eszközei, a `commitment.yaml` (tartalma már a rekordban van).
* **Pin és devel:** a pin (`73ae469`) a `devel` őse; a 12-ből 11 bájtra azonos a `devel` fején, a `P0-4-MIGRATION.md` eltér. A listába vétel nem teszi azonossá: a Forms-pinnek megfelelő release a pin blobjait tartalmazó forráscommitból vágandó (a 2026-11-01-i döntés).
* **Nem tesz:** nem olvas fogyasztói pint; a lista explicit (új fájl addig nincs benne, amíg fel nem veszik); egy `specs ⊆ artifacts` termelői konzisztencia-ellenőrzés javaslat, nincs megvalósítva; a lista jóváhagyása nem release-engedély.
