#!/usr/bin/env python3
"""Machine comparison of the two raw outputs: byte identity, line counts, the first differing line. Exit 0 only if identical."""
import hashlib, sys
a, b = (open(p, "rb").read() for p in sys.argv[1:3])
print("go-output.txt   bytes=%d lines=%d sha256=%s" % (len(a), a.count(b"\n"), hashlib.sha256(a).hexdigest()))
print("rust-output.txt bytes=%d lines=%d sha256=%s" % (len(b), b.count(b"\n"), hashlib.sha256(b).hexdigest()))
if a == b:
    print("RESULT: IDENTICAL (byte for byte)")
    sys.exit(0)
la, lb = a.split(b"\n"), b.split(b"\n")
for i, (x, y) in enumerate(zip(la, lb), 1):
    if x != y:
        print("RESULT: DIFFERENT at line %d\n go:   %s\n rust: %s" % (i, x.decode(), y.decode()))
        break
else:
    print("RESULT: DIFFERENT (one output is a prefix of the other)")
sys.exit(1)
