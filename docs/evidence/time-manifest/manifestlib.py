"""The CANONICAL MANIFEST of the records that are to receive external time evidence (docs/en/T3-MANIFEST-CONTRACT.md). A line-oriented, byte-exact format, so that there is NO serialisation to disagree about:

    CIC-T3-MANIFEST/1\\n
    scope: <one line of text without a tab>\\n
    count: <n>\\n
    ---\\n
    <record_id>\\t<sha256 hex of the EXACT record bytes>\\t<size in bytes>\\t<repo>\\t<commit, 40 hex>\\t<ref: tag:<name> or branch:<name>>\\t<path>\\n      (n lines, sorted bytewise by record_id)

UTF-8, no BOM, LF only, a final LF, no other line. record_id = <repo>:<path>. The digest to be time-stamped is the SHA-256 of the WHOLE manifest byte stream. The bytes of a record are read from the git OBJECT
at the recorded commit (`git show <commit>:<path>`), never from a working tree. Nothing here signs, stamps or uploads anything."""
import hashlib, re, subprocess

HEADER = "CIC-T3-MANIFEST/1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")


class ManifestError(Exception):
    pass


def git_bytes(clone, *args):
    r = subprocess.run(["git", "-C", clone] + list(args), capture_output=True)
    if r.returncode != 0:
        raise ManifestError("git %s failed (exit %d): %s" % (" ".join(args), r.returncode, r.stderr.decode("utf-8", "replace").strip()[:120]))
    return r.stdout


def record_line(repo, path, commit, ref, data):
    rid = "%s:%s" % (repo, path)
    for part in (rid, repo, ref, path):
        if "\t" in part or "\n" in part or "\r" in part or not part:
            raise ManifestError("a field with a tab, a newline or nothing: %r" % part)
    return (rid, hashlib.sha256(data).hexdigest(), len(data), repo, commit, ref, path)


def render(scope, entries):
    """entries: list of 7-tuples -> the manifest bytes"""
    if "\t" in scope or "\n" in scope or not scope:
        raise ManifestError("the scope line must be one line of text without a tab")
    ids = [e[0].encode("utf-8") for e in entries]
    if len(set(ids)) != len(ids):
        raise ManifestError("duplicate record ids")
    out = [HEADER, "scope: " + scope, "count: %d" % len(entries), "---"]
    for e in sorted(entries, key=lambda e: e[0].encode("utf-8")):
        out.append("\t".join([e[0], e[1], str(e[2]), e[3], e[4], e[5], e[6]]))
    return ("\n".join(out) + "\n").encode("utf-8")


def parse(raw):
    """the manifest bytes -> (scope, count, entries); raises ManifestError for anything that is not the canonical form"""
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ManifestError("a byte order mark")
    if b"\r" in raw:
        raise ManifestError("a carriage return: the manifest is LF only")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ManifestError("not valid UTF-8")
    if not text.endswith("\n") or text.endswith("\n\n"):
        raise ManifestError("the manifest must end with exactly one LF")
    lines = text[:-1].split("\n")
    if len(lines) < 4 or lines[0] != HEADER or not lines[1].startswith("scope: ") or not re.fullmatch(r"count: (0|[1-9][0-9]*)", lines[2]) or lines[3] != "---":
        raise ManifestError("the header is not the canonical one")
    scope = lines[1][len("scope: "):]; count = int(lines[2][len("count: "):]); body = lines[4:]
    if len(body) != count:
        raise ManifestError("count says %d, there are %d record lines" % (count, len(body)))
    entries = []
    for ln in body:
        f = ln.split("\t")
        if len(f) != 7:
            raise ManifestError("a record line without exactly 7 tab-separated fields: %r" % ln[:60])
        rid, dg, size, repo, commit, ref, path = f
        if rid != "%s:%s" % (repo, path):
            raise ManifestError("the record id %r is not repo:path" % rid)
        if not HEX64.match(dg) or not HEX40.match(commit) or not re.fullmatch(r"(0|[1-9][0-9]*)", size) or not re.fullmatch(r"(tag|branch):.+", ref):
            raise ManifestError("a malformed field in %r" % rid)
        entries.append((rid, dg, int(size), repo, commit, ref, path))
    ids = [e[0].encode("utf-8") for e in entries]
    if ids != sorted(ids):
        raise ManifestError("the record lines are not sorted bytewise by record id")
    if len(set(ids)) != len(ids):
        raise ManifestError("duplicate record ids")
    return scope, count, entries


def digest(raw):
    return hashlib.sha256(raw).hexdigest()
