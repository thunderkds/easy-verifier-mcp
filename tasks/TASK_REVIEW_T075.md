# TASK_REVIEW — T075: requirement-fidelity code rules

> Sibling of `tasks/TASK_GUIDE_T075.md`. Everything here is **filled by the reviewer at Stage
> 4/5** — it is deliberately NOT in the guide, because the implementing agent re-reads the guide on
> every turn and never fills these two sections.
>
> Consumers resolve each section **guide first, this file second** (`.claude/hooks/lib/guide_sections.py`):
> a legacy guide that still carries these sections inline keeps working unchanged, and a stray
> review file can never override an inline section.

---

## Design (implementer, C3 — written before implementation code)

**Where the work happens.** The three new metrics are computed by the requirement-fidelity
dimension in `collect`, before its first yield and once per context (the budget calls `collect`
per tier pass), over the **whole text** of the files it reads (AC 11), and recorded as
`SampledMetric` records on `context.whole_file` — the T076 path `compute_metrics` already
prefers over the budgeted excerpts. The metric definitions in `core/metrics.py` abstain in every
other pack ("only the requirement-fidelity pack ..."). No new model type, no new pack field.

**Inputs read (whole files, through `read_source`, so secret-bearing files stay refused).**
- Source files: `_code_extract.source_candidates(context, "route evidence")` — all at or under the
  cap (200), else priority batches 1..N; when batched every route-derived derivation carries the
  `sample: batches N of M` note (edge case "labelled sample").
- Test files: in-scope files `code_kind == "test"`, sorted, at most `MAX_TEST_FILES` (2000); more
  is stated in the derivation (lower bound).
- Requirement documents: the files filling `requirements-doc` and `spec-doc` (rules + config).

**`routes_without_test_share` (40, at most 0.20).** Routes = `structure.find_routes` per source
file with the language's `route_tokens` (+ conventions). A route is **tested** when some test
file contains (a) its path literal's static prefix — the segments before the first parameter
(`:id`, `{id}`, `<id>`, `*`), e.g. `/users/:id` -> `users`, matched after a `/` or quote and not
followed by `[\w-]` — or else (b) its handler name as a whole word (fallback for helper-built
paths such as nest-api's `api-path.util.ts`). Value = untested / routes; derivation gives
route count, tested count, matched-by counts (path / handler) and up to 5 untested examples
(`file:line METHOD path handler`). Abstains when no route is found (states the source files read
and tokens used). Cites route files + matching test files.

**`commits_with_issue_reference_share` (20, at least 0.50).** Same window as #27: the last
`CO_CHANGE_WINDOW` (200) non-merge local commits, message bodies (`%B`). A commit counts when
`structure.find_issue_references` finds at least one reference minus the declared exclusion list
(AC 9). Abstains below `MIN_ISSUE_COMMITS` = 20 commits (squash-merged / young history) and on a
non-git or shallow repository, stating what bounded it. Cites the files changed by the window's
commits that this pack read (first 20), else abstains for lack of a citable file.

**`requirement_items_traced_share` (20, at least 0.80, project default).** Items =
`structure.find_requirement_items` over every requirement document read (any form the patterns
declare: ids such as `FR-012`/`AC-3`, Gherkin `Scenario:` lines, task-list lines, OpenAPI
`operationId:`). An `id` item is traced when it appears as a whole word in a source or test file;
a `line` item when its text appears (case-insensitive, whitespace collapsed) in one. Abstains when
no item is found. Cites the documents + tracing files.

**Rules / floor.** `RATING_RULES['requirement-fidelity']` = requirements_docs_count 10,
code_commits_with_docs_share 10, routes_without_test_share 40, commits_with_issue_reference_share
20, requirement_items_traced_share 20 (DDR-0011); the two AC-trace rules leave the table (their
metrics stay as unrated evidence). `ROLES` drops `task-breakdown` and gains three pseudo-sources —
`route handlers`, `test files`, `git history` — filled when found, so a repo with routes, tests and
history but no documents reaches 3/5 = 0.6 >= the 0.50 floor. Role patterns gain
`**/docs/requirements*/**`, OpenAPI/Swagger files (spec-doc); `specs/**/plan.md` is already covered.

**Documents missing (AC 7).** `code_commits_with_docs_share` no longer abstains when no document
was read: with history it reports the real share (0 when nothing co-changed), citing code files
read. `requirements_docs_count` keeps `at_most 1` (see report: zero documents vs "fail").

**AC 9 / 10** follow in later commits: a declared `issue_reference_exclusions` convention list
(UTF-8, SHA-256, ISO-8601, hex colours); single-argument call routes skipped; Ruby bare tokens only
in declared routes files; conventions (local layer + `.easy-verifier.toml`) embedded for replay.

## Evidence

| Check | Result | Notes / output snippet |
|-------|--------|------------------------|
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t075_requirement_fidelity_code_rules.py` (25 tests; nested-repo test replaced in T077 because it was a false pass) + `tests/test_t077_rf_review_fixes.py` (9) — pass |
| Verification command run | ☑ pass | Full suite (T077 agent, final HEAD 87faac6) 1990 passed, 2 skipped, 2 failed (known stale-Docker container tests); ruff clean — pass |
| Negative cases hold | ☑ pass | no routes → route rule abstains; < 20 commits / shallow / not git → issue-ref rule abstains; no items → items rule abstains; UTF-8/SHA-256/hex colours not issue refs; one-arg app.get(setting) not a route; Ruby routes only in routes files — pass |
| verify | ☑ pass | Supervisor real-repo runs after T077 fixes (see AFTER): nest-api 50, fullstack-ts 15→60, node-monorepo honest below-floor abstention (pattern gap → T079) — feature confirmed working — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Stage 4 found nest-api scored 0 for wrong reasons (multi-line decorators, plan checklists counted as requirements, nested-repo git path prefix) and AC 7 conflict on requirements_docs_count → fixed in T077 (Supervisor decisions A/B, DDR-0011 addendum). AC 10 conventions replay split to T078 — pass |
| Full smoke suite still green (no regression) | ☑ pass | 1990 passed; only the 2 pre-existing container failures — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | no UI change |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | no UI change |
| **UI: Responsiveness at target viewports** | ☐ N/A | no UI change |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (Supervisor, before any T073–T075 code, branch plan/code-derived-rules; real repos, `score --scope project`):

```
Sun Oct  4 10:03:33 AM UTC 2026
0a02f85 plan: code-derived rules — brainstorm + grilling, DDR-0011, FR-067..071, US-021, glossary
nest-api overall 65 | architecture below_coverage_floor | requirement-fidelity below_coverage_floor | all {'architecture': 'below_coverage_floor', 'blast-radius': 'all_metrics_abstained', 'code-quality': 71, 'requirement-fidelity': 'below_coverage_floor', 'security': 59, 'solution-fit': 'no_static_rule', 'test-strategy': 'insufficient_measured_weight'}
node-monorepo overall 66 | architecture 70 | requirement-fidelity below_coverage_floor | all {'architecture': 70, 'blast-radius': 'all_metrics_abstained', 'code-quality': 67, 'requirement-fidelity': 'below_coverage_floor', 'security': 50, 'solution-fit': 'no_static_rule', 'test-strategy': 75}
fullstack-ts overall 58 | architecture 100 | requirement-fidelity 15 | all {'architecture': 100, 'blast-radius': 'all_metrics_abstained', 'code-quality': 'insufficient_measured_weight', 'requirement-fidelity': 15, 'security': 59, 'solution-fit': 'no_static_rule', 'test-strategy': 'insufficient_measured_weight'}
```

**AFTER** (Supervisor, 2026-10-04 11:46 UTC, branch `87faac6`, CLI score --scope project):

```
nest-api overall 65; requirement-fidelity below_coverage_floor -> 50 (requirements_doc_missing FAIL, code_commits_with_docs_share 0.21 FAIL, routes_without_test_share 0.0 pass 17/17, commits_with_issue_reference_share 0.0 FAIL, requirement_items_traced_share abstained: no items in 13 docs)
node-monorepo overall 69; requirement-fidelity below_coverage_floor (0.4 < 0.5): routes written `webapp.get('/api/...')` not matched by curated tokens -> follow-up T079
fullstack-ts overall 72; requirement-fidelity 15 -> 60 (doc present pass, docs co-change 0.56 pass, routes untested 0.11 pass, issue refs 0.03 FAIL, items traced 0.24 FAIL)
```

**DELTA**: requirement-fidelity is rated from routes↔tests, commit issue references and any-form requirement items plus documents; nest-api and fullstack-ts get honest numbers.

**WITNESS**: Supervisor, 2026-10-04 11:46 UTC — three real-repo score runs.
