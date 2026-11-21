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


def pattern_nodes(nodes, path="$"):
    for n in nodes:
        p = path + "." + n["name"]
        for c in n.get("contract") or []:
            if c.get("type") == "pattern":
                yield p, c["expression"], bool(n.get("mandatory")), n.get("nullable", False)
        yield from pattern_nodes(n.get("fields") or [], p)
        yield from pattern_nodes(n.get("item_fields") or [], p + "[]")


def values(rec, path):
    cur = [rec]
    for seg in path[2:].split("."):
        isl = seg.endswith("[]"); k = seg[:-2] if isl else seg
        nxt = []
        for x in cur:
            if isinstance(x, dict) and k in x:
                v = x[k]
                nxt.extend(v if isl and isinstance(v, list) else [v] if not isl else [])
        cur = nxt
    return cur


def load(kind, ref):
    if kind == "git":
        r = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % ref], capture_output=True)
        if r.returncode != 0:
            raise SystemExit("INCOMPLETE: git show %s:%s failed: %s" % (ref[0], ref[1], r.stderr.decode().strip()))
        return r.stdout.decode("utf-8")
    return open(os.path.join(ROOT, ref), encoding="utf-8").read()


def measure(label, rec, nodes):
    """One record against the pattern nodes of its schema. Returns (lines, n_vals, n_lf, n_long, changed, n_nodes_without, outside)."""
    n_vals = n_nodes_without = n_lf = n_long = changed = 0
    outside, lines = [], []
    for path, expr, mandatory, nullable in pattern_nodes(nodes):
        if not S.parse(expr).ok and expr not in outside:
            outside.append(expr)
        strs = []
        vs = values(rec, path)
        strs = [v for v in vs if isinstance(v, str)]
        if not vs and mandatory and not nullable:
            n_nodes_without += 1; lines.append("   no value at %s (mandatory in the draft schema, absent in the record)" % path)
        for v in strs:
            n_vals += 1
            leg, new = verdicts(expr, v)
            n_lf += v.endswith("\n") or "\n" in v
            n_long += len(v) > VALUE_MAX
            if leg != new:
                changed += 1; lines.append("   CHANGED %s %r legacy=%s candidate=%s" % (path, v[:40], leg, new))
    return lines, n_vals, n_lf, n_long, changed, n_nodes_without, outside


def check_complete(label, n_vals, n_nodes_without, outside):
    """Raises SystemExit(INCOMPLETE) when the run cannot support the claim: a mandatory pattern node without a value, an expression outside the candidate subset
    (the claim would then not be about the candidate profile), or too few values (vacuous)."""
    if n_nodes_without:
        raise SystemExit("INCOMPLETE: %s: %d mandatory pattern node(s) found no value in the record (an unread node is not a measured node)" % (label, n_nodes_without))
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
        print("%s\n   pattern-constrained string values found: %d; with a line feed: %d; longer than %d code points: %d; verdicts that change: %d; mandatory nodes with no value: %d; expressions outside the subset: %d" % (
            label, n_vals, n_lf, VALUE_MAX, n_long, changed, n_without, len(outside)))
        for l in lines:
            print(l)
        check_complete(label, n_vals, n_without, outside)
        findings += changed
    print("verdicts changed by the candidate profile (subset + 256 code points + full match) over all records: %d" % findings)
    return 3 if findings else 0


def self_test():
    """The measurement must be able to see a change and must refuse an incomplete run."""
    ok = True
    def check(label, cond):
        nonlocal ok; ok = ok and cond; print("%-70s %s" % (label, "ok" if cond else "WRONG"))
    sem = r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"
    check("a clean value keeps its verdict", verdicts(sem, "1.2.3") == (True, True))
    check("a value with a trailing line feed CHANGES (legacy accepts, candidate refuses)", verdicts(sem, "1.2.3\n") == (True, False))
    check("a value with a leading line feed keeps its verdict (both refuse)", verdicts(sem, "\n1.2.3") == (False, False))
    check("the outer anchors are removed, an escaped dollar is kept", strip_anchors(r"^a\$$") == r"a\$" and strip_anchors("^ab$") == "ab")
    check("a path with a list is resolved item by item", values({"a": {"f": [{"d": "x"}, {"d": "y"}]}}, "$.a.f[].d") == ["x", "y"])
    check("a missing path gives no value (the caller counts it)", values({"a": 1}, "$.b.c") == [])
    check("a value over the 256 code point limit CHANGES (legacy accepts, candidate refuses)", verdicts(r"^[a-z]+$", "a" * 257) == (True, False) and verdicts(r"^[a-z]+$", "a" * 256) == (True, True))
    check("an expression outside the subset: the candidate profile refuses every value", verdicts(r"^\d+$", "123") == (True, False))
    node = lambda name, mand=True: {"name": name, "mandatory": mand, "contract": [{"type": "pattern", "expression": "^[a-z]{1,3}$"}]}
    good = {"a": "abc", "b": "ab", "c": "x", "d": "yz", "e": "q", "f": "r", "g": "s", "h": "t", "i": "u"}
    nodes = [node(k) for k in good]
    r = measure("t", good, nodes)
    check("a complete synthetic record passes (9 values, nothing missing, nothing outside)", r[1] == 9 and r[5] == 0 and not r[6] and check_complete("t", r[1], r[5], r[6]) is None)
    def refused(fn):
        try:
            fn(); return False
        except SystemExit as e:
            return str(e).startswith("INCOMPLETE")
    r2 = measure("t", {k: v for k, v in good.items() if k != "h"}, nodes)
    check("a mandatory pattern node with no value makes the run INCOMPLETE", refused(lambda: check_complete("t", r2[1], r2[5], r2[6])) and r2[5] == 1)
    r2b = measure("t", good, nodes[:-1] + [node("h", False)] )
    check("an optional node with no value does not", r2b[5] == 0)
    bad_nodes = nodes + [{"name": "z", "mandatory": False, "contract": [{"type": "pattern", "expression": r"^\d+$"}]}]
    r3 = measure("t", dict(good, z="1"), bad_nodes)
    check("an expression outside the subset makes the run INCOMPLETE", refused(lambda: check_complete("t", r3[1], r3[5], r3[6])) and r3[6] == [r"^\d+$"])
    r4 = measure("t", {"a": "abc"}, nodes[:1])
    check("too few values make the run INCOMPLETE (vacuous)", refused(lambda: check_complete("t", r4[1], r4[5], r4[6])))
    r5 = measure("t", dict(good, a="a" * 257), [{"name": "a", "mandatory": True, "contract": [{"type": "pattern", "expression": "^[a-z]+$"}]}])
    check("a long value in a record is counted as a changed verdict", r5[4] == 1 and r5[3] == 1)
    try:
        load("git", ("no-such-tag-for-the-self-test", "x")); check("a git error is refused, not read as zero", False)
    except SystemExit as e:
        check("a git error is refused, not read as zero", str(e).startswith("INCOMPLETE"))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(main())
