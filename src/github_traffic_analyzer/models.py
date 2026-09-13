from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackedRepository:
    owner: str
    name: str
    label: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"

    @property
    def display_name(self) -> str:
        return self.label or self.full_name


@dataclass(frozen=True)
class AppSettings:
    table_name: str
    repositories: list[TrackedRepository]
    github_token_secret_name: str | None = None
