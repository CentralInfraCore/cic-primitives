"""Vectors of the candidate subset classifier (subset_check.py): what it must accept and what it must refuse, each refusal with the reason it must give.
The classifier is a measurement prototype; this shows that it can say no, for the right reason. Exit 0 when every vector is as expected."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subset_check as S
ACCEPT = [r"^[0-9a-f]{40}$", r"^vault:v1:.+$", r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$", r"abc", r"a.c", r"[a-c]+", r"[a-]+", r"[a\-z]+", r"(ab){1,3}", r"a|b", r"a{3}", r"a{2,3}", r"a{2,}",
          r"ab?", r"a*", r"a\.c", r"a\\c", r"^a\$$", r"^[A-Za-z0-9+/]{43}=$", r"^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$", r"^a$", r"a$", r"^a", r"\\$", r"a*a*a*", r"(a{30}){30}", r"(\.[0-9]+)?", r"(a|b)", r"(ab){2}", r"[a&b]", r"[&a]", r"[a&]", r"[~a]", r"[a\-\-b]", r"a{0}", r"a{0,3}", r"(a|aa){1,255}", r"(a?){30}a{30}"]
REFUSE = [(r"\d+", "escape \\d"), (r"\w", "escape \\w"), (r"\s", "escape \\s"), (r"\bab", "escape \\b"), (r"[^a]", "negated class"), (r"[[:alpha:]]", "POSIX class"), (r"\p{L}", "escape \\p"),
          (r"(?i)a", "group extension"), (r"(?:a)", "group extension"), (r"(?P<n>a)", "group extension"), (r"(?<n>a)", "group extension"), (r"a(?=b)", "group extension"), (r"(a)\1", "escape \\1"),
          (r"a*?", "lazy"), (r"a+?", "lazy"), (r"a{1,2}?", "lazy"), (r"a++", "lazy, possessive or stacked"), (r"a**", "lazy, possessive or stacked"), (r"a{2,1}", "out of order"),
          (r"a{,3}", "malformed repetition"), (r"a{", "malformed repetition"), (r"a{x}", "malformed repetition"), (r"\x41", "escape \\x"), (chr(92) + "u0041", "escape \\u"), (r"\n", "escape \\n"), (r"\t", "escape \\t"),
          (r"\101", "escape \\1"), (r"a$b", "unexpected metacharacter"), (r"a^b", "unexpected metacharacter"), (r"\Aab", "escape \\A"), (r"ab\z", "escape \\z"), (r"ab\Z", "escape \\Z"), (r"\Qa\E", "escape \\Q"),
          (r"[z-a]", "out of order"), (r"[]a]", "empty class"), (r"[a-z&&[^b]]", "class set operator"), (r"[a[b]", "'[' inside a class"), (r"é", "not ASCII printable"), (r"a" + "\n", "not ASCII printable"), (r"(a", "unbalanced"), (r"a)", "unexpected"),
          (r"*a", "unexpected metacharacter"), (r"", "empty pattern"), (r"a" * 257, "length limit"), (r"a{256}", "above the limit"), (r"((((( a)))))".replace(" ", ""), "nesting deeper"), (r"(a|aa)+", "unbounded quantifier on a group"), (r"(a+)+", "unbounded quantifier on a group"), (r"(a*)*", "unbounded quantifier on a group"), (r"(ab){2,}", "unbounded quantifier on a group"), (r"a*a*a*a*", "more than 3 unbounded"), (r"(a{40}){30}", "product of nested repeat counts"), (r"^^a", "unexpected metacharacter"), (r"a$$", "unexpected metacharacter"),
          (r"\\\x", "escape \\x"),
          (r"[a&&b]", "class set operator"), (r"[a--b]", "class set operator"), (r"[a~~b]", "class set operator"), (r"[+--]", "class set operator"), (r"[--]", "class set operator"), (r"[a-c&&c-e]", "class set operator"),
          (r"a{01}", "leading zero"), (r"a{1,02}", "leading zero"), (r"a{00}", "leading zero"), (r"a{0,03}", "leading zero"),
          (r"a|", "empty alternative"), (r"|a", "empty alternative"), (r"a||b", "empty alternative"), (r"(|a)", "empty alternative"), (r"(a|)", "empty alternative"), (r"()", "empty alternative"), (r"^$", "empty alternative"), (r"^|a$", "empty alternative")]
bad = 0
for p in ACCEPT:
    r = S.parse(p); ok = r.ok; bad += not ok
    print("%-8s %-60s %s" % ("ok" if ok else "WRONG", repr(p)[:60], "" if ok else "refused: " + r.reason))
for p, why in REFUSE:
    r = S.parse(p); ok = (not r.ok) and why in r.reason; bad += not ok
    print("%-8s %-60s %s" % ("ok" if ok else "WRONG", repr(p)[:60], ("refused: " + r.reason) if not r.ok else "ACCEPTED (must refuse: %s)" % why))
print("%d vectors, %d wrong" % (len(ACCEPT) + len(REFUSE), bad))
sys.exit(1 if bad else 0)
