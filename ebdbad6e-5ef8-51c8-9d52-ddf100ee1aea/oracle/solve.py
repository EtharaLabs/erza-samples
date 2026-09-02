"""Reference solution. Derives every graded figure from the shipped ledger."""

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import heat_content  # noqa: E402

DATA = os.environ.get("DATA_DIR", "/root/data")
OUT = os.environ.get("RESULTS_PATH", "/root/results.json")


def main():
    with open(os.path.join(DATA, "question.json")) as fh:
        question = json.load(fh)
    group_energy = {"%s|%s" % (g["fuel"], g["customer_class"]): 0.0
                    for g in question["groups"]}

    with open(os.path.join(DATA, "fuel_ledger.csv")) as fh:
        for row in csv.DictReader(fh):
            # the factor is chosen by fuel AND consuming sector AND year, one row
            # at a time; nothing is pooled before the conversion
            energy = heat_content.energy_tbtu(
                row["quantity"], row["fuel"], row["customer_class"], row["year"])
            group_energy["%s|%s" % (row["fuel"], row["customer_class"])] += energy

    with open(OUT, "w") as fh:
        json.dump({"group_energy_tbtu": group_energy}, fh, indent=2, sort_keys=True)
    print("wrote %s" % OUT)


if __name__ == "__main__":
    main()
