#!/usr/bin/env python3
"""Checks the contract conformance declaration against the schema parts and the probe evidence (design evidence; draft).
usage: check_declaration.py <probe-output (go-output.txt)>

  1. every contract entry of the parts (node level and surface level) has exactly one declaration entry, and the reverse (part, location, type, expression);
  2. the parts carry NO evaluation status: a contract entry has only type, expression (and error_message, description); the status lives in the declaration only;
  3. the Form status is checked against the probe: the nodes the Form lists as unevaluated are exactly the nodes that declare a contract (surface-level
     validation entries are not nodes: status not_reported, and none is listed);
  4. every verifier reason is a reason of the contract (section 11 table) or one the generalization plan adds;
  5. the verifier-only list is not empty.
Exit 0 only if all hold."""
import os, re, sys, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compose as C
PLAN_REASONS = {"kind_missing", "kind_unsupported", "kind_schema_violation", "schema_field_collision"}
problems = []

def node_contracts(nodes, path):
    for n in nodes:
        p = path + "." + n["name"]
        for c in n.get("contract") or []:
            yield p, c
        if n.get("shape_type") == "composite":
            yield from node_contracts(n["fields"], p)
        if n.get("shape_type") == "collection" and n.get("item_fields"):
            yield from node_contracts(n["item_fields"], p + "[]")

parts = {}
for part, f in (("common", "common.yaml"), ("primitive-release", "primitive-release.yaml"), ("module-release", "module-release.yaml")):
    d = yaml.safe_load(open(os.path.join(HERE, f)))["spec"]["config_surface"]
    ents = [(part, loc, c) for loc, c in node_contracts(d["nodes"], "$")] + [(part, "surface", c) for c in d.get("validation") or []]
    parts[part] = ents
declared = yaml.safe_load(open(os.path.join(HERE, "contract-conformance.yaml")))
key = lambda part, loc, c: (part, loc, c["type"], repr(c["expression"]))
from_parts = {}
for ents in parts.values():
    for part, loc, c in ents:
        extra = set(c) - {"type", "expression", "error_message", "description"}
        if extra:
            problems.append("2: the contract at %s %s carries %s (an evaluation status belongs in the declaration only)" % (part, loc, sorted(extra)))
        from_parts[key(part, loc, c)] = c
ids = [e["id"] for e in declared["contracts"]]
if len(ids) != len(set(ids)):
    problems.append("1: duplicate ids in the declaration")
from_decl = {}
for e in declared["contracts"]:
    k = (e["part"], e["location"], e["type"], repr(e["expression"]))
    if k in from_decl:
        problems.append("1: %s is declared twice" % (k,))
    from_decl[k] = e
for k in from_parts:
    if k not in from_decl:
        problems.append("1: a contract of the parts is not declared: %s" % (k,))
for k in from_decl:
    if k not in from_parts:
        problems.append("1: a declared contract does not exist in the parts: %s" % (k,))
# 3. the Form status against the probe
out = open(sys.argv[1], encoding="utf-8").read().splitlines()
listed = {}
for line in out:
    p = line.split("|", 3)
    if len(p) == 4 and p[1] == "-" and p[2] == "compile" and p[3].startswith("OK|unevaluated="):
        listed[p[0]] = set(filter(None, p[3].split("=", 1)[1].split(",")))
cases = {"K01_primitive_release": "PrimitiveRelease", "K02_module_release": "ModuleRelease"}
for case, kind in cases.items():
    comp = C.compose(HERE, kind)["spec"]["config_surface"]
    expect = {loc for loc, c in node_contracts(comp["nodes"], "$")}
    if case not in listed:
        problems.append("3: no compile line for %s in the probe output" % case); continue
    if listed[case] != expect:
        problems.append("3: %s: the Form lists %s, the nodes declaring a contract are %s" % (case, sorted(listed[case] ^ expect), "different"))
    for k, e in from_decl.items():
        part, loc = k[0], k[1]
        if part not in ("common", "primitive-release" if kind == "PrimitiveRelease" else "module-release"):
            continue
        if loc == "surface":
            if e["form"]["status"] != "not_reported":
                problems.append("3: %s is a surface-level entry and must have the status not_reported" % e["id"])
        elif e["form"]["status"] == "unevaluated" and loc not in listed[case]:
            problems.append("3: %s is declared unevaluated but the Form does not list %s for %s" % (e["id"], loc, kind))
        elif e["form"]["status"] != "unevaluated":
            problems.append("3: %s is a node-level entry and must have the status unevaluated" % e["id"])
# 4. reasons
doc = open(os.path.join(HERE, "..", "..", "en", "RELEASE-RECORD-CONTRACT.md"), encoding="utf-8").read()
known = set(re.findall(r"^\| `([a-z_]+)` \|", doc, re.M)) | PLAN_REASONS
for e in declared["contracts"]:
    for r in e["verifier"]["reasons"]:
        if r not in known:
            problems.append("4: %s names the reason %r, which is neither in the contract table nor added by the plan" % (e["id"], r))
if not declared.get("verifier_only"):
    problems.append("5: the verifier-only list is empty")
node_n = sum(1 for k in from_decl if k[1] != "surface")
print("contracts declared %d (node level %d, surface level %d); verifier-only checks %d; known reasons %d" % (len(from_decl), node_n, len(from_decl) - node_n, len(declared["verifier_only"]), len(known)))
for k, v in listed.items():
    print("the Form lists %d unevaluated nodes for %s" % (len(v), k))
for p in problems:
    print("PROBLEM: " + p)
print("RESULT: " + ("INCONSISTENT" if problems else "CONSISTENT"))
sys.exit(1 if problems else 0)
