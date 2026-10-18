#!/usr/bin/env python3
"""Reference model of the Access / PolicySurface grammar (access-policy/1).

This is the executable form of P0-4-ACCESS-GRAMMAR.md. It exists so the
normative rules can be run against golden vectors; it is not the engine and it
does not enforce anything at runtime. Pure functions, standard library only, no
I/O, no clock.

Sections of the specification map to functions:

  reading   read_mode, read_rule, read_policy, recognize, expand, collapse
  authority conformance_basis
  resolving resolve
"""

from __future__ import annotations

import json
import re

MODES = ("inherit", "no-inherit", "reset")
ACCESS_KEYS = ("value", "access", "modify", "inherit", "default_injection", "conformance")
CONFORMANCE_VALUES = ("implemented", "not_implemented", "deprecated")
POLICY_KEYS = ("default_access", "default_modify", "surface_rules", "inherit_policy")
OPS = ("access", "modify")
SYSTEM_SYMBOL = {"access": "open", "modify": "owner"}

_ATTR = r"[A-Za-z][A-Za-z0-9.-]*"
_VAL = r"[^=,\s][^=,]*"
_PAIR = rf"{_ATTR}={_VAL}"
PATTERN_RE = re.compile(rf"^{_PAIR}(,{_PAIR})*$")


class PolicyError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


# ── Grammar version binding ──────────────────────────────────────────────────

SUPPORTED_GRAMMARS = (1, 2)


def bind_grammar(context_version, pin_version) -> int:
    """The grammar version is a property of the processing context, checked against
    the version the pinned schema declares. A document never carries it, and one
    context binds exactly one version for the whole document."""
    for v in (context_version, pin_version):
        if v is None:
            raise PolicyError("GRAMMAR_VERSION_MISSING")
    for v in (context_version, pin_version):
        if type(v) is not int or v not in SUPPORTED_GRAMMARS:
            raise PolicyError("UNKNOWN_GRAMMAR_VERSION", repr(v))
    if context_version != pin_version:
        raise PolicyError("GRAMMAR_VERSION_CONFLICT", f"context {context_version}, pinned schema {pin_version}")
    return context_version


def read_document(nodes, position: str, context_version, pin_version, origin: str = "authored"):
    """Expand every Access node of one document under ONE bound grammar."""
    g = bind_grammar(context_version, pin_version)
    return [expand(n, position, g, origin, False) for n in nodes]


# ── InheritanceMode ──────────────────────────────────────────────────────────

def read_mode(value, grammar: int) -> str:
    """Read a spelling of InheritanceMode. Exactly one spelling set is valid per
    grammar version; the two are never mixed and never coerced."""
    is_bool = type(value) is bool
    is_zero = type(value) is int and value == 0
    if grammar == 1:
        if is_bool:
            return "inherit" if value else "no-inherit"
        if is_zero:
            return "reset"
        if isinstance(value, str) and value in MODES:
            raise PolicyError("INHERIT_ENUM_IN_GRAMMAR_1", repr(value))
        raise PolicyError("INVALID_INHERIT", repr(value))
    if grammar == 2:
        if isinstance(value, str) and value in MODES:
            return value
        if is_bool or is_zero:
            raise PolicyError("LEGACY_INHERIT_IN_GRAMMAR_2", repr(value))
        raise PolicyError("INVALID_INHERIT", repr(value))
    raise PolicyError("UNKNOWN_GRAMMAR_VERSION", repr(grammar))


def write_mode(mode: str, grammar: int):
    """The inverse of read_mode: a bijection per grammar version."""
    if grammar == 1:
        return {"inherit": True, "no-inherit": False, "reset": 0}[mode]
    return mode


def migrate_mode(value, frm: int, to: int):
    """Explicit, lossless migration of one spelling. Never implicit."""
    return write_mode(read_mode(value, frm), to)


# ── CertPattern and rules ────────────────────────────────────────────────────

def _pairs(text: str):
    return [tuple(p.split("=", 1)) for p in text.split(",")]


def valid_pattern(p) -> bool:
    return isinstance(p, str) and PATTERN_RE.match(p) is not None


def pattern_matches(pattern: str, subject: str) -> bool:
    """A pattern matches when EVERY attr=value pair of it is satisfied by some
    pair of the subject; `*` in a value is a wildcard."""
    have = _pairs(subject)
    for attr, want in _pairs(pattern):
        rx = re.compile("^" + ".*".join(re.escape(x) for x in want.split("*")) + "$")
        if not any(a == attr and rx.match(v) for a, v in have):
            return False
    return True


def read_rule(value, symbol: str | None = "inherit"):
    """access / modify value: ('list', patterns) or ('symbol', name)."""
    if isinstance(value, list):
        for p in value:
            if not valid_pattern(p):
                raise PolicyError("INVALID_CERT_PATTERN", repr(p))
        return ("list", tuple(value))
    if isinstance(value, str) and symbol is not None and value == symbol:
        return ("symbol", value)
    raise PolicyError("INVALID_ACCESS_VALUE", repr(value))


# ── Recognition, expansion, collapse ─────────────────────────────────────────

def recognize(node) -> str:
    if not isinstance(node, dict):
        return "short"
    keys = set(node)
    if keys == set(ACCESS_KEYS):
        return "expanded"
    if set(ACCESS_KEYS) < keys:
        raise PolicyError("EXPANDED_WITH_EXTRA_KEY", ",".join(sorted(keys - set(ACCESS_KEYS))))
    return "short"


def conformance_basis(value, form: str, origin: str, attested: bool) -> str:
    """ADR 0010 of cic-primitive-forms, restated as a pure function."""
    if type(value) is not str or value not in CONFORMANCE_VALUES:
        raise PolicyError("INVALID_CONFORMANCE_VALUE", repr(value))
    if origin == "authored":
        if value != "implemented":
            raise PolicyError("CONFORMANCE_NOT_AUTHORABLE", value)
        return "authored_claim" if form == "expanded" else "default"
    if origin == "materialized":
        if attested:
            return "binding_attested"
        if value != "implemented":
            raise PolicyError("CONFORMANCE_NOT_AUTHORABLE", value)
        return "default"
    raise PolicyError("INVALID_ORIGIN", repr(origin))


def expand(node, position: str, grammar: int, origin: str = "authored", attested: bool = False):
    """Short -> expanded with SYMBOLIC defaults. Returns (expanded, basis)."""
    form = recognize(node)
    if form == "short":
        if isinstance(node, dict) and position == "scalar":
            raise PolicyError("MAP_AT_SCALAR_POSITION", "partial expanded form is not an override")
        out = {
            "value": node,
            "access": "inherit",
            "modify": "inherit",
            "inherit": write_mode("inherit", grammar),
            "default_injection": None,
            "conformance": "implemented",
        }
        return out, conformance_basis("implemented", "short", origin, attested)
    out = {"value": node["value"], "default_injection": node["default_injection"]}
    for op in OPS:
        kind, v = read_rule(node[op])
        out[op] = list(v) if kind == "list" else v
    out["inherit"] = write_mode(read_mode(node["inherit"], grammar), grammar)
    basis = conformance_basis(node["conformance"], "expanded", origin, attested)
    out["conformance"] = node["conformance"]
    return out, basis


def _is_default_long(e: dict, grammar: int) -> bool:
    return (
        e["access"] == "inherit" and e["modify"] == "inherit"
        and read_mode(e["inherit"], grammar) == "inherit"
        and e["default_injection"] is None and e["conformance"] == "implemented"
    )


def collapse(expanded: dict, grammar: int, authored_expanded: bool, basis: str):
    """Short form only when nothing explicit is lost (ADR 0001, ADR 0010)."""
    v = expanded["value"]
    short_ok = (
        not authored_expanded  # fault-site: collapse-authored
        and basis != "binding_attested"
        and _is_default_long(expanded, grammar)
        and not (isinstance(v, dict) and set(ACCESS_KEYS) <= set(v))
    )
    return v if short_ok else expanded


def canonical(obj) -> str:
    """Deterministic bytes: sorted keys, bool/int kept apart (false vs 0)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# ── PolicySurface ────────────────────────────────────────────────────────────

def read_policy(ps, grammar: int):
    """ps: dict, or the markers 'absent' / 'unknown' (known to have none / not known)."""
    if ps in ("absent", "unknown"):
        return ps
    if not isinstance(ps, dict):
        raise PolicyError("INVALID_POLICY", repr(ps))
    out = {"declared": {}, "rules": {}, "mode": None}
    for key in ps:
        if key not in POLICY_KEYS:
            raise PolicyError("UNKNOWN_POLICY_KEY", key)
    if "default_access" in ps:
        out["declared"]["access"] = read_rule(ps["default_access"], "open")
    if "default_modify" in ps:
        out["declared"]["modify"] = read_rule(ps["default_modify"], "owner")
    for entry in ps.get("surface_rules", []):
        if not isinstance(entry, dict) or set(entry) - {"surface", "access", "modify"} \
                or not isinstance(entry.get("surface"), str) or not entry["surface"]:
            raise PolicyError("INVALID_SURFACE_RULE", repr(entry))
        for op in OPS:
            if op in entry:
                kind, v = read_rule(entry[op])
                if kind == "list":
                    if (entry["surface"], op) in out["rules"]:
                        raise PolicyError("SURFACE_RULE_CONFLICT", f"{entry['surface']}.{op}")
                    out["rules"][(entry["surface"], op)] = v
    if "inherit_policy" in ps:
        out["mode"] = read_mode(ps["inherit_policy"], grammar)
    return out


# ── Resolution ───────────────────────────────────────────────────────────────

def _decide_list(patterns, layer, req):
    if not req["requestor"]["authenticated"]:
        return {"outcome": "deny", "code": "UNAUTHENTICATED", "layer": layer}
    if not patterns:
        return {"outcome": "deny", "code": "EXPLICIT_EMPTY", "layer": layer}
    subj = req["requestor"]["subject"]
    if any(pattern_matches(p, subj) for p in patterns):
        return {"outcome": "allow", "code": None, "layer": layer}
    return {"outcome": "deny", "code": "NO_PATTERN_MATCH", "layer": layer}


def _valid_identity(x) -> bool:
    """An identity is a non-empty string without surrounding whitespace. None, "",
    numbers and lists are never an identity, so two missing identities never match."""
    return isinstance(x, str) and x != "" and x == x.strip()


def check_request(req) -> None:
    """The request context comes from the authenticated channel and from a trusted
    owner binding, never from the document. The resolver demands it typed."""
    r = req.get("requestor") if isinstance(req, dict) else None
    if req.get("op") not in OPS or not isinstance(r, dict) or type(r.get("authenticated")) is not bool:
        raise PolicyError("INVALID_REQUEST_CONTEXT", "op / requestor / authenticated")
    if r["authenticated"]:
        subj = r.get("subject")
        if not (isinstance(subj, str) and PATTERN_RE.match(subj) and "*" not in subj):
            raise PolicyError("INVALID_REQUEST_CONTEXT", "subject")
    owner = req.get("owner")
    if owner is not None and (not isinstance(owner, dict) or owner.get("trust") not in ("trusted", "untrusted")):
        raise PolicyError("INVALID_REQUEST_CONTEXT", "owner.trust")


def _decide_symbol(symbol, layer, req):
    r = req["requestor"]
    if not r["authenticated"]:
        return {"outcome": "deny", "code": "UNAUTHENTICATED", "layer": layer}
    if symbol == "open":
        return {"outcome": "allow", "code": None, "layer": layer}
    owner = req.get("owner")
    if not owner or owner.get("trust") != "trusted":  # fault-site: owner-trust
        return {"outcome": "deny", "code": "OWNER_NOT_TRUSTED", "layer": layer}
    if not _valid_identity(owner.get("identity")):  # fault-site: owner-identity
        return {"outcome": "deny", "code": "OWNER_IDENTITY_INVALID", "layer": layer}
    if not _valid_identity(r.get("identity")):  # fault-site: requestor-identity
        return {"outcome": "deny", "code": "REQUESTOR_IDENTITY_INVALID", "layer": layer}
    if owner.get("identity") != r.get("identity"):
        return {"outcome": "deny", "code": "OWNER_MISMATCH", "layer": layer}
    return {"outcome": "allow", "code": None, "layer": layer}


def _decide(kind_v, layer, req):
    kind, v = kind_v
    return _decide_list(v, layer, req) if kind == "list" else _decide_symbol(v, layer, req)


def _local_rule(pol, surface, op):
    """Layers 2 and 3 of one object: declared surface rule, then declared default."""
    if pol in ("absent", "unknown"):
        return None
    hit = pol["rules"].get((surface, op))
    if hit is not None:
        return (("list", hit), "surface_rules")
    if op in pol["declared"]:
        return (pol["declared"][op], "default")
    return None


def resolve(ctx: dict, target: dict, req: dict, grammar: int) -> dict:
    """Deterministic resolution of one (object, surface, field, operation).

    Every input is declared. A missing object, a cycle or an unknown policy that
    the walk has to read yields outcome `error`, never an invented permission."""
    try:
        check_request(req)
    except PolicyError as ex:
        return {"outcome": "error", "code": ex.code, "layer": "none"}
    op = req["op"]
    objs = {}
    for oid, o in ctx["objects"].items():
        car = o.get("carrier")
        objs[oid] = {
            "parent": o.get("parent"),
            "policy": read_policy(o.get("policy", "absent"), grammar),
            "carrier": None if car is None else {
                "mode": read_mode(car.get("inherit", write_mode("inherit", grammar)), grammar),
                "access": read_rule(car.get("access", "inherit")),
                "modify": read_rule(car.get("modify", "inherit")),
            },
        }
    if target["object"] not in objs:
        return {"outcome": "error", "code": "CONTEXT_INCOMPLETE", "layer": "none"}
    cur = objs[target["object"]]

    # layer 1: explicit field-level rule of the target field itself
    kind, v = read_rule(target["field"].get(op, "inherit"))
    if kind == "list":
        return _decide((kind, v), "field", req)

    # layers 2-3: local surface_rules, local default_*
    if cur["policy"] == "unknown":
        return {"outcome": "error", "code": "POLICY_CONTEXT_UNKNOWN", "layer": "none"}
    hit = _local_rule(cur["policy"], target["surface"], op)
    if hit:
        return _decide(hit[0], hit[1], req)

    # layer 4a: field-level rule passed down by carrier fields (nearest explicit wins)
    reset_barrier = False
    field_open = True
    seen = {target["object"]}
    o = cur
    while True:
        # An object-level reset cuts what this object takes from above, carrier rule included.
        if isinstance(o["policy"], dict) and o["policy"]["mode"] == "reset":  # fault-site: object-reset-first
            reset_barrier = True
            break
        if o["carrier"] is None:
            break
        if o["policy"] == "unknown" and o is not cur:
            return {"outcome": "error", "code": "POLICY_CONTEXT_UNKNOWN", "layer": "none"}
        mode = o["carrier"]["mode"]
        if mode == "reset":
            reset_barrier = True
            field_open = False
            break
        if mode == "no-inherit":
            field_open = False
        elif field_open:
            ck, cv = o["carrier"][op]
            if ck == "list":
                return _decide((ck, cv), "field_inherited", req)
        if o["parent"] is None or o["parent"] not in objs or o["parent"] in seen:
            return {"outcome": "error", "code": "CONTEXT_INCOMPLETE", "layer": "none"}
        seen.add(o["parent"])
        o = objs[o["parent"]]

    # layer 4b: inherited PolicySurface chain, only where each step permits it
    seen = {target["object"]}
    o = cur
    while True:
        pol_mode = o["policy"]["mode"] if isinstance(o["policy"], dict) else None
        if pol_mode == "reset":
            reset_barrier = True
            break
        if pol_mode == "no-inherit":
            break
        if o["carrier"] is not None and o["carrier"]["mode"] == "reset":
            reset_barrier = True
            break
        pid = o["parent"]
        if pid is None:
            break
        if pid not in objs or pid in seen:
            return {"outcome": "error", "code": "CONTEXT_INCOMPLETE", "layer": "none"}
        seen.add(pid)
        o = objs[pid]
        if o["policy"] == "unknown":
            return {"outcome": "error", "code": "POLICY_CONTEXT_UNKNOWN", "layer": "none"}
        hit = _local_rule(o["policy"], target["surface"], op)
        if hit:
            return _decide(hit[0], "policy_inherited", req)

    # layer 5: documented system default, never after a reset barrier
    if reset_barrier:
        return {"outcome": "deny", "code": "RESET_NO_LOCAL_RULE", "layer": "none"}
    return _decide(("symbol", SYSTEM_SYMBOL[op]), "system", req)
