"""The published package, measured: what a consumer can do with ONLY the declared files.

Builds a directory from the git blobs of the files project.yaml declares (nothing else from the repository), and runs, in Python's isolated mode (-I), the tools that are
part of that surface, plus a consumer-side check of the published node-name vectors. Used by tests/test_release_declaration.py and, run as a script, as the measurement
of docs/evidence/publication-name-vectors/.

    python tests/published_package.py [<commit>]        # prints the table
"""
import pathlib
import subprocess
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONSUMER = r'''
import importlib.util, sys, yaml
spec = importlib.util.spec_from_file_location("g", "proposals/atom-grammar/check_grammar.py")
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
vec = yaml.safe_load(open("proposals/atom-grammar/name-vectors/node-name.yaml", encoding="utf-8"))
validator = g.load_schema(node_name_grammar=2)
bad = []
for n in vec["names"]:
    got = "accept" if not g.check_document(g.as_document({"name": n["name"], "shape_type": "opaque"}), validator) else "refuse"
    if got != n["v2"]:
        bad.append(n["id"])
def dec(x):
    return str(x["str"]) if isinstance(x, dict) and "str" in x else float(x["float"]) if isinstance(x, dict) and "float" in x else x
for b in vec["binding"]:
    try:
        g.bind_node_name_grammar(dec(b["context"]), dec(b["pin"])); got = "ok"
    except g.GrammarVersionError as e:
        got = e.code
    if got != b["expect"]:
        bad.append(b["id"])
print("%d names and %d binding cases of the published vectors, %d mismatch(es) %s" % (len(vec["names"]), len(vec["binding"]), len(bad), bad))
sys.exit(1 if bad else 0)
'''


def declared_paths(commit="HEAD"):
    text = subprocess.run(["git", "-C", str(ROOT), "show", "%s:project.yaml" % commit], capture_output=True, check=True).stdout
    return yaml.safe_load(text)["compiler_settings"]["release_artifacts"]["paths"]


def build(directory, commit="HEAD"):
    paths = declared_paths(commit)
    for p in paths:
        blob = subprocess.run(["git", "-C", str(ROOT), "show", "%s:%s" % (commit, p)], capture_output=True, check=True).stdout
        target = pathlib.Path(directory) / p
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
    return paths


def run(directory):
    """Returns [(label, exit code, last output line)]."""
    def py(*args, label):
        r = subprocess.run([sys.executable, "-I", *args], cwd=directory, capture_output=True, text=True)
        lines = [l for l in (r.stdout + r.stderr).strip().splitlines() if l.strip()]
        return (label, r.returncode, lines[-1].replace("\x1b[92m", "").replace("\x1b[0m", "") if lines else "")
    return [
        py("proposals/atom-grammar/check_access_vectors.py", label="check_access_vectors.py"),
        py("proposals/atom-grammar/check_access_vectors.py", "--self-test", label="check_access_vectors.py --self-test"),
        py("proposals/atom-grammar/check_grammar.py", "--self-test", "--node-name-grammar", "2", label="check_grammar.py --self-test --node-name-grammar 2"),
        py("proposals/atom-grammar/check_grammar.py", "--self-test", label="check_grammar.py --self-test (no version: must refuse)"),
        py("-c", CONSUMER, label="consumer check of name-vectors/node-name.yaml with the published checker"),
    ]


if __name__ == "__main__":
    commit = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    with tempfile.TemporaryDirectory() as d:
        paths = build(d, commit)
        print("a directory with ONLY the %d declared files of %s (python -I)" % (len(paths), subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", commit], capture_output=True, text=True).stdout.strip()))
        for label, rc, last in run(d):
            print("exit %d  %-75s %s" % (rc, label, last[:110]))
