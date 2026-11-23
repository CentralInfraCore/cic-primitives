"""Self-test of check_reader_contract.py: can it FAIL, and for the right reason? Typed exits; infrastructure is never a detection.
A: the package as it is (exit 0). B: planted defects of the REFERENCE READING (CIC_READER_PLANT), each counted only when the check exits 1 AND prints a FAIL-EXPECT line for the vectors that state the rule.
C: planted faults in COPIES of the contract, the vectors, the extension cases, the measurement and the document, each counted only with the intended FAIL-EXPECT line. D: an unreadable input exits 2.
Exit: 0 all as expected, 1 a mutant was not detected or a control failed, 2 the self-test itself could not run."""
import copy, json, os, shutil, subprocess, sys, tempfile
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "..", "design")
CONTRACT = os.path.join(D, "pattern-profile-reader", "reader-contract.yaml")
VECTORS = os.path.join(D, "pattern-profile-reader", "reader-vectors.yaml")
CASES = os.path.join(D, "pattern-profile-spec", "extension-cases.yaml")
DOC = os.path.join(HERE, "..", "..", "en", "GRAMMAR-PATTERN-READER-CONTRACT-DRAFT.md")
MEAS = os.path.join(HERE, "results", "pyyaml-measurement.json")
CHECK = os.path.join(HERE, "check_reader_contract.py")
bad = 0


def report(label, ok, extra=""):
    global bad
    print("%-112s %s %s" % (label, "OK" if ok else "FAIL", extra))
    bad += not ok


def run(args, plant=None):
    env = dict(os.environ); env.pop("CIC_READER_PLANT", None)
    if plant:
        env["CIC_READER_PLANT"] = plant
    r = subprocess.run([sys.executable, CHECK] + args, capture_output=True, text=True, env=env, timeout=600)
    return r.returncode, r.stdout + r.stderr


def sub(text, a, b):
    assert text.count(a) >= 1, a
    return text.replace(a, b, 1)


def main():
    vectors = yaml.safe_load(open(VECTORS, encoding="utf-8"))
    contract = yaml.safe_load(open(CONTRACT, encoding="utf-8")); cases = yaml.safe_load(open(CASES, encoding="utf-8"))
    doc = open(DOC, encoding="utf-8").read(); meas = json.load(open(MEAS, encoding="utf-8"))
    vid = lambda text, kind="scalar": next(v["id"] for v in vectors["vectors"] if v.get("text") == text and v["kind"] == kind)
    hid = lambda hx: next(v["id"] for v in vectors["vectors"] if v.get("hex") == hx)
    rc, o = run([])
    report("A positive control (the package as it is)", rc == 0 and "all expectations held" in o, "exit=%d" % rc)
    plants = [("yaml11-scalars", [vid("yes"), vid("010"), vid("1_000")], "the YAML 1.1 booleans, octal and underscore integers"),
              ("host-dict-keys", [vid("{1: a, true: b, 1.0: c, \"1\": d}", "doc"), vid("{0.0: a, -0.0: b}", "doc"), vid("{.nan: a, .nan: b}", "doc")], "duplicate keys by the host language's equality"),
              ("alias-ok", [vid("a: &x 1\n", "doc"), vid("a: &x 1\nb: *x\n", "doc")], "aliases and anchors accepted (an undefined alias stays an error)"),
              ("merge-ok", [vid("{<<: {b: 1}}", "doc")], "merge keys accepted"),
              ("any-tag", [vid("!local 1"), vid("!!set {a}")], "any tag accepted"),
              ("float-overflow-inf", [vid("1e999")], "an overflowing float read as an infinity"),
              ("bom-ok", [hid("efbbbf613a2031")], "a byte order mark accepted"),
              ("dup-ignore", [vid("{a: 1, a: 2}", "doc")], "a duplicate key ignored")]
    for plant, needles, what in plants:
        rc, o = run([], plant)
        lines = [l for l in o.splitlines() if l.startswith("FAIL-EXPECT")]
        report("B planted reading: %s" % what, rc == 1 and all(any(("reference.%s" % n) in l for l in lines) for n in needles), "exit=%d needles=%s" % (rc, needles))

    def mut_vec(f):
        d = copy.deepcopy(vectors); f(d["vectors"]); return d

    def find(vs, text, kind="scalar"):
        return next(v for v in vs if v.get("text") == text and v["kind"] == kind)

    def mut_con(f):
        d = copy.deepcopy(contract); f(d); return d

    def mut_cases(f):
        d = copy.deepcopy(cases); f(d["cases"]); return d

    faults = [
        ("a vector expects the YAML 1.1 reading of 010 (the int 8)", dict(vec=mut_vec(lambda vs: find(vs, "010")["expect"].update(node=["i", "8"]))), "reference.%s" % vid("010")),
        ("a vector with an unknown rule", dict(vec=mut_vec(lambda vs: find(vs, "010").__setitem__("rule", "RC-99"))), "vectors.rule.%s" % vid("010")),
        ("a vector whose error kind is not in the closed set", dict(vec=mut_vec(lambda vs: find(vs, "1e999").__setitem__("expect", {"error": "float_too_big"}))), "vectors.error-kind.%s" % vid("1e999")),
        ("a vector with two expectations", dict(vec=mut_vec(lambda vs: find(vs, "010")["expect"].update(error="yaml_syntax"))), "vectors.one-expectation.%s" % vid("010")),
        ("a malformed typed tree (a float with 15 hex digits)", dict(vec=mut_vec(lambda vs: find(vs, "1.0")["expect"].update(node=["f", "3ff000000000000"]))), "vectors.tree.%s" % vid("1.0")),
        ("every vector of the error kind float_overflow removed", dict(vec=mut_vec(lambda vs: [vs.remove(v) for v in list(vs) if v["expect"].get("error") == "float_overflow"])), "contract.kind.produced.float_overflow"),
        ("every vector of the rule RC-16 removed", dict(vec=mut_vec(lambda vs: [vs.remove(v) for v in list(vs) if v["rule"] == "RC-16"])), "contract.rule.has-vectors.RC-16"),
        ("a rule names an error kind that is not in the closed set", dict(con=mut_con(lambda d: d["rules"][0].__setitem__("kinds", ["encoding", "bogus"]))), "contract.rule.kinds.RC-01"),
        ("an open question that names an unknown rule", dict(con=mut_con(lambda d: d["open_questions"][0].__setitem__("rules", ["RC-77"]))), "contract.question.rules.OQ-1"),
        ("a rule with an unknown basis", dict(con=mut_con(lambda d: d["rules"][3].__setitem__("basis", "decided_by_me"))), "contract.rule.basis.RC-04"),
        ("an open question claims a vector that its alternative does not change (OQ-1 claims V-SC-001)", dict(con=mut_con(lambda d: next(q for q in d["open_questions"] if q["id"] == "OQ-1")["affected_vectors"].append("V-SC-001"))), "contract.question.effect.OQ-1"),
        ("an open question leaves out a vector that its alternative changes (OQ-2 omits one of four)", dict(con=mut_con(lambda d: next(q for q in d["open_questions"] if q["id"] == "OQ-2")["affected_vectors"].pop())), "contract.question.effect.OQ-2"),
        ("an open question without a switchable alternative claims vectors (OQ-3)", dict(con=mut_con(lambda d: next(q for q in d["open_questions"] if q["id"] == "OQ-3").__setitem__("affected_vectors", ["V-SC-001"]))), "contract.question.effect.OQ-3"),
        ("an open question names an alternative but no way to compute its effect (OQ-5 without alt_env)", dict(con=mut_con(lambda d: next(q for q in d["open_questions"] if q["id"] == "OQ-5").__setitem__("alt_env", None))), "contract.question.alt.OQ-5"),
        ("an open question that claims a vector that does not exist", dict(con=mut_con(lambda d: next(q for q in d["open_questions"] if q["id"] == "OQ-8")["affected_vectors"].append("V-NOPE-999"))), "contract.question.vectors-exist.OQ-8"),
        ("the decision table of the document edited by hand (OQ-4 changes 33 vectors)", dict(doc=sub(doc, "| 33: V-TG-001", "| 32: V-TG-001")), "doc.table.questions"),
        ("an accepted extension case that no longer agrees (E-PIN-29 expects no reader error)", dict(cases=mut_cases(lambda cs: next(c for c in cs if c["id"] == "E-PIN-29").__setitem__("expect", {"outcome": "refuse", "code": "pattern_profile_unknown", "at": None}))), "extension.E-PIN-29"),
        ("an accepted extension case with a reader error the reading does not give (E-PIN-28 expects duplicate_key)", dict(cases=mut_cases(lambda cs: next(c for c in cs if c["id"] == "E-PIN-28").__setitem__("expect", {"outcome": "reader_error", "kind": "duplicate_key"}))), "extension.E-PIN-28"),
        ("the rule table of the document edited by hand", dict(doc=sub(doc, "| RC-07 | owner_decision |", "| RC-07 | proposal |")), "doc.table.rules"),
        ("the coverage table of the document edited by hand", dict(doc=sub(doc, "| RC-16 | 3 | 0 | 0 |", "| RC-16 | 4 | 0 | 0 |")), "doc.table.coverage"),
        ("the open-question table of the document edited by hand", dict(doc=sub(doc, "| OQ-1 | RC-01 |", "| OQ-1 | RC-02 |")), "doc.table.questions"),
        ("the measurement table of the document edited by hand", dict(doc=sub(doc, "| agrees with the contract | %d |" % meas["counts"]["agrees"], "| agrees with the contract | %d |" % (meas["counts"]["agrees"] + 1))), "doc.table.measurement"),
        ("the measurement file no longer matches the document", dict(meas=dict(meas, counts=dict(meas["counts"], agrees=meas["counts"]["agrees"] + 1))), "doc.table.measurement"),
        ("the document without the rule table markers", dict(doc=doc.replace("<!-- BEGIN RULES TABLE -->", "")), "doc.markers.rules"),
        ("the document states another number of vectors", dict(doc=sub(doc, "270 draft vectors, written", "271 draft vectors, written")), "doc.count.vectors"),
    ]
    for name, files, needle in faults:
        d = tempfile.mkdtemp()
        try:
            args = []
            for key, flag in (("vec", "--vectors"), ("con", "--contract"), ("cases", "--cases"), ("doc", "--doc"), ("meas", "--measurement")):
                if key in files:
                    f = os.path.join(d, key + ".dat"); data = files[key]
                    open(f, "w", encoding="utf-8").write(data if isinstance(data, str) else (json.dumps(data) if key == "meas" else yaml.safe_dump(data, sort_keys=False, allow_unicode=True)))
                    args += [flag, f]
            rc, o = run(args)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        named = [l for l in o.splitlines() if l.startswith("FAIL-EXPECT") and needle in l]
        report("C planted: " + name, rc == 1 and bool(named), "exit=%d needle=%s" % (rc, needle))
    rc, o = run(["--vectors", "/nonexistent/vectors.yaml"])
    report("D infra: the vectors are unreadable (exit 2, not a detection)", rc == 2 and "INCOMPLETE" in o, "exit=%d" % rc)
    print("self-test: %s" % ("all as expected" if not bad else "%d problem(s)" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
