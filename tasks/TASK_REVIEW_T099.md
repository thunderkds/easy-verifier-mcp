# TASK_REVIEW — T099: Redaction keeps extensionless lower-case word paths

> Sibling of `tasks/TASK_GUIDE_T099.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t099_extensionless_word_paths.py` (17 tests; 4 red on develop before the fix). Sabotage check: widening the piece to `[A-Za-z0-9]` makes 3 negatives fail. Supervisor rerun 2026-10-14T03:48Z of T099 plus all redaction suites (T051/T053/T091/T095/T097): `248 passed in 11.14s` |
| Verification command run | ☑ pass | Agent full suite: `2 failed, 2841 passed, 2 skipped in 668.60s`. The 2 failures are the pre-existing container tests (stale Docker image), which fail the same way on develop. `ruff check src tests` → `All checks passed!` (agent + Supervisor) |
| Negative cases hold | ☑ pass | Supervisor probe: Slack webhook → `xQzR…****:751e81a725f9`, `AKIA…****:1a5d44a2dca1`, `bin/aB3x…****:b0b781daa6b1`, a no-slash identifier `buil…****`, mixed case `Bin/…****`. The trigger survives. A low-entropy userinfo password (`hunter2secretpw`) is unmasked identically on develop, so this branch did not cause it |
| verify | ☑ pass | `redact()` driven directly (the redaction surface every adapter shares), plus the agent's `score --scope project` on 6 real repos: hits only went down (node-monorepo 11→9, this repo 7→3, fullstack-ts/nest-api/python-ml unchanged), ratings identical, and k8s-ops tracked paths changed by redact went 1→0 of 597. Each vanished hit was checked by hand and is a path or a branch name. Pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | code-review covered `core/redact.py` (`_entropy_spans` long-token loop only) and the new test. P0 0, P1 0, P2 0, P3 0. ReDoS: the pieces are bounded and a joiner is required between them, so the pattern is linear. Security review done by hand (Medium risk; the built-in skill needs an `origin` remote): named detectors, the per-segment rule and the hex rule are untouched, and the residue is documented in the docstring. Pass |
| Full smoke suite still green (no regression) | ☑ pass | No new failures beyond the 2 pre-existing container tests |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend task, no UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Pure backend task, no UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | Pure backend task, no UI |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured 2026-10-14T03:34:04Z on develop `2452bcf`, before any implementation commit; run by backend-developer):

```
$ PYTHONPATH=src .venv/bin/python -c "from easy_verifier.core.redact import redact; print(redact('bin/build-push-kibana-docker-image'))"
bin/…****:e169e83f548e
$ git -C k8s-ops ls-files | count paths where redact(p) != p
tracked 597 changed 1
  bin/build-push-kibana-docker-image -> bin/…****:e169e83f548e
```

**AFTER** (2026-10-14T03:37:09Z, worktree `fix/T099-extensionless-paths`):

```
bin/build-push-kibana-docker-image
tracked 597 changed 0
```

**DELTA**: a citation to `bin/build-push-kibana-docker-image` (and any extensionless lower-case word path) now resolves; k8s-ops goes from 1 tracked path changed by `redact()` to 0.

**WITNESS**: Supervisor (not the implementing agent), 2026-10-14T03:48Z: test rerun and `redact()` probe as above; the trace is in `memory/event-trace/T099.jsonl`.