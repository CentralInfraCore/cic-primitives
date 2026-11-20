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
run("an unknown verifier reason", decl(lambda d: d["contracts"][0]["verifier"].update(reasons=["no_such_reason"])))
run("an empty verifier-only list", decl(lambda d: d.update(verifier_only=[])))
run("the Form no longer lists a node of the probe", lambda p: None, probe_mut=lambda t: t.replace("$.version,", "", 1))
run("the probe output lacks the compile line of a kind", lambda p: None, probe_mut=lambda t: "\n".join(l for l in t.split("\n") if not l.startswith("K02_module_release|-|compile")))
# composition
sys.path.insert(0, HERE)
import compose as C
common = yaml.safe_load(open(os.path.join(HERE, "common.yaml")))
def comp_part(nodes):
    return {"spec": {"config_surface": {"nodes": nodes, "validation": []}}}
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
try:
    out = C.compose_parts(common, comp_part([{"name": "provenance", "shape_type": "composite", "fields": [{"name": "extra", "shape_type": "scalar", "scalar_type": "string"}]}]), "X")
    names = [f["name"] for n in out["spec"]["config_surface"]["nodes"] if n["name"] == "provenance" for f in n["fields"]]
    ok = names == ["envelope", "source_commit", "extra"]
except Exception:
    ok = False
print("%-70s -> %s" % ("composition: a kind part ADDS a field to provenance (merged by path)", "merged as expected" if ok else "UNEXPECTED"))
results.append(ok)
print("%d of %d checks as expected" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
