# TASK_REVIEW — T106: Kev backend alongside Laya (experiment)

> Sibling of `tasks/TASK_GUIDE_T106.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t104_experiment_harness.py`: 7 new kev tests on a stdlib stub `/v1/systemone` server (request shape + private repo accepted, `KEV_MODEL`/`KEV_API_KEY` header, confidence fallbacks, server latency pickup, foreign choice counted invalid, non-ASCII path, unreachable URL exit 2, 503 mid-run exit 2 naming the id); implementer confirmed 7 failed before the backend existed. Supervisor re-run: `36 passed in 4.72s` (harness + T100 guard) — pass |
| Verification command run | ☑ pass | `ruff check src tests experiments` → `All checks passed!`; `git diff develop...HEAD -- src pyproject.toml run.py evaluate.py` → empty — pass |
| Negative cases hold | ☑ pass | Supervisor live, 2026-10-16 05:22 UTC, no server running: `run.py --model kev` → `kev server: http://127.0.0.1:8009 (model kev-0.8b)` / `error: kev server unreachable at http://127.0.0.1:8009: <urlopen error [Errno 111] Connection refused>` exit=2, no answer file written — pass |
| verify | ☑ pass | Real `kev.serve` (Kev-0.8B, CPU fp32, 127.0.0.1:8009) answered all 56 questions (implementer run, 91 s); Supervisor re-scored `.local/t106/answers/kev08.jsonl` independently: `overall 56 / 0 missing / 0 invalid / top-1 0.625 / ECE 0.236 / p50 1651.9 ms / p95 2691.8 ms / cov@0.8 0.107` — matches the report. Kev-4B bf16 sample 14 questions: top-1 0.571, p50 24.3 s. Remote-host mode documented, not exercised — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed the 6-file diff: new `kev_backend.py`, REGISTRY line, `jev_backend.py` refactor (body extracted verbatim into `choice_body()`, jev tests untouched and green), README, tests. code-review: P0/P1/P2 none; P3: the start-up probe sends the bearer header on a GET to the base URL (harmless, our server). Security (Medium): no allow-list by design (user: own server); stderr names the target URL so a remote host is never implicit; no content left the machine in this run — pass |
| Full smoke suite still green (no regression) | ☑ pass | Implementer: `2940 passed, 3 skipped` (667 s, exit 0) on a clean rerun; an earlier run had 44 teardown errors in `test_t013_report.py` caused by the concurrent Kev clone writing under `.local/` during the suite (file passes alone, 44 passed) — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | No UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | No UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | No UI |

---

## Demonstration

**BEFORE** (captured before any implementation commit):

```
$ date -u; <py312> experiments/t104_laya/run.py --model kev --questions .local/t104/questions.jsonl --out /tmp/claude-1000/x.jsonl; echo exit=$?
Fri Oct 16 04:30:43 AM UTC 2026
error: unknown model 'kev'; known: random, heuristic, laya, laya-ft, jev
exit=2
```

**AFTER** (real `kev.serve --run jaredpalmer/kev-0.8b --device cpu`, 2026-10-16 04:48-04:49 UTC):

```
$ KEV_BASE_URL=http://127.0.0.1:8009 run.py --model kev --questions .local/t104/questions_only.jsonl --out .local/t106/answers/kev08.jsonl
kev server: http://127.0.0.1:8009 (model kev-0.8b)
exit=0     (56 answers, 0 missing, 0 invalid; overall top-1 0.625, ECE 0.236, p50 1651.9 ms)
```

**DELTA**: `--model kev` went from `unknown model` (exit 2) to 56 scored answers from a self-hosted server; verdict reject against the unchanged bar.

**WITNESS**: backend-developer agent, 2026-10-16 (BEFORE 04:30:43 UTC, AFTER 04:49:58 UTC); Supervisor independently re-scored the answer file and drove the unreachable-server refusal at 05:22 UTC.

