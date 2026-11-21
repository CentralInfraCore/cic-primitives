"""RED-initial evidence for review F3.1 and F4: the same cases are run against the PREVIOUS version of subset_check.py and compat_records.py (head 7b16e34, given as a directory)
and against the current ones. The previous version must show the defect (a case that has to be refused is accepted), the current one must not.
Usage (from the repository root): red_initial_f31_f4.py <directory with the previous subset_check.py and compat_records.py>. Exit 0 if the previous version shows every defect and the
current one none; exit 1 otherwise."""
import importlib.util, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); OLD = os.path.abspath(sys.argv[1])
def load(name, d):
    sys.path.insert(0, d); sys.argv = [sys.argv[0]]
    spec = importlib.util.spec_from_file_location(name, os.path.join(d, name.split("@")[0] + ".py")); m = importlib.util.module_from_spec(spec)
    sys.modules.pop("subset_check", None); spec.loader.exec_module(m); sys.path.pop(0); return m
old_s = load("subset_check@old", OLD); old_c = load("compat_records@old", OLD)
new_s = load("subset_check@new", HERE); new_c = load("compat_records@new", HERE)
bad = 0
print("F4: resource limits before and during the parse        previous                      current")
for label, p, want in [("whole text 257 with anchors (body 255)", "^" + "a" * 255 + "$", "length limit"), ("300 chars, also unbalanced: length decides first", "a" * 300 + "(", "length limit"),
                       ("10 deep, also unbalanced: depth decides first", "(" * 10 + "a", "nesting deeper"), ("a{256}(: the count decides before the parse ends", "a{256}(", "above the limit")]:
    o, n = old_s.parse(p), new_s.parse(p)
    red = (o.ok or want not in o.reason); green = (not n.ok and want in n.reason)
    print("  %-52s %-30s %s   %s" % (label, "ACCEPT" if o.ok else "REFUSE: " + o.reason[:20], ("REFUSE: " + n.reason[:24]) if not n.ok else "ACCEPT", "RED/GREEN as required" if red and green else "UNEXPECTED"))
    bad += not (red and green)
print("F3.1: element-level completeness (INCOMPLETE = refused)   previous                      current")
pat = [{"type": "pattern", "expression": "^[a-z]{1,3}$"}]
leaf = lambda mand=True, nullable=False: {"name": "d", "mandatory": mand, "nullable": nullable, "contract": pat}
node = [{"name": "items", "mandatory": True, "item_fields": [leaf()]}]
base = [{"d": c * 2} for c in "abcdefghi"]
def refused(fn):
    try:
        fn(); return False
    except SystemExit as e:
        return str(e).startswith("INCOMPLETE")
for label, rec in [("one element lacks the mandatory key (the review's case)", {"items": base + [{"path": "example.yaml"}]}), ("one element has a null where null is not allowed", {"items": base + [{"d": None}]}),
                   ("one element has an integer", {"items": base + [{"d": 7}]}), ("one element has a list", {"items": base + [{"d": ["x"]}]})]:
    ro = old_c.measure("t", rec, node); rn = new_c.measure("t", rec, node)
    o_ref = refused(lambda: old_c.check_complete("t", ro[1], ro[5], ro[6])); n_ref = refused(lambda: new_c.check_complete("t", rn[1], rn[5], rn[6]))
    print("  %-52s %-30s %s   %s" % (label, "refused" if o_ref else "ACCEPTED (the defect)", "refused" if n_ref else "ACCEPTED", "RED/GREEN as required" if (not o_ref and n_ref) else "UNEXPECTED"))
    bad += not (not o_ref and n_ref)
sys.exit(1 if bad else 0)
