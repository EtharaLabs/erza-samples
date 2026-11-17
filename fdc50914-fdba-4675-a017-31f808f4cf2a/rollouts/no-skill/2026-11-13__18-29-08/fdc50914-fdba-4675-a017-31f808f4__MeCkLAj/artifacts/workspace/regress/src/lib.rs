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
mod ecma2025_regressions {
    use crate::{Regex, BudgetedMatch};
    #[test]
    fn named_and_sets() {
        let cases = [
            (r"(?:(?<x>a)|(?<x>b))\k<x>", "", "bb", Some(0..2)),
            (r"(?:(?<x>a)|(?<x>b))\k<x>", "", "b", None),
            (r"[\q{}]", "v", "", Some(0..0)),
            (r"[a\q{}]", "v", "a", Some(0..1)),
            (r"(?:(a?){1,2}){2}b", "", "aab", Some(0..3)),
            (r"[k]", "iu", "K", Some(0..3)),
            (r"[a&&A]", "iv", "A", Some(0..1)),
            (r"[a--A]", "iv", "a", None),
            (r"[\q{a}&&a]", "v", "a", Some(0..1)),
            (r"[a&]", "v", "a", Some(0..1)),
            (r"[\b]", "v", "\u{8}", Some(0..1)),
            (r"[\W]", "iv", "ſ", None),
        ];
        for (pattern, flags, text, expected) in cases {
            let re = Regex::with_flags(pattern, flags).unwrap();
            let actual = match re.find_from_budgeted(text, 0, 1_000_000) {
                BudgetedMatch::Match(m) => Some(m.range),
                BudgetedMatch::NoMatch => None,
                BudgetedMatch::BudgetExhausted => panic!("budget: {pattern}"),
            };
            assert_eq!(actual, expected, "{pattern}");
        }
        assert!(Regex::new(r"(?:(?<x>a)|b)(?:c|(?<x>d))").is_err());
        assert!(Regex::with_flags(r"[^\q{}]", "v").is_err());
        assert!(Regex::with_flags(r"\u{+41}", "u").is_err());
        assert!(Regex::with_flags(r"\u+041", "u").is_err());
        let m = Regex::new(r"(?<x>a)|(?<x>b)").unwrap().find("b").unwrap();
        assert_eq!(m.named_group("x"), Some(0..1));
    }
}

#[cfg(all(test, feature = "utf16"))]
mod ecma2025_utf16_regressions {
    use crate::Regex;
    #[test]
    fn code_unit_ranges() {
        let re = Regex::with_flags(r"(?<x>K)", "iu").unwrap();
        let input: Vec<u16> = "😀k".encode_utf16().collect();
        let m = re.find_from_utf16(&input, 0).next().unwrap();
        assert_eq!(m.range, 2..3);
        assert_eq!(m.named_group("x"), Some(2..3));
        let m = re.find_from_ucs2(&input, 0).next().unwrap();
        assert_eq!(m.range, 2..3);
        assert_eq!(m.named_group("x"), Some(2..3));
    }
}
