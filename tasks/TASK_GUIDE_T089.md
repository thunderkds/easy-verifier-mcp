# TASK_GUIDE — T089: Document roles filled by content or declaration, never by a name alone
**Date**: 2026-10-12
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Note the **Complexity Level** above and apply the matching process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md`
7. Read `docs/ddr/0012-recognize-by-behaviour-and-content-not-names.md` (§3) and `BRAINSTORMING_LOG_document-recognition.md` § Round 2 (probe results)

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-10-12): *"how can we know what kind of document that project cover, some project covers A,
some of B, C in any. But we just cover in A. The risk will come from B and C"*, and *"we should find
a way, not the way we can not do, we bypass it"*.

Verified 2026-10-12: `_document_rule` (`core/metrics.py:918`) returns **1 = missing** whenever no
file matches the role's name patterns. `GENERIC_PATTERNS` (`core/roles.py:103`) includes the kit
names `PROJECT_SPEC.md` (architecture-doc) and `BRAINSTORMING_LOG*.md` (decision-record).
- k8s-ops: README "Folder structures" (`- bin: helper scripts`, `- elk: …`) is reported
  missing. That is a **false negative**.
- node-monorepo passes on `backend/docs/event_design.md`, an event-payload document that matched
  `*design*`. That is a **false positive**.

**Restated intent**:
> A document role is filled when a document's **content** has the role's shape, or when the project
> **declares** it. A name match alone never fills it. "Missing" then means *no document in the
> repository has that content*, a measured fact rather than our naming convention.

**Out of scope**:
- Weights (architecture docs 10 + 10, requirements doc 10 stay)
- Prose-only descriptions without list, table or tree structure (record as a known limitation with
  real examples, if found)
- The `readme`, `spec-doc`, `task-breakdown` and `contributing-guide` roles

**Requirement Refs**:
- FR-076 (added 2026-10-12)
- US-021

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed (user: "find a way"; G5/G6 recorded; "go" 2026-10-12)
- [x] Domain terms align with `PROJECT_SPEC.md` (source role, documentation rule)
- [x] Every Acceptance Criterion traces to the Requirement
- [x] FR-076 exists in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T087 (third-party docs, e.g. Harbor's own `docs/`, must not fill the host's roles)

**Entry point**: `_document_rule` in `src/easy_verifier/core/metrics.py`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | **architecture-doc** content shape: one document with ≥ 3 *described entries*, each naming a path that exists in the repository (directory or source file) followed by ≥ 2 words of description. Accepted forms: list item (`- bin: helper scripts`), table row (`` | `core/judge.py` | rules | ``), tree line (`├── eval/  # Evaluation set`), including inside fenced code blocks. Constant `MIN_DESCRIBED_ENTRIES = 3`, documented | content, anchored to the real tree |
| 2 | **decision-record** content shape: a document with a decision structure, either ≥ 2 of the headings/fields *Context*, *Decision*, *Consequences*, *Status*, *Alternatives*, or a dated entry (`YYYY-MM-DD`) with a decision verb (`decided`, `chose`, `we will`) and a rationale marker (`because`, `instead of`, `trade-off`). Cited sources: Nygard ADR, MADR | content |
| 3 | **requirements-doc** content shape: a document with ≥ 1 requirement item under the existing `requirement_item_patterns` (no new pattern list) | reuse |
| 4 | A file-name match **alone never fills** a role. Conventional names only raise scan priority. `PROJECT_SPEC.md` and `BRAINSTORMING_LOG*.md` are removed from `GENERIC_PATTERNS` | no name-only pass |
| 5 | A `.easy-verifier.toml` role declaration or an MCP detect-gate pick still fills the role, cited as `declared`, without a content check | project authority |
| 6 | When no document has the shape, the metric is `1` (missing) with a reason naming what was searched: *"N documents read; none describes ≥3 real repository paths"*. When the document scan was cut by batches or the cap, it abstains as today | missing is a measured fact |
| 7 | The payload states which evidence filled a role: `content` (with the cited lines), `declared`, or `readme-heading`. The existing README "Architecture" heading path is kept only if the section also passes AC 1 | provenance |
| 8 | **Real repos (paste, hand-checked)**: k8s-ops architecture-doc **filled** by README.md (cite the entries). node-monorepo: `event_design.md` **no longer** fills it; report what does, if anything. fullstack-ts and easy-verifier pass on content (their PROJECT_SPEC module tables), or the gap is reported. python-ml is filled by `travel_chatbot/README.md`. nest-api: report the result | real-repo verified |
| 9 | Negative fixtures: a changelog listing files (`- src/a.ts: fix typo`) **does** match AC 1's shape. Decide and document whether `CHANGELOG*` / release notes are excluded from architecture-doc candidates. Supervisor default: exclude them | precision |


### Amendment (Supervisor, 2026-10-13, after the implementer's findings 1–4)

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 10 | **Best document wins**: when several documents qualify for architecture-doc, the one with the **most described entries** fills it (tie: scan priority order). Cited lines come from that document | precision of the citation (finding 1) |
| 11 | **decision-record needs an actual decision**: a decision field (heading or bold field whose name is one of *Decision*, *Decision Outcome*, *Recommended Path* / *Recommendation*, *Chosen* / *Chosen Option*, *Selected* / *Selected Option*, *Approved direction*) **plus** at least one of *Context*, *Consequences*, *Status*, *Alternatives* / *Considered Options* / *Options*. Covers Nygard ADRs, MADR and brainstorming logs by content. Context + Status alone never fills it. Supersedes AC 2's field rule; the dated-entry form of AC 2 stays | python-ml false positive (finding 2); kit brainstorming logs back for solution-fit by content, not name (finding 4) |
| 12 | **requirements-doc by structure too**: also filled by a heading naming requirements (*Requirements*, *Functional Requirements*, *Non-functional Requirements*, *User Stories*, *Acceptance Criteria*, *Use Cases*), followed by 3 or more list items before the next heading of the same or higher level. Evidence kind `content`, lines cited. `requirement_items_traced_share` still uses only `requirement_item_patterns` (unchanged) | python-ml false negative (finding 3): "find a way" |
| 13 | `tests/test_t001_pipeline.py::test_cited_line_numbers_are_1_indexed_and_match_the_file` passes (root-cause the failure; do not weaken the assertion) | suite green |
| 14 | Real repos re-run after 10–12. This repo's own score is also run (finding 4): show solution-fit's evidence still includes the brainstorming log by content | real-repo verified |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | README listing `- bin: helper scripts`, `- elk: logs stack`, `- vagrant: vm files`, dirs exist | architecture-doc filled (content), 3 lines cited | automated test |
| 2 | same README, but `elk/` does not exist | only 2 real entries → not filled | automated test |
| 3 | `docs/design-tokens.md` with no structure | not filled despite the name | automated test |
| 4 | `docs/decisions/use-pg.md` with Context/Decision/Consequences | decision-record filled | automated test |
| 5 | toml declares `roles.architecture-doc = ["NOTES.md"]` | filled, `declared` | automated test |
| 6 | sabotage: set `MIN_DESCRIBED_ENTRIES` to 0 and to 999 | SC 1–3 flip as expected (pins both extremes) | automated test |

### Verification Command (exact, runnable)

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
# real repos, one at a time, run_in_background
.venv/bin/easy-verifier score --repo <repo> --scope project > /tmp/<name>.json
```

### Evidence

> Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T089.md`.

---

## UI / Design Acceptance Criteria

> N/A: backend only. All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `_document_rule` / `_readme_section` in `core/metrics.py` (where the role is
decided); `requirement_item_patterns` consumption (reuse for requirements-doc); the probe
`probe2.py` (shape idea; its parser missed code-block tables, so fix that).

Candidates: every in-scope document (`.md`, `.rst`, `.adoc`, `.txt`), with conventional names
scanned first so the read cap favours them. Validate each entry's path against the repo file set
already in hand. Never read the disk again per entry.

---

## Edge Case Checklist

- [ ] Paths written with `./`, trailing `/`, or backticks normalize before lookup
- [ ] Entries naming excluded (third-party, secret-bearing) paths do not count
- [ ] Very large docs: bounded read (existing per-file limits)
- [ ] Generated API docs (typedoc/sphinx output) are excluded by T087's `generated` patterns
- [ ] Non-English descriptions count (≥ 2 words, any script)

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/metrics.py` | content-shape recognizers in `_document_rule`; provenance |
| `src/easy_verifier/core/roles.py` | remove kit names from `GENERIC_PATTERNS` |
| `docs/SCORING_RULES.md` | rows for the 3 document rules |
| `tests/test_t086_document_content.py` | new |
| T068 snapshot | regenerate only where the role outcome changes; justify in review |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `RATING_RULES` weights | unchanged (DDR-0011) |
| `core/gate.py` | MCP pick already works |

---

## Test Plan

Unit fixtures SC 1–6, with both-extremes sabotage. Real-repo pass on 5 repos, hand-checked against
each cited line.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review (Medium risk: reads arbitrary docs; nothing echoed unredacted)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T089.md`
- [ ] Real-repo runs pasted (AC 8)
- [ ] Supervisor notified: task ready for Stage 4 review
