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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☒ pass | `tests/test_t089_document_content.py` (22 tests: SC 1–6 incl. MIN_DESCRIBED_ENTRIES 0/3/999, AC 3/4/6/7/9, entry forms, normalization, third-party, secret, non-English, prose/npm negatives): `22 passed in 1.57s` (implementer) |
| Verification command run | ☐ pass / ☒ fail | implementer, 2026-10-13: `3 failed, 2669 passed, 2 skipped in 483.85s`; failures: 2 container tests (pre-existing, stale image) and `test_t001_pipeline.py::test_cited_line_numbers_are_1_indexed_and_match_the_file` (still red after switching it from PROJECT_SPEC.md to README.md; not diagnosed, step limit). `ruff check src tests`: All checks passed |
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

**AFTER** (2026-10-13T04:12:55Z–04:13:54Z, branch @ `465598b`, same command, one repo at a time, all exit 0;
provenance from `pack.documents`, hand-checked by backend-developer against each source file):

| Repo | architecture_description_missing | decision_records_missing | requirements_doc_missing | architecture | requirement-fidelity | overall |
|---|---|---|---|---|---|---|
| bryony | 0 → **0**, now `content`: `backend/scripts/README.md` "Folder structure" L8–12 (`/common`, `/companies`, `/crunchbase`, `/similarweb` exist under backend/scripts; `/salesforce` does not and is not counted). `event_design.md` no longer fills it | 1 → 1 (40 docs read) | 1 → 1 (40 docs read) | 83 → 83 | abstain → abstain | 59 → 59 |
| scraping-devops | **1 → 0**, `content`: README.md L6–10 (`- bin: helper scripts`, `- elk: …`, `- vagrant: …`, `- docker-registry: …`, `- rancher: …`) | 1 → 1 (12 read) | 1 → 1 (12 read) | abstain → abstain (`below_coverage_floor`) | abstain → abstain | abstain → abstain |
| kitchd | 0 → 0, `content`: **BRAINSTORMING_LOG.md L85–90** (a planned-files list, see deviations); PROJECT_SPEC.md has only 5 entries (risk table, `/apps/api/src/inventory/**` …) and is scanned later | 0 → 0, `content`: `docs/adr/0001-…md` L3 Status, L6 Context, L10 Decision, L18 Consequences | 0 → 0, `content`: PRD.md L33–37 `US-001…US-005` | 100 → 100 | 60 → 60 | 56 → 56 |
| ai-training | 0 → 0, `content`: `travel_chatbot/README.md` tree L95–100 (`├── agents/  # …`, `core/`, `edges/`, `nodes/`, `builder.py`) | **1 → 0**, `content`: `travel_chatbot/docs/trvl_flights_gondola_hotels_requirements.md` L4 `**Status**:` + L7 `## Context` (a requirements doc; literal AC 2, see deviations) | **0 → 1**: 44 docs read, no FR-/US-/AC-/Scenario item; its requirements doc uses plain bullets | 83 → **100** | abstain → abstain | 60 → **63** |
| coffee-shop-api | **1 → 0**, `content`: README.md "Project Structure" fenced tree L69–73 under `src/` (`common/`, `entities/`, `enums/`, `constants/`, `guards/`) | 1 → 1 (14 read) | 1 → 1 (14 read) | 80 → **90** | 50 → 50 | 74 → **76** |

easy-verifier (this repo, `docscan.py`): architecture-doc `content` BRAINSTORMING_LOG.md L215–219 module list;
decision-record `content` memory/decisions.md; requirements-doc `content` PRD.md (FR/US ids).

**DELTA**: a document role is now filled only by what a document contains (≥3 described real paths, a
decision structure, or a requirement item) or by a declaration, with the cited lines in the payload,
so scraping-devops and coffee-shop-api get credit for the structure their READMEs describe and a name
match such as bryony's `event_design.md` no longer passes.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
