"""Structure and coverage of the pattern-profile vector file. An ISOLATED check, not a CI gate (the gate is on hold). Implements nothing of the profile.
Exit: 0 all expectations held, 1 a measured expectation failed (a FAIL-EXPECT line), 2 the file could not be read (infrastructure, never a result).
Checks: unique ids; every vector names requirements that exist; encodings are printable ASCII or {seq}; the verdict and the code of every vector come from the stated sets; an accepted expression has a PI;
every requirement has at least one vector (or is listed as not testable by vectors); every code has a vector that expects it; every limit has an accepting and a refusing vector; value vectors only
ask for the verdicts of the value rules; the matrix of requirements to vectors is printed."""
import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vectors_lib as V

fails = []

# The accepted decisions (O2 of #48 and the limits of #46), written here independently of the vector file: the file's own metadata is checked AGAINST them (review F2 of #49).
DECIDED_LIMITS = {"length": 256, "repeat_count": 255, "group_depth": 4, "repeat_product": 1000, "unbounded_quantifiers": 3, "pi_max": 2048, "value_code_points": 256}
DECIDED_CODES = {
    "expression": {"pattern_empty", "pattern_too_long", "pattern_not_ascii_printable", "pattern_empty_branch", "pattern_unbalanced_group", "pattern_group_extension", "pattern_escape_unsupported",
                   "pattern_metachar_unexpected", "pattern_anchor_misplaced", "pattern_class_empty", "pattern_class_negated", "pattern_class_unterminated", "pattern_class_range_order",
                   "pattern_class_nested_or_posix", "pattern_class_set_operator", "pattern_quantifier_malformed", "pattern_quantifier_leading_zero", "pattern_quantifier_bounds_order",
                   "pattern_quantifier_not_greedy", "pattern_nesting_too_deep", "pattern_repeat_count_too_large", "pattern_repeat_product_too_large", "pattern_unbounded_too_many",
                   "pattern_unbounded_on_group", "pattern_program_too_large"},
    "value": {"pattern_value_not_unicode_scalar", "pattern_value_too_long", "pattern_value_mismatch"},
    "pin": {"pattern_profile_missing", "pattern_profile_unknown", "pattern_profile_conflict"},
}


def expect(label, cond, detail=""):
    if not cond:
        fails.append(label); print("FAIL-EXPECT %s %s" % (label, detail))


def printable(s):
    return all(0x20 <= ord(c) <= 0x7E for c in s)


def enc_ok(x):
    if isinstance(x, str):
        return printable(x)
    if isinstance(x, dict) and set(x) == {"seq"} and isinstance(x["seq"], list):
        for e in x["seq"]:
            if isinstance(e, str):
                if not printable(e):
                    return False
            elif not (isinstance(e, list) and len(e) == 2 and isinstance(e[0], int) and isinstance(e[1], int) and 0 <= e[0] <= 0x10FFFF and e[1] >= 1):
                return False
        return True
    return False


def main(path=None):
    try:
        d = V.load(path)
    except BaseException as e:
        print("INCOMPLETE: the vector file cannot be read: %r" % (e,)); return 2
    if d.get("vectors_format") != 1:
        print("INCOMPLETE: unknown vectors_format"); return 2
    req = {r["id"]: r for r in d["requirements"]}
    nt = {r["id"] for r in d.get("not_testable_by_vectors", [])}
    expr_codes, value_codes, pin_codes = d["codes"]["expression"], d["codes"]["value"], d["codes"]["pin"]
    kinds = (("expressions", "X"), ("values", "V"), ("schemas", "S"))
    seen = {}; byreq = collections.defaultdict(list); bycode = collections.defaultdict(list)
    for k, pre in kinds:
        for v in d[k]:
            i = v.get("id", "?")
            expect("id.unique.%s" % i, i not in seen, "duplicate id")
            seen[i] = k
            expect("id.prefix.%s" % i, str(i).startswith(pre + "-"), "a vector of kind %s must start with %s-" % (k, pre))
            rs = v.get("req") or []
            expect("req.present.%s" % i, bool(rs), "no requirement named")
            for r in rs:
                expect("req.known.%s.%s" % (i, r), r in req, "unknown requirement")
                byreq[r].append(i)
            if k == "expressions":
                expect("enc.%s" % i, enc_ok(v.get("expr")), "the expression is not printable ASCII / {seq}")
                if v.get("expect") == "accept":
                    expect("pi.present.%s" % i, isinstance(v.get("pi"), int), "an accepted expression needs its PI")
                    expect("code.absent.%s" % i, "code" not in v)
                else:
                    expect("expect.%s" % i, v.get("expect") == "refuse", "expect must be accept or refuse")
                    expect("code.known.%s" % i, v.get("code") in expr_codes, "the code %r is not an expression code" % v.get("code"))
                    bycode[v.get("code")].append(i)
            elif k == "values":
                expect("enc.expr.%s" % i, enc_ok(v.get("expr")))
                expect("enc.value.%s" % i, enc_ok(v.get("value")), "the value is not printable ASCII / {seq}")
                expect("expect.%s" % i, v.get("expect") == "match" or v.get("expect") in value_codes, "expect %r is neither match nor a value code" % v.get("expect"))
                bycode[v.get("expect")].append(i)
            else:
                expect("pin.%s" % i, isinstance(v.get("pin"), dict) and v["pin"].get("state") in ("ok", "missing", "unknown", "conflict"))
                for c in v.get("contracts", []):
                    expect("enc.contract.%s" % i, enc_ok(c.get("expr")) and "path" in c)
                if v.get("expect") == "refuse":
                    expect("code.known.%s" % i, v.get("code") in expr_codes + pin_codes, "the code %r is not known" % v.get("code"))
                    bycode[v.get("code")].append(i)
                    n = len(v.get("contracts", []))
                    if v.get("code") in pin_codes:     # a pin error is about the schema, not about one expression: no position
                        expect("schema.at.forbidden.%s" % i, "at" not in v, "a pin refusal must not carry a position")
                    else:                              # an expression refusal names the position of the refused contract in document order
                        expect("schema.at.required.%s" % i, isinstance(v.get("at"), int) and 1 <= v["at"] <= n, "an expression refusal needs `at`, 1..%d, got %r" % (n, v.get("at")))
                else:
                    expect("expect.%s" % i, v.get("expect") == "accept")
                    expect("schema.at.forbidden.%s" % i, "at" not in v, "an accepted schema has no position")
    # ---- the normative metadata against the accepted decisions, and against the vectors' own boundaries (review F2 of #49)
    expect("meta.profile.name", d.get("profile", {}).get("name") == "pattern", "profile.name is %r" % (d.get("profile", {}).get("name"),))
    ver = d.get("profile", {}).get("version")
    expect("meta.profile.version", isinstance(ver, int) and ver >= 1, "profile.version must be a positive integer (a working assumption until the pin decision)")
    lim = d.get("limits", {})
    expect("meta.limits.keys", set(lim) == set(DECIDED_LIMITS), "limits keys %s" % sorted(lim))
    for k, want in DECIDED_LIMITS.items():
        expect("meta.limits.%s" % k, lim.get(k) == want, "declared %r, decided %r" % (lim.get(k), want))
    for k in ("expression", "value", "pin"):
        expect("meta.codes.%s" % k, set(d["codes"].get(k, [])) == DECIDED_CODES[k] and len(d["codes"].get(k, [])) == len(DECIDED_CODES[k]),
               "the %s codes differ from the decided set (missing %s, extra %s)" % (k, sorted(DECIDED_CODES[k] - set(d["codes"].get(k, []))), sorted(set(d["codes"].get(k, [])) - DECIDED_CODES[k])))
    xs = d["expressions"]
    expect("meta.boundary.pi_max", any(x.get("pi") == lim.get("pi_max") and x["expect"] == "accept" for x in xs) and any(x.get("pi") == (lim.get("pi_max") or 0) + 1 and x["expect"] == "refuse" for x in xs),
           "the declared pi_max %r has no accepted vector with PI = pi_max and no refused vector with PI = pi_max + 1" % lim.get("pi_max"))
    lens = [(len(V.dec(x["expr"])), x["expect"]) for x in xs if x["id"].startswith("X-T")]
    expect("meta.boundary.length", (lim.get("length"), "accept") in lens and ((lim.get("length") or 0) + 1, "refuse") in lens, "no vector at length = limit accepted and length = limit + 1 refused")
    vl = [(len(V.dec(x["value"])), x["expect"]) for x in d["values"] if x["id"].startswith("V-L")]
    expect("meta.boundary.value_code_points", (lim.get("value_code_points"), "match") in vl and ((lim.get("value_code_points") or 0) + 1, "pattern_value_too_long") in vl, "no value vector at the value limit matching and at limit + 1 too long")
    sc_ok = [x["pin"].get("version") for x in d["schemas"] if x["pin"].get("state") == "ok"]
    expect("meta.pin.known-version", bool(sc_ok) and set(sc_ok) == {ver}, "the schema vectors with a known pin use version %s, the profile says %r" % (sorted(set(sc_ok)), ver))
    expect("meta.pin.unknown-differs", all(x["pin"].get("version") != ver for x in d["schemas"] if x["pin"].get("state") == "unknown"), "an `unknown` pin vector uses the known version")
    for r in req:
        expect("coverage.requirement.%s" % r, r in byreq, "no vector exercises this requirement")
    for r in nt:
        expect("notestable.%s" % r, r not in byreq, "listed as not testable by vectors but a vector names it")
    for c in expr_codes + value_codes + pin_codes:
        expect("coverage.code.%s" % c, c in bycode, "no vector expects this code")
    by_id = {v["id"]: v for k, _ in kinds for v in d[k]}
    for r in req:
        if r.startswith("R-LIM-"):
            ids = byreq.get(r, [])
            acc = [i for i in ids if by_id[i].get("expect") in ("accept", "match")]
            ref = [i for i in ids if by_id[i].get("expect") not in ("accept", "match")]
            expect("boundary.%s" % r, bool(acc) and bool(ref), "a limit needs an accepting and a refusing vector (%d / %d)" % (len(acc), len(ref)))
    print("vectors: %d expressions, %d values, %d schemas; %d requirements (%d not testable by vectors); %d codes" % (len(d["expressions"]), len(d["values"]), len(d["schemas"]), len(req), len(nt), len(expr_codes) + len(value_codes) + len(pin_codes)))
    print("## requirement -> vectors")
    for r in req:
        ids = byreq.get(r, [])
        print("%-26s %3d  %s" % (r, len(ids), " ".join(ids[:6]) + (" ..." if len(ids) > 6 else "")))
    for r in d.get("not_testable_by_vectors", []):
        print("%-26s  --  not testable by a verdict vector: %s" % (r["id"], r["where"]))
    print("## code -> vectors")
    for c in expr_codes + value_codes + pin_codes:
        print("%-38s %3d" % (c, len(bycode.get(c, []))))
    if fails:
        print("FAILED: %d expectation(s)" % len(fails)); return 1
    print("all expectations held"); return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
