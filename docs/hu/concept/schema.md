# CIC érvényesítési és sémaalapú validációs modell

## Alapfogalmak

A CIC rendszerben minden komponens (modul, relay, output) és azok konfigurációja szigorúan séma alapún érvényesül. A séma nemcsak struktúrát, hanem viselkedést és jogosultságot is meghatároz.

Ezáltal a teljes rendszer:

* deklaratív,
* önvalidáló,
* önvédelmi mechanizmussal rendelkezik.

---

## 1. A séma szerepe

A séma egy objektum minden kulcsát, elvárt típusát, alapértelmékeit és megengedett értékeit definiálja.

### Kulcstulajdonságok:

* `required`: a kulcs kötelező jelenléte
* `default`: hiányzás esetén alkalmazott alapérték
* `nullable`: elfogadhat-e null/None értéket
* `enum`: elfogadott értékkészlet

---

## 2. Validálási folyamat

1. **Betöltés:** A YAML/JSON konfigurációs objektum betöltése.
2. **Séma hozzárendelés:** Verzó alapján hozzárendelés a megfelelő séma-definícióhoz.
3. **Validálás:** A kulcsok, típusok és megkötések ellenőrzése.
4. **Kitöltés:** Alapértékek automatikus hozzárendelése.
5. **Visszacsatolás:** Valid/invalid visszajelzés, tárolt audit információk.

---

## 3. Séma és öröklődés

A rendszerben a sémák egymásból öröklődhetnek, ezzel támogatva:

* modulcsaládok egységes kezelését,
* verzózott konzisztencia biztosítását,
* bonyolult interfészek leírhatóságát kevés duplikációval.

A Relay csak akkor fogad el egy modult, ha annak sémája:

* megfelelően validált,
* a megadott verzó él,
* nincs konfliktusban a jelenlegi végrehajtási gráffal.

---

## 4. Validáció mint oktatási eszköz

A rendszer tanulhatóságát maga a validálási rendszer biztosítja:

* a sémák közzé vannak téve,
* minden validációs hiba visszajelzés érthető,
* az építő folyamat determinisztikus,
* így a hibákból tanulhat a fejlesztő is, nemcsak az AI.

---

## 5. Sémafájl struktúra (minta)

```yaml
version: v1
kind: relay.module
spec:
  name:
    type: string
    required: true
  inputs:
    type: array
    items:
      type: object
      properties:
        type:
          type: string
          required: true
  config:
    type: object
    properties:
      retries:
        type: integer
        default: 3
      timeout:
        type: number
        default: 5.0
      secure:
        type: boolean
        default: true
```

### 5.1 Alapértelmezett értékek viselkedése és szerepe a validációban

Az `default` mező nemcsak opcionális kényelmi funkció, hanem **a rendszer determinisztikus működésének** záloga is.

Az alapértelmezett értékek alkalmazása:

* **kötelező érvényesítés** során: ha egy nem kötelező mező nem szerepel, automatikusan a default érték kerül beillesztésre,
* **interfész-konformitás** megőrzéséhez: a végrehajtó Relay vagy modul minden esetben ugyanazt a konfigurációs struktúrát kapja,
* **önjavító működés**: kisebb hibák vagy hiányzó kulcsok esetén nem áll le a rendszer, hanem feltölti az értelmes alapértelmezetttel.

Ez a viselkedés be van építve a validációs pipeline-ba, és a rendszer minden egyes kontextusban egységesen kezeli azt.

---

## 6. Következtetés

A sémaalapú modell nemcsak formai, hanem **struktúkrális garancia** is a rendszer viselkedésére.
Ezáltal a CIC rendszer:

* validálható,
* reprodukálhó,
* AI-vezérelhető,
* auditálható,
* oktatható.

Ez a verifikálható séma az alapja annak, hogy a rendszer nyitott, mégis védett.
