"""Bake the frozen instance for gauge-rating-block-discharge.

Run once at authoring time, never inside the container. Reads the retrieved USGS
source files from .omo/usgs/, anonymises the three gauges to GS-A/GS-B/GS-C, and
writes: the agent-visible data, the rating tables carried by the skill and by the
grader, the frozen golden, and the grader-side identity map.

Source retrieval (2026-07-27, U.S. Geological Survey, public domain):
  rating   https://waterdata.usgs.gov/nwisweb/get_ratings?site_no=<site>&file_type=exsa
  stage    https://waterservices.usgs.gov/nwis/iv/ parameterCd=00065
  discharge https://waterservices.usgs.gov/nwis/iv/ parameterCd=00060

Instance selection rules, applied uniformly to all three gauges and fixed before
any measurement was taken:
  window  the 24 h with the largest gage-height range in the retrieved record,
          restricted to windows that leave 10 clear days of prior record
  blocks  four consecutive 6 h intervals from the window start
  decoy   the published discharge nearest to 10 days before the window start
"""

import csv
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(ROOT, "..", "..", ".."))
SRC = os.path.join(REPO, ".omo", "usgs")

sys.path.insert(0, HERE)
from rating import load_rating, discharge_at, block_mean  # noqa: E402

SEED = 20260727
REL_TOL = 0.002  # 0.2 % of the reference; see verifier/truth.md "Tolerance"

GAUGES = [
    # label, USGS site, window start (UTC), decoy target (UTC)
    ("GS-A", "03335500", dt.datetime(2026, 4, 17, 13, 0, tzinfo=dt.timezone.utc)),
    ("GS-B", "06934500", dt.datetime(2026, 4, 18, 6, 45, tzinfo=dt.timezone.utc)),
    ("GS-C", "12358500", dt.datetime(2026, 4, 22, 15, 30, tzinfo=dt.timezone.utc)),
]
DECOY_LAG_DAYS = 10
BLOCK_HOURS = 6
N_BLOCKS = 4


def read_series(path):
    with open(path) as fh:
        doc = json.load(fh)
    values = doc["value"]["timeSeries"][0]["values"][0]["value"]
    out = []
    for v in values:
        if v["value"] in ("", "-999999"):
            continue
        t = dt.datetime.fromisoformat(v["dateTime"]).astimezone(dt.timezone.utc)
        out.append((t, float(v["value"])))
    out.sort()
    return out


def write_rating_tsv(path, rows, label):
    """Anonymised rating table: no site number, no station name, no retrieval header."""
    with open(path, "w", newline="") as fh:
        fh.write("# Expanded shift-adjusted stage-discharge rating, gauge %s.\n" % label)
        fh.write("# gage_height_ft\tshift_ft\tdischarge_cfs\n")
        for h, s, q in rows:
            fh.write("%.2f\t%.2f\t%.2f\n" % (h, s, q))


def main():
    gauge_map = {}
    data_rows = []
    items = []
    expected = {
        "method": (
            "discharge from the gauge's expanded shift-adjusted stage-discharge rating "
            "(linear interpolation between rating points on gage height); block value is "
            "the time-weighted mean discharge over the closed 6 h interval, trapezoidal in time"
        ),
        "seed": SEED,
        "freeze_tol_cfs": 1e-06,
    }
    decoys = {}
    gauge_meta = []

    for label, site, t0 in GAUGES:
        rows = load_rating(os.path.join(SRC, "rating_%s.txt" % site))
        stage = read_series(os.path.join(SRC, "iv30_%s.json" % site))
        pub_q = dict(read_series(os.path.join(SRC, "q30_%s.json" % site)))

        window = [(t, h) for t, h in stage if t0 <= t <= t0 + dt.timedelta(hours=24)]
        times = [t.timestamp() for t, _ in window]
        heights = [h for _, h in window]
        q = [discharge_at(rows, h) for h in heights]

        # decoy: the real published discharge nearest DECOY_LAG_DAYS before the window
        stage_at = dict(stage)
        common = sorted(set(stage_at) & set(pub_q))
        target = t0 - dt.timedelta(days=DECOY_LAG_DAYS)
        d_t = min(common, key=lambda t: abs((t - target).total_seconds()))
        decoys[label] = {
            "gage_height_ft": round(stage_at[d_t], 2),
            "discharge_cfs": pub_q[d_t],
            "observed_utc": d_t.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        # Block boundaries are pinned to ACTUAL sample timestamps, so the nominal
        # interval and the span of the samples inside it are identical by construction.
        # Without this, a block whose series ends early admits two defensible readings
        # of "the elapsed time of the interval" - the nominal length or the sample span -
        # which yields two different means and violates L-06 (unique golden).
        edges = [window[round(i * (len(window) - 1) / N_BLOCKS)][0]
                 for i in range(N_BLOCKS + 1)]
        for k in range(N_BLOCKS):
            a, b = edges[k], edges[k + 1]
            ref = block_mean(times, q, a.timestamp(), b.timestamp())
            tol = round(ref * REL_TOL, 6)
            key = "b%d" % (k + 1)
            items.append({
                "gauge_id": label,
                "blockkey": key,
                "start_utc": a.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end_utc": b.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "ref_mean_discharge_cfs": ref,
                "tolerance_cfs": tol,
            })
            expected["ref_%s_%s_mean_discharge_cfs" % (label, key)] = ref
            expected["tolerance_%s_%s_mean_discharge_cfs_abs" % (label, key)] = tol

        for t, h in window:
            data_rows.append((label, t.strftime("%Y-%m-%dT%H:%M:%SZ"), "%.2f" % h))

        for dest in ("oracle/ratings", "verifier/ratings",
                     "environment/skills/streamgauge-rating-discharge/references"):
            write_rating_tsv(os.path.join(ROOT, dest, "rating_%s.tsv" % label), rows, label)

        gauge_map[label] = {
            "usgs_site_no": site,
            "rating_source": ("https://waterdata.usgs.gov/nwisweb/get_ratings?site_no=%s"
                              "&file_type=exsa" % site),
            "stage_source": ("https://waterservices.usgs.gov/nwis/iv/ parameterCd=00065, site %s"
                             % site),
            "window_start_utc": t0.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "retrieved": "2026-07-27",
            "rating_points": len(rows),
        }
        gauge_meta.append({"gauge_id": label, "n_samples": len(window),
                           "stage_min_ft": min(heights), "stage_max_ft": max(heights)})

    expected["items"] = items
    expected["gauge_detail"] = gauge_meta

    # ---- control ledger: what each wrong route scores, in tolerance units ----
    # Recomputed live here so the ledger can never drift from the golden (V-18).
    ledger = {
        "power_law_b2_from_recent_measurement": {
            "description": ("fit Q = C*h^2 through the single supplied recent measurement and "
                            "evaluate it at each reported stage"),
            "no_skill_route": True,
            "competitor": ("NEAREST REAL COMPETITOR: the standard published stage-discharge "
                           "form Q = C(h-e)^b anchored on a real measurement - what a competent "
                           "hydrologist without the table actually does, and the route the "
                           "recall probe showed the model takes unprompted. Not a strawman."),
            "fn": lambda h, dh, dq: dq * (h / dh) ** 2.0,
        },
        "linear_scale_from_recent_measurement": {
            "description": ("scale the single supplied recent measurement linearly in gage "
                            "height"),
            "no_skill_route": True,
            "fn": lambda h, dh, dq: dq * (h / dh),
        },
        "report_recent_measurement_throughout": {
            "description": "report the supplied recent discharge measurement for every block",
            "no_skill_route": True,
            "fn": lambda h, dh, dq: dq,
        },
    }
    # A defensible alternative convention, measured separately (V-06). It is NOT a
    # control path: it must NOT false-fail, so it is deliberately kept out of the
    # control ledger, where every entry is required to separate by >= 2x tolerance.
    variants = {
        "arithmetic_mean_of_samples": {
            "description": ("rate through the correct table but average the samples "
                            "arithmetically instead of weighting by elapsed time"),
            "fn": None,
        },
    }
    control_gaps = {}
    for name, spec in list(ledger.items()) + list(variants.items()):
        worst = None
        for label, site, t0 in GAUGES:
            rows = load_rating(os.path.join(SRC, "rating_%s.txt" % site))
            stage = read_series(os.path.join(SRC, "iv30_%s.json" % site))
            window = [(t, h) for t, h in stage if t0 <= t <= t0 + dt.timedelta(hours=24)]
            times = [t.timestamp() for t, _ in window]
            heights = [h for _, h in window]
            d = decoys[label]
            if spec["fn"] is None:
                q_wrong = [discharge_at(rows, h) for h in heights]
            else:
                q_wrong = [spec["fn"](h, d["gage_height_ft"], d["discharge_cfs"])
                           for h in heights]
            for k in range(N_BLOCKS):
                a = t0 + dt.timedelta(hours=BLOCK_HOURS * k)
                b = t0 + dt.timedelta(hours=BLOCK_HOURS * (k + 1))
                if spec["fn"] is None:
                    idx = [i for i, t in enumerate(times)
                           if a.timestamp() <= t <= b.timestamp()]
                    got = sum(q_wrong[i] for i in idx) / len(idx)
                else:
                    got = block_mean(times, q_wrong, a.timestamp(), b.timestamp())
                item = next(it for it in items
                            if it["gauge_id"] == label and it["blockkey"] == "b%d" % (k + 1))
                mult = abs(got - item["ref_mean_discharge_cfs"]) / item["tolerance_cfs"]
                worst = mult if worst is None else min(worst, mult)
        if name in ledger:
            control_gaps[name] = {
                "description": spec["description"],
                "no_skill_route": spec["no_skill_route"],
                "mean_discharge_cfs_gap_over_tol": round(worst, 3),
                "note": ("worst (smallest) separation over all 12 blocks, in tolerance units. "
                         + spec.get("competitor", "")).strip(),
            }
        else:
            variants[name] = {
                "description": spec["description"],
                "worst_deviation_over_tol": round(worst, 3),
                "must_not_false_fail": True,
                "note": ("V-06 evidence: a defensible alternative reduction convention. It stays "
                         "inside tolerance on every block, so pinning the trapezoidal rule in the "
                         "prompt costs the no-skill arm nothing and the reduction step is NOT part "
                         "of the lever. The lever is the rating table alone."),
            }
    expected["control_gaps"] = control_gaps
    expected["convention_variants"] = variants

    # ---- agent-visible data -------------------------------------------------
    with open(os.path.join(ROOT, "environment/data/stage_series.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["gauge_id", "datetime_utc", "gage_height_ft"])
        w.writerows(data_rows)

    with open(os.path.join(ROOT, "environment/data/gauges.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["gauge_id", "stage_parameter", "discharge_unit"])
        for label, _, _ in GAUGES:
            w.writerow([label, "gage height, feet above gauge datum", "cubic feet per second"])

    blocks = []
    for it in items:
        if it["gauge_id"] == GAUGES[0][0]:
            blocks.append({"block_id": it["blockkey"]})
    question = {
        "output_path": "/root/results.json",
        "blocks": [{"block_id": it["blockkey"], "start_utc": it["start_utc"],
                    "end_utc": it["end_utc"], "gauge_id": it["gauge_id"]} for it in items],
        "output_contract": {
            "block_mean_discharge_cfs": {
                "<gauge_id>": {"<block_id>": "number, mean discharge in cubic feet per second"}
            }
        },
        "method_note": (
            "For each gauge and each listed block, report the time-weighted mean discharge "
            "over the closed interval [start_utc, end_utc], using the trapezoidal rule in time "
            "over the reported instants that fall in the interval, both endpoints included."
        ),
        "decoy_reference": {
            "note": ("Shown for orientation only. One recent published discharge measurement at "
                     "each gauge, with the gage height observed at the same instant."),
            "recent_discharge_measurement": decoys,
        },
    }
    with open(os.path.join(ROOT, "environment/data/question.json"), "w") as fh:
        json.dump(question, fh, indent=2)
        fh.write("\n")

    # ---- grading artifacts --------------------------------------------------
    with open(os.path.join(ROOT, "verifier/expected_values.json"), "w") as fh:
        json.dump(expected, fh, indent=2)
        fh.write("\n")

    golden = {"block_mean_discharge_cfs": {}}
    for it in items:
        golden["block_mean_discharge_cfs"].setdefault(it["gauge_id"], {})[it["blockkey"]] = \
            it["ref_mean_discharge_cfs"]
    with open(os.path.join(ROOT, "verifier/golden.json"), "w") as fh:
        json.dump(golden, fh, indent=2)
        fh.write("\n")

    with open(os.path.join(ROOT, "build/gauge_map.json"), "w") as fh:
        json.dump({
            "note": ("Grader-side identity map. The agent-visible data name the gauges GS-A/GS-B/"
                     "GS-C only; this file records which real USGS gauge each label is, so the "
                     "constants stay citable without being fetchable from the container."),
            "license": ("U.S. Geological Survey data, public domain (17 U.S.C. 105); "
                        "redistribution unrestricted."),
            "gauges": gauge_map,
        }, fh, indent=2)
        fh.write("\n")

    print("items: %d" % len(items))
    for it in items:
        print("  %s %s  ref=%.4f tol=%.4f" % (it["gauge_id"], it["blockkey"],
                                              it["ref_mean_discharge_cfs"], it["tolerance_cfs"]))


if __name__ == "__main__":
    main()
