from datetime import datetime, timezone
import json

date_formats = [
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%-d/%-m/%Y",
    "%d/%-m/%Y",
    "%-d/%m/%Y",
    "%d-%-m-%Y",
    "%-d-%m-%Y",
    "%-d-%-m-%Y",
    "%-d-%b-%y",
    "%d-%b-%y",
    "%-d-%b-%Y",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H",
    "%Y-%m-%d",
]


def parse_date(date_str: str) -> datetime:
    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Date '{date_str}' is not in a valid UTC format.")


def Print(data, title="Result"):
    print(f"{title}\n", json.dumps(data, indent=2, default=str))
