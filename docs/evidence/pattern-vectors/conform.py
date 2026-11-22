"""Conformance run of the pattern-profile vectors against the existing implementations. An ISOLATED measurement, not a CI gate (on hold). The expectations are in the vector file, authored by hand
from the specification; this script never writes or derives one. A disagreement is a finding about the vector, the text or the implementation and is logged, not corrected here.

Implementations: P  the prototype (pattern_codes.py + nfa_engine.py) for expressions, PI, values, and the schema rule written below from the text;
                 S  the second implementation written from the rule text (spec_classifier.py), for the expression verdicts;
                 G  Go regexp, R  Rust regex: the value verdicts (match / mismatch) of every value vector whose value they can be given, and "an accepted expression compiles" (rule D);
                 L  the LEGACY reading (Python re.search of the original expression): run with --legacy as a RED-initial, it must disagree where the legacy defect is.
Exit: 0 every implementation of the run agrees with every vector it was asked, 1 a DISAGREE line, 2 INCOMPLETE (infrastructure, never a result), 3 a failed canary of a native runner.
Usage: conform.py [--no-native] [--legacy]"""
import os, re, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
EVID = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(EVID, "pattern-limits-errors"))
sys.path.insert(0, os.path.join(EVID, "grammar-pattern-measurement"))
sys.path.insert(0, os.path.join(EVID, "pattern-engine-selection"))
import vectors_lib as V

EXIT_DISAGREE, EXIT_INFRA, EXIT_CANARY = 1, 2, 3
NO_NATIVE = "--no-native" in sys.argv
CPLANT = os.environ.get("CIC_CONFORM_PLANT", "")      # a planted defect of the schema rule, for the self-test only
LEGACY = "--legacy" in sys.argv
_argv = sys.argv; _tmp = tempfile.mkdtemp(); sys.argv = [_argv[0], _tmp]
try:
    import pattern_codes as C
    import spec_classifier as SP
    import nfa_engine as N
    import probe_engines as PE
except BaseException as e:
    print("INCOMPLETE: cannot import the implementations: %r" % (e,)); sys.exit(EXIT_INFRA)
finally:
    sys.argv = _argv; shutil.rmtree(_tmp, ignore_errors=True)

dis = []


def check(impl, vid, got, want, extra=""):
    if got != want:
        dis.append((impl, vid))
        print("DISAGREE %s %s got %s want %s %s" % (impl, vid, got, want, extra))


def p_expression(v):
    e = V.dec(v["expr"])
    code, _ = C.classify(e)
    got = "accept" if code == "" else "refuse:" + code
    want = "accept" if v["expect"] == "accept" else "refuse:" + v["code"]
    check("P", v["id"], got, want, "expr=%s" % V.show(v["expr"]))
    if C.S.parse(e).ok:                         # PI is defined for every expression that passed tiers 1 and 2
        pi = C.size(N.parse_ast(e))
        if "pi" in v:
            check("P.pi", v["id"], pi, v["pi"], "expr=%s" % V.show(v["expr"]))
    elif "pi" in v:
        check("P.pi", v["id"], "tier-1/2 refusal has no PI", v["pi"])


def s_expression(v):
    e = V.dec(v["expr"])
    got = SP.classify(e)
    want = "" if v["expect"] == "accept" else v["code"]
    check("S", v["id"], got or "accept", want or "accept", "expr=%s" % V.show(v["expr"]))


def p_value(v):
    e = V.dec(v["expr"]); val = V.dec(v["value"])
    code, _ = C.classify(e)
    if code:
        check("P", v["id"], "expression refused: " + code, "accepted expression", "expr=%s" % V.show(v["expr"])); return
    check("P", v["id"], C.check_value(e, val), v["expect"], "expr=%s value=%s" % (V.show(v["expr"]), V.show(v["value"])))


def schema_verdict(sc):
    """The schema rule, written from the text of limits doc 3.2 (the pin errors first, then the first refused expression in document order). No other implementation of it exists."""
    cons = sc.get("contracts", [])
    if CPLANT == "pin-after-expressions":
        for i, c in enumerate(cons, 1):
            code, _ = C.classify(V.dec(c["expr"]))
            if code:
                return "refuse", code, i
    if cons:
        st = sc["pin"]["state"]
        if st == "missing":
            return "refuse", "pattern_profile_missing", None
        if st == "unknown":
            return "refuse", "pattern_profile_unknown", None
        if st == "conflict" and len(set(sc["pin"]["versions"])) > 1:
            return "refuse", "pattern_profile_conflict", None
    order = list(enumerate(cons, 1))
    if CPLANT == "last-refused":
        order.reverse()
    for i, c in order:
        code, _ = C.classify(V.dec(c["expr"]))
        if code:
            return "refuse", code, i
    return "accept", None, None


def p_schema(sc):
    verdict, code, at = schema_verdict(sc)
    want = (sc["expect"], sc.get("code"), sc.get("at"))
    check("P.schema", sc["id"], (verdict, code, at), want)          # the whole triple, nothing masked (review F1 of #49)


def legacy(v):
    """Python re.search of the ORIGINAL expression: what the jsonschema library does today"""
    e = V.dec(v["expr"]); val = V.dec(v["value"])
    if v["expect"] not in ("match", "pattern_value_mismatch"):
        return None
    try:
        got = "match" if re.search(e, val) else "pattern_value_mismatch"
    except re.error:
        got = "compile_error"
    return got


def native(values, exprs):
    import json
    cases = []
    for v in values:
        val = V.dec(v["value"])
        if v["expect"] not in ("match", "pattern_value_mismatch"):
            continue
        try:
            val.encode("utf-8")
        except UnicodeEncodeError:
            continue
        cases.append({"id": v["id"], "p": V.dec(v["expr"]), "input": val})
    for v in exprs:
        e = V.dec(v["expr"])
        if v["expect"] == "accept" and v.get("pi", 10 ** 9) <= 2048 and len(e) <= 256:
            cases.append({"id": "compile." + v["id"], "p": e, "input": ""})
    res = {}
    for kind in ("go", "rust"):
        try:
            res[kind] = PE.ext_run(kind, cases, tempfile.mkdtemp())
        except SystemExit as e:
            msg = str(e.code)
            print("%s: %s" % ("CANARY" if "CANARY" in msg else "INCOMPLETE", msg)); sys.exit(EXIT_CANARY if "CANARY" in msg else EXIT_INFRA)
        if res[kind] is None:
            print("INCOMPLETE: the %s toolchain is not available" % kind); sys.exit(EXIT_INFRA)
    byid = {v["id"]: v for v in values}
    n = 0
    for kind, tag in (("go", "G"), ("rust", "R")):
        for c in cases:
            verdict = res[kind][c["id"]][0]
            if c["id"].startswith("compile."):
                check(tag, c["id"], "compiles" if verdict != "compile_error" else "compile_error", "compiles", "rule D: an accepted expression must compile everywhere")
            else:
                want = "match" if byid[c["id"]]["expect"] == "match" else "nomatch"
                check(tag, c["id"], verdict, want, "expr=%s value=%s" % (V.show(byid[c["id"]]["expr"]), V.show(byid[c["id"]]["value"])))
            n += 1
    return len(cases)


def main():
    try:
        d = V.load()
    except BaseException as e:
        print("INCOMPLETE: the vector file cannot be read: %r" % (e,)); return EXIT_INFRA
    ex, va, sc = d["expressions"], d["values"], d["schemas"]
    lim = d.get("limits", {})                     # the declared limits against the constants of the implementation (review F2 of #49)
    for k, got in (("length", C.S.LIMITS["length"]), ("repeat_count", C.S.LIMITS["repeat"]), ("group_depth", C.S.LIMITS["depth"]), ("repeat_product", C.S.LIMITS["repeat_product"]),
                   ("unbounded_quantifiers", C.S.LIMITS["unbounded"]), ("pi_max", C.PI_MAX), ("value_code_points", C.VALUE_MAX)):
        check("P.meta", "limits." + k, lim.get(k), got)
    if LEGACY:
        n = bad = 0; lf_red = False
        for v in va:
            g = legacy(v)
            if g is None:
                continue
            n += 1
            if g != v["expect"]:
                bad += 1
                lf_red = lf_red or "R-MATCH-NO-TRAILING-LF" in v["req"]
                print("DISAGREE L %s legacy re.search says %s, the vector says %s  expr=%s value=%s" % (v["id"], g, v["expect"], V.show(v["expr"]), V.show(v["value"])))
        print("legacy reading (re.search of the original expression): %d match/mismatch vectors, %d disagree" % (n, bad))
        if lf_red:
            print("RED shown: the vectors distinguish the legacy reading (a trailing line feed is accepted by re.search and refused by the profile)"); return 0
        print("NOT RED: no vector tagged R-MATCH-NO-TRAILING-LF separates the legacy reading"); return EXIT_DISAGREE
    for v in ex:
        p_expression(v); s_expression(v)
    for v in va:
        p_value(v)
    for s in sc:
        p_schema(s)
    nn = 0 if NO_NATIVE else native(va, ex)
    print("checked: %d expression vectors (P, S; PI), %d value vectors (P), %d schema vectors (P.schema), %d native cases (G, R)%s" % (len(ex), len(va), len(sc), nn, " [native skipped]" if NO_NATIVE else ""))
    if dis:
        print("FAILED: %d disagreement(s): %s" % (len(dis), ", ".join("%s %s" % x for x in dis[:12])))
        return EXIT_DISAGREE
    print("all implementations agree with all vectors"); return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(EXIT_INFRA)
