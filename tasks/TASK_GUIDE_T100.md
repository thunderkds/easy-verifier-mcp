# TASK_GUIDE — T100: Remove personal and client repository identifiers from every tracked file
**Date**: 2026-10-14
**Complexity Level**: C2
**Risk Level**: Medium (touches ~141 files across src comments, tests, docs, tasks and memory; a wrong replacement could break doc-truth tests or a vendored NOTICE)
**Priority**: P0 (blocks the push of `feat/wave20-T098-T099`)
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`
**Depends on**: none

## Feature Task Guide — T100

### Restated Intent (user, 2026-10-14)
"review the repos and remove the personal repos inside this one". The user chose **names in tracked
files**: scrub the names and absolute paths of the user's personal and client repositories, and of
other people, from every tracked file before the branch is pushed. The user also chose the
**squashed push branch** for history: the Supervisor builds a single commit on `github/develop`
after this task merges. The agent does **not** touch git history, branches or remotes.

### Identifiers to remove (case-insensitive) and their replacements
Use these neutral aliases consistently in every file.

The original names are deliberately not repeated in this tracked guide; the alias-to-original map,
the absolute paths and the literal AC1 search pattern are in `.local/real-repos.md` (local,
git-ignored). The aliases describe each repo's shape so examples stay meaningful.

| Alias | Shape |
|---|---|
| `node-monorepo` | the Node.js monorepo client project (its git repo is one level below its parent folder) |
| `node-api` / `next-web` / `next-app` | the client's Node API / Next.js web app / any other repo of that client |
| `fullstack-ts` | the user's full-stack TypeScript monorepo |
| `k8s-ops` | the Kubernetes / Compose ops repo |
| `python-ml` | the Python ML training repo |
| `nest-api` | the NestJS training API |
| `client-app` | the client organisation's folder |
| `<real-repos>/<alias>` | replaces an absolute path to a real repo |
| `<repo>` | replaces this repo's absolute path (or a sibling worktree as `<repo>-Txxx`); the redaction test uses a neutral absolute-looking path, `/home/user/work/easy-verifier-mcp` |
| "the user" or a role | replaces a person or handle name in prose; in a path the name goes with the path |

Leave alone: the public GitHub owner `thunderkds` (it is the remote itself), and generic fixtures
like `/home/user/keys/` and `/home/you/.easy-verifier-sot`.

Identifiers in code (test helper names) are renamed with the alias
(`_monorepo_shaped`, `_monorepo_code_quality`), including every importer
(e.g. `tests/test_t069_report_summary.py` imports from `test_t067`).

### Where the real paths go instead
Real-repo verification must keep working (project rule: Done means verified on real repos). Create
`.local/real-repos.md`, mapping each alias to its absolute path, and add `/.local/` to `.gitignore`.
Every tracked guide/doc "Real repos" list then names aliases and says
"absolute paths: `.local/real-repos.md` (local, git-ignored)".

### Special cases
- `src/easy_verifier/registry/vendored/NOTICE` is generated from `scripts/vendor_sources.py`. Change
  the reasons in the script, then make NOTICE match exactly as the script would emit it (regenerate
  if the script supports it offline; otherwise edit both identically). Existing NOTICE/vendor tests
  must pass.
- `scripts/verify_release_gate.sh` hardcodes another person's interpreter path. Replace it with an
  environment variable (e.g. `EV_RELEASE_PYTHON`) that fails with a clear message when unset. Do not
  change any other behaviour.
- `docs/EVALUATION_GUIDE.md` / `docs/AREA_COVERAGE.md` / `README.md` examples are pinned by doc-truth
  tests (`test_t071_evaluation_docs.py`, `test_t080_evaluation_guide_refresh.py`). Rename in docs and
  tests together; numbers stay identical.
- Tracked `memory/*.md` (MEMORY.md, decisions, learnings, glossary, codebase-map) and every `tasks/*`
  file are scrubbed too. Keep each entry's meaning; change only the identifiers.
- `.claude/` tracked files (agents, skills, hooks): scrub them too if they match.

### Acceptance Criteria
| # | Criterion |
|---|-----------|
| 1 | `git grep -nIiE '<AC1 pattern>'` (the 13-token pattern, written out in `.local/real-repos.md`) on the branch returns **nothing** (paste the empty output and its exit code 1) |
| 2 | `git grep -nIE '/home/' ` returns only the generic fixtures (`/home/user/...`, `/home/you/...`); paste the output |
| 3 | `.local/real-repos.md` exists, is git-ignored (`git check-ignore -v .local/real-repos.md` pasted), and maps all 7 aliases to real paths |
| 4 | New test `tests/test_t100_no_personal_identifiers.py` runs the AC1 search over `git ls-files` and fails if any identifier reappears (red before the scrub, green after). The forbidden list must be stored so the test file does not itself contain the names in plain text (e.g. as sha256 digests of lowercased tokens, or reversed strings) |
| 5 | Full suite passes except the 2 known container tests (`test_container_parity_is_explicitly_verified`, `test_container_redaction_proof_is_not_silent_when_docker_is_missing`, stale Docker image); `ruff check src tests` clean |
| 6 | No behaviour change: `score --repo <real-repos>/k8s-ops` and `<real-repos>/fullstack-ts` give the same payload before and after, except text that echoes identifiers. Paste the overall and ratings before → after |

### Files to Change (prediction, not contract)
Every tracked file matched by the AC1 search (~141: `tasks/` 105, `tests/` 16, `src/` 5, `docs/`, `memory/`, `scripts/`, root `*.md`), `.gitignore`, the new `.local/real-repos.md` (untracked), and the new test.

### Files Must NOT Touch
Detection logic and thresholds in `src/` (only comments, docstrings and NOTICE text change). Git history, branches and remotes.

### Verification Command
```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
git grep -nIiE '<AC1 pattern>' ; echo "exit $?"
```

### Real repos
Absolute paths: `.local/real-repos.md` (local, git-ignored). Run scans in the background with `</dev/null`.
Agent worktrees have no `.venv`, so use the main checkout's interpreter with `PYTHONPATH=src`.

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T100.md`.

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T100.md`.

## UI / Design Acceptance Criteria

> N/A — no UI. All three UI Evidence rows are ☐ N/A.
