from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from github_traffic_analyzer.github_api import GitHubTrafficClient
from github_traffic_analyzer.models import TrackedRepository
from github_traffic_analyzer.store import TrafficArchiveStore
from github_traffic_analyzer.utils import parse_date, parse_iso8601, to_iso8601, utc_now


def collect_repository(
    repository: TrackedRepository,
    client: GitHubTrafficClient,
    store: TrafficArchiveStore,
    captured_at: str | None = None,
) -> dict[str, Any]:
    captured_timestamp = captured_at or to_iso8601(utc_now())

    views = client.fetch_views(repository)
    clones = client.fetch_clones(repository)
    referrers = client.fetch_referrers(repository)
    paths = client.fetch_paths(repository)

    for bucket in views.get("views", []):
        store.put_daily_metric(
            repository=repository,
            metric="views",
            bucket_start=bucket["timestamp"],
            count=int(bucket["count"]),
            uniques=int(bucket["uniques"]),
            collected_at=captured_timestamp,
        )

    for bucket in clones.get("clones", []):
        store.put_daily_metric(
            repository=repository,
            metric="clones",
            bucket_start=bucket["timestamp"],
            count=int(bucket["count"]),
            uniques=int(bucket["uniques"]),
            collected_at=captured_timestamp,
        )

    for referrer in referrers:
        store.put_snapshot(
            repository=repository,
            snapshot_type="referrer",
            snapshot_at=captured_timestamp,
            name=str(referrer["referrer"]),
            count=int(referrer["count"]),
            uniques=int(referrer["uniques"]),
        )

    for path in paths:
        store.put_snapshot(
            repository=repository,
            snapshot_type="path",
            snapshot_at=captured_timestamp,
            name=str(path["path"]),
            title=str(path.get("title", path["path"])),
            path=str(path["path"]),
            count=int(path["count"]),
            uniques=int(path["uniques"]),
        )

    return {
        "repository": repository.full_name,
        "capturedAt": captured_timestamp,
        "viewsPoints": len(views.get("views", [])),
        "clonesPoints": len(clones.get("clones", [])),
        "referrerSnapshots": len(referrers),
        "pathSnapshots": len(paths),
    }


def build_dashboard_payload(
    repositories: list[TrackedRepository],
    items_by_repository: dict[str, list[dict[str, Any]]],
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    repository_payloads = [
        build_repository_dashboard(
            repository,
            items_by_repository.get(repository.full_name, []),
            start_date=start_date,
            end_date=end_date,
        )
        for repository in repositories
    ]

    available_start_dates = [
        repository_payload["availableStartDate"]
        for repository_payload in repository_payloads
        if repository_payload["availableStartDate"]
    ]
    available_end_dates = [
        repository_payload["availableEndDate"]
        for repository_payload in repository_payloads
        if repository_payload["availableEndDate"]
    ]
    selected_start_dates = [
        repository_payload["selectedStartDate"]
        for repository_payload in repository_payloads
        if repository_payload["selectedStartDate"]
    ]
    selected_end_dates = [
        repository_payload["selectedEndDate"]
        for repository_payload in repository_payloads
        if repository_payload["selectedEndDate"]
    ]

    return {
        "generatedAt": to_iso8601(utc_now()),
        "availableStartDate": min(available_start_dates)
        if available_start_dates
        else None,
        "availableEndDate": max(available_end_dates) if available_end_dates else None,
        "selectedStartDate": min(selected_start_dates)
        if selected_start_dates
        else None,
        "selectedEndDate": max(selected_end_dates) if selected_end_dates else None,
        "repositories": repository_payloads,
    }


def build_repository_dashboard(
    repository: TrackedRepository,
    items: list[dict[str, Any]],
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    daily_series: dict[str, list[dict[str, Any]]] = {"views": [], "clones": []}
    snapshots: dict[str, dict[str, list[dict[str, Any]]]] = {
        "referrer": defaultdict(list),
        "path": defaultdict(list),
    }

    for item in items:
        entity_type = item.get("entityType")
        if entity_type == "daily":
            metric = str(item["metric"])
            daily_series.setdefault(metric, []).append(
                {
                    "date": str(item["bucketDate"]),
                    "timestamp": str(item["bucketStart"]),
                    "count": int(item["count"]),
                    "uniques": int(item["uniques"]),
                }
            )
        elif entity_type == "snapshot":
            snapshot_type = str(item["snapshotType"])
            snapshots.setdefault(snapshot_type, defaultdict(list))[
                str(item["snapshotAt"])
            ].append(
                {
                    "name": str(item["name"]),
                    "title": str(item.get("title", item["name"])),
                    "path": str(item.get("path", item["name"])),
                    "count": int(item["count"]),
                    "uniques": int(item["uniques"]),
                }
            )

    all_views_series = _sort_series(daily_series["views"])
    all_clones_series = _sort_series(daily_series["clones"])
    available_start_date, available_end_date = _available_date_range(
        all_views_series,
        all_clones_series,
        snapshots["referrer"],
        snapshots["path"],
    )
    selected_start_date, selected_end_date = _resolve_selected_range(
        available_start_date,
        available_end_date,
        start_date,
        end_date,
    )

    views_series = _filter_series(
        all_views_series, selected_start_date, selected_end_date
    )
    clones_series = _filter_series(
        all_clones_series, selected_start_date, selected_end_date
    )
    latest_referrers = _latest_snapshot_with_delta(
        snapshots["referrer"],
        selected_start_date,
        selected_end_date,
    )
    latest_paths = _latest_snapshot_with_delta(
        snapshots["path"],
        selected_start_date,
        selected_end_date,
    )

    return {
        "fullName": repository.full_name,
        "label": repository.display_name,
        "owner": repository.owner,
        "name": repository.name,
        "availableStartDate": available_start_date.isoformat()
        if available_start_date
        else None,
        "availableEndDate": available_end_date.isoformat()
        if available_end_date
        else None,
        "selectedStartDate": selected_start_date.isoformat()
        if selected_start_date
        else None,
        "selectedEndDate": selected_end_date.isoformat() if selected_end_date else None,
        "viewsSeries": views_series,
        "clonesSeries": clones_series,
        "viewsSummary": _summarize_series(
            all_views_series, selected_start_date, selected_end_date
        ),
        "clonesSummary": _summarize_series(
            all_clones_series, selected_start_date, selected_end_date
        ),
        "topReferrers": latest_referrers,
        "topPaths": latest_paths,
        "historyStart": _history_start(views_series, clones_series),
        "historyEnd": _history_end(views_series, clones_series),
    }


def _sort_series(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(points, key=lambda point: point["timestamp"])


def _filter_series(
    points: list[dict[str, Any]],
    start_date: date | None,
    end_date: date | None,
) -> list[dict[str, Any]]:
    return [
        point
        for point in points
        if _date_in_range(
            parse_iso8601(point["timestamp"]).date(), start_date, end_date
        )
    ]


def _summarize_series(
    all_points: list[dict[str, Any]],
    start_date: date | None,
    end_date: date | None,
) -> dict[str, Any]:
    range_days = _range_day_count(start_date, end_date)
    if not all_points and range_days == 0:
        return {
            "rangeDays": 0,
            "count": 0,
            "dailyUniqueSum": 0,
            "changeFromPreviousWindow": 0,
        }

    effective_start = start_date
    effective_end = end_date
    if all_points:
        effective_start = (
            effective_start or parse_iso8601(all_points[0]["timestamp"]).date()
        )
        effective_end = (
            effective_end or parse_iso8601(all_points[-1]["timestamp"]).date()
        )

    current_points = _filter_series(all_points, effective_start, effective_end)

    current_total = sum(point["count"] for point in current_points)
    previous_points = []
    if effective_start and effective_end:
        effective_range_days = _range_day_count(effective_start, effective_end)
        previous_start = effective_start - timedelta(days=effective_range_days)
        previous_end = effective_start - timedelta(days=1)
        previous_points = [
            point
            for point in all_points
            if previous_start
            <= parse_iso8601(point["timestamp"]).date()
            <= previous_end
        ]
    previous_total = sum(point["count"] for point in previous_points)

    return {
        "rangeDays": _range_day_count(effective_start, effective_end),
        "count": current_total,
        "dailyUniqueSum": sum(point["uniques"] for point in current_points),
        "changeFromPreviousWindow": current_total - previous_total,
    }


def _latest_snapshot_with_delta(
    grouped_snapshots: dict[str, list[dict[str, Any]]],
    start_date: date | None,
    end_date: date | None,
) -> list[dict[str, Any]]:
    if not grouped_snapshots or not start_date or not end_date:
        return []

    ordered_timestamps = [
        timestamp
        for timestamp in sorted(grouped_snapshots.keys())
        if _date_in_range(parse_iso8601(timestamp).date(), start_date, end_date)
    ]
    if not ordered_timestamps:
        return []

    latest_timestamp = ordered_timestamps[-1]
    latest_items = sorted(
        grouped_snapshots[latest_timestamp],
        key=lambda item: (-item["count"], -item["uniques"], item["name"]),
    )

    previous_lookup: dict[str, dict[str, Any]] = {}
    if len(ordered_timestamps) > 1:
        previous_timestamp = ordered_timestamps[-2]
        previous_lookup = {
            item["name"]: item for item in grouped_snapshots[previous_timestamp]
        }

    enriched_items = []
    for item in latest_items:
        previous = previous_lookup.get(item["name"], {"count": 0, "uniques": 0})
        enriched_items.append(
            {
                **item,
                "snapshotAt": latest_timestamp,
                "countDelta": item["count"] - int(previous["count"]),
                "uniquesDelta": item["uniques"] - int(previous["uniques"]),
            }
        )
    return enriched_items


def _history_start(*series_groups: list[dict[str, Any]]) -> str | None:
    timestamps = [group[0]["timestamp"] for group in series_groups if group]
    return min(timestamps) if timestamps else None


def _history_end(*series_groups: list[dict[str, Any]]) -> str | None:
    timestamps = [group[-1]["timestamp"] for group in series_groups if group]
    return max(timestamps) if timestamps else None


def _available_date_range(
    views_series: list[dict[str, Any]],
    clones_series: list[dict[str, Any]],
    referrer_snapshots: dict[str, list[dict[str, Any]]],
    path_snapshots: dict[str, list[dict[str, Any]]],
) -> tuple[date | None, date | None]:
    daily_dates = [
        parse_iso8601(point["timestamp"]).date()
        for group in (views_series, clones_series)
        for point in group
    ]
    snapshot_dates = [
        parse_iso8601(timestamp).date()
        for grouped_snapshots in (referrer_snapshots, path_snapshots)
        for timestamp in grouped_snapshots
    ]
    all_dates = daily_dates + snapshot_dates
    if not all_dates:
        return None, None
    return min(all_dates), max(all_dates)


def _resolve_selected_range(
    available_start_date: date | None,
    available_end_date: date | None,
    start_date: str | None,
    end_date: str | None,
) -> tuple[date | None, date | None]:
    if not available_start_date or not available_end_date:
        return None, None

    selected_start_date = parse_date(start_date) if start_date else available_start_date
    selected_end_date = parse_date(end_date) if end_date else available_end_date

    if selected_start_date > selected_end_date:
        raise ValueError("startDate must be on or before endDate.")

    return selected_start_date, selected_end_date


def _date_in_range(value: date, start_date: date | None, end_date: date | None) -> bool:
    if start_date and value < start_date:
        return False
    return not (end_date and value > end_date)


def _range_day_count(start_date: date | None, end_date: date | None) -> int:
    if not start_date or not end_date:
        return 0
    return (end_date - start_date).days + 1
