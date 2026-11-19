# Forms grammar capability measurement (evidence)

Evidence for `docs/en/RELEASE-GRAMMAR-CAPABILITY-MEASUREMENT.md` (step 1 of section 11 of the generalization plan). Not production code.

* Measured on the **unchanged** Form: `cic-primitive-forms` `main` `2f02a75592a4b0894a3b76891e9ba3741479a7c5` (2026-11-05), grammar profile `cic-primitives-73ae469-6a188078` (the only profile the Forms carry; a development commit, not a release). The only file added to the checkout is the example `rust/examples/capprobe.rs` (= `probe.rs.txt`); no library file is touched.
* Toolchains: Rust `rustc 1.99.1` (image `rust:1`), Go `go1.26.11` (image `golang:1.26.11`).
* `gen_cases.py <dir>` writes the 25 cases (106 documents): one `schema.yaml` and a few documents per capability. Prefix `pos_` = conforming, `neg_` = the record contract needs it refused, `inf_` = recorded without expectation.
* `probe.go.txt` and `probe.rs.txt` (stored with a `.txt` suffix so no build of this repository picks them up): per case, `compile_schema` then `parse` and `validate` of every document. Go: put `probe.go.txt` as `main.go` next to `go.mod.txt` (as `go.mod`, with `replace` pointing to the checkout's `go/`) and run `go run . <cases>`. Rust: put `probe.rs.txt` as `rust/examples/capprobe.rs` and run `cargo run -q --example capprobe -- <cases>`.
* `expected-output.txt` (129 lines, SHA-256 `285ce31a5bd522bde0e7b82ead33127ac355a686d411888d2e0fbd72060c5bc7`) is the output of **both** readers; they were identical byte for byte. A difference between the two would be a STOP.
* Line format: `case|document|stage|result`; `compile` lines have `-` as the document.
