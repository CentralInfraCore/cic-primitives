#!/usr/bin/env python3
"""Validate CIC composition instances against the atom grammar.

Two layers, deliberately separated:

  * section 2 (structural type algebra) -> instance-grammar.schema.yaml, JSON Schema
  * sections 3 and 4 (role algebra, inter-primitive contracts) -> this file,
    because they cross node and primitive boundaries and JSON Schema cannot
    express them

Usage:
    check_grammar.py <composition.yaml> [<composition.yaml> ...]
    check_grammar.py --self-test

Dependencies: PyYAML, jsonschema. Runs outside any container on purpose: a
grammar only its own pipeline can run is not third-party verifiable.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).with_name("instance-grammar.schema.yaml")

# Certificate patterns that count as an adapter identity for C1. The adapter is
# the only writer of observed state; anything else writing it means the field
# was misclassified.
ADAPTER_PATTERN = re.compile(r"OU=adapters\b")

RANGE_RE = re.compile(r"^\s*(-?\d+)\s*\.\.\s*(-?\d+)\s*$")
NAMESPACE_RE = re.compile(r"^cic:[a-z][a-z0-9-]*$")

SCALAR_PY_TYPES = {
    "string": str,
    "integer": int,
    "boolean": bool,
    "number": (int, float),
    "bytes": str,
}


class Finding:
    def __init__(self, rule: str, path: str, message: str):
        self.rule = rule
        self.path = path
        self.message = message

    def __str__(self) -> str:
        return f"  [{self.rule}] {self.path}\n      {self.message}"


# ──────────────────────────────────────────────────────────────────────────────
# Role normalization (README section 3.1)
# ──────────────────────────────────────────────────────────────────────────────

SHORT_ROLE_EXPANSION = {
    "config": {"authority": "config", "structural": [], "lifecycle": None},
    "state": {"authority": "state", "structural": [], "lifecycle": None},
    "operational": {"authority": "operational", "structural": [], "lifecycle": None},
    # A key is supplied by the requester at creation, so its authority is config.
    "key": {"authority": "config", "structural": ["key"], "lifecycle": None},
    # `derived` and `volatile` are lifecycle values, and both exclude authority
    # `config` — so the bare default cannot apply to them. They expand to
    # `state`: role.yaml maps both to `config false`, GET only, and every corpus
    # occurrence sits on a state_surface. Anyone wanting `operational` with
    # either must write the long form.
    "derived": {"authority": "state", "structural": [], "lifecycle": "derived"},
    "volatile": {"authority": "state", "structural": [], "lifecycle": "volatile"},
}


def expand_role(raw, path: str, out: list[Finding]) -> dict | None:
    """Return the long form of a role, or None if it is unusable."""
    if raw is None:
        return {"authority": "config", "structural": [], "lifecycle": None}
    if isinstance(raw, str):
        if raw == "reference":
            out.append(Finding(
                "R-SHORT", path,
                "`role: reference` has no short form: a reference's authority "
                "cannot be derived. Write the long form with an explicit authority."))
            return None
        if raw not in SHORT_ROLE_EXPANSION:
            out.append(Finding(
                "R-SHORT", path,
                f"`{raw}` is not a short role form "
                f"({', '.join(sorted(SHORT_ROLE_EXPANSION))})"))
            return None
        return dict(SHORT_ROLE_EXPANSION[raw])
    if isinstance(raw, dict):
        return {
            "authority": raw.get("authority", "config"),
            "structural": list(raw.get("structural") or []),
            "lifecycle": raw.get("lifecycle"),
        }
    out.append(Finding("R-SHORT", path, "`role` must be a string or a mapping"))
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Node walking
# ──────────────────────────────────────────────────────────────────────────────

# A node lives at a closed set of structural positions, and nowhere else.
#
# The first version discovered nodes by looking for a `shape_type` member. That
# is fail-open, and provably so: a field that omits `shape_type` was not
# reported as invalid, it was not seen at all — 0 nodes examined, 0 findings.
# Every "0 findings" this checker ever printed therefore proved less than it
# claimed. Discovery must not depend on the member whose absence is itself the
# defect.
# `input`, `output` and `payload` are node lists too: a Behavior's parameters
# and an Event's payload are inline Shapes with exactly the field-descriptor
# form. Leaving them out was a second fail-open, found by diffing this walker
# against the one it replaced — the old one saw them, and only by accident,
# because they happen to carry `shape_type`. When these members hold a STRING
# instead of a list they are a reference, and C6/C7 resolve them; the isinstance
# guard below keeps the two cases apart.
NODE_CONTAINERS = ("nodes", "fields", "item_fields", "input", "output", "payload")


def _node_children(node: dict, here: str):
    """(child, path, key_names) for a node's own structural children."""
    # An explicit item_key wins; with none, a single `role: key` item field is
    # the key by derivation (section 2.3).
    keys = frozenset(node.get("item_key") or [
        f.get("name") for f in (node.get("item_fields") or [])
        if isinstance(f, dict) and is_key_role(f.get("role"))])
    for child in node.get("fields") or []:
        if isinstance(child, dict):
            yield child, here, frozenset()
    for child in node.get("item_fields") or []:
        if isinstance(child, dict):
            yield child, here + "[]", keys
    for case in node.get("cases") or []:
        if isinstance(case, dict):
            for child in case.get("fields") or []:
                if isinstance(child, dict):
                    yield child, f"{here}<{case.get('name', '?')}>", frozenset()


def _walk_node(node: dict, path: str, in_item_key: frozenset[str]):
    name = node.get("name", "?")
    here = f"{path}.{name}"
    yield node, here, name in in_item_key
    for child, cpath, ckeys in _node_children(node, here):
        yield from _walk_node(child, cpath, ckeys)


def walk_nodes(obj, path: str = "$", in_item_key: frozenset[str] = frozenset()):
    """Yield (node, path, is_key_position) for every node position in a document.

    A node is an element of a `nodes`, `fields` or `item_fields` LIST — whatever
    it contains. A mapping that merely happens to carry `shape_type` somewhere
    else is not a node, and a list element that lacks `shape_type` still is one.
    """
    if isinstance(obj, dict):
        for key in NODE_CONTAINERS:
            entries = obj.get(key)
            if not isinstance(entries, list):
                continue
            for item in entries:
                if isinstance(item, dict):
                    yield from _walk_node(item, f"{path}.{key}", in_item_key)
        for k, v in obj.items():
            # The containers above are fully handled by _walk_node, and `cases`
            # is reached through it; descending again would double-report.
            if k in NODE_CONTAINERS or k == "cases":
                continue
            yield from walk_nodes(v, f"{path}.{k}", in_item_key)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk_nodes(item, path, in_item_key)


def collect_shape_names(doc) -> set[str]:
    return {n.get("name") for n, _, _ in walk_nodes(doc) if n.get("name")}


# ──────────────────────────────────────────────────────────────────────────────
# Section 4 — inter-primitive contracts
# ──────────────────────────────────────────────────────────────────────────────

def contract_entries(node) -> list[dict]:
    return [c for c in (node.get("contract") or []) if isinstance(c, dict)]


def check_default_against_contracts(node, path, out: list[Finding]) -> None:
    """C3 and C5 — a default must satisfy the node's own constraints."""
    if "default" not in node:
        return
    default = node["default"]

    scalar_type = node.get("scalar_type")
    if scalar_type in SCALAR_PY_TYPES and default is not None:
        expected = SCALAR_PY_TYPES[scalar_type]
        # bool is a subclass of int in Python; keep integer strict.
        if scalar_type == "integer" and isinstance(default, bool):
            ok = False
        else:
            ok = isinstance(default, expected)
        if not ok:
            out.append(Finding(
                "C3", path,
                f"default {default!r} is not compatible with scalar_type "
                f"`{scalar_type}`"))

    for c in contract_entries(node):
        ctype, expr = c.get("type"), c.get("expression")
        if ctype == "range" and isinstance(expr, str) and isinstance(default, int):
            m = RANGE_RE.match(expr)
            if m:
                lo, hi = int(m.group(1)), int(m.group(2))
                if not (lo <= default <= hi):
                    out.append(Finding(
                        "C3", path,
                        f"default {default} is outside the declared range "
                        f"{lo}..{hi}"))
        elif ctype == "enum":
            values = expr if isinstance(expr, list) else None
            if values is None and isinstance(expr, str):
                values = [v.strip() for v in expr.strip("[]").split(",") if v.strip()]
            if values and default not in values:
                out.append(Finding(
                    "C5", path,
                    f"default {default!r} is not among the enum values {values}"))
        elif ctype == "pattern" and isinstance(expr, str) and isinstance(default, str):
            try:
                if not re.search(expr, default):
                    out.append(Finding(
                        "C3", path,
                        f"default {default!r} does not match pattern {expr!r}"))
            except re.error:
                out.append(Finding(
                    "C3", path, f"pattern {expr!r} is not a valid regex"))


def check_access_against_role(node, role, path, out: list[Finding]) -> None:
    """C1 and C2 — who may write is constrained by what the node means."""
    access = node.get("access")
    if not isinstance(access, dict):
        return
    modify = access.get("modify")
    if modify is None:
        return
    patterns = modify if isinstance(modify, list) else [modify]
    patterns = [p for p in patterns if isinstance(p, str)]

    if role["lifecycle"] == "derived" and patterns:
        out.append(Finding(
            "C2", path,
            "a derived value is computed, so it cannot be written: "
            f"access.modify must be empty, found {patterns}"))
        return

    if role["authority"] in ("state", "operational"):
        foreign = [p for p in patterns if not ADAPTER_PATTERN.search(p)]
        if foreign:
            out.append(Finding(
                "C1", path,
                f"role authority `{role['authority']}` is observed state, so only "
                f"an adapter may write it; these are not adapter patterns: {foreign}"))


def check_role_algebra(node, role, path, is_key_position, out: list[Finding]) -> None:
    """README section 3.2."""
    authority = role["authority"]
    structural = set(role["structural"])
    lifecycle = role["lifecycle"]

    if authority not in ("config", "state", "operational"):
        out.append(Finding("R-AUTH", path, f"`{authority}` is not a valid authority"))
        return

    if lifecycle in ("derived", "volatile") and authority == "config":
        out.append(Finding(
            "R-LIFE", path,
            f"`{lifecycle}` excludes authority `config`: a {lifecycle} value has "
            "no desired state"))

    if "key" in structural:
        if authority != "config":
            out.append(Finding(
                "R-KEY", path,
                f"a key is supplied by the requester, so its authority must be "
                f"`config`, not `{authority}`"))
        if node.get("optional"):
            out.append(Finding("R-KEY", path, "a key cannot be optional"))
        if lifecycle:
            out.append(Finding(
                "R-KEY", path,
                f"a key is fixed at creation, so it cannot be `{lifecycle}`"))
        if not is_key_position:
            out.append(Finding(
                "R-KEY", path,
                "`role: key` is only meaningful on a field listed in the "
                "enclosing collection's item_key"))

    if "reference" in structural and node.get("semantic_type") != "cic-reference":
        out.append(Finding(
            "R-REF", path,
            "structural role `reference` requires `semantic_type: cic-reference`"))


def is_key_role(role) -> bool:
    return role == "key" or (isinstance(role, dict)
                             and "key" in (role.get("structural") or []))


def check_collection(node, path, out: list[Finding]) -> None:
    """C8 — every list has a key, and a composite key states its order."""
    if node.get("collection_variant") != "list":
        return
    items = [f for f in (node.get("item_fields") or []) if isinstance(f, dict)]
    item_names = {f.get("name") for f in items}
    by_name = {f.get("name"): f for f in items}
    declared = node.get("item_key")
    keyed = [f.get("name") for f in items if is_key_role(f.get("role"))]

    if not declared:
        if not keyed:
            out.append(Finding(
                "C8", path,
                "a list has no key: declare `item_key`, or mark an item field "
                "`role: key`. Without one an element's address is its position, "
                "and a position moves when a neighbour is inserted"))
        elif len(keyed) > 1:
            out.append(Finding(
                "C8", path,
                f"{len(keyed)} item fields carry `role: key` ({keyed}), so the key "
                "is composite and its order is undefined: declare `item_key` "
                "explicitly"))
        return

    for key in declared:
        if key not in item_names:
            out.append(Finding(
                "C8", path, f"item_key names `{key}`, which is not an item field"))
            continue
        krole = by_name[key].get("role")
        krole_name = krole if isinstance(krole, str) else (krole or {}).get("structural")
        if not is_key_role(krole):
            out.append(Finding(
                "C8", path,
                f"item field `{key}` is named in item_key but its role is "
                f"`{krole_name}`, not key"))


def check_reference_target(node, path, out: list[Finding]) -> None:
    """C10 — {namespace}:{Kind}, and the namespace itself carries the cic: prefix."""
    target = node.get("reference_target")
    if not isinstance(target, str):
        return
    parts = target.split(":")
    if len(parts) != 3:
        out.append(Finding(
            "C10", path,
            f"reference_target `{target}` must be {{namespace}}:{{Kind}} where the "
            "namespace is itself cic-prefixed, e.g. cic:network:NetworkInterface"))
        return
    namespace = ":".join(parts[:2])
    if not NAMESPACE_RE.match(namespace):
        out.append(Finding(
            "C10", path, f"`{namespace}` is not a valid namespace"))
    if not parts[2][:1].isupper():
        out.append(Finding(
            "C10", path, f"`{parts[2]}` is not a Kind (Kinds are PascalCase)"))


def check_shape_references(doc, out: list[Finding]) -> None:
    """C6 and C7 — a named input/output/payload must resolve to a declared shape."""
    known = collect_shape_names(doc)

    def scan(obj, path):
        if isinstance(obj, dict):
            for member in ("input", "output", "payload"):
                val = obj.get(member)
                if isinstance(val, str) and val not in known:
                    rule = "C7" if member == "payload" else "C6"
                    out.append(Finding(
                        rule, f"{path}.{member}",
                        f"`{val}` does not resolve to any Shape declared in this "
                        "composition"))
            for k, v in obj.items():
                scan(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for item in obj:
                scan(item, path)

    scan(doc, "$")


# ──────────────────────────────────────────────────────────────────────────────
# Driver
# ──────────────────────────────────────────────────────────────────────────────

def load_schema():
    with SCHEMA_PATH.open() as fh:
        return Draft202012Validator(yaml.safe_load(fh))


def check_document(doc, validator) -> list[Finding]:
    out: list[Finding] = []
    for node, path, is_key_position in walk_nodes(doc):
        for err in sorted(validator.iter_errors(node), key=lambda e: list(e.path)):
            out.append(Finding("S2", path, err.message))
        role = expand_role(node.get("role"), path, out)
        if role is not None:
            check_role_algebra(node, role, path, is_key_position, out)
            check_access_against_role(node, role, path, out)
        check_default_against_contracts(node, path, out)
        check_collection(node, path, out)
        check_reference_target(node, path, out)
    check_shape_references(doc, out)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Self-test — the gate must be shown capable of failing
# ──────────────────────────────────────────────────────────────────────────────

MUST_REJECT = {
    "scalar without scalar_type": {
        "name": "a", "shape_type": "scalar", "role": "config"},
    "scalar carrying composite fields": {
        "name": "a", "shape_type": "scalar", "scalar_type": "string",
        "fields": [{"name": "b", "shape_type": "scalar", "scalar_type": "string"}]},
    "mandatory and optional together": {
        "name": "a", "shape_type": "scalar", "scalar_type": "string",
        "mandatory": True, "optional": True},
    "mandatory with a default": {
        "name": "a", "shape_type": "scalar", "scalar_type": "integer",
        "mandatory": True, "default": 1},
    "default outside its own range": {
        "name": "a", "shape_type": "scalar", "scalar_type": "integer",
        "optional": True, "default": 0,
        "contract": [{"type": "range", "expression": "1..256"}]},
    "default not in its own enum": {
        "name": "a", "shape_type": "scalar", "scalar_type": "string",
        "optional": True, "default": "sideways",
        "contract": [{"type": "enum", "expression": ["up", "down"]}]},
    "default of the wrong scalar type": {
        "name": "a", "shape_type": "scalar", "scalar_type": "integer",
        "optional": True, "default": "twelve"},
    "list with neither item_key nor a key-roled field": {
        "name": "a", "shape_type": "collection", "collection_variant": "list",
        "item_fields": [{"name": "b", "shape_type": "scalar",
                         "scalar_type": "string"}]},
    "composite key with undefined order": {
        "name": "a", "shape_type": "collection", "collection_variant": "list",
        "item_fields": [
            {"name": "b", "shape_type": "scalar", "scalar_type": "string",
             "role": "key", "mandatory": True},
            {"name": "c", "shape_type": "scalar", "scalar_type": "string",
             "role": "key", "mandatory": True}]},
    "item_key naming a non-key field": {
        "name": "a", "shape_type": "collection", "collection_variant": "list",
        "item_key": ["b"],
        "item_fields": [{"name": "b", "shape_type": "scalar",
                         "scalar_type": "string", "role": "config"}]},
    "derived with a desired state": {
        "name": "a", "shape_type": "scalar", "scalar_type": "string",
        "role": {"authority": "config", "lifecycle": "derived"}},
    "user writing observed state": {
        "name": "a", "shape_type": "scalar", "scalar_type": "string",
        "role": "state", "access": {"modify": ["O=acme"]}},
    "writing a derived value": {
        "name": "a", "shape_type": "scalar", "scalar_type": "string",
        "role": {"authority": "state", "lifecycle": "derived"},
        "access": {"modify": ["OU=adapters,O=cic"]}},
    "reference without a target": {
        "name": "a", "shape_type": "scalar", "scalar_type": "string",
        "semantic_type": "cic-reference"},
    "double-prefixed reference target": {
        "name": "a", "shape_type": "scalar", "scalar_type": "string",
        "semantic_type": "cic-reference",
        "reference_target": "cic:cic:network:NetworkInterface"},
    "two-segment identity reference": {
        "name": "a", "shape_type": "scalar", "scalar_type": "string",
        "semantic_type": "cic-reference",
        "reference_target": "cic:ManagedEntity"},
    "shape_type reference, the retired form": {
        "name": "a", "shape_type": "reference", "scalar_type": "string"},
    "short form role: reference": {
        "name": "a", "shape_type": "scalar", "scalar_type": "string",
        "role": "reference"},
}

# Fixtures that must be rejected but are documents, not bare nodes: the defect
# is the absence of a member, so they only exist at a real node position.
MUST_REJECT_DOCS = {
    "a field with no shape_type at all": {
        "spec": {"config_surface": {"nodes": [
            {"name": "ghost", "scalar_type": "string", "role": "config"}]}}},
    "a field carrying only an unknown member": {
        "spec": {"config_surface": {"nodes": [
            {"name": "alien", "totally_unknown": True}]}}},
    "a composite child with no shape_type": {
        "spec": {"config_surface": {"nodes": [
            {"name": "outer", "shape_type": "composite", "role": "config",
             "fields": [{"name": "inner", "scalar_type": "string"}]}]}}},
    "a collection item with no shape_type": {
        "spec": {"state_surface": {"nodes": [
            {"name": "list_node", "shape_type": "collection",
             "collection_variant": "list", "role": "state",
             "item_fields": [{"name": "k", "shape_type": "scalar",
                              "scalar_type": "string", "role": "key",
                              "mandatory": True},
                             {"name": "broken"}]}]}}},
}

MUST_ACCEPT = {
    "a plain mandatory scalar": {
        "name": "cpu_cores", "shape_type": "scalar", "scalar_type": "integer",
        "role": "config", "mandatory": True,
        "contract": [{"type": "range", "expression": "1..256"}]},
    "an optional scalar with a valid default": {
        "name": "replicas", "shape_type": "scalar", "scalar_type": "integer",
        "role": "config", "optional": True, "default": 1,
        "contract": [{"type": "range", "expression": "1..1000"}]},
    "a keyed list with a cross-domain reference": {
        "name": "network_interfaces", "shape_type": "collection",
        "collection_variant": "list", "role": "config", "optional": True,
        "item_key": ["name"],
        "item_fields": [
            {"name": "name", "shape_type": "scalar", "scalar_type": "string",
             "role": "key", "mandatory": True},
            {"name": "network", "shape_type": "scalar", "scalar_type": "string",
             "semantic_type": "cic-reference",
             "reference_target": "cic:network:NetworkInterface",
             "role": {"authority": "config", "structural": ["reference"]}},
        ]},
    "a single-key list, the shape the corpus writes": {
        "name": "env", "shape_type": "collection", "collection_variant": "list",
        "role": "config", "optional": True,
        "item_fields": [
            {"name": "name", "shape_type": "scalar", "scalar_type": "string",
             "role": "key", "mandatory": True},
            {"name": "value", "shape_type": "scalar", "scalar_type": "string"}]},
    "the short lifecycle forms the corpus writes": {
        "name": "effective_state", "shape_type": "scalar", "scalar_type": "string",
        "role": "derived"},
    "the combination the flat model could not express": {
        "name": "last_seen_peer", "shape_type": "scalar", "scalar_type": "string",
        "semantic_type": "cic-reference",
        "reference_target": "cic:network:NetworkInterface",
        "role": {"authority": "state", "structural": ["reference"],
                 "lifecycle": "volatile"}},
}


def as_document(node: dict) -> dict:
    """Put a bare node fixture at a real node position.

    Discovery is structural now, so a fixture floating outside any `nodes` list
    would simply not be looked at — which is exactly the bug these fixtures
    exist to catch.
    """
    return {"spec": {"config_surface": {"nodes": [node]}}}


def self_test(validator) -> int:
    failures = 0
    print("--- must be rejected ---")
    for label, node in {**{k: as_document(v) for k, v in MUST_REJECT.items()},
                        **MUST_REJECT_DOCS}.items():
        findings = check_document(node, validator)
        if findings:
            print(f"  \033[92mrejected\033[0m  {label}  [{findings[0].rule}]")
        else:
            print(f"  \033[91mLEAKED\033[0m    {label}")
            failures += 1

    print("\n--- must be accepted ---")
    for label, node in MUST_ACCEPT.items():
        findings = check_document(as_document(node), validator)
        if not findings:
            print(f"  \033[92maccepted\033[0m  {label}")
        else:
            print(f"  \033[91mFALSE POSITIVE\033[0m  {label}")
            for f in findings:
                print(f)
            failures += 1

    total = len(MUST_REJECT) + len(MUST_REJECT_DOCS) + len(MUST_ACCEPT)
    print(f"\nself-test: {total - failures}/{total}")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    validator = load_schema()

    if args.self_test:
        return self_test(validator)

    if not args.files:
        ap.error("give at least one composition, or --self-test")

    status = 0
    for path in args.files:
        # Multi-document safe: the repository's own negative fixtures are
        # `---` separated, and a gate that tracebacks on its input is not a gate.
        try:
            with path.open() as fh:
                docs = [d for d in yaml.safe_load_all(fh) if d is not None]
        except yaml.YAMLError as exc:
            status = 1
            first = str(exc).splitlines()[0] or exc.__class__.__name__
            print(f"\033[91m✗\033[0m {path}  (unparseable: {first})")
            continue

        findings: list[Finding] = []
        node_count = 0
        for i, doc in enumerate(docs):
            prefix = "" if len(docs) == 1 else f"[doc {i}]"
            node_count += sum(1 for _ in walk_nodes(doc))
            for f in check_document(doc, validator):
                f.path = prefix + f.path
                findings.append(f)

        if findings:
            status = 1
            print(f"\n\033[91m✗\033[0m {path}  ({node_count} node, "
                  f"{len(findings)} finding)")
            for f in findings:
                print(f)
        else:
            print(f"\033[92m✓\033[0m {path}  ({node_count} node)")
    return status


if __name__ == "__main__":
    sys.exit(main())
