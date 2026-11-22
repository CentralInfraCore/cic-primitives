"""Adapters of the Python-side candidates behind ONE interface: compile(engine, p) -> a callable value -> bool that answers the FULL-match verdict of the pattern profile for the
ORIGINAL expression p (outer anchors removed, `\\A(?:body)\\z`-style full match, no flags), or raises Unsupported when the engine refuses the expression (fail-closed).
The 256 code point cap on the value is the profile's wrapper, not an engine property: callers apply it (see cap()).
Engines: re2p_default is pyre2 WITHOUT turning the fallback off (measured only to show the hazard). re (stdlib, backtracking, the baseline), regex (PyPI, backtracking), re2g (google-re2, the official bindings), re2p (pyre2, the Cython wrapper; its silent fallback to `re` is
turned OFF here and measured separately), nfa (nfa_engine.py, the own linear-time evaluator). Each engine needs its own interpreter (re2g and re2p both install the module `re2`)."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
VALUE_MAX = 256


class Unsupported(Exception):
    pass


def strip_anchors(p):
    a = p.startswith("^"); b = p.endswith("$") and not re.search(r"(?<!\\)(\\\\)*\\\$$", p)
    return p[(1 if a else 0):len(p) - (1 if b else 0)]


def cap(v):
    return len(v) <= VALUE_MAX


def compile(engine, p):
    body = strip_anchors(p)
    if engine == "re":
        try:
            r = re.compile(r"\A(?:%s)\Z" % body)
        except (re.error, RecursionError, OverflowError) as e:
            raise Unsupported(type(e).__name__)
        return lambda v: r.match(v) is not None
    if engine == "regex":
        import regex
        try:
            r = regex.compile(r"\A(?:%s)\Z" % body)
        except Exception as e:
            raise Unsupported(type(e).__name__)
        return lambda v: r.match(v) is not None
    if engine in ("re2g", "re2p", "re2p_default"):
        import re2
        if engine == "re2p":
            re2.set_fallback_notification(re2.FALLBACK_EXCEPTION)     # fail-closed: no silent fallback to `re`
        try:
            r = re2.compile(r"\A(?:%s)\z" % body)
        except Exception as e:
            raise Unsupported(type(e).__name__)
        return lambda v: r.match(v) is not None
    if engine == "nfa":
        import nfa_engine
        try:
            m = nfa_engine.compile(p)
        except nfa_engine.Refused as e:
            raise Unsupported(str(e))
        return m.fullmatch
    raise SystemExit("unknown engine %s" % engine)
