"""Shared reading of docs/design/pattern-profile-vectors/pattern-profile.yaml: loading and the decoding of the {seq: [...]} encoding. No implementation of the profile is imported here."""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.path.join(HERE, "..", "..", "design", "pattern-profile-vectors", "pattern-profile.yaml")


def load(path=None):
    import yaml
    with open(path or os.environ.get("CIC_VECTORS", DEFAULT), encoding="utf-8") as f:
        return yaml.safe_load(f)


def dec(x):
    """a plain string, or {seq: [ 'text' | [codepoint, count] ... ]} -> the Python string (a lone surrogate is a legal Python str)"""
    if isinstance(x, str):
        return x
    if isinstance(x, dict) and set(x) == {"seq"}:
        out = []
        for e in x["seq"]:
            if isinstance(e, str):
                out.append(e)
            else:
                cp, n = e
                out.append(chr(cp) * n)
        return "".join(out)
    raise ValueError("not an expression or value encoding: %r" % (x,))


def show(x, n=48):
    s = dec(x)
    t = "".join(c if 0x20 <= ord(c) <= 0x7E else "\\u%04x" % ord(c) for c in s)
    return t if len(t) <= n else t[:n] + "...(%d)" % len(s)
