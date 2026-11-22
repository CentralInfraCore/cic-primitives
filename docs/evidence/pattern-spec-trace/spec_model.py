"""An executable reading of the NEW rules of the implementation specification (docs/en/GRAMMAR-PATTERN-IMPLEMENTATION-SPEC.md): the profile version resolution (the exact type), the deterministic traversal
of nested contracts, the boundary between the document reader and the pattern validator, and the validation order. An ISOLATED model, not an implementation: its only purpose is to make the proposed
extension cases (docs/design/pattern-profile-spec/extension-cases.yaml) derivable from the text, and to show that the new rules reproduce the verdicts of the schema vectors of the approved set.
Expression classification is delegated to the existing prototype (pattern_codes.classify): the profile rules themselves are not restated here.

Outcomes: ("accept",) | ("refuse", code, path) | ("reader_error", kind, path). A reader_error is OUTSIDE the pattern code set: the pattern validator never sees such a document.
"""
import hashlib, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pattern-limits-errors"))
sys.path.insert(0, os.path.join(HERE, "..", "grammar-pattern-measurement"))
sys.path.insert(0, os.path.join(HERE, "..", "pattern-engine-selection"))
import yaml
import pattern_codes as C

KNOWN_VERSION = 1                  # the decided profile version identifier (the exact type int, the value 1)
PLANT = os.environ.get("CIC_SPECMODEL_PLANT", "")      # a planted defect for the self-test only


class ReaderError(Exception):
    def __init__(self, kind, path=None):
        Exception.__init__(self, kind); self.kind, self.path = kind, path


class _OrderedLoader(yaml.SafeLoader):
    """the DOCUMENT READER: mapping entries stay in source order (Python dicts keep insertion order) and a duplicate key is a READER error, never a pattern code"""


def _mapping(loader, node, deep=False):
    seen = set()
    for knode, _ in node.value:
        k = loader.construct_object(knode, deep=deep)
        if k in seen:
            raise ReaderError("duplicate_key", str(k))
        seen.add(k)
    return loader.construct_mapping(node, deep=deep)


_OrderedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def read(text):
    try:
        return yaml.load(text, Loader=_OrderedLoader)
    except ReaderError:
        raise
    except yaml.YAMLError:
        raise ReaderError("yaml_syntax")


def contracts(node, path=()):
    """the pattern contracts of a schema in DOCUMENT ORDER: depth-first, pre-order; mapping entries in source order, sequence items by index. A pattern contract is a mapping with `type: pattern` that is an
    element of a `contract` sequence; it is visited at the position of the key `contract` among its siblings. Yields (path, element)."""
    if isinstance(node, dict):
        items = list(node.items())
        if PLANT == "contract-last":                       # planted: the own contract after the children, whatever the source order
            items.sort(key=lambda kv: kv[0] == "contract")
        for k, v in items:
            if k == "contract" and isinstance(v, list):
                for i, el in enumerate(v):
                    if isinstance(el, dict) and el.get("type") == "pattern":
                        yield path + (k, i), el
            else:
                yield from contracts(v, path + (k,))
    elif isinstance(node, list):
        for i, el in enumerate(node):
            yield from contracts(el, path + (i,))


def kind(v):
    """the type class of a YAML value; a bool is NOT an int (Python's bool is a subclass of int, which is exactly the trap)"""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "str"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "map"
    raise ReaderError("unsupported_yaml_value")


def identical(a, b):
    """THE IDENTITY OF TWO DECLARED VALUES (a rule of the specification, not a property of any serialisation): two values are identical iff they have the same type class and
    null: both null; bool: the same truth value; int: the same integer; float: the same IEEE-754 binary64 bit pattern, all NaN being identical to each other (so 0.0 and -0.0 differ);
    str: the same sequence of code points; list: the same length and pairwise identical items in the same order; map: the same number of entries and every entry of one has an entry of the other whose
    KEY is identical (the key's type class counts: the int 1 and the text 1 are different keys) and whose value is identical; the order of the entries of a map is irrelevant.
    A mapping key that is not a scalar is a reader error and never reaches this rule."""
    ka, kb = kind(a), kind(b)
    if ka != kb:
        return False
    if ka == "null":
        return True
    if ka in ("bool", "int", "str"):
        return a == b
    if ka == "float":
        return (a != a and b != b) or struct.pack(">d", a) == struct.pack(">d", b)
    if ka == "list":
        return len(a) == len(b) and all(identical(x, y) for x, y in zip(a, b))
    if len(a) != len(b):
        return False
    rest = list(b.items())
    for k, v in a.items():
        for n, (k2, v2) in enumerate(rest):
            if identical(k, k2) and identical(v, v2):
                del rest[n]; break
        else:
            return False
    return not rest


def _identical_planted(a, b):
    """planted defect: identity by a serialisation (Python's json with default=str), the weakness the review found: a 1 key and a text 1 key, or different types that print alike, collapse"""
    import json
    f = lambda v: json.dumps(v, sort_keys=True, default=str)
    return f(a) == f(b)


def resolve_pin(declarations):
    """declarations: the raw typed values the reader found, in document order (a declaration with the value null is a declaration). -> ('ok',) | ('refuse', code)
    The result depends only on the SET of the declarations, not on their order."""
    if not declarations:
        return ("refuse", "pattern_profile_missing")
    same = _identical_planted if PLANT == "json-identity" else identical
    if any(not same(declarations[0], d) for d in declarations[1:]):
        return ("refuse", "pattern_profile_conflict")
    v = declarations[0]
    ok = (type(v) is int and v == KNOWN_VERSION) if PLANT != "equality-version" else (v == KNOWN_VERSION)      # planted: Python equality accepts true and 1.0
    return ("ok",) if ok else ("refuse", "pattern_profile_unknown")


def _lp(b):
    return struct.pack(">Q", len(b)) + b


def _enc_path(path):
    out = b""
    for seg in path:
        out += (b"I" + struct.pack(">q", seg)) if isinstance(seg, int) else (b"S" + _lp(str(seg).encode("utf-8")))
    return _lp(out)


def delivery_digest(items):
    """the DELIVERY DIGEST (specification, binding of the result to its input): SHA-256 over a length-prefixed encoding of the ORDERED list of (path, expression) pairs as the reader delivers them.
    items: [(path, expression)]. The order is part of the input: two documents with the same contracts in another delivery order have different delivery digests."""
    seq = list(items)
    if PLANT == "digest-sorted":                       # planted: an order-erasing digest, which cannot tell the two orders apart
        seq = sorted(seq, key=lambda it: (_enc_path(it[0]), it[1]))
    h = hashlib.sha256()
    for path, expr in seq:
        h.update(_enc_path(path)); h.update(_lp(expr.encode("utf-8")))
    return h.hexdigest()


def content_digest(items):
    """the order-erasing digest of the same contracts (what a canonical form that sorts keys would see)"""
    h = hashlib.sha256()
    for path, expr in sorted(items, key=lambda it: (_enc_path(it[0]), it[1])):
        h.update(_enc_path(path)); h.update(_lp(expr.encode("utf-8")))
    return h.hexdigest()


def deliver(schema_text):
    """the reader's output for a schema text: [(path, expression)] in document order, or raises ReaderError"""
    doc = read(schema_text)
    out = []
    for path, el in contracts(doc):
        e = el.get("expression")
        if not isinstance(e, str):
            raise ReaderError("expression_not_a_string", "/".join(map(str, path)))
        out.append((path, e))
    return out


def validate_delivered(declarations, items):
    """the validator step alone: the contracts are ALREADY delivered, [(path, expression)]. The pin first (only when there is a contract), then the first refused expression in the given order."""
    if items:
        pin = resolve_pin(declarations)
        if pin[0] == "refuse":
            return ("refuse", pin[1], None)
    for path, e in items:
        code, _ = C.classify(e)
        if code:
            return ("refuse", code, "/".join(map(str, path)))
        if PLANT == "stop-at-first-accept":            # planted: the verdict class then depends on the delivery order
            return ("accept",)
    return ("accept",)


def validate(schema_text, declarations):
    """the validation order of the specification: reader, then the pin (only when the schema has at least one pattern contract), then the expressions in document order"""
    try:
        doc = read(schema_text)
        items = list(contracts(doc))
        exprs = []
        for path, el in items:
            e = el.get("expression")
            if not isinstance(e, str):
                raise ReaderError("expression_not_a_string", "/".join(map(str, path)))
            exprs.append((path, e))
    except ReaderError as r:
        return ("reader_error", r.kind, r.path)
    if exprs:
        pin = resolve_pin(declarations)
        if pin[0] == "refuse":
            return ("refuse", pin[1], None)
    for path, e in exprs:
        code, _ = C.classify(e)
        if code:
            return ("refuse", code, "/".join(map(str, path)))
        if PLANT == "stop-at-first-accept":            # planted: the verdict class then depends on the delivery order
            return ("accept",)
    return ("accept",)
