# TASK_REVIEW — T082: The score names the evaluation areas it does not measure

> Sibling of `tasks/TASK_GUIDE_T082.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☒ pass | `tests/test_t082_uncovered_areas.py` — 13 new tests, `13 passed in 0.26s`. AC1: `test_abstained_metric_does_not_count_its_area`, `test_code_quality_only_measures_only_its_measured_areas`, `test_abstained_dimension_rule_areas_are_not_measured_but_its_doc_result_is`, `test_blended_counts_rule_areas_and_agent_rated_counts_none`, `test_areas_measured_are_in_areas_order_without_duplicates`; AC1/SC1: `test_areas_without_rule_are_the_not_yet_rows_of_the_area_doc` (parses `docs/AREA_COVERAGE.md`, asserts exactly the 21 "Not yet" rows); AC2: `test_adding_a_documentation_rule_removes_its_area`, `test_adding_a_rating_rule_removes_its_area` (monkeypatched tables); AC3: `test_overall_disclosure_states_the_measured_area_count`; AC5: `test_withheld_overall_still_carries_both_lists`, `test_report_shows_area_lists_when_overall_is_withheld`; AC4: `test_report_panel_shows_count_and_folded_uncovered_list` (escaping: `Error handling &amp; safe degradation` present, raw `&` absent); validator: `test_forged_overall_area_list_is_rejected`. **Sabotage check** (full-tree copy, one guard broken at a time): ignore documentation results, count unmeasured rule areas, ignore GatedRating unwrapping, ignore DOCUMENTATION_RULES in the uncovered list, drop `esc`, hide panel on withheld overall, drop the payload key, disable the validator, drop the disclosure count, unordered list — **each made at least one named test fail** (10/10). |
| Verification command run | ☒ pass | 2026-10-06T04:15:58Z, worktree: `PYTHONPATH=src .venv/bin/python -m pytest -q` → `2021 passed, 2 skipped in 216.31s (0:03:36)`, exit 0. `.venv/bin/python -m ruff check src tests` → `All checks passed!`, exit 0. Baseline (clean `git archive eb16069` copy): `7 failed, 1999 passed, 2 skipped` — the 7 are git-tracked-file tests (t003 changes scope, t029/t051/t053) that fail only because an archive is not a git repo; they pass in the worktree. Delta +15 = 13 new T082 tests + 2 new `DECLARED` identifier cases in t071. |
| Negative cases hold | ☒ pass | abstained metric (area 31) not counted; abstained dimension's rule areas (security 10, 20) not counted while its documentation result (area 8) is; failed dimension contributes nothing; agent-rated GatedRating contributes no rule area; forged `areas_measured` (unknown name, wrong order) rejected with `ValueError`. |
| **AC 6 — no rating value changes** | ☒ pass | Tests updated only where they pin the payload key set or exact payload: `tests/test_score_operation.py` (2 key sets + `areas_measured`, `areas_without_rule`), `tests/test_t071_evaluation_docs.py` (`DECLARED` gains both keys), `tests/snapshots/t068_under_cap_score.json` regenerated — scripted diff vs the committed snapshot: `added keys: ['areas_measured', 'areas_without_rule'] removed: []`, `changed top-level keys: ['overall']`, `overall changed fields: ['disclosure']` (gains "measured 3 of 32 evaluation areas"). Real repo: every payload key other than the two new ones is byte-identical before/after, and `overall` differs only in the disclosure clause (see AC 8). |
| **AC 8 — real repo** | ☒ pass | nest-api, `--scope project`, 2026-10-06T04:09:34Z. JSON: `overall 65 -> 65`; `areas_measured (8): ["Architecture & dependency direction", "Business-rule correctness", "AuthN/Z, sessions, offboarding", "Threat modeling, abuse cases, appsec", "Type safety & code quality", "Maintainability, reuse, library judgment, patterns", "Dependencies, vulns, licenses, obsolescence", "Documentation source-of-truth governance"]`; `areas_without_rule (21): ["Financial integrity & historical reconstruction", "Data model, constraints, migrations", "Transactions, concurrency, idempotency", "API contracts, validation, versioning", "PHI minimization, retention, test-data safety", "Infra security: IAM, networking, KMS, secrets", "Error handling & safe degradation", "Retries, deadlines, unknown outcomes, vendor outages", "Observability, auditing, SLOs, error budgets", "Performance, scalability, capacity, cost", "Accessibility, responsive UX, browser compat", "CI quality & reproducibility", "Artifact provenance, SBOM, signing, promotion, rollback", "Terraform state, environment, account, drift", "Database HA, backups, restore, DR", "Incident response, change mgmt, access review", "Configuration ownership & operational readiness", "Vendor, BAA, data classification, residency", "AI-assisted-development safety", "Developer experience & deterministic local setup", "Business continuity & degraded modes"]`; disclosure: `4 of 7 dimensions contributed (4 rule-rated, 0 blended, 0 agent-rated); measured 8 of 32 evaluation areas; ratings average contributors only, ...`; `rest identical: True`, `disclosure delta: True` (only the inserted clause). Report `reports/evidence-report-project-20261006T040937-510984Z.html` (in nest-api): `<div class="area-coverage"><p>This score measured 8 of 32 evaluation areas; 21 have no rule yet, so it says nothing about them.</p><details class="areas-without-rule"><summary>Areas no rule covers yet (21)</summary><ul class="miss-list"><li>Financial integrity &amp; historical reconstruction</li><li>Data model, constraints, migrations</li>` … `<li>Business continuity &amp; degraded modes</li></ul></details></div>`; `measured 8 of 32 evaluation areas` appears twice (panel line + overall disclosure). |
| verify | ☒ pass | Supervisor 2026-10-06: live CLI `score --repo . --scope changes --ref develop...HEAD < /dev/null` on the T082 branch → overall 40, `areas_measured` 8, `areas_without_rule` 21; disclosure: "5 of 7 dimensions contributed (5 rule-rated, 0 blended, 0 agent-rated); measured 8 of 32 evaluation areas; …" — feature confirmed working at the CLI surface — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☒ pass | Supervisor code-review over `develop..feat/T082-uncovered-areas`: judge.py (area helpers, OverallRating field + validator), score.py (payload keys), report.py (`_render_area_coverage`), their callers `rate_overall` / `ScoreResult.to_dict` / `_render_score_panel`, and the 4 updated test files. Dimensions untouched. P0 0 · P1 0 · P2 0 · P3 1 (stale 2026-10-04 nest-api example in AREA_COVERAGE.md, carried as follow-up). Security: report text is static `AREAS` strings passed through `ctx.esc`; no input handling added — pass |
| Full smoke suite still green (no regression) | ☒ pass | Supervisor rerun 2026-10-06: `2021 passed, 2 skipped in 229.00s`; `ruff check src tests` → All checks passed — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☒ N/A | No UI (Spec Constraint 11); the report reuses existing `miss-list` markup in a `<details>` block. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☒ N/A | No UI (Spec Constraint 11). |
| **UI: Responsiveness at target viewports** | ☒ N/A | No UI (Spec Constraint 11). |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured 2026-10-06T04:03:36Z–04:03:53Z on worktree HEAD `eb16069` (no implementation
commit exists), by backend-developer, target nest-api, `--scope project`:

```
$ PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli score \
    --repo <real-repos>/nest-api --scope project < /dev/null > before.json   # exit=0
$ python -c "d=json.load(open('before.json')); o=d['overall']; print(sorted(o)); print(o['disclosure'])"
['abstentions', 'contributor_count', 'contributor_values', 'contributors', 'disclosure', 'kind',
 'method', 'rated_by', 'total_dimension_count', 'value']
disclosure: 4 of 7 dimensions contributed (4 rule-rated, 0 blended, 0 agent-rated); ratings average
contributors only, so abstention can raise the overall; abstained: solution-fit (no_static_rule: ...),
test-strategy (insufficient_measured_weight: ...), blast-radius (all_metrics_abstained: ...)
$ "areas_measured" / "areas_without_rule" / "evaluation areas" anywhere in before.json -> False False False
overall value: 65

$ ... write-report --repo .../nest-api --scope project --findings empty.json < /dev/null
{"path": "reports/evidence-report-project-20261006T040354-734779Z.html", "advisory": null}  # exit=0
$ grep -c "evaluation area\|Areas no rule" <that report>  ->  0
```

The payload has no area count and no uncovered-area list; the disclosure names dimensions only; the
HTML score panel never mentions evaluation areas.

**AFTER**: captured 2026-10-06T04:09:34Z on the implementation working tree, same commands, same
target:

```
$ ... score --repo .../nest-api --scope project < /dev/null > after.json   # exit=0
overall 65 -> 65
areas_measured (8): ["Architecture & dependency direction", "Business-rule correctness",
  "AuthN/Z, sessions, offboarding", "Threat modeling, abuse cases, appsec", "Type safety & code quality",
  "Maintainability, reuse, library judgment, patterns", "Dependencies, vulns, licenses, obsolescence",
  "Documentation source-of-truth governance"]
areas_without_rule (21): ["Financial integrity & historical reconstruction", ..., "Business continuity & degraded modes"]
disclosure: 4 of 7 dimensions contributed (4 rule-rated, 0 blended, 0 agent-rated); measured 8 of 32
  evaluation areas; ratings average contributors only, so abstention can raise the overall; abstained: ...
disclosure-only diff in overall: True     rest identical: True     disclosure delta: True

$ ... write-report ... --findings empty.json < /dev/null
{"path": "reports/evidence-report-project-20261006T040937-510984Z.html", "advisory": null}  # exit=0
<div class="area-coverage"><p>This score measured 8 of 32 evaluation areas; 21 have no rule yet, so it
says nothing about them.</p><details class="areas-without-rule"><summary>Areas no rule covers yet (21)
</summary><ul class="miss-list"><li>Financial integrity &amp; historical reconstruction</li> ... </ul></details></div>
```

**DELTA**: A reader of any score (CLI JSON, MCP payload, HTML report) now sees that nest-api's
65 speaks for 8 of the 32 evaluation areas and can read, by name, the 21 areas no rule covers —
without opening `docs/AREA_COVERAGE.md`.

**WITNESS**: Supervisor, 2026-10-06 — reran the full suite (2021 passed) and a live changes-scope `score` on the branch (8 of 32 measured, 21 without rule). The implementer's trace after 04:09:19Z is mis-attributed to T043 (shared `active_task` file, parallel run) — recorded as a known limitation, not a gap in the evidence above.