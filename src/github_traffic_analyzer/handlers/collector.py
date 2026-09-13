from __future__ import annotations

from github_traffic_analyzer.aws_helpers import get_secret_token
from github_traffic_analyzer.config import load_collector_settings
from github_traffic_analyzer.github_api import GitHubTrafficClient
from github_traffic_analyzer.service import collect_repository
from github_traffic_analyzer.store import TrafficArchiveStore
from github_traffic_analyzer.utils import json_dumps


def handler(event, context):
    settings = load_collector_settings()
    token = get_secret_token(settings.github_token_secret_name or "")
    client = GitHubTrafficClient(token=token)
    store = TrafficArchiveStore.from_table_name(settings.table_name)

    results = [
        collect_repository(repository=repository, client=client, store=store)
        for repository in settings.repositories
    ]

    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json_dumps({"results": results}),
    }
