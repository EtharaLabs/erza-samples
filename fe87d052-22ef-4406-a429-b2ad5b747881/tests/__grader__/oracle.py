"""The exact rational oracle for the restated contract (ROUNDING.md and FROM_CHARS.md).

A kind names the call: f and d are from_chars on char input, a and b on char16_t, p and q on
char32_t, each for float and double; j and i are integer_times_pow10 for float and double, whose
text is "<integer mantissa> <decimal exponent>" and whose errc and ptr are always 0.

expect(kind, text) returns (bits, errc, ptr): bits is the lowercase hexadecimal bit pattern the
contract requires, or "qnan" when any quiet NaN satisfies it; errc is the integer value of the
std::errc the call must return (0, EINVAL, or ERANGE); ptr is the offset one past the matched
pattern, or 0 when nothing matches. Arithmetic is exact (fractions.Fraction), so no tolerance
enters any comparison.
"""

from __future__ import annotations

import errno
from fractions import Fraction

# kind: (significand bits stored, emin, emax + 1, total width)
FORMATS = {"d": (52, -1022, 1024, 64), "f": (23, -126, 128, 32)}
SENTINEL = {"d": "c0c81c8000000000", "f": "c640e400"}  # -12345.0, the probe's starting value
BASE = {"f": "f", "d": "d", "a": "f", "b": "d", "p": "f", "q": "d", "j": "f", "i": "d"}
EINVAL = errno.EINVAL
ERANGE = errno.ERANGE
_NAN_TAIL = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")


def _match(text: str) -> tuple[int, str, str, str, str] | None:
    """The longest prefix of the pattern: (end, sign, integer digits, fraction digits, exponent)."""
    i, n = 0, len(text)
    sign = ""
    if i < n and text[i] == "-":
        sign, i = "-", i + 1
    lower = text[i:].lower()
    if lower.startswith("infinity"):
        return i + 8, sign, "inf", "", ""
    if lower.startswith("inf"):
        return i + 3, sign, "inf", "", ""
    if lower.startswith("nan"):
        j = i + 3
        if j < n and text[j] == "(":
            k = j + 1
            while k < n and text[k] in _NAN_TAIL:
                k += 1
            if k < n and text[k] == ")":
                return k + 1, sign, "nan", "", ""
        return j, sign, "nan", "", ""
    start = i
    while i < n and text[i].isdigit() and text[i].isascii():
        i += 1
    integer = text[start:i]
    fraction = ""
    if i < n and text[i] == ".":
        j = i + 1
        while j < n and text[j].isdigit() and text[j].isascii():
            j += 1
        fraction = text[i + 1 : j]
        if integer or fraction:
            i = j
    if not integer and not fraction:
        return None
    exponent = ""
    if i < n and text[i] in "eE":
        j = i + 1
        if j < n and text[j] in "+-":
            j += 1
        k = j
        while k < n and text[k].isdigit() and text[k].isascii():
            k += 1
        if k > j:
            exponent, i = text[i + 1 : k], k
    return i, sign, integer, fraction, exponent


def _bits(kind: str, x: Fraction) -> tuple[int, bool]:
    """Round a positive exact value; return (bit pattern without sign, overflowed to infinity)."""
    mbits, emin, emax, width = FORMATS[kind]
    e = x.numerator.bit_length() - x.denominator.bit_length()
    if Fraction(2) ** e > x:
        e -= 1
    if Fraction(2) ** (e + 1) <= x:
        e += 1
    e = max(e, emin)
    q = x / Fraction(2) ** (e - mbits)
    n, rem = divmod(q.numerator, q.denominator)
    rem = Fraction(rem, q.denominator)
    if rem > Fraction(1, 2) or (rem == Fraction(1, 2) and n % 2 == 1):
        n += 1
    if n == 1 << (mbits + 1):
        n >>= 1
        e += 1
    if e >= emax:
        return ((1 << (width - 1 - mbits)) - 1) << mbits, True
    if n < (1 << mbits):
        return n, False
    return ((e - emin + 1) << mbits) | (n - (1 << mbits)), False


def _scaled(kind: str, text: str) -> tuple[str, int, int]:
    """integer_times_pow10: the correctly rounded value of mantissa x 10^exponent."""
    mantissa_text, exponent_text = text.split(" ")
    mbits, _, _, width = FORMATS[kind]
    mantissa, exponent = int(mantissa_text), int(exponent_text)
    sign_bit = (1 << (width - 1)) if mantissa < 0 else 0
    if mantissa == 0:
        return f"{sign_bit:0{width // 4}x}", 0, 0
    magnitude = len(str(abs(mantissa))) + exponent
    if magnitude > 400:
        return f"{(((1 << (width - 1 - mbits)) - 1) << mbits) | sign_bit:0{width // 4}x}", 0, 0
    if magnitude < -400:
        return f"{sign_bit:0{width // 4}x}", 0, 0
    bits, _ = _bits(kind, Fraction(abs(mantissa)) * Fraction(10) ** exponent)
    return f"{bits | sign_bit:0{width // 4}x}", 0, 0


def expect(kind: str, text: str) -> tuple[str, int, int]:
    call, kind = kind, BASE[kind]
    if call in "ij":
        return _scaled(kind, text)
    mbits, _, _, width = FORMATS[kind]
    match = _match(text)
    if match is None:
        return SENTINEL[kind], EINVAL, 0
    end, sign, integer, fraction, exponent = match
    sign_bit = (1 << (width - 1)) if sign else 0
    infinity = ((1 << (width - 1 - mbits)) - 1) << mbits
    if integer == "inf":
        return f"{infinity | sign_bit:0{width // 4}x}", 0, end
    if integer == "nan":
        return "qnan", 0, end
    digits = (integer + fraction).lstrip("0")
    if not digits:
        return f"{sign_bit:0{width // 4}x}", 0, end
    scale = (int(exponent) if exponent else 0) - len(fraction)
    stripped = digits.rstrip("0")
    scale += len(digits) - len(stripped)
    magnitude = scale + len(stripped)  # the value lies in [10^(magnitude-1), 10^magnitude)
    if magnitude > 400:
        return f"{infinity | sign_bit:0{width // 4}x}", ERANGE, end
    if magnitude < -400:
        return f"{sign_bit:0{width // 4}x}", ERANGE, end
    x = Fraction(int(stripped)) * Fraction(10) ** scale
    bits, overflowed = _bits(kind, x)
    errc = ERANGE if overflowed or bits == 0 else 0
    return f"{bits | sign_bit:0{width // 4}x}", errc, end


def is_quiet_nan(kind: str, bits: str) -> bool:
    mbits, _, _, width = FORMATS[BASE[kind]]
    value = int(bits, 16)
    exponent_all_ones = ((value >> mbits) & ((1 << (width - 1 - mbits)) - 1)) == (1 << (width - 1 - mbits)) - 1
    return exponent_all_ones and (value >> (mbits - 1)) & 1 == 1


def agrees(kind: str, text: str, record: tuple[str, int, int]) -> bool:
    bits, errc, ptr = expect(kind, text)
    got_bits, got_errc, got_ptr = record
    if (got_errc, got_ptr) != (errc, ptr):
        return False
    if bits == "qnan":
        return is_quiet_nan(kind, got_bits)
    return got_bits == bits
