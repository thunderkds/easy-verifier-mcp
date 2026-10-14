# TASK_REVIEW — T073: Structure convention patterns

> Sibling of `tasks/TASK_GUIDE_T073.md`. Everything here is **filled by the reviewer at Stage
> 4/5** — it is deliberately NOT in the guide, because the implementing agent re-reads the guide on
> every turn and never fills these two sections.
>
> Consumers resolve each section **guide first, this file second** (`.claude/hooks/lib/guide_sections.py`):
> a legacy guide that still carries these sections inline keeps working unchanged, and a stray
> review file can never override an inline section.

---

## Design

Written by the implementer (backend-developer) before any T073 code. No conflict found between
DDR-0011 and the DDR-0007 registry model: every new convention is a cited-value field in the same
TOML schema, loaded and validated by the same code, extended add-only by the same local layer.

**Where the patterns live.**
- Language-specific `route_tokens` → a new `ENTRY_FIELDS` field in each language's curated file
  (`registry/curated/<lang>.toml`), so a framework entry or the local layer adds to it exactly like
  `import_syntax`. Listed in `FIELD_METRICS` with no metric yet (`()`), so `required_fields()` does
  not ask for it until T075 maps it to a rule (parity unchanged).
- Language-agnostic `layer_paths`, `requirement_item_patterns`, `issue_reference_patterns` (and an
  optional repo-wide `route_tokens`) → one reserved entry, `conventions.toml`, in the curated
  directory (shipped) and optionally in the local layer directory (`$EASY_VERIFIER_SOT`).
  `load_registry` skips the reserved name; `load_conventions()` loads it with the same
  `_cited_values` validation (curated tag in the package, `LOCAL_TAGS` + local shape bounds in the
  local layer). Curated wins value by value, as in `overlay`.

**Field shapes** (each value one string; a `kind=` prefix keeps `CitedValue` unchanged, like
`frameworks`' `<framework>=<dependency>`):
- `layer_paths`: `"<api|service|data>=<repo glob>"`, e.g. `"api=**/*.controller.*"`; globs match with
  the bounded `roles._config_matcher`. A file matching two layers is unclassified (never guess); a
  test file is never classified.
- `route_tokens`: `"<GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS|ANY>=<code token>"`, e.g. `"GET=@Get("`.
  Token syntax is the registry's existing one (`metric_tables.token_regex`), so no value can inject
  regex. A token starting with `@`, `[` or `#[` is a decorator (handler = next declaration);
  otherwise a call (handler = last identifier argument).
- `requirement_item_patterns`: `"id=<token>"` (an identifier anywhere, e.g. `"id=AC-<0-9>*"`) or
  `"line=<token>"` (at line start; the item is the rest of the line, e.g. `"line=Scenario:"`).
- `issue_reference_patterns`: `"<token>"`, e.g. `"#<0-9>*"`, `"<A-Z><A-Z><A-Z0-9>*-<0-9>*"`.

**Extension path.** (1) local layer: `$EASY_VERIFIER_SOT/conventions.toml` (shared fields) or
`<lang>.toml` (`route_tokens`), tagged `LOCAL_TAGS`; (2) `.easy-verifier.toml` `[conventions]
<field> = ["value", …]`, validated in `load_repo_config` alongside `[roles]` and tagged
`user-supplied` with the config file as its source. Both are add-only.

**Pure functions** (`core/structure.py`, no file reads; callers pass text and patterns):
`layer_of`, `find_routes` (on comment/string-blanked code), `find_requirement_items` and
`find_issue_references` (on raw prose). No rule, weight, floor, payload or report change.

---

## Evidence

| Check | Result | Notes / output snippet |
|-------|--------|------------------------|
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t073_structure_patterns.py` (38 tests: layer_of incl. tests/ambiguity unclassified; find_routes NestJS/Express/Flask/Spring/ASP.NET/Go…, comment/string blanking, multi-line decorators; requirement items id/line forms; issue references; extension via local conventions.toml and .easy-verifier.toml [conventions]; registry validation). Agent sabotage of each guard turned tests red — pass |
| Verification command run | ☑ pass | Supervisor 2026-10-04: full suite 1913 passed, 2 skipped, 2 failed (known stale-Docker container tests); ruff All checks passed — pass |
| Negative cases hold | ☑ pass | nest-api score payload (ratings, overall, improvement_plan) identical to BEFORE — no score change, as scoped — pass |
| verify | ☑ pass | Supervisor drove CLI score on nest-api (unchanged) and ran layer_of over its 106 src .ts files: api 4, service 6, data 12, unclassified 84 (23 are tests). Finding carried to T074: NestJS dto/schema/guard/middleware/filter/interceptor/decorator/migrations unclassified; cross-cutting module/config/util/constant/enum/types need an excluded class — pass (scope of T073 met) |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed core/structure.py, conventions.toml, route_tokens in 9 language files, registry/roles/metric_tables loaders, test_t030 change. code-review: P0–P1 none. P2 → carried to T074/T075: (a) layer coverage on NestJS (above); (b) false positives: Jira-key pattern matches UTF-8/SHA-256, `#<digit>` hex colours, Express `app.get(setting)`, Spring class-level @RequestMapping; (c) Ruby bare route tokens → restrict to routes files; (d) local/config conventions not yet embedded for replay (FR-048) before T075 scores with them. Accepted: `.easy-verifier.toml` citation for config entries (tag user-supplied); citations written from knowledge, spot-check at T075 — pass |
| Full smoke suite still green (no regression) | ☑ pass | 1913 passed; only the 2 pre-existing container failures — pass |
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

**AFTER**: same scores (no rule change by design); new `core/structure.py` finders + `registry/curated/conventions.toml` + `route_tokens` in 9 languages. nest-api: `layer_of` classifies 22 of 83 non-test sources (api 4, service 6, data 12).

**DELTA**: the engine can now classify layers and find routes, requirement items and issue references from cited, repo-extendable patterns — the inputs T074/T075 score.

**WITNESS**: Supervisor, 2026-10-04 — full-suite re-run, unchanged-score check and real-repo layer sanity run.
