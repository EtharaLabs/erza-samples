use crate::{BudgetedMatch, Flags, Regex};

fn check(pattern: &str, flags: &str, text: &str, expected: Option<(usize, usize)>) {
    for no_opt in [false, true] {
        let mut f = Flags::from(flags);
        f.no_opt = no_opt;
        let re = Regex::with_flags(pattern, f).unwrap();
        let result = match re.find_from_budgeted(text, 0, 1_000_000) {
            BudgetedMatch::Match(m) => Some((m.start(), m.end())),
            BudgetedMatch::NoMatch => None,
            BudgetedMatch::BudgetExhausted => panic!("budget: {pattern}"),
        };
        assert_eq!(result, expected, "{pattern}/{flags} on {text:?}; no_opt={no_opt}");
    }
}

#[test]
fn spec_matching() {
    for (p, f, t, e) in [
        (r"^(?:(?<x>a)|(?<x>b))\k<x>$", "u", "a", None),
        (r"^(?:(?<x>a)|(?<x>b))\k<x>$", "u", "bb", Some((0,2))),
        (r"\u{61}", "", "a", None),
        (r"\u{61}", "", &"u".repeat(61), Some((0,61))),
        (r"[a&&A]", "iv", "A", Some((0,1))),
        (r"[a--A]", "iv", "a", None),
        (r"[\q{ab}&&\q{AB}]", "iv", "Ab", Some((0,2))),
        (r"[\q{a}&&a]", "v", "a", Some((0,1))),
        (r"[a&&\q{a}]", "v", "a", Some((0,1))),
        (r"[a&b]", "v", "a", Some((0,1))),
        (r"[!#]", "v", "!", Some((0,1))),
        (r"[\q{}]", "v", "", Some((0,0))),
        (r"[\q{|ab}a]", "v", "a", Some((0,1))),
        (r"[\q{ab|a}]b", "v", "ab", Some((0,2))),
        (r"[\b]", "v", "\u{8}", Some((0,1))),
        (r"[\q{\b}]", "v", "\u{8}", Some((0,1))),
        (r"[^\q{ab}&&a]", "v", "b", Some((0,1))),
        (r"[a--\q{ab}]", "v", "a", Some((0,1))),
        (r"\P{Lowercase_Letter}", "iu", "a", Some((0,1))),
        (r"\P{Lowercase_Letter}", "iv", "a", None),
        (r"[\P{Lowercase_Letter}]", "iv", "A", None),
        (r"[^a]", "iv", "A", None),
        (r"[[^a]&&A]", "iv", "A", None),
        (r"\w", "iv", "K", Some((0,3))),
        (r"\W", "iv", "K", None),
        (r"[\W]", "iu", "K", None),
        (r"[\W]", "iv", "K", None),
        (r"\bK\b", "iv", "K", Some((0,3))),
        (r"(k)\1", "iv", "kK", Some((0,4))),
        (r"\u{1f600}", "v", "😀", Some((0,4))),
        (r"(?<=([\q{ab|abc}]))x", "v", "abcx", Some((3,4))),
        (r"(?i-:a)", "u", "A", Some((0,1))),
        (r"(aa|aabaac|ba|b|c)*", "u", "aabaac", Some((0,4))),
        (r"^(?:(?:(?:(a)){0,3}){1,2}?){1,2}?$", "u", "ab", None),
        (r"\uD800\u0061", "u", "a", None),
        (r"^(?:(a|ab){1,2}){2}c$", "u", "ababc", Some((0,5))),
    ] { check(p,f,t,e); }
}

#[test]
fn spec_syntax() {
    for (p, f) in [
        (r"\b+", ""), (r"\B?", "u"), (r"(?=a)*", "v"),
        (r"\a", "v"), (r"\1", "v"), (r"{", "v"),
        (r"(?:(?<x>a)|b)(?:c|(?<x>d))", "u"),
        (r"(?<x>a)(?<x>b)", "u"),
        (r"[^\q{ab}]", "v"), (r"[^\q{}]", "v"),
        (r"[^\q{ab}--\q{ab}]", "v"),
        (r"[a&&&]", "v"), (r"[a&&b&&&]", "v"),
        (r"[a&&b--c]", "v"), (r"[ab&&c]", "v"),
        (r"[!!]", "v"), (r"[\q{[}]", "v"),
        (r"(?i-i:a)", "u"), (r"(?<a\u003e>x)", "u"),
        (r"\u{+61}", "u"),
        (r"a{999999999999999999999999999999,888888888888888888888888888888}", "u"),
    ] { assert!(Regex::with_flags(p,f).is_err(), "accepted: {p}/{f}"); }
    for p in [r"(?:(?<x>a)|(?:(?<x>b)|(?<x>c)))", r"(?<\u{61}>a)\k<a>"] {
        assert!(Regex::new(p).is_ok(), "rejected: {p}");
    }
}

#[test]
fn spec_captures() {
    let re = Regex::with_flags(r"^(?:(?<x>a)|(?<x>b))\k<x>$", "u").unwrap();
    let BudgetedMatch::Match(m) = re.find_from_budgeted("bb",0,1_000_000) else { panic!() };
    assert_eq!(m.captures, vec![None, Some(0..1)]);
    assert_eq!(m.named_group("x"), Some(0..1));
    let re = Regex::new(r"(z)((a+)?(b+)?(c))*").unwrap();
    let m = re.find("zaacbbbcac").unwrap();
    assert_eq!(m.captures, vec![Some(0..1),Some(8..10),Some(8..9),None,Some(9..10)]);
}

#[test]
fn string_set_lookbehind_captures() {
    let re = Regex::with_flags(r"(?<=([\q{ab|abc}]))x", "v").unwrap();
    let m = re.find("abcx").unwrap();
    assert_eq!(m.captures, vec![Some(0..3)]);
}

#[cfg(feature = "utf16")]
#[test]
fn surrogate_escape_rollback() {
    let re = Regex::with_flags(r"\uD800\u0061", "u").unwrap();
    assert_eq!(re.find_from_utf16(&[0xD800,0x61],0).next().unwrap().range(),0..2);
}
