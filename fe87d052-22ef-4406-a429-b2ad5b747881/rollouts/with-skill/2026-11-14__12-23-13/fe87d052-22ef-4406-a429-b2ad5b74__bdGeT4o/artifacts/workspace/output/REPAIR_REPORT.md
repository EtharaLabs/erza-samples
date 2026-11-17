# Decimal conversion repair

The changes preserve the public API, C++17, and header-only conversion. No external text-to-floating-point conversion is used.

## Observed rounding causes

### 1. Normal midpoint parity

The normal rounding branch cleared the rounding bit whenever it was set, including when the retained significand was odd. It must clear it only when the retained significand is even (`mantissa & 3 == 1`). Otherwise the subsequent rounding operation must increment the odd neighbour.

Reproduction: char float 16777219 required 0x4b800002 produced 0x4b800001

These are adjacent integers at a binary32 midpoint; the even significand belongs to 16777220. Regression: tests/rounding_contract.cpp. The test also checks both signed and unsigned integer-times-power-of-ten entry points and all three character widths.

### 2. Binary32 negative-exponent tie range

The float minimum exponent for exact tie detection was -4. It must be -17: powers of five through that exponent can divide a 64-bit significand and produce an exact binary midpoint. Without detection these ties round upward even when the lower neighbour is even.

Reproduction: char float 52428803125e-5 required 0x49000000 produced 0x49000001

The exact input is 524288.03125; binary32 neighbours are 524288 and 524288.0625. Regression: tests/rounding_contract.cpp. A second case, `216211103515625e-10`, exercises a more negative exponent.

### 3. Overflow at the infinity exponent

The overflow check used `>` instead of `>=`. An exponent equal to the infinity exponent with a nonzero fraction therefore escaped as a NaN. The repair clears the fraction at that exponent.

Reproduction: char double 2e308 required 0x7ff0000000000000 produced 0x7ff1ccf385ebc8a0
Reproduction: char float 4e38 required 0x7f800000 produced 0x7f967699

Regression: tests/rounding_contract.cpp, including error codes, full consumption, all three character widths, and an integer conversion.

All reproduction bits above were obtained by running the original headers, saved before editing. Repaired bits were also run. The expected bits follow exact integer/rational rounding, independently checked with a Python Fraction oracle.

## Cost causes

### 4. Incompatible representations in the long-input certainty check

Affected input: `1.500000000000000000000000000000`, char, double. The rounded result for the first 19 digits was compared with an unresolved, shifted approximation for the next mantissa. These representations cannot establish equality. This routed a whole class of product-decidable inputs to arbitrary precision, violating the stated fast-path property. Both endpoints now use `nearest_binary`; exact comparison occurs only when they disagree.

Regression: tests/rounding_contract.cpp includes this input form with 100,000 trailing zeros, in every character width. The path defect and its removal were verified by inspecting the called functions and representations; instruction counts were not measured.

### 5. Overlapping suffix scans

Affected input: `1.000000059604644775390625` followed by a long all-zero suffix, char, float. When the exact significand digit cap was reached in the fractional part, each iteration scanned the entire remaining suffix but advanced only eight characters. This is quadratic work and violates the linear-growth property. A single suffix scan suffices and replaces the loop.

Regression: tests/rounding_contract.cpp includes 100,000 trailing zeros and a separate far-tail nonzero case, across character widths. The quadratic and linear complexity claims are inferred directly from the loop bounds. Valgrind is not installed; neither architecture's instruction-count bound was measured.

## Additional arithmetic safeguards

Explicit exponent accumulation previously stopped updating after reaching a fixed threshold. That loses cancellation information for sufficiently long significands. It now saturates at the int64 limit, with saturating additions when combining the exponent and significand lengths. This extreme-length issue was identified by inspection; a multi-gigabyte public-input cancellation example was not executed.

The cached-product conversion now marks an all-one low word unresolved outside the established safe exponent interval. Both integer-mantissa overloads can resolve that uncertainty directly with the existing bigint comparison routines, without formatting or parsing text. These safeguards were reviewed mathematically; no original-library public bit mismatch specifically attributable to this rare uncertainty case was found in the executed corpus.

## Verification and interactions

Every shipped `.cpp` test was built separately with `g++ -std=c++17 -O2` and the repaired include directory, and every executable exited zero. The added tests/rounding_contract.cpp was also built against the original include directory: it exited nonzero (15 failed checks before the additional minimal exponent-range case was added). The final version was rebuilt against both directories and checked again.

An independent Python oracle parsed decimal inputs as exact Fractions and rounded using integer quotient/remainder arithmetic with ties to even, subnormal handling, and overflow. It checked 11,002 generated exact-midpoint/boundary inputs and 18,000 long exact-midpoint and near-midpoint inputs for both target types, with zero repaired mismatches. The first corpus exposed 250 original mismatches. These corpus checks used char; the regression and shipped wide-character tests exercise the other widths. This is finite testing, not an exhaustive execution of all inputs or an instruction-count certification.

The causes share the conversion pipeline. The long-input certainty defect forced exact comparison and could mask defects in the product rounding branch. Correcting it exposes that branch on long spellings, so midpoint and overflow repairs must hold there as well as on short inputs and integer conversion. It also amplified the suffix-scan defect by sending extra inputs into arbitrary precision; true ambiguous midpoint inputs still require that path after the certainty repair, so the scan independently needed fixing. Midpoint parity and exponent-range detection affect different conditions within the same rounding decision. Overflow normalization is shared by both text and integer entry points. The complete exact-midpoint corpus passed after the rounding and certainty repairs, and the long corpus passed after the suffix repair and again after the arithmetic safeguards.
