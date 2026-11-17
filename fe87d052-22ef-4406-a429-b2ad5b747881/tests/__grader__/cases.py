"""Deterministic case generators, one per graded category.

Each generator draws from its own fixed seed, so every grading run feeds the same inputs and the
oracle recomputes every expected result at grading time; no expected value is stored anywhere.

Usage: python cases.py <category> <out file>   writes lines "<f|d> <text>"
"""

from __future__ import annotations

import random
import sys
from decimal import Decimal, getcontext
from fractions import Fraction

getcontext().prec = 4000
MBITS = {"d": 52, "f": 23}
EMIN = {"d": -1074, "f": -149}  # exponent of the smallest subnormal's unit
MAXFIN = {"d": (2 - Fraction(1, 2**52)) * Fraction(2) ** 1023, "f": (2 - Fraction(1, 2**23)) * Fraction(2) ** 127}
HALF_ULP_TOP = {"d": Fraction(2) ** 970, "f": Fraction(2) ** 103}


def exact(x: Fraction) -> str:
    """The exact decimal expansion of a dyadic rational, without exponent."""
    s = format(Decimal(x.numerator) / Decimal(x.denominator), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def sig_digits(s: str) -> int:
    return len(s.replace(".", "").replace("-", "").lstrip("0").rstrip("0"))


def respell(rng: random.Random, s: str) -> str:
    """Rewrite a plain decimal string in an equivalent form: scientific, padded, or as is."""
    choice = rng.randrange(4)
    if choice == 0 or "e" in s:
        return s
    intpart, _, frac = s.partition(".")
    digits = (intpart + frac).lstrip("0")
    if not digits:
        return s
    point = len(intpart) - (len(intpart + frac) - len((intpart + frac).lstrip("0")))
    if choice == 1:
        return f"{digits[0]}.{digits[1:] or '0'}e{point - 1}"
    if choice == 2:
        return f"0.{digits}e{point}"
    return f"000{s}{'0' * rng.randrange(1, 4) if '.' in s else ''}"


def midpoint(kind: str, m: int, e: int) -> Fraction:
    """The exact value halfway between m * 2^e and (m + 1) * 2^e."""
    return Fraction(2 * m + 1) * Fraction(2) ** (e - 1)


def short_ties(rng: random.Random, kind: str, count: int, elo: int, ehi: int) -> list[str]:
    mb = MBITS[kind]
    out: list[str] = []
    while len(out) < count:
        m = rng.randrange(1 << mb, 1 << (mb + 1))
        s = exact(midpoint(kind, m, rng.randrange(elo, ehi)))
        if sig_digits(s) <= 19:
            out.append(respell(rng, s))
    return out


def nudge(s: str, delta: int) -> str:
    """Move the last significant digit of a plain decimal string by delta (one unit), keeping its length."""
    body = s.replace(".", "")
    point = s.find(".")
    value = int(body) + delta
    if value <= 0:
        return s
    text = str(value).rjust(len(body), "0")
    return text if point < 0 else f"{text[:point]}.{text[point:]}"


def c1() -> list[str]:
    rng = random.Random(0xC1)
    cases = [f"d {s}" for s in short_ties(rng, "d", 3000, -30, 45)]
    for _ in range(1500):
        s = exact(midpoint("d", rng.randrange(1 << 52, 1 << 53), rng.randrange(-20, 30)))
        if sig_digits(s) <= 18 and "." not in s[-1:]:
            cases.append(f"d {nudge(s, rng.choice((-1, 1)))}")
    for _ in range(2500):
        n = (1 << 53) + 2 * rng.randrange(0, 1 << 52) + 1  # every odd integer in (2^53, 2^54) is a tie
        cases.append(f"d {respell(rng, str(n))}")
    return cases


def c2() -> list[str]:
    rng = random.Random(0xC2)
    cases = [f"f {s}" for s in short_ties(rng, "f", 3500, -60, 40)]
    for _ in range(1500):
        s = exact(midpoint("f", rng.randrange(1 << 23, 1 << 24), rng.randrange(-50, 30)))
        if sig_digits(s) <= 18:
            cases.append(f"f {nudge(s, rng.choice((-1, 1)))}")
    for _ in range(1500):
        shift = rng.randrange(0, 7)
        n = ((1 << 24) + 2 * rng.randrange(0, 1 << 23) + 1) << shift
        cases.append(f"f {respell(rng, str(n))}")
    return cases


def c3() -> list[str]:
    rng = random.Random(0xC3)
    cases = []
    for i in range(20000):
        m = rng.randrange((1 << 53) + 1, (1 << 54) + 1) if i % 2 == 0 else rng.randrange(1, (1 << 53) + 1)
        e = rng.randrange(-22, 23)
        cases.append(f"d {m}e{e}" if e else f"d {m}")
    return cases


def c4() -> list[str]:
    rng = random.Random(0xC4)
    cases = []
    for kind in ("d", "f"):
        top = MAXFIN[kind]
        bound = top + HALF_ULP_TOP[kind]
        tiny = Fraction(2) ** EMIN[kind]
        anchors = [top, bound, bound - Fraction(1, 10**6) * tiny, top - HALF_ULP_TOP[kind]]
        for value in anchors:
            for sign in ("", "-"):
                cases.append(f"{kind} {sign}{exact(value)}")
        for _ in range(900):
            x = top + HALF_ULP_TOP[kind] * Fraction(rng.randrange(-40000, 40000), 10000)
            digits = rng.randrange(2, 40)
            d = Decimal(x.numerator) / Decimal(x.denominator)
            sign = rng.choice(("", "-"))
            cases.append(f"{kind} {sign}{d:.{digits}e}".replace("e+", "e"))
        for _ in range(300):
            x = top * Fraction(rng.randrange(10001, 60000), 10000)
            d = Decimal(x.numerator) / Decimal(x.denominator)
            cases.append(f"{kind} {rng.choice(('', '-'))}{d:.{rng.randrange(1, 25)}e}".replace("e+", "e"))
        half = tiny / 2
        for value in (half, half + tiny / 1000, half - tiny / 1000, tiny / 3, tiny, tiny * 3 / 2):
            for sign in ("", "-"):
                cases.append(f"{kind} {sign}{exact(value)}")
        for _ in range(300):
            x = half * Fraction(rng.randrange(1, 40000), 20000)
            d = Decimal(x.numerator) / Decimal(x.denominator)
            cases.append(f"{kind} {rng.choice(('', '-'))}{d:.{rng.randrange(1, 30)}e}".replace("e+", "e"))
        for text in ("1e400", "1e-400", "1e99999999999999999999", "1e-99999999999999999999", "0e99999", "123456789e-500"):
            for sign in ("", "-"):
                cases.append(f"{kind} {sign}{text}")
    return cases


def c5() -> list[str]:
    rng = random.Random(0xC5)
    cases = []
    for kind, (elo, ehi) in (("d", (-60, 60)), ("f", (-60, 40))):
        mb = MBITS[kind]
        for _ in range(1200):
            x = midpoint(kind, rng.randrange(1 << mb, 1 << (mb + 1)), rng.randrange(elo, ehi))
            s = exact(x)
            if sig_digits(s) < 20:
                s = s + ("" if "." in s else ".") + "0" * (20 - sig_digits(s)) + "0"
            cases.append(f"{kind} {s}")
            above = exact(x + Fraction(2) ** (rng.randrange(elo, ehi) - 120))
            cases.append(f"{kind} {above}")
            below = exact(x - Fraction(2) ** (rng.randrange(elo, ehi) - 120))
            cases.append(f"{kind} {below}")
        for _ in range(400):
            digits = rng.randrange(20, 800)
            body = str(rng.randrange(1, 10)) + "".join(rng.choice("0123456789") for _ in range(digits - 1))
            point = rng.randrange(1, len(body))
            cases.append(f"{kind} {body[:point]}.{body[point:]}e{rng.randrange(-30, 30)}")
    return [c for c in cases if sig_digits(c.split(" ", 1)[1].split("e")[0]) >= 20]


def c6() -> list[str]:
    rng = random.Random(0xC6)
    cases = []
    for kind in ("d", "f"):
        mb, e0 = MBITS[kind], EMIN[kind]
        for _ in range(900):
            top = rng.random() < 0.6
            k = rng.randrange((1 << (mb - 1)) if top else 1, 1 << mb)
            tie = Fraction(2 * k + 1) * Fraction(2) ** (e0 - 1)
            cases.append(f"{kind} {exact(tie)}")
            cases.append(f"{kind} {exact(tie + Fraction(2) ** (e0 - rng.randrange(6, 60)))}")
            cases.append(f"{kind} {exact(tie - Fraction(2) ** (e0 - rng.randrange(6, 60)))}")
            value = Fraction(k) * Fraction(2) ** e0
            d = Decimal(value.numerator) / Decimal(value.denominator)
            cases.append(f"{kind} {d:.{rng.randrange(3, 18)}e}".replace("e+", "e"))
        boundary = Fraction(2) ** (e0 + mb)  # the smallest normal value
        for value in (boundary, boundary - Fraction(2) ** (e0 - 1), boundary - Fraction(2) ** e0):
            cases.append(f"{kind} {exact(value)}")
    return cases


def c7() -> list[str]:
    rng = random.Random(0xC7)
    cases = []
    for _ in range(10000):
        kind = rng.choice("df")
        if kind == "d":
            x = rng.uniform(-1, 1) * 10.0 ** rng.randrange(-300, 300)
            text = rng.choice((repr(x), f"{x:.17g}", f"{x:.10e}"))
        else:
            x = rng.uniform(-1, 1) * 10.0 ** rng.randrange(-37, 38)
            text = rng.choice((f"{x:.9g}", f"{x:.6e}", f"{x:.12g}"))
        cases.append(f"{kind} {text}")
    for _ in range(4000):
        kind = rng.choice("df")
        digits = "".join(rng.choice("0123456789") for _ in range(rng.randrange(1, 30)))
        point = rng.randrange(0, len(digits) + 1)
        exp = rng.choice(("", f"e{rng.randrange(-60, 60)}", f"E+{rng.randrange(0, 30)}"))
        cases.append(f"{kind} {rng.choice(('', '-'))}{digits[:point]}.{digits[point:]}{exp}")
    odd = [
        "+1", " 1", "e5", "-", ".", "", "abc", "+inf", "-.e5", ".e1", "--1", "\t2",
        "1e", "1e+", "1e-", "1.5e3abc", "0x10", "12,5", "5.", ".5", "-0", "-0.0e7", "0e0",
        "inf", "INF", "-Infinity", "infinit", "infx", "nan", "NaN", "-nan", "nan(abc_1)", "nan(", "nan(a b)",
        "1.2.3", "007", "1_000",
    ]
    for kind in "df":
        cases.extend(f"{kind} {text}" for text in odd)
    return cases


MAX_DIGITS = {"d": 769, "f": 114}  # the significant digits the long-input fallback reads before it rounds


def scientific(digits: str, exponent: int) -> str:
    """A significant digit string and the decimal exponent of its last digit, as d.ddde<n>."""
    return f"{digits[0]}.{digits[1:] or '0'}e{exponent + len(digits) - 1}"


def c8() -> list[str]:
    """The wide-character entry points (char16_t and char32_t) and integer_times_pow10."""
    rng = random.Random(0xC8)
    cases = []
    for wide, kind in (("a", "f"), ("b", "d"), ("p", "f"), ("q", "d")):
        mb, e0 = MBITS[kind], EMIN[kind]
        elo, ehi = (-60, 60) if kind == "d" else (-60, 40)
        for _ in range(250):
            x = midpoint(kind, rng.randrange(1 << mb, 1 << (mb + 1)), rng.randrange(elo, ehi))
            s = exact(x)
            cases.append(f"{wide} {s}")
            cases.append(f"{wide} {exact(x + Fraction(2) ** (rng.randrange(elo, ehi) - 120))}")
            pad = MAX_DIGITS[kind] + rng.randrange(8, 40) - sig_digits(s)
            if pad > 0:
                cases.append(f"{wide} {s if '.' in s else s + '.'}{'0' * pad}")
        for _ in range(150):
            k = rng.randrange(1, 1 << mb)
            tie = Fraction(2 * k + 1) * Fraction(2) ** (e0 - 1)
            cases.append(f"{wide} {exact(tie)}")
            cases.append(f"{wide} {exact(tie - Fraction(2) ** (e0 - rng.randrange(6, 60)))}")
        for _ in range(200):
            m = rng.randrange(1 << mb, 1 << (mb + 1))
            s = exact(midpoint(kind, m, rng.randrange(elo, ehi)))
            if sig_digits(s) <= 19:
                cases.append(f"{wide} {respell(rng, s)}")
        for _ in range(300):
            x = rng.uniform(-1, 1) * 10.0 ** (rng.randrange(-300, 300) if kind == "d" else rng.randrange(-37, 38))
            cases.append(f"{wide} {repr(x) if kind == 'd' else format(x, '.9g')}")
        cases.extend(f"{wide} {text}" for text in ("-0", "inf", "-nan", "1e400", "1e-400", "abc", "1.5e3x", ".5", "007"))
    for scaled, kind in (("j", "f"), ("i", "d")):
        mb = MBITS[kind]
        for _ in range(600):
            m = rng.randrange(1, 1 << 64)
            e = rng.randrange(-340, 320) if kind == "d" else rng.randrange(-60, 50)
            cases.append(f"{scaled} {m} {e}")
        for _ in range(400):
            m = rng.randrange(1, 1 << 63)
            e = rng.randrange(-30, 30)
            cases.append(f"{scaled} -{m} {e}")
        for _ in range(400):
            m = rng.randrange(1, (1 << (mb + 2)) + 1)
            cases.append(f"{scaled} {m} {rng.randrange(-22, 23)}")
        for _ in range(400):
            s = exact(midpoint(kind, rng.randrange(1 << mb, 1 << (mb + 1)), rng.randrange(-30, 30)))
            digits = s.replace(".", "").lstrip("0")
            if len(digits.rstrip("0")) <= 19:
                stripped = digits.rstrip("0")
                point = s.find(".")
                frac = len(s) - point - 1 if point >= 0 else 0
                cases.append(f"{scaled} {stripped} {len(digits) - len(stripped) - frac}")
        for m, e in ((0, 0), (1, 400), (1, -400), (17976931348623157, 292), (17976931348623159, 292), (34028236, 31), (34028237, 31), (1, -45), (7, -46)):
            cases.append(f"{scaled} {m} {e}")
    return cases


GENERATORS = {"C1": c1, "C2": c2, "C3": c3, "C4": c4, "C5": c5, "C6": c6, "C7": c7, "C8": c8}


def main() -> None:
    category, out = sys.argv[1], sys.argv[2]
    lines = GENERATORS[category]()
    with open(out, "w", encoding="utf-8") as handle:
        handle.write("".join(line + "\n" for line in lines))


if __name__ == "__main__":
    main()
