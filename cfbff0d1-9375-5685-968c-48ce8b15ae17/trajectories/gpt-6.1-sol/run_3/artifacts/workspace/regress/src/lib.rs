/*!

# regress - REGex in Rust with EcmaScript Syntax

This crate provides a regular expression engine which targets EcmaScript (aka JavaScript) regular expression syntax.

# Example: test if a string contains a match

```rust
use regress::Regex;
let re = Regex::new(r"\d{4}").unwrap();
let matched = re.find("2020-20-05").is_some();
assert!(matched);
```

# Example: iterating over matches

Here we use a backreference to find doubled characters:

```rust
use regress::Regex;
let re = Regex::new(r"(\w)\1").unwrap();
let text = "Frankly, Miss Piggy, I don't give a hoot!";
for m in re.find_iter(text) {
    println!("{}", &text[m.range()])
}
// Output: ss
// Output: gg
// Output: oo

```

# Example: using capture groups

Capture groups are available in the `Match` object produced by a successful match.
A capture group is a range of byte indexes into the original string.

```rust
use regress::Regex;
let re = Regex::new(r"(\d{4})").unwrap();
let text = "Today is 2020-20-05";
let m = re.find(text).unwrap();
let group = m.group(1).unwrap();
println!("Year: {}", &text[group]);
// Output: Year: 2020
```

# Example: using with Pattern trait (nightly only)

When the `pattern` feature is enabled and using nightly Rust, `Regex` can be used with standard string methods:

```rust,ignore
#![feature(pattern)]
use regress::Regex;
let re = Regex::new(r"\d+").unwrap();
let text = "abc123def456";

// Use with str methods
assert_eq!(text.find(&re), Some(3));
assert!(text.contains(&re));
let parts: Vec<&str> = text.split(&re).collect();
assert_eq!(parts, vec!["abc", "def", ""]);
```

# Example: escaping strings for literal matching

Use the `escape` function to escape special regex characters in a string:

```rust
use regress::{escape, Regex};
let user_input = "How much $ do you have? (in dollars)";
let escaped = escape(user_input);
let re = Regex::new(&escaped).unwrap();
assert!(re.find(user_input).is_some());
```

# Supported Syntax

regress targets ES 2018 syntax. You can refer to the many resources about JavaScript regex syntax.

There are some features which have yet to be implemented:

- Named character classes liks `[[:alpha:]]`
- Unicode property escapes like `\p{Sc}`

Note the parser assumes the `u` (Unicode) flag, as the non-Unicode path is tied to JS's UCS-2 string encoding and the semantics cannot be usefully expressed in Rust.

# Unicode remarks

regress supports Unicode case folding. For example:

```rust
use regress::Regex;
let re = Regex::with_flags("\u{00B5}", "i").unwrap();
assert!(re.find("\u{03BC}").is_some());
```

Here the U+00B5 (micro sign) was case-insensitively matched against U+03BC (small letter mu).

regress does NOT perform normalization. For example,  e-with-accute-accent can be precomposed or decomposed, and these are treated as not equivalent:

```rust
use regress::{Regex, Flags};
let re = Regex::new("\u{00E9}").unwrap();
assert!(re.find("\u{0065}\u{0301}").is_none());
```

This agrees with JavaScript semantics. Perform any required normalization before regex matching.

## Ascii matching

regress has an "ASCII mode" which treats each 8-bit quantity as a separate character.
This may provide improved performance if you do not need Unicode semantics, because it can avoid decoding UTF-8 and has simpler (ASCII-only) case-folding.

Example:

```rust
use regress::Regex;
let re = Regex::with_flags("BC", "i").unwrap();
assert!(re.find("abcd").is_some());
```

# Comparison to regex crate

regress supports features (required by the EcmaScript spec) that regex does not, including backreferences and zero-width lookaround assertions.
However the regex crate provides linear-time matching guarantees, while regress does not. This difference is due
to the architecture: regex uses finite automata while regress uses "classical backtracking."


# Architecture

regress has a parser, intermediate representation, optimizer which acts on the IR, bytecode emitter, and two bytecode interpreters, referred to as "backends".

The major interpreter is the "classical backtracking" which uses an explicit backtracking stack, similar to JS implementations.

# Crate features

- **utf16**. When enabled, additional APIs are made available that allow matching text formatted in UTF-16 and UCS-2 (`&[u16]`) without going through a conversion to and from UTF-8 (`&str`) first. This is particularly useful when interacting with and/or (re)implementing existing systems that use those encodings, such as JavaScript, Windows, and the JVM.

- **pattern**. When enabled (nightly only), implements the `std::str::pattern::Pattern` trait for `Regex`, allowing it to be used with standard string methods like `str::find`, `str::contains`, `str::split`, etc.

*/

#![cfg_attr(not(feature = "std"), no_std)]
#![cfg_attr(feature = "pattern", feature(pattern))]
#![warn(clippy::all)]
#![allow(
    clippy::upper_case_acronyms,
    clippy::match_like_matches_macro,
    clippy::uninlined_format_args,
    clippy::collapsible_if
)]
// Clippy's manual_range_contains suggestion produces worse codegen.
#![allow(clippy::manual_range_contains)]

#[cfg(all(not(feature = "std"), not(feature = "alloc")))]
compile_error!(
    "`regress` requires the `alloc` feature when building without `std`; use `--no-default-features --features alloc`."
);

#[cfg(not(feature = "std"))]
#[macro_use]
extern crate alloc;

pub use crate::api::*;

#[macro_use]
mod util;

mod api;
mod bytesearch;
mod charclasses;
mod classicalbacktrack;
mod codepointset;
mod cursor;
mod emit;
mod exec;
mod indexing;
mod insn;
mod ir;
// UTF-16 never matches against bytes, so the byte-oriented literal lowering is
// UTF-8 only. See `emit_code_point_sequence` for the UTF-16 path.
#[cfg(not(feature = "utf16"))]
mod literal;
mod matchers;
mod optimizer;
mod parse;
mod position;
mod scm;
mod startpredicate;
mod types;
mod unicode;
mod unicodetables;


#[cfg(test)]
mod spec_regressions {
    use crate::{BudgetedMatch, Regex};
    fn check(pattern: &str, flags: &str, input: &str, expected: Option<(usize, usize)>) {
        for no_opt in [false, true] {
            let mut options = crate::Flags::from(flags);
            options.no_opt = no_opt;
            let re = Regex::with_flags(pattern, options).unwrap();
            match (re.find_from_budgeted(input, 0, 1_000_000), expected) {
                (BudgetedMatch::Match(m), Some((a, b))) => assert_eq!(m.range(), a..b, "{pattern} / {flags}"),
                (BudgetedMatch::NoMatch, None) => (),
                _ => panic!("unexpected result for {pattern} / {flags} on {input:?}"),
            }
        }
    }
    #[test]
    fn named_references() {
        check(r"^(?:(?<x>a)|(?<x>b))\k<x>$", "", "aa", Some((0, 2)));
        check(r"^(?:(?<x>a)|(?<x>b))\k<x>$", "", "a", None);
        assert!(Regex::new(r"(?:(?<x>a)|b)(?:c|(?<x>d))").is_err());
        let re = Regex::new(r"(?:(?<x>a)|(?<x>b))+").unwrap();
        let m = re.find("ab").unwrap();
        assert_eq!(m.group(1), None);
        assert_eq!(m.group(2), Some(1..2));
        assert_eq!(m.named_group("x"), Some(1..2));
        check(r"^(a|a\1)b$", "", "aab", None);
    }
    #[test]
    fn class_sets() {
        check(r"(?<=[\q{ab}])c", "v", "abc", Some((2, 3)));
        check(r"[a&&A]", "iv", "a", Some((0, 1)));
        check(r"[a--A]", "iv", "a", None);
        check(r"[\q{a|}]", "v", "z", Some((0, 0)));
        check(r"[a\q{}]", "v", "a", Some((0, 1)));
        check(r"[a&]", "v", "a", Some((0, 1)));
        check(r"[\b]", "v", "\x08", Some((0, 1)));
        check(r"[!#]", "v", "!", Some((0, 1)));
        check(r"[^\q{ab}&&a]", "v", "x", Some((0, 1)));
        for p in [r"[^\q{ab}]", r"[^\q{}]", r"[a&&&b]", r"[a&&b--c]", r"[a-b&&c]", r"[\q{[}]", r"[\q{]}]", r"\a"] {
            assert!(Regex::with_flags(p, "v").is_err(), "{p}");
        }
    }
    #[test]
    fn unicode_modes_and_escapes() {
        for flag in ["iu", "iv"] {
            check("k", flag, "K", Some((0, 3)));
            check(r"[\W]", flag, "K", None);
        }
        check(r"\P{Lowercase_Letter}", "iv", "a", None);
        check(r"\P{Lowercase_Letter}", "iu", "a", Some((0, 1)));
        check(r"\u{61}", "", "u".repeat(61).as_str(), Some((0, 61)));
        for p in [r"\u{+61}", r"\u+061", r"(?<x\u003E>a)"] {
            assert!(Regex::with_flags(p,"u").is_err());
        }
        assert!(Regex::new("a{99999999999999999999999999999,88888888888888888888888888888}").is_err());
        assert!(Regex::with_flags("a", "uv").is_err());
        check(r"[\q{Ab}&&\q{aB}]", "iv", "AB", Some((0, 2)));
    }
    #[test]
    fn nested_quantifiers() {
        check(r"^(?:(a*?))*b$", "", "aaab", Some((0, 4)));
        check(r"^(?:(a?){2}){2}a$", "", "aaa", Some((0, 3)));
        check(r"^(a?)*$", "", "", Some((0, 0)));
        check(r"^((a?)*)*ab$", "", "ab", Some((0, 2)));
        let m = Regex::new(r"^((a?)*)*ab$").unwrap().find("aab").unwrap();
        assert_eq!(m.group(1), Some(0..1));
        assert_eq!(m.group(2), Some(0..1));
    }
}
