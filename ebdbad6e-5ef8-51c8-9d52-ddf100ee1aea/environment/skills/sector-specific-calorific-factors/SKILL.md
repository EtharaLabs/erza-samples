---
name: sector-specific-calorific-factors
description: >-
  Convert a physical fuel quantity - barrels, short tons, cubic feet - into
  energy using the calorific value the national statistical agency publishes for
  that fuel AND the consuming sector AND the vintage year, rather than one
  generic per-fuel value. Use when a ledger of fuel volumes or tonnages has to be
  put on an energy basis and the rows differ in who burned the fuel or in when.
  Do NOT use when the source already reports the quantity in energy units, when a
  contract or regulation names the calorific value to be used (a supply contract's
  stated value governs over any published statistic), when the fuel is natural gas
  measured at a metered heating value, when the analysis is confined to one
  consuming sector in one year so the choice cannot change any relative result,
  or when the answer wanted is a physical quantity rather than an energy one.
---

# Putting a physical fuel quantity on an energy basis

A barrel is a volume and a short ton is a mass. Neither is an amount of energy.
The number that connects them is a **calorific value** - Btu per barrel, Btu per
short ton, Btu per cubic foot - and the single most common error in fuel
accounting is to treat it as one constant per fuel.

It is not. "Petroleum products" is a basket, and the basket is different for
every consuming sector: a household burns distillate and propane, a chemical
plant burns petrochemical feedstocks and still gas, a utility burns residual fuel
oil. "Coal" is a rank, and coke plants buy a metallurgical rank that a school's
boiler never sees. The energy in a barrel therefore depends on **who bought it**,
and it drifts year on year as the product mix and the coal rank shift.

National energy statistics agencies publish exactly this: a table of calorific
values indexed by fuel, by consuming sector, and by year. Use that table.

## The procedure

1. **Read the consuming sector off each row, not off the file.** A ledger keyed
   by customer class, rate class, tariff group or SIC band is keyed by consuming
   sector under another name. Map each label onto the sector the published table
   uses before doing anything else; do not pool the ledger and apply one value.

2. **Read the vintage year off each row too.** These are *measured annual
   averages*, not physical constants, and the published series is one value per
   year. A row for 2013 takes the 2013 value even if the same account has rows
   for 2019.

3. **Check how the publisher partitions the sectors, because it is not always
   the obvious partition.** Two traps recur:
   - the publisher may report **one value covering two sectors jointly** where
     the underlying quantities are too small to separate;
   - the publisher may **split one sector** where the fuel differs materially
     inside it, most often industrial coal, which is reported separately for coke
     plants and for everything else.
   Match the row to the partition the publisher actually uses, not to the sector
   name you started with.

4. **Convert row by row, then aggregate.** Multiply each row's quantity by that
   row's own value and sum afterwards. Summing quantities first and multiplying
   by one value is only correct if every row in the sum shares a sector and a
   year, and it silently produces a mix-weighted answer when they do not.

5. **Mind the unit chain.** Published quantities are often rates - thousand
   barrels *per day* - while ledgers carry annual totals; annualise with the
   calendar day count for that year before comparing. And a "thousand barrels"
   quantity times a "million Btu per barrel" value is 10^9 Btu, which is a
   *billion* Btu, not a trillion; divide by 1000 to report trillion Btu.

6. **Never substitute the aggregate row.** The same table carries an all-sector
   average, and it is a different quantity: it is the value for the national mix,
   which is dominated by whichever sector burns the most. Using it for a
   residential book is the commonest way this procedure is got wrong.

## Where the published values live, for the United States

The U.S. Energy Information Administration publishes these in the Monthly Energy
Review, Appendix A: **Table A3 for petroleum products and Table A5 for coal**.
Both are annual, both are indexed by consuming sector, and both are revised
silently - so record which vintage of the table you used.

Source: U.S. Energy Information Administration, *Monthly Energy Review*, Tables
A3 and A5, `https://www.eia.gov/totalenergy/data/monthly/` (CSV endpoints
`.../data/browser/csv.php?tbl=TA3` and `?tbl=TA5`). EIA's reuse terms grant use
and redistribution and request this acknowledgment; the EIA logo and the "Energy
Ant" character are excluded from that grant.

Read the cells from the extract of those tables supplied with the task, and
record the vintage its source note declares. This skill does not carry the cells
itself, and it should not: the cells are revised, and a copy inside a skill goes
stale. What the skill carries is what does not go stale - knowing which cell a
row is entitled to - and the shape of the two tables tells you that:

- **Table A3** is laid out sector by sector across the columns - residential,
  commercial, industrial, transportation, electric power - with an all-sector
  column beside them, one row per year. Take the column for the sector that
  consumed the fuel and the row for the year it was consumed.
- **Table A5** does not use the same partition. Coal for the residential and
  commercial sectors is reported as **one joint series**, so there is no
  commercial-only coal column to take; and industrial coal is **split**, coke
  plants carrying their own series apart from all other industrial coal. A
  ledger that says "commercial" or "industrial" must be mapped onto whichever
  of those the publisher actually reports before a value is read.

What the tables show, qualitatively, is worth knowing before you open them,
because it is what makes the sector dimension load-bearing rather than a detail:

- In any single year the sectors differ from each other by **double-digit
  percentages** for the same physical barrel. The spread across sectors is far
  larger than the spread across years within one sector.
- Coal is the wider of the two. The coke-plant rank carries **substantially more
  energy per short ton** than any other consuming sector's coal - it is the
  highest series in the table by a wide margin, and the utility series is near
  the bottom.
- The all-sector petroleum row is **not a neutral average**. It sits close to the
  transportation row, because transportation is the great bulk of US petroleum
  consumption; it is a transportation number wearing a national label, and it is
  far off the residential and commercial rows.
- The year dimension is smaller than the sector dimension but real, and it is
  **not monotone**: at least one series steps sharply between two adjacent years
  when the reported rank or product mix changes, and the residential-and-
  commercial coal series drifts down materially across the 2010s. Neither
  movement can be reconstructed by interpolating or by carrying one year's value
  across the window.

## Where these numbers come from, and what that means for using them

Each cell is a consumption-weighted average of the product-level or rank-level
calorific values over what that sector actually consumed in that year. That has
two consequences:

- The value is only valid for a quantity measured on the same basis as the
  publisher's - total petroleum products for that sector, total coal for that
  sector. Applying a sector row to a single product is wrong in both directions.
- Two published tables of the same agency must agree: the sector energy series
  and the sector physical series are related by exactly these values, and the
  all-sector row is the quantity-weighted mean of the sector rows. If a
  calculation breaks either identity, a value has been mis-selected or mistyped.

## Checks before reporting

- Every row was priced with the value for **its own** sector and **its own**
  year; no aggregate row was substituted for a sector row.
- Where the publisher reports a joint or a split sector, the ledger's rows were
  mapped onto the publisher's partition and not onto the label they arrived with.
- The conversion happened per row, before any summation.
- The unit chain closes: thousand physical units times million Btu per unit is
  billion Btu, and trillion Btu is a further factor of 1000 down.
- The implied average value for each group sits inside the published spread for
  that fuel: for the United States, roughly 4.5 to 6.0 million Btu per barrel and
  18 to 29 million Btu per short ton. These are deliberately coarse outer bounds
  on the whole of Tables A3 and A5 - wide enough to contain every sector and every
  year, and therefore far too wide to select a value with. They catch a group
  priced with the wrong fuel's value or the wrong unit; they cannot tell you which
  sector row was right. Only the published table can do that - Source: U.S. Energy
  Information Administration, *Monthly Energy Review*, Tables A3 and A5,
  `https://www.eia.gov/totalenergy/data/monthly/`.
