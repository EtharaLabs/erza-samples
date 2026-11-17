# The fast_float::from_chars contract for float and double

This text restates, in its own words, the contract that the C++ standard library's `std::from_chars` sets for parsing a floating-point value, as the fast_float library at version 8.3.3 specifies it in its README, including the README's section on the behaviour of `result_out_of_range`. It is written for this task and quotes neither the standard nor the README.

## The call

```cpp
#include "fast_float/fast_float.h"

fast_float::from_chars_result r = fast_float::from_chars(first, last, value);
// first, last: const char*, the half-open range [first, last) to parse
// value: float& or double&
// an optional fourth argument is a fast_float::chars_format; it defaults to chars_format::general
```

`from_chars_result` has two members: `ptr`, a `const char*`, and `ec`, a `std::errc`.

## The pattern

With `chars_format::general`, the call matches the longest prefix of `[first, last)` that has this form, and reads nothing past it:

1. an optional `-` sign (a leading `+` is not part of the pattern, and neither is leading whitespace), then
2. either a decimal significand, which is a non-empty sequence of digits with at most one `.` anywhere in it and at least one digit, optionally followed by an exponent made of `e` or `E`, an optional `+` or `-`, and one or more digits, where an `e` or `E` that is not followed by a complete exponent is not part of the match;
3. or one of `inf`, `infinity`, `nan`, or `nan(` followed by letters, digits, and underscores and a closing `)`, each matched without regard to letter case.

Hexadecimal significands are not part of the pattern, so `0x10` matches only its leading `0`.

## The result

- No match: when no prefix of `[first, last)` has the form above, `ec` is `std::errc::invalid_argument`, `ptr` equals `first`, and `value` is left unmodified.
- A match: `ptr` points one past the last character of the matched pattern. For a decimal significand, `value` is set to the result that ROUNDING.md defines for the matched text in the type of `value`, with the sign applied, and `ec` is `std::errc()`, except in the two out-of-range cases below. `inf` and `infinity` give an infinity of the matched sign, and every `nan` form gives a quiet NaN, each with `ec` equal to `std::errc()`.
- Out of range, too large: when the decimal value's correctly rounded result is an infinity, `value` is set to that infinity with the sign of the input, `ec` is `std::errc::result_out_of_range`, and `ptr` points one past the parsed text.
- Out of range, too small: when the decimal significand has at least one non-zero digit and its correctly rounded result is a zero, `value` is set to that zero with the sign of the input, `ec` is `std::errc::result_out_of_range`, and `ptr` points one past the parsed text.

A result that is a non-zero subnormal value is in range: `value` is set to it and `ec` is `std::errc()`. A significand whose digits are all zero gives a zero of the input's sign with `ec` equal to `std::errc()`, whatever its exponent.

This out-of-range behaviour follows the fast_float README and differs from leaving `value` unmodified on `result_out_of_range`.
