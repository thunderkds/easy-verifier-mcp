# TASK_REVIEW — T046: operations dimension (#14/#25/#26/#29/#30)

> Sibling of `tasks/TASK_GUIDE_T046.md`. Everything here is **filled by the reviewer at Stage
> 4/5** — it is deliberately NOT in the guide, because the implementing agent re-reads the guide on
> every turn and never fills these two sections.
>
> Consumers resolve each section **guide first, this file second** (`.claude/hooks/lib/guide_sections.py`):
> a legacy guide that still carries these sections inline keeps working unchanged, and a stray
> review file can never override an inline section.

---

## Evidence

| Check | Result | Notes / output snippet |
|-------|--------|------------------------|
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t046_operations.py` (20 tests): AC1 discovery and roles; role globs never match source (`src/logger.ts`, `src/codeowners.service.ts`, `src/runbook/Runbook.java`, `claude.ts`, ...); AC2 rules cited per area, weights 100, floor 0.25, 4 documentation rules, no lockfile rule; AC3 tokens and pin files in the registry/generic layer; AC5 all rules met rates 100, no roles abstains naming all 7 misses, documents alone never reach the floor. Plus a sabotage pair per predicate (each flips exactly its metric), only the exact-pattern secret detectors count (template prose gives 0, a planted `AKIA…` key in AGENTS.md gives 1, never quoted), no agent files means guardrails and secrets abstain, narrow scope abstains on presence, a manifest-declared logging library counts (nested `backend/package.json`; confirmed failing with the fix reverted), and a service Makefile counts. |
| Verification command run | ☑ pass | `PYTHONPATH=src .venv/bin/python -m pytest -q` → `2309 passed, 2 skipped in 330.97s`, exit=0 (container tests ran against `easy-verifier-mcp:t046` via `COMPOSE_FILE=compose.yaml:<scratchpad>/compose.t046.yaml`); `ruff check src tests` → `All checks passed!` |
| Negative cases hold | ☑ pass | empty repo abstains `below_coverage_floor` naming all 7 roles; docs-only repo abstains; repo without agent files: guardrails/secrets abstain and only the #29 documentation rule reports missing (user decision 2026-10-07); heuristic redaction hits on CLAUDE.md prose count 0 |
| verify | ☑ pass | Real surfaces were driven: `scripts/verify_container.sh` on the rebuilt t046 image → `PASS: uid=10001, tools=12, root=read-only, reports=writable, network=none, ports=none, caps=none`; CLI `score --scope project` on 5 real repos (table below) — pass. The `verify` skill itself is left to the Supervisor. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | Left to the Supervisor (code-review and security-review at Stage 4) |
| Full smoke suite still green (no regression) | ☑ pass | Full suite as above. T068 snapshot regenerated: overall 61 unchanged and only the operations rating added. On the real repos, every other dimension's rating is unchanged. |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | pure backend task |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | pure backend task |
| **UI: Responsiveness at target viewports** | ☐ N/A | pure backend task |

### Real repositories (CLI `score --scope project`, 2026-10-07, worktree src)

"Before" = the same run's overall with the operations rating excluded (no other rating changed); this repo's before was also measured on tip 5dc54c6 (49).

| Repo | Roles found (of 7, floor 0.25) | logging | audit | codeowners | guardrails | secrets | pin | dev-env | Documentation rules present | operations | Overall before → after |
|---|---|---|---|---|---|---|---|---|---|---|---|
| easy-verifier-mcp (this) | docs, logging, agent-config (3/7) | 0 | 1 | 1 | 1 | 0 | 1 | 1 | #26 runbook (templates/RUNBOOK_template.md), #29 AGENTS.md | **40** | 49 → 48 |
| kitchd | docs, logging, agent-config (3/7) | 0 | 1 | 1 | 0 (.claude/settings.json) | 0 | 1 | 1 | #26 RUNBOOK.md, #29 .claude/agents/backend.md | **50** | 56 → 56 |
| coffee-shop-api | logging only (1/7) | 0 | 1 | 1 | abstain | abstain | 1 | 1 | none | abstains below_coverage_floor | 80 → 80 |
| ai-training | logging only (1/7) | 0 | 1 | 1 | abstain | abstain | 1 | 1 | none | abstains below_coverage_floor | 62 → 62 |
| bryony | dev-environment only (1/7) | 0 (winston in backend/package.json) | 1 | 1 | abstain | abstain | 1 | 0 (backend/Makefile, vagrant/Vagrantfile) | none | abstains below_coverage_floor | 59 → 59 |

### Known limitations

- Guardrails fail on this repo because its `.claude/` is git-ignored, and the evidence walk skips untracked ignored files by design (`context.py`). Only committed agent configuration counts.
- Bryony's logging library is declared in a manifest, not imported in the 200 sampled files. It passes the rule but does not fill the "logging or tracing in source files" role, which stays truthful to its name, so bryony still abstains at 1/7 roles.
- `audit_log_writes_missing` is textual (a call through an identifier naming "audit"). It fails on all five repos and is a lower bound; the calling agent judges the audit trail.
- `agent_config_secrets_observed` counts only the exact-pattern detectors (`private_key_pem`, `aws_access_key_id`, `aws_secret_access_key`, `jwt`, `credential_assignment`; Supervisor 2026-10-07). A bare high-entropy token with no key name is not counted.
- `Makefile`/`justfile` presence counts as a one-command setup. Presence is the evidence; whether it really sets up the environment is not judged.
- Incident handling, SLO attainment and access review are not verifiable offline. Only their documents are checked.

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured before any T046 commit (tip 5dc54c6), command
`date -u; PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli list-dimensions` (JSON abridged to names):

```
Wed Oct  7 10:29:35 AM UTC 2026
11 ['api', 'architecture', 'blast-radius', 'code-quality', 'data', 'reliability', 'requirement-fidelity', 'security', 'solution-fit', 'supply-chain', 'test-strategy']
```

No `operations` entry exists.

**AFTER**: same command on the T046 worktree (JSON abridged to names):

```
Wed Oct  7 03:02:20 PM UTC 2026
12 ['api', 'architecture', 'blast-radius', 'code-quality', 'data', 'operations', 'reliability', 'requirement-fidelity', 'security', 'solution-fit', 'supply-chain', 'test-strategy']
```

**DELTA**: A user can now get a cited `operations` rating covering observability/audit (#14), ownership (#26), coding-agent guardrails and secrets (#29) and reproducible setup (#30), with present/missing documentation checks for incident/change (#25), SLO (#14), runbook (#26) and agent instruction (#29) documents. A repository with too little evidence abstains, never 0.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T046.jsonl`, never the
implementing agent alone]
