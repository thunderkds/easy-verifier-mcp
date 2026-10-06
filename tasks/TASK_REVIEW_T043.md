# TASK_REVIEW — T043: New dimension: reliability

> Sibling of `tasks/TASK_GUIDE_T043.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t043_reliability.py` (78 tests, written test-first; failed on the pre-change code with `ImportError: cannot import name 'reliability_findings'`). AC1 `test_reliability_is_discoverable_with_purpose_and_roles`; AC2 `test_rules_are_cited_weighted_and_labelled_by_area`, `test_floor_is_the_user_approved_quarter_inclusive`, `test_business_continuity_is_a_documentation_rule_only`; AC3 `test_fields_are_optional_registry_fields_feeding_the_rules`, `test_curated_values_load_cleanly_with_https_citations`, `test_dimension_module_holds_no_language_tokens`; AC5 `test_every_rule_met_rates_100_with_its_document_present`, `test_no_role_filled_abstains_below_the_floor_with_named_misses`. Implementer run 2026-10-06T04:53Z: `78 passed in 3.15s` |
| Verification command run | ☐ pass / ☒ fail (environment only) | Implementer run at the code of `2ab0928` (docs-only `c205feb` after), 2026-10-06T04:47:18Z..04:51:45Z: `PYTHONPATH=src .venv/bin/python -m pytest -q` → `2 failed, 2087 passed, 2 skipped in 266.67s`; `python -m ruff check src tests` → `All checks passed!`. The 2 failures are the container tests (`test_container_parity_is_explicitly_verified`, `test_container_redaction_proof_is_not_silent_when_docker_is_missing`): the local image `easy-verifier-mcp:0.1.0` was built 2026-10-04 and `scripts/verify_container.sh` now expects the new tool: `FAIL: tools/list did not return the expected tool set (missing=['reliability'], unexpected=[])`. Not rebuilt by the implementer: a compose build retags the shared 0.1.0 image while T082 verifies in parallel. Baseline before the change (eb16069): `2006 passed, 2 skipped in 195.30s` |
| Negative cases hold | ☑ pass | Go `if err != nil { return err }` and `fmt.Errorf` wrapping are not swallowed; a handler holding a comment, or `pass  # why`, is not counted; a string quoting `except: pass` is not counted; test files are not scanned; a loop header (`for row in session.query(...)`) and a loop around a function definition are not query-in-loop; a file setting a client-wide deadline (`AbortController`, `.setTimeout(`) bounds its wrapper calls; timeout/retry/loop rules abstain with nothing to judge; an unresolved `--scope task` reads nothing and names all four sources. Sabotage (each predicate hardwired, scratch copy): `_in_loop`→True fails 5 tests, →False fails 6; comments blanked in the swallowed scan fails 1; wrapper ignored fails 1 |
| verify | ☒ pass | Supervisor 2026-10-06: live CLI on the T043 branch — `list-dimensions` lists `reliability` with its purpose and roles; `score --repo coffee-shop-api --scope project < /dev/null` → overall 72, reliability 100 (matches implementer's 65→72) — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Affected set: new `dimensions/reliability.py`; additions in `core/metrics.py` (scanner, 4 metrics, a per-view cache field on `_PackView`), `core/metric_tables.py` (9 optional fields), `core/registry.py` (field names), `core/judge.py` (floor, 4 rules, 1 documentation rule), `core/improve.py` / `core/report.py` (texts), curated TOMLs, `scripts/verify_container.sh` (tool set). No existing metric, rule or weight changed: the regenerated T068 snapshot keeps every existing rating, metric and the overall (61) byte-identical. Shared hubs touched only by addition (judge tables, METRIC_DEFINITIONS). Security pass done by hand (built-in `security-review` needs `origin/HEAD`): reads go only through `read_source` (`_code_extract._read`), excerpts pass the pipeline's redaction, new token fields are in `_TOKEN_FIELDS` so local-layer values keep the 2-wildcard ReDoS bound; one finding fixed: per-match newline recounting over whole files was quadratic (an adversarial 1.15 MB file with 75k matches now scans in 0.73 s) |
| Full smoke suite still green (no regression) | ☒ pass (code) / container pending | Supervisor rerun 2026-10-06 after weight sign-off `4d09a2d`: `2 failed, 2087 passed, 2 skipped in 222.71s`; `ruff check` All checks passed. The 2 failures are `test_container_parity_is_explicitly_verified` and `test_container_redaction_proof_is_not_silent_when_docker_is_missing`: the local `easy-verifier-mcp:0.1.0` image (built 2026-10-04) lacks `reliability`. Image is rebuilt from develop after the T082+T043 merge; the result is recorded in the Wave 16 integration commit |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend task: no UI (Spec Constraint 11) |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Pure backend task: no UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | Pure backend task: no UI |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured by backend-developer in worktree `easy-verifier-mcp-T043` at `eb16069` (develop, no T043 commit yet).

```text
$ PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli list-dimensions < /dev/null   # 2026-10-06T04:04:09Z
dimension names: architecture, blast-radius, code-quality, requirement-fidelity, security, solution-fit, test-strategy  (7 dimensions; no 'reliability')
exit=0

$ ... cli score --repo /home/hungnguyenhuu/workspace/training/tien.nguyen/nestjs-training/coffee-shop-api --scope project < /dev/null   # 2026-10-06T04:04:25Z .. 2026-10-06T04:04:27Z, exit=0
overall 65 (4 of 7 dimensions)
ratings: architecture=80 blast-radius=all_metrics_abstained code-quality=71 requirement-fidelity=50 security=59 solution-fit=no_static_rule test-strategy=insufficient_measured_weight
'reliability' anywhere in the payload: False

$ ... cli score --repo /home/hungnguyenhuu/workspace/project/bryony/bryony --scope project < /dev/null   # 2026-10-06T04:04:39Z .. 2026-10-06T04:04:51Z, exit=0
overall 69 (4 of 7 dimensions)
ratings: architecture=83 blast-radius=all_metrics_abstained code-quality=67 requirement-fidelity=below_coverage_floor security=50 solution-fit=no_static_rule test-strategy=75
'reliability' anywhere in the payload: False

$ ... cli score --repo /home/hungnguyenhuu/workspace/pets/hungnguyen111/kitchd --scope project < /dev/null   # 2026-10-06T04:04:51Z .. 2026-10-06T04:04:56Z, exit=0
overall 72 (4 of 7 dimensions)
ratings: architecture=100 blast-radius=all_metrics_abstained code-quality=70 requirement-fidelity=60 security=59 solution-fit=no_static_rule test-strategy=insufficient_measured_weight
'reliability' anywhere in the payload: False
```

**AFTER**: captured by backend-developer in the worktree at `c205feb` (same commands as BEFORE).

```text
$ PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli list-dimensions < /dev/null   # 2026-10-06T04:52:21Z at c205feb
dimension names: architecture, blast-radius, code-quality, reliability, requirement-fidelity, security, solution-fit, test-strategy  (8 dimensions)
reliability roles: source files of a registry language; outbound HTTP client calls in source files; database access calls in source files; readme
exit=0

$ ... cli score --repo .../coffee-shop-api --scope project < /dev/null   # 2026-10-06T04:52:21Z .. 2026-10-06T04:52:23Z at c205feb, exit=0
overall 72 (5 of 8 dimensions)
ratings: architecture=80 blast-radius=all_metrics_abstained code-quality=71 reliability=100 requirement-fidelity=50 security=59 solution-fit=no_static_rule test-strategy=insufficient_measured_weight
  reliability input swallowed_errors_observed = 0 (pass, weight 35)
  reliability input queries_in_loops_observed = 0 (pass, weight 20)
  reliability unmeasured outbound_calls_without_timeout_observed: no outbound call was found in the 85 source-file excerpt(s) scanned, so there is nothing to judge
  reliability unmeasured retries_without_backoff_observed: no retry statement was found in the 85 source-file excerpt(s) scanned, so there is nothing to judge
  reliability documentation #32: missing

$ ... cli score --repo .../project/bryony/bryony --scope project < /dev/null   # 2026-10-06T04:52:23Z .. 2026-10-06T04:52:40Z at c205feb, exit=0
overall 67 (5 of 8 dimensions)
ratings: architecture=83 blast-radius=all_metrics_abstained code-quality=67 reliability=61 requirement-fidelity=below_coverage_floor security=50 solution-fit=no_static_rule test-strategy=75
  reliability input swallowed_errors_observed = 0 (pass, weight 35)
  reliability input outbound_calls_without_timeout_observed = 5 (fail, weight 35)
  reliability input queries_in_loops_observed = 0 (pass, weight 20)
  reliability unmeasured retries_without_backoff_observed: no retry statement was found in the 200 source-file excerpt(s) scanned, so there is nothing to judge
  reliability documentation #32: missing

$ ... cli score --repo .../pets/hungnguyen111/kitchd --scope project < /dev/null   # 2026-10-06T04:52:40Z .. 2026-10-06T04:52:47Z at c205feb, exit=0
overall 58 (5 of 8 dimensions)
ratings: architecture=100 blast-radius=all_metrics_abstained code-quality=70 reliability=0 requirement-fidelity=60 security=59 solution-fit=no_static_rule test-strategy=insufficient_measured_weight
  reliability input swallowed_errors_observed = 4 (fail, weight 35)
  reliability input outbound_calls_without_timeout_observed = 20 (fail, weight 35)
  reliability input queries_in_loops_observed = 4 (fail, weight 20)
  reliability unmeasured retries_without_backoff_observed: no retry statement was found in the 185 source-file excerpt(s) scanned, so there is nothing to judge
  reliability documentation #32: missing
```

Cited sites checked by hand: kitchd `apps/web/src/features/tasks/TasksPage.tsx:93` is `.catch(() => {})`; `apps/web/src/components/AnnouncementsWidget/api.ts:23` is `fetch(...)` with no signal; `apps/api/src/inventory/alerts/alerts.service.ts:71` is `this.prisma.user.findMany(...)` inside `for (const ingredient of newlyLow)` (a real N+1). bryony `backend/platform/db/services/dashboard-benchmarking-data.js:1087` is `http.request(this.exportOptionsPost, ...)` with no timeout. coffee-shop-api's 6 catch blocks all handle or rethrow (0 is correct). bryony `--all` (every batch, 35 s): reliability 22 (18 swallowed, 45 of 50 calls without a deadline, 0 of 153 queries in loops), the 18 empty catches being in `backend/scripts/`, which batch 1 does not read.

**DELTA**: A user can now score a repository's reliability (swallowed errors, outbound calls without a deadline, retries without backoff, queries in loops), get its transaction and idempotency code quoted for the agent, and see whether a business-continuity document exists; before, no dimension measured areas #6, #12, #13, #15 or #32.

**WITNESS**: Supervisor, 2026-10-06 — Stage 4 code-review of `develop...feat/T043-reliability` (rules, citations, floor, documentation rule; P0 0 · P1 0), weights and #6 evidence-only signed off by the user, full suite rerun (2087 passed; 2 stale-image container tests) and a live coffee-shop-api score (reliability 100, overall 72). Implementer reruns of bryony (61) and kitchd (0) checked against cited sites (real N+1 at kitchd `alerts.service.ts:71`).