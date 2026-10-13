# TASK_REVIEW — T089: Document roles filled by content or declaration, never by a name alone

> Sibling of `tasks/TASK_GUIDE_T089.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE** (captured 2026-10-13T03:33:08Z–03:34:59Z on `feat/T089-document-content` @ `494cae2`, before any
implementation commit; backend-developer). Command, one repo at a time, sequentially:
`PYTHONPATH=<worktree>/src <main>/.venv/bin/python -m easy_verifier.adapters.cli score --repo <repo> --scope project < /dev/null`
(runner log: `bryony 03:33:08→03:33:40`, `scraping 03:33:40→03:33:45`, `kitchd 03:33:45→03:33:57`,
`aitraining 03:33:57→03:34:03`, `coffee 03:34:03→03:34:09`, all exit 0). The score payload's
derivation does not name the filling file, so the files were captured at 03:34:59Z with the same
pre-change code (`roles.resolve` of the three roles, `load_repo_config` applied).

| Repo | architecture_description_missing | decision_records_missing | requirements_doc_missing | architecture | requirement-fidelity | overall |
|---|---|---|---|---|---|---|
| bryony | **0** — filled by name: `backend/docs/event_design.md` (`*design*`; an event-payload doc, false positive) | 1 — no file matched | 1 — "no file in the repository matched its patterns (the search ran to completion)" | 83 | abstain `below_coverage_floor` | 59 |
| scraping-devops | **1** — no file matched (README "Folder structures" not recognized, false negative) | 1 — no file matched | 1 — no file matched | abstain `below_coverage_floor` | abstain `below_coverage_floor` | abstain `no_dimension_rated` |
| kitchd | 0 — by name: `.claude/agents/api-designer.md` (`*design*`), `PROJECT_SPEC.md` (kit name), `docs/adr/0001-theme-system-token-architecture.md` | 0 — by name: `BRAINSTORMING_LOG*.md` ×4 (kit name), `docs/adr/0001-…md`, `memory/decisions.md` | 0 — by name: `PRD.md`, `requirement.md` | 100 | 60 | 56 |
| ai-training | 0 — by name: `travel_chatbot/docs/architecture.md` | 1 — no file matched | 0 — by name: `travel_chatbot/docs/trvl_flights_gondola_hotels_requirements.md` | 83 | abstain `insufficient_measured_weight` | 60 |
| coffee-shop-api | 1 — no file matched | 1 — no file matched | 1 — no file matched | 80 | 50 | 74 |

Pasted derivations (verbatim, `extract.py before`):
```
== bryony
  architecture_description_missing = 0
    source role 'architecture-doc' is filled (architecture-doc) in this pack's sources_found: 0 when a file matching the role was read, else 1 (missing); role matching is by the registry's glob patterns (list-dimensions prints them), over the files listed here
  decision_records_missing = 1
    source role 'decision-record' is not filled in this pack's sources_found: ...
  requirements_doc_missing = 1
    source role 'requirements-doc' is not filled: no file in the repository matched its patterns (the search ran to completion), so the document is missing (1), whatever else the byte budget cut
  rating architecture: 83 | rating requirement-fidelity: below_coverage_floor | overall: 59
== scraping
  architecture_description_missing = 1   (cites: ['README.md'])
    source role 'architecture-doc' is not filled in this pack's sources_found: ...
  decision_records_missing = 1 | requirements_doc_missing = 1
  rating architecture: below_coverage_floor | rating requirement-fidelity: below_coverage_floor | overall: no_dimension_rated
== kitchd
  architecture_description_missing = 0 | decision_records_missing = 0 | requirements_doc_missing = 0   (all "is filled (<role>) in this pack's sources_found")
  rating architecture: 100 | rating requirement-fidelity: 60 | overall: 56
== aitraining
  architecture_description_missing = 0 | decision_records_missing = 1 | requirements_doc_missing = 0
  rating architecture: 83 | rating requirement-fidelity: insufficient_measured_weight | overall: 60
== coffee
  architecture_description_missing = 1 | decision_records_missing = 1 | requirements_doc_missing = 1
  rating architecture: 80 | rating requirement-fidelity: 50 | overall: 74
```
Role files at 03:34:59Z (`roles_before.py`, HEAD `494cae2`):
```
bryony:          architecture-doc ['backend/docs/event_design.md'] | decision-record [] | requirements-doc []
scraping-devops: architecture-doc [] | decision-record [] | requirements-doc []
kitchd:          architecture-doc ['.claude/agents/api-designer.md', 'PROJECT_SPEC.md', 'docs/adr/0001-theme-system-token-architecture.md']
                 decision-record ['BRAINSTORMING_LOG.md', 'BRAINSTORMING_LOG_react-native-migration.md', 'BRAINSTORMING_LOG_team-roles.md', 'BRAINSTORMING_LOG_theme-system.md', 'docs/adr/0001-theme-system-token-architecture.md', 'memory/decisions.md']
                 requirements-doc ['PRD.md', 'requirement.md']
ai-training:     architecture-doc ['travel_chatbot/docs/architecture.md'] | decision-record [] | requirements-doc ['travel_chatbot/docs/trvl_flights_gondola_hotels_requirements.md']
coffee-shop-api: architecture-doc [] | decision-record [] | requirements-doc []
```

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
