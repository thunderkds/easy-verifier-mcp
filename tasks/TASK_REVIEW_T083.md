# TASK_REVIEW — T083: changes-scope crash on non-code diff

> Sibling of `tasks/TASK_GUIDE_T083.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t044_api.py::test_non_code_diff_abstains_breaking_metric_and_score_completes`, `::test_removed_route_in_unread_file_abstains_rather_than_citing_nothing` — red on 129de71 (MetricCitationError / uncited value 1), green on f0fc3bb. Supervisor re-run 2026-10-08: `20 passed in 3.34s` |
| Verification command run | ☑ pass | `python -m ruff check src tests` → `All checks passed!`; full suite: see smoke row |
| Negative cases hold | ☑ pass | diff touching a route file still yields a cited value (bryony `--ref HEAD~1..HEAD`: value 0, cited, exit 0); existing T044 breaking-change tests (removed route/spec path counted) still pass |
| verify | ☑ pass | Supervisor 2026-10-08, tfvars-only repro `--scope changes --ref HEAD~1..HEAD`: CLI on base src exit=2 `validation error: metric 'breaking_api_changes_observed' (api) reports a value but cites no evidence`; CLI on fix src exit=0, api metric `{'abstained': True, 'reason': 'no API specification or route source file in this diff was read'}`; MCP `score` same args: `isError False`, same abstention — CLI/MCP agree, pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | reviewed `dimensions/api.py:_breaking_metric` + its sole caller `api.py:173` + `tests/test_t044_api.py`; security/perf/migration/adversarial/api personas skipped (9-line logic diff, no input/secret/loop/schema/signature change). Findings: P0 0 / P1 0 / P2 1 (partial-read case: removals in unread files still counted when another file is read — pre-existing, follow-up) / P3 1 (second test could also assert "cannot be cited"). Security review (manual — built-in needs origin/HEAD, absent): abstention text is fixed string + int, passed through `redact()`; no findings |
| Full smoke suite still green (no regression) | ☑ pass | Supervisor re-run 2026-10-08 on f0fc3bb: `2 failed, 2340 passed, 2 skipped in 315.06s`. The 2 failures are the container tests `test_adapter_parity.py::test_container_parity_is_explicitly_verified` and `test_redaction_proof.py::test_container_redaction_proof_is_not_silent_when_docker_is_missing`; they also fail with the change stashed (implementer check). Known issue: stale local Docker image (MEMORY.md). Not a regression; pass |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | backend-only metric fix, no UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | backend-only |
| **UI: Responsiveness at target viewports** | ☐ N/A | backend-only |
| Repro loop | ☑ pass | temp repo, commit 2 changes only `prod.tfvars`; `score --scope changes --ref HEAD~1..HEAD </dev/null` → exit 2 on 129de71 (see BEFORE) |
| Regression test | ☑ pass | `tests/test_t044_api.py` (2 tests above) |
| Smoke suite | ☑ pass | bug-specific: same repro exits 0 on CLI and MCP after fix (verify row) |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured 2026-10-08T02:54:40Z on base 129de71 (pre-fix). Repro: temp git repo, commit 1 = `prod.tfvars` + README, commit 2 changes only `prod.tfvars`; `easy-verifier score --repo <r> --scope changes --ref HEAD~1..HEAD </dev/null` (via `python -c` calling `easy_verifier.adapters.cli.main`, same entry point):

```
2026-10-08T02:54:40Z
validation error: metric 'breaking_api_changes_observed' (api) reports a value but cites no evidence
exit=2
```

(Note: changes scope needs `--ref`; a bare working-tree diff resolves to "changes scope could not be resolved", so the repro uses a committed range.)

**AFTER**: 2026-10-08T02:55:41Z same repro, post-fix: score completes (exit 0), api metric:
`"name": "breaking_api_changes_observed", "outcome": {"abstained": true, "reason": "no API specification or route source file in this diff was read"}`. Real repo `project/bryony/bryony` `--ref HEAD~1..HEAD` (2026-10-08T02:57:59Z): exit=0, metric value 0, cited.

**DELTA**: `score --scope changes` on a diff with no API spec or route source file now completes, with the breaking-change metric abstaining honestly instead of crashing the whole score.

**WITNESS**: Supervisor, 2026-10-08 — independently re-ran the repro on base vs fix src (CLI) and on the MCP adapter; trace attributed via active_task (`memory/event-trace/T083.jsonl`).
