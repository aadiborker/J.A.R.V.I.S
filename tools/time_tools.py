from __future__ import annotations

import datetime

_IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30), name="IST")

_ORDINAL_WORDS = {
    1: "first",
    2: "second",
    3: "third",
    4: "fourth",
    5: "fifth",
    6: "sixth",
    7: "seventh",
    8: "eighth",
    9: "ninth",
    10: "tenth",
    11: "eleventh",
    12: "twelfth",
    13: "thirteenth",
    14: "fourteenth",
    15: "fifteenth",
    16: "sixteenth",
    17: "seventeenth",
    18: "eighteenth",
    19: "nineteenth",
    20: "twentieth",
    21: "twenty first",
    22: "twenty second",
    23: "twenty third",
    24: "twenty fourth",
    25: "twenty fifth",
    26: "twenty sixth",
    27: "twenty seventh",
    28: "twenty eighth",
    29: "twenty ninth",
    30: "thirtieth",
    31: "thirty first",
}

_YEAR_ONES = {
    0: "hundred",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
    13: "thirteen",
    14: "fourteen",
    15: "fifteen",
    16: "sixteen",
    17: "seventeen",
    18: "eighteen",
    19: "nineteen",
    20: "twenty",
    21: "twenty one",
    22: "twenty two",
    23: "twenty three",
    24: "twenty four",
    25: "twenty five",
    26: "twenty six",
    27: "twenty seven",
    28: "twenty eight",
    29: "twenty nine",
    30: "thirty",
}


def _now_ist(now: datetime.datetime | None = None) -> datetime.datetime:
    if now is not None:
        if now.tzinfo is None:
            return now.replace(tzinfo=_IST)
        return now.astimezone(_IST)
    return datetime.datetime.now(datetime.timezone.utc).astimezone(_IST)


def ordinal_day(day: int) -> str:
    if 10 <= (day % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return _ORDINAL_WORDS.get(day, f"{day}{suffix}")


def year_spoken(year: int) -> str:
    if 2000 <= year <= 2099:
        ones = year % 100
        if ones == 0:
            return "two thousand"
        return f"twenty {_YEAR_ONES.get(ones, str(ones))}"
    return str(year)


def format_date_display(now: datetime.datetime | None = None) -> str:
    """Numeric date for display, e.g. 05-08-2026."""
    return _now_ist(now).strftime("%d-%m-%Y")


def format_date_spoken(now: datetime.datetime | None = None) -> str:
    """Spoken date, e.g. fifth of August twenty twenty six."""
    n = _now_ist(now)
    return f"{ordinal_day(n.day)} of {n.strftime('%B')} {year_spoken(n.year)}"


def format_time_display(now: datetime.datetime | None = None) -> str:
    return _now_ist(now).strftime("%I:%M %p").lstrip("0")


def get_time(**_kwargs) -> dict[str, str]:
    """Return clock time plus display/spoken date (IST)."""
    now = _now_ist()
    date_display = format_date_display(now)
    date_spoken = format_date_spoken(now)
    time_str = format_time_display(now)
    return {
        "time": time_str,
        "date": date_display,
        "date_spoken": date_spoken,
        "display": f"{time_str} · {date_display}",
        "spoken": f"{time_str} on the {date_spoken}",
    }
