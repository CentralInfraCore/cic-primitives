"""Integrity of the files the vector package writes: did the writing mechanism keep the bytes? (owner decision of 2026-11-22, after the observed corruption of a backslash-u escape into a plain
character on its way into a file). An ISOLATED tool-chain check, not a CI gate, and it implements nothing of the profile. Read-only: it NEVER repairs a damaged file.

Two mechanisms that cover different errors:
  canary  : the raw bytes of the file, BEFORE any decoding (no YAML or text parser is involved), must contain the expected representation of every escape-shaped text. The expected bytes are held
            here as INTEGER byte values, so this source file holds no escape text that a faulty writer could have turned into another character; the expectation does not depend on the writer.
  sha256  : the SHA-256 of the whole file must equal a reference value. The tool VERIFIES that the file equals the reference; it cannot AUTHENTICATE the reference, because it cannot establish when or from
            which bytes the value was computed (a value computed from an already damaged file passes the verification: the canary is what still sees that damage). The authentication is a PROCEDURE,
            not a property of the tool: the value stated in the PR description, recomputed independently by the review from the git objects, and supplied EXPLICITLY in the acceptance run
            (--acceptance --expect-sha256 VALUE). The repository reference file (integrity-reference.json) is a convenience for the default run and is NOT an independent basis of trust.
Fail-closed: --no-canary together with --no-sha is refused (exit 2): a run that checks nothing must not report success. Each switch alone stays available (the self-test needs them to show that the
two mechanisms differ).
Exit: 0 all held, 1 a FAIL-EXPECT line (a damaged file or a wrong reference), 2 infrastructure (a file or the reference is missing / unreadable): never a result.
Usage: integrity_check.py [--file PATH] [--expect-sha256 HEX] [--reference PATH] [--no-canary] [--no-sha] [--docs DIR] [--acceptance]
  --acceptance: the review run; requires an explicit --expect-sha256 and refuses --reference, --no-sha and --no-canary (exit 2)"""
import hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
VEC = os.path.join(HERE, "..", "..", "design", "pattern-profile-vectors", "pattern-profile.yaml")
REF = os.path.join(HERE, "integrity-reference.json")


def lit(text):
    return list(text.encode("ascii"))


# (id, the ASCII text before the escape in the vector line, the expected bytes of the escape-shaped part as integers, the ASCII text after it)
# 92 is the backslash, 117 u, 120 x, 110 n, 112 p, 100 d, 123/125 the braces, 76 L, 91/93 the brackets, 45 the hyphen, 39 the quote.
CANARIES = [
    ("X-S146 (backslash, u, 0041)", "{id: X-S146, expr: '", [92, 117, 48, 48, 52, 49], "', expect: refuse"),
    ("X-S145 (backslash, x, 41)", "{id: X-S145, expr: '", [92, 120, 52, 49], "', expect: refuse"),
    ("X-S144 (backslash, n)", "{id: X-S144, expr: '", [92, 110], "', expect: refuse"),
    ("X-S150 (backslash, 1)", "{id: X-S150, expr: '", [92, 49], "', expect: refuse"),
    ("X-S151 (backslash, 0)", "{id: X-S151, expr: '", [92, 48], "', expect: refuse"),
    ("X-S153 (backslash, p, {L})", "{id: X-S153, expr: '", [92, 112, 123, 76, 125], "', expect: refuse"),
    ("X-K109 ([backslash d, hyphen, hyphen])", "{id: X-K109, expr: '[", [92, 100, 45, 45], "]', expect: refuse"),
    ("X-A033 (a, backslash, dollar)", "{id: X-A033, expr: 'a", [92, 36], "', expect: accept"),
]
# the documents state the sequence in prose: the bytes (backtick, backslash, u, 0041, backtick) must be there
DOC_CANARY = [96, 92, 117, 48, 48, 52, 49, 96]
DOCS = ["en/GRAMMAR-PATTERN-VECTORS.md", "hu/GRAMMAR-PATTERN-VECTORS.md"]
fails = []


def expect(label, cond, detail=""):
    if not cond:
        fails.append(label); print("FAIL-EXPECT %s %s" % (label, detail))


def read(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError as e:
        print("INCOMPLETE: %s cannot be read: %r" % (path, e)); sys.exit(2)


def main(argv):
    def opt(name):
        return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None
    if "--no-canary" in argv and "--no-sha" in argv:
        print("INCOMPLETE: --no-canary together with --no-sha selects no check; a run that checks nothing must not report success"); return 2
    acceptance = "--acceptance" in argv
    if acceptance:
        if opt("--expect-sha256") is None or "--reference" in argv or "--no-sha" in argv or "--no-canary" in argv:
            print("INCOMPLETE: --acceptance needs an explicit --expect-sha256 (the independently approved value) and refuses --reference, --no-sha and --no-canary"); return 2
    path = opt("--file") or VEC
    data = read(path)
    if "--no-canary" not in argv:
        for name, pre, esc, post in CANARIES:
            want = bytes(lit(pre) + esc + lit(post))
            expect("canary.%s" % name, want in data, "the raw bytes %s are not in %s" % (list(want[-len(esc) - len(post):][:len(esc)]), os.path.basename(path)))
        docs_root = opt("--docs")
        if docs_root:
            for d in DOCS:
                body = read(os.path.join(docs_root, d))
                expect("canary.doc.%s" % d, bytes(DOC_CANARY) in body, "the escape sequence stated in prose is not in the document")
    if "--no-sha" not in argv:
        ref = opt("--expect-sha256")
        source = "the value supplied on the command line" if ref is not None else "the repository reference file"
        if ref is None:
            try:
                ref = json.loads(read(opt("--reference") or REF).decode("ascii"))["vector_file_sha256"]
            except (ValueError, KeyError) as e:
                print("INCOMPLETE: the reference value is missing or unreadable: %r" % (e,)); return 2
        got = hashlib.sha256(data).hexdigest()
        print("sha256 of %s: %s (reference %s, from %s)" % (os.path.basename(path), got, ref, source))
        print("mode: %s" % ("ACCEPTANCE: verified against an explicit value; the value is authenticated by the review procedure (PR description, independent recomputation), not by this tool" if acceptance
                            else "verification only: the reference is %s, which is NOT an independent basis of trust" % source))
        expect("sha256", got == ref, "the file differs from the bytes the reference was computed from")
    if fails:
        print("FAILED: %d expectation(s); the file was not touched" % len(fails)); return 1
    print("all expectations held"); return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
