"""Restructure the fast_float headers: drop every comment and rename the conversion helpers.

The result behaves identically to the input; only comments and helper names change.
Usage: python restructure.py <include/fast_float dir>   rewrites each header in place.
"""

import re
import sys
from pathlib import Path

RENAME = {
    'add_native': 'mul_add_limb',
    'clinger_fast_path_impl': 'exact_small_product',
    'compute_error': 'scaled_binary',
    'compute_error_scaled': 'scaled_binary_shifted',
    'compute_float': 'nearest_binary',
    'compute_product_approximation': 'pow5_product',
    'digit_comp': 'exact_compare',
    'invalid_am_bias': 'unresolved_bias',
    'is_truncated': 'has_nonzero_digits',
    'minimal_nineteen_digit_integer': 'significand_limit',
    'negative_digit_comp': 'exact_compare_neg',
    'parse_eight_digits': 'take_eight_digits',
    'parse_mantissa': 'load_significand',
    'parse_number_slow_path': 'reparse_with_spans',
    'parse_one_digit': 'take_digit',
    'positive_digit_comp': 'exact_compare_pos',
    'powers_of_ten_uint64': 'pow10_u64',
    'round_down': 'truncate_bits',
    'round_nearest_tie_even': 'round_half_even',
    'round_up_bigint': 'bump_last_digit',
    'scientific_exponent': 'decimal_magnitude',
    'skip_zeros': 'skip_leading_zeros',
    'to_extended': 'unpack_float',
    'to_extended_halfway': 'midpoint_above',
}


def strip_comments(text):
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1]); i = j + 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
            out.append("\x00")
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            out.append("\x00")
        else:
            out.append(c); i += 1
    lines, result = "".join(out).split("\n"), []
    for line in lines:
        had = "\x00" in line
        line = line.replace("\x00", "").rstrip()
        if had and not line.strip():
            line = ""
        if line == "" and result and result[-1] == "":
            continue
        result.append(line)
    return "\n".join(result)


PATTERN = re.compile(r"\b(" + "|".join(sorted(RENAME, key=len, reverse=True)) + r")\b")


def transform(text):
    return PATTERN.sub(lambda m: RENAME[m.group(1)], strip_comments(text))


def main():
    for path in sorted(Path(sys.argv[1]).glob("*.h")):
        path.write_text(transform(path.read_text()))


if __name__ == "__main__":
    main()
