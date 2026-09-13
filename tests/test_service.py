import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from github_traffic_analyzer.models import TrackedRepository
from github_traffic_analyzer.service import (
    build_dashboard_payload,
    build_repository_dashboard,
)


class BuildRepositoryDashboardTests(unittest.TestCase):
    def test_summarizes_daily_metrics_and_snapshots(self) -> None:
        repository = TrackedRepository(
            owner="example-org",
            name="example-repo",
            label="Example Repository",
        )
        items = [
            {
                "entityType": "daily",
                "metric": "views",
                "bucketDate": "2026-06-01",
                "bucketStart": "2026-06-01T00:00:00Z",
                "count": 12,
                "uniques": 8,
            },
            {
                "entityType": "daily",
                "metric": "views",
                "bucketDate": "2026-06-02",
                "bucketStart": "2026-06-02T00:00:00Z",
                "count": 18,
                "uniques": 10,
            },
            {
                "entityType": "daily",
                "metric": "clones",
                "bucketDate": "2026-06-02",
                "bucketStart": "2026-06-02T00:00:00Z",
                "count": 5,
                "uniques": 4,
            },
            {
                "entityType": "snapshot",
                "snapshotType": "referrer",
                "snapshotAt": "2026-06-10T00:00:00Z",
                "name": "google.com",
                "count": 20,
                "uniques": 14,
            },
            {
                "entityType": "snapshot",
                "snapshotType": "referrer",
                "snapshotAt": "2026-06-11T00:00:00Z",
                "name": "google.com",
                "count": 25,
                "uniques": 16,
            },
            {
                "entityType": "snapshot",
                "snapshotType": "path",
                "snapshotAt": "2026-06-11T00:00:00Z",
                "name": "/blob/main/README.md",
                "title": "README",
                "path": "/blob/main/README.md",
                "count": 11,
                "uniques": 9,
            },
        ]

        dashboard = build_repository_dashboard(repository, items)

        self.assertEqual(dashboard["fullName"], "example-org/example-repo")
        self.assertEqual(dashboard["viewsSummary"]["count"], 30)
        self.assertEqual(dashboard["clonesSummary"]["count"], 5)
        self.assertEqual(dashboard["topReferrers"][0]["name"], "google.com")
        self.assertEqual(dashboard["topReferrers"][0]["countDelta"], 5)
        self.assertEqual(dashboard["topPaths"][0]["title"], "README")

    def test_applies_selected_date_range_to_series_and_snapshots(self) -> None:
        repository = TrackedRepository(
            owner="example-org",
            name="example-repo",
            label="Example Repository",
        )
        items = [
            {
                "entityType": "daily",
                "metric": "views",
                "bucketDate": "2026-06-01",
                "bucketStart": "2026-06-01T00:00:00Z",
                "count": 12,
                "uniques": 8,
            },
            {
                "entityType": "daily",
                "metric": "views",
                "bucketDate": "2026-06-02",
                "bucketStart": "2026-06-02T00:00:00Z",
                "count": 18,
                "uniques": 10,
            },
            {
                "entityType": "daily",
                "metric": "views",
                "bucketDate": "2026-06-03",
                "bucketStart": "2026-06-03T00:00:00Z",
                "count": 9,
                "uniques": 5,
            },
            {
                "entityType": "snapshot",
                "snapshotType": "referrer",
                "snapshotAt": "2026-06-02T00:00:00Z",
                "name": "google.com",
                "count": 20,
                "uniques": 14,
            },
            {
                "entityType": "snapshot",
                "snapshotType": "referrer",
                "snapshotAt": "2026-06-03T00:00:00Z",
                "name": "google.com",
                "count": 25,
                "uniques": 16,
            },
        ]

        dashboard = build_repository_dashboard(
            repository,
            items,
            start_date="2026-06-02",
            end_date="2026-06-03",
        )

        self.assertEqual(dashboard["selectedStartDate"], "2026-06-02")
        self.assertEqual(dashboard["selectedEndDate"], "2026-06-03")
        self.assertEqual(len(dashboard["viewsSeries"]), 2)
        self.assertEqual(dashboard["viewsSummary"]["count"], 27)
        self.assertEqual(dashboard["topReferrers"][0]["count"], 25)
        self.assertEqual(dashboard["topReferrers"][0]["countDelta"], 5)

    def test_dashboard_payload_reports_available_and_selected_ranges(self) -> None:
        repository = TrackedRepository(
            owner="example-org",
            name="example-repo",
            label="Example Repository",
        )
        items = [
            {
                "entityType": "daily",
                "metric": "views",
                "bucketDate": "2026-06-01",
                "bucketStart": "2026-06-01T00:00:00Z",
                "count": 12,
                "uniques": 8,
            },
            {
                "entityType": "daily",
                "metric": "views",
                "bucketDate": "2026-06-03",
                "bucketStart": "2026-06-03T00:00:00Z",
                "count": 18,
                "uniques": 10,
            },
        ]

        payload = build_dashboard_payload(
            repositories=[repository],
            items_by_repository={repository.full_name: items},
            start_date="2026-06-02",
            end_date="2026-06-03",
        )

        self.assertEqual(payload["availableStartDate"], "2026-06-01")
        self.assertEqual(payload["availableEndDate"], "2026-06-03")
        self.assertEqual(payload["selectedStartDate"], "2026-06-02")
        self.assertEqual(payload["selectedEndDate"], "2026-06-03")
