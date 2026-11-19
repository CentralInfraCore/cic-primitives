# Forms grammar capability measurement (evidence)

Evidence for `docs/en/RELEASE-GRAMMAR-CAPABILITY-MEASUREMENT.md` (step 1 of section 11 of the generalization plan). Not production code.

* Measured on the **unchanged** Form: `cic-primitive-forms` `main` `2f02a75592a4b0894a3b76891e9ba3741479a7c5` (2026-11-05), grammar profile `cic-primitives-73ae469-6a188078` (the only profile the Forms carry; a development commit, not a release). The only file added to the checkout is the example `rust/examples/capprobe.rs` (= `probe.rs.txt`); no library file is touched.
* Toolchains: Rust `rustc 1.99.1` (image `rust:1`), Go `go1.26.11` (image `golang:1.26.11`).
* `gen_cases.py <dir>` writes the 34 cases (128 documents): one `schema.yaml` and a few documents per capability; the committed `cases/` equal its output. Prefix `pos_` = conforming, `neg_` = the record contract needs it refused, `inf_` = recorded without expectation.
* `probe.go.txt` and `probe.rs.txt` (stored with a `.txt` suffix so no build of this repository picks them up): per case, `compile_schema` (the compile line also lists the nodes whose `contract` is passed through unevaluated), then `parse` and `validate` of every document. Go: put `probe.go.txt` as `main.go` next to `go.mod.txt` (as `go.mod`, with `replace` pointing to the checkout's `go/`) and run `go run . <cases>`; it exits 2 on a read error, a missing case or an empty document set. Rust: put `probe.rs.txt` as `rust/examples/capprobe.rs` and run `cargo run -q --example capprobe -- <cases>`.
* **Raw outputs, kept apart**: `go-output.txt` and `rust-output.txt` (160 lines, 8309 bytes each). `SHA256SUMS` has the full digests of both (and of the generator, the probes and `comparison.txt`). `comparison.txt` is the machine comparison (`python3 compare.py go-output.txt rust-output.txt`): byte-identical. A difference would be a STOP.
* Line format: `case|document|stage|result`; `compile` lines have `-` as the document.
