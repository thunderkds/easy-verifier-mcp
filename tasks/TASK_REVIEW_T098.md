# TASK_REVIEW — T098: The score payload discloses capped inputs

> Sibling of `tasks/TASK_GUIDE_T098.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t098_capped_disclosure.py` (11 tests, AC1–AC4; written first, all 11 red on `2452bcf`). Supervisor rerun 2026-10-14: `pytest -q tests/test_t098_capped_disclosure.py tests/test_t055_git_evidence_areas.py tests/integration/test_adapter_parity.py -k 'not container'` → `68 passed, 1 deselected in 27.20s` |
| Verification command run | ☑ pass | Agent full suite: `2 failed, 2835 passed, 2 skipped in 561.61s`. The 2 failures are `test_container_parity_is_explicitly_verified` and `test_container_redaction_proof_is_not_silent_when_docker_is_missing` (stale local Docker image, `missing=['api','data','infrastructure','operations','supply-chain']`), and both fail identically on develop `b840609`, so they predate this branch. `ruff check src tests` → `All checks passed!` (agent + Supervisor) |
| Negative cases hold | ☑ pass | No cap hit → no `capped` key in the score or pack JSON (AC2); a count exactly at the limit is not reported; ratings and the whole payload except `capped` are byte-identical on 6 real repos (k8s-ops 100, node-monorepo 59, fullstack-ts 56, nest-api 81, python-ml 64, this repo 43; all unchanged) |
| verify | ☑ pass | verify skill run by the Supervisor on 2026-10-14 03:35Z. CLI `score` and MCP stdio `score` on k8s-ops both return `capped: [{dimension: infrastructure, role: k8s-manifest, matched: 197, read: 50}]` and agree, with overall 100 unchanged. Feature confirmed working — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | code-review covered the 10 src files in the diff, plus their callers (`run_dimension`, `score_packs`, `metrics.py:4028` pack construction, which takes the None default) and the 2 test files. Findings: P0 0, P1 0, P2 1, P3 1. **P2** (confidence 100, verified): under `--scope changes` the role cap is repo-wide, before scoping, so `capped` says `read: 50` while the pack read 15 files. The existing pack warning has the same blind spot; logged as a follow-up. **P3**: the test-file pattern `**/test_*.py` matches `src/.../test_strategy.py` (pre-existing). security-review was done by hand (the built-in skill needs an `origin` remote, which this repo lacks): role names are engine constants, because repo config only adds patterns to them; values are integers; the blast-radius recount lists files without reading them. Pass |
| Full smoke suite still green (no regression) | ☑ pass | No new failures. The only 2 failing tests are the pre-existing container ones (see above), which fail the same way on develop |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend task, no UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Pure backend task, no UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | Pure backend task, no UI |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured by backend-developer on `feat/T098-capped-disclosure` at `2452bcf` (= develop, no
implementation commit yet), 2026-10-14T03:06:56Z-03:07:01Z UTC. Command, from the worktree:
`PYTHONPATH=src <main>/.venv/bin/python -m easy_verifier.adapters.cli score --repo <real-repos>/k8s-ops </dev/null`
(rc 0), summarised by a read-only JSON script:

```
== scraping  start 2026-10-14T03:06:56Z end 2026-10-14T03:07:01Z rc 0
ratings: {'api': 'abstain:below_coverage_floor', 'architecture': 'abstain:insufficient_measured_weight', 'blast-radius': 'abstain:all_metrics_abstained', 'code-quality': 'abstain:below_coverage_floor', 'data': 'abstain:below_coverage_floor', 'infrastructure': 100, 'operations': 'abstain:below_coverage_floor', 'reliability': 'abstain:all_metrics_abstained', 'requirement-fidelity': 'abstain:below_coverage_floor', 'security': 'abstain:below_coverage_floor', 'solution-fit': 'abstain:no_static_rule', 'supply-chain': 'abstain:below_coverage_floor', 'test-strategy': 'abstain:below_coverage_floor'}
overall: 100
capped key: False None
'exceed the cap' in json: False | 'matched more than' in json: False
```

infrastructure inputs and their `computed_from` sizes:
`[('iac_wildcard_iam_observed', 50), ('iac_open_ingress_observed', 50), ('iac_unencrypted_storage_observed', 50)]`

True role match count with the 50-file role cap lifted (probe: `roles.MAX_ROLE_FILES = 10**6`, then
`roles.resolve(repo, infrastructure.ROLES)`), 2026-10-14T03:08:46Z:
`{'terraform-file': 0, 'k8s-manifest': 197, 'cloud-template': 0, 'container-config': 45}`

So infrastructure is rated 100 from 50 of 197 k8s manifests and the score payload says nothing about it.

**AFTER**: Supervisor, `feat/T098-capped-disclosure` at `ec49280`, 2026-10-14T03:35:47Z–03:36:01Z UTC, same
command through the CLI and through the MCP stdio server:

```
cli rc 0
mcp rc 0
CLI capped: [{'dimension': 'infrastructure', 'role': 'k8s-manifest', 'matched': 197, 'read': 50}]
CLI overall: 100
MCP capped: [{'dimension': 'infrastructure', 'role': 'k8s-manifest', 'matched': 197, 'read': 50}]
capped equal: True
```

**DELTA**: An agent reading only the score payload can now see that infrastructure 100 on k8s-ops rests on 50 of 197 manifests (and test-strategy on 50 of 69/55/100 test files on fullstack-ts, python-ml and this repo). Before this change the payload gave no sign of it.

**WITNESS**: Supervisor (not the implementing agent), 2026-10-14T03:35Z, via the verify skill at both adapters; the trace is in `memory/event-trace/T098.jsonl`.
