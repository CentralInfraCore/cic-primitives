"""A REFERENCE READING of the reader contract (docs/design/pattern-profile-reader/reader-contract.yaml): an executable reading of the RULES, used to check the draft vectors against the draft contract.
It is NOT the implementation of the profile and NOT a conformant YAML 1.2 parser. It takes from PyYAML only the SYNTAX (the event stream: where a scalar, a sequence, a mapping, an alias, an anchor, a tag, a directive
and a style are), and decides EVERYTHING ELSE itself, from the rules: how a plain scalar is typed, which tags are honoured, what a key is, when two keys are the same, which error comes first. PyYAML's own implicit
typing (the YAML 1.1 resolver) and its constructors are never used. Where PyYAML's syntax differs from YAML 1.2 the vectors avoid the construct (open question OQ-7).
CIC_READER_PLANT plants a defect for the self-test only (yaml11-scalars, host-dict-keys, alias-ok, merge-ok, any-tag, float-overflow-inf, bom-ok, dup-ignore, order-semantic-first).
The tree: [n] [b,bool] [i,"decimal"] [f,"16 hex digits"] [s,text] [seq,[...]] [map,[[k,v],...]]."""
import os, re, struct

PLANT = os.environ.get("CIC_READER_PLANT", "")
NULLS = ("~", "null", "Null", "NULL", "")
BOOLS = {"true": True, "True": True, "TRUE": True, "false": False, "False": False, "FALSE": False}
INT10 = re.compile(r"^[-+]?[0-9]+$")
INT8 = re.compile(r"^0o[0-7]+$")
INT16 = re.compile(r"^0x[0-9a-fA-F]+$")
FLOAT = re.compile(r"^[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?$")
INF = re.compile(r"^[-+]?\.(inf|Inf|INF)$")
NAN = re.compile(r"^\.(nan|NaN|NAN)$")
CORE = {"str", "int", "float", "bool", "null", "seq", "map"}
NAN_BITS = "7ff8000000000000"


class ReaderError(Exception):
    def __init__(self, kind):
        super().__init__(kind); self.kind = kind


def _bits(x):
    return NAN_BITS if x != x else struct.pack(">d", x).hex()


def _plain_int(t):
    if PLANT == "yaml11-scalars" and re.match(r"^0[0-7]+$", t):
        return int(t, 8)                                         # planted: the YAML 1.1 octal
    if PLANT == "yaml11-scalars" and re.match(r"^[-+]?[0-9][0-9_]*$", t) and "_" in t:
        return int(t.replace("_", ""))                           # planted: the YAML 1.1 underscore
    if INT10.match(t):
        return int(t, 10)                                        # leading zeros are decimal
    if INT8.match(t):
        return int(t[2:], 8)
    if INT16.match(t):
        return int(t[2:], 16)
    return None


def _plain_float(t, tagged=False):
    """-> bits string or None; raises float_overflow"""
    if INF.match(t):
        return _bits(float("-inf") if t.startswith("-") else float("inf"))
    if NAN.match(t):
        return NAN_BITS
    if FLOAT.match(t):
        v = float(t)
        if v in (float("inf"), float("-inf")):
            if PLANT == "float-overflow-inf":
                return _bits(v)
            raise ReaderError("float_overflow")
        return _bits(v)
    return None


def _resolve_plain(t):
    if t in NULLS:
        return ["n"]
    if t in BOOLS:
        return ["b", BOOLS[t]]
    if PLANT == "yaml11-scalars" and t in ("yes", "Yes", "YES", "no", "No", "NO", "on", "On", "ON", "off", "Off", "OFF"):
        return ["b", t.lower() in ("yes", "on")]                # planted: the YAML 1.1 booleans
    iv = _plain_int(t)
    if iv is not None:
        return ["i", str(iv)]
    fb = _plain_float(t)
    if fb is not None:
        return ["f", fb]
    return ["s", t]


def _by_tag(name, text):
    if name == "str":
        return ["s", text]
    if name == "null":
        if text in NULLS:
            return ["n"]
    elif name == "bool":
        if text in BOOLS:
            return ["b", BOOLS[text]]
    elif name == "int":
        iv = _plain_int(text)
        if iv is not None:
            return ["i", str(iv)]
    elif name == "float":
        fb = _plain_float(text)
        if fb is not None:
            return ["f", fb]
    raise ReaderError("tag_mismatch")


def _identity(node):
    t = node[0]
    if PLANT == "host-dict-keys":                                # planted: the host language's equality (1 == True == 1.0, 0.0 == -0.0)
        if t == "n": return None
        if t == "b": return bool(node[1])
        if t == "i": return int(node[1])
        if t == "f": return struct.unpack(">d", bytes.fromhex(node[1]))[0] if node[1] != NAN_BITS else object()
        return node[1]
    return (t, node[1] if len(node) > 1 else None)


def read(data, mode="plain"):
    """bytes or str -> the typed tree, or raises ReaderError(kind)"""
    import yaml
    raw = data.encode("utf-8") if isinstance(data, str) else data
    # RC-01 encoding
    if raw.startswith(b"\xef\xbb\xbf"):
        if PLANT == "bom-ok":
            raw = raw[3:]
        else:
            raise ReaderError("encoding")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ReaderError("encoding")
    # RC-04 syntax (the whole input is scanned and parsed before any other reader error is decided)
    try:
        events = list(yaml.parse(text))
        tokens = list(yaml.scan(text))
    except yaml.YAMLError:
        raise ReaderError("yaml_syntax")
    if PLANT == "order-semantic-first":
        pass
    # RC-03 directives
    if any(isinstance(t, yaml.DirectiveToken) for t in tokens):
        raise ReaderError("directive_not_allowed")
    # RC-02 documents
    starts = [e for e in events if isinstance(e, yaml.DocumentStartEvent)]
    if not starts:
        raise ReaderError("empty_document")
    if len(starts) > 1:
        raise ReaderError("multiple_documents")
    body = events[[i for i, e in enumerate(events) if isinstance(e, yaml.DocumentStartEvent)][0] + 1:]
    root = body[0]
    if isinstance(root, yaml.ScalarEvent) and root.value == "" and root.style is None and root.tag is None and root.anchor is None:
        raise ReaderError("empty_document")
    pos = [0]

    def node_checks(ev):
        if ev.anchor is not None and PLANT != "alias-ok":
            raise ReaderError("anchor_not_allowed")
        tag = getattr(ev, "tag", None)
        if tag is not None:
            if tag == "!" or not tag.startswith("tag:yaml.org,2002:") or tag[len("tag:yaml.org,2002:"):] not in CORE:
                if PLANT != "any-tag":
                    raise ReaderError("tag_not_allowed")
                return None
            return tag[len("tag:yaml.org,2002:"):]
        return None

    anchors = {}

    def parse_node():
        ev = body[pos[0]]
        if isinstance(ev, yaml.AliasEvent):
            if PLANT == "alias-ok" and ev.anchor in anchors:
                pos[0] += 1
                return anchors[ev.anchor]
            raise ReaderError("alias_not_allowed")
        name = node_checks(ev)
        if isinstance(ev, yaml.ScalarEvent):
            pos[0] += 1
            if name:
                n = _by_tag(name, ev.value)
            elif ev.style is None:
                n = _resolve_plain(ev.value)
            else:
                n = ["s", ev.value]
            if ev.anchor is not None and PLANT == "alias-ok":
                anchors[ev.anchor] = n
            return n
        if isinstance(ev, yaml.SequenceStartEvent):
            if name and name != "seq":
                raise ReaderError("tag_mismatch")
            pos[0] += 1; items = []
            while not isinstance(body[pos[0]], yaml.SequenceEndEvent):
                items.append(parse_node())
            pos[0] += 1
            n = ["seq", items]
            if ev.anchor is not None and PLANT == "alias-ok":
                anchors[ev.anchor] = n
            return n
        if isinstance(ev, yaml.MappingStartEvent):
            if name and name != "map":
                raise ReaderError("tag_mismatch")
            pos[0] += 1; entries = []; seen = []
            while not isinstance(body[pos[0]], yaml.MappingEndEvent):
                kev = body[pos[0]]
                if isinstance(kev, (yaml.SequenceStartEvent, yaml.MappingStartEvent)):
                    node_checks(kev)                                       # anchor, tag first (RC-17), then the key rule
                    raise ReaderError("non_scalar_key")
                knode = parse_node()
                if knode[0] == "s" and knode[1] == "<<" and PLANT != "merge-ok":
                    raise ReaderError("merge_key_not_allowed")
                if mode == "schema" and knode[0] != "s":
                    raise ReaderError("non_string_key")
                ident = _identity(knode)
                if ident in seen and PLANT != "dup-ignore":
                    raise ReaderError("duplicate_key")
                seen.append(ident)
                entries.append([knode, parse_node()])
            pos[0] += 1
            n = ["map", entries]
            if ev.anchor is not None and PLANT == "alias-ok":
                anchors[ev.anchor] = n
            return n
        raise ReaderError("yaml_syntax")

    return parse_node()


def error_kind(data, mode="plain"):
    try:
        read(data, mode); return None
    except ReaderError as e:
        return e.kind
