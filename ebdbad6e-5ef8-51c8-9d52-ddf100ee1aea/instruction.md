Task:
An energy-services firm is closing out its delivered-fuel book for its United
States accounts and has to restate it on an energy basis. Report, for each of the
five books, the total energy the firm delivered over the whole period covered by
the ledger.

Input (`/root/data/`):

1. `fuel_ledger.csv` - one row per account per year, with a header and the
   columns `account_id`, `fuel`, `customer_class`, `year`, `quantity` and
   `quantity_unit`. `account_id` is an opaque label. `fuel` says what was
   delivered. `customer_class` says what kind of customer the account is.
   `quantity` is what was physically delivered to that account in that year, in
   the units named by `quantity_unit`. Accounts open and close, so not every
   account appears in every year.

2. `heat_content_published.csv` - the published annual heat contents for these
   fuels: one row per fuel, consuming sector and year, in the sector partition
   the publisher uses, with the unit named per row.
   `heat_content_published.SOURCES.txt` records the source and vintage.

3. `question.json` - the five books to report (`groups`, each a `fuel` and a
   `customer_class`), the years the ledger covers, the unit to report in, the
   output contract, and a `decoy_reference` block. The decoy block prices the
   whole ledger with one flat number per fuel; it is supplied for orientation
   only.

The energy a barrel or a short ton actually delivers is not a fixed constant. It
is measured and published annually by the national statistics agency for this
industry, and it is published at a finer grain than "one number per fuel". Which
value applies to a given row is a property of that row. The table the agency
publishes for these fuels is supplied beside the ledger as
`heat_content_published.csv`, at the grain the agency publishes it; its source
and vintage are recorded in `heat_content_published.SOURCES.txt`.

Report energy in trillion Btu. A book's figure is the total over every row of the
ledger belonging to that book, across all years the ledger covers.

Output:
Write `/root/results.json` with exactly:

```json
{"group_energy_tbtu": {"kerosene|municipal": 999999.9}}
```

- `group_energy_tbtu` - for every entry in `question.json`'s `groups`, the total
  energy delivered to that book over the whole ledger, in trillion Btu. Key each
  entry `"<fuel>|<customer_class>"`, exactly as those two fields are spelled in
  the ledger.

(The key and the number above are placeholders that show the JSON shape only.
They are not the answer: `kerosene` is not a fuel in the ledger, `municipal` is
not a customer class in it, and `999999.9` is roughly ten thousand times the
largest correct figure.)

Scoring: one test case per book, 5 in total. A case passes iff the reported value
is within 1.0% of the reference. Score = cases passed / 5.

The container has Python 3 with numpy installed. No network access.
