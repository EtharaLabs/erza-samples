"""Verifier-side SECOND FORMULATION. Deliberately not the oracle's code.

The oracle looks each graded sector's heat content up in EIA's Appendix A row for
that sector and multiplies. This module never reads Appendix A's row for the
sector it is pricing. It derives every graded sector's factor from EIA series
published in DIFFERENT tables, by two routes:

  1. IMPLIED FROM A SEPARATELY PUBLISHED ENERGY SERIES. EIA publishes each
     sector's energy consumption in Btu in the Table 2.x series, independently of
     Appendix A's heat contents. Dividing that energy by the same sector's
     published physical quantity gives the factor back:

       petroleum / residential  = Table 2.2 residential petroleum energy
                                  / Table 3.7a residential barrels
       coal / commercial        = Table 2.3 commercial coal energy
                                  / Table 6.2 commercial tons
       coal / coke plants       = (Table 2.4 industrial coal energy
                                   - other-industrial tons at their own factor)
                                  / Table 6.2 coke-plant tons

  2. SOLVED FROM THE PUBLISHED ALL-SECTOR IDENTITY. EIA's all-sector petroleum
     heat content is the barrel-weighted mean of the five sector heat contents.
     Solving that identity for one sector, holding the other four, recovers it:

       f_s = (f_all * sum_k Q_k - sum_{k != s} Q_k f_k) / Q_s

     This is the route for petroleum / commercial and petroleum / industrial,
     because EIA's published petroleum ENERGY series for those two sectors
     excludes blended biofuel while the barrels do not, so route 1's ratio is on
     a different basis there (measured: -3.0 and -0.2 percent, recorded in
     `build/build_report.json:independent_verification`).

Both routes read only `anchor.csv`, which carries the separately published series
and no Appendix A row for any graded sector. `_TRANSCRIBED` below is a second,
independent transcription of the graded rows; it is used ONLY to supply the four
OTHER sectors when route 2 solves for a fifth, never for the sector being solved.

A mistyped factor therefore cannot agree with itself: it would have to be wrong
in the oracle, wrong in this transcription, and wrong in EIA's separately
published energy series in exactly the same way.

Source: U.S. Energy Information Administration (2026-07-29), Monthly Energy
Review, Tables 2.2, 2.3, 2.4, 3.7a, 3.7b, 3.7c, 6.2, A3 and A5,
https://www.eia.gov/totalenergy/data/monthly/ .
"""
from __future__ import annotations

import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ANCHOR = os.path.join(HERE, "anchor.csv")

YEARS = list(range(2011, 2022))

# Independent re-transcription of the five graded Appendix A rows. Used only to
# hold the OTHER sectors while route 2 solves for one of them.
_TRANSCRIBED = {
    ("petroleum_products", "residential"): {
        2011: 4.657, 2012: 4.714, 2013: 4.648, 2014: 4.664,
        2015: 4.721, 2016: 4.631, 2017: 4.623, 2018: 4.620,
        2019: 4.540, 2020: 4.536, 2021: 4.611,
    },
    ("petroleum_products", "commercial"): {
        2011: 5.176, 2012: 5.126, 2013: 5.053, 2014: 5.016,
        2015: 5.050, 2016: 5.022, 2017: 5.006, 2018: 4.971,
        2019: 4.962, 2020: 4.889, 2021: 4.909,
    },
    ("petroleum_products", "industrial"): {
        2011: 4.887, 2012: 4.843, 2013: 4.801, 2014: 4.804,
        2015: 4.767, 2016: 4.799, 2017: 4.769, 2018: 4.664,
        2019: 4.646, 2020: 4.534, 2021: 4.524,
    },
    ("coal", "commercial"): {
        2011: 22.099, 2012: 21.300, 2013: 21.233, 2014: 21.307,
        2015: 20.699, 2016: 20.078, 2017: 19.467, 2018: 19.269,
        2019: 19.084, 2020: 18.297, 2021: 18.399,
    },
    ("coal", "industrial_coke_plants"): {
        2011: 26.299, 2012: 28.636, 2013: 28.705, 2014: 28.458,
        2015: 28.526, 2016: 28.608, 2017: 28.673, 2018: 28.608,
        2019: 28.629, 2020: 28.717, 2021: 28.666,
    },
}

# Domain-plausible envelope for a published heat content. A value outside this is
# a unit error, not a hard task.
ENVELOPE = {"petroleum_products": (4.0, 6.5), "coal": (14.0, 32.0)}

# quantity series published as a DAILY RATE and therefore annualised here
_DAILY_RATE = {"PARCPUS", "PACCPUS", "PAICPUS", "PAACPUS", "PAEIZUS"}

# petroleum sectors of the published all-sector identity: (quantity, factor key)
_PETROLEUM_MIX = [
    ("PARCPUS", ("petroleum_products", "residential")),
    ("PACCPUS", ("petroleum_products", "commercial")),
    ("PAICPUS", ("petroleum_products", "industrial")),
    ("PAACPUS", "PAACKUS"),
    ("PAEIZUS", "PAEIKUS"),
]


class MissingAnchor(Exception):
    """The external anchor is absent. Never a skip - always a hard failure."""


def days_in_year(year: int) -> int:
    year = int(year)
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    return 366 if leap else 365


_CACHE: dict = {}


def anchor(path: str = ANCHOR) -> dict:
    """{msn: {year: value}} from the separately published EIA series."""
    if path in _CACHE:
        return _CACHE[path]
    if not os.path.exists(path):
        raise MissingAnchor(
            "anchor.csv is missing from %s - the independent formulation has no "
            "external series to derive from and MUST fail rather than skip" % path)
    out: dict = {}
    with open(path) as fh:
        for row in csv.DictReader(fh):
            out.setdefault(row["series"], {})[int(row["year"])] = float(row["value"])
    if len(out) < 18:
        raise MissingAnchor("anchor.csv carries only %d series; expected 18"
                            % len(out))
    _CACHE[path] = out
    return out


def national_quantity(msn: str, year: int) -> float:
    """Annual physical quantity, annualising the series published as daily rates."""
    value = anchor()[msn][int(year)]
    return value * days_in_year(year) if msn in _DAILY_RATE else value


# --------------------------------------------------------------------------- #
# route 1: implied by a separately published energy series
# --------------------------------------------------------------------------- #

def implied_factor(fuel: str, sector: str, year: int):
    """The factor implied by EIA's own published energy series, or None when that
    series is on a different basis (petroleum commercial and industrial)."""
    year = int(year)
    a = anchor()
    if (fuel, sector) == ("petroleum_products", "residential"):
        return a["PARCBUS"][year] * 1000.0 / national_quantity("PARCPUS", year)
    if (fuel, sector) == ("coal", "commercial"):
        return a["CLCCBUS"][year] * 1000.0 / national_quantity("CLCCPUS", year)
    if (fuel, sector) == ("coal", "industrial_coke_plants"):
        other = national_quantity("CLOCPUS", year) * a["CLOCKUS"][year]
        return (a["CLICBUS"][year] * 1000.0 - other) / national_quantity("CLKCPUS", year)
    return None


# --------------------------------------------------------------------------- #
# route 2: solved from the published all-sector heat-content identity
# --------------------------------------------------------------------------- #

def _petroleum_factor_for_mix(entry, year: int) -> float:
    if isinstance(entry, str):
        return anchor()[entry][int(year)]
    return _TRANSCRIBED[entry][int(year)]


def solved_factor(fuel: str, sector: str, year: int) -> float:
    """Solve the published all-sector identity for one petroleum sector.

    The sector being solved never contributes its own factor to the arithmetic.
    """
    if fuel != "petroleum_products":
        raise KeyError("the all-sector identity route is petroleum-only, not %r"
                       % ((fuel, sector),))
    year = int(year)
    target = (fuel, sector)
    total_q = sum(national_quantity(q, year) for q, _f in _PETROLEUM_MIX)
    rest = sum(national_quantity(q, year) * _petroleum_factor_for_mix(f, year)
               for q, f in _PETROLEUM_MIX if f != target)
    target_q = [q for q, f in _PETROLEUM_MIX if f == target]
    if not target_q:
        raise KeyError("%r is not a sector of the published petroleum mix" % (target,))
    all_sector = anchor()["PATCKUS"][year]
    return (all_sector * total_q - rest) / national_quantity(target_q[0], year)


def independent_factor(fuel: str, sector: str, year: int) -> float:
    """The factor for this fuel, sector and year, derived without reading the
    publisher's Appendix A row for that sector."""
    implied = implied_factor(fuel, sector, year)
    if implied is not None:
        return implied
    return solved_factor(fuel, sector, year)


def route_of(fuel: str, sector: str) -> str:
    return ("implied_from_published_energy_series"
            if implied_factor(fuel, sector, YEARS[0]) is not None
            else "solved_from_published_all_sector_identity")


# --------------------------------------------------------------------------- #
# the identity itself, as a standing tripwire on every transcribed factor
# --------------------------------------------------------------------------- #

def all_sector_identity_residual(fuel: str, year: int) -> float:
    """Relative gap between the quantity-weighted mean of the sector factors and
    EIA's separately published ALL-SECTOR factor for that fuel and year.

    A typo in ANY sector factor - including the two the graded ledger prices
    through route 2 - moves this. It is the tripwire that a single-route check
    cannot provide.
    """
    year = int(year)
    a = anchor()
    if fuel == "petroleum_products":
        mix = [(national_quantity(q, year), _petroleum_factor_for_mix(f, year))
               for q, f in _PETROLEUM_MIX]
        published = a["PATCKUS"][year]
    elif fuel == "coal":
        mix = [
            (national_quantity("CLCCPUS", year),
             _TRANSCRIBED[("coal", "commercial")][year]),
            (national_quantity("CLKCPUS", year),
             _TRANSCRIBED[("coal", "industrial_coke_plants")][year]),
            (national_quantity("CLOCPUS", year), a["CLOCKUS"][year]),
            (national_quantity("CLEIPUS", year), a["CLEIKUS"][year]),
        ]
        published = a["CLTCKUS"][year]
    else:
        raise KeyError(fuel)
    weighted = sum(q * f for q, f in mix) / sum(q for q, _f in mix)
    return (weighted - published) / published


# --------------------------------------------------------------------------- #
# grading through the independent factors
# --------------------------------------------------------------------------- #

def read_ledger(data_dir: str) -> list:
    with open(os.path.join(data_dir, "fuel_ledger.csv")) as fh:
        return list(csv.DictReader(fh))


def recompute(rows: list, factor_fn=None) -> dict:
    """Every graded figure, aggregated year-major rather than row-major."""
    factor_fn = factor_fn or independent_factor
    by_cell: dict = {}
    for row in rows:
        cell = (row["fuel"], row["customer_class"], int(row["year"]))
        by_cell[cell] = by_cell.get(cell, 0.0) + float(row["quantity"])

    out: dict = {}
    for (fuel, sector, year), quantity in by_cell.items():
        energy = quantity * factor_fn(fuel, sector, year) / 1000.0
        key = "group-%s-%s" % (fuel, sector)
        out[key] = out.get(key, 0.0) + energy
    return out
