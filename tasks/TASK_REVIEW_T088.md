# TASK_REVIEW — T088: Layers assigned by observed behaviour

> Sibling of `tasks/TASK_GUIDE_T088.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE**: captured 2026-10-12T09:54Z on `feat/T088-behaviour-layers` at `72223c5` (no implementation commit yet), by `PYTHONPATH=<worktree>/src .venv/bin/python -m easy_verifier.adapters.cli score --repo <repo> --scope project`, one repo at a time. Run log:

```
=== bryony 2026-10-12T09:54:04Z
warning [batches]: read batches 1 of 6 (200 of 1159 in-scope source files, most important and most-changed first); continue with --batches 2, or --all
exit 0 2026-10-12T09:54:31Z
=== scraping-devops 2026-10-12T09:54:31Z
exit 0 2026-10-12T09:54:36Z
=== kitchd 2026-10-12T09:54:36Z
exit 0 2026-10-12T09:54:46Z
=== ai-training 2026-10-12T09:54:46Z
exit 0 2026-10-12T09:54:51Z
=== coffee-shop-api 2026-10-12T09:54:51Z
exit 0 2026-10-12T09:54:54Z
DONE
```

`layer_direction_violations` (architecture dimension) per repo, extracted from the JSON:

```
## bryony  overall=59  architecture=83
  ABSTAINED: 88 of 195 non-shared source file(s) quoted here classify into a layer (api, service, data) by the declared layer_paths conventions, below the declared minimum share of 0.50, so the layer direction of this code is not measurable; curated layer_paths only: no local-layer or .easy-verifier.toml layer paths were declared
## scraping-devops  overall=None  architecture=None
  ABSTAINED: no import statement was found in this pack's source-file excerpts, so there is no import graph to measure; that is not the same as a graph without edges. import statements are the registry's import tokens, found textually in excerpts of registry-language files; a statement names a file when it contains the file's stem (a package's __init__-style file: its directory) as a whole word -- a textual match, not a resolved import
## kitchd  overall=56  architecture=100
  ABSTAINED: 32 of 177 non-shared source file(s) quoted here classify into a layer (api, service, data) by the declared layer_paths conventions, below the declared minimum share of 0.50, so the layer direction of this code is not measurable; curated layer_paths only: no local-layer or .easy-verifier.toml layer paths were declared; all 185 source files -- computed over the whole text of those files, not only the excerpts quoted in this pack
## ai-training  overall=60  architecture=83
  ABSTAINED: 2 of 79 non-shared source file(s) quoted here classify into a layer (api, service, data) by the declared layer_paths conventions, below the declared minimum share of 0.50, so the layer direction of this code is not measurable; curated layer_paths only: no local-layer or .easy-verifier.toml layer paths were declared; all 90 source files -- computed over the whole text of those files, not only the excerpts quoted in this pack
## coffee-shop-api  overall=80  architecture=80
  value: 0
  derivation: 0 import statement(s) from a lower to a higher layer (data -> service, service -> api, data -> api). 35 of 35 non-shared source file(s) quoted here classify into a layer (api, service, data) by the declared layer_paths conventions (curated layer_paths only: no local-layer or .easy-verifier.toml layer paths were declared); shared and unclassified files never count, and a file stem shared by files of different layers names none; only the import statements quoted in this pack are seen; import statements are the registry's import tokens, found textually in excerpts of registry-language files; a statement names a file when it contains the file's stem (a package's __init__-style file: its directory) as a whole word -- a textual match, not a resolved import; all 85 source files -- computed over the whole text of those files, not only the excerpts quoted in this pack
```

Summary: bryony abstains at 88/195 classified (45%), kitchd 32/177 (18%), ai-training 2/79 (3%), scraping-devops has no import graph (abstains, no source imports read), coffee-shop-api 35/35 classified by folder name with 0 violations (no cited examples: there are none). No file is classified by what its code does.

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
