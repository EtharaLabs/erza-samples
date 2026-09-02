# TRUTH.md — energy-sector-heat-content (golden trajectory)

The ordered moves a competent run makes, from opening the task to writing the
answer. Each step says **what to do and why**; **no step states what it evaluates
to**. Derived from `oracle/solve.sh` with every produced value stripped out: no
book total, no realised value, no tolerance and no golden appears anywhere in
this file.

**Method is kept; step answers are stripped.** The relations below are complete —
the indexing of the published table, the partition traps, the unit chain, the
ordering argument, and the two published identities that bind the values. What is
deliberately **not** printed here is the numeric calorific value for the five
books this instance grades. Those five series are the withheld lever the task
exists to measure, and this file is handed to a human reviewer; printing them would
make it a second answer key, which `HUMAN-AUTHOR-TO-30.md` §6.11 forbids. Two
*other* rows of the same published table — sectors this instance does not carry —
are printed in full at Step 3, so the form and the spread are concrete rather
than gestured at.

---

## What is being asked

One row per account per year, five books, each a (fuel, customer class) pair, over
an eleven-year window. Each row carries a physical quantity — thousand barrels of
petroleum products, or thousand short tons of coal — and nothing in energy units.
For each of the five books: the total energy that book delivered over the whole
window, in trillion Btu. Five graded figures, one output object, one file.

The books, the window and the reporting unit come from `/root/data/question.json`;
the rows come from `/root/data/fuel_ledger.csv`. Both are supplied.

## Delta-lever

A physical fuel quantity converts to energy with the calorific value the national
statistics agency publishes for that fuel, that **consuming sector** and that
**year** — applied per row, before any summation; the default route prices the
whole ledger with one constant per fuel.

Everything else in this task — reading a CSV, grouping, summing — is arithmetic a
competent run does correctly without help. The lever is entirely in *whether the
value is indexed by consuming sector at all*, *whether it is indexed by year*, and
*whether the row is mapped onto the partition the publisher actually uses*.

## The crux

**The crux is Step 3: every ledger row is priced with the calorific value
published for that row's own consuming sector and that row's own year, before
anything is summed.**

It has four failure surfaces. The first three are separately fatal; the fourth
is a real method error whose measured cost on this instance is smaller, and it is
recorded as such rather than asserted to be fatal:

1. **One constant per fuel.** The route available to a run that does not hold the
   table. It is what `question.json`'s `decoy_reference` block shows — an
   orientation figure, explicitly labelled as not the answer, that a run under
   time pressure copies.
2. **The aggregate row substituted for the sector row.** The same table carries an
   all-sector average and it is a different quantity: it is the national mix,
   dominated by whichever sector burns the most of that fuel. This is the nearest
   real competitor and it is one line away from the right answer.
3. **One sector row reused across sectors.** The table is found and read, and then
   a single row of it is applied to every class of that fuel. This is a distinct
   error from (1), not a milder version: it uses the publisher's own year-specific
   values and still collapses the dimension the task exists to measure.
4. **Summing before converting.** Totalling a book's quantities and multiplying by
   one value is only correct when every row in the sum shares a sector *and* a
   year, which no book here does. Measured, though: taken with the arithmetic
   mean of that book's own published series, the shortcut still lands inside the
   graded band on four of the five books, because the value moves only a few
   percent across the window inside any one book. It is a real method error and a
   reviewer should mark it, and it is **not** a route available to a run without
   the table - taking the mean of a book's series needs the series. But its
   measured outcome cost here is one case, not five, and the control ledger says
   so under `sum_quantities_then_convert_once` rather than leaving the intuition
   unchecked.

The gap between "priced by sector and year" and each of these is measured, per
route, in `../expected_values.json` under `control_gaps`.

## Step 0 — Read the ledger

Open `/root/data/fuel_ledger.csv` and `/root/data/question.json`. The CSV carries
`account_id`, `fuel`, `customer_class`, `year`, `quantity` and `quantity_unit`;
the JSON carries the books, the window, the reporting unit, the output contract
and the orientation block. The ledger has a few hundred rows over five books and
eleven years, so a solver is written and run rather than the figures being
assembled by inspection.

`account_id` is an opaque label and carries no information. The book is a
synthetic portfolio: every figure reported is a property of *this ledger*, so no
published national statistic is an answer to this task, and a figure that a model
can regenerate from its own weights is by construction not a measurement of this
ledger.

## Step 1 — Establish that the conversion is not one number per fuel

`quantity_unit` says thousand barrels or thousand short tons. Neither is an amount
of energy. The number that connects them is a calorific value, and the single most
common error in fuel accounting is to treat it as one constant per fuel.

It is not one constant, for a physical reason. "Petroleum products" is a basket
and the basket differs by who bought it — a household burns distillate and
propane, a chemical plant burns feedstocks and still gas, a utility burns residual
fuel oil. "Coal" is a rank, and coke plants buy a metallurgical rank a school
boiler never sees. The published value is therefore indexed by consuming sector,
and it drifts year on year as the mix and the rank shift.

## Step 2 — Map the ledger's labels onto the publisher's sectors

`customer_class` is the join key. It is the consuming sector under another name:
a ledger keyed by customer class, rate class or tariff group is keyed by consuming
sector. Map each label onto the sector the published table uses **before** doing
anything else, and do not pool the ledger and apply one value.

Two of this ledger's books do not map onto the obvious row, and both are decided
here rather than at Step 3:

- one of the coal books' sectors is **not published on its own** — the publisher
  reports one value covering it jointly with a neighbouring sector, because the
  underlying quantities are too small to separate;
- the other coal book sits inside a sector the publisher **splits**, because the
  fuel differs materially within it. Industrial coal is reported separately for
  coke plants and for everything else, and the two rows are far apart.

## Step 3 — Price every row by its own sector and its own year  *(crux)*

The published table gives, per fuel, per consuming sector, per year, a calorific
value in million Btu per barrel or per short ton. Apply it to **each individual
row**, keyed on that row's own `customer_class` and its own `year`. A value
published for one sector must never be applied to another, and there is no single
blanket constant.

The five series this instance grades are not printed here (see the header). Two
other rows of the same published table are, so the form and the spread are
concrete:

| consuming sector | published petroleum value at the first, middle and last year of the window, million Btu per barrel |
|---|---|
| transportation | `5.315`, `5.303`, `5.307` |
| electric power | `5.900`, `5.885`, `5.883` |

Both are from the EIA table cited under **Sources**. Note what they show: two
sectors of the same country, in the same year, differ by more than **11 percent**
on the identical physical barrel, and neither moves much across a decade while the
gap between them persists. That spread is the whole argument against a single
constant per fuel, and it is why failure surfaces 1, 2 and 3 above are distinct
errors rather than small ones.

The year dimension is smaller than the sector dimension but it is not decorative:
one of this table's coal rows steps by about **9 percent** between two consecutive
years when the reported rank changes.

## Step 4 — Convert per row, then sum

Only now: multiply each row's `quantity` by that row's own value, and sum the
results per book. Writing `E = Σ_i q_i · f_i`, the sum collapses to `(Σ_i q_i) · f`
only when every `f_i` in the book is the same, and here they differ by year within
every book. A run that totals the quantities per book and multiplies once has
computed `(Σ q_i) · f̄` for some `f̄` it chose, and no published value corresponds
to that.

How much that costs is measured rather than assumed, and the measurement is in
`../expected_values.json:control_gaps.sum_quantities_then_convert_once`: on this
ledger the shortcut, taken with the arithmetic mean of the book's own series,
still lands inside the graded band on most books. The ordering is the right method
and doing it the other way is a real error; the honest statement is that on this
instance it is not the error that decides the score.

## Step 5 — Close the unit chain

A quantity in **thousand** physical units times a value in **million** Btu per
unit is 10^9 Btu — a *billion* Btu. The contract asks for **trillion** Btu, which
is 10^12, so the row product is divided by 1000. The same factor applies to both
fuels, because both are quoted as thousand-units against million-Btu-per-unit.

Getting this wrong is a factor-of-1000 error, which the plausibility check at
Step 6 catches.

## Step 6 — Sanity-check against something that can disagree

A sound run checks before writing. Three checks that can actually fail:

- **The realised value per book.** Divide each book's energy back by that book's
  total quantity and multiply by 1000. The result is the quantity-weighted mean
  calorific value the book realised, and it must sit inside the published spread
  for that fuel — roughly 4.5 to 6.0 million Btu per barrel, and 18 to 29 million
  Btu per short ton. A book outside that has been priced with the wrong fuel's
  value or the wrong unit.
- **The publisher's own aggregation identity.** The all-sector row of the same
  table is the quantity-weighted mean of the sector rows. If the values used break
  that identity against the publisher's national quantities, one of them has been
  mis-selected or mistyped. This is the identity
  `../independent_energy.py:all_sector_identity_residual` evaluates.
- **The publisher's second table.** The same agency publishes each sector's energy
  consumption in Btu in a *different* table from the calorific values. That energy
  divided by the sector's published physical quantity must return the calorific
  value. Where the two tables are on the same basis this closes exactly; where the
  energy series excludes blended biofuel and the physical series does not, it does
  not, and that is a basis difference rather than an error.

## Step 7 — Emit the contract

Write `/root/results.json` with exactly one top-level object,
`group_energy_tbtu`, keyed `"<fuel>|<customer_class>"` exactly as those two fields
are spelled in the ledger, with one numeric, finite value per book in
`question.json`'s `groups`. The key and the number shown in the prompt are a shape
illustration: the fuel and the class in them are not in the ledger and the number
is orders of magnitude away from any book, so copying either through is not an
answer.

## Where runs break

Each route below is recomputed live in `../expected_values.json:control_gaps` and
recorded there with its distance from the reference in tolerance units.

- **One constant per fuel** — the crude-oil-equivalent and round-number coal
  values. This is the producible route for a run that does not hold the table, and
  it is what the orientation block shows.
- **The orientation block echoed** — `decoy_reference.generic_group_energy_tbtu`
  copied into the answer. It is the same route as the above, pre-computed, and the
  input labels it honestly.
- **The all-sector row substituted** — the nearest real competitor, one line off
  in the right table.
- **The power-sector row reused** — the most widely quoted row of the table
  applied to every sector.
- **One sector row reused for every sector of that fuel** — the table read, the
  sector dimension dropped.
- **A single vintage carried across the window** — right sector, wrong year.
  Measured as NON-DISCRIMINATING on part of the graded set and recorded rather
  than left undocumented; it is reachable only with the table already in hand.
- **Coke plants priced on the general industrial coal row** — the mis-selection
  the publisher's split invites.
- **Summing before converting** — a mix-weighted number no published value
  corresponds to.
- **The unit chain left open** — a figure 1000 times too large or too small.

## What cannot be done

The calorific values are not recoverable from the supplied ledger. It carries
**physical units only**: no quantity in the ledger stands in a fixed ratio to any
graded figure, so the values cannot be back-solved by division - they can only be
read from the supplied published extract. A run that claims to have derived them
from the ledger alone has not; judge such a claim on the arithmetic it shows, not
on its confidence.

Equally, the graded figures are not published anywhere. The book is a synthetic
portfolio with opaque account labels, so a figure a model regenerates from its own
weights — a national consumption total, a headline energy statistic — is not an
answer to this task even when it lands nearby.

## Sources

- **The calorific value table, and the transportation and electric power rows
  quoted at Step 3** — U.S. Energy Information Administration, *Monthly Energy
  Review*, Appendix A, Table A3 (petroleum products) and Table A5 (coal),
  `https://www.eia.gov/totalenergy/data/monthly/`, CSV endpoints
  `.../data/browser/csv.php?tbl=TA3` and `?tbl=TA5`, downloaded 2026-07-29
  (sha256 `998c0a05…aaf151d` and `b017d75b…5872ef`, recorded in
  `../../build/build_report.json:sources`). EIA publishes no DOI or report number
  for these tables; the Monthly Energy Review is the citable identity and the
  bundle records that as an open provenance field rather than inventing one.
  Source: U.S. Energy Information Administration (2026-07-29).
- **The books, the window, the reporting unit and the output contract** —
  `../../environment/data/question.json`, mirrored in `../expected_values.json`
  (`groups`, `years`, `reporting_unit`).
- **The two identities of Step 6 and the plausibility envelope** —
  `../independent_energy.py` (`implied_factor`, `solved_factor`,
  `all_sector_identity_residual`, `ENVELOPE`), the verifier's second formulation,
  which never reads the publisher's Appendix A row for the sector it is pricing.
- **The per-route separations quoted under "Where runs break"** —
  `../expected_values.json:control_gaps`, each recomputed at build time.
