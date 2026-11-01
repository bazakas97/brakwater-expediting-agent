"""Business date handling for the Keelson ERP sandbox.

The sandbox data was recorded on REFERENCE_DATE. To keep the data realistic on any
day, every date is shifted by the number of days between REFERENCE_DATE and the
business date (today, or KEELSON_TODAY if set). Dates mentioned inside memo texts
(for example "02/10" or "wk 45") are shifted the same way.
"""
import os
import re
from datetime import date, timedelta

REFERENCE_DATE = date(2026, 10, 12)

_DAY_MONTH = re.compile(r"\b(\d{1,2})/(\d{1,2})\b")
_WEEK = re.compile(r"\b(wk|kw|week)(\s?)(\d{1,2})\b", re.IGNORECASE)


def business_today() -> date:
    """Today's business date. Set KEELSON_TODAY=YYYY-MM-DD to pin it."""
    value = os.getenv("KEELSON_TODAY")
    return date.fromisoformat(value) if value else date.today()


def offset() -> timedelta:
    return business_today() - REFERENCE_DATE


def shift_date(value: str | None) -> str | None:
    if value is None:
        return None
    return (date.fromisoformat(value) + offset()).isoformat()


def shift_memo(text: str) -> str:
    delta = offset()
    if not text or delta == timedelta(0):
        return text

    def day_month(m: re.Match) -> str:
        day, month = int(m.group(1)), int(m.group(2))
        try:
            shifted = date(REFERENCE_DATE.year, month, day) + delta
        except ValueError:
            return m.group(0)
        return f"{shifted.day:02d}/{shifted.month:02d}"

    def week(m: re.Match) -> str:
        monday = date.fromisocalendar(REFERENCE_DATE.year, int(m.group(3)), 1)
        shifted_week = (monday + delta).isocalendar().week
        return f"{m.group(1)}{m.group(2)}{shifted_week}"

    return _WEEK.sub(week, _DAY_MONTH.sub(day_month, text))
