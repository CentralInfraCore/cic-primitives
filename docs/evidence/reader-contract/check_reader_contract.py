"""Consistency check of the DRAFT reader contract (OP-1): the rules, the draft vectors, the reference reading, the 47 accepted extension cases and the review document. An ISOLATED check, not a CI gate; it changes nothing.
Checks (a failure is a FAIL-EXPECT line, exit 1; an unreadable input is INCOMPLETE, exit 2, never a result):
  contract    rule ids unique; every error kind a rule names is in the closed set; every error kind of the contract (except the schema-layer one) is produced by at least one negative vector; every rule has at least one
              vector, except the two meta rules (boundary, independence)
  vectors     ids unique; each names an existing rule; exactly one expectation; error kinds in the closed set; the typed tree is well-formed (types, 16 hex digits for a float, decimal text for an int); modes known
  reference   the reference reading of the RULES (reference_reader.py, which takes only the syntax from PyYAML) gives the expected result of every vector: 0 differences
  extension   the 47 accepted extension cases agree with the contract at the READER level: a case whose expected result is a reader error of the scalar reader (yaml_syntax, duplicate_key, non_scalar_key,
              non_string_key) is refused by the reference reading with that kind, in the pin text (plain mode) or in the schema document (schema mode); every other case is read without a reader error
  doc         the rule table, the coverage matrix, the open-question table and the measurement table of the review document are exactly the tables rendered from the data (nothing is hand-edited into them)
Usage: check_reader_contract.py [--render] [--contract PATH] [--vectors PATH] [--cases PATH] [--doc PATH] [--measurement PATH]"""
import collections, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
D = os.path.join(HERE, "..", "..", "design")
CONTRACT = os.path.join(D, "pattern-profile-reader", "reader-contract.yaml")
VECTORS = os.path.join(D, "pattern-profile-reader", "reader-vectors.yaml")
CASES = os.path.join(D, "pattern-profile-spec", "extension-cases.yaml")
DOC = os.path.join(HERE, "..", "..", "en", "GRAMMAR-PATTERN-READER-CONTRACT-DRAFT.md")
MEAS = os.path.join(HERE, "results", "pyyaml-measurement.json")
MARK = {"rules": ("<!-- BEGIN RULES TABLE -->", "<!-- END RULES TABLE -->"), "coverage": ("<!-- BEGIN COVERAGE TABLE -->", "<!-- END COVERAGE TABLE -->"),
        "questions": ("<!-- BEGIN QUESTIONS TABLE -->", "<!-- END QUESTIONS TABLE -->"), "measurement": ("<!-- BEGIN MEASUREMENT TABLE -->", "<!-- END MEASUREMENT TABLE -->")}
META = {"RC-18", "RC-19"}
SCALAR_READER_KINDS = {"yaml_syntax", "duplicate_key", "non_scalar_key", "non_string_key"}
fails = []


def expect(label, cond, detail=""):
    if not cond:
        fails.append(label); print("FAIL-EXPECT %s %s" % (label, detail))


def arg(argv, name, default):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else default


def flat(s):
    return " ".join(str(s).split())


def well_formed(t):
    if not isinstance(t, list) or not t: return False
    k = t[0]
    if k == "n": return len(t) == 1
    if k == "b": return len(t) == 2 and isinstance(t[1], bool)
    if k == "i": return len(t) == 2 and isinstance(t[1], str) and re.fullmatch(r"-?[0-9]+", t[1]) is not None
    if k == "f": return len(t) == 2 and isinstance(t[1], str) and re.fullmatch(r"[0-9a-f]{16}", t[1]) is not None
    if k == "s": return len(t) == 2 and isinstance(t[1], str)
    if k == "seq": return len(t) == 2 and isinstance(t[1], list) and all(well_formed(x) for x in t[1])
    if k == "map": return len(t) == 2 and isinstance(t[1], list) and all(isinstance(e, list) and len(e) == 2 and well_formed(e[0]) and well_formed(e[1]) for e in t[1])
    return False


def coverage(vectors, rules):
    cov = {r["id"]: collections.Counter() for r in rules}
    ids = collections.defaultdict(list)
    for v in vectors:
        if v.get("rule") in cov:
            cov[v["rule"]][v.get("class")] += 1; ids[v["rule"]].append(v["id"])
    return cov, ids


def render(contract, vectors, meas):
    rules = contract["rules"]
    rt = ["| Rule | Basis | Topic | Rule text | Error kinds |", "|---|---|---|---|---|"]
    for r in rules:
        rt.append("| %s | %s | %s | %s | %s |" % (r["id"], r["basis"], r["topic"], flat(r["text"]).replace("|", "/"), ", ".join("`%s`" % k for k in r["kinds"]) or "none"))
    cov, ids = coverage(vectors, rules)
    ct = ["| Rule | Positive | Negative | Boundary | Vectors |", "|---|---|---|---|---|"]
    for r in rules:
        c = cov[r["id"]]; n = sum(c.values())
        ct.append("| %s | %d | %d | %d | %s |" % (r["id"], c["positive"], c["negative"], c["boundary"], ("%d (%s .. %s)" % (n, ids[r["id"]][0], ids[r["id"]][-1])) if n else "none (a meta rule)"))
    qt = ["| Question | Rules | Question text | Draft answer |", "|---|---|---|---|"]
    for q in contract["open_questions"]:
        qt.append("| %s | %s | %s | %s |" % (q["id"], ", ".join(q["rules"]), flat(q["question"]).replace("|", "/"), q["draft"]))
    c = meas["counts"]
    mt = ["| PyYAML %s over %d draft vectors | Vectors |" % (meas["pyyaml_version"], meas["vectors"]), "|---|---|"]
    for k, label in (("agrees", "agrees with the contract"), ("differs_in_value", "reads a value that differs from the contract"), ("accepts_what_the_contract_rejects", "accepts a document the contract rejects"), ("rejects_what_the_contract_reads", "rejects a document the contract reads")):
        mt.append("| %s | %d |" % (label, c[k]))
    return {"rules": "\n".join(rt), "coverage": "\n".join(ct), "questions": "\n".join(qt), "measurement": "\n".join(mt)}


def data_of(v):
    return bytes.fromhex(v["hex"]) if v["kind"] == "bytes" else (("- " + v["text"] + "\n") if v["kind"] == "scalar" else v["text"])


def main(argv):
    import yaml
    try:
        contract = yaml.safe_load(open(arg(argv, "--contract", CONTRACT), encoding="utf-8"))
        vectors = yaml.safe_load(open(arg(argv, "--vectors", VECTORS), encoding="utf-8"))["vectors"]
        cases = yaml.safe_load(open(arg(argv, "--cases", CASES), encoding="utf-8"))["cases"]
        meas = json.load(open(arg(argv, "--measurement", MEAS), encoding="utf-8"))
        doc = open(arg(argv, "--doc", DOC), encoding="utf-8").read() if "--render" not in argv else ""
        import reference_reader as R
        tables = render(contract, vectors, meas)
    except BaseException as e:
        print("INCOMPLETE: an input cannot be read: %r" % (e,)); return 2
    if "--render" in argv:
        for k, v in tables.items():
            print("## %s\n%s\n" % (k, v))
        return 0
    rules = contract["rules"]; rids = [r["id"] for r in rules]; kinds = {k["kind"] for k in contract["error_kinds"]}
    expect("contract.rule-ids.unique", len(rids) == len(set(rids)))
    for r in rules:
        expect("contract.rule.kinds.%s" % r["id"], set(r["kinds"]) <= kinds, "unknown error kinds %s" % sorted(set(r["kinds"]) - kinds))
        expect("contract.rule.basis.%s" % r["id"], r["basis"] in ("owner_decision", "review_recommendation", "proposal"), "basis %r" % r["basis"])
    for q in contract["open_questions"]:
        expect("contract.question.rules.%s" % q["id"], set(q["rules"]) <= set(rids), "unknown rules")
    vids = [v["id"] for v in vectors]
    expect("vectors.ids.unique", len(vids) == len(set(vids)))
    cov, _ = coverage(vectors, rules)
    for r in rules:
        if r["id"] not in META:
            expect("contract.rule.has-vectors.%s" % r["id"], sum(cov[r["id"]].values()) > 0, "no vector states this rule")
    produced = collections.Counter()
    for v in vectors:
        i = v["id"]
        expect("vectors.rule.%s" % i, v.get("rule") in rids, "unknown rule %r" % v.get("rule"))
        expect("vectors.class.%s" % i, v.get("class") in ("positive", "negative", "boundary"))
        expect("vectors.kind.%s" % i, v.get("kind") in ("scalar", "doc", "bytes") and ((v.get("kind") == "bytes") == ("hex" in v)) and (v.get("kind") == "bytes" or "text" in v))
        expect("vectors.mode.%s" % i, v.get("mode", "plain") in ("plain", "schema"))
        e = v.get("expect") or {}
        expect("vectors.one-expectation.%s" % i, len(e) == 1 and set(e) <= {"node", "tree", "error"}, "expect %s" % list(e))
        if "error" in e:
            expect("vectors.error-kind.%s" % i, e["error"] in kinds, "unknown kind %r" % e["error"])
            produced[e["error"]] += 1
            rk = next((r["kinds"] for r in rules if r["id"] == v.get("rule")), [])
        for key in ("node", "tree"):
            if key in e:
                expect("vectors.tree.%s" % i, well_formed(e[key]), "the typed tree is malformed")
    for k in contract["error_kinds"]:
        if k["kind"] != "expression_not_a_string":
            expect("contract.kind.produced.%s" % k["kind"], produced[k["kind"]] > 0, "no negative vector produces this error kind")
    for r in rules:                                            # every kind a rule names is produced by a vector of THAT rule
        for k in r["kinds"]:
            expect("contract.rule-kind.vector.%s.%s" % (r["id"], k), any(v.get("rule") == r["id"] and (v.get("expect") or {}).get("error") == k for v in vectors), "no vector of this rule states this kind")
    # the reference reading
    diffs = 0
    for v in vectors:
        try:
            got, gk = R.read(data_of(v), v.get("mode", "plain")), None
        except R.ReaderError as ex:
            got, gk = None, ex.kind
        except BaseException as ex:
            print("INCOMPLETE: the reference reading raised %r on %s" % (ex, v["id"])); return 2
        e = v.get("expect") or {}
        if "error" in e: ok = gk == e["error"]
        elif "node" in e: ok = gk is None and got[0] == "seq" and len(got[1]) == 1 and got[1][0] == e["node"]
        else: ok = gk is None and got == e.get("tree")
        if not ok:
            diffs += 1
        expect("reference.%s" % v["id"], ok, "expected %s, the reference reading gives %s" % (e, gk if gk else got))
    # the 47 accepted extension cases at the reader level
    for c in cases:
        ex = c["expect"]
        want = ex.get("kind") if ex.get("outcome") == "reader_error" and ex.get("kind") in SCALAR_READER_KINDS else None
        got = None
        for text, mode in ((c["schema"], "schema"), (c.get("pin_text"), "plain")):
            if text is None: continue
            k = R.error_kind(text, mode)
            if k and got is None: got = k
        expect("extension.%s" % c["id"], got == want, "the case expects the reader result %r, the contract's reference reading gives %r" % (want, got))
    # the document
    for k, (b, e) in MARK.items():
        if b in doc and e in doc:
            expect("doc.table.%s" % k, doc.split(b, 1)[1].split(e, 1)[0].strip() == tables[k].strip(), "the %s table of the document differs from the table rendered from the data" % k)
        else:
            expect("doc.markers.%s" % k, False, "the document has no %s table markers" % k)
    if doc:
        expect("doc.count.vectors", ("\n%d draft vectors, written" % len(vectors)) in doc and ("(0 differences)" in doc), "the document does not state the number of draft vectors (%d) and 0 differences" % len(vectors))
        expect("doc.count.extension", "the 47 accepted extension cases" in doc and len(cases) == 47, "the document names 47 accepted extension cases, the case file has %d" % len(cases))
    cls = collections.Counter(v["class"] for v in vectors)
    print("rules %d (basis: %s); vectors %d (%s); reference differences %d; extension cases checked %d; open questions %d" % (
        len(rules), ", ".join("%s %d" % kv for kv in sorted(collections.Counter(r["basis"] for r in rules).items())), len(vectors), ", ".join("%s %d" % kv for kv in sorted(cls.items())), diffs, len(cases), len(contract["open_questions"])))
    if fails:
        print("FAILED: %d expectation(s)" % len(fails)); return 1
    print("all expectations held"); return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
