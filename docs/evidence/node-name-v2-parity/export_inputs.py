#!/usr/bin/env python3
"""Exports what the Go and Rust runners are given, from the REAL files: names.json from the vectors, rule.json from the name sub-schema of the grammar file.
usage: export_inputs.py <out-dir>      (the gate, check C8, recomputes both and compares them with the committed ones)"""
import json, sys
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[3]
vec = yaml.safe_load((ROOT / "proposals/atom-grammar/name-vectors/node-name.yaml").read_text(encoding="utf-8"))
name = yaml.safe_load((ROOT / "proposals/atom-grammar/instance-grammar.schema.yaml").read_text(encoding="utf-8"))["properties"]["name"]
out = Path(sys.argv[1])
(out / "names.json").write_text(json.dumps([{"id": n["id"], "name": n["name"]} for n in vec["names"]], ensure_ascii=True, indent=0) + "\n", encoding="utf-8")
(out / "rule.json").write_text(json.dumps({"min_length": name.get("minLength"), "pattern": name.get("pattern"), "not_pattern": (name.get("not") or {}).get("pattern")}, indent=0) + "\n", encoding="utf-8")
