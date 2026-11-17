---
name: correctly-rounded-decimal-parsing
description: Method for verifying and repairing a decimal-to-binary floating-point parser against a correct-rounding contract, and for testing it at its boundary cases. Use when a parser of decimal text into float or double must return the correctly rounded result (round to nearest, ties to even) for every input, including long inputs, subnormal and out-of-range results, and several character types.
---

# Correctly rounded decimal parsing

## What correct rounding means

The correctly rounded result of a decimal string is a pure function of its exact value: write the value as an exact rational number, find the two adjacent representable numbers that bracket it, and take the nearer one; when it lies exactly halfway, take the one whose significand is even. Nothing else may influence the result: not how many digits are written, not whether the value is spelled with an exponent, leading zeros, or trailing zeros, and not which character type holds the text.

Two consequences follow:

- Equal values must give equal bits. `1.5`, `15e-1`, `0001.5000`, and `1.50000000000000000000000000000` are one value.
- Exact halfway values are rare but decisive. For binary64 a midpoint can need several hundred significant decimal digits to write exactly, and a parser must read all of them, or prove the unread ones cannot matter, before it decides.

## Build an exact oracle first

Before changing parser code, write an independent reference that cannot be wrong for the reason the parser is wrong:

1. Parse the text into sign, digit string, and decimal exponent yourself, following the written grammar of the contract, including what counts as a match and where the match ends.
2. Form the exact value with rational arithmetic (for example Python's `fractions.Fraction`), never with floating point.
3. Round to the target format by integer arithmetic on the scaled significand: compute the quotient and remainder, compare the remainder with one half exactly, and break ties to even. Handle the subnormal range by clamping the exponent at the minimum and letting the significand shrink, and handle overflow by the contract's rule for out-of-range values.
4. Compare bit patterns, not printed values, and compare every other output the contract specifies (error code, end pointer) separately from the value, since a value can be right while the error code is wrong and the other way round.

Check the oracle itself on values whose bits you can derive by hand: powers of two, the largest finite value, the smallest normal and subnormal values, and a few exact midpoints.

## Generate inputs where parsers fail

Random inputs almost never land on the hard cases. Construct them from the format instead of from decimal strings:

- **Exact midpoints.** For a random significand `m` and exponent `e`, the value `(2m + 1) * 2^(e - 1)` lies exactly halfway between two neighbours. Write it out exactly, in its shortest exact decimal form and also padded with extra zeros.
- **Just off a midpoint.** Add or subtract a tiny amount far below the last written digit, so the correct answer is decided by digits deep in the string.
- **Spelling variants of one value.** Short (at most 19 significant digits), long (more than 19), very long (hundreds of digits), scientific notation, leading and trailing zeros. Parsers often take different internal paths by digit count, so each spelling exercises different code.
- **Every range boundary.** The subnormal range and especially its top binade, the boundary between the largest subnormal and the smallest normal value, half the smallest subnormal, the largest finite value and the rounding threshold just above it, and exponents far outside the range in both directions.
- **Integer limits.** Integers near the largest integer the format represents exactly, and odd integers just above it, which are midpoints.
- **Every entry point and character type.** If the API accepts several character types or offers other entry points that share the rounding core, run the same values through each of them. Code specialised for one character width is a separate path.
- **Malformed and partial inputs.** Text that matches only a prefix, signs, infinities, NaNs, and text that matches nothing, checked against the contract's rules for the end pointer and the error code.

Generate thousands of cases per class from fixed seeds so every run is reproducible, and keep the classes separate so a failure tells you where to look.

## Locate and repair a defect

1. **Minimise.** Take the shortest failing input of each class, and confirm the oracle and the parser disagree on it by bits.
2. **Find the path.** Instrument or step through the parser to see which path the input takes: a fast exact path, an approximation with a certainty check, or a slow exact fallback. Compare the decision each stage makes with the decision the exact value requires.
3. **Read the decision, not the symptom.** Check each condition and each data transformation on the path against the mathematics it implements, including the range of exponents or significands it is meant to cover, rather than adjusting the output until it looks right.
4. **Repair the cause where it lives.** A patch at a call site that rewrites a wrong output into a right one leaves every other caller of the faulty routine wrong.
5. **Re-run every class after every repair.** Defects in one parser can interact, and one can hide another's symptoms, so a repair can make previously passing inputs fail. Record which classes change after each repair; that record is how you learn how the causes interact.

## Regression tests

For each distinct cause, keep a small test program that feeds the minimised input and checks the exact bits and the other outputs. Build it against the unrepaired code first and confirm it fails there; a regression test that passes on the broken code tests nothing. Then confirm it passes after the repair. Keep each test single-threaded and fast.

## Reporting

For each cause, state the input, its character type and target type, the bits the contract requires, and the bits the unrepaired code produced; name its regression test; and say which claims you confirmed by running code and which you inferred. State how the causes interact, or that they do not, from the record of what changed after each repair.
