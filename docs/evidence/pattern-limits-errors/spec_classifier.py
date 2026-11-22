"""A SECOND implementation of the proposed refusal order, written from the SPECIFICATION TEXT of section 3.2 of GRAMMAR-PATTERN-LIMITS-AND-ERRORS.md (rules T1..T3, S1..S6, C1..C4, Q1..Q6)
and NOT from subset_check.py / pattern_codes.py: it imports neither. Its job is to show that the text alone determines the verdict (review F1 of #48): codes_probe.py compares it with the
prototype over the precedence cases, the multi-defect cases and the seeded random corpus; any disagreement is a defect of the text or of one implementation.
It is written by the same author as the prototype, so the independence is limited to the code path; the differential is evidence for the text, not a proof.

Returns the code ('' when accepted). The environment variable CIC_SPEC_PLANT switches on a planted defect for the self-test only.
"""
import os

PLANT = os.environ.get("CIC_SPEC_PLANT", "")
LIMIT_LEN, LIMIT_COUNT, LIMIT_DEPTH, LIMIT_UNB, LIMIT_PROD, PI_MAX = 256, 255, 4, 3, 1000, 2048
ESC = set("\\.[](){}*+?|^$-")
NEUTRAL = "xx"


class Stop(Exception):
    def __init__(self, code):
        self.code = code


def classify(text):
    try:
        # T1: whole text, fixed order
        if text == "":
            raise Stop("pattern_empty")
        if len(text) > LIMIT_LEN:
            raise Stop("pattern_too_long")
        if any(not (0x20 <= ord(c) <= 0x7E) for c in text):
            raise Stop("pattern_not_ascii_printable")
        body = text[1:] if text[0] == "^" else text
        if body.endswith("$"):
            k = 0
            j = len(body) - 2
            while j >= 0 and body[j] == "\\":
                k += 1; j -= 1
            if k % 2 == 0:               # the final $ is the outer end anchor iff an even number of backslashes precedes it
                body = body[:-1]
        sc = _Scan(body)
        tree, _ = sc.alternation(0)
        if sc.i != len(body):            # S5: only a stray ")" can stop the scan early
            raise Stop("pattern_unbalanced_group")
        pi = size(tree)
        if pi > PI_MAX:
            raise Stop("pattern_program_too_large")
        return ""
    except Stop as s:
        return s.code


def size(n):
    k = n[0]
    if k == "atom":
        return 1
    if k == "seq":
        return sum(size(c) for c in n[1])
    if k == "alt":
        return 1 + sum(size(c) for c in n[1])
    _, child, lo, hi = n
    x = size(child)
    if hi is None:
        return 1 + (lo + 1) * x
    return lo * x + (hi - lo) * (1 + x)


class _Scan:
    def __init__(self, body):
        self.b = body
        self.i = 0
        self.unb = 0

    def at(self, k=0):
        j = self.i + k
        return self.b[j] if j < len(self.b) else ""

    # S1: an alternation entered at depth d
    def alternation(self, d):
        if d > LIMIT_DEPTH:
            raise Stop("pattern_nesting_too_deep")
        branches, prods = [], []
        while True:
            seq, prod = self.sequence(d)
            branches.append(seq); prods.append(prod)
            if self.at() == "|":
                self.i += 1
                continue
            break
        node = branches[0] if len(branches) == 1 else ("alt", branches)
        return node, max(prods)

    # S2: a sequence of repeat items up to "|", ")" or the end; empty -> pattern_empty_branch
    def sequence(self, d):
        items, prod = [], 1
        start = self.i
        while self.at() not in ("", "|", ")"):
            it, p = self.item(d)
            items.append(it); prod = max(prod, p)
        if self.i == start:
            raise Stop("pattern_empty_branch")
        return ("seq", items), prod

    # S3 + S4: an atom and its optional quantifier
    def item(self, d):
        atom, is_group, inner_prod = self.atom(d)
        node, prod = atom, inner_prod
        c = self.at()
        if c in ("*", "+", "?") and c != "":
            self.i += 1
            if c in ("*", "+"):
                self.count_unbounded()
                if is_group:
                    raise Stop("pattern_unbounded_on_group")      # Q2
                node = ("rep", atom, 0 if c == "*" else 1, None)
            else:
                node = ("rep", atom, 0, 1)
        elif c == "{":
            node, prod = self.braces(atom, is_group, inner_prod)
        if self.at() != "" and self.at() in "?*+{":                # Q6: a quantifier directly after a quantifier
            raise Stop("pattern_quantifier_not_greedy")
        return node, prod

    def count_unbounded(self):
        self.unb += 1
        if self.unb > LIMIT_UNB:
            raise Stop("pattern_unbounded_too_many")                # Q1 precedes Q2

    def braces(self, atom, is_group, inner_prod):
        j = self.i + 1
        d1 = ""
        while j < len(self.b) and self.b[j].isdigit() and self.b[j] in "0123456789":
            d1 += self.b[j]; j += 1
        if d1 == "":
            raise Stop("pattern_quantifier_malformed")
        comma, d2 = False, ""
        if j < len(self.b) and self.b[j] == ",":
            comma = True; j += 1
            while j < len(self.b) and self.b[j] in "0123456789":
                d2 += self.b[j]; j += 1
        if j >= len(self.b) or self.b[j] != "}":
            raise Stop("pattern_quantifier_malformed")
        self.i = j + 1
        n = int(d1)
        hi = int(d2) if d2 != "" else None
        for digits in (d1, d2):                                       # Q3
            if len(digits) > 1 and digits[0] == "0":
                raise Stop("pattern_quantifier_leading_zero")
        if comma and hi is not None and hi < n:                       # Q4
            raise Stop("pattern_quantifier_bounds_order")
        if PLANT == "count-before-bounds-spec" and max(n, hi or 0) > LIMIT_COUNT:
            raise Stop("pattern_repeat_count_too_large")
        if comma and hi is None:                                      # Q5: open-ended {n,}
            self.count_unbounded()
            if is_group:
                raise Stop("pattern_unbounded_on_group")
        top = n if not comma else (hi if hi is not None else n)
        if max(n, top) > LIMIT_COUNT:                                 # Q5b
            raise Stop("pattern_repeat_count_too_large")
        prod = inner_prod * max(top, 1)
        if prod > LIMIT_PROD:
            raise Stop("pattern_repeat_product_too_large")
        if not comma:
            return ("rep", atom, n, n), prod
        return ("rep", atom, n, hi), prod

    def atom(self, d):
        c = self.at()
        if c == "(":
            self.i += 1
            if PLANT == "depth-before-extension-spec" and d + 1 > LIMIT_DEPTH:
                raise Stop("pattern_nesting_too_deep")
            if self.at() == "?":
                raise Stop("pattern_group_extension")
            inner, prod = self.alternation(d + 1)
            if self.at() != ")":
                raise Stop("pattern_unbalanced_group")
            self.i += 1
            return inner, True, prod
        if c == "[":
            self.cls()
            return ("atom",), False, 1
        if c == ".":
            self.i += 1
            return ("atom",), False, 1
        if c == "\\":
            e = self.at(1)
            if e == "" or e not in ESC:
                raise Stop("pattern_escape_unsupported")
            self.i += 2
            return ("atom",), False, 1
        if c in "*+?{}]^$":
            raise Stop("pattern_anchor_misplaced" if c in "^$" else "pattern_metachar_unexpected")
        self.i += 1
        return ("atom",), False, 1

    # C1..C4
    def cls(self):
        start = self.i + 1
        j = start
        while j < len(self.b) and self.b[j] != "]":
            j += 2 if self.b[j] == "\\" else 1
        text = self.b[start:min(j, len(self.b))]
        flat = []
        k = 0
        while k < len(text):
            if text[k] == "\\":
                flat.append(NEUTRAL); k += 2
            else:
                flat.append(text[k]); k += 1
        flat = "".join(flat)
        ops = ("&&", "--", "~~")
        if PLANT not in ("no-class-precheck-spec", "class-reading-order-spec") and any(o in flat for o in ops):   # C1: the pre-check, before anything else of the class
            raise Stop("pattern_class_set_operator")
        self.i = start
        if self.at() == "^":                                           # C2
            raise Stop("pattern_class_negated")
        n = 0
        while self.at() != "]":                                        # C3
            if self.at() == "":
                raise Stop("pattern_class_unterminated")
            if PLANT == "class-reading-order-spec" and self.b[self.i:self.i + 2] in ops:   # the rule of the previous text of 3.2: pure reading order
                raise Stop("pattern_class_set_operator")
            a = self.cls_char()
            n += 1
            if self.at() == "-" and self.at(1) not in ("]", ""):
                self.i += 1
                b = self.cls_char()
                if ord(b) < ord(a):
                    raise Stop("pattern_class_range_order")
        if n == 0:                                                     # C4
            raise Stop("pattern_class_empty")
        self.i += 1

    def cls_char(self):
        c = self.at()
        self.i += 1
        if c == "[":
            raise Stop("pattern_class_nested_or_posix")
        if c == "\\":
            e = self.at()
            self.i += 1
            if e == "" or e not in ESC:
                raise Stop("pattern_escape_unsupported")
            return e
        return c
