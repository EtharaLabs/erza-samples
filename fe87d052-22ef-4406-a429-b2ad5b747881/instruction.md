# Make fast_float's decimal parsing conform to its contract

`/workspace/fast_float` is a copy of the header-only C++ library fast_float at version 8.3.3. Its `fast_float::from_chars` turns a decimal character sequence into a `float` or a `double`, and its `fast_float::integer_times_pow10` turns an integer mantissa and a decimal exponent into one. In this copy, the library does not meet its contract for every input. Bring it into conformance.

## The contract

Two texts in `/workspace/spec` define the required behaviour, and they are the whole contract:

- `/workspace/spec/ROUNDING.md` defines the correctly rounded result of a decimal string in binary32 (`float`) and binary64 (`double`) under round to nearest, ties to even.
- `/workspace/spec/FROM_CHARS.md` defines the `fast_float::from_chars` contract: the pattern it matches, the `ptr` it returns, the `ec` it returns (`std::errc()`, `std::errc::invalid_argument`, or `std::errc::result_out_of_range`), and the value it stores, including the out-of-range behaviour the fast_float README documents, where a value too large stores the signed infinity, a value too small stores the signed zero, both return `std::errc::result_out_of_range`, and `ptr` points one past the parsed text.

The contract holds for every input of any length, for both `float` and `double`, with `char`, `char16_t`, and `char32_t` input and the default `fast_float::chars_format::general`. Conformance is judged by calling `fast_float::from_chars(first, last, value)` on `[first, last)` and comparing the bit pattern stored in `value`, the returned `ec`, and the returned `ptr` with what the contract determines.

`fast_float::integer_times_pow10(mantissa, decimal_exponent)`, in its `uint64_t` and `int64_t` mantissa overloads and with `float` or `double` as its result type, must return the value mantissa times ten to the power decimal_exponent rounded to that type by the rule `ROUNDING.md` defines, so a result too large is the signed infinity and a result too small is the signed zero. Conformance is judged by comparing the bit pattern it returns with that value.

Besides the behaviour those texts define, the contract bounds the cost of conversion, and a cause that breaks this bound is a cause of nonconformance. Cost is the number of machine instructions executed inside `fast_float::from_chars` and `fast_float::integer_times_pow10`, counted with valgrind on linux/amd64 and on linux/arm64 over fixed sets of inputs of both floating-point types and all three character types. On each set, the library may execute at most 1.5 times the instructions that fast_float 8.3.3 as released executes when built and counted the same way in the same run, and on inputs of one form at lengths n and 4n characters it may execute at most 5 times as many instructions for the longer input as for the shorter. fast_float 8.3.3 resorts to arbitrary-precision arithmetic only for an input whose correctly rounded result cannot be decided from a 128-bit product of its first 19 significant digits and a power of ten, and its work grows linearly with the length of the input; a library that keeps both properties and adds no more than a small constant to the work of each conversion is within both bounds, and one that routes a whole class of inputs that product decides to the arbitrary-precision path, or whose work grows faster than linearly with length, is not. For a cause of this kind, which changes no bit pattern, the report gives in place of items 1 and 2 an input it affects with its character type and floating-point type, and the property above that it breaks.

## The public API

Keep the public API of the library unchanged: the header `fast_float/fast_float.h`, the functions `fast_float::from_chars` and `fast_float::integer_times_pow10` with their signatures, overloads, and default arguments, the types `fast_float::from_chars_result`, `fast_float::from_chars_result_t`, and `fast_float::chars_format`, the support for `char`, `char16_t`, and `char32_t` input, and the library's support for C++17. The library stays header-only.

## Edit rules

- Change only files under `/workspace/fast_float/include/fast_float/`, and add or change files under `/workspace/fast_float/tests/`. Change, add, or remove nothing else under `/workspace/fast_float/`, and change nothing under `/workspace/spec/`.
- The upstream tests shipped in `/workspace/fast_float/tests/` must still build and pass. Each is one source file with its own `main`, built with `g++ -std=c++17 -O2 -I /workspace/fast_float/include /workspace/fast_float/tests/<name>.cpp -o /tmp/<name>`, and passes when it exits with status 0.
- Keep the conversion inside the library: `fast_float::from_chars` must compute its results itself and must not call `std::from_chars`, `std::strtod`, `std::strtof`, `std::strtold`, `std::stod`, `std::stof`, `sscanf`, `atof`, or any other routine outside the library that converts text to a floating-point value.
- The container has no network access.

## Report

Write `/workspace/output/REPAIR_REPORT.md`. For each distinct cause of nonconformance you found, it must give:

1. a reproducing input, its character type and floating-point type, the bit pattern the contract requires, and the bit pattern the unrepaired library produced;
2. the regression test you added under `/workspace/fast_float/tests/` for it, by file name;
3. which of your claims you verified by running code and which you inferred without running it;

and the report must state how the causes you found interact with one another.

Give each reproduction also on a line of its own in exactly this form, starting at the beginning of the line: `Reproduction: <character type> <floating-point type> <input> required 0x<hex> produced 0x<hex>`, where the character type is `char`, `char16_t`, or `char32_t`, the floating-point type is `float` or `double`, the input is the exact character sequence passed to `fast_float::from_chars` and consists of printable ASCII characters other than space, and the two hexadecimal bit patterns are the one the contract requires and the one the library as shipped to you stores. Each such line must be true of the library as shipped and of the contract, and the report holds at least one.

Name each regression test as `tests/<name>.cpp`. Every file the report names this way that you added or changed under `/workspace/fast_float/tests/` counts as a regression test and must build with the `g++` command above both against your repaired library and against the library as shipped to you, exit with status 0 against your repaired library, and exit with a non-zero status against the library as shipped. Each runs single-threaded and starts no other process, and must build within 120 seconds and run within 10 seconds of CPU time. The report names at least one and at most 16 such tests.
