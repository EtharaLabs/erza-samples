//! Reads cases from stdin, one per line: id, hex(pattern), flags, hex(input), entry.
//! Writes one result line per case to file descriptor 3, never stdout, so anything the library
//! under test prints cannot mix with results: id, then E (syntax error), N (no match), B (budget exhausted),
//! P (panic), or M followed by the match range and every capture group (start:end or -).
//! Ranges are UTF-8 byte offsets for the utf8 entry and UTF-16 code-unit offsets for utf16 and ucs2.
use std::io::{BufRead, Write};

const BUDGET: u64 = 1_000_000;

fn unhex(s: &str) -> String {
    let bytes: Vec<u8> = (0..s.len()).step_by(2).map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap()).collect();
    String::from_utf8(bytes).unwrap()
}

fn fmt_match(range: std::ops::Range<usize>, groups: &[Option<std::ops::Range<usize>>]) -> String {
    let mut out = format!("M {}:{}", range.start, range.end);
    for g in groups {
        match g {
            Some(r) => out.push_str(&format!(" {}:{}", r.start, r.end)),
            None => out.push_str(" -"),
        }
    }
    out
}

fn run(pattern: &str, flags: &str, input: &str, entry: &str) -> String {
    let re = match regress::Regex::with_flags(pattern, flags) {
        Ok(re) => re,
        Err(_) => return "E".to_string(),
    };
    match entry {
        "compile" => "C".to_string(),
        e if e.starts_with("budget:") => match re.find_from_budgeted(input, 0, e[7..].parse().unwrap()) {
            regress::BudgetedMatch::Match(m) => fmt_match(m.range(), &m.captures),
            regress::BudgetedMatch::NoMatch => "N".to_string(),
            regress::BudgetedMatch::BudgetExhausted => "B".to_string(),
        },
        "utf8" => match re.find_from_budgeted(input, 0, BUDGET) {
            regress::BudgetedMatch::Match(m) => fmt_match(m.range(), &m.captures),
            regress::BudgetedMatch::NoMatch => "N".to_string(),
            regress::BudgetedMatch::BudgetExhausted => "B".to_string(),
        },
        "utf16" | "ucs2" => {
            let units: Vec<u16> = input.encode_utf16().collect();
            let found = if entry == "utf16" { re.find_from_utf16(&units, 0).next() } else { re.find_from_ucs2(&units, 0).next() };
            match found {
                Some(m) => fmt_match(m.range(), &m.captures),
                None => "N".to_string(),
            }
        }
        _ => "X".to_string(),
    }
}

fn main() {
    let stdin = std::io::stdin();
    // test.sh opens descriptor 3 on the result file before dropping privilege; it is used as inherited,
    // never reopened by path, because the file belongs to root and this process runs as the sandbox user.
    // SAFETY: descriptor 3 is open for writing for the whole process and nothing else in the harness owns it.
    let mut out = unsafe { <std::fs::File as std::os::fd::FromRawFd>::from_raw_fd(3) };
    for line in stdin.lock().lines() {
        let line = line.unwrap();
        let f: Vec<&str> = line.split('\t').collect();
        if f.len() != 5 {
            continue;
        }
        let (pattern, flags, input, entry) = (unhex(f[1]), f[2].to_string(), unhex(f[3]), f[4].to_string());
        let result = std::panic::catch_unwind(|| run(&pattern, &flags, &input, &entry)).unwrap_or_else(|_| "P".to_string());
        writeln!(out, "{}\t{}", f[0], result).unwrap();
        out.flush().unwrap();
    }
}
