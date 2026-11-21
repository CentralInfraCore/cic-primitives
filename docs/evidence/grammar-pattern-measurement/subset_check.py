r"""PROTOTYPE of the closed pattern subset (candidate P1 profile). A MEASUREMENT tool of the design, not a grammar change and not production code.

Grammar of the candidate subset (everything not listed is refused; there is no fallback to the native engine):
  pattern := ['^'] alt ['$']        '^' and '$' only at the OUTER boundary (an anchor anywhere else is refused)
  alt     := concat ('|' concat)*
  concat  := repeat*
  repeat  := atom [quant]           quant := '*' | '+' | '?' | '{n}' | '{n,m}' | '{n,}'     (greedy only; '??', '*?', '+?', '{n,m}?' refused)
  atom    := literal | '.' | class | '(' alt ')'                  (a group is plain: '(?' of any kind is refused)
  class   := '[' item+ ']'          item := char | char '-' char   (ASCII; NO negated class, no escape other than the listed ones, no POSIX class)
  literal := an ASCII printable char that is not a metacharacter, or '\' + one of  \ . [ ] ( ) * + ? { } | ^ $ -
Metacharacters: \ . [ ] ( ) * + ? { } | ^ $
The pattern text itself is ASCII printable only (0x20..0x7E).
Counts are written without leading zeros ('{0}' is fine, '{01}' is refused); every alternative, group and the body is non-empty; inside a class the pairs '&&', '--', '~~' are refused.
The limits bound the SIZE of the compiled program, NOT the worst-case time of a backtracking engine (see the timing probe): the evaluator must be linear-time.
Limits (CANDIDATE values, to be decided from the measurement): see LIMITS.
parse(p) returns a Result(ok, reason, stats) ; stats = length, max_repeat, depth, groups, unbounded (number of unbounded quantifiers), alt (alternations).
"""
import re
from collections import namedtuple

LIMITS = {"length": 256, "repeat": 255, "depth": 4, "unbounded": 3, "repeat_product": 1000}   # candidate values, to be decided from the measurement
META = set("\\.[]()*+?{}|^$")
ESCAPABLE = set("\\.[]()*+?{}|^$-")
Result = namedtuple("Result", "ok reason stats")


class Refused(Exception):
    pass


class P:
    def __init__(self, s):
        self.s, self.i = s, 0
        self.stats = {"length": len(s), "max_repeat": 0, "depth": 0, "groups": 0, "unbounded": 0, "alt": 0, "repeat_product": 1}
        self.rep_stack = [1]   # the product of the repeat counts of the groups an expression is inside

    def peek(self):
        return self.s[self.i] if self.i < len(self.s) else None

    def take(self):
        c = self.peek(); self.i += 1; return c

    def alt(self, depth, end):
        self.stats["depth"] = max(self.stats["depth"], depth)
        prod = self.nonempty_concat(depth, end)
        while self.peek() == "|":
            self.i += 1; self.stats["alt"] += 1; prod = max(prod, self.nonempty_concat(depth, end))
        return prod

    def nonempty_concat(self, depth, end):
        start = self.i
        prod = self.concat(depth, end)
        if self.i == start:
            raise Refused("an empty alternative, empty group or empty body is not in the subset")
        return prod

    def concat(self, depth, end):
        prod = 1
        while True:
            c = self.peek()
            if c is None or c == "|" or c == ")":
                return prod
            prod = max(prod, self.repeat(depth))

    def atom(self, depth):
        c = self.take()
        if c == "(":
            if self.peek() == "?":
                raise Refused("group extension '(?' is not in the subset")
            self.stats["groups"] += 1
            inner = self.alt(depth + 1, -1)
            if self.take() != ")":
                raise Refused("unbalanced parenthesis")
            return "group", inner
        if c == "[":
            n = 0
            start = self.i
            m = re.match(r"(?:\\.|[^\]\\])*", self.s[start:])           # the class text up to its first unescaped ']' (checked BEFORE the range rules, so no other rule can hide it)
            raw = re.sub(r"\\.", "xx", m.group(0))                        # an escaped character cannot form an operator pair
            for op in ("&&", "--", "~~"):
                if op in raw:
                    raise Refused("class set operator %r is not in the subset (Rust regex reads it as intersection, difference or symmetric difference)" % op)
            if self.peek() == "^":
                raise Refused("negated class is not in the subset")
            while self.peek() != "]":
                if self.peek() is None:
                    raise Refused("unterminated class")
                a = self.class_char()
                n += 1
                if self.peek() == "-" and self.s[self.i + 1:self.i + 2] not in ("]", ""):
                    self.i += 1
                    b = self.class_char()
                    if ord(b) < ord(a):
                        raise Refused("class range out of order")
            if n == 0:
                raise Refused("empty class")
            self.i += 1
            return "class", 1
        if c == ".":
            return "dot", 1
        if c == "\\":
            e = self.take()
            if e is None or e not in ESCAPABLE:
                raise Refused("escape \\%s is not in the subset" % (e,))
            return "lit", 1
        if c in META:
            raise Refused("unexpected metacharacter %r" % c)
        return "lit", 1

    def class_char(self):
        c = self.take()
        if c == "[":
            raise Refused("'[' inside a class (POSIX class or nesting) is not in the subset")
        if c == "\\":
            e = self.take()
            if e is None or e not in ESCAPABLE:
                raise Refused("escape \\%s in a class is not in the subset" % (e,))
            return e
        return c

    def repeat(self, depth):
        kind, prod = self.atom(depth)
        c = self.peek()
        if c in ("*", "+", "?"):
            self.i += 1
            if c != "?":
                self.stats["unbounded"] += 1
                if kind == "group":
                    raise Refused("an unbounded quantifier on a group (resource rule: it may only follow a single atom)")
        elif c == "{":
            m = re.match(r"\{(\d+)(?:(,)(\d*))?\}", self.s[self.i:])
            if not m:
                raise Refused("malformed repetition")
            self.i += m.end()
            n = int(m.group(1)); hi = m.group(3)
            for num in (m.group(1), hi):
                if num and len(num) > 1 and num[0] == "0":
                    raise Refused("a repetition count with a leading zero is not in the subset")
            top = n if not m.group(2) else (int(hi) if hi else n)
            if m.group(2) and hi and int(hi) < n:
                raise Refused("repetition bounds out of order")
            if m.group(2) and not hi:
                self.stats["unbounded"] += 1
                if kind == "group":
                    raise Refused("an unbounded quantifier on a group (resource rule: it may only follow a single atom)")
            self.stats["max_repeat"] = max(self.stats["max_repeat"], top, n)
            prod *= max(top, 1)
            self.stats["repeat_product"] = max(self.stats["repeat_product"], prod)
        if self.peek() in ("?", "*", "+", "{"):
            raise Refused("lazy, possessive or stacked quantifier is not in the subset")
        return prod


def parse(p):
    st = {}
    try:
        if not p:
            raise Refused("empty pattern")
        if any(not (0x20 <= ord(ch) <= 0x7E) for ch in p):
            raise Refused("the pattern text is not ASCII printable")
        s = p
        a = s.startswith("^")
        # a trailing '$' is the outer end anchor only when it is not escaped
        b = s.endswith("$") and not re.search(r"(?<!\\)(\\\\)*\\\$$", s)
        body = s[(1 if a else 0):len(s) - (1 if b else 0)]
        q = P(body); st = q.stats
        q.alt(0, -1)
        if q.i != len(body):
            raise Refused("unexpected %r at %d" % (body[q.i], q.i))
        if "^" in re.sub(r"\\.|\[(?:\\.|[^\]])*\]", "", body):
            raise Refused("'^' is allowed only at the outer start")
        if "$" in re.sub(r"\\.|\[(?:\\.|[^\]])*\]", "", body):
            raise Refused("'$' is allowed only at the outer end")
        if st["length"] > LIMITS["length"]:
            raise Refused("longer than the length limit %d" % LIMITS["length"])
        if st["max_repeat"] > LIMITS["repeat"]:
            raise Refused("a repetition count above the limit %d" % LIMITS["repeat"])
        if st["depth"] > LIMITS["depth"]:
            raise Refused("group nesting deeper than the limit %d" % LIMITS["depth"])
        if st["unbounded"] > LIMITS["unbounded"]:
            raise Refused("more than %d unbounded quantifiers" % LIMITS["unbounded"])
        if st["repeat_product"] > LIMITS["repeat_product"]:
            raise Refused("the product of nested repeat counts exceeds %d" % LIMITS["repeat_product"])
        return Result(True, "", st)
    except Refused as e:
        return Result(False, str(e), st)


if __name__ == "__main__":
    import sys
    for a in sys.argv[1:]:
        r = parse(a); print("%-6s %s %s" % ("ACCEPT" if r.ok else "REFUSE", a, r.reason))
