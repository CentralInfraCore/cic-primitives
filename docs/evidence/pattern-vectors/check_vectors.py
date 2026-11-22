"""Structure and coverage of the pattern-profile vector file. An ISOLATED check, not a CI gate (the gate is on hold). Implements nothing of the profile.
Exit: 0 all expectations held, 1 a measured expectation failed (a FAIL-EXPECT line), 2 the file could not be read (infrastructure, never a result).
Checks: unique ids; every vector names requirements that exist; encodings are printable ASCII or {seq}; the verdict and the code of every vector come from the stated sets; an accepted expression has a PI;
every requirement has at least one vector (or is listed as not testable by vectors); every code has a vector that expects it; every limit has an accepting and a refusing vector; value vectors only
ask for the verdicts of the value rules; the matrix of requirements to vectors is printed."""
import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vectors_lib as V

fails = []


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
                else:
                    expect("expect.%s" % i, v.get("expect") == "accept")
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
