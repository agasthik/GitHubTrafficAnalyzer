from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def parse_iso8601(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def to_iso8601(value: datetime) -> str:
    return (
        value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )


def to_decimal_safe(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: to_decimal_safe(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [to_decimal_safe(inner) for inner in value]
    return value


def json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    if isinstance(value, datetime):
        return to_iso8601(value)
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def load_text(relative_path: str) -> str:
    base_dir = Path(__file__).resolve().parent
    return (base_dir / relative_path).read_text(encoding="utf-8")


def json_dumps(payload: Any) -> str:
    return json.dumps(payload, default=json_default, separators=(",", ":"))
