# TASK_REVIEW — T033: Registry-driven token metrics: approximate CCN per function, imports, fan-in, cycles

> Sibling of `tasks/TASK_GUIDE_T033.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t033_token_metrics.py` — 54 tests: hand-counted CCN fixtures for all 9 languages (±0), keywords in strings/comments not counted, innermost-function ownership, bracket continuation, 500-char line cap, escapes, import cycles, fan-in blast-radius-only, test files excluded, truncation abstention (whole-set) vs evidence-local `max_function_ccn`. Every guard sabotage-checked. Structural test updates: `test_judge.py` rule table = first 11 metric names; `.tokens` added to metrics import whitelist; untruncated fixture skips the two import metrics. Supervisor re-run `1008 passed, 2 skipped in 25.73s` |
| Verification command run | ☑ pass | Supervisor 2026-09-28: pytest `1008 passed, 2 skipped` (exit 0); `ruff check src tests` → `All checks passed!` (exit 0) |
| Negative cases hold | ☑ pass | Supervisor spot-check via `approximate_ccn`: Python function with `if/and/elif/for` plus `if`/`while for and` inside a comment and a string → CCN 5 (hand count 5); Go function with `if`, `||`, `switch/case` → CCN 4 (hand count 4, switch not counted, case counted — lizard-style) |
| verify | ☑ pass | Real CLI (agent capture in AFTER, scratch repo `score --scope worktree`): architecture pack `max_function_ccn` 5, `top_level_import_cycles` 1 (alpha↔beta); blast-radius `max_fan_in_changed` 2; metric names absent before. Code-quality CCN abstains because its pack holds no code — follow-up T050 created (Supervisor ruling) — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed new `core/tokens.py` (pure; delimiters escaped; 500-char line cap bounds regex cost), `core/metrics.py` (4 new metrics; 77 existing outcomes unchanged; overall 62→62), `core/metric_tables.py`, `core/registry.py` (5 fields; delimiter fields have their own shape check), 9 curated TOML, 3 structural test edits. Code review: P0 0, P1 0. Supervisor rulings: accept indentation-based function end for all languages and anywhere-in-line tokens (guide deviation, documented); code-quality/architecture packs lack code → new task T050 before T035. P2 carried: blast-radius scan cap not reported as truncation so fan-in can be a silent lower bound; Go imports matched by stem undercount fan-in; JS class methods / generic-return Java/C# methods / Ruby blocks not detected as functions; ternary/`??`/Kotlin `when` not counted. Citations are official-doc https links, not fetched. Security inline (Med): all registry values escaped before regex; line cap bounds ReDoS |
| Full smoke suite still green (no regression) | ☑ pass | full suite 1008 passed, 2 skipped |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend task, no UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Pure backend task, no UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | Pure backend task, no UI |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured by backend-developer on the worktree at `2b7ae8c` (no T033 commit yet).
Scratch repo: `src/app/{alpha,beta,gamma}.py` (alpha<->beta import each other, gamma imports beta,
`classify` has if/and/elif/for plus `if while for` inside a string and a comment), `tests/test_alpha.py`,
`pyproject.toml`; alpha.py and beta.py modified in the worktree.

```
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-09-28T05:51:33Z
$ PYTHONPATH=src ../easy-verifier-mcp/.venv/bin/python -m easy_verifier.adapters.cli score --repo $S/repo --scope worktree < /dev/null > $S/before.json
exit=0
$ python names.py before.json        # lists every metric name in the score payload
metric names: ['assertion_density_per_test', 'assertions_observed', 'declared_source_coverage', 'evidence_lines_observed', 'excerpts_observed', 'mean_excerpt_lines', 'redacted_file_share', 'redaction_hits_observed', 'source_file_share', 'source_files_without_covering_test', 'test_to_source_ratio']
approximate_ccn ABSENT
functions_over_ccn_10_share ABSENT
max_function_ccn ABSENT
top_level_import_cycles ABSENT
max_fan_in_changed ABSENT
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-09-28T05:51:42Z
$ PYTHONPATH=src python -c "from easy_verifier.core.tokens import approximate_ccn"
ModuleNotFoundError: No module named 'easy_verifier.core.tokens'
$ PYTHONPATH=src python -c "import easy_verifier.core.metrics as m; print(hasattr(m,'approximate_ccn'))"
False
```

**AFTER**: same scratch repo, same command, on the T033 implementation (backend-developer).

```
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-09-28T06:10:21Z
$ PYTHONPATH=src ../easy-verifier-mcp/.venv/bin/python -m easy_verifier.adapters.cli score --repo $S/repo --scope worktree < /dev/null > $S/after.json
exit=0
functions_over_ccn_10_share present
max_function_ccn present
top_level_import_cycles present
max_fan_in_changed present
architecture functions_over_ccn_10_share 0.0 ['src/app/alpha.py:1-12', 'src/app/beta.py:1-8', 'src/app/gamma.py:1-5']
architecture max_function_ccn 5 ['src/app/alpha.py:1-12']
architecture top_level_import_cycles 1 ['src/app/alpha.py:1-12', 'src/app/beta.py:1-8']
architecture max_fan_in_changed ABSTAIN: only the blast-radius pack says which files changed: ...
blast-radius max_fan_in_changed 2 ['src/app/alpha.py', 'src/app/alpha.py:1-1', 'src/app/beta.py', 'src/app/beta.py:1-1', 'src/app/gamma.py:1-1', 'tests/test_alpha.py:1-1']
code-quality functions_over_ccn_10_share ABSTAIN: no source-file excerpt in this pack contains a function start ...
code-quality max_function_ccn ABSTAIN: no source-file excerpt in this pack contains a function start ...
$ python -c "...approximate_ccn(open('src/app/alpha.py').read(), curated_metric_tables().syntax['.py'])"
(FunctionCcn(line=4, end_line=11, ccn=5),)
existing metrics unchanged: True 77 105        # all 77 pre-T033 (dimension, metric) outcomes byte-equal
overall before/after: 62 62
```

Hand check: `classify` has if, and, elif, for = 4 decision points -> CCN 5; the `if while for` inside
the string and the comment are not counted. alpha<->beta is the one cycle. alpha (imported by beta,
test_alpha) and beta (imported by alpha, gamma) tie at fan-in 2.

Known gap at the real surface: code-quality packs carry no source excerpts, and on this repository's
own project scope the architecture pack carries 0 code excerpts of 7, so the CCN and cycle metrics
abstain there (honestly, with reasons). See the completion report for the proposed dimension change.

**DELTA**: The engine now measures approximate cyclomatic complexity per function, import cycles and fan-in for all 9 curated languages from cited registry data, ready for T035's code-quality, architecture and blast-radius rules.
import cycles and the max fan-in of changed files, each cited to the excerpts it was computed from,
for all 9 curated languages from registry data only.

**WITNESS**: Supervisor re-ran suite, ruff and hand-counted CCN spot-checks (Python 5, Go 4) on 2026-09-28, independent of the implementing agent.