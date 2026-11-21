"""Semantic compatibility on REAL DATA: every value that a `pattern` contract of the composed release schemas constrains, in the records that exist, under the two
semantics: legacy (Python re.search of the original expression: what the jsonschema library does today) and the candidate (full match of the expression with its outer
^ and $ removed, as in probe_engines.py). The candidate rule must not change the verdict of any value of any existing record.
Fail-closed: a git error, an unreadable record, a record in which fewer than MIN_VALUES constrained values are found, or a record/schema pair that finds no value for a
declared mandatory pattern node makes the exit code 1. Exit 0: complete, and no value changes its verdict. Exit 3: complete, at least one value changes (a finding).
Usage: compat_records.py <repo root>"""
import os, re, subprocess, sys, yaml
ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else os.getcwd()
sys.path.insert(0, os.path.join(ROOT, "docs", "design", "release-schemas")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose as C
import subset_check as S
MIN_VALUES = 8
VALUE_MAX = 256   # candidate limit: a value longer than this many code points does not match
RECORDS = [("tag primitives/@v0.2.1 release/cic-primitives-v0.2.1.yaml", "git", ("primitives/@v0.2.1", "release/cic-primitives-v0.2.1.yaml"), "PrimitiveRelease"),
           ("tests/fixtures/envelope3/golden-record.yaml", "file", "tests/fixtures/envelope3/golden-record.yaml", "PrimitiveRelease"),
           ("docs/evidence/release-schema-draft-probe/base-record.yaml", "file", "docs/evidence/release-schema-draft-probe/base-record.yaml", "PrimitiveRelease")]


def strip_anchors(p):
    a = p.startswith("^"); b = p.endswith("$") and not re.search(r"(?<!\\)(\\\\)*\\\$$", p)
    return p[(1 if a else 0):len(p) - (1 if b else 0)]


def candidate(expr, v):
    """The WHOLE candidate profile for one value: the expression must be inside the closed subset (else the schema is refused at read, so no value is valid),
    the value must be within the length limit, and the expression must match the whole value (outer anchors removed, `.` never LF)."""
    if not S.parse(expr).ok or len(v) > VALUE_MAX:
        return False
    return bool(re.fullmatch(strip_anchors(expr), v))


def verdicts(expr, v):
    """(legacy, candidate) for one value."""
    return bool(re.search(expr, v)), candidate(expr, v)


def pattern_nodes(nodes, path="$", chain=()):
    """Yields (path, expression, chain) for every pattern contract; chain = one (mandatory, nullable) pair per path segment, outermost first."""
    for n in nodes:
        p = path + "." + n["name"]
        c2 = chain + ((bool(n.get("mandatory")), bool(n.get("nullable", False))),)
        for c in n.get("contract") or []:
            if c.get("type") == "pattern":
                yield p, c["expression"], c2
        yield from pattern_nodes(n.get("fields") or [], p, c2)
        yield from pattern_nodes(n.get("item_fields") or [], p + "[]", c2)


class Acct:
    """Element-level accounting of one path: strings found, mandatory elements that lack the key, nulls where null is not allowed, values of the wrong type."""
    def __init__(self):
        self.strs, self.missing, self.null_bad, self.type_bad = [], 0, 0, 0


def values(rec, path, chain):
    """Walks the path ELEMENT BY ELEMENT. Nothing that is not a string value is dropped silently: each missing mandatory key, each null that the node does not allow
    and each value or container of the wrong type is counted on the Acct (a collection where one element has the field and another lacks it is NOT complete)."""
    a = Acct()
    segs = path[2:].split(".")
    cur = [rec]
    for depth, seg in enumerate(segs):
        isl = seg.endswith("[]"); k = seg[:-2] if isl else seg
        mandatory, nullable = chain[depth]
        last = depth == len(segs) - 1
        nxt = []
        for x in cur:
            if not isinstance(x, dict):
                a.type_bad += 1; continue
            if k not in x:
                if mandatory:
                    a.missing += 1
                continue
            v = x[k]
            if v is None:
                if not nullable:
                    a.null_bad += 1
                continue
            if isl:
                if not isinstance(v, list):
                    a.type_bad += 1; continue
                items = v
            else:
                items = [v]
            for it in items:
                if it is None:
                    if not nullable:
                        a.null_bad += 1
                elif last:
                    if isinstance(it, str):
                        a.strs.append(it)
                    else:
                        a.type_bad += 1
                else:
                    nxt.append(it)
        cur = nxt
    return a


def load(kind, ref):
    if kind == "git":
        r = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % ref], capture_output=True)
        if r.returncode != 0:
            raise SystemExit("INCOMPLETE: git show %s:%s failed: %s" % (ref[0], ref[1], r.stderr.decode().strip()))
        return r.stdout.decode("utf-8")
    return open(os.path.join(ROOT, ref), encoding="utf-8").read()


def measure(label, rec, nodes):
    """One record against the pattern nodes of its schema. Returns (lines, n_vals, n_lf, n_long, changed, bad, outside); bad = missing + null_bad + type_bad (element level)."""
    n_vals = n_lf = n_long = changed = bad = 0
    outside, lines = [], []
    for path, expr, chain in pattern_nodes(nodes):
        if not S.parse(expr).ok and expr not in outside:
            outside.append(expr)
        a = values(rec, path, chain)
        if a.missing or a.null_bad or a.type_bad:
            bad += a.missing + a.null_bad + a.type_bad
            lines.append("   %s: %d mandatory element(s) without the key, %d null where not allowed, %d value(s) of the wrong type" % (path, a.missing, a.null_bad, a.type_bad))
        for v in a.strs:
            n_vals += 1
            leg, new = verdicts(expr, v)
            n_lf += "\n" in v
            n_long += len(v) > VALUE_MAX
            if leg != new:
                changed += 1; lines.append("   CHANGED %s %r legacy=%s candidate=%s" % (path, v[:40], leg, new))
    return lines, n_vals, n_lf, n_long, changed, bad, outside


def check_complete(label, n_vals, bad, outside):
    """Raises SystemExit(INCOMPLETE) when the run cannot support the claim: any element-level gap (a mandatory key missing in ANY element, a null that is not allowed,
    a value of the wrong type), an expression outside the candidate subset, or too few values (vacuous)."""
    if bad:
        raise SystemExit("INCOMPLETE: %s: %d element-level gap(s) (a mandatory pattern node missing in some element, a null that is not allowed, or a wrong type): an unread value is not a measured value" % (label, bad))
    if outside:
        raise SystemExit("INCOMPLETE: %s: pattern expression(s) outside the candidate subset (the candidate profile would refuse the schema): %s" % (label, "; ".join(outside)))
    if n_vals < MIN_VALUES:
        raise SystemExit("INCOMPLETE: only %d constrained values found in %s (need at least %d): the measurement would be vacuous" % (n_vals, label, MIN_VALUES))


def main():
    findings = 0
    for label, kind, ref, schema_kind in RECORDS:
        try:
            rec = yaml.safe_load(load(kind, ref))
        except SystemExit:
            raise
        except Exception as e:
            raise SystemExit("INCOMPLETE: %s is not readable (%s)" % (label, type(e).__name__))
        if not isinstance(rec, dict):
            raise SystemExit("INCOMPLETE: %s is not a mapping" % label)
        schema = C.compose(os.path.join(ROOT, "docs", "design", "release-schemas"), schema_kind)
        lines, n_vals, n_lf, n_long, changed, n_without, outside = measure(label, rec, schema["spec"]["config_surface"]["nodes"])
        print("%s\n   pattern-constrained string values found: %d; with a line feed: %d; longer than %d code points: %d; verdicts that change: %d; element-level gaps: %d; expressions outside the subset: %d" % (
            label, n_vals, n_lf, VALUE_MAX, n_long, changed, n_without, len(outside)))
        for l in lines:
            print(l)
        check_complete(label, n_vals, n_without, outside)
        findings += changed
    print("verdicts changed by the candidate profile (subset + 256 code points + full match) over all records: %d" % findings)
    return 3 if findings else 0


def self_test():
    """The measurement must be able to see a change and must refuse an incomplete run, element by element."""
    ok = True
    def check(label, cond):
        nonlocal ok; ok = ok and cond; print("%-92s %s" % (label, "ok" if cond else "WRONG"))
    def refused(fn):
        try:
            fn(); return False
        except SystemExit as e:
            return str(e).startswith("INCOMPLETE")
    sem = r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"
    check("a clean value keeps its verdict", verdicts(sem, "1.2.3") == (True, True))
    check("a value with a trailing line feed CHANGES (legacy accepts, candidate refuses)", verdicts(sem, "1.2.3\n") == (True, False))
    check("a value with a leading line feed keeps its verdict (both refuse)", verdicts(sem, "\n1.2.3") == (False, False))
    check("the outer anchors are removed, an escaped dollar is kept", strip_anchors(r"^a\$$") == r"a\$" and strip_anchors("^ab$") == "ab")
    check("a value over the 256 code point limit CHANGES (legacy accepts, candidate refuses)", verdicts(r"^[a-z]+$", "a" * 257) == (True, False) and verdicts(r"^[a-z]+$", "a" * 256) == (True, True))
    check("an expression outside the subset: the candidate profile refuses every value", verdicts(r"^\d+$", "123") == (True, False))
    pat = [{"type": "pattern", "expression": "^[a-z]{1,3}$"}]
    def leaf(name, mand=True, nullable=False):
        return {"name": name, "mandatory": mand, "nullable": nullable, "contract": pat}
    def run(rec, nodes):
        r = measure("t", rec, nodes)
        return r, refused(lambda: check_complete("t", r[1], r[5], r[6]))
    flat = {k: v for k, v in zip("abcdefghi", ["abc", "ab", "x", "yz", "q", "r", "s", "t", "u"])}
    r, ref = run(flat, [leaf(k) for k in flat])
    check("a complete flat record passes (9 values, no gap, nothing outside)", r[1] == 9 and r[5] == 0 and not r[6] and not ref)
    r, ref = run({k: v for k, v in flat.items() if k != "h"}, [leaf(k) for k in flat])
    check("a mandatory key missing in the record: INCOMPLETE", ref and r[5] == 1)
    r, ref = run({k: v for k, v in flat.items() if k != "h"}, [leaf(k, k != "h") for k in flat])
    check("an optional key missing is not a gap", not ref and r[5] == 0)
    # collections: ELEMENT level (the review's example: one element has the field, another lacks it)
    coll = {"items": [{"d": "aa"}, {"d": "bb"}, {"d": "cc"}, {"d": "dd"}, {"d": "ee"}, {"d": "ff"}, {"d": "gg"}, {"d": "hh"}, {"d": "ii"}]}
    node = [{"name": "items", "mandatory": True, "item_fields": [leaf("d")]}]
    r, ref = run(coll, node)
    check("a complete collection passes (9 elements)", r[1] == 9 and not ref)
    part = {"items": coll["items"] + [{"path": "example.yaml"}]}
    r, ref = run(part, node)
    check("ONE element without the mandatory key among nine that have it: INCOMPLETE (the review's case)", ref and r[5] == 1 and r[1] == 9)
    r, ref = run({"items": coll["items"] + [{"d": None}]}, node)
    check("a null in one element where the node is not nullable: INCOMPLETE", ref and r[5] == 1)
    node_n = [{"name": "items", "mandatory": True, "item_fields": [leaf("d", True, True)]}]
    r, ref = run({"items": coll["items"] + [{"d": None}]}, node_n)
    check("the same null where the node IS nullable is not a gap", not ref and r[5] == 0)
    r, ref = run({"items": coll["items"] + [{"d": 7}]}, node)
    check("a value of the wrong type (an integer) in one element: INCOMPLETE", ref and r[5] == 1)
    r, ref = run({"items": coll["items"] + [{"d": ["x"]}]}, node)
    check("a list where a string is expected: INCOMPLETE", ref and r[5] == 1)
    r, ref = run({"items": coll["items"] + [None]}, node)
    check("a null list element (an item that is null) where the node is not nullable: INCOMPLETE", ref and r[5] == 1)
    r, ref = run({"items": coll["items"] + ["not-a-mapping"]}, node)
    check("an element that is not a mapping: INCOMPLETE", ref and r[5] == 1)
    r, ref = run({"items": "oops"}, node)
    check("a collection that is not a list: INCOMPLETE", ref and r[5] == 1)
    nest = [{"name": "o", "mandatory": True, "fields": [{"name": "items", "mandatory": True, "item_fields": [leaf("d")]}]}]
    r, ref = run({"o": {"items": coll["items"] + [{}]}}, nest)
    check("the same gap one level deeper (an object, then a collection): INCOMPLETE", ref and r[5] == 1)
    r, ref = run({"o": {"items": coll["items"]}}, nest)
    check("the nested complete record passes", not ref and r[1] == 9)
    r, ref = run({}, nest)
    check("a mandatory parent that is absent: INCOMPLETE (not read as zero)", ref)
    bad_nodes = [leaf(k) for k in flat] + [{"name": "z", "mandatory": False, "contract": [{"type": "pattern", "expression": r"^\d+$"}]}]
    r, ref = run(dict(flat, z="1"), bad_nodes)
    check("an expression outside the subset: INCOMPLETE", ref and r[6] == [r"^\d+$"])
    r, ref = run({"a": "abc"}, [leaf("a")])
    check("too few values: INCOMPLETE (vacuous)", ref)
    plus = [{"name": k, "mandatory": True, "contract": [{"type": "pattern", "expression": "^[a-z]+$"}]} for k in flat]
    r = measure("t", dict(flat, a="a" * 257), plus)
    check("a long value is counted as a changed verdict", r[4] == 1 and r[3] == 1)
    try:
        load("git", ("no-such-tag-for-the-self-test", "x")); check("a git error is refused, not read as zero", False)
    except SystemExit as e:
        check("a git error is refused, not read as zero", str(e).startswith("INCOMPLETE"))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(main())
