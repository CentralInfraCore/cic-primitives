#!/usr/bin/env python3
"""Cases for the draft release schemas: the composed schema of each kind and documents derived from the (sanitized) published v0.2.1 record.
usage: gen_cases.py <dir> | --inventory      Document prefix: pos_ conforming, neg_ the Form must refuse, inf_ recorded (a constraint the Form does not evaluate)."""
import copy, os, sys, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
DESIGN = os.path.join(HERE, "..", "..", "design", "release-schemas")
sys.path.insert(0, DESIGN)
import compose as C
INVENTORY = sys.argv[1] == "--inventory"
OUT = None if INVENTORY else sys.argv[1]
base = yaml.safe_load(open(os.path.join(HERE, "base-record.yaml")))
dump = lambda d: yaml.safe_dump(d, sort_keys=False, width=200)

def mod(f):
    d = copy.deepcopy(base); f(d); return dump(d)

def module_record():
    d = copy.deepcopy(base)
    d["kind"] = "ModuleRelease"
    items = list(d.items())
    d = dict(items[:1] + [("name", "PLACEHOLDER-module-name")] + items[1:])   # ModuleRelease-specific member (review #38 P5.1)
    del d["specs"]
    for k in ("dependency_lock_sha256", "grammar_sha256", "grammar_schema_sha256"):
        del d["provenance"][k]
    files = d["artifacts"]["files"]
    files += [{"path": "module/module.wasm", "digest": "sha256:" + "a" * 64}, {"path": "project.yaml", "digest": "sha256:" + "b" * 64}]
    files.sort(key=lambda e: e["path"].encode())
    return d
mdump = lambda f: (lambda d: (f(d), dump(d))[1])(module_record())

def schema_text(kind):
    return yaml.safe_dump(C.compose(DESIGN, kind), sort_keys=False, width=200)

cases = {}
def case(cid, desc, kind, docs):
    cases[cid] = (desc, schema_text(kind), docs)

case("K01_primitive_release", "the composed PrimitiveRelease schema against the sanitized published v0.2.1 record and defects", "PrimitiveRelease", {
  "pos_published_shape": dump(base),
  "pos_without_countersign": mod(lambda d: d.pop("cic_countersign")),
  "neg_missing_source_commit": mod(lambda d: d["provenance"].pop("source_commit")),
  "neg_unknown_top_field": mod(lambda d: d.update(extra="x")),
  "neg_unknown_provenance_field": mod(lambda d: d["provenance"].update(foo="x")),
  "neg_module_name_in_primitive_record": mod(lambda d: d.update(name="x")),
  "neg_duplicate_artifact_path": mod(lambda d: d["artifacts"]["files"].insert(1, copy.deepcopy(d["artifacts"]["files"][0]))),
  "neg_empty_files": mod(lambda d: d["artifacts"].update(files=[])),
  "neg_missing_specs": mod(lambda d: d.pop("specs")),
  "neg_missing_grammar_digest": mod(lambda d: d["provenance"].pop("grammar_sha256")),
  "neg_countersign_without_authority": mod(lambda d: d["cic_countersign"].pop("authority")),
  "neg_envelope_as_string": mod(lambda d: d["provenance"].update(envelope="3")),
  "inf_bad_version": mod(lambda d: d.update(version="x")),
  "inf_bad_source_commit": mod(lambda d: d["provenance"].update(source_commit="ZZZ")),
  "inf_bad_kind": mod(lambda d: d.update(kind="Other")),
  "inf_bad_digest_form": mod(lambda d: d["artifacts"]["files"][0].update(digest="abc")),
  "inf_unsorted_artifacts": mod(lambda d: d["artifacts"]["files"].reverse()),
  "inf_envelope_4": mod(lambda d: d["provenance"].update(envelope=4)),
})
case("K02_module_release", "the composed ModuleRelease schema against a ModuleRelease record built from the same base (no specs)", "ModuleRelease", {
  "pos_module_sample": dump(module_record()),
  "neg_specs_present": mdump(lambda d: d.update(specs=copy.deepcopy(base["specs"]))),
  "neg_primitive_provenance_field": mdump(lambda d: d["provenance"].update(grammar_sha256="x")),
  "neg_missing_kind": mdump(lambda d: d.pop("kind")),
  "neg_missing_name": mdump(lambda d: d.pop("name")),
  "neg_name_not_a_string": mdump(lambda d: d.update(name=7)),
  "inf_name_differs_from_descriptor_identity": mdump(lambda d: d.update(name="another-module")),
  "inf_kind_is_primitive_release": mdump(lambda d: d.update(kind="PrimitiveRelease")),
  "inf_required_wasm_path_absent": mdump(lambda d: d["artifacts"].update(files=[f for f in d["artifacts"]["files"] if f["path"] != "module/module.wasm"])),
  "inf_required_descriptor_path_absent": mdump(lambda d: d["artifacts"].update(files=[f for f in d["artifacts"]["files"] if f["path"] != "project.yaml"])),
})
case("K03_primitive_record_against_module_schema", "a PrimitiveRelease record against the ModuleRelease schema (the kind parts must not mix)", "ModuleRelease", {
  "neg_primitive_record": dump(base)})
case("K04_module_record_against_primitive_schema", "a ModuleRelease record against the PrimitiveRelease schema", "PrimitiveRelease", {
  "neg_module_record": dump(module_record())})

if INVENTORY:
    for cid, (desc, sch, docs) in sorted(cases.items()):
        print("%s|-|compile=OK" % cid)
        for name in sorted(docs):
            print("%s|%s" % (cid, name))
    sys.exit(0)
for cid, (desc, sch, docs) in sorted(cases.items()):
    d = os.path.join(OUT, cid, "docs")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(OUT, cid, "schema.yaml"), "w", encoding="utf-8", newline="").write(sch)
    open(os.path.join(OUT, cid, "DESCRIPTION"), "w", encoding="utf-8").write(desc + "\n")
    for name, text in docs.items():
        open(os.path.join(d, name + ".yaml"), "w", encoding="utf-8", newline="").write(text)
print(len(cases), "cases", sum(len(c[2]) for c in cases.values()), "documents")
