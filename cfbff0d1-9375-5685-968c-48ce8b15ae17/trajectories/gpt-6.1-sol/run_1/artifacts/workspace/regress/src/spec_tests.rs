use crate::{BudgetedMatch, Flags, Regex};

fn check(pattern: &str, flags: &str, text: &str, expected: Option<(usize, usize)>, captures: &[Option<(usize, usize)>]) {
    for no_opt in [false, true] {
    let mut options = Flags::from(flags);
    options.no_opt = no_opt;
    let re = Regex::with_flags(pattern, options).unwrap();
    match (re.find_from_budgeted(text, 0, 1_000_000), expected) {
        (BudgetedMatch::NoMatch, None) => {},
        (BudgetedMatch::Match(m), Some((start, end))) => {
            assert_eq!(m.range(), start..end, "{pattern} / {flags} on {text:?}");
            let expected: Vec<_> = captures.iter().map(|r| r.map(|(a,b)| a..b)).collect();
            assert_eq!(m.captures, expected, "{pattern} / {flags} on {text:?}");
        },
        (_, _) => panic!("{pattern} / {flags} on {text:?}: unexpected match result"),
    }
    }
}

#[test]
fn spec_named_groups() {
    check(r"^(?:(?<x>a)|(?<x>b))\k<x>$", "", "b", None, &[]);
    check(r"^(?:(?<x>a)|(?<x>b))\k<x>$", "", "bb", Some((0,2)), &[None,Some((0,1))]);
    let m = Regex::new(r"(?<=(?<a>a)(?<b>b))(?<c>c)").unwrap().find("abc").unwrap();
    assert_eq!(m.named_group("a"), Some(0..1));
    assert_eq!(m.named_group("b"), Some(1..2));
    let m = Regex::new(r"(?<x>a)|(?<x>b)").unwrap().find("b").unwrap();
    assert_eq!(m.named_group("x"), Some(0..1));
    assert!(Regex::new(r"(?:(?<x>a)|b)(?:c|(?<x>d))").is_err());
    assert!(Regex::new(r"(?:(?<x>a)|(?:(?<x>b)|c))").is_ok());
}

#[test]
fn spec_case_and_sets() {
    for flags in ["ui", "vi"] {
        check("k", flags, "K", Some((0,3)), &[]);
        check(r"\b\w\b", flags, "ſ", Some((0,2)), &[]);
        check(r"[\W]", flags, "K", None, &[]);
        check(r"(k)\1", flags, "kK", Some((0,4)), &[Some((0,1))]);
    }
    check(r"[a--A]", "vi", "a", None, &[]);
    check(r"[a&&A]", "vi", "A", Some((0,1)), &[]);
    check(r"[^a]", "vi", "A", None, &[]);
    check(r"\P{Lowercase_Letter}", "vi", "a", None, &[]);
    check(r"\P{Lowercase_Letter}", "ui", "a", Some((0,1)), &[]);
    check(r"[\q{ab}&&\q{AB}]", "vi", "AB", Some((0,2)), &[]);
    check(r"[\q{a}&&a]", "v", "a", Some((0,1)), &[]);
    check(r"[\q{|a}]", "v", "a", Some((0,1)), &[]);
    check(r"[\q{}]", "v", "x", Some((0,0)), &[]);
    check(r"[\q{ab|a}]b", "v", "ab", Some((0,2)), &[]);
    check(r"[^\q{a}]", "v", "b", Some((0,1)), &[]);
    check(r"\u{61}", "", "a", None, &[]);
    check(r"^\u{61}$", "", &"u".repeat(61), Some((0,61)), &[]);
    check(r"[a&]", "v", "a", Some((0,1)), &[]);
    check(r"[!#]", "v", "#", Some((0,1)), &[]);
    check(r"[\b]", "v", "\x08", Some((0,1)), &[]);
    check(r"(?<=[\q{ab}])c", "v", "abc", Some((2,3)), &[]);
    assert!(Regex::with_flags(r"[^\q{ab}&&a]", "v").is_ok());
    for pattern in [r"[^\q{}]", r"[^\q{ab}]", r"[^\q{ab}--\q{ab}]", r"[ab&&c]", r"[a&&&]", r"[a--b&&c]", r"\a", r"(?=a)*", r"\b+"] {
        assert!(Regex::with_flags(pattern, "v").is_err(), "{pattern}");
    }
    assert!(Regex::with_flags(r"\u{+61}", "u").is_err());
    assert!(Regex::new(r"(?<a\u003ex)").is_err());
    assert!(Regex::new("a{99999999999999999999999,99999999999999999999998}").is_err());
    check(r"[\uD800\u0061]", "u", "a", Some((0,1)), &[]);
    assert!(Regex::with_flags(r"\u+abc", "u").is_err());
    assert!(Regex::with_flags("a", "uv").is_err());
    check(r"(?<=[\q{ab}])c", "vi", "ABc", Some((2,3)), &[]);
}

#[test]
fn spec_quantifiers() {
    check(r"^(?:(?:a?)*)*ab$", "", "aaab", Some((0,4)), &[]);
    check(r"\p{RGI_Emoji}", "v", "👨‍👩‍👧", Some((0,"👨‍👩‍👧".len())), &[]);
    check(r"^(?:(a+)?b)+$", "", "ababb", Some((0,5)), &[None]);
    check(r"(aa|aabaac|ba|b|c)*", "", "aabaac", Some((0,4)), &[Some((2,4))]);
    check(r"(a*)*", "", "b", Some((0,0)), &[None]);
    check(r"^(a{1,2}?){2}a$", "", "aaaa", Some((0,4)), &[Some((1,3))]);
    check(r"^(a{1,2}){2}a$", "", "aaaa", Some((0,4)), &[Some((2,3))]);
}
