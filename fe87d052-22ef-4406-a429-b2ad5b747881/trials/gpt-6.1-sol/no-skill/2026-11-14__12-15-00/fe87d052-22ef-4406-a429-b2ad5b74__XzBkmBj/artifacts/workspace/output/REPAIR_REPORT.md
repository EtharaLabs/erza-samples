# Repair report

All regressions are in `tests/decimal_contract.cpp`. It builds against both header sets, passes against the repair, and aborts against the shipped headers. It checks the stored bits, error code, and end pointer for all three character types, plus signed and unsigned integer conversions.

## Inexact integer conversion in the double fast path

The admitted integer range extended to 2^54 instead of 2^53. Converting such a mantissa to double before scaling can round twice.

Reproduction: char double 9007199254740995e-1 required 0x430999999999999c produced 0x430999999999999d

The regression checks this input and its integer API equivalent. Both bit patterns were observed by running the respective headers. The required result was also checked against the system decimal converter; exact rational rounding independently explains it.

## Incorrect parity test at exact midpoints

The normal rounding path cleared the rounding bit for both parities instead of only when the lower neighbour is even.

Reproduction: char double 7539960883769189760e-1 required 0x43a4ed76e5237b08 produced 0x43a4ed76e5237b07

Both results were verified by running code. The integer significand here ends in an exact binary midpoint, and the required neighbour is even. The regression checks it for each character type.

## Infinity exponent retained a nonzero fraction

The overflow check used `>` instead of `>=`. Results at the infinity exponent could retain fraction bits and become NaNs.

Reproduction: char double 2142139806994845388e290 required 0x7ff0000000000000 produced 0x7ff310d0379e57d0

Both results were verified by running code. The regression also covers negative overflow, float overflow, and signed integer overflow.

## Long significands unnecessarily entered arbitrary precision

Affected input: `1.0000000000000000000000000000000000000001`, character type char, floating-point type double (also affects the other character types).

The endpoint comparison compared a rounded result with an unresolved, shifted result. It therefore rejected intervals whose endpoints round identically. This breaks the requirement to retain the 128-bit product decision for inputs it decides. The repair compares rounded endpoints and constructs the unresolved approximation only when needed. The regression covers this input. The control-flow defect and its repair were verified by inspection; no instruction-count measurement was run.

## Repeated scanning of a discarded zero suffix

Affected input: the exact midpoint `1.00000000000000011102230246251565404236316680908203125` followed by 3000 zero characters, character type char, floating-point type double.

After reaching the significant-digit limit, each eight-character step scanned the entire remaining suffix. All-zero suffixes thus took quadratic work, violating the linear-growth bound. The repair scans each chunk once. The regression checks the midpoint with a zero suffix and with a final nonzero digit. These numerical checks were run; the asymptotic cost claim follows from inspecting the loops. Valgrind counts were not measured.

## Additional boundary hardening

Exponent accumulation now saturates at the signed 64-bit limit instead of prematurely at approximately 268 million. Saturating combination with digit offsets prevents signed overflow. The old cap could fail when an extremely long significand offsets a large explicit exponent. This consequence is inferred, not reproduced with a hundreds-of-millions-character allocation. The regression exercises huge explicit exponents and signed zero, but does not reproduce this cancellation defect.

The product path now marks an all-one low product word as unresolved outside the exact-power interval. The integer APIs resolve that rare ambiguity with the same internal exact comparison as text parsing, using at most 20 stack-resident decimal digits. This restores the uncertainty handling without sending ordinary conversions to arbitrary precision. This boundary correction was established by inspection, without a concrete failing shipped input.

## Interactions and validation

The oversized double fast path can hide the midpoint defect by returning before integer rounding, or introduce its own double-rounding error. Overflow affects both APIs through their shared rounding routine. The long-input endpoint error unnecessarily exposes the exact path and can magnify the repeated-suffix scanning defect. Correcting the endpoint comparison leaves truly ambiguous midpoints on the exact path, where linear suffix scanning is still necessary. Product uncertainty requires exact fallback in both APIs; repairing only text conversion would leave integer conversion incomplete.

All shipped test sources were compiled individually with C++17 and optimization and run successfully after the repair. A three-million-input randomized double comparison against the system converter completed without a mismatch after the rounding repairs. These finite checks do not constitute exhaustive verification or measured instruction-budget validation. No conversion routine outside the library is called by the implementation. The API remains unchanged and the repair remains header-only.
