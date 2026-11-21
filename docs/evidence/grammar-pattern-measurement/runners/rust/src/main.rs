// Pattern probe, Rust (the `regex` crate, default limits: size_limit 10 MiB, nest_limit 250). It applies NO rule of its own: it compiles the `native` string it is given and
// matches it against the input it is given (hex). Output, one line per case: `id|verdict|elapsed_ns`, verdict = compile_error | match | nomatch.
// The error text goes to stderr only when VERBOSE=1. Usage: cargo run -q --locked -- cases.json
use serde_json::Value;
use std::time::Instant;

fn unhex(s: &str) -> Vec<u8> {
    (0..s.len()).step_by(2).map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap()).collect()
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let cs: Value = serde_json::from_str(&std::fs::read_to_string(&a[1]).unwrap()).unwrap();
    let list = cs.as_array().unwrap();
    if list.is_empty() {
        eprintln!("no cases: refusing to produce an empty result");
        std::process::exit(2);
    }
    let verbose = std::env::var("VERBOSE").map(|v| v == "1").unwrap_or(false);
    for x in list {
        let id = x["id"].as_str().unwrap();
        let native = x["native"].as_str().unwrap();
        let input = String::from_utf8(unhex(x["input_hex"].as_str().unwrap())).unwrap();
        match regex::Regex::new(native) {
            Err(e) => {
                if verbose {
                    eprintln!("{}: {}", id, e);
                }
                println!("{}|compile_error|0", id);
            }
            Ok(re) => {
                let t = Instant::now();
                let m = re.is_match(&input);
                let e = t.elapsed().as_nanos();
                println!("{}|{}|{}", id, if m { "match" } else { "nomatch" }, e);
            }
        }
    }
}
