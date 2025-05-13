import re
from datetime import datetime


ISO_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def natural_dt(iso_str: str) -> str:
    dt = datetime.fromisoformat(iso_str)

    def ordinal(n: int) -> str:
        return {1: "st", 2: "nd", 3: "rd"}.get(n if 10 < n % 100 < 14 else n % 10, "th")

    day_suffix = ordinal(dt.day)
    return dt.strftime(f"%-I:%M %p on %-d{day_suffix} %B %Y")
