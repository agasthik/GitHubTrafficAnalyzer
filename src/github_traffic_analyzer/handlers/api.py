from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs

from github_traffic_analyzer.config import load_api_settings
from github_traffic_analyzer.service import build_dashboard_payload
from github_traffic_analyzer.store import TrafficArchiveStore
from github_traffic_analyzer.utils import json_dumps

INDEX_HTML = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text(
    encoding="utf-8"
)


def _response(status_code: int, body: str, content_type: str) -> dict[str, object]:
    return {
        "statusCode": status_code,
        "headers": {
            "content-type": content_type,
            "cache-control": "no-store",
        },
        "body": body,
    }


def handler(event, context):
    path = event.get("rawPath", "/")
    settings = load_api_settings()

    if path == "/health":
        return _response(200, json_dumps({"ok": True}), "application/json")

    if path == "/api/traffic":
        store = TrafficArchiveStore.from_table_name(settings.table_name)
        items_by_repository = {
            repository.full_name: store.query_repository(repository)
            for repository in settings.repositories
        }
        try:
            payload = build_dashboard_payload(
                repositories=settings.repositories,
                items_by_repository=items_by_repository,
                start_date=_query_param(event, "startDate"),
                end_date=_query_param(event, "endDate"),
            )
        except ValueError as exc:
            return _response(400, json_dumps({"message": str(exc)}), "application/json")
        return _response(200, json_dumps(payload), "application/json")

    return _response(200, INDEX_HTML, "text/html; charset=utf-8")


def _query_param(event: dict[str, object], name: str) -> str | None:
    query_string_parameters = event.get("queryStringParameters")
    if isinstance(query_string_parameters, dict):
        value = query_string_parameters.get(name)
        return str(value) if value else None

    raw_query_string = event.get("rawQueryString")
    if isinstance(raw_query_string, str) and raw_query_string:
        parsed = parse_qs(raw_query_string)
        values = parsed.get(name)
        if values:
            return values[0]
    return None
