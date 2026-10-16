# TASK_REVIEW — T104: Laya vs LLM on detect-gate picks (experiment)

> Sibling of `tasks/TASK_GUIDE_T104.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t104_experiment_harness.py` (26 tests: AC1 determinism/label-in-candidates/cap 20/shuffle, AC2 over-budget drop + skip counted, AC3 accuracy/ECE/latency/coverage by hand + missing/invalid + no torch import, AC10 unknown model / missing key exit 2 naming it, jev allow-list refusal, shared answer format, end-to-end CLI without ML deps). Testvenv has no torch/laya: `27 passed in 1.43s` (incl. 1 parametrised); `tests/test_t100_no_personal_identifiers.py`: `3 passed in 0.68s` — pass |
| Verification command run | ☑ pass | `pytest -q tests/test_t104_experiment_harness.py` → `27 passed in 1.43s`; `ruff check src tests experiments` → `All checks passed!`; `git diff develop...HEAD -- src pyproject.toml compose.yaml Dockerfile scripts` → empty (Files Must NOT Touch held) — pass |
| Negative cases hold | ☑ pass | Live, 2026-10-16 03:25 UTC: `run.py --model nope` → `error: unknown model 'nope'; known: random, heuristic, laya, laya-ft, jev` exit=2; `run.py --model jev` on the 56 real questions with a dummy key → `error: model 'jev' refuses repos not on its public allow-list ['easy-verifier-mcp']: fullstack-ts, k8s-ops, …` exit=2, before any network call — pass |
| verify | ☑ pass | No `src/` change, so the product surfaces (CLI/MCP/report/container) are untouched; the delivered surface is the harness, driven for real: `run.py --model heuristic` on the 56 real-repo questions exit=0 → `evaluate.py` overall `56 / 0 missing / 0 invalid / accuracy 0.696 / ece 0.237` (identical to the earlier recorded run). Experiment runs: random, heuristic, laya zero-shot on all 56; laya-ft LORO on 3 of 8 folds (user 2026-10-16: "just use some for testing is oke, not run through all"); LLM baseline by a separate blind agent, 56/56. Outputs and report git-ignored (`git check-ignore` confirms `.local/t104/questions.jsonl`, `docs/experiments/T104_laya_picks.md`) — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed the 12-file diff (`experiments/t104_laya/**`, the test file, this review file) plus the `easy_verifier.core` symbols it imports read-only (`gate._eligible/_heading/_DOC_*/_CONFIG_*`, `context._walk/_is_secret_bearing`, `roles.resolve`). Nothing in `src/` calls the harness, so no product callers. code-review: P0 0 / P1 0 / P2 0 / P3 2 (ECE mis-bins a confidence outside 0–1 silently; Jev allow-list trusts the alias string). Security review (Medium risk, inline): the only network path is `jev`, gated before construction by the allow-list and absent key; no repo content left the machine (Jev not run); all real-repo data and the report sit under git-ignored paths; T100 guard green — pass |
| Full smoke suite still green (no regression) | ☑ pass | `pytest -q -x` (py3.12 testvenv, branch HEAD) → `2934 passed, 3 skipped in 501.08s (0:08:21)` — pass (T103 baseline 2907 + 27 new) |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | No UI — experiment harness and a local Markdown report |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | No UI — experiment harness and a local Markdown report |
| **UI: Responsiveness at target viewports** | ☑ N/A | No UI — experiment harness and a local Markdown report |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured by backend-developer in worktree `easy-verifier-mcp-T104`, branch
`feat/T104-laya-picks-experiment` at `0ca6e35`, before any implementation commit):

```
$ date -u; ls experiments/; echo "exit=$?"
Thu Oct 15 02:46:48 PM UTC 2026
ls: cannot access 'experiments/': No such file or directory
exit=2
```

And `memory/decisions.md` (2026-10-15 "Jev / Laya revisit") states the bar is unmeasured:
> "Must be measured before adoption: zero-shot is useless, so it needs our own labelled gate questions
> from the real repos." … "Awaiting user go."

**AFTER** (Supervisor, worktree `easy-verifier-mcp-T104`, 2026-10-16):

```
$ ls experiments/
t104_laya
$ run.py --model heuristic … && evaluate.py …   (56 real-repo questions)
| overall | 56 | 0 | 0 | 0.696 | 0.237 | 0.017 | 0.069 | 0.411 | 0.913 |
```

Results (local report `docs/experiments/T104_laya_picks.md`): top-1 on 56 questions — random 0.054,
heuristic 0.696, Laya zero-shot 0.304 (p50 906 ms), LLM 0.946 (ECE 0.131); Laya fine-tuned
leave-one-repo-out on a 3-fold sample (11 questions) 11/11, ECE 0.000/0.000/0.134, p50 343–808 ms.
Verdict against the pre-registered bar: **not yet — CPU latency** (bar p50 ≤ 200 ms).

**DELTA**: The Jev/Laya question is now answered with numbers on our own repos — fine-tuned Laya can match the LLM on detect picks but is 2–4× too slow on CPU — and any future model is measured by adding one backend file.

**WITNESS**: Supervisor (session 2026-10-16) re-ran the heuristic path and both refusals live after the implementer's runs; LLM answers produced by a separate blind agent.
