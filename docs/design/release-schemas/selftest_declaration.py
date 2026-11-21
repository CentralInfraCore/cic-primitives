#!/usr/bin/env python3
"""Negative tests of check_declaration.py and of the composition: every planted defect must be refused; the real set must pass.
usage: selftest_declaration.py <probe-output>"""
import os, re, shutil, subprocess, sys, tempfile, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
probe = os.path.abspath(sys.argv[1])
results = []

def run(label, mutate, expect_fail=True, probe_mut=None):
    d = tempfile.mkdtemp()
    shutil.copytree(HERE, d + "/docs/design/release-schemas", ignore=shutil.ignore_patterns("__pycache__"))
    os.makedirs(d + "/docs/en", exist_ok=True)
    shutil.copy(os.path.join(HERE, "..", "..", "en", "RELEASE-RECORD-CONTRACT.md"), d + "/docs/en/")
    mutate(d + "/docs/design/release-schemas")
    pr = d + "/probe.txt"
    text = open(probe, encoding="utf-8").read()
    open(pr, "w", encoding="utf-8").write(probe_mut(text) if probe_mut else text)
    r = subprocess.run([sys.executable, d + "/docs/design/release-schemas/check_declaration.py", pr], capture_output=True, text=True)
    failed = r.returncode != 0
    ok = failed == expect_fail
    why = next((l[9:] for l in r.stdout.splitlines() if l.startswith("PROBLEM: ")), "")
    print("%-62s -> %s (%s)%s" % (label, "refused" if failed else "ACCEPTED", "as expected" if ok else "UNEXPECTED", ("  [" + why[:70] + "]") if why else ""))
    results.append(ok)

def edit_yaml(path, f):
    d = yaml.safe_load(open(path)); f(d); open(path, "w").write(yaml.safe_dump(d, sort_keys=False, width=1000))
decl = lambda f: (lambda p: edit_yaml(p + "/contract-conformance.yaml", f))
part = lambda name, f: (lambda p: edit_yaml(p + "/" + name, f))
run("the real set", lambda p: None, expect_fail=False)
run("a declaration entry removed", decl(lambda d: d["contracts"].pop(0)))
run("a declaration entry duplicated", decl(lambda d: d["contracts"].append(dict(d["contracts"][0]))))
run("a contract added to a part and not declared", part("common.yaml", lambda d: d["spec"]["config_surface"]["nodes"][0].update(contract=[{"type": "pattern", "expression": "^x$"}])))
run("an evaluation status inside a schema part", part("common.yaml", lambda d: d["spec"]["config_surface"]["nodes"][1]["contract"][0].update(status="unevaluated")))
run("a node-level entry declared with the wrong status", decl(lambda d: d["contracts"][0]["form"].update(status="evaluated")))
run("a surface-level entry declared unevaluated", decl(lambda d: [e for e in d["contracts"] if e["location"] == "surface"][0]["form"].update(status="unevaluated")))
run("an unknown verifier reason", decl(lambda d: [e for e in d["contracts"] if e["id"] == "C05"][0]["verifier"].update(reasons=["no_such_reason"])))
def gone(sect, i):
    return decl(lambda d: d[sect].pop(i))
run("a further requirement (owner of artifact_order) removed", decl(lambda d: d["further_requirements"].remove([e for e in d["further_requirements"] if e["id"] == "V03"][0])))
run("every further requirement removed (empty list)", decl(lambda d: d.update(further_requirements=[])))
run("a global admission requirement (G01) removed", decl(lambda d: d["global_requirements"].remove([e for e in d["global_requirements"] if e["id"] == "G01"][0])))
run("G02 weakened: no 2^53-1 over the whole tree", decl(lambda d: [e for e in d["global_requirements"] if e["id"] == "G02"][0].update(text="integers are checked")))
run("an implemented requirement with an empty reason list", decl(lambda d: d["contracts"][0]["verifier"].update(status="implemented", reasons=[])))
run("not_implemented without a note", decl(lambda d: d["contracts"][0]["verifier"].update(note="")))
run("implemented claimed for a plan-only reason", decl(lambda d: [e for e in d["global_requirements"] if e["id"] == "G02"][0].update(status="implemented")))
run("an unknown status word", decl(lambda d: d["contracts"][0]["verifier"].update(status="done")))
def further(i):
    return lambda d: [e for s in ("further_requirements", "global_requirements") for e in d[s] if e["id"] == i][0]
run("F2.1: the owner removed from G02", decl(lambda d: further("G02")(d).pop("owner")))
run("F2.1: the owner of a contract entry removed", decl(lambda d: d["contracts"][4]["verifier"].pop("owner")))
run("F2.1: an owner that does not exist", decl(lambda d: further("V03")(d).update(owner="the_verifier_team")))
run("F2.1: an empty owner", decl(lambda d: further("V03")(d).update(owner="")))
run("F2.1: owner none on an implemented requirement", decl(lambda d: further("V03")(d).update(owner="none")))
run("F2.1: not_implemented that still names an executor", decl(lambda d: d["contracts"][0]["verifier"].update(owner="verifier")))
run("F2.1: not_implemented that still names reasons", decl(lambda d: d["contracts"][0]["verifier"].update(reasons=["artifact_order"])))
run("F2.1: the composition reason owned by the verifier", decl(lambda d: further("G04")(d).update(owner="verifier")))
run("F2.1: a producer reason owned by the verifier", decl(lambda d: further("P01")(d).update(owner="verifier")))
run("F2.1: a verifier reason owned by the composition", decl(lambda d: further("V03")(d).update(owner="composition")))
run("P5.1: the module name requirement (V08) removed", decl(lambda d: d["further_requirements"].remove(further("V08")(d))))
run("P5.2: the producer requirement (P01) removed", decl(lambda d: d["further_requirements"].remove(further("P01")(d))))
# decision P7: integer_out_of_range is refused by the producer AND, independently, by the verifier
run("P7: the producer requirement (P02) removed", decl(lambda d: d["further_requirements"].remove(further("P02")(d))))
run("P7: integer_out_of_range removed from G02 (no verifier executor)", decl(lambda d: further("G02")(d).update(reasons=["value_type_unsupported"])))
run("P7: value_type_unsupported removed from G02 (a type error has no owner)", decl(lambda d: further("G02")(d).update(reasons=["integer_out_of_range"])))
run("P7: G02 no longer says the verifier checks independently", decl(lambda d: further("G02")(d).update(text=further("G02")(d)["text"].replace("independently", "together with"))))
run("P7: the new reason owned by the composition", decl(lambda d: further("P02")(d).update(owner="composition")))
run("P7: P02 downgraded to not_implemented (the producer check silently absent)", decl(lambda d: further("P02")(d).update(status="not_implemented", owner="none", reasons=[], note="x")))
run("P7: the verifier executor is the producer (G02 owned by the producer)", decl(lambda d: further("G02")(d).update(owner="producer")))
run("a requirement downgraded to not_implemented loses its reason's owner", decl(lambda d: further("V03")(d).update(status="not_implemented", owner="none", reasons=[], note="x")))
def dup_contract(d):
    n = d["spec"]["config_surface"]["nodes"][1]
    n["contract"] = n["contract"] + n["contract"]
run("the same contract entry twice in a part (would overwrite)", part("common.yaml", dup_contract))
run("the Form no longer lists a node of the probe", lambda p: None, probe_mut=lambda t: t.replace("$.version,", "", 1))
run("the probe output lacks the compile line of a kind", lambda p: None, probe_mut=lambda t: "\n".join(l for l in t.split("\n") if not l.startswith("K02_module_release|-|compile")))
# composition
sys.path.insert(0, HERE)
import compose as C
common = yaml.safe_load(open(os.path.join(HERE, "common.yaml")))
def comp_part(nodes):
    return {"spec": {"identity": {}, "config_surface": {"aggregate_ref": common["spec"]["config_surface"]["aggregate_ref"], "nodes": nodes, "validation": []}}}
def comp_fails(label, nodes):
    try:
        C.compose_parts(common, comp_part(nodes), "X"); failed = False
    except C.Collision:
        failed = True
    ok = failed
    print("%-70s -> %s (%s)" % (label, "refused" if failed else "ACCEPTED", "as expected" if ok else "UNEXPECTED"))
    results.append(ok)
comp_fails("composition: a kind part redefines the common node 'kind'", [{"name": "kind", "shape_type": "scalar", "scalar_type": "string"}])
comp_fails("composition: a kind part redefines provenance.source_commit", [{"name": "provenance", "shape_type": "composite", "fields": [{"name": "source_commit", "shape_type": "scalar", "scalar_type": "string"}]}])
comp_fails("composition: a kind part replaces a composite by a scalar", [{"name": "artifacts", "shape_type": "scalar", "scalar_type": "string"}])
def prov(**kw):
    return [dict({"name": "provenance", "shape_type": "composite", "fields": [{"name": "extra", "shape_type": "scalar", "scalar_type": "string"}]}, **kw)]
cprov = [n for n in common["spec"]["config_surface"]["nodes"] if n["name"] == "provenance"][0]
comp_fails("composition: the kind part relaxes the composite (mandatory differs)", prov(mandatory=not cprov.get("mandatory", False)))
comp_fails("composition: the kind part adds a contract to the common composite", prov(contract=[{"type": "must", "expression": "true()"}]))
comp_fails("composition: the kind part adds an optional flag the common lacks", prov(optional=True))
comp_fails("composition: a duplicate field name inside the kind part", [{"name": "a", "shape_type": "scalar", "scalar_type": "string"}, {"name": "a", "shape_type": "scalar", "scalar_type": "string"}])
comp_fails("composition: a duplicate nested name inside the kind part", [{"name": "g", "shape_type": "composite", "fields": [{"name": "x", "shape_type": "scalar", "scalar_type": "string"}, {"name": "x", "shape_type": "scalar", "scalar_type": "string"}]}])
try:
    C.compose_parts(common, {"spec": {"identity": {}, "config_surface": {"aggregate_ref": "other", "nodes": [], "validation": []}}}, "X"); ok = False
except C.Collision:
    ok = True
print("%-70s -> %s" % ("composition: a kind part with a different aggregate_ref", "refused, as expected" if ok else "ACCEPTED, UNEXPECTED"))
results.append(ok)
bad = {"spec": {"identity": {}, "config_surface": {"nodes": [], "validation": [], "extra_key": 1}}}
try:
    C.compose_parts(common, bad, "X"); ok = False
except C.Collision:
    ok = True
print("%-70s -> %s" % ("composition: a kind part with an unknown config_surface key", "refused, as expected" if ok else "ACCEPTED, UNEXPECTED"))
results.append(ok)
try:
    out = C.compose_parts(common, comp_part([dict({k: v for k, v in cprov.items() if k != "fields"}, **{"fields": [{"name": "extra", "shape_type": "scalar", "scalar_type": "string"}]})]), "X")
    names = [f["name"] for n in out["spec"]["config_surface"]["nodes"] if n["name"] == "provenance" for f in n["fields"]]
    ok = names == ["envelope", "source_commit", "extra"]
except Exception:
    ok = False
print("%-70s -> %s" % ("composition: a kind part ADDS a field to provenance (merged by path)", "merged as expected" if ok else "UNEXPECTED"))
results.append(ok)
print("%d of %d checks as expected" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
