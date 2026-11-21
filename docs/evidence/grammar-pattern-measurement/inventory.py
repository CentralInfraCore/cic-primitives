"""Inventory of every regular expression that a schema or grammar file of the measured trees declares, and the verdict of the candidate subset on each.
Fail-closed: an unreadable YAML file, a missing root or zero expressions found makes the exit code 1.
Usage: inventory.py <label>=<root> [<label>=<root> ...]
Two kinds are found: 'contract' (a mapping {type: pattern, expression: ...}) and 'jsonschema' (a key `pattern` with a string value, or the keys of
`patternProperties`: the grammar-internal checks that only the Python jsonschema library evaluates)."""
import os, sys, yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subset_check as S


def walk(x, path=""):
    if isinstance(x, dict):
        if x.get("type") == "pattern" and isinstance(x.get("expression"), str):
            yield "contract", path, x["expression"]
        for k, v in x.items():
            if k == "pattern" and isinstance(v, str):
                yield "jsonschema", path + "/pattern", v
            if k == "patternProperties" and isinstance(v, dict):
                for pk in v:
                    yield "jsonschema", path + "/patternProperties", pk
            yield from walk(v, "%s/%s" % (path, k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from walk(v, "%s[%d]" % (path, i))


def main(args):
    rows, problems = [], []
    for a in args:
        label, root = a.split("=", 1)
        if not os.path.isdir(root):
            problems.append("root %s does not exist" % root); continue
        files = sorted(os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs if f.endswith((".yaml", ".yml")) and ".git" not in d.split(os.sep))
        if not files:
            problems.append("no YAML file under %s" % root)
        for f in files:
            try:
                docs = list(yaml.safe_load_all(open(f, encoding="utf-8")))
            except Exception as e:
                problems.append("%s is not readable YAML (%s)" % (f, type(e).__name__)); continue
            for doc in docs:
                for kind, path, expr in walk(doc):
                    rows.append((label, os.path.relpath(f, root), kind, path, expr))
    if not rows:
        problems.append("no expression found at all")
    if problems:
        print("INCOMPLETE INVENTORY:\n  " + "\n  ".join(problems)); return 1
    print("%-9s %-10s %-7s %-58s %s" % ("tree", "kind", "subset", "file", "expression"))
    n = {}
    for label, f, kind, path, expr in rows:
        r = S.parse(expr)
        n[(label, kind, r.ok)] = n.get((label, kind, r.ok), 0) + 1
        print("%-9s %-10s %-7s %-58s %s%s" % (label, kind, "accept" if r.ok else "REFUSE", f[-58:], expr if len(expr) < 90 else expr[:87] + "...", "" if r.ok else "   <- " + r.reason))
    print("\nsummary (tree, kind, in the subset): count")
    for k in sorted(n):
        print("  %s %s %s: %d" % (k[0], k[1], "accept" if k[2] else "REFUSE", n[k]))
    mx = {"length": 0, "max_repeat": 0, "depth": 0}
    for _, _, _, _, expr in rows:
        r = S.parse(expr)
        if r.ok:
            for k in mx:
                mx[k] = max(mx[k], r.stats[k])
    print("maxima over the accepted expressions: length=%(length)d max_repeat=%(max_repeat)d depth=%(depth)d" % mx)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
