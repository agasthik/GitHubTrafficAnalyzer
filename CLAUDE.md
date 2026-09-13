# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Serverless AWS SAM application that archives GitHub traffic metrics (views, clones, top referrers, top paths) for a configurable set of repositories, defeating GitHub's 14-day retention window. It runs a daily collector Lambda into DynamoDB and serves a dashboard + JSON API through a second Lambda behind an HTTP API.

## Commands

Local validation (no AWS credentials needed):

```bash
python3 -m compileall src tests          # syntax check
python3 -m unittest discover -s tests    # run all tests
python3 -m unittest tests.test_service.BuildRepositoryDashboardTests.test_summarizes_daily_metrics_and_snapshots  # single test
ruff check src tests                     # lint
ruff format --check src tests            # formatting check (drop --check to auto-format)
```

**MANDATORY before deploying (`sam deploy`) or pushing any change that touches a `.py` file:** run both `ruff check src tests` and `ruff format --check src tests`, and fix everything they report (`ruff check --fix` and `ruff format` resolve most issues automatically) before proceeding. Do not deploy or push with lint or formatting failures outstanding.

This gate is enforced, not just advisory: `scripts/install-hooks.sh` wires a `.githooks/pre-push` hook that runs `scripts/ruff-gate.sh` on every `git push`, and deploys should go through `scripts/sam-deploy.sh` (which runs the same gate) since a bare `sam deploy` bypasses it.

Build and deploy (AWS SAM CLI, Python 3.12 runtime):

```bash
sam build
sam deploy                               # uses samconfig.toml defaults
sam deploy --guided                      # first-time / to change params
```

Manually trigger a collection (schedule is otherwise once daily via EventBridge):

```bash
aws lambda invoke --function-name "$(aws cloudformation describe-stacks \
  --stack-name github-traffic-analyzer \
  --query 'Stacks[0].Outputs[?OutputKey==`CollectorFunctionName`].OutputValue' \
  --output text)" /tmp/response.json
```

## Deployment

The stack name is `github-traffic-analyzer`. Choose the AWS account, region, and
credential profile at deploy time — configure them in `samconfig.toml` or pass
`--profile`/`--region` to `sam deploy` (see the README). The commands below use
the default credential chain; add `--profile <your-profile>` if you use named
profiles.

All deployed resources are grouped under the `github-traffic-analyzer`
Resource Group (defined as `AWS::ResourceGroups::Group` in `template.yaml`, via a
`CLOUDFORMATION_STACK_1_0` query that auto-tracks every resource in the stack). To
list them from the CLI:

```bash
aws resource-groups list-group-resources --group-name github-traffic-analyzer \
  --region us-east-1
```

## Architecture

Two Lambda entry points share one internal package (`src/github_traffic_analyzer/`):

- **`handlers/collector.py`** — scheduled. Reads the GitHub token from Secrets Manager, calls the GitHub traffic API per repository, writes each day/snapshot into DynamoDB.
- **`handlers/api.py`** — HTTP API. Routes on `event["rawPath"]`: `/health`, `/api/traffic` (JSON, optional `startDate`/`endDate` query params), everything else serves the dashboard `static/index.html`.

Layered modules, no cross-layer shortcuts — handlers → service → store/github_api → aws_helpers:

- **`config.py`** — parses env vars into `AppSettings`. `TRACKED_REPOSITORIES` is a JSON array (of `{owner,name,label}` objects, or `"owner/name"` strings); falls back to `DEFAULT_REPOSITORIES`. `TABLE_NAME` and (collector only) `GITHUB_TOKEN_SECRET_NAME` are required.
- **`service.py`** — pure functions, the bulk of the logic and the only layer with test coverage. `collect_repository` orchestrates fetch→store; `build_dashboard_payload`/`build_repository_dashboard` transform raw DynamoDB items into the dashboard shape (date-range filtering, previous-window deltas, snapshot delta enrichment). Keep this layer free of boto3/network I/O so it stays unit-testable.
- **`store.py`** — DynamoDB access. Single-table design: `PK = REPO#{owner}/{name}`, `SK` is either `DAY#{bucketStart}#{metric}` (daily views/clones) or `SNAPSHOT#{snapshotAt}#{type}#{name}` (referrer/path snapshots). `query_repository` pulls all items for one repo (with pagination) and hands them to the service layer.
- **`github_api.py`** — thin GitHub REST client using stdlib `urllib` only (no `requests`).
- **`models.py`** — frozen dataclasses `TrackedRepository` and `AppSettings` (the shapes `config.py` produces and the rest of the code consumes).
- **`aws_helpers.py`** — lazily imports `boto3` (available in the Lambda runtime, not a project dependency) so local validation and tests work without it.
- **`utils.py`** — UTC time helpers, `to_decimal_safe` (floats→Decimal before DynamoDB writes), and `json_default` (Decimal/datetime→JSON on the way out).

## Key conventions

- **The dependency list is intentionally empty** (`pyproject.toml`). The runtime relies only on the Python stdlib plus `boto3`, which the Lambda runtime provides. Do not add third-party dependencies without a strong reason — it would require a build/packaging step this project deliberately avoids.
- **Tracked repositories are configured, not hardcoded.** The source of truth is the `TrackedRepositories` override in `samconfig.toml` (a single escaped JSON string). A plain `sam deploy` without that override resets the list to the template default, so edit `samconfig.toml` when adding/removing repos — see README "Add Another Repository". The template default and `config.py`'s `DEFAULT_REPOSITORIES` are an intentional placeholder (`your-org/your-repo`), not a real repo: the GitHub traffic API requires push access to a repository, so no default works for every deployer. Keep them as placeholders — do not substitute a real repository.
- **`uniques` are summed across days** in the dashboard, not de-duplicated — this is a known simplification (GitHub does not expose multi-day unique audiences).
- All timestamps are UTC ISO-8601 with a `Z` suffix; date filtering compares calendar dates.
