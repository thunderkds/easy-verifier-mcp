# TASK_GUIDE — T116: Vercel deploy configuration + runbook
**Date**: 2026-10-19
**Complexity Level**: C1
**Risk Level**: Medium
**Priority**: P1
**Assigned agent**: common-infrastructure
**Agent guide**: `.claude/agents/common-infrastructure.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC_SITE.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/common-infrastructure.md`
5. Note the **Complexity Level** above and apply the matching process from the Complexity matrix in `.claude/agents/general-agent-template.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

User, 2026-10-19: deploy the verifier's landing page like the kit's (`https://personal-agentic-claude.vercel.app/`); deploy route chosen: **Vercel Git integration, production from `main`**.

**Restated intent**:
> Add the minimum config so Vercel serves exactly `site/` with no build, never uploads anything else, and document the operator's exact steps to connect the repo and go live — without any agent pushing or deploying.

**Out of scope**:
- Connecting the Vercel project, pushing to GitHub, merging develop → `main` (operator; `ship`)
- Page content (T115)
- A CI workflow that deploys

**Requirement Refs**: `PROJECT_SPEC_SITE.md` §Stack decision, §Release dependency, §Drift constraint (snapshot regeneration command).

**Why Risk Medium**: a wrong `outputDirectory` or a missing/denylist `.vercelignore` publishes or uploads `memory/`, `tasks/`, `reports/` (scores of other repos) to a third party.

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (Supervisor, against the 2026-10-19 answers)
- [x] Domain terms align with `PROJECT_SPEC_SITE.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] Requirement Refs exist and are covered

---

## Dependencies & Reachability

**Depends on**: T115 — `site/index.html` and `site/sample-score.json` must exist

**Entry point**: `vercel.json`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `vercel.json` parses as JSON and equals `{"outputDirectory": "site"}` (no `buildCommand`, no rewrites, no functions) | serve exactly `site/`, no build |
| 2 | `.vercelignore` is an allowlist: first effective line `*`, then only `!site/`, `!site/**`, `!vercel.json`; comment explains why (copy the kit's reasoning) | never upload anything else |
| 3 | Negative: a test fails if any `!` line in `.vercelignore` re-admits a path other than those three, or if `*` is removed | upload safety |
| 4 | `docs/RELEASE_GUIDE.md` gains a "Landing site" section with: (a) Vercel dashboard steps — import `thunderkds/easy-verifier-mcp`, framework preset "Other", root directory `.`, production branch `main`, no build command; (b) the statement that nothing goes live until develop is released to `main`; (c) the exact snapshot regeneration command from T115's TASK_REVIEW; (d) how to check the live page (`curl -sI https://<project>.vercel.app/` → 200, and `curl -s .../memory/MEMORY.md` → 404) | operator steps, Release dependency |
| 5 | README's `## Documentation` list links the site URL as "pending first deploy" placeholder only if the user confirms the Vercel project name; otherwise README is untouched | avoid publishing a wrong URL |

---

## Evaluation & Acceptance

### Success Criteria

| # | Given | Expect | How it's checked |
|---|-------|--------|------------------|
| 1 | Repo tree after T115 | `tests/test_site_deploy_config.py` passes | automated |
| 2 | `.vercelignore` with an extra `!memory/` line | test fails | automated (AC 3) |
| 3 | Allowlist applied to the real tree | the set of admitted paths is exactly `site/**` + `vercel.json` | automated: walk the tree with gitignore-style matching (stdlib `fnmatch` per the kit's approach) |

### Verification Command

```bash
cd "$(git rev-parse --show-toplevel)"   # repo root
PYTHONPATH=src:.venv/lib/python3.12/site-packages /usr/bin/python3.12 -m pytest tests/test_site_deploy_config.py -q
```

---

## UI / Design Acceptance Criteria

N/A — config + docs only; no UI. All three UI Evidence rows are ☐ N/A (no rendered surface changes).

---

## Approach

**Pattern reference**: `~/workspace/pets/personal-agentic-claude/vercel.json`, `~/workspace/pets/personal-agentic-claude/.vercelignore`, and the Vercel section of `~/workspace/pets/personal-agentic-claude/RUNBOOK.md` (lines ~115–150, including its caveat that `.vercelignore` behaviour on the automatic Git path is not established). Carry that caveat over honestly rather than claiming the allowlist governs Git-integration builds.

Test first (`tests/test_site_deploy_config.py`), then the two config files, then the docs section.

---

## Edge Case Checklist

- [ ] `.vercelignore` comment lines and blank lines are ignored by the parser in the test
- [ ] `reports/` is gitignored locally but must still be excluded by the allowlist (CLI deploys upload the working tree, not git)
- [ ] The Git-integration path builds from GitHub's clone — `memory/`, `tasks/` are committed and therefore *in* that clone; document that `outputDirectory` is what keeps them unserved, and that the repo itself is public anyway

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `vercel.json` | new |
| `.vercelignore` | new |
| `docs/RELEASE_GUIDE.md` | add "Landing site" section |
| `tests/test_site_deploy_config.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `site/**` | T115 |
| `src/**` | engine scope |
| `PROJECT_KANBAN*.md`, `memory/**` | Supervisor-only |

---

## Test Plan

`tests/test_site_deploy_config.py` for AC 1–3 and Success 3; doc section reviewed by the Supervisor against AC 4.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Risk Medium)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T116.md` Evidence (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — or ☐ N/A with reason (no runnable surface until the operator connects Vercel)
- [ ] Supervisor notified: task ready for Stage 4 review
