"""Published EIA heat contents, indexed by fuel, CONSUMING SECTOR and year.

Transcribed from the Monthly Energy Review, Appendix A: Table A3 (petroleum
products) and Table A5 (coal). Petroleum values are million Btu per barrel; coal
values are million Btu per short ton.

Source: U.S. Energy Information Administration (2026-07-29), Monthly Energy
Review, Tables A3 and A5, https://www.eia.gov/totalenergy/data/monthly/ .

This module is the ORACLE's forward implementation. The verifier deliberately
does NOT import it: `verifier/independent_energy.py` derives each graded sector's
factor from EIA series published in DIFFERENT tables, so a transcription error
here cannot agree with itself. See `verifier/test_outputs.py`.
"""

# (fuel, consuming_sector) -> {year: heat content}
#
# Two sector labels are not the obvious ones and are the reason this table cannot
# be replaced by one value per fuel:
#   * coal / commercial      - the publisher reports ONE factor covering the
#     residential and commercial sectors together (MSN CLHCKUS); there is no
#     commercial-only coal row.
#   * coal / industrial_coke_plants - coke plants carry their own factor (CLKCKUS)
#     distinct from the rest of industrial coal (CLOCKUS), because coking coal is
#     a different rank of coal.
FACTORS = {
    ("petroleum_products", "residential"): {
        2011: 4.657, 2012: 4.714, 2013: 4.648, 2014: 4.664,
        2015: 4.721, 2016: 4.631, 2017: 4.623, 2018: 4.62,
        2019: 4.54, 2020: 4.536, 2021: 4.611,
    },
    ("petroleum_products", "commercial"): {
        2011: 5.176, 2012: 5.126, 2013: 5.053, 2014: 5.016,
        2015: 5.05, 2016: 5.022, 2017: 5.006, 2018: 4.971,
        2019: 4.962, 2020: 4.889, 2021: 4.909,
    },
    ("petroleum_products", "industrial"): {
        2011: 4.887, 2012: 4.843, 2013: 4.801, 2014: 4.804,
        2015: 4.767, 2016: 4.799, 2017: 4.769, 2018: 4.664,
        2019: 4.646, 2020: 4.534, 2021: 4.524,
    },
    ("coal", "commercial"): {
        2011: 22.099, 2012: 21.3, 2013: 21.233, 2014: 21.307,
        2015: 20.699, 2016: 20.078, 2017: 19.467, 2018: 19.269,
        2019: 19.084, 2020: 18.297, 2021: 18.399,
    },
    ("coal", "industrial_coke_plants"): {
        2011: 26.299, 2012: 28.636, 2013: 28.705, 2014: 28.458,
        2015: 28.526, 2016: 28.608, 2017: 28.673, 2018: 28.608,
        2019: 28.629, 2020: 28.717, 2021: 28.666,
    },
}


def factor(fuel, consuming_sector, year):
    """The published heat content for this fuel, sector and year."""
    try:
        series = FACTORS[(fuel, consuming_sector)]
    except KeyError:
        raise KeyError("no published heat content for %r consumed by the %r "
                       "sector" % (fuel, consuming_sector))
    try:
        return series[int(year)]
    except KeyError:
        raise KeyError("no published %r / %r heat content for %r"
                       % (fuel, consuming_sector, year))


def energy_tbtu(quantity, fuel, consuming_sector, year):
    """Trillion Btu from a physical quantity.

    Petroleum quantities are thousand barrels and the factor is million Btu per
    barrel; coal quantities are thousand short tons and the factor is million Btu
    per short ton. thousand x million = 10^9 Btu, and a trillion Btu is 10^12, so
    the scale is 1/1000 for both fuels.
    """
    return float(quantity) * factor(fuel, consuming_sector, year) / 1000.0
