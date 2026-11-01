# A compiler envelope 3-at ír

A `python tools/compiler.py release` kizárólag **envelope 3** `PrimitiveRelease` rekordot ír (docs/en/RELEASE-RECORD-CONTRACT.md). Az envelope 1 és 2 rekordot nem ír többé, a meglévőket nem érinti: a `verify-release` változatlanul olvassa őket, a valódi `cic-primitives-v0.1.5.yaml` (envelope 1) és `cic-primitives-v0.2.0.yaml` (envelope 2) tesztesetek. Rekord átírása, újraaláírása vagy migrációja nincs.

* **`source_commit` kötelező** (`git rev-parse HEAD`, 40 kisbetűs hex); ha a git nem tud felelni, a compiler megáll, nem ír `null`-t.
* **A termelő deklarálja a közzétett fájlokat** a `project.yaml`-ban (`compiler_settings.release_artifacts.paths`, explicit útvonalak, glob/`include`/`exclude` nélkül). A deklarációt a **forráscommit**ból olvassa, az útvonalakat a commit **Git-fájából** oldja fel; nem a munkakönyvtárból, nem szűrt checkoutból, nem fogyasztói pin-manifestből. Könyvtár, link, submodule, abszolút útvonal, `..`/`.`, vezérlőkarakter, duplikátum, hiányzó útvonal, üres lista, ismeretlen kulcs: leáll az okkal, **még a Vault hívása előtt**.
* **`artifacts`:** útvonalanként `sha256:` + a blob bájtjainak SHA-256-ja, az útvonal UTF-8 bájtjai szerint rendezve, plusz `manifest_digest`. A `specs[].source_path` egyedi.
* **Aláírás:** a meglévő mechanizmus (`build_hash` a teljes csomagra, `release.sign`, külső `cic_countersign`); az `artifacts` és a `source_commit` ezért lefedett.
* **Nem a compiler igazolja magát:** a kimenetet a referencia-verifier olvassa vissza (nem importálják egymást), a 32 lefedettségi vektor a compiler rekordján is lefut, a deklarációs vektorok a compiler saját függvényén, és a #25 mércéje befagyasztott (`tests/test_conformance_frozen.py`). 58 planted defect a `tools/compiler.py`-ban.
* **`verify-release`:** elfogadja az envelope 3-at, és kimondja, hogy az artifact-lista ellenőrzése nem az ő dolga (`release_record_conformance.py`); a kettő különálló, egyik sem importálja a másikat.
* **Ellenjegyző szolgáltatás (csak olvasó vizsgálat):** a `cic-countersign` a `build_hash`-t átlátszatlan, kész digestként kapja és nem számolja újra; a `document` csak naplóhoz; az envelope-ból és az `artifacts`-ból semmit nem olvas. Nem módosítottam.
* **Deklaráció nélküli repó nem adhat ki release-t** (`declaration_missing`); a közzétett fájlok listája a termelő döntése, külön változásban.
