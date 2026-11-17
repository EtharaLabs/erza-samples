#!/bin/bash
# Reference repair for child 2: restores the six seeded lines (four that change results, two that
# change only the cost of conversion), repairs the exponent saturation inherited from fast_float
# 8.3.3, adds one regression test per cause, registers them with CTest, and writes the repair report.
set -euo pipefail
python3 - <<'PY'
import json
from pathlib import Path
lib = Path("/workspace/fast_float")
for rel, faulty, base in json.loads(r'''[
 [
  "include/fast_float/decimal_to_binary.h",
  "\n      (q <= binary::max_exponent_round_to_even()) &&\n      ((answer.mantissa & 1) == 1)) {",
  "\n      (q <= binary::max_exponent_round_to_even()) &&\n      ((answer.mantissa & 3) == 1)) {"
 ],
 [
  "include/fast_float/float_common.h",
  "binary_format<float>::min_exponent_round_to_even() {\n  return -4;",
  "binary_format<float>::min_exponent_round_to_even() {\n  return -17;"
 ],
 [
  "include/fast_float/float_common.h",
  "binary_format<double>::max_mantissa_fast_path() {\n  return uint64_t(4) << mantissa_explicit_bits();",
  "binary_format<double>::max_mantissa_fast_path() {\n  return uint64_t(2) << mantissa_explicit_bits();"
 ],
 [
  "include/fast_float/decimal_to_binary.h",
  "if fastfloat_clang_unlikely (answer.power2 > binary::infinite_power()) {",
  "if fastfloat_clang_unlikely (answer.power2 >= binary::infinite_power()) {"
 ],
 [
  "include/fast_float/parse_number.h",
  "  if (pns.too_many_digits && am.power2 >= 0 &&\n      pns.exponent >= binary_format<T>::smallest_power_of_ten() &&\n      pns.exponent <= binary_format<T>::largest_power_of_ten()) {\n    if (am != scaled_binary<binary_format<T>>(pns.exponent, pns.mantissa + 1)) {",
  "  if (pns.too_many_digits && am.power2 >= 0) {\n    if (am != nearest_binary<binary_format<T>>(pns.exponent, pns.mantissa + 1)) {"
 ],
 [
  "include/fast_float/ascii_number.h",
  "        if (exp_number < 0x10000000) {",
  "        if (exp_number < 0x0100000000000000) {"
 ],
 [
  "include/fast_float/digit_comparison.h",
  "        bool truncated = false;\n        while (!truncated && p != pend) {\n          UC const *chunk_end = pend - p > 8 ? p + 8 : pend;\n          truncated = has_nonzero_digits(p, pend);\n          p = chunk_end;\n        }\n        if (truncated) {\n          bump_last_digit(result, digits);",
  "        bool truncated = has_nonzero_digits(p, pend);\n        if (truncated) {\n          bump_last_digit(result, digits);"
 ]
]'''):
    path = lib / rel
    text = path.read_text()
    if text.count(faulty) != 1:
        raise SystemExit(f"{rel}: expected one faulty anchor")
    path.write_text(text.replace(faulty, base))
for rel, body in json.loads(r'''{
 "tests/regression_halfway_parity.cpp": "// Regression test for cause 1: the exact-halfway test in nearest_binary tested (answer.mantissa & 1) == 1, so an exact tie whose lower neighbour has an odd significand rounded down instead of to even.\n#include \"fast_float/fast_float.h\"\n\n#include <cstdint>\n#include <cstdio>\n#include <cstring>\n#include <string>\n#include <system_error>\n\nstatic int failures = 0;\n\ntemplate <typename T, typename UC>\nstatic void check(const char *text, std::uint64_t bits, std::errc ec = std::errc()) {\n  const std::string narrow = text;\n  const std::basic_string<UC> s(narrow.begin(), narrow.end());\n  T value = T(42);\n  auto r = fast_float::from_chars(s.data(), s.data() + s.size(), value);\n  std::uint64_t got = 0;\n  std::memcpy(&got, &value, sizeof value);\n  if (got != bits || r.ec != ec || r.ptr != s.data() + s.size()) {\n    std::printf(\"FAIL %s (%zu-byte value, %zu-byte char): got %016llx\\n\", text, sizeof(T), sizeof(UC), (unsigned long long)got);\n    ++failures;\n  }\n}\n\ntemplate <typename T> static void all_chars(const char *text, std::uint64_t bits, std::errc ec = std::errc()) {\n  check<T, char>(text, bits, ec);\n  check<T, char16_t>(text, bits, ec);\n  check<T, char32_t>(text, bits, ec);\n}\n\ntemplate <typename T> static void power(std::uint64_t m, int e, std::uint64_t bits) {\n  T value = fast_float::integer_times_pow10<T>(m, e);\n  std::uint64_t got = 0;\n  std::memcpy(&got, &value, sizeof value);\n  if (got != bits) {\n    std::printf(\"FAIL integer_times_pow10(%llu, %d): got %016llx\\n\", (unsigned long long)m, e, (unsigned long long)got);\n    ++failures;\n  }\n}\n\nint main() {\n  all_chars<double>(\"3786351887433356.75\", 0x432ae7557e7d7d1aull);\n  all_chars<float>(\"22626205433856\", 0x55a4a098u);\n  power<float>(22626205433856ull, 0, 0x55a4a098u);\n  return failures == 0 ? 0 : 1;\n}\n",
 "tests/regression_float_tie_window.cpp": "// Regression test for cause 2: binary_format<float>::min_exponent_round_to_even() returned -4, the binary64 value, so binary32 exact ties with a decimal exponent from -17 to -5 skipped the tie test and rounded up.\n#include \"fast_float/fast_float.h\"\n\n#include <cstdint>\n#include <cstdio>\n#include <cstring>\n#include <string>\n#include <system_error>\n\nstatic int failures = 0;\n\ntemplate <typename T, typename UC>\nstatic void check(const char *text, std::uint64_t bits, std::errc ec = std::errc()) {\n  const std::string narrow = text;\n  const std::basic_string<UC> s(narrow.begin(), narrow.end());\n  T value = T(42);\n  auto r = fast_float::from_chars(s.data(), s.data() + s.size(), value);\n  std::uint64_t got = 0;\n  std::memcpy(&got, &value, sizeof value);\n  if (got != bits || r.ec != ec || r.ptr != s.data() + s.size()) {\n    std::printf(\"FAIL %s (%zu-byte value, %zu-byte char): got %016llx\\n\", text, sizeof(T), sizeof(UC), (unsigned long long)got);\n    ++failures;\n  }\n}\n\ntemplate <typename T> static void all_chars(const char *text, std::uint64_t bits, std::errc ec = std::errc()) {\n  check<T, char>(text, bits, ec);\n  check<T, char16_t>(text, bits, ec);\n  check<T, char32_t>(text, bits, ec);\n}\n\ntemplate <typename T> static void power(std::uint64_t m, int e, std::uint64_t bits) {\n  T value = fast_float::integer_times_pow10<T>(m, e);\n  std::uint64_t got = 0;\n  std::memcpy(&got, &value, sizeof value);\n  if (got != bits) {\n    std::printf(\"FAIL integer_times_pow10(%llu, %d): got %016llx\\n\", (unsigned long long)m, e, (unsigned long long)got);\n    ++failures;\n  }\n}\n\nint main() {\n  all_chars<float>(\"0.6982338134765625e4\", 0x45da32b4u);\n  power<float>(6982338134765625ull, -12, 0x45da32b4u);\n  return failures == 0 ? 0 : 1;\n}\n",
 "tests/regression_fast_path_bound.cpp": "// Regression test for cause 3: binary_format<double>::max_mantissa_fast_path() returned 2^54, so binary64 mantissas above 2^53 took Clinger's fast path and were rounded twice.\n#include \"fast_float/fast_float.h\"\n\n#include <cstdint>\n#include <cstdio>\n#include <cstring>\n#include <string>\n#include <system_error>\n\nstatic int failures = 0;\n\ntemplate <typename T, typename UC>\nstatic void check(const char *text, std::uint64_t bits, std::errc ec = std::errc()) {\n  const std::string narrow = text;\n  const std::basic_string<UC> s(narrow.begin(), narrow.end());\n  T value = T(42);\n  auto r = fast_float::from_chars(s.data(), s.data() + s.size(), value);\n  std::uint64_t got = 0;\n  std::memcpy(&got, &value, sizeof value);\n  if (got != bits || r.ec != ec || r.ptr != s.data() + s.size()) {\n    std::printf(\"FAIL %s (%zu-byte value, %zu-byte char): got %016llx\\n\", text, sizeof(T), sizeof(UC), (unsigned long long)got);\n    ++failures;\n  }\n}\n\ntemplate <typename T> static void all_chars(const char *text, std::uint64_t bits, std::errc ec = std::errc()) {\n  check<T, char>(text, bits, ec);\n  check<T, char16_t>(text, bits, ec);\n  check<T, char32_t>(text, bits, ec);\n}\n\ntemplate <typename T> static void power(std::uint64_t m, int e, std::uint64_t bits) {\n  T value = fast_float::integer_times_pow10<T>(m, e);\n  std::uint64_t got = 0;\n  std::memcpy(&got, &value, sizeof value);\n  if (got != bits) {\n    std::printf(\"FAIL integer_times_pow10(%llu, %d): got %016llx\\n\", (unsigned long long)m, e, (unsigned long long)got);\n    ++failures;\n  }\n}\n\nint main() {\n  all_chars<double>(\"15446755860161931e-8\", 0x41a269f9cd340772ull);\n  power<double>(15446755860161931ull, -8, 0x41a269f9cd340772ull);\n  return failures == 0 ? 0 : 1;\n}\n",
 "tests/regression_overflow_infinity.cpp": "// Regression test for cause 4: the overflow clamp at the end of nearest_binary tested answer.power2 > binary::infinite_power(), so a result landing on the infinite exponent with a non-zero fraction was packed as a NaN while ec still reported result_out_of_range.\n#include \"fast_float/fast_float.h\"\n\n#include <cstdint>\n#include <cstdio>\n#include <cstring>\n#include <string>\n#include <system_error>\n\nstatic int failures = 0;\n\ntemplate <typename T, typename UC>\nstatic void check(const char *text, std::uint64_t bits, std::errc ec = std::errc()) {\n  const std::string narrow = text;\n  const std::basic_string<UC> s(narrow.begin(), narrow.end());\n  T value = T(42);\n  auto r = fast_float::from_chars(s.data(), s.data() + s.size(), value);\n  std::uint64_t got = 0;\n  std::memcpy(&got, &value, sizeof value);\n  if (got != bits || r.ec != ec || r.ptr != s.data() + s.size()) {\n    std::printf(\"FAIL %s (%zu-byte value, %zu-byte char): got %016llx\\n\", text, sizeof(T), sizeof(UC), (unsigned long long)got);\n    ++failures;\n  }\n}\n\ntemplate <typename T> static void all_chars(const char *text, std::uint64_t bits, std::errc ec = std::errc()) {\n  check<T, char>(text, bits, ec);\n  check<T, char16_t>(text, bits, ec);\n  check<T, char32_t>(text, bits, ec);\n}\n\ntemplate <typename T> static void power(std::uint64_t m, int e, std::uint64_t bits) {\n  T value = fast_float::integer_times_pow10<T>(m, e);\n  std::uint64_t got = 0;\n  std::memcpy(&got, &value, sizeof value);\n  if (got != bits) {\n    std::printf(\"FAIL integer_times_pow10(%llu, %d): got %016llx\\n\", (unsigned long long)m, e, (unsigned long long)got);\n    ++failures;\n  }\n}\n\nint main() {\n  all_chars<double>(\"1.798e308\", 0x7ff0000000000000ull, std::errc::result_out_of_range);\n  power<double>(1798ull, 305, 0x7ff0000000000000ull);\n  return failures == 0 ? 0 : 1;\n}\n",
 "tests/regression_product_decides.cpp": "// Regression test for cause 5: for more than 19 significant digits, from_chars_advanced compared nearest_binary at the truncated significand with scaled_binary at the significand plus one, so every long input the 128-bit product decides took the arbitrary-precision path. It counts the big-integer index checks (FASTFLOAT_DEBUG_ASSERT) a decided long input performs: none after the repair, hundreds before, and the result bits are the same either way.\n#include <cstdint>\n#include <cstdio>\n#include <cstring>\n#include <string>\n\nstatic unsigned long long bigint_steps = 0;\n#define FASTFLOAT_DEBUG_ASSERT(x) { ++bigint_steps; static_cast<void>(x); }\n#include \"fast_float/fast_float.h\"\n\nint main() {\n  const char *text = \"6.83941199975692349231310104239542605453707329827661608465236342102926307944427328678732e-300\";\n  double value = 0;\n  auto r = fast_float::from_chars(text, text + std::strlen(text), value);\n  std::uint64_t bits = 0;\n  std::memcpy(&bits, &value, sizeof bits);\n  if (bits != 0x01d2523b9bf62188ull || r.ec != std::errc()) {\n    std::printf(\"FAIL result %016llx\\n\", (unsigned long long)bits);\n    return 1;\n  }\n  if (bigint_steps != 0) {\n    std::printf(\"FAIL a long input the 128-bit product decides used the big-integer path (%llu steps)\\n\", bigint_steps);\n    return 1;\n  }\n  return 0;\n}\n",
 "tests/regression_linear_tail.cpp": "// Regression test for cause 6: in load_significand the check for non-zero digits after the last loaded one re-ran has_nonzero_digits(p, pend) from each eight-character step, so the work grew with the square of the input length. It counts the bytes the parser reads through memcpy for an all-zero tail of n and 4n characters: about 4 times as many after the repair, about 31 times before.\n#include <cstdint>\n#include <cstdio>\n#include <cstring>\n#include <string>\n\nstatic unsigned long long copied = 0;\nstatic void *counted_memcpy(void *d, const void *s, size_t n) {\n  copied += n;\n  return std::memcpy(d, s, n);\n}\n#define memcpy counted_memcpy\n#include \"fast_float/fast_float.h\"\n#undef memcpy\n\nstatic unsigned long long work(size_t zeros, int &failures) {\n  std::string s = \"402752343221584.34375\";\n  s.append(zeros, '0');\n  copied = 0;\n  double value = 0;\n  auto r = fast_float::from_chars(s.data(), s.data() + s.size(), value);\n  std::uint64_t bits = 0;\n  std::memcpy(&bits, &value, sizeof bits);\n  if (bits != 0x42f6e4d1659a5506ull || r.ec != std::errc() || r.ptr != s.data() + s.size()) {\n    std::printf(\"FAIL result %016llx for %zu zeros\\n\", (unsigned long long)bits, zeros);\n    ++failures;\n  }\n  return copied;\n}\n\nint main() {\n  int failures = 0;\n  unsigned long long shorter = work(2000, failures), longer = work(8000, failures);\n  if (failures != 0) return 1;\n  if (shorter == 0 || longer > 8 * shorter) {\n    std::printf(\"FAIL 4 times the length read %llu bytes against %llu\\n\", longer, shorter);\n    return 1;\n  }\n  return 0;\n}\n",
 "tests/regression_exponent_saturation.cpp": "// Regression test for cause 7: parse_number_string stopped accumulating explicit exponent digits once the magnitude reached 2^28 and only then added the digit-position offset, so an input with about 2^28 fractional digits cancelled the saturated exponent and was computed from a wrong exponent.\n#include \"fast_float/fast_float.h\"\n\n#include <cstdint>\n#include <cstdio>\n#include <cstring>\n#include <string>\n#include <system_error>\n\nint main() {\n  std::string s = \"0.\";\n  s.append(268435455, '0');\n  s += \"1e2684354560\";\n  double value = 42;\n  auto r = fast_float::from_chars(s.data(), s.data() + s.size(), value);\n  std::uint64_t bits = 0;\n  std::memcpy(&bits, &value, sizeof bits);\n  if (bits != 0x7ff0000000000000ull || r.ec != std::errc::result_out_of_range || r.ptr != s.data() + s.size()) {\n    std::printf(\"FAIL got %016llx\\n\", (unsigned long long)bits);\n    return 1;\n  }\n  return 0;\n}\n"
}''').items():
    (lib / rel).write_text(body)
cmake = lib / "tests/CMakeLists.txt"
text = cmake.read_text()
text += "\nforeach(TEST_NAME regression_halfway_parity regression_float_tie_window regression_fast_path_bound regression_overflow_infinity regression_product_decides regression_linear_tail regression_exponent_saturation)\n  add_executable(${TEST_NAME} ${TEST_NAME}.cpp)\n  target_link_libraries(${TEST_NAME} PUBLIC fast_float)\n  add_test(NAME ${TEST_NAME} COMMAND ${TEST_NAME})\nendforeach()\n"
cmake.write_text(text)
PY
mkdir -p /workspace/output
cat > /workspace/output/REPAIR_REPORT.md <<'REPORT'
# Repair report

Each claim is marked [verified] when I confirmed it by running code, or [inferred] when I did not run code for it. Seven causes were found: five change result bit patterns and two change only the cost of conversion.

## Cause 1: include/fast_float/decimal_to_binary.h, nearest_binary

- Mechanism: the exact-halfway test tested `(answer.mantissa & 1) == 1`, so an exact tie whose lower neighbour has an odd significand rounded down instead of to even. [verified]
- Reproducing input: `3786351887433356.75` parsed from `char` as `double`. The contract requires `0x432AE7557E7D7D1A`; the unrepaired library produced `0x432AE7557E7D7D19`. [verified]

Reproduction: char double 3786351887433356.75 required 0x432AE7557E7D7D1A produced 0x432AE7557E7D7D19

- Repair: the test reads `((answer.mantissa & 3) == 1)`. [verified]
- Regression test: `tests/regression_halfway_parity.cpp`, which fails on the unrepaired library and passes after the repair. [verified]

## Cause 2: include/fast_float/float_common.h, binary_format<float>::min_exponent_round_to_even

- Mechanism: it returned -4, the binary64 value, so binary32 exact ties with a decimal exponent from -17 to -5 skipped the tie test and rounded up. [verified]
- Reproducing input: `0.6982338134765625e4` parsed from `char` as `float`. The contract requires `0x45DA32B4`; the unrepaired library produced `0x45DA32B5`. [verified]

Reproduction: char float 0.6982338134765625e4 required 0x45DA32B4 produced 0x45DA32B5

- Repair: it returns -17. [verified]
- Regression test: `tests/regression_float_tie_window.cpp`, which fails on the unrepaired library and passes after the repair. [verified]

## Cause 3: include/fast_float/float_common.h, binary_format<double>::max_mantissa_fast_path

- Mechanism: it returned 2^54, so binary64 mantissas above 2^53 took Clinger's fast path (`exact_small_product`) and were rounded twice. [verified]
- Reproducing input: `15446755860161931e-8` parsed from `char` as `double`. The contract requires `0x41A269F9CD340772`; the unrepaired library produced `0x41A269F9CD340773`. [verified]

Reproduction: char double 15446755860161931e-8 required 0x41A269F9CD340772 produced 0x41A269F9CD340773

- Repair: it returns `uint64_t(2) << mantissa_explicit_bits()`, 2^53. [verified]
- Regression test: `tests/regression_fast_path_bound.cpp`, which fails on the unrepaired library and passes after the repair. [verified]

## Cause 4: include/fast_float/decimal_to_binary.h, the overflow clamp of nearest_binary

- Mechanism: it tested `answer.power2 > binary::infinite_power()`, so a result landing on the infinite exponent with a non-zero fraction was packed as a NaN while `ec` still reported `std::errc::result_out_of_range`. [verified]
- Reproducing input: `1.798e308` parsed from `char` as `double`. The contract requires `0x7FF0000000000000` with `std::errc::result_out_of_range`; the unrepaired library produced `0x7FF000B2FDC560A6`. [verified]

Reproduction: char double 1.798e308 required 0x7FF0000000000000 produced 0x7FF000B2FDC560A6

- Repair: the clamp tests `answer.power2 >= binary::infinite_power()`. [verified]
- Regression test: `tests/regression_overflow_infinity.cpp`, which fails on the unrepaired library and passes after the repair. [verified]

## Cause 5 (cost, no bit pattern changes): include/fast_float/parse_number.h, from_chars_advanced

- Mechanism: for an input with more than 19 significant digits, the comparison that decides whether the arbitrary-precision path runs compared `nearest_binary` at the truncated significand with `scaled_binary` at the significand plus one. The two never agree, so every such input within the power-of-ten table's range took the arbitrary-precision path even when the 128-bit product of its first 19 digits decides it. [verified]
- Property broken: the arbitrary-precision path must run only for an input the 128-bit product cannot decide; a whole class of decidable inputs was routed there. [verified]
- Affected input: `6.83941199975692349231310104239542605453707329827661608465236342102926307944427328678732e-300` parsed from `char` as `double`. The result bits are correct (`0x01D2523B9BF62188`) before and after the repair; before the repair the conversion performed 378 big-integer index checks, after it none. [verified]
- Repair: both candidates come from `nearest_binary`. [verified]
- Regression test: `tests/regression_product_decides.cpp`, which fails on the unrepaired library and passes after the repair. [verified]

## Cause 6 (cost, no bit pattern changes): include/fast_float/digit_comparison.h, load_significand

- Mechanism: after the last digit the big integer holds, the check for non-zero digits beyond it re-ran `has_nonzero_digits(p, pend)` from each eight-character step to the end of the input instead of once. [verified]
- Property broken: work must grow linearly with the length of the input; for an all-zero tail it grew with the square of the length. [verified]
- Affected input: `402752343221584.34375` followed by 8000 zeros, parsed from `char` as `double`. Against the same input with 2000 zeros, the parser read about 31 times as many bytes before the repair and about 4 times as many after it; the result bits are the same. [verified]
- Repair: the check runs once, `bool truncated = has_nonzero_digits(p, pend);`. [verified]
- Regression test: `tests/regression_linear_tail.cpp`, which fails on the unrepaired library and passes after the repair. [verified]

## Cause 7: include/fast_float/ascii_number.h, parse_number_string, explicit exponent

- Mechanism: while parsing an explicit exponent, the accumulation stopped once the magnitude reached `0x10000000` (2^28), and the digit-position offset was added only afterwards, so for an input with about 2^28 or more fractional digits the offset cancelled the saturated exponent and the result was computed from a wrong exponent. This cause is inherited from fast_float 8.3.3. [verified]
- Reproducing input: `0.` followed by 268435455 zeros and `1e2684354560` (268,435,469 characters) parsed from `char` as `double`. The contract requires `0x7FF0000000000000` with `std::errc::result_out_of_range`; the unrepaired library produced `0x3FF0000000000000` with `std::errc()`. Its Reproduction line, which spells the input in full, is the last line of this report. [verified]
- Repair: the accumulation continues while the magnitude is below 2^56, which no digit-position offset of an input can cancel. [verified]
- Regression test: `tests/regression_exponent_saturation.cpp`, which fails on the unrepaired library and passes after the repair. [verified]

## How the causes interact

- Cause 3 hid cause 1 on integer ties: with the fast path widened, integers such as `9007199254740995` were rounded by the hardware conversion and came out right, so repairing cause 3 alone makes those inputs wrong through cause 1. [verified]
- Causes 1 and 2 overlap on binary32 ties: with both present, binary32 ties round down in one exponent window and up in another, so repairing cause 1 alone leaves binary32 ties with exponents from -17 to -5 wrong through cause 2. [verified]
- Cause 5 hid causes 2 and 4 on long spellings: it sent long inputs to the arbitrary-precision path, which rounds them exactly, so long spellings of binary32 ties and of values near overflow came out right, and repairing cause 5 alone exposes causes 2 and 4 on those spellings. [verified]
- Cause 6 does not interact with the other causes: it changes only the work of the big-integer path, never a result. [inferred]
- Cause 7 does not interact with the other causes: it changes the decimal exponent before any rounding decision is made. [inferred]
REPORT
python3 -c 'import sys; sys.stdout.write("\nReproduction: char double 0." + "0" * 268435455 + "1e2684354560 required 0x7FF0000000000000 produced 0x3FF0000000000000\n")' >> /workspace/output/REPAIR_REPORT.md
