#!/usr/bin/env python3
"""Cases for the node-name measurement: what the (unchanged) Form does with a node name that the pinned grammar's name rule
`^[a-z][a-z0-9_]*$` accepts or rejects. One schema per name (a single mandatory string field of that name) and a few documents.
usage: gen_cases.py <dir> | --inventory      Case ids start with K (the probes read only such directories). Document prefix: pos_ the Form must accept, neg_ the Form must refuse.
The HYPOTHESIS under test: the Form does not enforce the grammar's name rule, so every case compiles. The first run FALSIFIED it for one case (the empty
name is refused: the grammar has minLength 1, and the Form enforces that, not the pattern); that case is therefore listed in REFUSED, with the code that was
observed, so the expectation is stated and checked, not silently adjusted."""
import os, sys, yaml
INVENTORY = sys.argv[1] == "--inventory"
OUT = None if INVENTORY else sys.argv[1]
HEAD = {"spec": {"identity": {"atomic_ref": "cic:core:Identity@v0.2.0", "kind": "NameProbe", "namespace": "cic:probe", "version": "v0.0.1"},
                 "config_surface": {"aggregate_ref": "cic:core:ConfigSurface@v0.2.0", "nodes": None}}}

def schema(names):
    d = yaml.safe_load(yaml.safe_dump(HEAD))
    d["spec"]["config_surface"]["nodes"] = [{"name": n, "shape_type": "scalar", "scalar_type": "string", "mandatory": True} for n in names]
    return yaml.safe_dump(d, sort_keys=False, width=1000, allow_unicode=True)

def doc(pairs):
    return yaml.safe_dump(dict(pairs), sort_keys=False, width=1000, allow_unicode=True) if pairs else "{}\n"

# id, description, names, the expected verdict of the CURRENT grammar rule (for the record, not for the Form)
NAMES = [
    ("K01_lower", "a", ["a"], "valid"),
    ("K02_snake", "created_by", ["created_by"], "valid"),
    ("K03_camel", "createdBy: the field of the released records", ["createdBy"], "INVALID"),
    ("K04_pascal", "CreatedBy", ["CreatedBy"], "INVALID"),
    ("K05_upper_single", "A", ["A"], "INVALID"),
    ("K06_digit_first", "1abc", ["1abc"], "INVALID"),
    ("K07_underscore_first", "_x", ["_x"], "INVALID"),
    ("K08_hyphen", "a-b", ["a-b"], "INVALID"),
    ("K09_space", "a b", ["a b"], "INVALID"),
    ("K10_dot", "a.b", ["a.b"], "INVALID"),
    ("K11_non_ascii", "a name with a non-ASCII letter (U+00E9)", ["ét"], "INVALID"),
    ("K12_trailing_newline", "a name with a trailing line feed", ["abc\n"], "INVALID"),
    ("K13_empty", "an empty name", [""], "INVALID"),
    ("K14_long", "a 300 character name", ["a" * 300], "valid"),
    ("K15_mixed", "aB_c9", ["aB_c9"], "INVALID"),
]
REFUSED = {"K13_empty": "SCHEMA_INVALID"}   # observed, after the first run falsified 'every case compiles'
cases = {}
for cid, desc, names, verdict in NAMES:
    n = names[0]
    docs = {"pos_key_present": doc([(n, "v")]), "neg_key_missing": doc([]), "neg_other_key": doc([(n + "x", "v")])}
    cases[cid] = ("node name %s (current grammar rule: %s)" % (desc, verdict), schema(names), docs)
# two names that differ only in case (case-sensitive identity of siblings)
cases["K16_case_siblings"] = ("two sibling names that differ only in case: createdby and createdBy (current grammar rule: createdBy INVALID)", schema(["createdby", "createdBy"]), {
    "pos_both": doc([("createdby", "v"), ("createdBy", "w")]),
    "neg_only_lower": doc([("createdby", "v")]),
    "neg_only_camel": doc([("createdBy", "w")])})

if INVENTORY:
    for cid, (desc, sch, docs) in sorted(cases.items()):
        print("%s|-|compile=%s" % (cid, ("ERR[%s]" % REFUSED[cid]) if cid in REFUSED else "OK"))
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
