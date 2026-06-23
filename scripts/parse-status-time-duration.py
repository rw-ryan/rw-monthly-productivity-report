"""Parse Status Time Free duration strings to decimal days."""
import re

DURATION_RE = re.compile(
    r"(?:(\d+)M\s*)?(?:(\d+)w\s*)?(?:(\d+)d\s*)?(?:(\d+)h\s*)?(?:(\d+)m)?"
)


def parse_status_time_duration(raw: str | None) -> float:
    if raw is None or raw.strip() in ("", "-"):
        return 0.0
    s = raw.strip()
    if s == "0m":
        return 0.0
    m = DURATION_RE.fullmatch(s)
    if not m:
        return 0.0
    months, weeks, days, hours, minutes = (int(x) if x else 0 for x in m.groups())
    total_minutes = months * 30 * 24 * 60 + weeks * 7 * 24 * 60 + days * 24 * 60 + hours * 60 + minutes
    return round(total_minutes / (24 * 60), 2)
