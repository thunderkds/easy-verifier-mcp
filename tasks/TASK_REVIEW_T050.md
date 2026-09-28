# TASK_REVIEW — T050: Code-quality and architecture packs gather code evidence (source excerpts, import lines)

> Sibling of `tasks/TASK_GUIDE_T050.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE**: captured by backend-developer on the worktree at `13cef1c` (no T050 commit yet).
Scratch repo `$S/repo` (git, committed): `src/app/alpha.py` (`route`: if, elif, elif+and, if+or,
for, if, while, if, if = 11 decision points, CCN 12 by `approximate_ccn`; imports `beta`),
`src/app/beta.py` (imports `alpha`), `src/app/__init__.py`, `tests/test_alpha.py`,
`pyproject.toml` (with `[tool.ruff]`), `README.md`. `show.py` prints the three T050 metrics for
the code-quality and architecture packs from the score JSON; `packbytes.py` runs `run_dimension`
for both dimensions at project scope and sums excerpt bytes (NFR-009 baseline).

```
$ git -C easy-verifier-mcp-T050 rev-parse --short HEAD
13cef1c
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-09-28T06:16:03Z
$ PYTHONPATH=src python -m easy_verifier.adapters.cli score --repo $S/repo --scope project < /dev/null > $S/before_scratch.json
exit=0
$ python show.py before_scratch.json
architecture  functions_over_ccn_10_share  ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
architecture  max_function_ccn             ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
architecture  top_level_import_cycles      ABSTAIN: no import statement was found in this pack's source-file excerpts, so there is no import graph to measure; tha
code-quality  functions_over_ccn_10_share  ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
code-quality  max_function_ccn             ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
code-quality  top_level_import_cycles      ABSTAIN: no import statement was found in this pack's source-file excerpts, so there is no import graph to measure; tha
$ PYTHONPATH=src python -m easy_verifier.adapters.cli score --repo . --scope project < /dev/null > $S/before_self.json
exit=0
$ python show.py before_self.json
architecture  functions_over_ccn_10_share  ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
architecture  max_function_ccn             ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
architecture  top_level_import_cycles      ABSTAIN: no import statement was found in this pack's source-file excerpts, so there is no import graph to measure; tha
code-quality  functions_over_ccn_10_share  ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
code-quality  max_function_ccn             ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
code-quality  top_level_import_cycles      ABSTAIN: no import statement was found in this pack's source-file excerpts, so there is no import graph to measure; tha
$ PYTHONPATH=src python packbytes.py $S/repo   # NFR-009 baseline
code-quality  bytes=70 excerpts=1 truncated=False omitted=0
architecture  bytes=49 excerpts=1 truncated=False omitted=0
$ PYTHONPATH=src python packbytes.py .
code-quality  bytes=1711 excerpts=1 truncated=False omitted=0
architecture  bytes=84498 excerpts=7 truncated=False omitted=0
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-09-28T06:16:04Z
```

All three metrics abstain in both packs on both repos because neither pack quotes any source code
(code-quality: 1 config excerpt; architecture on this repo: 7 doc excerpts, 0 code).

> **Correction to the BEFORE setup note (added with AFTER, capture above unchanged)**: `$S/repo`
> pre-existed in the shared scratchpad from T033, so it also contains `src/app/gamma.py` (T033's
> file: `from app import beta`, one function `g`, CCN 1) and an earlier T033 commit. The BEFORE
> output is unaffected (every metric abstained); AFTER counts `g` as a fourth function, hence the
> share 1/4 = 0.25 here versus 1/3 in the automated fixture, which has no gamma.py.

**AFTER**: same commands on the T050 implementation `04b1101` (backend-developer), plus pack bytes
on an external TypeScript repo (`nestjs-with-socket`; "before" = the `d8f4d7f` source tree via
`git archive`).

```
$ git rev-parse --short HEAD
04b1101
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-09-28T06:24:28Z
$ PYTHONPATH=src python -m easy_verifier.adapters.cli score --repo $S/repo --scope project < /dev/null > $S/after_scratch.json
exit=0
$ python show.py after_scratch.json
architecture  functions_over_ccn_10_share  ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
architecture  max_function_ccn             ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
architecture  top_level_import_cycles      1 from ['src/app/alpha.py:1-1', 'src/app/beta.py:1-1']
code-quality  functions_over_ccn_10_share  0.25 from ['src/app/alpha.py:4-22', 'src/app/beta.py:4-5', 'src/app/beta.py:8-9', 'src/app/gamma.py:4-5']
code-quality  max_function_ccn             12 from ['src/app/alpha.py:4-22']
code-quality  top_level_import_cycles      ABSTAIN: no import statement was found in this pack's source-file excerpts, so there is no import graph to measure; tha
$ time PYTHONPATH=src python -m easy_verifier.adapters.cli score --repo . --scope project < /dev/null > $S/after_self.json
exit=0 elapsed=0.85s
$ python show.py after_self.json
architecture  functions_over_ccn_10_share  ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
architecture  max_function_ccn             ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
architecture  top_level_import_cycles      0 from ['scripts/vendor_sources.py:22-22', 'scripts/vendor_sources.py:24-34', 'src/easy_verifier/adapters/cli.py:12-24', 'src/easy_verifier/adapters/cli.py:3-3']
code-quality  functions_over_ccn_10_share  ABSTAIN: whole-set-dependent: the byte budget truncated this pack, so any ratio, density or share computed here describ
code-quality  max_function_ccn             53 from ['src/easy_verifier/core/judge.py:691-802']
code-quality  top_level_import_cycles      ABSTAIN: whole-set-dependent: the byte budget truncated this pack, so any ratio, density or share computed here describ
$ PYTHONPATH=src python packbytes.py $S/repo
code-quality  bytes=589 excerpts=5 truncated=False omitted=0
architecture  bytes=110 excerpts=4 truncated=False omitted=0
$ PYTHONPATH=src python packbytes.py .
code-quality  bytes=118849 excerpts=54 truncated=True omitted=1
architecture  bytes=97412 excerpts=125 truncated=False omitted=0
# external repo (TypeScript), before = source tree of d8f4d7f, after = HEAD
$ PYTHONPATH=$S/pre_t050/src python packbytes.py nestjs-with-socket
code-quality  bytes=887 excerpts=2 truncated=False omitted=0
architecture  bytes=43 excerpts=1 truncated=False omitted=0
$ PYTHONPATH=src python packbytes.py nestjs-with-socket
code-quality  bytes=1014 excerpts=3 truncated=False omitted=0
architecture  bytes=948 excerpts=8 truncated=False omitted=0
$ PYTHONPATH=src python -m easy_verifier.adapters.cli score --repo nestjs-with-socket --scope project | show.py
exit=0
architecture  functions_over_ccn_10_share  ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
architecture  max_function_ccn             ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
architecture  top_level_import_cycles      0 from ['backend/src/app.controller.spec.ts:1-3', 'backend/src/app.controller.ts:1-2', 'backend/src/app.module.ts:1-4', 'backend/src/app.service.ts:1-1']
code-quality  functions_over_ccn_10_share  0.0 from ['backend/src/main.ts:4-7']
code-quality  max_function_ccn             1 from ['backend/src/main.ts:4-7']
code-quality  top_level_import_cycles      ABSTAIN: no import statement was found in this pack's source-file excerpts, so there is no import graph to measure; tha
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-09-28T06:24:30Z
```

| Pack (project scope) | bytes before | bytes after | truncated after | budget |
|---|---|---|---|---|
| this repo, code-quality | 1,711 | 118,849 | yes (omitted ≥1) | 120,000 |
| this repo, architecture | 84,498 | 97,412 | no | 120,000 |
| scratch repo, code-quality | 70 | 589 | no | 120,000 |
| scratch repo, architecture | 49 | 110 | no | 120,000 |
| nestjs-with-socket, code-quality | 887 | 1,014 | no | 120,000 |
| nestjs-with-socket, architecture | 43 | 948 | no | 120,000 |

Scratch repo: code-quality `max_function_ccn` 12 (`route`), `functions_over_ccn_10_share` 0.25;
architecture `top_level_import_cycles` 1 (alpha <-> beta). This repo: architecture
`top_level_import_cycles` 0 (not truncated); code-quality `max_function_ccn` 53
(`core/judge.py:691`, the most complex function, ranked first so the budget keeps it) while
`functions_over_ccn_10_share` abstains **for truncation only** (whole-set, FR-027a; the functions of
33 source files exceed the 120,000-byte budget). Every pack stays within its budget (NFR-009).

**DELTA**: A user running `score` on a real repository now gets code-quality approximate CCN figures and an architecture import-cycle count computed from cited function and import-line excerpts, instead of three abstentions.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T050.jsonl`, never the
implementing agent alone]
