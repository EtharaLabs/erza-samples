use crate::{BudgetedMatch, Flags, Regex};

fn check(pattern: &str, flags: &str, input: &str, expected: Option<(usize, usize)>, captures: &[Option<(usize, usize)>]) {
    for no_opt in [false, true] {
        let mut f = Flags::from(flags);
        f.no_opt = no_opt;
        let re = Regex::with_flags(pattern, f).unwrap();
        match (re.find_from_budgeted(input, 0, 1_000_000), expected) {
            (BudgetedMatch::Match(m), Some((a,b))) => {
                assert_eq!(m.range(), a..b, "{pattern:?} {flags} {input:?} opt={}", !no_opt);
                for (i, expected) in captures.iter().enumerate() {
                    assert_eq!(m.group(i+1), expected.map(|(a,b)| a..b), "{pattern:?} capture {}", i+1);
                }
            }
            (BudgetedMatch::NoMatch, None) => (),
            (actual, expected) => panic!("{pattern:?} {flags} {input:?}: {}, expected {expected:?}", match actual { BudgetedMatch::Match(m) => format!("{:?}",m.range()), BudgetedMatch::NoMatch => "no match".into(), BudgetedMatch::BudgetExhausted => "budget exhausted".into() }),
        }
    }
}

#[test]
fn duplicate_groups_and_names() {
    check(r"(?:(?<x>a)|(?<x>b))\k<x>", "", "b", None, &[]);
    check(r"(?:(?<x>a)|(?<x>b))\k<x>", "", "bb", Some((0,2)), &[None,Some((0,1))]);
    check(r"(?:(?<x>a)|(?<x>b))+\k<x>", "", "abb", Some((0,3)), &[None,Some((1,2))]);
    let m = Regex::new(r"(?<x>a)|(?<x>b)").unwrap().find("b").unwrap();
    assert_eq!(m.named_group("x"), Some(0..1));
    assert_eq!(m.named_groups().collect::<Vec<_>>(), vec![("x",Some(0..1))]);
    for p in [r"(?:(?<x>a)|b)(?:c|(?<x>d))", r"(?<x>a)(?<x>b)", r"(?<x\u003e>a)"] {
        assert!(Regex::new(p).is_err(), "{p}");
    }
    check(r"(?<\u{61}>a)\k<a>", "", "aa", Some((0,2)), &[Some((0,1))]);
}

#[test]
fn unicode_and_sets() {
    for flags in ["iu", "iv"] {
        check("^[a-z]+$", flags, "Kſ", Some((0,5)), &[]);
        check(r"^(K)\1$", flags, "Kk", Some((0,4)), &[Some((0,3))]);
        check(r"^[\W]$", flags, "K", None, &[]);
        check(r"^\W$", flags, "ſ", None, &[]);
    }
    for (p, input, expected) in [
        (r"[a&&A]", "a", Some((0,1))),
        (r"[a--A]", "a", None),
        (r"[\q{a}&&a]", "a", Some((0,1))),
        (r"[\q{ab}&&\q{AB}]", "Ab", Some((0,2))),
        (r"[a&b]", "a", Some((0,1))),
        (r"[\b]", "\x08", Some((0,1))),
        (r"[\q{}]", "", Some((0,0))),
        (r"[\q{|ab}a]", "ab", Some((0,2))),
        (r"[\q{|ab}a]", "a", Some((0,1))),
        (r"[^\q{ab}&&a]", "b", Some((0,1))),
        (r"[\P{Lowercase_Letter}]", "a", None),
        (r"\P{Lowercase_Letter}", "a", None),
        (r"(?<=[\q{abK}])x", "abkx", Some((3,4))),
    ] { check(p, "iv", input, expected, &[]); }
    check(r"\P{Lowercase_Letter}", "iu", "a", Some((0,1)), &[]);
    check(r"\p{RGI_Emoji}", "v", "👩‍💻", Some((0,11)), &[]);
    check(r"[\p{RGI_Emoji}]", "v", "👩‍💻", Some((0,11)), &[]);
    for p in [r"[^\q{}]", r"[^\q{ab}]", r"[^\q{ab}--\q{ab}]", r"[\q{[}]", r"[a&&&]", r"[a&&]", r"[a&&b--c]"] {
        assert!(Regex::with_flags(p,"v").is_err(), "{p}");
    }
    assert!(Regex::with_flags("a", "uv").is_err());
    assert!(Regex::with_flags(r"\a", "v").is_err());
    check(r"[!#]", "v", "!", Some((0,1)), &[]);
}

#[test]
fn quantifiers_and_grammar() {
    check(r"(a|(b))+", "", "aba", Some((0,3)), &[Some((2,3)),None]);
    check(r"(a*)*", "", "a", Some((0,1)), &[Some((0,1))]);
    check(r"(a*)+", "", "", Some((0,0)), &[Some((0,0))]);
    check(r"^(?:(a|ab)*?b)*?c$", "", "abbc", Some((0,4)), &[None]);
    for p in [r"a{999999999999999999999,888888888888888888888}", r"\u{+61}", r"\u+061"] {
        assert!(Regex::with_flags(p, "u").is_err(), "{p}");
    }
    check(r"a{3}1", "", "aaa1", Some((0,4)), &[]);
    check(r"\u{61}", "", &"u".repeat(61), Some((0,61)), &[]);
}

// A small direct implementation of CompileTerm / RepeatMatcher, independent
// of bytecode lowering and optimization, for generated nested repetitions.
#[derive(Clone)]
enum Atom { Lit(char), Empty, Alt(Box<Atom>, Box<Atom>), Cat(Box<Atom>,Box<Atom>), Cap(Box<Atom>), Rep(Box<Atom>,usize,Option<usize>,bool) }
use Atom::*;
impl Atom {
    fn pattern(&self) -> String {
        match self {
            Lit(c) => c.to_string(), Empty => String::new(),
            Alt(a,b) => format!("(?:{}|{})",a.pattern(),b.pattern()),
            Cat(a,b) => format!("{}{}",a.pattern(),b.pattern()),
            Cap(a) => format!("({})",a.pattern()),
            Rep(a,min,max,greedy) => format!("(?:{}){{{},{}}}{}",a.pattern(),min,max.map(|n| n.to_string()).unwrap_or_default(),if *greedy {""} else {"?"}),
        }
    }
    fn has_cap(&self) -> bool {
        match self { Cap(_) => true, Alt(a,b)|Cat(a,b) => a.has_cap()||b.has_cap(), Rep(a,..) => a.has_cap(), _ => false }
    }
    fn eval(&self, input: &[char], pos: usize, cap: Option<(usize,usize)>) -> Vec<(usize,Option<(usize,usize)>)> {
        match self {
            Empty => vec![(pos,cap)],
            Lit(c) => if input.get(pos) == Some(c) {vec![(pos+1,cap)]} else {vec![]},
            Alt(a,b) => { let mut r=a.eval(input,pos,cap); r.extend(b.eval(input,pos,cap)); r },
            Cat(a,b) => a.eval(input,pos,cap).into_iter().flat_map(|(p,c)|b.eval(input,p,c)).collect(),
            Cap(a) => a.eval(input,pos,cap).into_iter().map(|(p,_)|(p,Some((pos,p)))).collect(),
            Rep(a,min,max,greedy) => {
                if *max == Some(0) { return vec![(pos,cap)]; }
                let mut r = vec![];
                if *min == 0 && !greedy { r.push((pos,cap)); }
                for (p,c) in a.eval(input,pos,if a.has_cap() {None} else {cap}) {
                    if *min == 0 && p == pos {continue;}
                    r.extend(Rep(a.clone(),min.saturating_sub(1),max.map(|n|n-1),*greedy).eval(input,p,c));
                }
                if *min == 0 && *greedy { r.push((pos,cap)); }
                r
            }
        }
    }
}
#[test]
fn generated_repeat_matcher() {
    let a=Box::new(Lit('a')); let b=Box::new(Lit('b'));
    let bodies=vec![Empty,Lit('a'),Alt(a.clone(),b.clone()),Alt(a.clone(),Box::new(Cat(a.clone(),b.clone()))),Alt(Box::new(Empty),a.clone()),Cap(Box::new(Alt(a.clone(),Box::new(Cat(a.clone(),b.clone())))))];
    for body in bodies {
        for (min,max) in [(0,None),(1,None),(2,Some(3)),(0,Some(2))] {
            for greedy in [false,true] {
                for outer_greedy in [false,true] {
                    let atom=Cat(Box::new(Rep(Box::new(Cat(Box::new(Rep(Box::new(body.clone()),min,max,greedy)),b.clone())),0,None,outer_greedy)),a.clone());
                    let pattern=format!("^{}$",atom.pattern());
                    for len in 0..=5 {
                        for bits in 0..1<<len {
                            let input: String=(0..len).map(|n|if bits & (1<<n)==0 {'a'} else {'b'}).collect();
                            let expected=atom.eval(&input.chars().collect::<Vec<_>>(),0,None).into_iter().find(|(p,_)|*p==len);
                            let caps = [expected.and_then(|(_,c)|c)];
                            check(&pattern,"",&input,expected.map(|(p,_)|(0,p)),if atom.has_cap() { &caps } else { &[] });
                        }
                    }
                }
            }
        }
    }
}

#[test]
fn budget_exhaustion_is_not_assertion_failure() {
    let re = Regex::new(r"(?!(?:a|aa)+b)a").unwrap();
    assert!(matches!(re.find_from_budgeted(&"a".repeat(30),0,10),BudgetedMatch::BudgetExhausted));
}

#[test]
fn set_algebra_against_finite_sets() {
    let operands: [(&str, &[&str]); 7] = [
        ("a", &["a"]), ("A", &["A"]), (r"\q{a|ab|}", &["a","ab",""]),
        (r"\q{AB|b}", &["AB","b"]), ("[a-b]", &["a","b"]),
        ("[aA]", &["a","A"]), (r"\q{b|}", &["b",""]),
    ];
    for (left,ls) in operands {
        for (right,rs) in operands {
            for op in ["&&","--",""] {
                for icase in [false,true] {
                    let canon=|s: &&str| if icase {s.to_lowercase()} else {s.to_string()};
                    let l: Vec<String>=ls.iter().map(canon).collect();
                    let r: Vec<String>=rs.iter().map(canon).collect();
                    let mut expected: Vec<String>=match op {
                        "&&" => l.into_iter().filter(|s|r.contains(s)).collect(),
                        "--" => l.into_iter().filter(|s|!r.contains(s)).collect(),
                        _ => l.into_iter().chain(r).collect(),
                    };
                    expected.sort_by(|a,b|b.len().cmp(&a.len()));
                    for input in ["", "a", "A", "b", "ab", "AB", "aba", "c"] {
                        let folded=if icase {input.to_lowercase()} else {input.to_string()};
                        let result=expected.iter().find(|s|folded.starts_with(s.as_str())).map(|s|(0,s.len()));
                        check(&format!("^[{left}{op}{right}]"),if icase {"iv"} else {"v"},input,result,&[]);
                    }
                }
            }
        }
    }
}

#[cfg(feature = "utf16")]
#[test]
fn unicode_escape_surrogate_rollback() {
    let re = Regex::with_flags(r"\uD800\u0061", "u").unwrap();
    let input = [0xD800,0x61];
    assert_eq!(re.find_from_utf16(&input,0).next().unwrap().range(),0..2);
}
