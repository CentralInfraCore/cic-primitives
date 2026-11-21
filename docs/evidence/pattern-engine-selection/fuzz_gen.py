"""Deterministic generator of (pattern, input) cases for the differential run. Patterns are drawn from the grammar of the closed subset (and sometimes outside it on purpose: the
classifier decides, and the number it refuses is reported); inputs are a matching sample, near misses and random strings, including LF, a non-ASCII and an astral code point.
Usage: gen(n_patterns, seed) -> (cases, stats). case = {id, p, input (str)}."""
import os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import nfa_engine as N
import subset_check as S
LITS = list("abc01-./_:x"); META = set("\\.[]()*+?{}|^$")
EXTRA = ["\n", "é", "\U0001F600", " ", "A"]


def lit(rng):
    c = rng.choice(LITS + ["\\.", "\\-", "\\$", "\\*", "\\(", "\\[", "\\\\"])
    return c


def cls(rng):
    items = []
    for _ in range(rng.randint(1, 3)):
        k = rng.random()
        if k < 0.5:
            a = rng.choice("0aAx"); b = chr(ord(a) + rng.randint(0, 5)); items.append("%s-%s" % (a, b))
        elif k < 0.7:
            items.append(rng.choice(["&", "~", "\\-", "\\]", ".", "_"]))
        else:
            items.append(rng.choice("abc01"))
    if rng.random() < 0.15:
        items.append("-")
    return "[" + "".join(items) + "]"


def quant(rng, group):
    k = rng.random()
    if k < 0.45:
        return ""
    if k < 0.6:
        return "?"
    if k < 0.75 and not group:
        return rng.choice(["*", "+", "{2,}"])
    if k < 0.85:
        return "{%d}" % rng.randint(0, 4)
    return "{%d,%d}" % (lambda a: (a, a + rng.randint(0, 4)))(rng.randint(0, 3))


def gen_alt(rng, depth):
    return "|".join(gen_cat(rng, depth) for _ in range(rng.choice([1, 1, 1, 2, 3])))


def gen_cat(rng, depth):
    return "".join(gen_rep(rng, depth) for _ in range(rng.randint(1, 4)))


def gen_rep(rng, depth):
    k = rng.random()
    if k < 0.5:
        a, group = lit(rng), False
    elif k < 0.6:
        a, group = ".", False
    elif k < 0.8:
        a, group = cls(rng), False
    elif depth < 3:
        a, group = "(" + gen_alt(rng, depth + 1) + ")", True
    else:
        a, group = lit(rng), False
    return a + quant(rng, group if rng.random() < 0.9 else False)   # 10%: an unbounded quantifier on a group may appear (the classifier must refuse it)


def sample(node, rng):
    k = node[0]
    if k == "lit":
        return node[1]
    if k == "any":
        return rng.choice(["a", "é", "\U0001F600", " ", "0"])
    if k == "cls":
        lo, hi = rng.choice(node[1]); return chr(rng.randint(lo, hi))
    if k == "cat":
        return "".join(sample(x, rng) for x in node[1])
    if k == "alt":
        return sample(rng.choice(node[1]), rng)
    _, inner, lo, hi = node
    n = rng.randint(lo, (hi if hi is not None else lo + 3))
    return "".join(sample(inner, rng) for _ in range(n))


def gen(n, seed):
    rng = random.Random(seed); cases = []; st = {"patterns": 0, "refused_by_classifier": 0, "cases": 0}
    tries = 0
    while st["patterns"] < n and tries < n * 20:
        tries += 1
        body = gen_alt(rng, 0)
        p = ("^" if rng.random() < 0.5 else "") + body + ("$" if rng.random() < 0.5 else "")
        if not S.parse(p).ok:
            st["refused_by_classifier"] += 1; continue
        st["patterns"] += 1
        ast = N.parse_ast(p)
        pool = [sample(ast, rng) for _ in range(2)]
        vals = list(pool)
        vals += [v + rng.choice(LITS + EXTRA) for v in pool[:1]] + [pool[0][:-1], pool[0] + "\n", "\n" + pool[0], ""]
        for _ in range(3):
            vals.append("".join(rng.choice(LITS + EXTRA) for _ in range(rng.randint(0, 8))))
        for j, v in enumerate(vals):
            if len(v) <= 256:
                cases.append({"id": "fz.%d.%d" % (st["patterns"], j), "p": p, "input": v}); st["cases"] += 1
    return cases, st


if __name__ == "__main__":
    cs, st = gen(int(sys.argv[1]) if len(sys.argv) > 1 else 5, 1)
    print(st)
    for c in cs[:12]:
        print(repr(c["p"]), repr(c["input"]))
