"""Reference solution.

Reads the shipped stage series, converts every gage height to a discharge through
that gauge's own rating table, then reports the time-weighted mean over each block.
Nothing is read from the verifier and no golden is embedded - the answer is derived.
"""

import csv
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rating import load_rating, discharge_at, block_mean  # noqa: E402

DATA = "/root/data"
RATINGS = os.path.join(HERE, "ratings")
OUT = "/root/results.json"


def epoch(iso):
    return dt.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=dt.timezone.utc).timestamp()


def main():
    with open(os.path.join(DATA, "question.json")) as fh:
        question = json.load(fh)

    series = {}
    with open(os.path.join(DATA, "stage_series.csv")) as fh:
        for row in csv.DictReader(fh):
            series.setdefault(row["gauge_id"], []).append(
                (epoch(row["datetime_utc"]), float(row["gage_height_ft"])))

    discharge = {}
    for gauge, points in series.items():
        points.sort()
        rows = load_rating(os.path.join(RATINGS, "rating_%s.tsv" % gauge))
        discharge[gauge] = ([p[0] for p in points],
                            [discharge_at(rows, p[1]) for p in points])

    out = {}
    for block in question["blocks"]:
        gauge = block["gauge_id"]
        times, q = discharge[gauge]
        value = block_mean(times, q, epoch(block["start_utc"]), epoch(block["end_utc"]))
        out.setdefault(gauge, {})[block["block_id"]] = value

    with open(OUT, "w") as fh:
        json.dump({"block_mean_discharge_cfs": out}, fh, indent=2)
        fh.write("\n")


if __name__ == "__main__":
    main()
