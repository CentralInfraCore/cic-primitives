#!/usr/bin/env python3
"""Draft composition of the release schema fragments (design evidence; not the production tool).
usage: compose.py <dir> <Kind>   writes the composed composition to stdout. A collision exits with schema_field_collision."""
import sys, yaml, copy


class Collision(Exception):
    pass


def merge(a, b, path):
    names = {n["name"]: n for n in a}
    for n in b:
        if n["name"] not in names:
            a.append(copy.deepcopy(n))
            continue
        old = names[n["name"]]
        if old.get("shape_type") == "composite" and n.get("shape_type") == "composite":
            merge(old["fields"], n["fields"], path + "." + n["name"])
        else:
            raise Collision("schema_field_collision at %s.%s" % (path, n["name"]))


def compose(d, kind):
    comp = yaml.safe_load(open(d + "/composition.yaml"))["composition"]
    common = yaml.safe_load(open(d + "/" + comp["common"]))
    part = yaml.safe_load(open(d + "/" + comp["kinds"][kind]["part"]))
    return compose_parts(common, part, kind)


def compose_parts(common, part, kind):
    out = copy.deepcopy(common)
    cs = out["spec"]["config_surface"]
    merge(cs["nodes"], part["spec"]["config_surface"]["nodes"], "$")
    v = (common["spec"]["config_surface"].get("validation") or []) + (part["spec"]["config_surface"].get("validation") or [])
    if v:
        cs["validation"] = v
    out["spec"]["identity"]["kind"] = kind
    return out


if __name__ == "__main__":
    try:
        yaml.safe_dump(compose(sys.argv[1], sys.argv[2]), sys.stdout, sort_keys=False, width=200)
    except Collision as e:
        sys.exit(str(e))
