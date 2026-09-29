# TASK_REVIEW — T039: Documentation-present rule, N-dim overall, area labels

> Sibling of `tasks/TASK_GUIDE_T039.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☐ pass / ☐ fail | Implementer-supplied (reviewer to confirm): `tests/test_t039_doc_rule_areas.py` — 23 tests, AC1 (areas, labels on inputs, unknown/forged area rejected), AC2 (runbook present cites `docs/runbook.md`, no number anywhere in payload; missing + bounded reason; zero weight; doc-only dimension abstains `documentation_only`; failed dimension carries no doc result; score_packs feeds `files_read`), AC3 (8 declared dims: overall 75, `4 of 8 dimensions contributed`; missing dim rejected; all-abstain reason not "seven"), AC4 (payload keys = pre-T039 + `area` only), report grouping. At `cbc7945`: `23 passed in 0.80s`. Sabotage: 7 predicates hardwired (doc always present / always missing / area not compared / doc-only→no_static_rule / doc validation off / report no grouping / score ignores files_read) — each fails ≥1 test. |
| Verification command run | ☐ pass / ☐ fail | Implementer run 2026-09-29T04:00:11Z at `cbc7945` (worktree, main-checkout interpreter, `PYTHONPATH=src`): `python -m pytest -q` → `1365 passed, 2 skipped in 75.13s`, exit 0; `python -m ruff check src tests` → `All checks passed!`, exit 0. AC4 at the real CLI: `score --scope worktree` on a small fixture repo with pre-change source (`git archive 6e0e723 src`) vs HEAD → `identical after removing area keys: True`, overall 50 → 50, 4 area labels emitted. |
| Negative cases hold | ☐ pass / ☐ fail | |
| verify | ☐ pass / ☐ fail / ☐ N/A | [what was observed — must literally state "pass" or "fail" here too, e.g. "skill run, feature confirmed working — pass": the merge gate scans this Notes column for the word "pass", not just the Result column] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [what was reviewed vs. skipped, and why] |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail | |
| **UI: Visual regression (diff or verdict pasted)** | ☐ pass / ☐ fail / ☐ N/A | [screenshot path or LLM verdict — required for UI tasks, Hard-Stop Gate 6] |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ pass / ☐ fail / ☐ N/A | [method used + output] |
| **UI: Responsiveness at target viewports** | ☐ pass / ☐ fail / ☐ N/A | [viewports tested, any overflow findings] |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured 2026-09-29T03:28:57Z at `6e0e723` (branch `feat/T039-doc-rule-areas`, before any
implementation commit) by backend-developer. Command (worktree root; the demo script is reproduced
verbatim at the end of this section so AFTER re-runs the same thing):

```
$ date -u +%Y-%m-%dT%H:%M:%SZ && git rev-parse --short HEAD && PYTHONPATH=src <main>/.venv/bin/python - < demo_T039.py
2026-09-29T03:28:57Z
6e0e723
documentation_present exists: False
architecture rule area: <no area field>
rating input keys: ['comparison', 'computed_from', 'earned_weight', 'metric_citation', 'metric_name', 'metric_value', 'passed', 'registry_citations', 'source_tag', 'threshold', 'threshold_citation', 'weight']
overall value: 75 | total: 8
disclosure: 4 of 8 dimensions contributed (4 rule-rated, 0 blended, 0 agent-rated); ratings average contributors only, so abstention can raise the overall; abstained: d5 (no_static_rule: ...), d6 (...), d7 (...), d8 (...)
all-abstain reason: none of the seven dimensions produced a rating
exit=0
```

Observed: no `documentation_present`, no `area` on rules or rating inputs. `rate_overall` already
averages over whatever `COVERAGE_FLOORS` declares (8 here), but the all-abstain reason still claims
"none of the **seven** dimensions" when eight were declared.

Demo script (`demo_T039.py`, run from stdin):

```python
import easy_verifier.core.judge as j
print("documentation_present exists:", hasattr(j, "documentation_present"))
rule = next(iter(j.RATING_RULES["architecture"].values()))
print("architecture rule area:", getattr(rule, "area", "<no area field>"))
print("rating input keys:", sorted(j.RatingInput.__dataclass_fields__))
c = j.Citation("x", "https://example.org/x")
area = {"area": j.AREAS[0]} if hasattr(j, "AREAS") else {}
j.COVERAGE_FLOORS.clear(); j.RATING_RULES.clear()
for i in range(1, 9):
    j.COVERAGE_FLOORS[f"d{i}"] = j.CoverageFloor(0.5, "inclusive")
    j.RATING_RULES[f"d{i}"] = {f"m{i}": j.RatingRule(f"m{i}", 100, 0, "at_most", (c,), c, **area)} if i <= 4 else {}
def rated(i, v):
    return j.Rating(f"d{i}", 100 if v == 0 else 0, (j.RatingInput(f"m{i}", v, 100, 0, "at_most", v == 0, 100 if v == 0 else 0, ("a.py",), (c,), c, "curated", **area),))
ratings = [rated(1, 0), rated(2, 0), rated(3, 0), rated(4, 5)] + [j.RatingAbstention(f"d{i}", "no_static_rule", coverage_floor=0.5) for i in range(5, 9)]
o = j.rate_overall(ratings)
print("overall value:", o.value, "| total:", o.total_dimension_count)
print("disclosure:", o.disclosure)
none = j.rate_overall([j.RatingAbstention(f"d{i}", "no_static_rule", coverage_floor=0.5) for i in range(5, 9)] + [j.RatingAbstention(f"d{i}", "coverage_not_applicable", coverage_floor=0.5) for i in range(1, 5)])
print("all-abstain reason:", none.reason)
```

**AFTER**: same script, same worktree, at `cbc7945`:

```
2026-09-29T03:48:36Z
cbc7945
documentation_present exists: False
architecture rule area: Architecture & dependency direction
rating input keys: ['area', 'comparison', 'computed_from', 'earned_weight', 'metric_citation', 'metric_name', 'metric_value', 'passed', 'registry_citations', 'source_tag', 'threshold', 'threshold_citation', 'weight']
overall value: 75 | total: 8
disclosure: 4 of 8 dimensions contributed (4 rule-rated, 0 blended, 0 agent-rated); ratings average contributors only, so abstention can raise the overall; abstained: d5 (...), d6 (...), d7 (...), d8 (...)
all-abstain reason: none of the declared dimensions produced a rating
exit=0
```

The first line still reads `False` because the script probes `judge`, and the entry point lives in
`easy_verifier.core.roles` (moved there because `test_judge_is_structurally_arithmetic_only` pins
judge's import set; glob matching belongs with roles). Supplemental probe of the real entry point:

```
$ date -u +%Y-%m-%dT%H:%M:%SZ && PYTHONPATH=src <main>/.venv/bin/python -   # documentation_present(rule for AREAS[24], files)
2026-09-29T03:48:44Z
{"kind": "documentation", "area": "Incident response, change mgmt, access review", "status": "present", "file": "docs/runbook.md", "citation": [{"label": "NIST SP 800-61", "url": "https://csrc.nist.gov/pubs/sp/800/61/r2/final"}], "reason": "matched a file read"}
{"kind": "documentation", "area": "Incident response, change mgmt, access review", "status": "missing", "file": null, "citation": [{"label": "NIST SP 800-61", "url": "https://csrc.nist.gov/pubs/sp/800/61/r2/final"}], "reason": "no file matching **/runbook*.md was among the files this dimension read"}
exit=0
```

**DELTA**: every rule result now carries one of the user's 32 area labels (and the report groups by
them), a dimension can declare documentation rules that report present-with-file or missing and
never a number, and the overall's all-abstain reason is correct for any declared dimension count.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T039.jsonl`, never the
implementing agent alone]
