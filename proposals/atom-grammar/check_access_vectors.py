#!/usr/bin/env python3
"""Gate for the Access / PolicySurface grammar (access-policy/1).

Runs the golden vectors in access-vectors/ through the reference model
(access_policy.py), checks the structural rules and the properties that must
hold across all vectors, and proves with seeded faults that each of them can
fail.

Usage:
    check_access_vectors.py            # vectors + rules + schema sync
    check_access_vectors.py --self-test  # the above, then every seeded fault must turn it red

Dependencies: PyYAML. No network, no clock.
"""

from __future__ import annotations

import copy
import re
import sys
import types
from pathlib import Path

import yaml

HERE = Path(__file__).parent
VECTORS = HERE / "access-vectors"
MODEL = HERE / "access_policy.py"
ROOT = HERE.parent.parent
ACCESS_SCHEMA = ROOT / "schemas" / "atomic" / "access.yaml"
POLICY_SCHEMA = ROOT / "schemas" / "aggregate" / "policy-surface.yaml"

SUITES = ("reading", "expansion", "resolution", "migration")
KINDS = {"read_mode", "read_rule", "read_policy", "migrate_mode", "expand", "roundtrip", "resolve"}

# Every scenario the P0.4 acceptance names must be covered by at least one case.
REQUIRED_COVERAGE = {
    "short-to-long", "symbolic-defaults", "long-form-full", "partial-long-form",
    "empty-is-not-inherit", "null-is-not-inherit", "symbol-in-list-invalid",
    "inheritance-three-states", "legacy-compat", "no-implicit-spelling-change", "migration-lossless",
    "conflict-explicit-ban-vs-inherited-allow", "explicit-ban-terminal", "explicit-local-vs-inherited",
    "field-level-inherit", "noinherit-vs-reset", "policy-inherit-three-states", "policy-surface-types",
    "missing-policy-surface", "owner-authority", "reset-fail-closed", "historical-open-default",
    "unknown-context-no-invention", "conformance-authority", "lossless-normalize", "priority-order",
    "symbolic-default-no-shadow", "pattern-comma-hazard",
}

# Groups of cases that are one parent/child pair differing in the mode only.
DIFFERENTIAL_GROUPS = ("resolution.diff-field-", "resolution.diff-policy-g2-")


class Finding(Exception):
    pass


# ── loading ──────────────────────────────────────────────────────────────────

class StrictLoader(yaml.SafeLoader):
    pass


def _no_dupes(loader, node, deep=False):
    seen = set()
    for k, _ in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in seen:
            raise Finding(f"DUPLICATE_KEY: {key!r}")
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dupes)


def load_model(source: str | None = None) -> types.ModuleType:
    src = MODEL.read_text() if source is None else source
    mod = types.ModuleType("access_policy_under_test")
    exec(compile(src, str(MODEL), "exec"), mod.__dict__)
    return mod


def load_vectors() -> list[dict]:
    cases = []
    for suite in SUITES:
        doc = yaml.load((VECTORS / f"{suite}.yaml").read_text(), Loader=StrictLoader)
        if doc.get("format") != "access-vectors/1" or doc.get("suite") != suite:
            raise Finding(f"BAD_HEADER: {suite}")
        cases.extend(doc["cases"])
    return cases


# ── running a case ───────────────────────────────────────────────────────────

def run_case(m, case) -> dict:
    k, i = case["kind"], case["input"]
    try:
        if k == "read_mode":
            return {"mode": m.read_mode(i["value"], i["grammar"])}
        if k == "read_rule":
            kind, v = m.read_rule(i["value"])
            return {"kind": kind, "patterns": list(v)} if kind == "list" else {"kind": kind, "symbol": v}
        if k == "read_policy":
            p = m.read_policy(i["policy"], i["grammar"])
            out = {"ok": True}
            if isinstance(p, dict) and p["mode"] is not None:
                out["mode"] = p["mode"]
            return out
        if k == "migrate_mode":
            return {"value": m.migrate_mode(i["value"], i["from"], i["to"])}
        if k == "expand":
            e, basis = m.expand(i["node"], i["position"], i["grammar"], i["origin"], i["attested"])
            return {"expanded": e, "basis": basis}
        if k == "roundtrip":
            e, basis = m.expand(i["node"], i["position"], i["grammar"], i["origin"], i["attested"])
            c = m.collapse(e, i["grammar"], i["authored_expanded"], basis)
            back, _ = m.expand(c, i["position"], i["grammar"], i["origin"], i["attested"])
            form = "expanded" if (isinstance(c, dict) and m.recognize(c) == "expanded") else "short"
            return {"form": form, "equal": m.canonical(back) == m.canonical(e)}
        if k == "resolve":
            return m.resolve(i["ctx"], i["target"], i["req"], i["grammar"])
    except m.PolicyError as ex:
        return {"error": ex.code}
    raise Finding(f"UNKNOWN_KIND: {k}")


# ── rules ────────────────────────────────────────────────────────────────────

def check_vectors(m, cases) -> list[str]:
    bad = []
    for c in cases:
        got = run_case(m, c)
        if m.canonical(got) != m.canonical(c["expect"]):
            bad.append(f"VECTOR {c['id']}: expected {c['expect']}, got {got}")
    return bad


def check_structure(m, cases) -> list[str]:
    bad = []
    ids = set()
    for c in cases:
        cid = c.get("id", "?")
        if cid in ids:
            bad.append(f"DUPLICATE_ID {cid}")
        ids.add(cid)
        if c.get("kind") not in KINDS:
            bad.append(f"BAD_KIND {cid}")
        if c.get("polarity") not in ("positive", "negative"):
            bad.append(f"BAD_POLARITY {cid}")
            continue
        exp = c["expect"]
        if c["kind"] == "resolve":
            ok = (exp["outcome"] == "allow") == (c["polarity"] == "positive")
        else:
            ok = ("error" in exp) == (c["polarity"] == "negative")
        if not ok:
            bad.append(f"POLARITY_MISMATCH {cid}")
    covered = {t for c in cases for t in c.get("covers", [])}
    for t in sorted(REQUIRED_COVERAGE - covered):
        bad.append(f"UNCOVERED_SCENARIO {t}")
    for t in sorted(covered - REQUIRED_COVERAGE):
        bad.append(f"UNKNOWN_SCENARIO_TAG {t}")
    src = MODEL.read_text() if m is None else getattr(m, "_SOURCE", MODEL.read_text())
    codes = set(re.findall(r'PolicyError\("([A-Z_]+)"', src)) | set(re.findall(r'"code": "([A-Z_]+)"', src))
    used = {c["expect"].get("error") or c["expect"].get("code") for c in cases}
    for code in sorted(codes - used):
        bad.append(f"UNEXERCISED_CODE {code}")
    return bad


def check_properties(m, cases) -> list[str]:
    bad = []
    for c in cases:
        if c["kind"] == "expand":
            r = run_case(m, c)
            if "expanded" in r:
                again = copy.deepcopy(c)
                again["input"]["node"] = r["expanded"]
                again["input"]["position"] = "opaque"
                r2 = run_case(m, again)
                if m.canonical(r2.get("expanded")) != m.canonical(r["expanded"]):
                    bad.append(f"NOT_IDEMPOTENT {c['id']}")
                if m.canonical(run_case(m, c)) != m.canonical(r):
                    bad.append(f"NOT_DETERMINISTIC {c['id']}")
        if c["kind"] == "resolve":
            g = c["input"]["grammar"]
            other = 2 if g == 1 else 1
            mig = copy.deepcopy(c)
            mig["input"]["grammar"] = other
            try:
                for o in mig["input"]["ctx"]["objects"].values():
                    if "carrier" in o:
                        o["carrier"]["inherit"] = m.migrate_mode(o["carrier"].get("inherit", m.write_mode("inherit", g)), g, other)
                    if isinstance(o.get("policy"), dict) and "inherit_policy" in o["policy"]:
                        o["policy"]["inherit_policy"] = m.migrate_mode(o["policy"]["inherit_policy"], g, other)
                got = run_case(m, mig)
            except m.PolicyError as ex:
                got = {"error": ex.code}
            if m.canonical(got) != m.canonical(c["expect"]):
                bad.append(f"MIGRATION_CHANGES_RESULT {c['id']}")
    return bad


def _mask_modes(case):
    c = copy.deepcopy(case["input"])
    for o in c["ctx"]["objects"].values():
        if "carrier" in o:
            o["carrier"]["inherit"] = "*"
        if isinstance(o.get("policy"), dict) and "inherit_policy" in o["policy"]:
            o["policy"]["inherit_policy"] = "*"
    return yaml.safe_dump(c, sort_keys=True)


def check_differential(m, cases) -> list[str]:
    bad = []
    byid = {c["id"]: c for c in cases}
    for prefix in DIFFERENTIAL_GROUPS:
        grp = [c for c in cases if c["id"].startswith(prefix)]
        if len(grp) != 3:
            bad.append(f"DIFFERENTIAL_GROUP_SIZE {prefix}")
            continue
        if len({_mask_modes(c) for c in grp}) != 1:
            bad.append(f"DIFFERENTIAL_NOT_SAME_PAIR {prefix}")
        res = [m.canonical(run_case(m, c)) for c in grp]
        if len(set(res)) != 3:
            bad.append(f"MODES_NOT_DISTINGUISHED {prefix}")
        ni, rs = byid[prefix + "no-inherit"], byid[prefix + "reset"]
        if run_case(m, ni)["outcome"] == run_case(m, rs)["outcome"] and prefix == DIFFERENTIAL_GROUPS[0]:
            bad.append(f"NOINHERIT_RESET_SAME_OUTCOME {prefix}")
    return bad


def check_schema_sync(m, access=None, policy=None) -> list[str]:
    bad = []
    a = access or yaml.load(ACCESS_SCHEMA.read_text(), Loader=StrictLoader)
    p = policy or yaml.load(POLICY_SCHEMA.read_text(), Loader=StrictLoader)
    props = a["spec"]["fields"]["properties"]
    if tuple(["value"] + [k for k in props if k != "value"]) != m.ACCESS_KEYS:
        bad.append("SCHEMA_ACCESS_KEYS")
    for op in m.OPS:
        if props[op]["type"] != "list<CertPattern> | inherit" or props[op]["default"] != "inherit":
            bad.append(f"SCHEMA_ACCESS_{op.upper()}_TYPE")
    if props["inherit"]["type"] != "InheritanceMode" or props["inherit"]["default"] != "inherit":
        bad.append("SCHEMA_INHERIT_TYPE")
    if tuple(props["conformance"]["values"]) != m.CONFORMANCE_VALUES:
        bad.append("SCHEMA_CONFORMANCE_VALUES")
    if tuple(a["spec"]["inheritance_mode"]["values"]) != m.MODES:
        bad.append("SCHEMA_MODES")
    slots = p["spec"]["slots"]
    if slots["default_access"]["type"] != "list<CertPattern> | open":
        bad.append("SCHEMA_DEFAULT_ACCESS_TYPE")
    if slots["default_modify"]["type"] != "list<CertPattern> | owner":
        bad.append("SCHEMA_DEFAULT_MODIFY_TYPE")
    if slots["surface_rules"]["type"] != "list<SurfaceRule>" or slots["surface_rules"]["default"] != []:
        bad.append("SCHEMA_SURFACE_RULES_TYPE")
    if slots["inherit_policy"]["type"] != "InheritanceMode" or slots["inherit_policy"]["default"] != "inherit":
        bad.append("SCHEMA_INHERIT_POLICY_TYPE")
    if tuple(p["spec"]["resolution"]["priority"]) != ("field", "surface_rules", "default", "field_inherited", "policy_inherited", "system"):
        bad.append("SCHEMA_PRIORITY")
    return bad


def run_all(m, cases) -> list[str]:
    return (check_vectors(m, cases) + check_structure(m, cases) + check_properties(m, cases)
            + check_differential(m, cases) + check_schema_sync(m))


# ── seeded faults ────────────────────────────────────────────────────────────
# Each fault edits the reference model in exactly one place, or one vector set;
# the gate must go red. A fault whose edit does not apply fails the self-test.

MODEL_FAULTS = [
    ("null-read-as-bool-int", "is_bool = type(value) is bool", "is_bool = isinstance(value, int)"),
    ("float-zero-is-reset", "is_zero = type(value) is int and value == 0", "is_zero = isinstance(value, (int, float)) and value == 0"),
    ("reset-spelled-false", '"reset": 0}[mode]', '"reset": False}[mode]'),
    ("legacy-accepted-in-2", 'if is_bool or is_zero:\n            raise PolicyError("LEGACY_INHERIT_IN_GRAMMAR_2", repr(value))',
     'if is_bool or is_zero:\n            return "inherit" if value else "reset"'),
    ("symbol-valid-pattern", "return isinstance(p, str) and PATTERN_RE.match(p) is not None", "return isinstance(p, str)"),
    ("null-is-inherit", '    """access / modify value: (\'list\', patterns) or (\'symbol\', name)."""\n',
     '    """access / modify value: (\'list\', patterns) or (\'symbol\', name)."""\n    if value is None:\n        return ("symbol", "inherit")\n'),
    ("wildcard-broken", '".*".join(', '"".join('),
    ("list-is-and", "if any(pattern_matches(p, subj) for p in patterns):", "if all(pattern_matches(p, subj) for p in patterns):"),
    ("partial-form-override", 'if isinstance(node, dict) and position == "scalar":', "if False:"),
    ("conformance-authorable", '        if value != "implemented":\n            raise PolicyError("CONFORMANCE_NOT_AUTHORABLE", value)\n        return "authored_claim"',
     '        return "authored_claim"'),
    ("collapse-drops-authored", "not authored_expanded  # fault-site: collapse-authored", "True"),
    ("collapse-attested", '        and basis != "binding_attested"\n', ""),
    ("empty-list-falls-through", 'if kind == "list":\n        return _decide((kind, v), "field", req)', 'if kind == "list" and v:\n        return _decide((kind, v), "field", req)'),
    ("reset-uses-system-default", 'if reset_barrier:\n        return {"outcome": "deny"', 'if False:\n        return {"outcome": "deny"'),
    ("noinherit-cuts-like-reset", 'if pol_mode == "no-inherit":\n            break', 'if pol_mode == "no-inherit":\n            reset_barrier = True\n            break'),
    ("carrier-reset-boundary-ignored", 'and o["carrier"]["mode"] == "reset":', 'and o["carrier"]["mode"] == "never":'),
    ("carrier-noinherit-ignored", 'if mode == "no-inherit":\n            field_open = False', 'if mode == "no-inherit":\n            pass'),
    ("symbolic-default-shadows", '        return (pol["declared"][op], "default")\n    return None',
     '        return (pol["declared"][op], "default")\n    return (("symbol", SYSTEM_SYMBOL[op]), "default")'),
    ("default-before-surface-rule", 'hit = pol["rules"].get((surface, op))', 'hit = None if op in pol["declared"] else pol["rules"].get((surface, op))'),
    ("unknown-own-policy-ignored", '    if cur["policy"] == "unknown":', "    if False:"),
    ("unknown-ancestor-ignored", '        if o["policy"] == "unknown":', "        if False:"),
    ("owner-without-trust", 'if not owner or owner.get("trust") != "trusted":  # fault-site: owner-trust', "if not owner:"),
]


def vector_faults(cases):
    """(name, mutated cases) pairs for the structural rules."""
    def mut(fn):
        c = copy.deepcopy(cases)
        fn(c)
        return c
    first = lambda c, pref: next(x for x in c if x["id"].startswith(pref))
    yield "duplicate-id", "DUPLICATE_ID", mut(lambda c: c[1].__setitem__("id", c[0]["id"]))
    yield "bad-polarity", "BAD_POLARITY", mut(lambda c: c[0].__setitem__("polarity", "maybe"))
    yield "polarity-mismatch", "POLARITY_MISMATCH", mut(lambda c: first(c, "resolution.field-explicit-match").__setitem__("polarity", "negative"))
    yield "wrong-expectation", "VECTOR", mut(lambda c: first(c, "resolution.field-explicit-match")["expect"].__setitem__("outcome", "deny"))
    yield "false-is-zero-expectation", "VECTOR", mut(lambda c: first(c, "expansion.long-false-stays-false")["expect"]["expanded"].__setitem__("inherit", 0))
    yield "uncovered-scenario", "UNCOVERED_SCENARIO", mut(lambda c: [x["covers"].clear() for x in c if "noinherit-vs-reset" in x["covers"]])
    yield "unexercised-code", "UNEXERCISED_CODE", mut(lambda c: first(c, "resolution.system-owner-mismatch")["expect"].__setitem__("code", "NO_PATTERN_MATCH"))
    yield "unknown-tag", "UNKNOWN_SCENARIO_TAG", mut(lambda c: c[0]["covers"].append("invented-scenario"))
    yield "differential-collapsed", "MODES_NOT_DISTINGUISHED", mut(lambda c: first(c, "resolution.diff-field-reset").__setitem__("input", copy.deepcopy(first(c, "resolution.diff-field-no-inherit")["input"])) or first(c, "resolution.diff-field-reset").__setitem__("expect", copy.deepcopy(first(c, "resolution.diff-field-no-inherit")["expect"])))
    yield "differential-other-pair", "DIFFERENTIAL_NOT_SAME_PAIR", mut(lambda c: first(c, "resolution.diff-field-reset")["input"]["req"]["requestor"].__setitem__("subject", "O=zzz"))
    yield "differential-dropped", "DIFFERENTIAL_GROUP_SIZE", mut(lambda c: [x for x in c if x["id"] != "resolution.diff-field-reset"] and c.remove(first(c, "resolution.diff-field-reset")))


def schema_faults():
    a = yaml.load(ACCESS_SCHEMA.read_text(), Loader=StrictLoader)
    p = yaml.load(POLICY_SCHEMA.read_text(), Loader=StrictLoader)
    def a_mut(fn):
        x = copy.deepcopy(a); fn(x); return x, p
    def p_mut(fn):
        y = copy.deepcopy(p); fn(y); return a, y
    yield "schema-access-type", a_mut(lambda x: x["spec"]["fields"]["properties"]["access"].__setitem__("type", "list<CertPattern>"))
    yield "schema-inherit-boolean", a_mut(lambda x: x["spec"]["fields"]["properties"]["inherit"].__setitem__("type", "boolean | 0"))
    yield "schema-conformance-values", a_mut(lambda x: x["spec"]["fields"]["properties"]["conformance"].__setitem__("values", ["implemented"]))
    yield "schema-default-access", p_mut(lambda y: y["spec"]["slots"]["default_access"].__setitem__("type", "CertPattern[]"))
    yield "schema-surface-rules-empty-word", p_mut(lambda y: y["spec"]["slots"]["surface_rules"].__setitem__("default", "empty"))
    yield "schema-inherit-policy-boolean", p_mut(lambda y: y["spec"]["slots"]["inherit_policy"].__setitem__("type", "boolean"))
    yield "schema-priority", p_mut(lambda y: y["spec"]["resolution"]["priority"].reverse())


def self_test(cases) -> int:
    failed = 0
    base = MODEL.read_text()
    m = load_model()
    m._SOURCE = base
    if run_all(m, cases):
        print("self-test: the unmodified model/vectors are not green")
        return 1
    for name, old, new in MODEL_FAULTS:
        if base.count(old) != 1:
            print(f"FAULT {name}: edit site found {base.count(old)} times, must be exactly 1")
            failed += 1
            continue
        src = base.replace(old, new)
        mm = load_model(src)
        mm._SOURCE = src
        res = run_all(mm, cases)
        print(f"  fault {name:34} -> {'RED' if res else 'GREEN (NOT DETECTED)'}" + (f"  [{res[0][:60]}]" if res else ""))
        failed += 0 if res else 1
    for name, rule, mutated in vector_faults(cases):
        res = check_structure(m, mutated) + check_vectors(m, mutated) + check_differential(m, mutated)
        hit = any(r.startswith(rule) for r in res)
        print(f"  fault {name:34} -> {'RED by ' + rule if hit else 'NOT DETECTED BY ' + rule}")
        failed += 0 if hit else 1
    for name, (a, p) in schema_faults():
        res = check_schema_sync(m, a, p)
        print(f"  fault {name:34} -> {'RED' if res else 'GREEN (NOT DETECTED)'}" + (f"  [{res[0][:60]}]" if res else ""))
        failed += 0 if res else 1
    total = len(MODEL_FAULTS) + len(list(vector_faults(cases))) + len(list(schema_faults()))
    print(f"self-test: {total - failed}/{total} seeded faults detected")
    return 1 if failed else 0


def main() -> int:
    cases = load_vectors()
    if "--self-test" in sys.argv:
        return self_test(cases)
    m = load_model()
    m._SOURCE = MODEL.read_text()
    bad = run_all(m, cases)
    for b in bad:
        print(f"FAIL {b}")
    print(f"{len(cases)} cases, {len(bad)} failure(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
