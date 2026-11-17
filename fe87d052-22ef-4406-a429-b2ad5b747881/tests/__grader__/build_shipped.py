"""Turn the upstream fast_float tree at dbeabee into the tree shipped to the agent.

Usage: python build_shipped.py <extracted upstream tree> <output tree> [--reference]
(--reference restructures without applying the faults: fast_float 8.3.3 under the shipped names)

Copies the kept files only, strips comments and renames helpers (restructure.py), applies the six
seeded faults (four that change results, two that change only the cost of conversion) by exact
anchor, removes the benchmark block from the root CMakeLists.txt, and writes a tests/CMakeLists.txt
that builds the kept upstream tests with no network. Every edit asserts its anchor, so a moved upstream
byte fails the build instead of shipping a silently different tree.
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import restructure  # noqa: E402

KEPT_TESTS = (
    "rcppfastfloat_test",
    "wide_char_test",
    "supported_chars_test",
    "example_test",
    "example_comma_test",
    "example_integer_times_pow10",
    "p2497",
    "fast_int",
    "json_fmt",
    "javascript_fmt",
    "fortran",
)
KEPT_FILES = (
    "AUTHORS",
    "CONTRIBUTORS",
    "LICENSE-APACHE",
    "LICENSE-BOOST",
    "LICENSE-MIT",
    "README.md",
    "CMakeLists.txt",
    "cmake/config.cmake.in",
)
HEADERS = (
    "ascii_number.h",
    "bigint.h",
    "constexpr_feature_detect.h",
    "decimal_to_binary.h",
    "digit_comparison.h",
    "fast_float.h",
    "fast_table.h",
    "float_common.h",
    "parse_number.h",
)

# (file under include/fast_float, anchor, replacement), applied after the restructuring; each anchor must occur exactly once.
FAULTS = (
    ('decimal_to_binary.h', '\n      (q <= binary::max_exponent_round_to_even()) &&\n      ((answer.mantissa & 3) == 1)) {', '\n      (q <= binary::max_exponent_round_to_even()) &&\n      ((answer.mantissa & 1) == 1)) {'),
    ('float_common.h', 'binary_format<float>::min_exponent_round_to_even() {\n  return -17;', 'binary_format<float>::min_exponent_round_to_even() {\n  return -4;'),
    ('float_common.h', 'binary_format<double>::max_mantissa_fast_path() {\n  return uint64_t(2) << mantissa_explicit_bits();', 'binary_format<double>::max_mantissa_fast_path() {\n  return uint64_t(4) << mantissa_explicit_bits();'),
    ('decimal_to_binary.h', 'if fastfloat_clang_unlikely (answer.power2 >= binary::infinite_power()) {', 'if fastfloat_clang_unlikely (answer.power2 > binary::infinite_power()) {'),
    ('parse_number.h', '  if (pns.too_many_digits && am.power2 >= 0) {\n    if (am != nearest_binary<binary_format<T>>(pns.exponent, pns.mantissa + 1)) {', '  if (pns.too_many_digits && am.power2 >= 0 &&\n      pns.exponent >= binary_format<T>::smallest_power_of_ten() &&\n      pns.exponent <= binary_format<T>::largest_power_of_ten()) {\n    if (am != scaled_binary<binary_format<T>>(pns.exponent, pns.mantissa + 1)) {'),
    ('digit_comparison.h', '        bool truncated = has_nonzero_digits(p, pend);\n        if (truncated) {\n          bump_last_digit(result, digits);', '        bool truncated = false;\n        while (!truncated && p != pend) {\n          UC const *chunk_end = pend - p > 8 ? p + 8 : pend;\n          truncated = has_nonzero_digits(p, pend);\n          p = chunk_end;\n        }\n        if (truncated) {\n          bump_last_digit(result, digits);'),
)

BENCHMARK_BLOCK = """

option(FASTFLOAT_BENCHMARKS "Enable benchmarks" OFF)
if(FASTFLOAT_BENCHMARKS)
  add_subdirectory(benchmarks)
else(FASTFLOAT_BENCHMARKS)
  message(STATUS "Benchmarks are disabled. Set FASTFLOAT_BENCHMARKS to ON to build benchmarks (assumes C++17).")
endif(FASTFLOAT_BENCHMARKS)
"""

TESTS_CMAKE = """# Builds the upstream tests kept in this copy. Each test is one translation unit with its own
# main() and reads no data file, so the build needs no network.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
foreach(TEST_NAME {names})
  add_executable(${{TEST_NAME}} ${{TEST_NAME}}.cpp)
  target_link_libraries(${{TEST_NAME}} PUBLIC fast_float)
  add_test(NAME ${{TEST_NAME}} COMMAND ${{TEST_NAME}})
endforeach()
"""


def edit(path: Path, before: str, after: str) -> None:
    text = path.read_text()
    if text.count(before) != 1:
        raise SystemExit(f"{path.name}: expected one anchor, found {text.count(before)}: {before[:60]!r}")
    path.write_text(text.replace(before, after))


def main() -> None:
    upstream, out = Path(sys.argv[1]), Path(sys.argv[2])
    reference = sys.argv[3:] == ["--reference"]
    if out.exists():
        raise SystemExit(f"{out} already exists")
    for rel in KEPT_FILES:
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(upstream / rel, out / rel)
    (out / "include/fast_float").mkdir(parents=True)
    for name in HEADERS:
        shutil.copyfile(upstream / "include/fast_float" / name, out / "include/fast_float" / name)
    (out / "tests").mkdir()
    for name in KEPT_TESTS:
        shutil.copyfile(upstream / "tests" / f"{name}.cpp", out / "tests" / f"{name}.cpp")
    shipped_headers = sorted(p.name for p in (upstream / "include/fast_float").iterdir())
    if shipped_headers != sorted(HEADERS):
        raise SystemExit(f"upstream headers changed: {shipped_headers}")
    for name in HEADERS:
        path = out / "include/fast_float" / name
        path.write_text(restructure.transform(path.read_text()))
    for name, before, after in ([] if reference else FAULTS):
        edit(out / "include/fast_float" / name, before, after)
    edit(out / "CMakeLists.txt", BENCHMARK_BLOCK, "\n")
    (out / "tests/CMakeLists.txt").write_text(TESTS_CMAKE.format(names=" ".join(KEPT_TESTS)))
    print("shipped tree built")


if __name__ == "__main__":
    main()
