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


class TMap(object):
    """a TYPE-PRESERVING mapping: a list of (key, value) pairs with typed keys. A host-language dict is not used for a pin value, because Python merges the keys 1, True and 1.0 (they are equal and hash alike)
    while the specification defines three keys of three type classes."""
    def __init__(self, pairs):
        self.pairs = list(pairs)

    def __repr__(self):
        return "TMap(%r)" % (self.pairs,)


class _OrderedLoader(yaml.SafeLoader):
    """the DOCUMENT READER for the schema: mapping entries stay in source order; EVERY mapping key of the schema document must be a string (a non-string key is a reader error, an unambiguous input
    restriction: no type clash is possible); a duplicate key is a READER error, never a pattern code. The pin declarations are NOT read by this loader (see _TypedLoader)."""


def _mapping(loader, node, deep=False):
    seen = set()
    for knode, _ in node.value:
        k = loader.construct_object(knode, deep=deep)
        if not isinstance(k, str):
            raise ReaderError("non_string_key", repr(k))
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


class _TypedLoader(yaml.SafeLoader):
    """the reader of a PIN VALUE: scalars keep their resolved type (int, bool, float, str, null), sequences are lists, and EVERY mapping is a TMap whose keys keep their type; a duplicate key is detected by
    the IDENTITY RULE OF THE SPECIFICATION (1, true and 1.0 are three different keys, 0.0 and -0.0 two), never by the host language's equality; a mapping key that is not a scalar is a reader error"""


def _typed_mapping(loader, node, deep=False):
    pairs = []
    for knode, vnode in node.value:
        if not isinstance(knode, yaml.ScalarNode):
            raise ReaderError("non_scalar_key")
        k = loader.construct_object(knode, deep=True)
        v = loader.construct_object(vnode, deep=True)
        if PLANT == "python-keys":                         # planted: the host language's equality decides (1 == True == 1.0)
            if any(k == k2 for k2, _ in pairs):
                raise ReaderError("duplicate_key", repr(k))
        elif any(identical(k, k2) for k2, _ in pairs):
            raise ReaderError("duplicate_key", repr(k))
        pairs.append((k, v))
    return TMap(pairs)


_TypedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _typed_mapping)


def read_pin(text):
    """the pin declarations as the reader delivers them, from YAML text: a list of typed values. Raises ReaderError."""
    try:
        v = yaml.load(text, Loader=_TypedLoader)
    except ReaderError:
        raise
    except yaml.YAMLError:
        raise ReaderError("yaml_syntax")
    if not isinstance(v, list):
        raise ReaderError("pin_declarations_not_a_list")
    return v


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
    if isinstance(v, (dict, TMap)):
        return "map"
    raise ReaderError("unsupported_yaml_value")


def _pairs(m):
    return list(m.pairs) if isinstance(m, TMap) else list(m.items())


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
    pa, pb = _pairs(a), _pairs(b)
    if len(pa) != len(pb):
        return False
    rest = list(pb)
    for k, v in pa:
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


# THE DOMAIN TAGS (a rule of the specification: one tag per component and per identifier, so that no two of them can ever produce the same digest from the same bytes; the specification text lists them and the
# check compares the text with these constants)
TAG_CONTRACTS_CONTENT = b"cic.pattern.contracts.content/1"
TAG_CONTRACTS_DELIVERY = b"cic.pattern.contracts.delivery/1"
TAG_PIN_ORDERED = b"cic.pattern.pin.ordered/1"
TAG_PIN_SET = b"cic.pattern.pin.set/1"
TAG_CLASS = b"cic.pattern.class/1"
TAG_RESULT = b"cic.pattern.result/1"
ALL_TAGS = [TAG_CONTRACTS_CONTENT, TAG_CONTRACTS_DELIVERY, TAG_PIN_ORDERED, TAG_PIN_SET, TAG_CLASS, TAG_RESULT]


def _tagged(tag, count):
    """the start of every component digest: the domain tag and the number of entries (planted: no tag, the untagged digest the review found)"""
    return hashlib.sha256(b"" if PLANT == "no-domain-tags" and tag in (TAG_CONTRACTS_CONTENT, TAG_CONTRACTS_DELIVERY) else tag + struct.pack(">Q", count))


def delivery_digest(items):
    """the DELIVERY DIGEST (specification, binding of the result to its input): SHA-256 over a length-prefixed encoding of the ORDERED list of (path, expression) pairs as the reader delivers them.
    items: [(path, expression)]. The order is part of the input: two documents with the same contracts in another delivery order have different delivery digests."""
    seq = list(items)
    if PLANT == "digest-sorted":                       # planted: an order-erasing digest, which cannot tell the two orders apart
        seq = sorted(seq, key=lambda it: (_enc_path(it[0]), it[1]))
    h = _tagged(TAG_CONTRACTS_DELIVERY, len(seq))
    for path, expr in seq:
        h.update(_enc_path(path)); h.update(_lp(expr.encode("utf-8")))
    return h.hexdigest()


def content_digest(items):
    """the order-erasing digest of the same contracts (what a canonical form that sorts keys would see)"""
    h = _tagged(TAG_CONTRACTS_CONTENT, len(items))
    for path, expr in sorted(items, key=lambda it: (_enc_path(it[0]), it[1])):
        h.update(_enc_path(path)); h.update(_lp(expr.encode("utf-8")))
    return h.hexdigest()


_NAN_BITS = struct.pack(">Q", 0x7ff8000000000000)


def enc(v):
    """the TYPED CANONICAL ENCODING of a declared value (a rule of the specification): a type tag, then the payload, so that two values have the same encoding IF AND ONLY IF they are identical in the sense of
    `identical`. null N; bool B0/B1; int I + length-prefixed decimal ASCII; float F + 8 bytes (the binary64 bit pattern, every NaN as one canonical NaN); str S + length-prefixed UTF-8;
    list L + count + the encodings in order; mapping M + count + the entry encodings (key encoding + value encoding) SORTED as byte strings (the entry order is irrelevant)."""
    k = kind(v)
    if k == "null":
        return b"N"
    if k == "bool":
        return b"B1" if v else b"B0"
    if k == "int":
        return b"I" + _lp(str(v).encode("ascii"))
    if k == "float":
        return b"F" + (_NAN_BITS if v != v else struct.pack(">d", v))
    if k == "str":
        return b"S" + _lp(v.encode("utf-8"))
    if k == "list":
        return b"L" + struct.pack(">Q", len(v)) + b"".join(enc(x) for x in v)
    ents = sorted(enc(a) + enc(b) for a, b in _pairs(v))
    return b"M" + struct.pack(">Q", len(ents)) + b"".join(ents)


def pin_ordered_digest(declarations):
    """a COMPONENT: the declarations as delivered, in order, typed"""
    h = _tagged(TAG_PIN_ORDERED, len(declarations))
    for d in declarations:
        h.update(_lp(enc(d)))
    return h.hexdigest()


def pin_set_digest(declarations):
    """a COMPONENT: the SET of the distinct declared values (identity classes), typed and sorted; the pin resolution depends only on this set"""
    encs = sorted({enc(d) for d in declarations})
    h = _tagged(TAG_PIN_SET, len(encs))
    for e in encs:
        h.update(_lp(e))
    return h.hexdigest()


def _key(tag, profile_version, contracts_digest, pin_digest, implementation, conformance_ref):
    h = hashlib.sha256(tag)
    h.update(enc(profile_version)); h.update(_lp(contracts_digest.encode("ascii")))
    if PLANT != "key-without-pin":                     # planted: a key that does not bind the pin declarations (the review's FALSE_REUSE)
        h.update(_lp(pin_digest.encode("ascii")))
    h.update(_lp(implementation.encode("utf-8"))); h.update(_lp(conformance_ref.encode("ascii")))
    return h.hexdigest()


def class_key(profile_version, items, declarations, implementation, conformance_ref):
    """the key under which the accept/refuse CLASS of a validation may be reused: the profile version, the contracts WITHOUT their order (content digest), the pin declarations as a typed SET,
    the implementation identity and the conformance reference (the approved vector file hash)"""
    return _key(TAG_CLASS, profile_version, content_digest(items), pin_set_digest(declarations), implementation, conformance_ref)


def result_key(profile_version, items, declarations, implementation, conformance_ref):
    """THE FULL EVIDENCE IDENTIFIER of a validation result: the same context, with the contracts and the pin declarations IN THE ORDER DELIVERED. Only an equal result key makes the reported code and path reusable."""
    return _key(TAG_RESULT, profile_version, delivery_digest(items), pin_ordered_digest(declarations), implementation, conformance_ref)


def may_reuse(prev, cur, what):
    """prev, cur: dicts with class_key, result_key, content (the contracts content digest) and delivery (the contracts delivery digest). what: 'class' | 'code_path' | 'result'.
    A COMPONENT digest alone is never a reuse key."""
    if PLANT == "reuse-by-partial":                    # planted: the contracts digest alone decides
        return prev["content"] == cur["content"] if what == "class" else prev["delivery"] == cur["delivery"]
    return prev["class_key"] == cur["class_key"] if what == "class" else prev["result_key"] == cur["result_key"]


def evidence_for_schema(schema_text, declarations, profile_version, implementation, conformance_ref):
    """THE SCOPE OF THE KEYS (review F5 of #52): the class key and the evidence identifier identify ONLY the verdict of the SCHEMA PATTERN VALIDATION that follows a SUCCESSFUL document read. A document the
    reader refuses gets no key (None); a key contains no record value and no budget context and is no identifier of a value validation, of a reader error or of a release verdict."""
    try:
        items = deliver(schema_text)
    except ReaderError:
        if PLANT == "key-on-reader-error":                 # planted: a key is issued for a document the reader refused
            return dict(class_key="x", result_key="y", verdict=("reader_error",))
        return None
    return dict(class_key=class_key(profile_version, items, declarations, implementation, conformance_ref),
                result_key=result_key(profile_version, items, declarations, implementation, conformance_ref), verdict=validate_delivered(declarations, items))


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


def validate_case(schema_text, pin=None, pin_text=None):
    """a case of the extension file: the pin declarations as typed values (pin) or as YAML text read by the type-preserving reader (pin_text); a reader error of the pin is an outcome, not a crash"""
    try:
        decl = read_pin(pin_text) if pin_text is not None else pin
    except ReaderError as r:
        return ("reader_error", r.kind, None)
    return validate(schema_text, decl)


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
