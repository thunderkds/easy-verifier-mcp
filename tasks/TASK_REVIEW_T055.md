# TASK_REVIEW — T055: Area rule groups needing git evidence (#5, #27)

> Sibling of `tasks/TASK_GUIDE_T055.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t055_git_evidence_areas.py` (52 tests). AC1: removed public function counted at `src/shop/api.py:5-5`, dropped column counted, rename vs remove, new vs edited migration. AC2: project/worktree scope, unresolved changes scope, clipped diff and budget-dropped quotes all abstain with a reason. AC3: 2 competing docs give 2, code commits never touching docs give 0.0, no git / shallow clone abstain, merges skipped, templates excluded (user). AC4: git only through `run_git_text`, pre-T055 snapshot byte-identical, key-list pin. AC5: `test_signed_off_weights_thresholds_and_areas`. DDR-0002: `test_secret_bearing_files_in_the_diff_are_excluded_not_parsed` + control twin. Implementer red-first; 13 predicates sabotage-checked. Changed pins with reasons: T035 APPROVED table and AC-trace abstain test; README rating table; T037 field-count comment corrected (14) + new pin; T007/T014 serialize via `to_json_dict` (snapshot file unchanged); test_metrics lists the 4 new metrics |
| Verification command run | ☑ pass | Supervisor 2026-09-29 at `98eacc6`+wiring (`0b57853`): `1505 passed, 2 skipped` (exit 0), ruff exit 0. Implementer after the DDR-0002 fix `f0a16f6`: `1506 passed, 2 skipped` (exit 0), ruff exit 0 |
| Negative cases hold | ☑ pass | No diff (project/worktree scope) abstains with the scope named, never 0. A clipped diff and budget-dropped quotes abstain. No git or a shallow clone abstains for #27. Secret-bearing files in the diff are named only, never parsed or quoted. Template files are not requirements sources. `COVERAGE_FLOORS` and budgets are unchanged |
| verify | ☑ pass | Supervisor, real CLI, 2026-09-29T11:06Z, fixture repo with 2 commits. `score --scope changes --ref HEAD~1..HEAD`: public_symbols_removed 1 unmet ("src/shop/api.py:5-5 cancel_order removed"); destructive_migration_ops 1 unmet ("migrations/0002_drop.sql:1-1 DROP COLUMN in a new migration file"); both area "Backward compatibility & upgrade safety"; ".env" named as secret-bearing and excluded; the fake secret value is absent from the output. `score --scope project`: #5 abstains ("project scope, which carries no diff"); requirements_docs_count 2 (PRD.md, REQUIREMENT.md); code_commits_with_docs_share 0.5 (1 of 2) — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed the `e0a6d83..HEAD` src diff: models (additive `compat`/`doc_history` + `to_json_dict`, both adapters switched, so parity is kept), pipeline/context plumbing, blast_radius/requirement_fidelity collectors, metrics, registry field, judge wiring. P0/P1: none. P2 (DDR-0002): the #5 diff parser read secret-bearing files; fixed in `f0a16f6`. Manual security review: git only through the hardened runner, excerpts redacted at the evidence layer, `DiffItem.detail` redacted, paths redacted. Supervisor verified the reference-gate count with `required_fields()`: 10 → 13 (T040) → 14 (T055). ISO 26514 URL confirmed by search index only (iso.org 403). Migration knowledge in the engine accepted (user), follow-up T057 |
| Full smoke suite still green (no regression) | ☑ pass | 1506 passed, 2 skipped, exit 0 |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend task, no UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Pure backend task, no UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | Pure backend task, no UI |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured 2026-09-29T10:15:58Z by backend-developer at worktree HEAD `e0a6d83` (no T055
implementation commit exists). Fixture: a fresh git repo (5 commits) built by a scratch script —
`init` (src/shop/api.py with public `list_items`, `get_item` and private `_helper`;
`migrations/0001_init.sql`; README.md, PRD.md, docs/requirements.md, SPEC.md, ROADMAP.md,
pyproject.toml), three "code change" commits touching only `src/shop/api.py` (never docs), then
`HEAD` = "remove get_item; drop price column" (deletes `def get_item`, adds
`migrations/0002_drop_price.sql` = `ALTER TABLE items DROP COLUMN price;`).

```
$ PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli score --repo <fixture> --scope changes --ref HEAD </dev/null > before.json
exit=0
$ python show.py before.json   # ratings of the two dimensions T055 touches
blast-radius: kind=rating_abstention value=None reason=all_metrics_abstained
  unavailable max_fan_in_changed: no import statement was found in this pack's code-file excerpts, so there is no import graph to measure; ...
  unavailable changed_files_in_churn_hotspots_share: examined: only 5 local commit(s), fewer than the 20 a churn ranking needs, so no file is called a hotspot
requirement-fidelity: kind=rating value=0 reason=None
  input acceptance_criteria_traced_to_code_share = 0.0 (at_least 0.8, passed=False) area='Business-rule correctness'
  input acceptance_criteria_traced_to_test_share = 0.0 (at_least 0.8, passed=False) area='Business-rule correctness'
$ grep -c 'Documentation source-of-truth governance\|public_symbols_removed' before.json
0
```

No #5 rule sees the removed public function or the dropped column (blast-radius has only the fan-in
and churn rules, both abstaining), and no rule or metric carries the #27 area
`Documentation source-of-truth governance` — the two competing requirements docs (PRD.md,
docs/requirements.md) and the three code-only commits are invisible to the rating.

**AFTER**: captured 2026-09-29T10:59:09Z by backend-developer at worktree HEAD `9e95cf8`, on a
fresh fixture built by the same scratch script as BEFORE, using the same command.

```
$ PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli score --repo <fixture> --scope changes --ref HEAD </dev/null > after.json
exit=0
$ python show.py after.json
blast-radius: kind=rating value=0 reason=None
  input public_symbols_removed = 1 (at_most 0, passed=False) area='Backward compatibility & upgrade safety'
  input destructive_migration_ops = 1 (at_most 0, passed=False) area='Backward compatibility & upgrade safety'
  unavailable max_fan_in_changed: no import statement was found in this pack's code-file excerpts, ...
  unavailable changed_files_in_churn_hotspots_share: examined: only 5 local commit(s), fewer than the 20 a churn ranking needs, so no file is called a hotspot
requirement-fidelity: kind=rating value=0 reason=None
  input acceptance_criteria_traced_to_code_share = 0.0 (at_least 0.8, passed=False) area='Business-rule correctness'
  input acceptance_criteria_traced_to_test_share = 0.0 (at_least 0.8, passed=False) area='Business-rule correctness'
  input requirements_docs_count = 2 (at_most 1, passed=False) area='Documentation source-of-truth governance'
  input code_commits_with_docs_share = 0.2 (at_least 0.3, passed=False) area='Documentation source-of-truth governance'
$ grep -c 'Documentation source-of-truth governance\|public_symbols_removed' after.json
10
metric citations / derivations (blast-radius and requirement-fidelity packs):
public_symbols_removed ['src/shop/api.py:5-5'] | 1 removed or renamed public declaration(s) in the diff of 2 changed file(s): src/shop/api.py:5-5 get_item removed. ...
destructive_migration_ops ['migrations/0002_drop_price.sql:1-1'] | 1 destructive migration operation(s) in the diff of 2 changed file(s): migrations/0002_drop_price.sql:1-1 DROP COLUMN in a new migration file. ...
requirements_docs_count ['PRD.md', 'docs/requirements.md'] | 2 file(s) fill the requirements-doc role ...
code_commits_with_docs_share ['PRD.md', 'README.md', 'ROADMAP.md', 'SPEC.md', 'docs/requirements.md'] | 1 of 5 code-changing commit(s) also changed documentation, among the last 5 non-merge local commit(s) read (window 200); ...
```

**DELTA**: a `score` of a change now rates the removed public function and the dropped column
against SemVer-cited #5 rules, each cited at its diff line. It also rates the two competing
requirements docs and the code-only commits against 26514-cited #27 rules. Before this change
blast-radius abstained and neither area existed.

**WITNESS**: Supervisor, 2026-09-29T11:06:54Z, independent real-CLI runs at the changes and project scopes on a fresh fixture (above), recorded in `memory/event-trace/T055.jsonl`.