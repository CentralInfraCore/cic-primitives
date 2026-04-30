# Tervezési döntések

A fogalmak kialakulásának history-ja. Ha egy döntés eredetét keresed,
itt keresd először. Részletes thread: `primitive.txt`.

---

## D-001 — Git remote mint kompozíciós mechanizmus (2026-04-30, frissítve 2026-04-30)

**Döntés:** A primitive öröklődés git remote + pinnelt tag merge, nem YAML override-rules.yaml.

**Pontosítás (D-007-tel együtt):** Csak pinnelt tagre mergelhető (pl. `base@0.5.0`) — branch-re
(pl. `base/main`) nem. A tag rögzíti a composition boundary-t. A fogadó repo minden
remote-merge dependency-t `dependency.yaml`-ban dokumentál (ld. D-007).

**Miért:** A fájlstruktúra IS az interface contract. A merge konfliktus = séma sértés.
A pinnelt tag + dependency.yaml együtt ad determinisztikus, reprodukálható composition-t —
`git merge base/main` nem determinisztikus, bármikor változhat.

**Következmény:** Minden leszármazott repo-nak ugyanazt a fájl-topológiát kell követnie
mint az upstream. A `base-repo` remote a tooling + struktúra single source of truth.
Merge parancs: `git merge base/v0.0.0`, nem `git merge base/main`.

---

## D-002 — Aggregate-first, nem atomic-first (2026-04-30)

**Döntés:** Az első definiálandók az aggregate primitive-ek, nem az atomok.

**Miért:** Ha atomic-kal kezdünk, túl hamar YANG-szintű technikai részletekbe ragadunk.
Az aggregate adja a rendszer jelentését. Az atomic csak a backend részlet.

**Következmény:** `schemas/aggregate/` épül ki először, `schemas/atomic/` utána.

---

## D-003 — 7 atom mint irreducibilis szint (2026-04-30)

**Döntés:** Shape, Role, Behavior, Contract, Address, Identity, Event — ez a 7 atom.

**Miért:** Ezek nem YANG fogalmak, nem RESTCONF fogalmak — ezek a menedzsment-szemantika
irreducibilis atomjai. YANG, RESTCONF, OpenAPI mind ezek egyik kifejezési módja.
A CIC primitívek ebből generálhatnak bármilyen target formátumot.

**Következmény:** A primitive rendszer nem kötődik egyetlen szabványhoz sem.
YANG mapping, RESTCONF YAML mapping, saját CIC runtime contract egyaránt levezethetők.

---

## D-004 — YANG inspiráció, nem YANG kötöttség (2026-04-30)

**Döntés:** A YANG mint menedzsment-szemantikai referencia, nem mint kötelező szintaxis.

**Miért:** A YANG config/state szétválasztása, rpc/action/notification modellje jó
szemantikai alap — de a CIC primitívek nem YANG modulokat írnak le, hanem az alattuk
lévő fogalmi szintet.

**Következmény:** A primitive séma YAML-ban él (nem `.yang` fájlban), de a YANG
fogalomkészlete (config tree, state tree, operation, notification, identity, feature)
irányadó az aggregate-ek tervezésekor.

---

## D-005 — Sealed / defaulted / required slot rendszer (2026-04-30)

**Döntés:** Minden aggregate primitive-nek három kategóriájú slot-jai vannak.

| Kategória | Jelentés |
|---|---|
| `sealed` | Nem módosítható leszármazottban |
| `defaulted` | Van alapértelmezés, felülírható |
| `required` | Kötelezően specializálandó |

**Miért:** Nélküle a schema-generálás nem deterministikus és minden speciális eset
kézzel drótozott kivétel lesz.

**Következmény:** Minden aggregate YAML definíciónak tartalmaznia kell
explicit slot listát kategóriával.

---

## D-006 — repo_type döntés (LEZÁRVA: primitive)

**Döntés:** `repo_type: primitive`

**Miért:** A cic-primitives nem egyszerű schema repo — schema-képző primitive repo.
Ha `schema` marad, a tooling később szemantikailag torzítja a repo szerepét.
A `primitive` típus pontosan leírja, hogy ez a meta-szint, amelyből sémák deriválhatók.

**Következmény:** A `compiler.py`-t a base-repo-ban ki kell terjeszteni a `primitive`
repo_type kezelésére. A `project.yaml` task erre épít.

---

## D-007 — dependency.yaml mint composition lock (2026-04-30)

**Döntés:** Minden repo, amely `git merge <remote>/<tag>` composition-t végez,
kötelezően vezet egy `dependency.yaml` fájlt a gyökerében.

**Struktúra:**
```yaml
schema_version: "1"
dependencies:
  - name: base-repo
    source: github.com/CentralInfraCore/base-repo
    tag: base@0.5.0
    mode: remote-merge
    purpose: repository-contract
    imported_paths:
      - .github/
      - Makefile
      - mk/
      - tools/
```

**Szabályok:**
- Csak pinnelt tag kerülhet be — branch referencia (pl. `main`) tiltott
- Minden `git merge <remote>/<tag>` után frissítendő
- A `dependency.yaml` az egyetlen forrása annak, hogy mi honnan érkezett

**Miért:** Reprodukálhatóság + audit trail. A git history megmutatja _mit_ mergeltek,
a dependency.yaml megmutatja _szándékosan mit_ kellett behozni és miért.

**Következmény:** A `git-bootstrap` task után azonnal jön a `dependency-yaml` task
(PROMPTMAP Phase 1, priority 2).
