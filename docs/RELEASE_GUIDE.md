# Release guide

This guide is the reproducible v1 release runbook for `easy-verifier-mcp`.

## Release rule

A release candidate is ready only when the exact candidate is clean and published on
`github/develop`, and the release gate exits `0` with every required KPI reported as `PASS`.

`NOT VERIFIED` is a real gate result, not a pass. Missing Docker access, an unavailable MCP stdio
process boundary, a skipped required test, or any other missing proof must leave the gate non-zero
and the release unapproved.

## Prerequisites

- Run from the repository root.
- Verify the candidate commit and `github/develop` point to the same intended revision.
- Use a compatible Python environment with the project dependencies, including `pytest` and `mcp`.
- Have a working Docker daemon and permission to access its socket.
- Keep the candidate clean; do not treat uncommitted or unpublished changes as release evidence.

## Exact release command

```console
bash scripts/verify_release_gate.sh
```

The wrapper performs these required checks in order:

1. Host integration tests for adapter parity, redaction, self-containment, findings rejection, and
   discovery.
2. Container integration tests with Docker explicitly required.
3. The container hardening verifier, including the real MCP stdio boundary and path scrubbing.
4. The KPI summary, which is allowed to run only after the earlier checks pass.

The command must finish with output equivalent to:

```text
RESULT integration=0 container=0 release=0
```

The exact test counts may change as the suite evolves; the exit codes and KPI statuses may not.

## Supplemental checks

Run these against the same candidate and record their exit codes:

```console
PYTHONPATH=src <compatible-python> -m pytest -q --tb=short
ruff check src tests
ruff format --check src tests
bash -n scripts/verify_release_gate.sh
docker compose config --quiet
git diff --check
python -m pytest tests/test_t018_readme.py -q
```

The compatible interpreter must be recorded in the evidence; do not substitute a stale editable
installation or rely on a piped command whose exit code hides a failed test.

## Evidence and blocked outcomes

Record the following in `tasks/TASK_REVIEW_T023.md`:

- candidate commit and remote ref identity;
- exact commands, interpreter, environment, and exit codes;
- host, MCP stdio, and container results separately;
- all KPI rows and their statuses;
- any `NOT VERIFIED` proof and the environmental reason.

If any required check is unavailable or fails, keep the release task open and route the defect or
environmental remediation to a scoped follow-up. Do not edit the implementation or weaken an
assertion merely to obtain a green release result.
