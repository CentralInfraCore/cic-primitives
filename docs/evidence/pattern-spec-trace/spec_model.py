"""An executable reading of the NEW rules of the implementation specification (docs/en/GRAMMAR-PATTERN-IMPLEMENTATION-SPEC.md): the profile version resolution (the exact type), the deterministic traversal
of nested contracts, the boundary between the document reader and the pattern validator, and the validation order. An ISOLATED model, not an implementation: its only purpose is to make the proposed
extension cases (docs/design/pattern-profile-spec/extension-cases.yaml) derivable from the text, and to show that the new rules reproduce the verdicts of the schema vectors of the approved set.
Expression classification is delegated to the existing prototype (pattern_codes.classify): the profile rules themselves are not restated here.

Outcomes: ("accept",) | ("refuse", code, path) | ("reader_error", kind, path). A reader_error is OUTSIDE the pattern code set: the pattern validator never sees such a document.
"""
import os, sys, json

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


def resolve_pin(declarations):
    """declarations: the raw typed values the reader found, in document order (a declaration with the value null is a declaration). -> ('ok',) | ('refuse', code)"""
    if not declarations:
        return ("refuse", "pattern_profile_missing")
    distinct = {(type(v).__name__, json.dumps(v, sort_keys=True, default=str)) for v in declarations}
    if len(distinct) > 1:
        return ("refuse", "pattern_profile_conflict")
    v = declarations[0]
    ok = (type(v) is int and v == KNOWN_VERSION) if PLANT != "equality-version" else (v == KNOWN_VERSION)      # planted: Python equality accepts true and 1.0
    return ("ok",) if ok else ("refuse", "pattern_profile_unknown")


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
    return ("accept",)
