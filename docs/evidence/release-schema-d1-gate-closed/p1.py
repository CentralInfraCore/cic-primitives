# usage: python p1.py <dir holding composed-PrimitiveRelease.yaml and composed-ModuleRelease.yaml>; prints the P1 table
import re, yaml, sys
samples = {
 r'^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$': '1.2.3',
 r'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})$': '2026-11-02T10:00:00Z',
 r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$': '2026-11-02',
 r'^[0-9a-f]{40}$': 'a'*40,
 r'^sha256:[0-9a-f]{64}$': 'sha256:'+'b'*64,
 r'^[A-Za-z0-9+/]{43}=$': 'A'*43+'=',
 r'^vault:v1:.+$': 'vault:v1:abc',
}
seen = set()
for k in ("PrimitiveRelease","ModuleRelease"):
    d = yaml.safe_load(open(sys.argv[1]+"/composed-%s.yaml"%k))
    def walk(x):
        if isinstance(x, dict):
            if x.get("type") == "pattern": seen.add(x["expression"])
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    walk(d)
print("distinct patterns in composed schemas:", len(seen))
for p in sorted(seen):
    s = samples[p]
    print("%-3s valid=%s  valid+LF(search)=%s  valid+LF(fullmatch)=%s  %s" % ("", bool(re.search(p,s)), bool(re.search(p,s+"\n")), bool(re.fullmatch(p,s+"\n")), p[:60]))
