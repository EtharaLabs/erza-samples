"""Deterministic corpora for the conversion-cost categories (instruction.md, Conversion cost).

Usage: python cost_cases.py <out dir>   writes one "<name>.in" per corpus, lines "<kind> <text>"
Each corpus draws from fixed seeds, so every grading run measures the same inputs.
"""

import os
import random
import sys
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cases import MBITS, exact, midpoint  # noqa: E402

RATIO = ["ties_double", "ties_float", "fast_path", "near_overflow", "scaled_ties",
         "long_char_double", "long_char16_double", "long_char32_double"]
LINEAR = ["char_double", "char_float", "char16_double", "char16_float", "char32_double", "char32_float"]
LENGTHS = (2000, 8000)
OUT = sys.argv[1] if __name__ == "__main__" else "."


def write(name, lines): open(f"{OUT}/{name}.in", "w").write("".join(l + "\n" for l in lines))
def short_ties(r, kind, n, qlo, qhi):
    out = []
    while len(out) < n:
        mb = MBITS[kind]
        s = exact(midpoint(kind, r.randrange(1 << mb, 1 << (mb + 1)), r.randrange(-80, 80)))
        digits = s.replace(".", "").lstrip("0").rstrip("0")
        frac = len(s.split(".")[1]) if "." in s else 0
        q = (len(s.replace(".", "").lstrip("0")) - len(digits)) - frac if "." in s else len(s) - len(s.rstrip("0"))
        if len(digits) <= 19 and qlo <= q <= qhi: out.append(f"{kind} {digits}e{q}")
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    r = random.Random(0xC0)
    write("ties_double", short_ties(r, "d", 2000, -4, 23))
    write("ties_float", short_ties(r, "f", 2000, -17, -5))
    write("fast_path", [f"d {r.randrange((1 << 53) + 1, (1 << 54) + 1)}e{r.randrange(-22, 23)}" for _ in range(2000)])
    nearmax = []
    for kind, top in (("d", Fraction(2) ** 1024), ("f", Fraction(2) ** 128)):
        for _ in range(1000):
            x = top * Fraction(r.randrange(990000, 999990), 1000000)
            nearmax.append(f"{kind} {Decimal(x.numerator) / Decimal(x.denominator):.16e}".replace("e+", "e"))
    write("near_overflow", nearmax)
    def long_dec(r, kinds, n):
        """Long inputs the 128-bit step decides, near each type's exponent extremes."""
        out = []
        for _ in range(n):
            k = r.choice(kinds); base = {"a": "f", "p": "f", "b": "d", "q": "d"}.get(k, k)
            L = r.randrange(30, 120)
            body = str(r.randrange(1, 10)) + "".join(r.choice("0123456789") for _ in range(L - 1))
            if base == "d":
                e = r.choice([r.randrange(-305, -250), r.randrange(250, 305)])
            else:
                e = r.choice([r.randrange(-44, -33), r.randrange(30, 38)])
            out.append(f"{k} {body[0]}.{body[1:]}e{e}")
        return out
    for k, name in (("d", "long_char_double"), ("b", "long_char16_double"), ("q", "long_char32_double")):
        write(name, long_dec(r, k, 1000))
    def padded(r, kinds, n, L):
        out = []
        for _ in range(n):
            k = r.choice(kinds); base = {"a": "f", "p": "f", "b": "d", "q": "d"}.get(k, k); mb = MBITS[base]
            s = exact(midpoint(base, r.randrange(1 << mb, 1 << (mb + 1)), r.randrange(-40, 20)))
            if "." not in s: s += "."
            out.append(f"{k} {s}{'0' * (L - len(s))}")
        return out
    for L in (2000, 8000):
        for k, name in (("d", "linear_char_double"), ("f", "linear_char_float"), ("b", "linear_char16_double"), ("a", "linear_char16_float"), ("q", "linear_char32_double"), ("p", "linear_char32_float")):
            write(f"{name}_{L}", padded(random.Random(L + len(name)), k, 30, L))
    st = []
    for line in short_ties(r, "d", 2000, -4, 23):
        k, rest = line.split(" "); m, q = rest.split("e"); st.append(f"{'i' if k == 'd' else 'j'} {m} {q}")
    write("scaled_ties", st)


if __name__ == "__main__":
    main()
