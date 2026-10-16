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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☐ pass / ☐ fail | [test file path(s) — required before Done] |
| Verification command run | ☐ pass / ☐ fail | [paste actual output] |
| Negative cases hold | ☐ pass / ☐ fail | |
| verify | ☐ pass / ☐ fail / ☐ N/A | [must literally state "pass" or "fail" here too] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail | |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | No UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | No UI |
| **UI: Responsiveness at target viewports** | ☐ N/A | No UI |

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

**WITNESS**: backend-developer agent, 2026-10-16 (BEFORE 04:30:43 UTC, AFTER 04:49:58 UTC).

