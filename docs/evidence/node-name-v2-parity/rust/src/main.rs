// The node-name verdict of version 2 as Rust (the `regex` crate) applies it (reference validation, not a Forms integration). It applies the rule it is given (rule.json,
// exported from the grammar file by check_name_vectors.py) to the names it is given (names.json, exported from the vectors): a minimum length in characters, a pattern
// that must match and a pattern that must NOT match. The gate builds and runs it on every run: cargo run -q --locked -- names.json rule.json
// Output: one line `id|accept` or `id|refuse` per name.
use serde_json::Value;

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let names: Value = serde_json::from_str(&std::fs::read_to_string(&a[1]).unwrap()).unwrap();
    let rule: Value = serde_json::from_str(&std::fs::read_to_string(&a[2]).unwrap()).unwrap();
    let pattern = rule["pattern"].as_str().unwrap_or("");
    let not_pattern = rule["not_pattern"].as_str().unwrap_or("");
    let min = rule["min_length"].as_u64().unwrap_or(0) as usize;
    let list = names.as_array().unwrap();
    if pattern.is_empty() || not_pattern.is_empty() || list.is_empty() {
        eprintln!("an empty rule or no names: refusing to produce an empty result");
        std::process::exit(2);
    }
    let pat = regex::Regex::new(pattern).unwrap();
    let not = regex::Regex::new(not_pattern).unwrap();
    for n in list {
        let id = n["id"].as_str().unwrap();
        let name = n["name"].as_str().unwrap();
        let ok = name.chars().count() >= min && pat.is_match(name) && !not.is_match(name);
        println!("{}|{}", id, if ok { "accept" } else { "refuse" });
    }
}
