# intents/utils_date.py

import re
from typing import Optional, Tuple

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def parse_month_year(text: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse month/year from a free text question. Returns (month, year)."""
    q = text.lower()
    month = None
    for name, idx in MONTHS.items():
        if name in q:
            month = idx
            break

    year = None
    for tok in re.findall(r"\b\d{4}\b", q):
        try:
            year = int(tok)
            break
        except ValueError:
            pass

    return month, year


def describe_period(text: str) -> str:
    """Human-friendly label for the period in the question."""
    month, year = parse_month_year(text)
    if month and year:
        name = [m for m, i in MONTHS.items() if i == month][0].title()
        return f"{name} {year}"
    if year:
        return f"{year}"
    q = text.lower()
    if "ytd" in q or "year to date" in q:
        return "year to date"
    return "the selected period"
