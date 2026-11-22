// Bench runner, Rust (the `regex` crate, default limits). One case per process so the peak resident memory belongs to the case.
// Input: a JSON file {native, input_hex, compiles, matches}. Output, one line: compile_ns_min|match_ns_median|vmhwm_kb|0   (vmhwm = the process peak, from /proc/self/status).
// Usage: cargo run -q --release --locked -- case.json
use serde_json::Value;
use std::time::Instant;

fn unhex(s: &str) -> Vec<u8> {
    (0..s.len()).step_by(2).map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap()).collect()
}

fn status(key: &str) -> i64 {
    let k = format!("{}:", key);
    std::fs::read_to_string("/proc/self/status").unwrap_or_default().lines().find(|l| l.starts_with(&k)).and_then(|l| l.split_whitespace().nth(1).and_then(|s| s.parse().ok())).unwrap_or(0)
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let x: Value = serde_json::from_str(&std::fs::read_to_string(&a[1]).unwrap()).unwrap();
    let native = x["native"].as_str().unwrap();
    let v = String::from_utf8(unhex(x["input_hex"].as_str().unwrap())).unwrap();
    let (compiles, matches) = (x["compiles"].as_u64().unwrap_or(0), x["matches"].as_u64().unwrap_or(0));
    if compiles < 1 || matches < 1 {
        eprintln!("bad case: refusing to produce a result");
        std::process::exit(2);
    }
    let _ = regex::Regex::new("a").unwrap().is_match(&v); // warm up
    let rss0 = status("VmRSS");
    if std::fs::write("/proc/self/clear_refs", "5").is_err() {
        eprintln!("INCOMPLETE: /proc/self/clear_refs is not writable");
        std::process::exit(4);
    }
    let mut re = None;
    let mut cmin = u128::MAX;
    for _ in 0..compiles {
        let t = Instant::now();
        let r = regex::Regex::new(native);
        let e = t.elapsed().as_nanos();
        match r {
            Ok(r) => re = Some(r),
            Err(e) => {
                eprintln!("compile error: {}", e);
                std::process::exit(3);
            }
        }
        cmin = cmin.min(e);
    }
    let re = re.unwrap();
    let mut ms: Vec<u128> = vec![];
    for _ in 0..matches {
        let t = Instant::now();
        re.is_match(&v);
        ms.push(t.elapsed().as_nanos());
    }
    ms.sort();
    println!("{}|{}|{}|0", cmin, ms[ms.len() / 2], (status("VmHWM") - rss0).max(0));
}
