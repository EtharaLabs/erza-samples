"""Stage-discharge rating application.

A streamgauge's rating is an empirical table specific to that gauge: it maps gage
height (the water-surface elevation above the gauge datum) to discharge. The table
shipped here is an expanded, shift-adjusted rating - the discharge column already
carries the shift in effect, so an observed gage height is looked up directly.

Two operations are needed:

  discharge_at(rows, h)  - discharge at a single gage height
  block_mean(ts, q, a, b) - time-weighted mean discharge over a closed interval

Both are used unchanged by the oracle and by the verifier's live recompute.
"""

import bisect


def load_rating(path):
    """Read a three-column rating table (gage height, shift, discharge).

    Returns rows sorted by gage height.
    """
    rows = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            try:
                rows.append((float(parts[0]), float(parts[1]), float(parts[2])))
            except ValueError:
                continue
    rows.sort()
    if not rows:
        raise ValueError("empty rating table: %s" % path)
    return rows


def discharge_at(rows, h):
    """Discharge for gage height h, linearly interpolated between rating points.

    Heights on or outside the tabulated range clamp to the end points; the shipped
    series stay well inside the table, so clamping never fires in this task.
    """
    xs = [r[0] for r in rows]
    i = bisect.bisect_left(xs, h)
    if i == 0:
        return rows[0][2]
    if i >= len(rows):
        return rows[-1][2]
    if xs[i] == h:
        return rows[i][2]
    x0, y0 = rows[i - 1][0], rows[i - 1][2]
    x1, y1 = rows[i][0], rows[i][2]
    return y0 + (y1 - y0) * (h - x0) / (x1 - x0)


def block_mean(times, discharges, start, end):
    """Time-weighted mean discharge over [start, end], trapezoidal in time.

    `times` are epoch seconds (ascending). Both endpoints are included. The mean is
    the trapezoidal integral over the interval divided by its elapsed time, so an
    uneven reporting interval is weighted by the time it actually represents.
    """
    idx = [k for k, t in enumerate(times) if start <= t <= end]
    if len(idx) < 2:
        raise ValueError("fewer than two samples in block")
    total = 0.0
    for k in range(len(idx) - 1):
        a, b = idx[k], idx[k + 1]
        total += (discharges[a] + discharges[b]) / 2.0 * (times[b] - times[a])
    span = times[idx[-1]] - times[idx[0]]
    return total / span
