import subprocess, sys, yaml, glob, os
LIM = 2**53 - 1
def ints(x, path="$"):
    if isinstance(x, bool): return
    if isinstance(x, int): yield path, x
    elif isinstance(x, dict):
        for k, v in x.items(): yield from ints(v, path + "." + str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x): yield from ints(v, "%s[%d]" % (path, i))
def report(name, text):
    try: docs = list(yaml.safe_load_all(text))
    except Exception as e: print("%-60s unreadable (%s)" % (name, type(e).__name__)); return
    allv = [(p, v) for d in docs for p, v in ints(d)]
    mx = max(allv, key=lambda t: abs(t[1])) if allv else None
    over = [t for t in allv if abs(t[1]) > LIM]
    print("%-60s integers=%d max_abs=%s beyond_2^53-1=%d" % (name, len(allv), (abs(mx[1]), mx[0]) if mx else "-", len(over)))
    return len(over)
bad = 0
for tag in ("primitives/@v0.1.4","primitives/@v0.1.5","primitives/@v0.2.0","primitives/@v0.2.1"):
    ls = subprocess.run(["git","ls-tree","-r","--name-only",tag,"--","release"],capture_output=True,text=True).stdout.split()
    for f in ls:
        if f.endswith(".yaml"):
            t = subprocess.run(["git","show",tag+":"+f],capture_output=True,text=True).stdout
            bad += report("%s:%s" % (tag, f), t) or 0
n = 0
for root in ("tests/fixtures", "docs/evidence/release-schema-draft-probe"):
    for f in sorted(glob.glob(root + "/**/*.yaml", recursive=True)):
        n += 1; 
        r = report(f, open(f, encoding="utf-8").read()); bad += r or 0
print("files scanned (fixtures and the probe base record):", n, " integers beyond 2^53-1 in all scanned files:", bad)
