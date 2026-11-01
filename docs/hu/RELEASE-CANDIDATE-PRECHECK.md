# Release candidate előellenőrzés

A `tools/release_candidate_precheck.py` egy kérdésre válaszol a release elkészítése előtt és után: **tartalmazza-e a release azt a grammart, amelyet a fogyasztó pinelt?**

A fogyasztó (`cic-primitive-forms`, `corpus/pins.yaml`) egy commitot és pontosan tizenkét fájl nyers blob-bájtjainak SHA-256 értékét pineli. Egy receipt csak akkor nevezhet meg egy release-t, ha az bizonyíthatóan tartalmazza ezt a tizenkét fájlt. Az eszköz ezt git-objektumokból, a release után a release-rekordból bizonyítja vagy cáfolja. Csak olvas: nem ír alá, nem tagel, nem publikál, és **nem ellenőriz aláírást** (az a `python tools/compiler.py verify-release <rekord> --trust-root <root.pem>` dolga). A kriptográfiai eredet és az „az aláírt állítás lefedi a pinelt grammart" két külön kérdés, egyik sem helyettesíti a másikat.

## Módok

* `candidate` (release előtt): a pinelt commit létezik és a `devel`-en van; a tizenkét fájl bájtra azonos a manifesttel; a manifest-digest és a pin neve újraszámolható; az a commit, amelyen a release ténylegesen fut (`--release-head`), ugyanazt a tizenkét fájlt tartalmazza; a verzió érvényes következő növelés; ki van listázva, mely fájlokban haladt tovább a `devel` a pin óta.
* `record` (release után): a rekord `provenance.source_commit`-ja bájtra azonos módon tartalmazza a tizenkét fájlt; **és** a rekord mind a tizenkét fájlról hordozza a saját digestjét. Ez release-követelmény (2026-11-01 döntés): a `source_commit` a forrásállapot azonosítására szolgál és kötelező marad, de nem helyettesíti a fájlszintű digesteket; a rekordnak a digestértékeket és az algoritmust is hordoznia kell, hogy a tizenkét fájl ellenőrzése ne függjön egy git-objektum későbbi elérhetőségétől. Hogy a rekord hol tárolja, az a rekord-szerződés dolga, itt nem dől el; az eszköz a meglévő helyeket olvassa, mezőt nem talál ki.

Az 1-es kilépési kód kemény hibát jelent. Az `OPEN` sorok olyan kapuk, amelyeket az eszköz nem zár le, és sosem válnak PASS-szá.

## Mért eredmény (2026-11-01, `cic-primitives-73ae469-6a188078`)

* `candidate` a `73ae469`-en: minden ellenőrzés zöld, 12/12 fájl azonos. A `devel` (`d27173f`) **továbbhaladt a `P0-4-MIGRATION.md`-ben**, ami pinelt fájl: **a `devel` fejéről vágott release nem a pin.** A release-nek a `73ae469`-ből vágott ágon kell futnia, vagy a pint kell mozgatni.
* `record` a `v0.2.0` rekordon: FAIL (4 fájl hiányzik, 5 eltér a source commitban; a rekord négy saját digestje sem egyezik a pinelttel).
* A mostani compilerrel a rekord **legfeljebb 6 fájlt digesteltethet a 12-ből** (a séma-források és a két grammar-fájl), ezért új release sem teljesítheti a 12/12 követelményt a rekord-szerződés változása nélkül. A `candidate` ezt nyitott kapuként tartja, a `record` 12/12 alatt hibát jelez. A `v0.2.0` negatív bizonyítéka befagyasztott fixture-rel reprodukálható, az eszköz semmit nem javít ki és nem fed el.
* A `12/12 PASS` **nem** állítja, hogy a release hiteles: az aláíró jogosultságát, a trust anchort és a tanúsítvány-érvényességet nem bizonyítja (`OPEN` sorok, minden futás `scope` sorral zár).
* A `73ae469` jelölt nem a `devel` jelenlegi feje. Egy `devel`-re célzó PR (mint ez) nem ad felhatalmazást a release `devel` fejéből való vágására.

## Nyitott kapuk (az eszköz nem ellenőrzi)

1. A rekordon **kívül** pinelt CIC root (`--trust-root`). 2. Az aláíró jogosultsága (az issuer tanúsítvány nincs láncolva; az ellenjegyzés önmagában felhatalmaz-e, nincs eldöntve). 3. A tanúsítványok érvényessége a release napján (a `v0.2.0` tanúsítványai 2026-12-31-én lejárnak). 4. A digest-kódolás szerződése (base64 és `sha256:` hex; Forms-egység Rust/Go golden tesztekkel). 5. Aláírás és publikálás: a tulajdonos HOLD-ja alatt.
