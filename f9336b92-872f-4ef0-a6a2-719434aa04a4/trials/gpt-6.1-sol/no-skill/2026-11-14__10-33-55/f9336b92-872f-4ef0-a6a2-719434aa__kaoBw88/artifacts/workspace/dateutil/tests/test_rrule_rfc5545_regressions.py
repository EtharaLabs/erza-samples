from datetime import datetime

import pytest
from dateutil.rrule import DAILY, rrule, rrulestr


def test_negative_setpos_orders_times_within_day():
    start = datetime(2024, 1, 1, 17)
    assert list(rrule(DAILY, dtstart=start, byhour=(9, 17),
                      bysetpos=-1, count=2)) == [
        start, datetime(2024, 1, 2, 17)]


@pytest.mark.parametrize("name,value", [
    ("bymonth", 13), ("bymonthday", 0), ("byyearday", 0),
    ("byyearday", 367), ("byweekno", 0), ("byweekno", 54),
    ("byhour", 24), ("byminute", 60),
])
def test_invalid_part_range(name, value):
    with pytest.raises(ValueError):
        rrule(DAILY, dtstart=datetime(2024, 1, 1), **{name: value})
    with pytest.raises(ValueError):
        rrulestr("FREQ=DAILY;{}={}".format(name.upper(), value),
                 dtstart=datetime(2024, 1, 1))
