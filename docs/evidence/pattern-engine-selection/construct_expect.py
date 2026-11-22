"""Independent, hand-authored expected verdicts for the 24 constructs of the profile probe that the closed subset ACCEPTS (review finding F3 of PR #47). Each construct has the original input
and a hand-authored counterpart (a near miss, or a control for the construct that was a refusal-like input). The verdict is the FULL-match verdict of the original expression (outer anchors
removed, no flags, `.` = one code point except LF). Nothing here was produced by running an engine.
EXPECT[(construct label)] = [(input, want), ...]  want in {"match", "nomatch"}.
The first input of each label is the one the probe already runs (its id is con.<label>); the counterpart is run as con.<label>.alt."""
EXPECT = {
    "literal": [("abc", "match"), ("abd", "nomatch")],
    "dot": [("abc", "match"), ("ac", "nomatch")],
    "dot_lf": [("a\nc", "nomatch"), ("abc", "match")],
    "dot_cr": [("a\rc", "match"), ("a\r\rc", "nomatch")],
    "dot_u2028": [("a" + chr(0x2028) + "c", "match"), ("a" + chr(0x2028) * 2 + "c", "nomatch")],
    "dot_astral": [("a\U0001F600c", "match"), ("a\U0001F600\U0001F600c", "nomatch")],
    "class": [("abc", "match"), ("abd", "nomatch")],
    "class_dash_end": [("a-", "match"), ("ab", "nomatch")],
    "class_escaped_dash": [("a-z", "match"), ("a-y", "nomatch")],
    "alternation": [("b", "match"), ("ab", "nomatch")],
    "repeat_exact": [("aaa", "match"), ("aa", "nomatch")],
    "repeat_range": [("aaaa", "nomatch"), ("a", "nomatch")],
    "repeat_open": [("aaa", "match"), ("a", "nomatch")],
    "optional": [("a", "match"), ("abb", "nomatch")],
    "star": [("", "match"), ("b", "nomatch")],
    "escape_dot": [("a.c", "match"), ("abc", "nomatch")],
    "escape_backslash": [("a\\c", "match"), ("ac", "nomatch")],
    "anchors_outer": [("abc", "match"), ("abcd", "nomatch")],
    "anchor_escaped_dollar": [("a$", "match"), ("a", "nomatch")],
    "dollar_before_lf": [("ab\n", "nomatch"), ("ab", "match")],
    "class_with_bracket": [("]", "match"), ("a", "nomatch")],
    "class_single_amp": [("&", "match"), ("a&", "nomatch")],
    "class_single_tilde": [("~", "match"), ("~~", "nomatch")],
    "repeat_zero": [("", "match"), ("a", "nomatch")],
}
