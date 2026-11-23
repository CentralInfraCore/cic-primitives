"""AFTER the contract is fixed: where does PyYAML's `yaml.safe_load` (the YAML 1.1 resolver and constructors) differ from the draft vectors? A MEASUREMENT, not a source of truth: the contract was written first and does not
follow this output (RC-19). It changes nothing and is not part of the pass or fail of check_reader_contract.py. Output: results/pyyaml-measurement.json (version, counts, the differing vector ids by class).
Usage: measure_pyyaml.py [--out PATH]. Exit 0, 2 an input cannot be read."""
import json, math, os, struct, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
VEC = os.path.join(HERE, "..", "..", "design", "pattern-profile-reader", "reader-vectors.yaml")


def to_tree(v):
    if v is None: return ["n"]
    if isinstance(v, bool): return ["b", v]
    if isinstance(v, int): return ["i", str(v)]
    if isinstance(v, float): return ["f", "7ff8000000000000" if v != v else struct.pack(">d", v).hex()]
    if isinstance(v, str): return ["s", v]
    if isinstance(v, list): return ["seq", [to_tree(x) for x in v]]
    if isinstance(v, dict): return ["map", [[to_tree(k), to_tree(x)] for k, x in v.items()]]
    return ["other", type(v).__name__]


def main(argv):
    import yaml
    out = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(HERE, "results", "pyyaml-measurement.json")
    try:
        vectors = yaml.safe_load(open(VEC, encoding="utf-8"))["vectors"]
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); return 2
    res = collections.OrderedDict((k, []) for k in ("agrees", "differs_in_value", "accepts_what_the_contract_rejects", "rejects_what_the_contract_reads"))
    for v in vectors:
        data = bytes.fromhex(v["hex"]) if v["kind"] == "bytes" else (("- " + v["text"] + "\n") if v["kind"] == "scalar" else v["text"])
        exp = v["expect"]
        try:
            got = to_tree(yaml.safe_load(data)); raised = False
        except BaseException:
            got = None; raised = True
        if "error" in exp:
            (res["agrees"] if raised else res["accepts_what_the_contract_rejects"]).append(v["id"])
        else:
            want = ["seq", [exp["node"]]] if "node" in exp else exp["tree"]
            if raised: res["rejects_what_the_contract_reads"].append(v["id"])
            else: (res["agrees"] if got == want else res["differs_in_value"]).append(v["id"])
    rec = {"pyyaml_version": yaml.__version__, "vectors": len(vectors), "counts": {k: len(x) for k, x in res.items()}, "ids": res}
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(rec, open(out, "w", encoding="utf-8"), indent=1); open(out, "a").write("\n")
    print("PyYAML %s over %d vectors: %s" % (yaml.__version__, len(vectors), ", ".join("%s %d" % (k, len(x)) for k, x in res.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
