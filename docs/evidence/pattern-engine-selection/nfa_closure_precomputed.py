"""SUPERSEDED COMPARATOR (the evaluator as reviewed at d1e0b8c): it precomputes the epsilon closure of EVERY state at compile time. Kept only so closure_probe.py can measure what that cost
(review finding F1). Not a candidate; nfa_engine.py is.

CANDIDATE D of the engine selection (as at d1e0b8c): a small linear-time evaluator for the CLOSED pattern subset (pure Python, no dependency). A MEASUREMENT prototype, not production code.

Design: the text is first judged by the closed-subset classifier (subset_check.parse); only an accepted text is parsed here, so the set of texts that RUN is exactly the set the
grammar accepts. The expression (outer anchors removed) becomes a Thompson NFA over Unicode code points (a repetition {n,m} is expanded into copies; the profile limits bound the
size), and a value is matched as a FULL match by simulating the set of states, one code point at a time: O(states x value length) in the worst case, never backtracking.
`.` is any code point except LF. A class is a list of ASCII ranges. Nothing else exists.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "grammar-pattern-measurement"))
import subset_check as S


class Refused(Exception):
    pass


def strip_anchors(p):
    a = p.startswith("^")
    b = p.endswith("$") and not _escaped_dollar(p)
    return p[(1 if a else 0):len(p) - (1 if b else 0)]


def _escaped_dollar(p):
    n = 0; i = len(p) - 2
    while i >= 0 and p[i] == "\\":
        n += 1; i -= 1
    return n % 2 == 1


class _Parser:
    """Recursive descent over a text the classifier has ALREADY accepted (so it checks little)."""
    def __init__(self, s):
        self.s, self.i = s, 0

    def peek(self):
        return self.s[self.i] if self.i < len(self.s) else None

    def alt(self):
        branches = [self.cat()]
        while self.peek() == "|":
            self.i += 1; branches.append(self.cat())
        return branches[0] if len(branches) == 1 else ("alt", branches)

    def cat(self):
        items = []
        while self.peek() not in (None, "|", ")"):
            items.append(self.rep())
        return ("cat", items)

    def rep(self):
        atom = self.atom()
        c = self.peek()
        if c == "*":
            self.i += 1; return ("rep", atom, 0, None)
        if c == "+":
            self.i += 1; return ("rep", atom, 1, None)
        if c == "?":
            self.i += 1; return ("rep", atom, 0, 1)
        if c == "{":
            j = self.s.index("}", self.i)
            body = self.s[self.i + 1:j]; self.i = j + 1
            if "," not in body:
                n = int(body); return ("rep", atom, n, n)
            lo, hi = body.split(","); return ("rep", atom, int(lo), int(hi) if hi else None)
        return atom

    def atom(self):
        c = self.s[self.i]; self.i += 1
        if c == "(":
            node = self.alt(); self.i += 1; return node
        if c == "[":
            return self.cls()
        if c == ".":
            return ("any",)
        if c == "\\":
            e = self.s[self.i]; self.i += 1; return ("lit", e)
        return ("lit", c)

    def cls(self):
        ranges = []
        while self.s[self.i] != "]":
            a = self.chr()
            if self.s[self.i] == "-" and self.s[self.i + 1] != "]":
                self.i += 1; b = self.chr(); ranges.append((ord(a), ord(b)))
            else:
                ranges.append((ord(a), ord(a)))
        self.i += 1
        return ("cls", ranges)

    def chr(self):
        c = self.s[self.i]; self.i += 1
        if c == "\\":
            c = self.s[self.i]; self.i += 1
        return c


def parse_ast(p):
    """AST of an expression the classifier accepts; Refused otherwise (fail-closed: no engine ever sees an unaccepted text)."""
    r = S.parse(p)
    if not r.ok:
        raise Refused(r.reason)
    return _Parser(strip_anchors(p)).alt()


class _Prog:
    def __init__(self):
        self.t = []          # per state: list of (kind, arg, next); kind: eps | c | any | cls
        self.accept = self.new()

    def new(self):
        self.t.append([]); return len(self.t) - 1

    def build(self, node, nxt):
        k = node[0]
        if k == "lit":
            s = self.new(); self.t[s].append(("c", node[1], nxt)); return s
        if k == "any":
            s = self.new(); self.t[s].append(("any", None, nxt)); return s
        if k == "cls":
            s = self.new(); self.t[s].append(("cls", node[1], nxt)); return s
        if k == "cat":
            cur = nxt
            for it in reversed(node[1]):
                cur = self.build(it, cur)
            return cur
        if k == "alt":
            s = self.new()
            for b in node[1]:
                self.t[s].append(("eps", None, self.build(b, nxt)))
            return s
        _, inner, lo, hi = node
        if hi is None:                                   # unbounded: a loop state; `lo` mandatory copies in front
            loop = self.new()
            self.t[loop].append(("eps", None, self.build(inner, loop))); self.t[loop].append(("eps", None, nxt))
            cur = loop
        else:                                            # bounded: (x(x(x)?)?)? after `lo` mandatory copies
            cur = nxt
            for _ in range(hi - lo):
                o = self.new()
                self.t[o].append(("eps", None, self.build(inner, cur))); self.t[o].append(("eps", None, nxt))
                cur = o
        for _ in range(lo):
            cur = self.build(inner, cur)
        return cur


class Matcher:
    def __init__(self, p):
        ast = parse_ast(p)
        self.prog = _Prog()
        self.start = self.prog.build(ast, self.prog.accept)
        t = self.prog.t
        self.closure = []
        for s in range(len(t)):                          # the consuming (or accepting) states reachable by epsilon moves only
            seen, stack, out = {s}, [s], []
            while stack:
                x = stack.pop()
                eps = [e for e in t[x] if e[0] == "eps"]
                if x == self.prog.accept or len(eps) != len(t[x]):
                    out.append(x)
                for _, _, n in eps:
                    if n not in seen:
                        seen.add(n); stack.append(n)
            self.closure.append(tuple(out))
        self.states = len(t)

    def fullmatch(self, value):
        t, cl, acc = self.prog.t, self.closure, self.prog.accept
        cur = set(cl[self.start])
        for ch in value:
            o = ord(ch); nxt = set()
            for s in cur:
                for kind, arg, n in t[s]:
                    if kind == "c":
                        ok = arg == ch
                    elif kind == "any":
                        ok = ch != "\n"
                    elif kind == "cls":
                        ok = any(lo <= o <= hi for lo, hi in arg)
                    else:
                        continue
                    if ok:
                        nxt.update(cl[n])
            cur = nxt
            if not cur:
                return False
        return acc in cur


def compile(p):
    return Matcher(p)
