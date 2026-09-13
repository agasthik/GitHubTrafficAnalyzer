from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from github_traffic_analyzer.models import TrackedRepository


class GitHubTrafficClient:
    API_ROOT = "https://api.github.com"

    def __init__(self, token: str, user_agent: str = "github-traffic-analyzer") -> None:
        self.token = token
        self.user_agent = user_agent

    def _get_json(self, path: str) -> Any:
        url = f"{self.API_ROOT}{path}"
        # Enforce https so this client can never be pointed at file:// or another
        # scheme (guards against a future change to API_ROOT). urlopen is only
        # ever reached with a validated https URL.
        if not url.startswith("https://"):
            raise ValueError(f"Refusing non-https GitHub API URL: {url}")
        req = request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "User-Agent": self.user_agent,
                "X-GitHub-Api-Version": "2022-11-28",
            },
            method="GET",
        )
        try:
            with request.urlopen(req, timeout=30) as response:  # nosec B310
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"GitHub API request failed for {path}: {exc.code} {details}"
            ) from exc

    def fetch_views(self, repository: TrackedRepository) -> dict[str, Any]:
        return self._get_json(f"/repos/{repository.full_name}/traffic/views")

    def fetch_clones(self, repository: TrackedRepository) -> dict[str, Any]:
        return self._get_json(f"/repos/{repository.full_name}/traffic/clones")

    def fetch_referrers(self, repository: TrackedRepository) -> list[dict[str, Any]]:
        return self._get_json(
            f"/repos/{repository.full_name}/traffic/popular/referrers"
        )

    def fetch_paths(self, repository: TrackedRepository) -> list[dict[str, Any]]:
        return self._get_json(f"/repos/{repository.full_name}/traffic/popular/paths")
