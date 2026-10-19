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

`scripts/verify_release_gate.sh` covers the stdio boundary only. It does not start or probe the
shared container; use the shared-container checks under Supplemental checks.

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
python -m pytest tests/test_t101_shared_container.py -q
```

Shared container (HTTP): the last command covers the shared container's code paths. To observe the
running container, follow the "Shared container (HTTP)" surface of the `verify` skill
(`.claude/skills/verify/SKILL.md`) and record the result beside the others.

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

## Landing site

The static landing page lives in `site/` (`site/index.html`, `site/sample-score.json`). It is
deployed by the Vercel Git integration, production from `main`. No agent pushes or deploys; these
steps are the operator's.

### Connect the repository (one time, Vercel dashboard)

1. Add New Project, then import `thunderkds/easy-verifier-mcp` from GitHub.
2. Framework Preset: **Other**. Root Directory: `.` (repo root).
3. Build Command: leave empty (no build). Install Command: leave empty. Output Directory: leave to
   `vercel.json`, which sets `{"outputDirectory": "site"}`.
4. Settings, Git: Production Branch **`main`**.
5. Deploy.

### When it goes live

Nothing goes live until `develop` is released to `main`. A push to `main` deploys production with
no preview step; merging to `main` makes the page public at once. Push a non-`main` branch for a
preview (confirm the integration's preview setting in the dashboard; not verified here).

### What is served versus uploaded

`vercel.json`'s `outputDirectory` is what keeps `memory/`, `tasks/` and the rest unserved: they are
committed, so they are in the clone Vercel builds from, but only `site/` is served (the repository
is public regardless). `.vercelignore` is an allowlist (`*`, then `!site/`, `!site/**`,
`!vercel.json`) that stops a Vercel CLI deploy from uploading the working tree, including the
gitignored `reports/`. Whether `.vercelignore` is honoured on the automatic Git path is not
established: Vercel's docs do not say. To check on a real deployment, open it in the dashboard and
append `/_src` to its URL (team-only Source view); if `memory/` or `tasks/` appear there, Vercel
retains the full repository on each push to `main`. Either way only `site/` is served.
`tests/test_site_deploy_config.py` guards both files.

### Refresh the sample score snapshot

`site/sample-score.json` is a committed snapshot; a drift test fails if the page and engine
disagree. To regenerate it, save this as `reduce.py`:

```python
import json, sys
d = json.load(open(sys.argv[1]))
out = {"commit": sys.argv[2], "date": sys.argv[3], "scope": "project",
       "overall": d["overall"]["value"],
       "ratings": [({"dimension": r["dimension"], "value": r["value"]} if r.get("value") is not None
                    else {"dimension": r["dimension"], "reason_code": r["reason_code"]}) for r in d["ratings"]],
       "areas_measured": list(d["areas_measured"]), "areas_without_rule": list(d["areas_without_rule"])}
json.dump(out, open(sys.argv[4], "w"), indent=2); open(sys.argv[4], "a").write("\n")
```

then, from the repo root:

```bash
python -m easy_verifier.adapters.cli score --repo . --scope project </dev/null > self.json
python reduce.py self.json "$(git rev-parse --short HEAD)" "$(date -u +%F)" site/sample-score.json
```

### Check the live page

```bash
curl -sI https://<project>.vercel.app/ | head -1          # expect HTTP/2 200
curl -s -o /dev/null -w '%{http_code}\n' https://<project>.vercel.app/memory/MEMORY.md   # expect 404
```
