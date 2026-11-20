#!/usr/bin/env python3
"""Generates the capability cases: one schema and a few documents per capability.
Document prefix: pos_ = a conforming document, neg_ = a document the record contract needs refused, inf_ = recorded, no expectation."""
import os, sys
INVENTORY = sys.argv[1] == "--inventory"
OUT = None if INVENTORY else sys.argv[1]
HEAD = """spec:
  identity:
    atomic_ref: "cic:core:Identity@v0.2.0"
    kind: CapProbe
    namespace: "cic:release"
    version: v0.0.1
  config_surface:
    aggregate_ref: "cic:core:ConfigSurface@v0.2.0"
    nodes:
"""
def schema(nodes):
    return HEAD + "".join("      " + l + "\n" for l in nodes.strip("\n").split("\n"))
S = lambda n, extra="": "- {name: %s, shape_type: scalar, scalar_type: string%s}" % (n, extra)
cases = {}
REFUSED = {}   # case id -> the reason code the Form must refuse the schema with (an expected refusal)
def case(cid, desc, nodes, docs, refused=None):
    cases[cid] = (desc, schema(nodes), docs)
    if refused:
        REFUSED[cid] = refused

case("K01_mandatory", "mandatory scalar", S("a", ", mandatory: true"), {
  "pos_present": "a: x\n", "neg_absent": "{}\n"})
case("K02_optional", "optional scalar; null is not allowed unless nullable", S("a", ", optional: true"), {
  "pos_absent": "{}\n", "pos_present": "a: x\n", "neg_null": "a: null\n"})
case("K03_nullable_mandatory", "mandatory + nullable", S("a", ", mandatory: true, nullable: true"), {
  "pos_null": "a: null\n", "pos_value": "a: x\n", "neg_absent": "{}\n"})
case("K04_nullable_optional", "optional + nullable", S("a", ", optional: true, nullable: true"), {
  "pos_absent": "{}\n", "pos_null": "a: null\n", "neg_map_at_scalar": "a: {x: 1}\n"})
case("K05_scalar_integer", "integer scalar", "- {name: n, shape_type: scalar, scalar_type: integer, mandatory: true}", {
  "pos_five": "n: 5\n", "pos_negative": "n: -3\n", "neg_quoted": "n: \"5\"\n", "neg_word": "n: x\n",
  "neg_bool": "n: true\n", "neg_float": "n: 1.5\n", "inf_plus": "n: +7\n", "inf_leading_zero": "n: 010\n", "inf_hex": "n: 0x10\n", "inf_underscore": "n: 1_000\n", "inf_exp": "n: 1e3\n", "inf_sexagesimal": "n: 1:30\n"})
case("K05b_scalar_boolean", "boolean scalar", "- {name: b, shape_type: scalar, scalar_type: boolean, mandatory: true}", {
  "pos_true": "b: true\n", "pos_False": "b: False\n", "neg_quoted": "b: \"true\"\n", "neg_int": "b: 1\n", "neg_yes": "b: yes\n", "inf_on": "b: on\n"})
case("K05c_scalar_string", "string scalar", S("s", ", mandatory: true"), {
  "pos_word": "s: x\n", "pos_quoted_digits": "s: \"5\"\n", "neg_map": "s: {a: 1}\n", "neg_list": "s: [1]\n",
  "inf_plain_int": "s: 5\n", "inf_plain_bool": "s: true\n", "inf_yes": "s: yes\n", "inf_date": "s: 2026-05-25\n", "inf_timestamp": "s: 2026-11-02T18:57:58+00:00\n"})
case("K06_integer_range", "integer range: the record contract (O3) allows |n| <= 2^53-1",
     "- {name: n, shape_type: scalar, scalar_type: integer, mandatory: true}", {
  "pos_max_safe": "n: 9007199254740991\n", "pos_min_safe": "n: -9007199254740991\n",
  "neg_2_53": "n: 9007199254740992\n", "neg_2_53_plus1": "n: 9007199254740993\n",
  "neg_int64_max": "n: 9223372036854775807\n", "neg_beyond_int64": "n: 9223372036854775808\n"})
LIST = """- name: files
  shape_type: collection
  collection_variant: list
  mandatory: true
  %s
  item_fields:
    - {name: path, shape_type: scalar, scalar_type: string, role: key}
    - {name: digest, shape_type: scalar, scalar_type: string, mandatory: true}"""
case("K07_min_items", "list with min_items 1", LIST % "min_items: 1", {
  "pos_one": "files:\n  - {path: a, digest: d}\n", "neg_empty": "files: []\n", "neg_absent": "{}\n"})
case("K07b_min_items_2", "list with min_items 2", LIST % "min_items: 2", {
  "pos_two": "files:\n  - {path: a, digest: d}\n  - {path: b, digest: d}\n", "neg_one": "files:\n  - {path: a, digest: d}\n"})
case("K08_max_items", "schema attempts max_items: 1 (declared by the grammar, refused by the Form)", LIST % "max_items: 1", {
  "pos_one": "files:\n  - {path: a, digest: d}\n", "neg_two": "files:\n  - {path: a, digest: d}\n  - {path: b, digest: d}\n"}, refused="SCHEMA_SHAPE_UNSUPPORTED")
COMP = """- name: c
  shape_type: composite
  mandatory: true
  fields:
    - {name: x, shape_type: scalar, scalar_type: string, mandatory: true}"""
case("K09_unknown_fields", "composite refuses unknown fields", COMP, {
  "pos_known": "c: {x: a}\n", "neg_unknown_nested": "c: {x: a, y: b}\n", "neg_unknown_top": "c: {x: a}\nz: 1\n"})
case("K10_list_key_identity", "list item identity by a declared key", LIST % "min_items: 1", {
  "pos_distinct": "files:\n  - {path: a, digest: d}\n  - {path: b, digest: d}\n",
  "neg_duplicate_key": "files:\n  - {path: a, digest: d1}\n  - {path: a, digest: d2}\n",
  "neg_missing_key": "files:\n  - {digest: d}\n",
  "inf_unsorted": "files:\n  - {path: b, digest: d}\n  - {path: a, digest: d}\n",
  "inf_duplicate_digest": "files:\n  - {path: a, digest: d}\n  - {path: b, digest: d}\n",
  "inf_case_keys": "files:\n  - {path: a, digest: d}\n  - {path: A, digest: d}\n"})
case("K11_composite_scalar_boundary", "composite against scalar positions", COMP, {
  "pos_map": "c: {x: a}\n", "neg_scalar_at_composite": "c: text\n", "neg_list_at_composite": "c: [1]\n", "neg_null_at_composite": "c: null\n"})
case("K12_enum_attempt", "schema attempts enum on a scalar (a closed set of values, e.g. a record kind)",
     S("kind", ", mandatory: true, enum: [PrimitiveRelease, ModuleRelease]"), {
  "pos_member": "kind: PrimitiveRelease\n", "neg_non_member": "kind: Other\n"})
case("K12b_const_attempt", "schema attempts const on a scalar", S("kind", ", mandatory: true, const: PrimitiveRelease"), {
  "pos_equal": "kind: PrimitiveRelease\n", "neg_different": "kind: Other\n"})
case("K13_pattern_attempt", "schema attempts a pattern on a string", S("d", ", mandatory: true, pattern: '^sha256:[0-9a-f]{64}$'"), {
  "pos_digest": "d: sha256:" + "a"*64 + "\n", "neg_no_prefix": "d: " + "a"*64 + "\n", "neg_upper": "d: sha256:" + "A"*64 + "\n", "neg_short": "d: sha256:" + "a"*63 + "\n"})
case("K13b_plain_string_no_constraint", "no schema constraint on a string: what is accepted", S("d", ", mandatory: true"), {
  "inf_digest": "d: sha256:" + "a"*64 + "\n", "inf_garbage": "d: not-a-digest\n", "inf_empty": "d: ''\n", "inf_control": "d: \"a\\tb\"\n"})
case("K14_opaque", "opaque field takes any value", "- {name: o, shape_type: opaque, mandatory: true}", {
  "pos_map": "o: {a: 1}\n", "pos_list": "o: [1, 2]\n", "pos_scalar": "o: x\n", "neg_absent": "{}\n"})
case("K15_set_uniqueness", "set collection of strings (unique scalars)", "- {name: s, shape_type: collection, collection_variant: set, item_scalar_type: string, mandatory: true}", {
  "pos_distinct": "s: [a, b]\n", "neg_duplicate": "s: [a, a]\n", "inf_empty": "s: []\n"})
PRE = "\n".join(S(n, ", optional: true").replace("scalar, scalar_type: string", "opaque").replace("opaque, optional", "opaque, optional") for n in ("a", "b", "yes", "1"))
PRE = "- {name: a, shape_type: opaque, optional: true}\n- {name: b, shape_type: opaque, optional: true}\n- {name: base, shape_type: opaque, optional: true}\n- {name: d, shape_type: opaque, optional: true}\n- {name: yes, shape_type: opaque, optional: true}\n- {name: \"1\", shape_type: opaque, optional: true}\n- {name: \"null\", shape_type: opaque, optional: true}"
case("K16_pre_tree_parse", "parse-level behavior the admission profile A needs refused before any tree (duplicate key, alias, merge key, tag, second document, BOM)", PRE, {
  "pos_plain": "a: 1\nb: 2\n",
  "neg_duplicate_key": "a: 1\na: 2\n",
  "neg_alias": "a: &x 1\nb: *x\n",
  "neg_merge_key": "base: &b {k: 1}\nd:\n  <<: *b\n",
  "neg_tag": "a: !!str 1\n",
  "neg_two_documents": "a: 1\n---\na: 2\n",
  "neg_bom": "﻿a: 1\n",
  "neg_key_yes": "yes: 1\n",
  "neg_key_one": "1: a\n",
  "neg_key_null": "null: 1\n",
  "inf_comment": "a: 1 # c\n# trailing\n",
  "inf_flow": "{a: 1, b: 2}\n",
  "inf_empty_document": "",
  "inf_document_start": "---\na: 1\n",
  "inf_crlf": "a: 1\r\nb: 2\r\n"})

case("K17a_unknown_schema_key", "an unknown key on a schema node (foo): accepted or refused by compile", S("a", ", mandatory: true, foo: bar"), {
  "pos_present": "a: x\n", "neg_absent": "{}\n"})
case("K17b_misspelled_presence_key", "a misspelled presence key (mandatry) instead of mandatory", S("a", ", mandatry: true"), {
  "inf_absent": "{}\n", "inf_present": "a: x\n"})
case("K17c_unknown_key_on_composite", "an unknown key on a composite node (pattern)", "- name: c\n  shape_type: composite\n  mandatory: true\n  pattern: x\n  fields:\n    - {name: x, shape_type: scalar, scalar_type: string, mandatory: true}", {
  "pos_known": "c: {x: a}\n", "neg_unknown": "c: {y: a}\n"})
case("K17d_unknown_key_on_list", "an unknown key on a list node (unique_items)", LIST % "unique_items: true", {
  "pos_one": "files:\n  - {path: a, digest: d}\n", "neg_duplicate_key": "files:\n  - {path: a, digest: d}\n  - {path: a, digest: d}\n"})

CN = lambda ctype, expr, base: base % ("contract: [{type: %s, expression: %s}]" % (ctype, expr))
case("K18a_contract_pattern", "a pattern as a Contract entry (the grammar's own mechanism), not as a node key",
     "- {name: d, shape_type: scalar, scalar_type: string, mandatory: true, contract: [{type: pattern, expression: '^sha256:[0-9a-f]{64}$'}]}", {
  "pos_digest": "d: sha256:" + "a"*64 + "\n", "neg_no_prefix": "d: " + "a"*64 + "\n", "neg_upper": "d: sha256:" + "A"*64 + "\n", "neg_short": "d: sha256:" + "a"*63 + "\n"})
case("K18b_contract_enum", "an enum as a Contract entry",
     "- {name: kind, shape_type: scalar, scalar_type: string, mandatory: true, contract: [{type: enum, expression: [PrimitiveRelease, ModuleRelease]}]}", {
  "pos_member": "kind: PrimitiveRelease\n", "neg_non_member": "kind: Other\n"})
case("K18c_contract_range", "a range as a Contract entry",
     "- {name: n, shape_type: scalar, scalar_type: integer, mandatory: true, contract: [{type: range, expression: '0..9007199254740991'}]}", {
  "pos_max_safe": "n: 9007199254740991\n", "pos_zero": "n: 0\n", "neg_2_53": "n: 9007199254740992\n", "neg_negative": "n: -1\n"})
case("K18d_contract_unique", "a unique as a Contract entry on a list (a non-key field)",
     "- name: files\n  shape_type: collection\n  collection_variant: list\n  mandatory: true\n  contract: [{type: unique, expression: digest}]\n  item_fields:\n    - {name: path, shape_type: scalar, scalar_type: string, role: key}\n    - {name: digest, shape_type: scalar, scalar_type: string, mandatory: true}", {
  "pos_distinct": "files:\n  - {path: a, digest: d1}\n  - {path: b, digest: d2}\n", "neg_duplicate_digest": "files:\n  - {path: a, digest: d}\n  - {path: b, digest: d}\n"})
case("K18e_contract_unknown_type", "a Contract entry whose type is outside the grammar's closed list",
     "- {name: a, shape_type: scalar, scalar_type: string, mandatory: true, contract: [{type: bogus, expression: x}]}", {
  "pos_present": "a: x\n", "neg_absent": "{}\n"})
case("K18f_contract_empty_list", "an empty contract list (the grammar requires minItems 1)",
     "- {name: a, shape_type: scalar, scalar_type: string, mandatory: true, contract: []}", {
  "pos_present": "a: x\n", "neg_absent": "{}\n"})
case("K18g_contract_missing_expression", "a Contract entry without the required expression",
     "- {name: a, shape_type: scalar, scalar_type: string, mandatory: true, contract: [{type: pattern}]}", {
  "pos_present": "a: x\n", "neg_absent": "{}\n"})
case("K19a_ordered_true", "ordered: true on a list (the grammar's flag that the element order is meaningful)", LIST % "ordered: true", {
  "inf_sorted": "files:\n  - {path: a, digest: d}\n  - {path: b, digest: d}\n", "inf_unsorted": "files:\n  - {path: b, digest: d}\n  - {path: a, digest: d}\n"})
case("K19b_ordered_false", "ordered: false on a list", LIST % "ordered: false", {
  "inf_sorted": "files:\n  - {path: a, digest: d}\n  - {path: b, digest: d}\n", "inf_unsorted": "files:\n  - {path: b, digest: d}\n  - {path: a, digest: d}\n"})
if INVENTORY:
    # the machine inventory of what the generator defines: one line per case and per document
    for cid, (desc, sch, docs) in sorted(cases.items()):
        print("%s|-|compile=%s" % (cid, ("ERR[%s]" % REFUSED[cid]) if cid in REFUSED else "OK"))
        for name in sorted(docs):
            print("%s|%s" % (cid, name))
    sys.exit(0)
for cid, (desc, sch, docs) in sorted(cases.items()):
    d = os.path.join(OUT, cid, "docs")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(OUT, cid, "schema.yaml"), "w", encoding="utf-8", newline="").write(sch)
    open(os.path.join(OUT, cid, "DESCRIPTION"), "w", encoding="utf-8").write(desc + "\n")
    for name, text in docs.items():
        open(os.path.join(d, name + ".yaml"), "w", encoding="utf-8", newline="").write(text)
print(len(cases), "cases", sum(len(c[2]) for c in cases.values()), "documents")
