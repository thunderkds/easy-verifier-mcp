# TASK_REVIEW — T074: architecture code rules

> Sibling of `tasks/TASK_GUIDE_T074.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t074_architecture_code_rules.py` (37 tests: weights 10/10/40/40 + citations; layer violations counted with file:line examples; unclassified/shared never count; abstain < 50% classified; README 'Architecture' section passes rule and fills role; missing docs fail; repository importing a DTO is not a violation; code-aware floor). Changed tests cite DDR-0011 — pass |
| Verification command run | ☑ pass | Agent full suite 1951 passed, 2 skipped, 2 failed (known stale-Docker container tests); ruff clean — pass |
| Negative cases hold | ☑ pass | review round fixed a guide error (AC9 put dto/schema in api → 17 false violations on idiomatic NestJS); dto/schema/exception/provider now shared; test pins it — pass |
| verify | ☑ pass | Supervisor 2026-10-04 10:43 UTC, CLI score on 3 real repos: coffee-shop-api overall 65→70, architecture below_coverage_floor→80 (docs fail, cycles 0, layer violations 0, 35/35 non-shared classified); bryony 66→69, architecture 70→83 (layer rule abstains: 88/195 classify); kitchd 58→37, architecture 100→insufficient_measured_weight — diagnosed: kitchd's former 100 was docs-only (import cycles already abstained on byte-budget truncation before T074); now docs weigh 20 so the honest result is no number. Root cause = T068 follow-up #2 (under-cap repos use budgeted excerpts) → new task T076 before T075 — feature confirmed working — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed judge architecture rules, metrics layer metric (pure via LanguageTables.layer_of), architecture dimension roles/floor, conventions.toml shared class, docs. code-review: P0/P1 none after review round; P2 → T075: local/config layer paths not yet used in scoring until replay embedding; P2 → T076: under-cap truncation — pass |
| Full smoke suite still green (no regression) | ☑ pass | 1951 passed; only the 2 pre-existing container failures — pass |
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
coffee-shop-api overall 65 | architecture below_coverage_floor | requirement-fidelity below_coverage_floor | all {'architecture': 'below_coverage_floor', 'blast-radius': 'all_metrics_abstained', 'code-quality': 71, 'requirement-fidelity': 'below_coverage_floor', 'security': 59, 'solution-fit': 'no_static_rule', 'test-strategy': 'insufficient_measured_weight'}
bryony overall 66 | architecture 70 | requirement-fidelity below_coverage_floor | all {'architecture': 70, 'blast-radius': 'all_metrics_abstained', 'code-quality': 67, 'requirement-fidelity': 'below_coverage_floor', 'security': 50, 'solution-fit': 'no_static_rule', 'test-strategy': 75}
kitchd overall 58 | architecture 100 | requirement-fidelity 15 | all {'architecture': 100, 'blast-radius': 'all_metrics_abstained', 'code-quality': 'insufficient_measured_weight', 'requirement-fidelity': 15, 'security': 59, 'solution-fit': 'no_static_rule', 'test-strategy': 'insufficient_measured_weight'}
```

**AFTER** (Supervisor, 2026-10-04 10:43 UTC, `d1565a3`): coffee-shop-api architecture 80 (overall 70); bryony 83 (69); kitchd insufficient_measured_weight (37) — kitchd explained above.

**DELTA**: architecture is rated from code structure (cycles + layer direction) with documents worth 20; coffee-shop-api gets an architecture number for the first time.

**WITNESS**: Supervisor, 2026-10-04 — three real-repo score runs and kitchd diagnosis (same truncated pack before/after; former 100 was docs-only).
