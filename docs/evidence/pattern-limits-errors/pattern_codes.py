"""O3 reference prototype: normative error codes and their deterministic precedence for the pattern profile (candidate text). An ISOLATED MEASUREMENT tool, not an implementation:
it wraps the existing closed-subset classifier (subset_check.parse) and maps what that refuses to the proposed codes; it adds the proposed size rule (PI, see limit_space.py) as the last tier.

Precedence (the proposal), one code per refused expression, never a list:
  tier 1  whole-text checks, fixed order:   pattern_empty, pattern_too_long (the WHOLE text, anchors included), pattern_not_ascii_printable
  tier 2  one left-to-right scan; the FIRST rule violated in reading order wins; the limits that are counted as the text is read (nesting on entry, a repeat count, the product, the number of
          unbounded quantifiers) belong to this tier and fire at their reading position, and at one position the order of the rules of the scan decides
  tier 3  the size of the whole program (PI > PI_MAX), computed only for a text that passed tiers 1 and 2 (arithmetic on the parsed tree; no program is built)
A value (after the expression was accepted): pattern_value_not_unicode_scalar, then pattern_value_too_long (the matcher is not run), then match / pattern_value_mismatch.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grammar-pattern-measurement"))
sys.path.insert(0, os.path.join(HERE, "..", "pattern-engine-selection"))
import subset_check as S
import nfa_engine as N

PI_MAX = 2048          # CANDIDATE value (O2), decided from results/limit_space.txt
VALUE_MAX = 256        # code points
PLANT = os.environ.get("CIC_CODES_PLANT", "")   # a planted defect for the self-test; empty in every real run

# (regular expression over the classifier's refusal text, code). Exactly one row must match a reason; none or several is a defect of this table (UNMAPPED / AMBIGUOUS).
ROWS = [
    (r"empty pattern", "pattern_empty"),
    (r"longer than the length limit", "pattern_too_long"),
    (r"the pattern text is not ASCII printable", "pattern_not_ascii_printable"),
    (r"group nesting deeper than the limit", "pattern_nesting_too_deep"),
    (r"an empty alternative, empty group or empty body", "pattern_empty_branch"),
    (r"group extension", "pattern_group_extension"),
    (r"unbalanced parenthesis", "pattern_unbalanced_group"),
    (r"unexpected '.*' at \d+", "pattern_unbalanced_group"),
    (r"unexpected metacharacter '[\^$]'", "pattern_anchor_misplaced"),
    (r"unexpected metacharacter '[^\^$]'", "pattern_metachar_unexpected"),
    (r"class set operator", "pattern_class_set_operator"),
    (r"negated class", "pattern_class_negated"),
    (r"unterminated class", "pattern_class_unterminated"),
    (r"empty class", "pattern_class_empty"),
    (r"class range out of order", "pattern_class_range_order"),
    (r"'\[' inside a class", "pattern_class_nested_or_posix"),
    (r"escape .* is not in the subset", "pattern_escape_unsupported"),
    (r"malformed repetition", "pattern_quantifier_malformed"),
    (r"a repetition count with a leading zero", "pattern_quantifier_leading_zero"),
    (r"repetition bounds out of order", "pattern_quantifier_bounds_order"),
    (r"lazy, possessive or stacked quantifier", "pattern_quantifier_not_greedy"),
    (r"a repetition count above the limit", "pattern_repeat_count_too_large"),
    (r"the product of nested repeat counts", "pattern_repeat_product_too_large"),
    (r"more than \d+ unbounded quantifiers", "pattern_unbounded_too_many"),
    (r"an unbounded quantifier on a group", "pattern_unbounded_on_group"),
    (r"'\^' is allowed only at the outer start", "pattern_anchor_misplaced"),
    (r"'\$' is allowed only at the outer end", "pattern_anchor_misplaced"),
]
if PLANT == "row-removed":
    ROWS = [r for r in ROWS if r[1] != "pattern_quantifier_leading_zero"]

ALL_CODES = sorted({c for _, c in ROWS} | {"pattern_program_too_large", "pattern_value_too_long", "pattern_value_mismatch", "pattern_value_not_unicode_scalar"})


def size(node):
    """PI (see limit_space.expanded): the number of NFA states minus the accept state, by recurrence on the tree."""
    k = node[0]
    if k in ("lit", "any", "cls"):
        return 1
    if k == "cat":
        return sum(size(x) for x in node[1])
    if k == "alt":
        return 1 + sum(size(x) for x in node[1])
    _, inner, lo, hi = node
    x = size(inner)
    if PLANT == "size-undercount":
        return (lo + 1) * x if hi is None else hi * x          # forgets the extra state of every optional copy
    return 1 + (lo + 1) * x if hi is None else lo * x + (hi - lo) * (1 + x)


def rows_of(reason):
    return [i for i, (rx, c) in enumerate(ROWS) if re.fullmatch(rx + r".*", reason, re.S)]


def _inner_nodes(node):
    """every repeated sub-expression of the tree (used only by the planted 'early-size' defect: a size check that ignores a later {0})"""
    k = node[0]
    if k in ("cat", "alt"):
        for c in node[1]:
            yield from _inner_nodes(c)
    elif k == "rep":
        yield node[1]
        yield from _inner_nodes(node[1])


def map_reason(reason):
    hits = [ROWS[i][1] for i in rows_of(reason)]
    if not hits:
        return "UNMAPPED"
    if len(set(hits)) > 1:
        return "AMBIGUOUS"
    c = hits[0]
    if PLANT == "nondeterministic" and c == "pattern_quantifier_not_greedy":
        return "pattern_quantifier_not_greedy" if hash(reason) % 2 else "pattern_quantifier_malformed"   # a code chosen by the hash seed
    return c


def classify(p):
    """-> (code, detail); code '' = accepted. Never raises for a str."""
    if PLANT == "charset-before-length":
        if p and any(not (0x20 <= ord(ch) <= 0x7E) for ch in p):
            return "pattern_not_ascii_printable", "tier 1"
    r = S.parse(p)
    if not r.ok:
        return map_reason(r.reason), r.reason
    if PLANT == "no-size-tier":
        return "", ""
    tree = N.parse_ast(p)
    pi = size(tree)
    if PLANT == "early-size" and any(size(inner) > PI_MAX for inner in _inner_nodes(tree)):
        return "pattern_program_too_large", "a subtree alone is above the limit (checked before the repeat factor is known)"
    limit = PI_MAX - 1 if PLANT == "size-off-by-one" else PI_MAX
    if pi > limit:
        return "pattern_program_too_large", "PI=%d > %d" % (pi, limit)
    return "", "PI=%d" % pi


def check_value(p, value):
    """-> verdict: 'match' | 'pattern_value_mismatch' | 'pattern_value_too_long' | 'pattern_value_not_unicode_scalar' (the expression must have been accepted)."""
    code, _ = classify(p)
    if code:
        raise ValueError("the expression is not accepted: " + code)
    if any(0xD800 <= ord(ch) <= 0xDFFF for ch in value):
        return "pattern_value_not_unicode_scalar"
    if PLANT == "value-mismatch-before-length":
        ok = N.Matcher(p).fullmatch(value[:VALUE_MAX])
        if not ok:
            return "pattern_value_mismatch"
    if len(value) > VALUE_MAX:
        return "pattern_value_too_long"
    return "match" if N.Matcher(p).fullmatch(value) else "pattern_value_mismatch"
