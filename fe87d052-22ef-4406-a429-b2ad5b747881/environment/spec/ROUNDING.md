# Rounding a decimal string to binary32 and binary64

This text restates, in its own words, the rule that IEEE 754-2019 fixes for converting a decimal character sequence to a binary floating-point format under the default rounding attribute, round to nearest with ties to even. It is written for this task and quotes no standard.

## The two formats

| Format | C++ type | Precision p (significand bits, hidden bit included) | Smallest normal exponent emin | Largest exponent emax |
| --- | --- | --- | --- | --- |
| binary32 | `float` | 24 | -126 | 127 |
| binary64 | `double` | 53 | -1022 | 1023 |

A finite value of a format is either zero, a normal value `m * 2^(e - p + 1)` with `2^(p-1) <= m < 2^p` and `emin <= e <= emax`, or a subnormal value `m * 2^(emin - p + 1)` with `1 <= m < 2^(p-1)`. Every finite value carries a sign, and zero exists as +0 and as -0. The largest finite magnitude is `(2 - 2^(1-p)) * 2^emax`, and the smallest positive subnormal is `2^(emin - p + 1)`.

## The exact value of a decimal string

A decimal string such as `123.456e-7` denotes one exact rational number: its digits read as an integer, scaled by ten to the power of its exponent minus the number of digits after the decimal point. The exact value does not depend on how the string is written. Leading zeros, trailing zeros, the position of the decimal point, and the number of digits written change nothing about the value, and so change nothing about the result. A string may carry any number of digits.

## The correctly rounded result

Write `x` for the exact magnitude of the decimal string. The result is chosen as follows, and the sign of the string is applied to it afterwards.

1. If `x` is zero, the result is zero.
2. Consider every finite value of the format, normal and subnormal, together with an unbounded continuation of normal values above the largest finite magnitude at the same spacing as the top binade. The result is the one of these closest to `x`.
3. If `x` lies exactly halfway between two adjacent candidates, the result is the candidate whose significand `m` is even. This applies everywhere in the range, including between two subnormal values, between the largest subnormal and the smallest normal value, and between two values of different binades.
4. If the candidate chosen in step 2 or 3 lies above the largest finite magnitude, the result is infinity. Equivalently, every `x` at or above `(2 - 2^(-p)) * 2^emax`, the largest finite magnitude plus half of its unit in the last place, rounds to infinity, and every `x` below that bound rounds to a finite value.
5. If the candidate chosen is zero, which happens for every `x` at or below half of the smallest positive subnormal, with exactly half rounding to zero because zero is even, the result is zero.

The result for `float` is computed from `x` directly. Rounding first to `double` and then to `float` is a different operation and can give a different answer.

## Examples

These examples illustrate the rule. They are not a test list.

| Input | Type | Result |
| --- | --- | --- |
| `0.1` | `double` | `0x3FB999999999999A` |
| `1e23` | `double` | `0x44B52D02C7E14AF6` |
| `9007199254740993` | `double` | `0x4340000000000000` (exactly halfway, the even neighbour 2^53 wins) |
| `16777217` | `float` | `0x4B800000` (exactly halfway, the even neighbour 2^24 wins) |
| `1e-400` | `double` | `0x0000000000000000` |
| `1e400` | `double` | `0x7FF0000000000000` |
