#!/usr/bin/env python3
"""Checks the contract conformance declaration against the schema parts and the probe evidence (design evidence; draft).
usage: check_declaration.py <probe-output (go-output.txt)>

  1. every contract entry of the parts (node level and surface level) has exactly one declaration entry, and the reverse (part, location, type, expression);
  2. the parts carry NO evaluation status: a contract entry has only type, expression (and error_message, description); the status lives in the declaration only;
  3. the Form status is checked against the probe: the nodes the Form lists as unevaluated are exactly the nodes that declare a contract (surface-level
     validation entries are not nodes: status not_reported, and none is listed);
  4. every verifier reason is a reason of the contract (section 11 table) or one the generalization plan adds;
  5. every known reason identifier and every normative requirement has an owner with an explicit status (implemented | planned | not_implemented); the global
     admission requirements (G01-G03, incl. the 2^53-1 bound over the whole tree) are present. A removed owner is an error.
Exit 0 only if all hold."""
import os, re, sys, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compose as C
PLAN_REASONS = {"kind_missing", "kind_unsupported", "kind_schema_violation", "schema_field_collision"}
A_REASONS = {"reading_differs", "reading_key_differs", "reading_structure_differs", "reading_value_differs", "duplicate_key", "key_not_string",
             "value_type_unsupported", "alias_forbidden", "merge_key_forbidden", "tag_forbidden", "multiple_documents", "encoding_form"}
BLOB_REASONS = {"artifact_absent", "artifact_digest_mismatch", "artifact_not_regular"}
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
        if key(part, loc, c) in from_parts:
            problems.append("1: the parts declare %s twice (a duplicate would overwrite)" % (key(part, loc, c),))
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
# 4. reasons and ownership: every requirement has an explicit status; every known reason has an owner
doc = open(os.path.join(HERE, "..", "..", "en", "RELEASE-RECORD-CONTRACT.md"), encoding="utf-8").read()
table = set(re.findall(r"^\| `([a-z_]+)` \|", doc, re.M))
IMPLEMENTED = table | BLOB_REASONS          # reasons the reference verifier makes today
PLANNED = PLAN_REASONS | A_REASONS           # named by the generalization plan, no code yet
inventory = IMPLEMENTED | PLANNED
STATUSES = {"implemented", "planned", "not_implemented", "implemented_draft"}
owned = {}
def account(rid, status, reasons, note):
    if status not in STATUSES:
        problems.append("4: %s has the status %r (allowed: %s)" % (rid, status, sorted(STATUSES))); return
    if status == "not_implemented":
        if reasons: problems.append("4: %s is not_implemented but names reasons %s" % (rid, reasons))
        if not note: problems.append("4: %s is not_implemented without a note saying why and what interim check exists" % rid)
        return
    if not reasons:
        problems.append("4: %s has the status %s and no reason: an executor must be named, or the status is not_implemented" % (rid, status)); return
    for r in reasons:
        if r not in inventory:
            problems.append("4: %s names the reason %r, which is neither in the contract table nor named by the plan" % (rid, r)); continue
        if status == "implemented" and r not in IMPLEMENTED:
            problems.append("4: %s claims implemented for %r, which the reference verifier does not make" % (rid, r))
        if status == "planned" and r in IMPLEMENTED:
            problems.append("4: %s says planned for %r, which the reference verifier already makes" % (rid, r))
        owned.setdefault(r, []).append(rid)
for e in declared["contracts"]:
    account(e["id"], e["verifier"].get("status"), e["verifier"]["reasons"], e["verifier"].get("note"))
for sect in ("further_requirements", "global_requirements"):
    items = declared.get(sect)
    if not items:
        problems.append("5: the %s list is missing or empty" % sect); continue
    for e in items:
        account(e["id"], e.get("status"), e.get("reasons") or [], e.get("note") or e.get("text"))
all_ids = [e["id"] for s in ("contracts", "further_requirements", "global_requirements") for e in declared.get(s) or []]
if len(all_ids) != len(set(all_ids)):
    problems.append("5: duplicate requirement ids across the declaration")
for r in sorted(inventory - set(owned)):
    problems.append("5: the reason %r has no owner in the declaration (a normative check would be silently absent)" % r)
for g in ("G01", "G02", "G03"):
    if g not in {e["id"] for e in declared.get("global_requirements") or []}:
        problems.append("5: the global admission requirement %s is missing" % g)
g2 = [e for e in declared.get("global_requirements") or [] if e["id"] == "G02"]
if g2 and not ("2^53" in g2[0].get("text", "") and "opaque" in g2[0].get("text", "")):
    problems.append("5: G02 must state the 2^53-1 bound over the whole tree including opaque members")
node_n = sum(1 for k in from_decl if k[1] != "surface")
print("contracts declared %d (node level %d, surface level %d); further requirements %d; global requirements %d; known reasons %d, all owned" % (len(from_decl), node_n, len(from_decl) - node_n, len(declared["further_requirements"]), len(declared["global_requirements"]), len(inventory)))
for k, v in listed.items():
    print("the Form lists %d unevaluated nodes for %s" % (len(v), k))
for p in problems:
    print("PROBLEM: " + p)
print("RESULT: " + ("INCONSISTENT" if problems else "CONSISTENT"))
sys.exit(1 if problems else 0)
