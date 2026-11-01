# Release candidate előellenőrzés

A `tools/release_candidate_precheck.py` egy kérdésre válaszol a release elkészítése előtt és után: **tartalmazza-e a release azt a grammart, amelyet a fogyasztó pinelt?**

A fogyasztó (`cic-primitive-forms`, `corpus/pins.yaml`) egy commitot és pontosan tizenkét fájl nyers blob-bájtjainak SHA-256 értékét pineli. Egy receipt csak akkor nevezhet meg egy release-t, ha az bizonyíthatóan tartalmazza ezt a tizenkét fájlt. Az eszköz ezt git-objektumokból, a release után a release-rekordból bizonyítja vagy cáfolja. Csak olvas: nem ír alá, nem tagel, nem publikál, és **nem ellenőriz aláírást** (az a `python tools/compiler.py verify-release <rekord> --trust-root <root.pem>` dolga). A kriptográfiai eredet és az „az aláírt állítás lefedi a pinelt grammart" két külön kérdés, egyik sem helyettesíti a másikat.

## Módok

* `candidate` (release előtt): a pinelt commit létezik és a `devel`-en van; a tizenkét fájl bájtra azonos a manifesttel; a manifest-digest és a pin neve újraszámolható; az a commit, amelyen a release ténylegesen fut (`--release-head`), ugyanazt a tizenkét fájlt tartalmazza; a verzió érvényes következő növelés; ki van listázva, mely fájlokban haladt tovább a `devel` a pin óta.
* `record` (release után): a rekord `provenance.source_commit`-ja bájtra azonos módon tartalmazza a tizenkét fájlt; és a rekord megmondja, melyeket digesteli maga (a `specs` forrásai és a két `provenance.grammar_*` fájl), és melyek csak a source commitra támaszkodnak.

Az 1-es kilépési kód kemény hibát jelent. Az `OPEN` sorok olyan kapuk, amelyeket az eszköz nem zár le, és sosem válnak PASS-szá.

## Mért eredmény (2026-11-01, `cic-primitives-73ae469-6a188078`)

* `candidate` a `73ae469`-en: minden ellenőrzés zöld, 12/12 fájl azonos. A `devel` (`d27173f`) **továbbhaladt a `P0-4-MIGRATION.md`-ben**, ami pinelt fájl: **a `devel` fejéről vágott release nem a pin.** A release-nek a `73ae469`-ből vágott ágon kell futnia, vagy a pint kell mozgatni.
* `record` a `v0.2.0` rekordon: FAIL (4 fájl hiányzik, 5 eltér a source commitban; a rekord négy saját digestje sem egyezik a pinelttel).
* 6 a 12 pinelt fájlból egy új release rekordjában sem kap saját digestet: csak az aláírt `source_commit` (git SHA-1 objektumazonosító) köti. Hogy ez elég-e, vagy a rekord mind a tizenkettőt digestelje, a tulajdonos döntése.

## Nyitott kapuk (az eszköz nem ellenőrzi)

1. A rekordon **kívül** pinelt CIC root (`--trust-root`). 2. Az aláíró jogosultsága (az issuer tanúsítvány nincs láncolva; az ellenjegyzés önmagában felhatalmaz-e, nincs eldöntve). 3. A tanúsítványok érvényessége a release napján (a `v0.2.0` tanúsítványai 2026-12-31-én lejárnak). 4. A digest-kódolás szerződése (base64 és `sha256:` hex; Forms-egység Rust/Go golden tesztekkel). 5. Aláírás és publikálás: a tulajdonos HOLD-ja alatt.
