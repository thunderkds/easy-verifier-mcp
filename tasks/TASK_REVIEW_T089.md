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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☒ pass | `tests/test_t089_document_content.py` (47 tests): SC 1–6 with MIN_DESCRIBED_ENTRIES 0/3/999; AC 3/4/6/7/9; AC 10 plus decision B (3 directories outrank 6 files in one directory; ties go to scan priority); AC 11 (ai-training-shaped Status+Context → 1, decision-only → 1, Decision+Status / MADR / kit log → 0); AC 12 plus decision A (`## Functional Requirements` over 3 bullets → 0, bare `## Requirements` / `## System Requirements` over `- Node`/`- Npm`/`- Docker` → 1, threshold tested at 0/3/4); decision C (templates never fill); AC 14 (solution-fit quotes a log by content). Result: `47 passed` (implementer) |
| Verification command run | ☒ pass | implementer, 2026-10-13 @ 484ce20, full suite: `2 failed, 2695 passed, 2 skipped in 410.63s`. Both failures are the pre-existing container tests (stale image). AC 13 `test_cited_line_numbers_are_1_indexed_and_match_the_file` and `test_architecture_pack_against_this_repo` both pass, with assertions unchanged in substance. `ruff check src tests`: All checks passed |
| Negative cases hold | ☐ pass / ☐ fail | |
| verify | ☑ pass | Supervisor 2026-10-13 drove the CLI from the branch: scraping-devops architecture-doc 0, filled by README.md (content: L6 `- bin: helper scripts`, L7 `- elk: …`, L8 `- vagrant: …`); decision-record 1 ("12 documents read; none has a decision structure"); requirements-doc 1. ai-training architecture-doc 0 (travel_chatbot/README.md tree L95+); decision-record 1 (Status+Context alone no longer counts); requirements-doc 0 (`## Functional Requirements` L38). t089 + t001: 96 passed — pass. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Supervisor review of `core/documents.py` (new), `metrics._document_rule`, `roles.GENERIC_PATTERNS` (kit names removed), `RoleResolution.walked`, the 3 dimension collect calls, and the test changes in finding 5 (each justified against AC 4/7). P0 0 · P1 0 after 3 rounds of precision decisions (AC 10–12, A–C). Security: cited lines and paths pass through `redact.scan` like `files_read`; candidates go through `peek_source` (refuses secret-bearing and out-of-repo files); third-party and secret-bearing paths never count as entries. Known limitations (follow-ups): the kitchd/this-repo architecture-doc citation is a task's Files-to-Change table (true content, weak citation); a WCAG URL path in README is masked by `high_entropy_string` (a redaction false positive found via AC 13). |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail | |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Backend only. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Backend only. |
| **UI: Responsiveness at target viewports** | ☑ N/A | Backend only. |

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

**AFTER** (final, after AC 10–14 and decisions A–C: 2026-10-13T04:59:02Z–05:00:09Z, branch @ `484ce20`,
same command, one repo at a time, all exit 0, plus this repo's main checkout; provenance from
`pack.documents`, hand-checked by backend-developer against each source file):

| Repo | architecture_description_missing | decision_records_missing | requirements_doc_missing | architecture | requirement-fidelity | overall |
|---|---|---|---|---|---|---|
| bryony | 0 → 0, `content`: `backend/scripts/README.md` "Folder structure" L8–12 (`/common`, `/companies`, `/crunchbase`, `/similarweb` exist; `/salesforce` does not and is not counted). `event_design.md` no longer fills it | 1 → 1 (40 docs read) | 1 → 1 (the netwise `## Requirements` install list no longer counts, decision A) | 83 → 83 | abstain → abstain | 59 → 59 |
| scraping-devops | **1 → 0**, `content`: README.md L6–10 (`- bin: helper scripts`, `- elk: …`, `- vagrant: …`, `- docker-registry: …`, `- rancher: …`) | 1 → 1 (12 read) | 1 → 1 (`### Requirements` install list no longer counts, decision A) | abstain `below_coverage_floor` → abstain `insufficient_measured_weight` (the filling README now counts toward coverage) | abstain → abstain | abstain → abstain |
| kitchd | 0 → 0, `content` (decision B, most distinct directories): **`tasks/TASK_GUIDE_T029.md` L163+ "Files to Change" table — still a task file list** | 0 → 0, `content`: `docs/adr/0001-…md` L3 `**Status**: Accepted` + L10 `## Decision` | 0 → 0, `content`: PRD.md L33–37 `US-001…US-005` | 100 → 100 | 60 → 60 | 56 → 56 |
| ai-training | 0 → 0, `content`: `travel_chatbot/README.md` tree L95–100 | 1 → 1 (AC 11: Status + Context, no decision field) | 0 → 0, now `content` (AC 12): the requirements doc's L38 `## Functional Requirements` over its bullets | 83 → 83 | abstain → abstain | 60 → 60 |
| coffee-shop-api | **1 → 0**, `content`: README.md "Project Structure" fenced tree L69–73 under `src/` | 1 → 1 (14 read) | 1 → 1 (14 read) | 80 → **90** | 50 → 50 | 74 → **76** |
| easy-verifier (main checkout) | `content` (decision B): **`tasks/TASK_GUIDE_T001.md` L170+ "Files to Change" table — a task file list** | `content`: memory/decisions.md L1 heading "decisions" + L140 `**Consequences**:` | `content`: PRD.md FR/US ids | 100 | 20 | 43 |

**AC 14 — solution-fit still reaches the brainstorming logs, by content** (`sfcheck.py`, solution-fit pack):
- easy-verifier: `decision_lines(BRAINSTORMING_LOG.md)` = `[(58, '## Alternative Paths'), (193, '## Recommended Path')]`; files_read holds BRAINSTORMING_LOG.md and the 6 BRAINSTORMING_LOG_*.md (the template no longer qualifies, decision C); excerpts `BRAINSTORMING_LOG.md` L67–86, 87–105, 106–123, 124–164, 193–211.
- kitchd: `decision_lines(BRAINSTORMING_LOG.md)` = `[(22, '## Alternative Paths'), (76, '## Recommended Path')]`; excerpts `BRAINSTORMING_LOG.md` L30–41, 42–53, 54–64, 76–81, plus the react-native log.

**DELTA**: a document role is now filled only by what a document contains, or by a declaration, with the
cited lines in the payload:
- architecture-doc: at least 3 described real paths; when several documents qualify, the one covering the most distinct directories wins.
- decision-record: a decision plus its context.
- requirements-doc: requirement items, or an explicitly named requirements heading over a list.

As a result, scraping-devops and coffee-shop-api get credit for the structure their READMEs describe,
bryony's `event_design.md` no longer passes on its name, and kit brainstorming logs still reach
solution-fit by their content.

Remaining findings:
- (B) On kitchd and on this repo, the winning architecture document is still a TASK_GUIDE "Files to Change" table, even when ranking by distinct directories. No name-based exclusion was added, as instructed.
- (D) `high_entropy_string` gives a false positive on the WCAG URL path in this repo's README.md. That was the root cause of AC 13; it is not fixed here.

**WITNESS**: Supervisor, 2026-10-13. Re-ran t089 + t001 (96 passed) and drove `score` on scraping-devops and ai-training from the branch; the results match the implementer's AFTER table.
