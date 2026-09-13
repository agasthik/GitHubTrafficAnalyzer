from __future__ import annotations

import json
import os

from github_traffic_analyzer.models import AppSettings, TrackedRepository

# Placeholder only. The GitHub traffic API requires push access to a repository,
# so there is no repo that works for every deployer out of the box. Override this
# via the TrackedRepositories deploy parameter (see samconfig.toml / README) with
# repositories your GitHub token can read traffic for.
DEFAULT_REPOSITORIES = [
    {
        "owner": "your-org",
        "name": "your-repo",
        "label": "Your Repository",
    }
]


def _parse_repository_item(raw_item: object) -> TrackedRepository:
    if isinstance(raw_item, str):
        owner, name = raw_item.split("/", maxsplit=1)
        return TrackedRepository(owner=owner, name=name)

    if isinstance(raw_item, dict):
        owner = str(raw_item["owner"])
        name = str(raw_item["name"])
        label = raw_item.get("label")
        return TrackedRepository(
            owner=owner, name=name, label=str(label) if label else None
        )

    raise ValueError(f"Unsupported repository config: {raw_item!r}")


def parse_repositories(raw_value: str | None) -> list[TrackedRepository]:
    if not raw_value:
        return [_parse_repository_item(item) for item in DEFAULT_REPOSITORIES]

    parsed = json.loads(raw_value)
    if not isinstance(parsed, list) or not parsed:
        raise ValueError("TRACKED_REPOSITORIES must be a non-empty JSON array.")

    return [_parse_repository_item(item) for item in parsed]


def load_api_settings() -> AppSettings:
    table_name = os.environ["TABLE_NAME"]
    repositories = parse_repositories(os.environ.get("TRACKED_REPOSITORIES"))
    return AppSettings(table_name=table_name, repositories=repositories)


def load_collector_settings() -> AppSettings:
    settings = load_api_settings()
    secret_name = os.environ["GITHUB_TOKEN_SECRET_NAME"]
    return AppSettings(
        table_name=settings.table_name,
        repositories=settings.repositories,
        github_token_secret_name=secret_name,
    )
