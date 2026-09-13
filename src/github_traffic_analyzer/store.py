from __future__ import annotations

from typing import Any

from github_traffic_analyzer.aws_helpers import get_dynamodb_table
from github_traffic_analyzer.models import TrackedRepository
from github_traffic_analyzer.utils import to_decimal_safe


class TrafficArchiveStore:
    def __init__(self, table) -> None:
        self.table = table

    @classmethod
    def from_table_name(cls, table_name: str) -> TrafficArchiveStore:
        return cls(get_dynamodb_table(table_name))

    def _repo_pk(self, repository: TrackedRepository) -> str:
        return f"REPO#{repository.full_name}"

    def put_daily_metric(
        self,
        repository: TrackedRepository,
        metric: str,
        bucket_start: str,
        count: int,
        uniques: int,
        collected_at: str,
    ) -> None:
        item = {
            "PK": self._repo_pk(repository),
            "SK": f"DAY#{bucket_start}#{metric}",
            "entityType": "daily",
            "repository": repository.full_name,
            "label": repository.display_name,
            "metric": metric,
            "bucketStart": bucket_start,
            "bucketDate": bucket_start[:10],
            "count": int(count),
            "uniques": int(uniques),
            "lastCollectedAt": collected_at,
        }
        self.table.put_item(Item=to_decimal_safe(item))

    def put_snapshot(
        self,
        repository: TrackedRepository,
        snapshot_type: str,
        snapshot_at: str,
        name: str,
        count: int,
        uniques: int,
        title: str | None = None,
        path: str | None = None,
    ) -> None:
        item = {
            "PK": self._repo_pk(repository),
            "SK": f"SNAPSHOT#{snapshot_at}#{snapshot_type}#{name}",
            "entityType": "snapshot",
            "repository": repository.full_name,
            "label": repository.display_name,
            "snapshotType": snapshot_type,
            "snapshotAt": snapshot_at,
            "name": name,
            "count": int(count),
            "uniques": int(uniques),
        }
        if title:
            item["title"] = title
        if path:
            item["path"] = path
        self.table.put_item(Item=to_decimal_safe(item))

    def query_repository(self, repository: TrackedRepository) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        query_kwargs = {
            "KeyConditionExpression": "PK = :pk",
            "ExpressionAttributeValues": {":pk": self._repo_pk(repository)},
        }

        response = self.table.query(**query_kwargs)
        items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = self.table.query(
                ExclusiveStartKey=response["LastEvaluatedKey"], **query_kwargs
            )
            items.extend(response.get("Items", []))
        return items
