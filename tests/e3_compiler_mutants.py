"""Planted defects for the compiler's envelope 3 output: a small, deliberate break in tools/compiler.py, and the test of tests/test_compiler_envelope3.py that has to turn
red because of it. Same rules as tests/e3_mutants.py: every `old` occurs exactly once; `kills` are substrings of test ids, one of which must be among the failures;
`equivalent` mutants change the source and no behaviour any input can show, carry the reason, and have to survive. `edits` is a list of (old, new) for a break that
needs more than one place.
"""


def m(id, edits, kills=(), equivalent=None):
    if isinstance(edits, tuple):
        edits = [edits]
    return {"id": id, "edits": list(edits), "kills": list(kills), "equivalent": equivalent}


MUTANTS = [
    # the version and the hash rule
    m("compiler-still-writes-envelope-2", ("RELEASE_ENVELOPE_VERSION = 3\n", "RELEASE_ENVELOPE_VERSION = 2\n"), ["envelope_the_compiler_writes_is_3", "writes_an_envelope_3_record"]),
    m("hash-payload-of-envelope-3-missing", ("if envelope_version in (2, 3):", "if envelope_version == 2:"), ["hash_payload_of_envelope_3"]),
    m("hash-payload-of-envelope-3-is-the-v1-rule", ("if envelope_version == 1:\n        return {", "if envelope_version in (1, 3):\n        return {"), ["hash_payload_of_envelope_3", "independent_one"]),
    m("verify-release-does-not-read-envelope-3", ("if envelope_version not in (1, 2, 3):", "if envelope_version not in (1, 2):"), ["reads_an_envelope_3_record"]),
    m("verify-release-says-nothing-of-the-artifact-list", ("        if envelope_version == 3:\n            unproven.append(", "        if False:\n            unproven.append("), ["reads_an_envelope_3_record"]),
    # the source commit
    m("source-commit-null-when-git-says-nothing", ("        sys.exit(1)\n    return commit\n", "        return None\n    return commit\n"), ["never_null", "cannot_name_the_source_commit"]),
    m("source-commit-any-text", ("SOURCE_COMMIT_RE = re.compile(r'^[0-9a-f]{40}$')", "SOURCE_COMMIT_RE = re.compile(r'^.*$')"), ["not_forty_lowercase_hex"]),
    m("source-commit-uppercase-allowed", ("SOURCE_COMMIT_RE = re.compile(r'^[0-9a-f]{40}$')", "SOURCE_COMMIT_RE = re.compile(r'^[0-9a-fA-F]{40}$')"), ["not_forty_lowercase_hex"]),
    m("source-commit-length-open", ("SOURCE_COMMIT_RE = re.compile(r'^[0-9a-f]{40}$')", "SOURCE_COMMIT_RE = re.compile(r'^[0-9a-f]{40,64}$')"), ["not_forty_lowercase_hex"]),
    m("source-commit-end-not-anchored", ("SOURCE_COMMIT_RE = re.compile(r'^[0-9a-f]{40}$')", "SOURCE_COMMIT_RE = re.compile(r'^[0-9a-f]{40}')"), ["not_forty_lowercase_hex"]),
    m("provenance-ignores-the-commit-it-is-given", ("'source_commit': commit or _source_commit()}", "'source_commit': _source_commit()}"), [],
      equivalent="the run asks git for HEAD, which is the commit run_release passed in; the two readings are the same value in every run"),
    m("provenance-without-a-commit-is-null", ("'source_commit': commit or _source_commit()}", "'source_commit': commit}"), ["never_null", "records_the_source_and_digests"]),
    # the git tree
    m("tree-without-directories", ("['git', 'ls-tree', '-r', '-t', '-z', '--full-tree', commit]", "['git', 'ls-tree', '-r', '-z', '--full-tree', commit]"),
      ["refuses_a_declaration_for_the_reason_of_the_vector", "tree_listing", "run_release_refuses_before_any_vault_call"]),
    m("tree-flag-full-tree", ("'-t', '-z', '--full-tree', commit]", "'-t', '-z', commit]"), [],
      equivalent="the compiler runs at the repository root, where the listing is the whole tree with or without --full-tree"),
    m("tree-names-split-on-lines", ("for record in listing.stdout.split(b'\\0'):", "for record in listing.stdout.split(b'\\n'):"), ["tree_listing"]),
    m("blob-from-the-working-directory", ("digest = 'sha256:' + get_sha256_hex(_git_blob(tree[path][2]))", "digest = 'sha256:' + get_sha256_hex(open(path, 'rb').read())"),
      ["blob_bytes_not_of_the_working_directory", "a_filter_in_the_checkout", "any_order_gives_the_same"]),
    m("declaration-from-the-working-directory", ("project = yaml.safe_load(_git_blob(entry[2]))", "project = yaml.safe_load(open('project.yaml', 'rb').read())"),
      ["declaration_comes_from_the_commit", "declaration_in_the_working_directory_only"]),
    m("declaration-found-without-the-commit-entry", ("    if entry is None or entry[1] != 'blob' or entry[0] not in REGULAR_FILE_MODES:\n        return {}\n", ""),
      ["declaration_in_the_working_directory_only", "without_any_declaration", "refuses_before_any_vault_call"]),
    # the declaration rules
    m("declaration-unknown-key-accepted", ("    if unknown:\n        return 'declaration_unknown_key'", "    if False:\n        return 'declaration_unknown_key'"), ["vector"]),
    m("declaration-not-a-list-accepted", ("    if not isinstance(paths, list):\n        return 'declaration_missing'", "    if False:\n        return 'declaration_missing'"), ["vector"]),
    m("declaration-empty-accepted", ("    if not paths:\n        return 'declaration_empty'", "    if False:\n        return 'declaration_empty'"), ["vector", "refuses_before_any_vault_call"]),
    m("declaration-form-not-checked", ("        problem = _release_artifact_path_problem(path)\n        if problem:\n            return 'declaration_path_form'", "        problem = None\n        if problem:\n            return 'declaration_path_form'"), ["vector", "refuses_before_any_vault_call"]),
    m("declaration-duplicate-accepted", ("    if len(set(paths)) != len(paths):", "    if False:"), ["vector", "refuses_before_any_vault_call"]),
    m("declaration-absent-path-accepted", ("        if path not in tree:\n            return 'declared_path_absent'", "        if False:\n            return 'declared_path_absent'"), ["vector", "working_directory_does_not_stand_in"]),
    m("declaration-not-regular-accepted", ("        if kind != 'blob' or mode not in REGULAR_FILE_MODES:\n            return 'declared_path_not_regular'", "        if False:\n            return 'declared_path_not_regular'"), ["vector"]),
    m("declaration-link-counted-regular", ("REGULAR_FILE_MODES = ('100644', '100755')", "REGULAR_FILE_MODES = ('100644', '100755', '120000')"), ["decl-symbolic-link"]),
    m("declaration-submodule-mode-counted-regular", ("REGULAR_FILE_MODES = ('100644', '100755')", "REGULAR_FILE_MODES = ('100644', '100755', '160000')"), [],
      equivalent="a submodule is a commit entry and the type test (kind != blob) still refuses it; the mode test and the type test each refuse it alone"),
    m("declaration-only-directories-refused", ("        if kind != 'blob' or mode not in REGULAR_FILE_MODES:\n            return 'declared_path_not_regular'", "        if mode == '040000':\n            return 'declared_path_not_regular'"), ["decl-symbolic-link", "decl-submodule"]),
    m("declaration-type-test-removed", ("        if kind != 'blob' or mode not in REGULAR_FILE_MODES:\n            return 'declared_path_not_regular'", "        if mode not in REGULAR_FILE_MODES:\n            return 'declared_path_not_regular'"), [],
      equivalent="every non-blob tree entry (a tree 040000, a commit 160000) has a mode outside REGULAR_FILE_MODES, so the type test adds nothing the mode test does not already refuse"),
    # the path rule
    m("path-control-characters-allowed", ("    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in path):", "    if False:"), ["path_rule_refuses", "vector"]),
    m("path-del-allowed", ("ord(ch) < 0x20 or ord(ch) == 0x7F", "ord(ch) < 0x20"), ["path-del", "path_rule_refuses"]),
    m("path-line-feed-allowed", ("ord(ch) < 0x20 or ord(ch) == 0x7F", "ord(ch) < 0x0A or ord(ch) > 0x0A and ord(ch) < 0x20 or ord(ch) == 0x7F"), ["path-line-feed", "decl-line-feed"]),
    m("path-backslash-allowed", ("    if '\\\\' in path:", "    if False:"), ["path-backslash", "decl-backslash"]),
    m("path-dot-allowed", ("        if segment in ('.', '..'):", "        if segment == '..':"), ["path-dot", "decl-dot"]),
    m("path-dot-dot-allowed", ("        if segment in ('.', '..'):", "        if segment == '.':"), ["path-dot-dot", "decl-dot-dot"]),
    m("path-empty-segment-allowed", ("        if segment == '':", "        if False:"), ["path-empty-segment"]),
    m("path-non-string-allowed", ("    if not isinstance(path, str) or path == '':", "    if path == '':"), ["path-a-number", "path_rule_refuses_the_rest", "decl-not-a-string"]),
    m("path-utf8-check-removed", ("    try:\n        path.encode('utf-8')\n    except UnicodeEncodeError:\n        return 'not UTF-8'\n", ""), ["path_rule_refuses_the_rest", "lone-surrogate"]),
    m("path-absolute-has-its-own-branch", ("    if path.startswith('/'):\n        return 'absolute'\n", ""), [],
      equivalent="a leading slash also gives an empty first segment, refused with the same reason; only the detail text differs"),
    m("path-trailing-slash-has-its-own-branch", ("    if path.endswith('/'):\n        return 'trailing slash'\n", ""), [],
      equivalent="a trailing slash also gives an empty last segment, refused with the same reason; only the detail text differs"),
    m("path-empty-has-its-own-branch", ("    if not isinstance(path, str) or path == '':", "    if not isinstance(path, str):"), [],
      equivalent="the empty string splits into one empty segment, refused with the same reason"),
    # the block
    m("artifacts-not-sorted", ("    for path in sorted(paths, key=lambda p: p.encode('utf-8')):", "    for path in list(paths):"), ["any_order_gives_the_same", "the_same_declared_set"]),
    m("artifacts-sorted-by-utf16", ("    for path in sorted(paths, key=lambda p: p.encode('utf-8')):", "    for path in sorted(paths, key=lambda p: p.encode('utf-16-be')):"), ["utf8_bytes_not_utf16"]),
    m("artifacts-sorted-by-code-point", ("    for path in sorted(paths, key=lambda p: p.encode('utf-8')):", "    for path in sorted(paths):"), [],
      equivalent="UTF-8 preserves code point order, so sorting by code point and by UTF-8 bytes agree on every input"),
    m("artifacts-sorted-descending", ("    for path in sorted(paths, key=lambda p: p.encode('utf-8')):", "    for path in sorted(paths, key=lambda p: p.encode('utf-8'), reverse=True):"), ["any_order_gives_the_same", "utf8_bytes_not_utf16"]),
    m("artifact-digest-without-prefix", ("digest = 'sha256:' + get_sha256_hex(_git_blob(tree[path][2]))", "digest = get_sha256_hex(_git_blob(tree[path][2]))"), ["any_order_gives_the_same", "writes_an_envelope_3_record"]),
    m("artifact-digest-base64", ("digest = 'sha256:' + get_sha256_hex(_git_blob(tree[path][2]))", "digest = 'sha256:' + get_sha256_b64(_git_blob(tree[path][2]))"), ["any_order_gives_the_same"]),
    m("artifact-digest-of-the-path", ("digest = 'sha256:' + get_sha256_hex(_git_blob(tree[path][2]))", "digest = 'sha256:' + get_sha256_hex(path.encode('utf-8'))"), ["any_order_gives_the_same"]),
    m("manifest-single-space", ("f\"{entry['digest'][len('sha256:'):]}  {entry['path']}\\n\"", "f\"{entry['digest'][len('sha256:'):]} {entry['path']}\\n\""), ["any_order_gives_the_same"]),
    m("manifest-no-line-feed", ("f\"{entry['digest'][len('sha256:'):]}  {entry['path']}\\n\"", "f\"{entry['digest'][len('sha256:'):]}  {entry['path']}\""), ["any_order_gives_the_same"]),
    m("manifest-without-prefix", ("return {'manifest_digest': 'sha256:' + get_sha256_hex(manifest.encode('utf-8')), 'files': files}", "return {'manifest_digest': get_sha256_hex(manifest.encode('utf-8')), 'files': files}"), ["any_order_gives_the_same"]),
    m("manifest-of-the-reversed-list", ("    manifest = ''.join(f\"{entry['digest'][len('sha256:'):]}  {entry['path']}\\n\" for entry in files)", "    manifest = ''.join(f\"{entry['digest'][len('sha256:'):]}  {entry['path']}\\n\" for entry in reversed(files))"), ["any_order_gives_the_same"]),
    # run_release
    m("record-without-artifacts", ("        'artifacts': artifacts,\n", ""), ["writes_an_envelope_3_record", "coverage_vectors"]),
    m("artifacts-added-after-the-hash", [("        'artifacts': artifacts,\n", ""), ("    bundle['release']['build_hash'] = build_hash\n", "    bundle['artifacts'] = artifacts\n    bundle['release']['build_hash'] = build_hash\n")],
      ["the_hash_the_compiler_wrote", "coverage_vectors", "writes_an_envelope_3_record"]),
    m("artifacts-resolved-after-vault", [("    artifacts = _resolve_release_artifacts(source_commit, tree)\n", "    artifacts = None\n"), ("        'artifacts': artifacts,\n", "        'artifacts': _resolve_release_artifacts(source_commit, tree),\n")],
      ["refuses_before_any_vault_call", "without_any_declaration", "declaration_in_the_working_directory_only", "working_directory_does_not_stand_in"]),
    m("release-block-keeps-envelope-2", ("            'envelope': RELEASE_ENVELOPE_VERSION,\n            'createdBy': release_created_by,", "            'envelope': 2,\n            'createdBy': release_created_by,"), ["writes_an_envelope_3_record"]),
    m("source-paths-not-checked-for-duplicates", ("    _check_unique_source_paths(specs)\n\n    # 6. Build hash", "    # 6. Build hash"), ["checks_the_source_paths_of_the_specs"]),
    m("duplicate-source-path-accepted", ("        if path in seen:\n            print(f\"\\033[91m✗ ERROR: spec_source_path_duplicate", "        if False:\n            print(f\"\\033[91m✗ ERROR: spec_source_path_duplicate"), ["duplicate_spec_source_paths"]),
    # the rest of the record is the source commit's too
    m("guard-not-called", ("    _check_release_inputs_match_commit(tree, schema_files)\n    print(", "    print("), ["ignored_schema_file", "assume_unchanged", "line_end_filter", "skip_worktree", "provenance_or_the_issuer", "ignored_commitment", "working_directory_that_declares"]),
    m("guard-ignores-the-bytes", ("                if fh.read() != _git_blob(entry[2]):", "                if False:"), ["assume_unchanged", "line_end_filter", "provenance_or_the_issuer", "working_directory_that_declares", "symbolic_link"]),
    m("guard-ignores-files-not-in-the-commit", ("        elif entry is None:\n            problems.append((path, 'not in the source commit'))", "        elif entry is None:\n            pass"), ["ignored_schema_file", "ignored_commitment"]),
    m("guard-ignores-missing-files", ("        if not present:\n            problems.append((path, 'missing from the working directory'))", "        if not present:\n            pass"), ["lacks_is_refused"]),
    m("guard-ignores-the-commits-schema-selection", ("    for path in sorted(set(_release_schema_files_in_tree(tree)) - {p.replace(os.sep, '/') for p in schema_files}):\n        problems.append(", "    for path in []:\n        problems.append("), ["skip_worktree"]),
    m("guard-accepts-a-link-in-the-commit", ("        elif entry[1] != 'blob' or entry[0] not in REGULAR_FILE_MODES:\n            problems.append((path, f'not a regular file", "        elif False:\n            problems.append((path, f'not a regular file"), []
      , equivalent="a schema file that is a link in the commit has a blob of the link target's name, which the byte comparison with the file it points to already refuses"),
    m("guard-skips-project-yaml", ("    read = list(schema_files) + ['project.yaml', 'commitment.yaml']", "    read = list(schema_files) + ['commitment.yaml']"), ["provenance_or_the_issuer", "working_directory_that_declares"]),
    m("guard-skips-commitment-yaml", ("    read = list(schema_files) + ['project.yaml', 'commitment.yaml']", "    read = list(schema_files) + ['project.yaml']"), ["ignored_commitment"]),
    m("guard-skips-the-provenance-inputs", ("+ [path for _label, path in PROVENANCE_FILES]", "+ []"), ["provenance_or_the_issuer"]),
    m("guard-skips-the-schema-files", ("    read = list(schema_files) + ['project.yaml', 'commitment.yaml']", "    read = ['project.yaml', 'commitment.yaml']"), ["ignored_schema_file", "assume_unchanged", "line_end_filter"]),
    m("tree-selection-takes-hidden-files", ("        if any(part.startswith('.') for part in path.split('/')):\n            continue\n", ""), ["tree_selection_of_schema_files"]),
    m("tree-selection-takes-empty-files", ("        if len(_git_blob(oid)) > 0:\n            selected.append(path)", "        selected.append(path)"), ["tree_selection_of_schema_files"]),
    m("tree-selection-takes-examples", ("        if os.path.basename(path) == 'index.yaml' or '/examples/' in path:", "        if os.path.basename(path) == 'index.yaml':"), ["tree_selection_of_schema_files"]),
    m("tree-selection-takes-other-directories", ("        if not path.startswith(source_dir + '/') or not path.endswith('.yaml'):", "        if not path.endswith('.yaml'):"), ["tree_selection_of_schema_files"]),
]
