# Contributing

Thanks for your interest in improving GitHub Traffic Analyzer! Contributions are
welcome via **fork and pull request**.

## Workflow

1. **Fork** this repository to your own GitHub account.
2. **Clone** your fork and create a branch for your change:
   ```bash
   git clone https://github.com/<your-user>/github-traffic-analyzer.git
   cd github-traffic-analyzer
   git checkout -b my-change
   ```
3. **Make your change**, keeping it focused — one logical change per pull request.
4. **Validate locally** (no AWS credentials needed):
   ```bash
   python3 -m compileall src tests
   python3 -m unittest discover -s tests
   ```
5. **Run the code quality gate.** Install the git hook once, then it runs on every
   push:
   ```bash
   ./scripts/install-hooks.sh
   ./scripts/ruff-gate.sh   # or let the pre-push hook run it for you
   ```
   Lint and formatting must be clean (`ruff check src tests` and
   `ruff format --check src tests`) before a change is accepted.
6. **Commit and push** to your fork, then **open a pull request** against this
   repository's default branch. Describe what changed and why.

## The code quality gate

Linting and formatting are enforced with [ruff](https://docs.astral.sh/ruff/)
before any push or deploy, so unformatted or lint-failing code never leaves your
machine.

- `./scripts/install-hooks.sh` sets `core.hooksPath` to the versioned
  `.githooks/` directory. After that, `git push` runs the gate automatically via
  the `pre-push` hook and blocks the push if ruff has to change any file or a
  lint error remains.
- The gate logic lives in `scripts/ruff-gate.sh`. It applies safe fixes
  (`ruff check --fix` and `ruff format`), then verifies the tree is clean; if
  ruff modified anything it prints the changed files and exits non-zero so you
  can review and commit before retrying. It uses an installed `ruff` if present,
  otherwise falls back to `uvx`/`uv`.
- If you edit the Python source and deploy, use `./scripts/sam-deploy.sh`
  (it forwards all arguments to `sam deploy` and runs the same gate first), since
  SAM has no native pre-deploy hook. A bare `sam deploy` bypasses the gate and is
  only appropriate when deploying the project unchanged.

## Guidelines

- **Keep the dependency list empty.** The runtime relies only on the Python
  standard library plus `boto3` (provided by the Lambda runtime). Please do not
  add third-party dependencies without a strong, discussed reason.
- **Keep `service.py` free of boto3/network I/O** so it stays unit-testable. Add
  or update tests in `tests/` for any behavior change to the service layer.
- **Match the existing style** — `ruff` enforces lint and formatting.
- **Do not commit secrets, real account IDs, or personal data.** Tracked
  repositories, AWS profiles, and tokens are all configured at deploy time, not
  hardcoded.

## Reporting issues

Found a bug or have a feature idea? Open an issue with clear reproduction steps
or a description of the proposed behavior before starting large changes, so we
can align on the approach.
