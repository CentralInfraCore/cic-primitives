# P7: reason a 2^53 - 1 feletti egészre (döntés-előkészítés)

Az angol változat (`docs/en/RELEASE-P7-INTEGER-RANGE-REASON.md`) a normatív forrás; ez az összefoglaló. **DÖNTVE (tulajdonos, 2026-11-21): B opció.** Az alábbi szakaszok az előkészítés (#44); a döntés a lap alján. Csak normatív döntés és deklaráció, **implementáció nincs**.

**Kérdés.** Az A profil zárt értéktartománya: null, boolean, egész szám legfeljebb 2^53 - 1 abszolút értékkel, string. A tartományon kívüli egészre a terv nem nevez reasont; a G02 ideiglenesen a `value_type_unsupported`-ot használja. **A:** marad a `value_type_unsupported`, a terv mondata módosul. **B:** külön reason a nagyságrendre (munkanév: `integer_out_of_range`), a típusra marad a régi.

**Mérések (evidence: `docs/evidence/p7-integer-range-reason/`).** (1) A reasont semmi nem bocsátja ki és nem fogyasztja: nincs a `tools/`-ban, a `tests/`-ben és a Relay-ben. (2) Egyetlen aláírt rekordot sem érint: a négy tag rekordjában a legnagyobb egész 3, a 38 fixture-ben 0 találat; a reason nem része rekordnak, aláírásnak. (3) A történeti (H) rekordok kívül esnek. (4) A PyYAML minden tesztelt egészet pontosan olvas; a Forms (Rust = Go) int64-ig elfogad, azon túl parse-hibát ad: a határt csak a verifier mondhatja ki. (5) A terv szókincse ott finom, ahol az olvasók eltérhetnek.

**Visszafelé kompatibilitás.** Egyik opció sem tör el semmit, ami létezik. A különbség az, mi olcsó *most*, amíg semmi nem fogyasztja: külön azonosító ma csak dokumentáció; egy összevont reason későbbi szétválasztása már kompatibilitási kérdés.

**Ajánlás (nem döntés): B**, a határ: abszolút érték legfeljebb 2^53 - 1 (a -2^53 már kívül van), a `value_type_unsupported`-dal azonos ellenőrzési fázisban (nyers parse, minden összehasonlítás előtt). Nyitott a döntésben: a végleges azonosító, és hogy csak verifier-oldali-e (G02) vagy producer-oldali elutasítás is kell.

**Nem állítom:** a JavaScript és más olvasók viselkedését (nem mértem); a terv jövőbeli szövegét.

**Döntés (tulajdonos, 2026-11-21).** Végleges hibakód: `integer_out_of_range` (a típushibára marad a `value_type_unsupported`). Tartomány: -(2^53-1) .. +(2^53-1) zárt intervallum. Az ellenőrzést a **producer** (nem bocsát ki ilyen rekordot) **és a verifier** is végzi, a verifier **önállóan**, a producer eredményére nem hagyatkozva; a **teljes értékfára**, az opaque tartalomra is; a H profil változatlan. Rögzítve: a terv (EN/HU), a deklaráció (G02 és az új P02, mindkettő `planned`), a `check_declaration.py` (38 reason, "megosztott reason": producer és verifier végrehajtó is kell) és az önteszt (50 ellenőrzés, 48 beültetett hiba, 7 új). **Nincs** implementáció, vektor; a reason a publikált szerződés 11. szakaszának táblájába még nem kerül, mert a verifier még nem bocsátja ki.
