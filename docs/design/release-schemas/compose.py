#!/usr/bin/env python3
"""Draft composition of the release schema fragments (design evidence; not the production tool).
usage: compose.py <dir> <Kind>   writes the composed composition to stdout. A collision exits with schema_field_collision."""
import sys, yaml, copy


class Collision(Exception):
    pass


def check_names(nodes, path):
    """A duplicate field name inside one node list (of either part) is an error, at every depth."""
    seen = set()
    for n in nodes:
        if n["name"] in seen:
            raise Collision("schema_field_collision: duplicate field name at %s.%s" % (path, n["name"]))
        seen.add(n["name"])
        for key in ("fields", "item_fields"):
            if n.get(key):
                check_names(n[key], path + "." + n["name"] + ("[]" if key == "item_fields" else ""))


def merge(a, b, path):
    """Field extension only. A same-name composite is merged only if every attribute other than 'fields' is identical
    (mandatory, optional, nullable, contract, ...): otherwise a kind-part constraint could be dropped or a common one redefined."""
    names = {n["name"]: n for n in a}
    for n in b:
        if n["name"] not in names:
            c = copy.deepcopy(n)
            a.append(c)
            names[n["name"]] = c
            continue
        old = names[n["name"]]
        if old.get("shape_type") == "composite" and n.get("shape_type") == "composite":
            ra = {k: v for k, v in old.items() if k != "fields"}
            rb = {k: v for k, v in n.items() if k != "fields"}
            if ra != rb:
                diff = sorted(k for k in set(ra) | set(rb) if ra.get(k) != rb.get(k))
                raise Collision("schema_field_collision: attribute conflict at %s.%s (%s)" % (path, n["name"], ", ".join(diff)))
            merge(old["fields"], n["fields"], path + "." + n["name"])
        else:
            raise Collision("schema_field_collision at %s.%s" % (path, n["name"]))


def compose(d, kind):
    comp = yaml.safe_load(open(d + "/composition.yaml"))["composition"]
    common = yaml.safe_load(open(d + "/" + comp["common"]))
    part = yaml.safe_load(open(d + "/" + comp["kinds"][kind]["part"]))
    return compose_parts(common, part, kind)


def compose_parts(common, part, kind):
    # a kind part may only carry what the composition knows how to add: nothing is silently ignored
    if set(part) != {"spec"} or set(part["spec"]) != {"identity", "config_surface"}:
        raise Collision("schema_field_collision: the kind part has members outside spec.identity and spec.config_surface")
    pcs, ccs = part["spec"]["config_surface"], common["spec"]["config_surface"]
    if not set(pcs) <= {"aggregate_ref", "nodes", "validation"}:
        raise Collision("schema_field_collision: the kind part config_surface has unknown keys %s" % sorted(set(pcs) - {"aggregate_ref", "nodes", "validation"}))
    if pcs.get("aggregate_ref") != ccs.get("aggregate_ref"):
        raise Collision("schema_field_collision: aggregate_ref differs between the parts")
    check_names(ccs["nodes"], "$")
    check_names(pcs["nodes"], "$")
    out = copy.deepcopy(common)
    cs = out["spec"]["config_surface"]
    merge(cs["nodes"], pcs["nodes"], "$")
    v = (ccs.get("validation") or []) + (pcs.get("validation") or [])
    if v:
        cs["validation"] = v
    out["spec"]["identity"]["kind"] = kind
    return out


if __name__ == "__main__":
    try:
        yaml.safe_dump(compose(sys.argv[1], sys.argv[2]), sys.stdout, sort_keys=False, width=200)
    except Collision as e:
        sys.exit(str(e))
