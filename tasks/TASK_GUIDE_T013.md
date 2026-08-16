# TASK_GUIDE — T013: report.py — self-contained multi-dimension HTML report
**Date**: 2026-08-15
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P0
**Assigned agent**: Backend-Implementer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. **C2** — apply the C2 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. **C2** — read `memory/codebase-map.md`
7. Read `templates/report_template.html` — the kit's existing report styling is the visual reference

> **Not a UI task.** This renders a static HTML document from structured data. There is no
> component, no client-side state, no interaction. The UI/Design AC section is deleted per
> `PROJECT_SPEC.md` Critical Constraint 11 and all three UI Evidence rows are ☐ N/A.

---

## Requirement (Pillar 1 — Adapt the requirement)

Turn validated findings and their packs into one browsable, self-contained HTML document, written
into the evaluated repo, that a developer can trust because every claim in it can be checked.

**Restated intent**:
> `write_report(findings, packs, target_repo)` validates via T006, then renders a single HTML file
> spanning **all** submitted dimensions — findings grouped by dimension with their evidence,
> confidence and any suggestion, plus per-dimension coverage scores each shown with its miss list —
> and writes it to the *evaluated* repo's `reports/` under a collision-proof, self-describing name.

**Out of scope**:
- Validation logic itself (T006) — this task calls it and refuses to render on rejection.
- Any report format other than HTML (explicitly out of scope in `PRD.md`).
- Applying suggestions (FR-024).

**Requirement Refs**:
- FR-014: `write_report` renders findings into a self-contained HTML report
- FR-017: written into the **evaluated** repo under `reports/`, never the verifier's own repo
- FR-018: self-contained — no external CSS, JS, font or image requests
- FR-018a: spans multiple dimensions, grouped, with a combined summary and per-dimension coverage
- FR-018b: unique self-describing filenames with sub-second UTC resolution; never overwrites
- FR-016a: coverage never rendered without the named miss list
- FR-004: standalone-mode limited-context warning present in every report
- FR-023: render the suggested improvement alongside its finding
- FR-021c: container-internal paths must never leak into a report
- NFR-011: on first write to a target's `reports/`, advise that reports may contain sensitive findings
- NFR-007: write nothing outside `reports/`

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

---

## Dependencies & Reachability

**Depends on**: T006 — `validate_findings()` must gate every render; T012 — `CombinedPack`/`CoverageSummary` are what the report presents.

**Entry point**: `write_report`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Renders one HTML file covering **all** submitted dimensions, grouped by dimension, with a combined summary — seven single-dimension files is a failure | FR-018a |
| 2 | Self-contained: a scan of the output finds zero `http://`/`https://`/`//` references in `src`, `href`, `url()`, `@import`, or `<script src>` | FR-018 |
| 3 | Written under `<target_repo>/reports/`, and a test asserts nothing is written into the verifier's own repo | FR-017, NFR-007 |
| 4 | Filename encodes scope and a UTC timestamp with sub-second resolution; two reports written in the same second do not collide | FR-018b |
| 5 | Writing **never** overwrites an existing file — a pre-existing name causes a new name, not a clobber | FR-018b |
| 6 | Every coverage score rendered is adjacent to its named miss list — a test asserts no score appears without one | FR-016a |
| 7 | In standalone mode the limited-context warning is rendered prominently | FR-004 |
| 8 | Each finding renders its evidence reference, confidence, and (where present) its suggestion | FR-015, FR-023 |
| 9 | Invalid findings → validation error returned, **no file written** | FR-015, NFR-004 |
| 10 | On first write to a target's `reports/`, the NFR-011 sensitivity advisory is returned to the caller and rendered in the report | NFR-011 |
| 11 | No container-internal path (e.g. `/workspace/...`) appears in output; paths are repo-relative or host-recognisable | FR-021c |
| 12 | All caller-supplied text is HTML-escaped — a finding titled `<script>alert(1)</script>` renders as text | Security |
| 13 | Truncation records and redaction presence are visible in the report, not silently dropped | FR-011b, NFR-010 |
| 14 | **Excluded sources render as `excluded: secret-bearing`**, visibly distinct from `not found` and `not examined` — a reader must be able to tell "we chose not to read this" from "this wasn't there" | DDR-0002, FR-016a |
| 15 | **The NFR-011 advisory names the real exposure**, not merely that redaction occurred: a report written into a target repo may be committed, attached to a ticket, or pasted into a PR, and in MCP mode pack content reaches the calling agent — which may be a hosted model. A test asserts the advisory text names both destinations | NFR-011, DDR-0002 |

> **Note (T004 blast-radius, 2026-08-16).** This task is where redaction stops
> being precautionary. Until now output reached only the invoking user's own
> terminal; T013 makes it durable inside someone else's repository. The unsalted
> fingerprint decision (DDR-0001) rests explicitly on the premise that *reports
> stay inside the evaluated repo* — if this task's output is ever designed to
> travel, that premise breaks and salting must be reconsidered before merge.

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | 5 valid findings across 3 dimensions + their packs, target = a temp repo | One HTML file in `<temp>/reports/`, all 3 dimensions grouped, opens standalone with no network | automated test |
| 2 | The rendered file scanned for external references | Zero | automated test |
| 3 | Two `write_report` calls in the same second | Two distinct files, neither overwritten | automated test |
| 4 | A finding lacking confidence | Validation error; `reports/` unchanged | automated test |
| 5 | A finding with `<script>` in its title | Escaped in output; no executable script tag | automated test |
| 6 | Packs carrying paths rooted at `/workspace` | No `/workspace` in the rendered output | automated test |

### Verification Command (exact, runnable)

```bash
pytest tests/test_t013_report.py -q && \
  grep -cE 'https?://|<script src|@import' "$(ls -t /tmp/evtest/reports/*.html | head -1)" || echo "0 external refs"
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T013.md`.
> This task's Evidence table is the audit artifact for the "Reports requiring a network fetch: 0" KPI.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T013.md`.

---

## UI / Design Acceptance Criteria

> **N/A — pure backend/output task.** Section deleted per `PROJECT_SPEC.md` Critical Constraint 11.
> All three UI Evidence rows in `tasks/TASK_REVIEW_T013.md` are marked ☐ N/A: this task renders a
> static document from structured data, with no component, no interaction and no design system to
> comply with. Visual reference is `templates/report_template.html`.

---

## Approach

**Pattern reference**: `templates/report_template.html` and `templates/delivery_report_template.html` — the kit's existing self-contained report style (inlined CSS, dark neon theme per `memory/decisions.md`). Match the approach to self-containment, not necessarily the exact styling.

Render with a plain Python string template or `string.Template` unless the MCP SDK already brings
Jinja — do not add a templating dependency for one document. Inline all CSS in a `<style>` block; no
fonts, no images, no scripts. If an icon is needed, use a Unicode character.

AC #12 deserves real care: this report renders text an LLM wrote about code it read, into HTML, and
that text routinely contains angle brackets, quotes and code fragments. Escape everything on the way
in, at one chokepoint, and do not "helpfully" allow a Markdown subset — a renderer that permits any
markup in caller-supplied text is an injection surface in a file a developer will open in a browser.

FR-021c (AC #11) is easy to forget because it only manifests inside the container, which is the last
place tested. Normalize paths to repo-relative at the point of rendering, and let T017's parity test
confirm it.

---

## Edge Case Checklist

- [ ] `reports/` does not exist in the target → created (this is the one permitted write outside an existing path)
- [ ] `reports/` exists but is read-only, or the whole mount is read-only (the container case, NFR-013) → clear actionable error, not a traceback
- [ ] Zero findings but valid packs → a report stating no findings were made, with coverage still shown (a real and useful result)
- [ ] A dimension with findings but a pack that was fully truncated → the truncation must be visible, or the coverage reads as better than it was
- [ ] Very many findings (hundreds) → a usable document; consider grouping/collapsing without scripts (`<details>` is inert HTML and acceptable)
- [ ] Extremely long excerpt text → wrapped, does not blow out the layout
- [ ] Non-ASCII content in findings or excerpts → correct `<meta charset>`, no mojibake
- [ ] Target repo path is a symlink → resolved consistently for both the write location and the rendered paths
- [ ] Concurrent writes from two processes → the collision-proof naming holds (AC #4/#5)
- [ ] The target repo *is* the verifier repo (self-evaluation, which is this project's own test case) → FR-017 is satisfied because the target genuinely is the evaluated repo; the test for AC #3 must distinguish "target happens to be self" from "wrote into the verifier by mistake"
- [ ] Redacted fingerprints render as fingerprints — never re-expanded, never linked back to a raw source line that shows the secret

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/report.py` | New — `write_report()`, rendering, filename generation, path normalization |
| `src/easy_verifier/core/models.py` | Add `ReportResult` (path written, advisory, validation errors) |
| `src/easy_verifier/adapters/cli.py` | `write-report` subcommand accepting `--findings <path>` or stdin JSON |
| `tests/test_t013_report.py` | New |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `.claude/hooks/**` | Must-not-touch |
| `src/easy_verifier/core/findings.py` | Owned by T006 — call it, do not modify validation |
| `templates/**` | Kit templates are shared assets; copy the approach, do not edit them |
| `memory/**`, `PROJECT_KANBAN.md` | Supervisor-only |

---

## Test Plan

`tests/test_t013_report.py` — render into `tmp_path` targets throughout. The self-containment test
(AC #2) should parse the output rather than grep it loosely, so a URL inside an escaped code excerpt
does not produce a false failure while a real `<link>` slips by. Include the collision test by
freezing/monkeypatching the clock so two writes genuinely share a second. Assert AC #3 by
snapshotting the verifier repo's own tree before and after every test in the module.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk — required; HTML injection surface)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T013.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] UI Evidence rows marked ☐ N/A with the justification above (Hard-Stop Gate 6)
- [ ] `Skill({ skill: "verify" })` run — a real report opened in a browser with the network disabled
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
