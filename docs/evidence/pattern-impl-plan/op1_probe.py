"""OP-1 of the implementation plan: how a YAML scalar becomes a typed value. ISOLATED measurement, no implementation of the profile.
The type class of a pin value (an int, a bool, a float, a string, a null) depends on the scalar resolution rules, and the specification says the reader delivers raw typed values but not which scalar schema.
This probe (a) holds a small REFERENCE RESOLVER of the YAML 1.2 CORE SCHEMA, written from the regular expressions of that schema, (b) checks it against a table of cases whose expected type and value are written by
hand from the YAML 1.2 specification text, and (c) measures where PyYAML (YAML 1.1 rules) differs, which is the gap a reader on PyYAML would have to close with its own resolver. It also records, without expectations,
how PyYAML treats aliases, merge keys, explicit tags and duplicate keys, the points the review asked to define.
Typed exits: 0 the reference resolver agrees with every hand-written expectation and the gap is real, 1 a FAIL-EXPECT line, 2 infrastructure (PyYAML missing).
CIC_OP1_PLANT plants a defect of the reference resolver for the self-test only (octal-int, bool-yaml11, underscore-int)."""
import math, os, re, sys

PLANT = os.environ.get("CIC_OP1_PLANT", "")
NULL = re.compile(r"^(~|null|Null|NULL|)$")
BOOL = re.compile(r"^(true|True|TRUE|false|False|FALSE)$")
INT10 = re.compile(r"^[-+]?[0-9]+$")
INT8 = re.compile(r"^0o[0-7]+$")
INT16 = re.compile(r"^0x[0-9a-fA-F]+$")
FLOAT = re.compile(r"^[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?$")
INF = re.compile(r"^[-+]?\.(inf|Inf|INF)$")
NAN = re.compile(r"^\.(nan|NaN|NAN)$")


def core(text):
    """the YAML 1.2 CORE SCHEMA resolution of a plain scalar -> (type name, value)"""
    if NULL.match(text):
        return ("null", None)
    if BOOL.match(text) or (PLANT == "bool-yaml11" and text in ("on", "off", "yes", "no", "On", "Off", "Yes", "No")):
        return ("bool", text.lower() in ("true", "on", "yes"))
    if PLANT == "underscore-int" and re.match(r"^[0-9][0-9_]*$", text):
        return ("int", int(text.replace("_", "")))
    if PLANT == "octal-int" and re.match(r"^0[0-7]+$", text):
        return ("int", int(text, 8))
    if INT10.match(text):
        return ("int", int(text, 10))                       # leading zeros are decimal in the core schema: 010 is the int 10
    if INT8.match(text):
        return ("int", int(text[2:], 8))
    if INT16.match(text):
        return ("int", int(text[2:], 16))
    if INF.match(text):
        return ("float", -math.inf if text.startswith("-") else math.inf)
    if NAN.match(text):
        return ("float", math.nan)
    if FLOAT.match(text):
        return ("float", float(text))
    return ("str", text)


# (the plain scalar, the type, the value) written by hand from the YAML 1.2 specification (core schema); nan is compared as "is nan"
CASES = [
    ("010", "int", 10), ("0o10", "int", 8), ("0x10", "int", 16), ("08", "int", 8), ("+1", "int", 1), ("-0", "int", 0), ("1", "int", 1), ("0", "int", 0),
    ("1_000", "str", "1_000"), ("1,000", "str", "1,000"), ("0b10", "str", "0b10"), ("0o8", "str", "0o8"), ("0x", "str", "0x"),
    ("on", "str", "on"), ("off", "str", "off"), ("yes", "str", "yes"), ("no", "str", "no"), ("y", "str", "y"), ("n", "str", "n"), ("tRUE", "str", "tRUE"),
    ("true", "bool", True), ("True", "bool", True), ("TRUE", "bool", True), ("false", "bool", False), ("False", "bool", False),
    ("~", "null", None), ("null", "null", None), ("Null", "null", None), ("", "null", None),
    ("1e3", "float", 1000.0), ("1.0", "float", 1.0), (".5", "float", 0.5), ("5.", "float", 5.0), ("-1.5e-2", "float", -0.015), (".inf", "float", math.inf), ("-.inf", "float", -math.inf), (".nan", "float", "nan"),
    ("1:30", "str", "1:30"), ("2001-01-01", "str", "2001-01-01"), ("0.1.2", "str", "0.1.2"), ("1.2.3", "str", "1.2.3"), ("abc", "str", "abc"),
]
fails = []


def expect(label, cond, detail=""):
    if not cond:
        fails.append(label); print("FAIL-EXPECT %s %s" % (label, detail))


def same(a, b):
    if a[0] != b[0]:
        return False
    if a[0] == "float" and (a[1] != a[1] or b[1] != b[1]):
        return (a[1] != a[1]) and (b[1] != b[1])
    return a[1] == b[1]


def describe(t):
    return "%s %r" % (t[0], t[1]) if t[0] != "float" or t[1] == t[1] else "float nan"


def main():
    if os.environ.get("CIC_OP1_NO_YAML"):
        print("INCOMPLETE: PyYAML is not available (simulated)"); return 2
    try:
        import yaml
    except BaseException as e:
        print("INCOMPLETE: PyYAML is not available: %r" % (e,)); return 2
    print("PyYAML %s, the YAML 1.1 rules" % yaml.__version__)
    print("%-10s %-22s %-22s %s" % ("scalar", "YAML 1.2 core schema", "PyYAML", "same?"))
    diverge = []
    for text, typ, val in CASES:
        ref = core(text)
        want = (typ, val)
        expect("core.%r" % text, same(ref, want) if val != "nan" else (ref[0] == "float" and ref[1] != ref[1]), "the reference resolver gives %s, the hand-written expectation is %s %r" % (describe(ref), typ, val))
        try:
            v = yaml.safe_load("v: %s" % text)["v"] if text != "" else yaml.safe_load("v:")["v"]
            tp = {type(None): "null", bool: "bool", int: "int", float: "float", str: "str"}.get(type(v), type(v).__name__)
            py = (tp, v)
        except BaseException as e:
            py = ("error", type(e).__name__)
        eq = same(ref, py)
        if not eq:
            diverge.append(text)
        print("%-10s %-22s %-22s %s" % (repr(text), describe(ref), describe(py), "yes" if eq else "NO"))
    print("PyYAML differs from the core schema on %d of %d scalars: %s" % (len(diverge), len(CASES), ", ".join(repr(d) for d in diverge)))
    expect("gap.exists", len(diverge) > 0, "PyYAML agrees with the core schema on every case: OP-1 would be moot (the table is too weak)")
    print("## recorded without expectations: what PyYAML does with the structures the review asked to define")
    probes = [("alias", "a: &x 1\nb: *x"), ("merge key", "a: &x {k: 1}\nb: {<<: *x, j: 2}"), ("explicit tag !!str", "v: !!str 1"), ("explicit tag !!int", "v: !!int \"1\""),
              ("unknown tag", "v: !custom 1"), ("python tag", "v: !!python/object:os.system {}"), ("duplicate key", "a: 1\na: 2"), ("keys 1 and true", "{1: a, true: b}"), ("complex key", "? [1, 2]\n: a")]
    for name, text in probes:
        try:
            r = yaml.safe_load(text)
            out = "accepted -> %r" % (r,)
        except BaseException as e:
            out = "error %s" % type(e).__name__
        print("%-22s %s" % (name, out))
    if fails:
        print("FAILED: %d expectation(s)" % len(fails)); return 1
    print("all expectations held"); return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
