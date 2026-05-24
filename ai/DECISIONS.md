# Tervezési döntések / Design Decisions

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
Merge parancs: `git merge base@0.5.0`, nem `git merge base/main`.

---

## D-002 — Aggregate-first, nem atomic-first (2026-04-30)

**Döntés:** Az első definiálandók az aggregate primitive-ek, nem az atomok.

**Miért:** Ha atomic-kal kezdünk, túl hamar YANG-szintű technikai részletekbe ragadunk.
Az aggregate adja a rendszer jelentését. Az atomic csak a backend részlet.

**Következmény:** `schemas/aggregate/` épül ki először, `schemas/atomic/` utána.

---

## D-003 — 8 atom mint irreducibilis szint (2026-04-30, bővítve 2026-05-04)

**Döntés:** Shape, Role, Behavior, Contract, Address, Identity, Event, Access — ez a 8 atom.

Az Access (D-011) a 8. irreducibilis atom: value-szintű jogosultsági burok, ortogonális
a Role atomhoz. Minden Shape értéken implicit jelen van.

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

## D-006 — repo_type döntés (LEZÁRVA: primitive — jövőbeli kiterjesztés)

**Döntés:** Szemantikailag `repo_type: primitive`, de ez a mező jelenleg **nem létezik**
a `project.schema.yaml`-ban és a `compiler.py`-ban.

**Jelenlegi állapot:** A `repo_type` nem `compiler_settings` alatt van — a compiler még
nem ismeri. A szándék `x-cic.repo_type: primitive`-ként dokumentálva a `project.yaml`-ban.

**Miért nem schema:** A cic-primitives nem egyszerű schema repo — schema-képző primitive
repo. Ha `schema` típus kerülne be, szemantikailag torzítaná a toolingot.

**Következmény:** A `compiler.py` és `project.schema.yaml` kiterjesztése a base-repo-ban
szükséges. Addig: `x-cic.repo_type: primitive` a szándék hordozója, `compiler_settings`-ben
nem szerepel.

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

---

## D-008 — Semantic validate = compiler responsibility, nem primitive modell (2026-04-30)

**Döntés:** A primitive YAML contract marad tisztán deklaratív (sealed/defaulted/required).
A séma-kompatibilitás ellenőrzése — hogy egy domain specializáció kompatibilis-e az upstream
primitive-vel — a `compiler.py validate` feladata, nem beépített override-szabály.

**Nyitott rész (merge stratégia):** Ha egy leszármazott `defaulted` slotot felülír, mi a
merge policy? `replace | deep_merge | append | union` — ez még nincs döntve.
Lezárási feltétel: az első domain repó ténylegesen override-ol egy slotot.

**Miért:** A primitive modell leírja _mit_ jelent egy kezelt objektum. A compiler mondja ki,
hogy egy specializáció _kompatibilis-e_. Ez clean separation of concerns — a primitive nem
tartalmaz futtatási logikát.

**Következmény:** A következő konkrét tooling lépés:
1. `schemas/index.yaml` → primitive meta-schema (mi egy érvényes atomic/aggregate YAML)
2. `compiler.py` → primitive YAML fájlokat is validálja (nem csak `*.meta.yaml`)
3. Semantic compatibility check domain repo specializációra → Phase 6 tooling

---

## D-009 — ExecutionSurface szándékosan hiányzik (2026-04-30)

**Döntés:** Az `ExecutionSurface` aggregate (triggers, dependencies, reconciliation,
failure_policy, ownership, graph_edges) **nem kerül be most**.

**Miért:** Ha a Relay valós graph execution modellje nélkül definiáljuk, spekulatív lesz
és valószínűleg újra kell írni. A helyes sorrend:
1. CIC-Relay valós futtatási modell (mi vált ki, mi a desired→actual átmenet, mi történik hibánál)
2. Abból visszavezetni az ExecutionSurface slot-jait
3. Nem fordítva

**Következmény:** Az ExecutionSurface nyitott bridge marad amíg a Relay modell nincs.
Ha valaki ExecutionSurface-t igényel, először a Relay execution modelljét kell definiálni.

---

## D-011 — Access: a 8. atom (2026-05-04)

**Döntés:** Az Access a 8. irreducibilis szemantikai atom — nem aggregate, nem PolicySurface.

**Miért atomic és nem aggregate:**
A permission wrapper VALUE szinten él, minden Shape példányon. A `key: 4` és a
`key: {value: 4, access: [...], modify: [...], inherit: true, default_injection: null}`
szemantikailag ekvivalens — a compiler normalizálja. Ez nem rárakott réteg, hanem
a Shape belső struktúrája. Aggregálni nem lehet tovább.

**Viszony a Role atomhoz:** ortogonális.
- `role` = mit jelent a mező a management modellben (config/state/operational)
- `access` = ki érheti el — cert-alapú identity
- Példa: `role: state` + `modify: [OU=adapters,O=cic]` → az adapter írja, user csak olvassa

**Access atom struktúrája:**
```
value:             a tényleges adat (Shape típusa határozza meg)
access:            ki olvashatja — CertPattern lista (OR szemantika)
modify:            ki írhatja — CertPattern lista (OR szemantika)
inherit:           true | false | 0
                   true = sub-objektum örökli
                   false = nem örökli, sub-objektum default szabályait kapja
                   0 = teljes reset, újraszámol
default_injection: mit kap a kérező ha nincs access joga (null = mező nem látható)
```

**CertPattern nyelv:**
X.509 Subject field alapú, wildcard `*` támogatással. Lista = OR szemantika.
- `O=acme` — bármely acme-corp cert
- `OU=ops,O=acme` — acme operátorok
- `CN=*,O=partner-a` — partner-a bármely user-je
Identity forrás: cert PEM mTLS kérésből — DN, SAN, vagy custom extension (implementációs részletkérdés).

**PolicySurface aggregate** (Phase 4.x, külön feladat):
Objektum-szintű default szabályok — az Access atom `inherit: true` esetén innen veszi
az alapértéket. Ez aggregate, nem atomic. Blokkolt az Access atom implementációjától.

**Következmény:** `schemas/atomic/access.yaml` létrehozandó (Phase 8.2).
A Shape atom leírása kiegészítendő: minden Shape érték Access atomba ágyazott.
Compiler: rövid forma → hosszú forma normalizálás.
Runtime: mTLS cert kiértékelés az Access szabályok ellen.

---

## D-012 — Access atom: conformance dimenzió (2026-05-06)

**Döntés:** Az Access atom `conformance` mezővel bővül, amely az eszköz-szintű
implementációs státuszt hordozza — elkülönítve a jogosultság-alapú láthatóságtól.

**Két alapvetően különböző eset:**

| | Jogosultság hiány | Nem implementált |
|---|---|---|
| Olvasás | null / mező nem látszik | null / mező nem látszik |
| Írás | PERMISSION DENIED | HARD REJECT — "not implemented on device X" |
| Jelentés | a mező létezik, te nem férsz hozzá | a mező NEM LÉTEZIK az eszközön |

**Miért nem ugyanaz:** Ha egy write csendes elfogadás helyett hard reject nélkül elveszik,
az operátor azt hiheti a konfig alkalmazva lett — miközben az eszközön semmi sem történt.
Példa: `dhcp_enabled: true` beírva egy DHCP-t nem támogató switch-re → silent failure →
az operátor DHCP-t feltételez ahol nincs.

**A `conformance` mező értékei:**
```
implemented      (default) — mező létezik és kezelhető az eszközön
not_implemented  — mező NEM létezik az eszközön, write HARD REJECT-tel zár
deprecated       — mező létezik de kerülendő, write WARNING + elfogadás
```

**Runtime enforcement `not_implemented` esetén:**
- Olvasás: `default_injection` értéke (tipikusan null → mező nem látszik)
- Írás: hard error, NEM permission denied — "field 'X' is not implemented on device Y"
- Csendes elfogadás: TILOS — a Relay nem droppolhatja a write-ot

**Hol jelenik meg:** Az adapter binding deklarálja device-szinten melyik mezők
`not_implemented`. A séma (RFC-derivált) teljes mezőlistát tartalmaz — a conformance
az adapter runtime annotációja, nem séma-szintű eltávolítás.

**Következmény:** `schemas/atomic/access.yaml` kiegészítendő `conformance` mezővel.
A Relay runtime enforcelja: `not_implemented` mezőre érkező write-ot nem droppolja,
hanem explicit hibával visszadobja a kérőnek.

---

## D-010 — Shape atom: permission-aware value wrapper (2026-05-04)

**Döntés:** Minden Shape értéknek két szintaktikailag ekvivalens reprezentációja van:

```yaml
# Rövid forma (syntactic sugar):
cpu_cores: 4

# Hosszú forma (ekvivalens, kibontott):
cpu_cores:
  value: 4
  access: [...]          # ki olvashatja — cert-alapú identity
  modify: [...]          # ki írhatja
  inherit: true          # sub-objektumok öröklik-e ezt a szabályt (false = nem, 0 = reset)
  default_injection: null  # mit kapjon a kérező ha nincs access joga
```

**Miért:** Az adat és a jogosultság elválaszthatatlan — nem kell külön policy fájl,
path referencia vagy szinkronizáció. A permission szabály az értékkel együtt utazik.
`default_injection` megakadályozza az információ-szivárgást és a null/error hibákat.

**Identity anchor:** X.509 cert PEM — az mTLS kérésben már ott van, nincs külön lookup.
Az `access`/`modify` listában cert-alapú identitás szerepel (DN, SAN, vagy custom extension
— implementációs részletkérdés, a cert PEM az alap).

**Normalizálás:** A compiler a rövid formát mindig kibontja hosszúvá az örökölt/default
szabályok alapján. A runtime mindig a kibontott formán dolgozik. A schema-k rövid formában
írhatók — csak ott kell long form ahol permission override szükséges.

**Öröklés:**
- `inherit: true` → sub-objektum örökli a szülő permission szabályait erre a mezőre
- `inherit: false` → nem örökli, sub-objektum default szabályait kapja
- `inherit: 0` → teljes reset, a sub-objektum teljesen újraszámolja

**Következmény:** A Shape atom belső struktúrája ez — nem két különböző típus.
A Phase 8 implementáció ezt a struktúrát dolgozza ki részletesen (atomic szintű spec,
compiler normalizáció, runtime kiértékelés).

---

## D-013 — build_hash és source_hash szétválasztása (2026-05-08, lezárva 2026-05-24)

**Státusz:** lezárva — a PrimitiveRelease bundle modell felváltotta

**Helyzet (eredeti):**
A régi release modellben `build_hash = source_hash` placeholder volt a `project.yaml`-ban.

**Döntés (végleges):**
A `PrimitiveRelease` bundle nem tartalmaz `build_hash`-t. A `release.content_hash`
a `specs[]` canonical JSON hash-e — ez egyszerre forrás és build hash, mivel a
primitive rétegnek nincs önálló fordítási lépése.

Ha a jövőben tényleges build artifact keletkezik (pyang compile, OpenAPI generátor,
code gen), a bundle kiterjeszthető `build_hash` mezővel. Addig nem kell placeholder.

```yaml
release:
  content_hash: sha256(canonical_json(specs[]))   # forrás + build azonos
  sign: vault:v1:ecdsa...
  cert: PEM...
```

---

## D-014 — Cross-domain referenciák típuskezelése (2026-05-08)

**Státusz:** nyitott — döntés szükséges (BACKLOG B-008)

**Helyzet:**
CIC objektumok közötti hivatkozások (pl. StorageResource → ComputeResource, KubernetesNode → KubernetesCluster)
jelenleg plain `string` típusú mezők. A `logical_id` formátum (`cic:{domain}:{...}`) dokumentált,
de schema szinten nincs kényszerítve.

**Döntés opciók:**
1. **Szemantikus típus a Shape atomban:** `type: cic-reference` — a compiler ellenőrzi a formátumot,
   a runtime (Relay) ellenőrzi a target létezését. Ez a legtisztább megoldás.
2. **Pattern constraint:** a meglévő string mezőhöz `contract: [{type: pattern, expression: "^cic:[a-z]+:"}]`
   — minimális változás, de nem ad domain-specifikus információt.
3. **Elfogadás:** a cross-domain referencia runtime constraint, nem schema constraint.
   A Relay validálja, a schema nem.

**Ajánlott:** opció 1 — a CIC modell értéke részben a tipizált referencia láncon múlik.
Ha ez csak string, a schema-driven tooling nem tudja feloldani a dependency gráfot.

---
---

# Design Decisions — English

History of how the concepts developed. If you are looking for the origin of a decision,
look here first. Detailed thread: `primitive.txt`.

---

## D-001 — Git remote as composition mechanism (2026-04-30, updated 2026-04-30)

**Decision:** Primitive inheritance is git remote + pinned tag merge, not YAML override-rules.yaml.

**Clarification (together with D-007):** Only pinnable tags may be merged (e.g. `base@0.5.0`) — not branches
(e.g. `base/main`). The tag fixes the composition boundary. The receiving repo documents every
remote-merge dependency in `dependency.yaml` (see D-007).

**Why:** The file structure IS the interface contract. A merge conflict = schema violation.
Pinned tag + dependency.yaml together give deterministic, reproducible composition —
`git merge base/main` is non-deterministic and can change at any time.

**Consequence:** Every derived repo must follow the same file topology as the upstream.
The `base-repo` remote is the single source of truth for tooling and structure.
Merge command: `git merge base@0.5.0`, not `git merge base/main`.

---

## D-002 — Aggregate-first, not atomic-first (2026-04-30)

**Decision:** The first things to define are aggregate primitives, not atoms.

**Why:** Starting with atoms gets us stuck in YANG-level technical details too early.
The aggregate gives the system its meaning. The atomic is just a backend detail.

**Consequence:** `schemas/aggregate/` is built out first, `schemas/atomic/` follows.

---

## D-003 — 8 atoms as the irreducible level (2026-04-30, extended 2026-05-04)

**Decision:** Shape, Role, Behavior, Contract, Address, Identity, Event, Access — these are the 8 atoms.

Access (D-011) is the 8th irreducible atom: a value-level access control wrapper, orthogonal
to the Role atom. It is implicitly present on every Shape value.

**Why:** These are not YANG concepts, not RESTCONF concepts — they are the irreducible atoms
of management semantics. YANG, RESTCONF, OpenAPI are all just one way to express them.
CIC primitives can generate any target format from these.

**Consequence:** The primitive system is not tied to any single standard.
YANG mapping, RESTCONF YAML mapping, and a native CIC runtime contract are all derivable.

---

## D-004 — YANG as inspiration, not as a constraint (2026-04-30)

**Decision:** YANG as a management-semantic reference, not as a mandatory syntax.

**Why:** YANG's config/state separation and its rpc/action/notification model are a good
semantic foundation — but CIC primitives do not describe YANG modules, they describe the
conceptual level beneath them.

**Consequence:** The primitive schema lives in YAML (not `.yang` files), but YANG's
conceptual vocabulary (config tree, state tree, operation, notification, identity, feature)
guides the design of aggregates.

---

## D-005 — Sealed / defaulted / required slot system (2026-04-30)

**Decision:** Every aggregate primitive has slots in three categories.

| Category | Meaning |
|---|---|
| `sealed` | Cannot be modified in a derived type |
| `defaulted` | Has a default, can be overridden |
| `required` | Must be specialized |

**Why:** Without this, schema generation is non-deterministic and every special case
becomes a hand-wired exception.

**Consequence:** Every aggregate YAML definition must contain an explicit slot list with categories.

---

## D-006 — repo_type decision (CLOSED: primitive — future extension)

**Decision:** Semantically `repo_type: primitive`, but this field does not currently **exist**
in `project.schema.yaml` or in `compiler.py`.

**Current state:** `repo_type` is not under `compiler_settings` — the compiler does not know it yet.
The intent is documented as `x-cic.repo_type: primitive` in `project.yaml`.

**Why not in schema:** cic-primitives is not a simple schema repo — it is a schema-forming primitive repo.
Adding the `schema` type would semantically distort the tooling.

**Consequence:** Extending `compiler.py` and `project.schema.yaml` in base-repo is required.
Until then: `x-cic.repo_type: primitive` carries the intent, and is not present in `compiler_settings`.

---

## D-007 — dependency.yaml as composition lock (2026-04-30)

**Decision:** Every repo that performs `git merge <remote>/<tag>` composition must maintain
a `dependency.yaml` file at its root.

**Structure:**
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

**Rules:**
- Only pinned tags are allowed — branch references (e.g. `main`) are forbidden
- Must be updated after every `git merge <remote>/<tag>`
- `dependency.yaml` is the sole source of what came from where

**Why:** Reproducibility + audit trail. Git history shows _what_ was merged,
dependency.yaml shows _what was intentionally brought in_ and why.

**Consequence:** The `git-bootstrap` task is immediately followed by the `dependency-yaml` task
(PROMPTMAP Phase 1, priority 2).

---

## D-008 — Semantic validate = compiler responsibility, not the primitive model (2026-04-30)

**Decision:** The primitive YAML contract remains purely declarative (sealed/defaulted/required).
Schema compatibility checking — whether a domain specialization is compatible with the upstream
primitive — is the responsibility of `compiler.py validate`, not a built-in override rule.

**Open part (merge strategy):** When a derived type overrides a `defaulted` slot, what is the
merge policy? `replace | deep_merge | append | union` — not yet decided.
Closing condition: the first domain repo actually overrides a slot.

**Why:** The primitive model describes _what_ a managed object means. The compiler declares
whether a specialization _is compatible_. This is a clean separation of concerns — the primitive
contains no execution logic.

**Consequence:** The next concrete tooling steps:
1. `schemas/index.yaml` → primitive meta-schema (what is a valid atomic/aggregate YAML)
2. `compiler.py` → also validates primitive YAML files (not only `*.meta.yaml`)
3. Semantic compatibility check for domain repo specializations → Phase 6 tooling

---

## D-009 — ExecutionSurface is intentionally absent (2026-04-30)

**Decision:** The `ExecutionSurface` aggregate (triggers, dependencies, reconciliation,
failure_policy, ownership, graph_edges) is **not included now**.

**Why:** Defining it without the Relay's actual graph execution model would make it speculative
and likely require a rewrite. The correct order is:
1. CIC-Relay actual execution model (what triggers, what is the desired→actual transition, what happens on failure)
2. Derive the ExecutionSurface slots from that
3. Not the other way around

**Consequence:** ExecutionSurface remains an open bridge until the Relay model is defined.
If anyone needs an ExecutionSurface, the Relay execution model must be defined first.

---

## D-011 — Access: the 8th atom (2026-05-04)

**Decision:** Access is the 8th irreducible semantic atom — not an aggregate, not a PolicySurface.

**Why atomic and not aggregate:**
The permission wrapper lives at the VALUE level, on every Shape instance. `key: 4` and
`key: {value: 4, access: [...], modify: [...], inherit: true, default_injection: null}`
are semantically equivalent — the compiler normalizes them. This is not an added layer;
it is the internal structure of Shape. It cannot be further aggregated.

**Relationship to the Role atom:** orthogonal.
- `role` = what the field means in the management model (config/state/operational)
- `access` = who can reach it — cert-based identity
- Example: `role: state` + `modify: [OU=adapters,O=cic]` → the adapter writes it, the user only reads it

**Access atom structure:**
```
value:             the actual data (type determined by the enclosing Shape)
access:            who can read it — CertPattern list (OR semantics)
modify:            who can write it — CertPattern list (OR semantics)
inherit:           true | false | 0
                   true = sub-object inherits
                   false = does not inherit; sub-object gets its own default rules
                   0 = full reset, recomputed from scratch
default_injection: what the requester receives when they lack access (null = field not visible)
```

**CertPattern language:**
X.509 Subject field based, with wildcard `*` support. List = OR semantics.
- `O=acme` — any acme-corp cert
- `OU=ops,O=acme` — acme operators
- `CN=*,O=partner-a` — any user of partner-a
Identity source: cert PEM from the mTLS request — DN, SAN, or custom extension (implementation detail).

**PolicySurface aggregate** (Phase 4.x, separate task):
Object-level default rules — the Access atom uses these as the default when `inherit: true`.
This is an aggregate, not an atom. Blocked on the Access atom implementation.

**Consequence:** `schemas/atomic/access.yaml` to be created (Phase 8.2).
The Shape atom description to be extended: every Shape value is wrapped in an Access atom.
Compiler: short form → long form normalization.
Runtime: mTLS cert evaluation against the Access rules.

---

## D-012 — Access atom: conformance dimension (2026-05-06)

**Decision:** The Access atom gains a `conformance` field, which carries the device-level
implementation status — separate from permission-based visibility.

**Two fundamentally different cases:**

| | Permission missing | Not implemented |
|---|---|---|
| Read | null / field not visible | null / field not visible |
| Write | PERMISSION DENIED | HARD REJECT — "not implemented on device X" |
| Meaning | the field exists, you cannot access it | the field does NOT EXIST on the device |

**Why they are not the same:** If a write silently disappears instead of a hard reject,
the operator may believe the config was applied — while nothing happened on the device.
Example: `dhcp_enabled: true` written to a switch that does not support DHCP → silent failure →
the operator assumes DHCP is active where it is not.

**The `conformance` field values:**
```
implemented      (default) — field exists and is manageable on the device
not_implemented  — field does NOT exist on the device, write closes with HARD REJECT
deprecated       — field exists but should be avoided, write gives WARNING + accepted
```

**Runtime enforcement for `not_implemented`:**
- Read: `default_injection` value (typically null → field not visible)
- Write: hard error, NOT permission denied — "field 'X' is not implemented on device Y"
- Silent acceptance: FORBIDDEN — the Relay must not drop the write

**Where it appears:** The adapter binding declares at the device level which fields are
`not_implemented`. The schema (RFC-derived) contains the full field list — conformance
is the adapter's runtime annotation, not a schema-level removal.

**Consequence:** `schemas/atomic/access.yaml` to be extended with a `conformance` field.
The Relay runtime enforces: a write to a `not_implemented` field is not dropped;
it is returned to the requester with an explicit error.

---

## D-010 — Shape atom: permission-aware value wrapper (2026-05-04)

**Decision:** Every Shape value has two syntactically equivalent representations:

```yaml
# Short form (syntactic sugar):
cpu_cores: 4

# Long form (equivalent, expanded):
cpu_cores:
  value: 4
  access: [...]          # who can read it — cert-based identity
  modify: [...]          # who can write it
  inherit: true          # do sub-objects inherit this rule (false = no, 0 = reset)
  default_injection: null  # what the requester gets if they have no access
```

**Why:** Data and permission are inseparable — no separate policy file,
path reference, or synchronization is needed. The permission rule travels with the value.
`default_injection` prevents information leakage and null/error issues.

**Identity anchor:** X.509 cert PEM — already present in the mTLS request, no separate lookup.
The `access`/`modify` list contains cert-based identities (DN, SAN, or custom extension
— implementation detail, the cert PEM is the anchor).

**Normalization:** The compiler always expands the short form to the long form based on
inherited/default rules. The runtime always works on the expanded form. Schemas may be written
in short form — only long form is needed where a permission override is required.

**Inheritance:**
- `inherit: true` → sub-object inherits the parent's permission rules for this field
- `inherit: false` → does not inherit; sub-object gets its own default rules
- `inherit: 0` → full reset; the sub-object recomputes entirely from scratch

**Consequence:** This is the internal structure of the Shape atom — not two different types.
The Phase 8 implementation elaborates this structure in detail (atomic-level spec,
compiler normalization, runtime evaluation).

---

## D-013 — build_hash and source_hash separation (2026-05-08, closed 2026-05-24)

**Status:** closed — superseded by the PrimitiveRelease bundle model

**Situation (original):**
In the old release model, `build_hash = source_hash` was a placeholder in `project.yaml`.

**Decision (final):**
The `PrimitiveRelease` bundle does not contain a `build_hash`. The `release.content_hash`
is the canonical JSON hash of `specs[]` — this serves as both source and build hash, since
the primitive layer has no independent compilation step.

If in the future an actual build artifact is produced (pyang compile, OpenAPI generator,
code gen), the bundle can be extended with a `build_hash` field. Until then, no placeholder is needed.

```yaml
release:
  content_hash: sha256(canonical_json(specs[]))   # source + build are identical
  sign: vault:v1:ecdsa...
  cert: PEM...
```

---

## D-014 — Cross-domain reference type handling (2026-05-08)

**Status:** open — decision required (BACKLOG B-008)

**Situation:**
References between CIC objects (e.g. StorageResource → ComputeResource, KubernetesNode → KubernetesCluster)
are currently plain `string` type fields. The `logical_id` format (`cic:{domain}:{...}`) is documented,
but is not enforced at the schema level.

**Decision options:**
1. **Semantic type in the Shape atom:** `type: cic-reference` — the compiler checks the format,
   the runtime (Relay) checks that the target exists. This is the cleanest solution.
2. **Pattern constraint:** add `contract: [{type: pattern, expression: "^cic:[a-z]+:"}]` to the existing string field
   — minimal change, but provides no domain-specific information.
3. **Acceptance:** the cross-domain reference is a runtime constraint, not a schema constraint.
   The Relay validates it, the schema does not.

**Recommended:** option 1 — the value of the CIC model depends in part on the typed reference chain.
If this is just a string, schema-driven tooling cannot resolve the dependency graph.
