from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from dateutil.rrule import DAILY, MINUTELY, rrule, rrulestr


def test_negative_setpos_orders_times_within_day():
    start = datetime(2024, 1, 1, 18)
    expected = [datetime(2024, 1, day, 18) for day in (1, 2, 3)]
    assert list(rrule(DAILY, dtstart=start, byhour=(9, 18),
                      bysetpos=-1, count=3)) == expected
    assert list(rrulestr('FREQ=DAILY;BYHOUR=9,18;BYSETPOS=-1;COUNT=3',
                         dtstart=start)) == expected


def test_until_compares_instants_in_repeated_hour():
    zone = ZoneInfo('America/New_York')
    start = datetime(2024, 11, 3, 0, 30, tzinfo=zone)
    until = datetime(2024, 11, 3, 6, tzinfo=timezone.utc)
    expected = [start, datetime(2024, 11, 3, 1, 0, tzinfo=zone),
                datetime(2024, 11, 3, 1, 30, tzinfo=zone)]
    assert list(rrule(MINUTELY, interval=30, dtstart=start,
                      until=until)) == expected
