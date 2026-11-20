#!/usr/bin/env python3
"""Completeness and comparison of the two raw measurement outputs.

usage: verify_measurement.py <cases-dir> <go-output> <rust-output> [--quiet]

A byte comparison of the two outputs is necessary and not sufficient: two empty outputs, or two outputs that lack the same case, are
byte-identical. So this tool first takes the INVENTORY from the generator (`gen_cases.py --inventory`, not from the outputs), checks that the
committed cases directory equals it, and then checks that EACH output accounts for every case and every document exactly once:

  * every inventory case has exactly one compile line;
  * where the schema compiled, every document has exactly one document line (stage parse or validate);
  * the compile result is well formed ('OK|unevaluated=...' or 'ERR[CODE] ...') and is exactly the outcome the inventory expects (a case that must
    compile and was refused, or that must be refused and compiled, or was refused with another code, is a problem);
  * where the schema was refused as expected, the documents are NOT RUN, and that is counted and named, not dropped;
  * no line for an unknown case or document, no duplicate, no document line for a refused schema.

Exit 0 only when both outputs are complete AND byte-identical AND the accounting of the two is equal."""
import os, re, subprocess, sys, collections

def inventory(gen):
    out = subprocess.run([sys.executable, gen, "--inventory"], capture_output=True, check=True, text=True).stdout
    inv = collections.OrderedDict()
    expect = {}
    for line in out.splitlines():
        parts = line.split("|")
        case, doc = parts[0], parts[1]
        inv.setdefault(case, [])
        if doc == "-":
            expect[case] = parts[2].split("=", 1)[1]
        else:
            inv[case].append(doc)
    return inv, expect

def disk(cases_dir):
    d = {}
    for case in sorted(os.listdir(cases_dir)):
        docs = sorted(f[:-5] for f in os.listdir(os.path.join(cases_dir, case, "docs")) if f.endswith(".yaml"))
        d[case] = docs
    return d

def account(name, data, inv, expect):
    """Returns (problems, accounting)."""
    problems = []
    if not data:
        return ["%s: the output is empty" % name], None
    if not data.endswith("\n"):
        problems.append("%s: the output does not end with a newline (truncated?)" % name)
    seen = collections.defaultdict(list)
    for n, line in enumerate(data.split("\n")[:-1] if data.endswith("\n") else data.split("\n"), 1):
        parts = line.split("|", 3)
        if len(parts) < 4:
            problems.append("%s: line %d is not case|document|stage|result: %r" % (name, n, line))
            continue
        case, doc, stage, result = parts
        if case not in inv:
            problems.append("%s: line %d names an unknown case %r" % (name, n, case))
            continue
        if doc != "-" and doc not in inv[case]:
            problems.append("%s: line %d names an unknown document %r of %s" % (name, n, doc, case))
            continue
        seen[(case, doc)].append((stage, result))
    acc = {"cases": len(inv), "docs_total": sum(len(v) for v in inv.values()), "compile_ok": 0, "compile_refused": [], "docs_run": 0, "docs_not_run": 0}
    for case, docs in inv.items():
        comp = seen.get((case, "-"), [])
        if len(comp) != 1:
            problems.append("%s: %s has %d compile lines (expected 1)" % (name, case, len(comp)))
            continue
        stage, result = comp[0]
        if stage != "compile":
            problems.append("%s: the first line of %s is not a compile line" % (name, case))
            continue
        ok_form = re.match(r"^OK\|unevaluated=[^|]*$", result)
        err_form = re.match(r"^ERR\[([A-Z0-9_]+)\]( .*)?$", result)
        if not ok_form and not err_form:
            problems.append("%s: the compile result of %s is neither 'OK|unevaluated=...' nor 'ERR[CODE] ...': %r" % (name, case, result))
            continue
        want = expect[case]
        got = "OK" if ok_form else "ERR[%s]" % err_form.group(1)
        if got != want:
            problems.append("%s: %s compiled as %s, the inventory expects %s" % (name, case, got, want))
            continue
        if ok_form:
            acc["compile_ok"] += 1
            for doc in docs:
                got = seen.get((case, doc), [])
                if len(got) != 1:
                    problems.append("%s: %s/%s has %d document lines (expected 1)" % (name, case, doc, len(got)))
                elif got[0][0] not in ("parse", "validate"):
                    problems.append("%s: %s/%s has the stage %r" % (name, case, doc, got[0][0]))
                else:
                    acc["docs_run"] += 1
        else:
            reason = result.split(" ", 1)[1].strip() if " " in result else result
            acc["compile_refused"].append((case, len(docs), reason))
            acc["docs_not_run"] += len(docs)
            for doc in docs:
                if seen.get((case, doc)):
                    problems.append("%s: %s/%s has a document line although the schema was refused" % (name, case, doc))
    if acc["docs_run"] + acc["docs_not_run"] != acc["docs_total"] and not problems:
        problems.append("%s: accounting does not add up" % name)
    return problems, acc

def main():
    cases_dir, go_path, rust_path = sys.argv[1:4]
    quiet = "--quiet" in sys.argv
    gen = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gen_cases.py")
    inv, expect = inventory(gen)
    problems = []
    if disk(cases_dir) != dict(inv):
        problems.append("the cases directory does not equal the generator inventory")
    # the RAW bytes are compared; a decode is only for the accounting and is strict (an invalid byte is a problem, never replaced)
    raw = {}
    for name, path in (("go", go_path), ("rust", rust_path)):
        raw[name] = open(path, "rb").read() if os.path.exists(path) else b""
    accs = {}
    for name in ("go", "rust"):
        try:
            data = raw[name].decode("utf-8")
        except UnicodeDecodeError as e:
            problems.append("%s: the output is not valid UTF-8 (%s)" % (name, e))
            accs[name] = None
            continue
        p, a = account(name, data, inv, expect)
        problems += p
        accs[name] = a
    if accs["go"] is not None and accs["rust"] is not None and accs["go"] != accs["rust"]:
        problems.append("the accounting of the two outputs differs")
    if raw["go"] != raw["rust"]:
        problems.append("the two outputs are not byte-identical (raw bytes compared)")
    if not quiet:
        print("inventory (generator): %d cases, %d documents" % (len(inv), sum(len(v) for v in inv.values())))
        for name in ("go", "rust"):
            a = accs[name]
            if a is None:
                print("%s: no accounting (output empty)" % name)
                continue
            print("%s: cases %d; schema compiled %d, refused %d; documents total %d, run %d, NOT RUN %d" % (name, a["cases"], a["compile_ok"], len(a["compile_refused"]), a["docs_total"], a["docs_run"], a["docs_not_run"]))
            for case, n, reason in a["compile_refused"]:
                print("  not run (schema refused): %s, %d documents: %s" % (case, n, reason))
    if problems:
        for p in problems:
            print("PROBLEM: " + p)
        print("RESULT: INCOMPLETE OR DIFFERENT")
        sys.exit(1)
    print("RESULT: COMPLETE AND IDENTICAL (every case and document accounted for in both outputs; byte for byte equal)")

main()
