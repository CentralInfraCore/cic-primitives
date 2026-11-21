# P7: reason a 2^53 - 1 feletti egészre (döntés-előkészítés)

Az angol változat (`docs/en/RELEASE-P7-INTEGER-RANGE-REASON.md`) a normatív forrás; ez az összefoglaló. **Döntés-előkészítés, nem döntés**: terv-szöveg, deklaráció, ellenőrző és verifier nem változik; a döntés a tulajdonosé.

**Kérdés.** Az A profil zárt értéktartománya: null, boolean, egész szám legfeljebb 2^53 - 1 abszolút értékkel, string. A tartományon kívüli egészre a terv nem nevez reasont; a G02 ideiglenesen a `value_type_unsupported`-ot használja. **A:** marad a `value_type_unsupported`, a terv mondata módosul. **B:** külön reason a nagyságrendre (munkanév: `integer_out_of_range`), a típusra marad a régi.

**Mérések (evidence: `docs/evidence/p7-integer-range-reason/`).** (1) A reasont semmi nem bocsátja ki és nem fogyasztja: nincs a `tools/`-ban, a `tests/`-ben és a Relay-ben. (2) Egyetlen aláírt rekordot sem érint: a négy tag rekordjában a legnagyobb egész 3, a 38 fixture-ben 0 találat; a reason nem része rekordnak, aláírásnak. (3) A történeti (H) rekordok kívül esnek. (4) A PyYAML minden tesztelt egészet pontosan olvas; a Forms (Rust = Go) int64-ig elfogad, azon túl parse-hibát ad: a határt csak a verifier mondhatja ki. (5) A terv szókincse ott finom, ahol az olvasók eltérhetnek.

**Visszafelé kompatibilitás.** Egyik opció sem tör el semmit, ami létezik. A különbség az, mi olcsó *most*, amíg semmi nem fogyasztja: külön azonosító ma csak dokumentáció; egy összevont reason későbbi szétválasztása már kompatibilitási kérdés.

**Ajánlás (nem döntés): B**, a határ: abszolút érték legfeljebb 2^53 - 1 (a -2^53 már kívül van), a `value_type_unsupported`-dal azonos ellenőrzési fázisban (nyers parse, minden összehasonlítás előtt). Nyitott a döntésben: a végleges azonosító, és hogy csak verifier-oldali-e (G02) vagy producer-oldali elutasítás is kell.

**Nem állítom:** a JavaScript és más olvasók viselkedését (nem mértem); a terv jövőbeli szövegét.
