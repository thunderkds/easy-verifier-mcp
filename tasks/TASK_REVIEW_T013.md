# TASK_REVIEW — T013: report.py — self-contained multi-dimension HTML report

> Sibling of `tasks/TASK_GUIDE_T[NNN].md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t013_report.py` — 43 tests, all written as part of this task, covering all 15 ACs. `PYTHONPATH=src python -m pytest tests/test_t013_report.py -q` → `43 passed in 0.29s` |
| Verification command run | ☑ pass | Full suite in the worktree: `PYTHONPATH=src python -m pytest -q` → `382 passed in 2.87s`. Lint: `ruff check src tests` → `All checks passed!`; `ruff format --check` clean. **Note on the guide's own Verification Command**: its trailing `grep -cE 'https?://\|<script src\|@import'` prints a non-zero count on a report whose *excerpt* quotes a URL — the loose-grep false positive the guide's Test Plan predicted. The real AC #2 check is the parsing scan `_external_references()`, which returns `[]` on the same file and self-tests against a planted `<link>`, `@import` and `<script src>`. The guide's command should be corrected to use the parser. |
| Negative cases hold | ☑ pass | Sabotage checks, each green on the real implementation and **red** when inverted: AC #2 (external `<link>` added → self-containment test fails), AC #5 (`O_EXCL`→`O_TRUNC` → overwrite test fails), AC #6 (bare `pack.coverage_score` rendered → "score outside a coverage entry" fails), AC #9 (write before validate → both tests fail, a file appears), AC #12 (`esc` returns text raw → 4 escaping tests fail; a "helpful" Markdown subset → the Markdown test fails). Three Stage 4/security regressions confirmed red on `4a36513` and `6624901` before their fixes. |
| verify | ☑ pass | `/verify` run by the user against the running app on the merge-equivalent overlay — **pass**. Report rendered into a throwaway repo containing a planted AWS key, then opened in headless Chromium with `--host-resolver-rules="MAP * ~NOTFOUND"`: renders fully, **0** `ERR_`/`net::` events, zero external references. Also driven: crashed dimension renders honestly (no false all-clear); a secret quoted in a finding's title/detail/suggestion renders fingerprinted; invalid finding → `ValidationError` with `reports/` byte-for-byte unchanged; read-only `reports/` and read-only repo → `ReportWriteError` naming the container case, not a traceback; 300 findings → one 152KB document using `<details>`; a 200k-char detail renders without blowing out; symlinked target repo resolves consistently; unicode (`café`, `naïve`, `✅`) intact. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed: `core/report.py` in full, `core/models.py` (the DDR-0004 seam types + `ReportResult`), `tests/test_t013_report.py`. Direct-caller sweep found no adapter reaching `write_report` (recorded as an open P2 below). Skipped: `findings.py` (T006-owned, called not modified — confirmed by the diff), the dimension modules, and `budget.py`. |
| Full smoke suite still green (no regression) | ☑ pass | 382 passed, up from the 339 baseline on `develop`. One pre-existing test in this task's own module was corrected — `test_a_score_of_none_reads_as_nothing_sought_not_as_zero` asserted the fabricated string the P1 fix removed; its real intent ("`None` must not render as `0.0%`") is preserved and it is renamed accordingly. On the merge-equivalent overlay with T012 applied: 407 passed. |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | Renders a static HTML document from structured data — no component, no client-side state, no interaction. Section deleted per `PROJECT_SPEC.md` Critical Constraint 11 and the guide's own note. The rendered page *was* inspected visually at Stage 5 (screenshots captured under `~/ev-verify/`), which is how the coverage P1 was found — but that is runtime verification, not visual-regression tooling against a baseline. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | No design system applies. Visual reference was `templates/report_template.html` (approach only — inlined CSS, dark theme); kit templates were not edited, per Files Must NOT Touch. |
| **UI: Responsiveness at target viewports** | ☐ N/A | Not a responsive UI surface. The document does carry `<meta name="viewport">` and inlines all CSS, but no viewport matrix was defined or required for this task. |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured 2026-08-25T09:53:41Z in worktree `easy-verifier-mcp-t013` at `5d61f46`, before
any implementation commit — `report.py` does not exist and the verification command's test file is
absent, so `write_report` cannot be called at all):

```
$ date -u
Tue Aug 25 09:53:41 AM UTC 2026
$ /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin/python -m pytest tests/test_t013_report.py -q
ERROR: file or directory not found: tests/test_t013_report.py

no tests ran in 0.00s
exit=4
$ ls src/easy_verifier/core/report.py
ls: cannot access 'src/easy_verifier/core/report.py': No such file or directory
exit=2
```

**AFTER** (captured 2026-08-25T10:03:25Z, same worktree, at `6b5d401`+):

```
$ date -u
Tue Aug 25 10:03:25 AM UTC 2026
$ .venv/bin/python -m pytest tests/test_t013_report.py -q
.......................................                                  [100%]
39 passed in 0.34s
exit=0
$ ls -l /tmp/evtest/reports/
-rw-r--r-- 1 hungnguyenhuu hungnguyenhuu 9667 Aug 25 17:00 evidence-report-project-20260825T100038-582758Z.html
```

**DELTA**: A caller can hand validated findings plus a multi-dimension `CombinedPack` to
`write_report` and get one self-contained, collision-proof HTML report written into the *evaluated*
repository's `reports/` — every coverage score shown with its named miss list, every caller-supplied
string escaped, and nothing fetched from the network when the file is opened.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T013.jsonl`, never the
implementing agent alone]

---

## Stage 4 — security-review (T013, Medium risk)

**The built-in `security-review` skill could not run.** It resolves the diff via
`origin/HEAD` and this repository's remote is named `github`, so it aborts with
`fatal: ambiguous argument 'origin/HEAD...'`. This is the **fifth** task blocked by
the same cause (T005, T008 previously recorded it). The Supervisor reviewed the diff
surface directly and drove the attacks below against the running code; substitution
recorded here per the precedent set in `TASK_REVIEW_T008.md`.

**Threat model.** T013 is the first component that writes a durable artifact into a
*third-party* repository, and that artifact renders text an LLM wrote about code it
read. Two egress paths matter: the file itself (committed, ticketed, pasted into a
PR) and, in MCP mode, the same content reaching a possibly-hosted model.

| # | Attack | Result |
|---|---|---|
| 1 | XSS via finding title / detail / suggestion (`<script>alert('xss')</script> & "quoted"`) | **PASS** — rendered as text. Every caller-supplied value in the module routes through `_Ctx.esc`/`_Ctx.path`/`_Ctx.agent_text`; an audit of every f-string interpolation found no unescaped sink. |
| 2 | Markup smuggling via a "helpful" Markdown subset | **PASS** — none offered; pinned by `test_no_markdown_subset_is_honoured`. |
| 3 | Attribute-context injection | **PASS** — no caller value is interpolated into an HTML attribute; `html.escape(quote=True)` regardless. |
| 4 | `confidence` as a free-text sink | **PASS** — validated against the closed `CONFIDENCE_DOMAIN` before rendering. |
| 5 | Report filename pre-planted as a symlink to a victim file outside `reports/` | **PASS** — `os.open(O_CREAT\|O_EXCL)` refuses to follow it, the writer rolls to `-2`, victim byte-identical afterwards. |
| 6 | `reports/` itself a symlink pointing outside the repository | **PASS** — refused with `ReportWriteError`; target directory verified empty (NFR-007). |
| 7 | Container-internal absolute path in a *path field* and in *prose* | **PASS** — both scrubbed (FR-021c); the prose case is what `esc`'s prefix strip covers. |
| 8 | Raw secret in an excerpt | **PASS** — fingerprinted upstream by T004; `AKIA…****:a09e8ab4fd7c` rendered, raw value absent. |
| 9 | **Raw secret quoted in the calling agent's own finding text** | **FAIL → fixed in `9797794`** — see below. |
| 10 | Network egress from the rendered document | **PASS** — opened in headless Chromium with `--host-resolver-rules="MAP * ~NOTFOUND"`; renders fully, zero `ERR_`/`net::` events, zero external references. |

### P1 — secret leak via finding text (fixed, `9797794`)

Excerpts are redacted at the evidence layer before they reach a pack, so quoted code
inherited that protection. **Finding titles, details and suggestions inherited
nothing.** An agent reporting a hardcoded credential routinely quotes it in all three
fields, and a finding written as `Hardcoded key AKIAIOSFODNN7EXAMPLE in app.py` put
the raw value into the written file **three times** — while the engine's own
`redact()` catches that exact string.

This is precisely the risk the guide's T004 blast-radius note names: *"this task is
where redaction stops being precautionary… T013 makes it durable inside someone
else's repository."* Redaction at the pack layer stops being sufficient the moment a
new egress path is added.

Fixed with `_Ctx.agent_text()` (redact → escape), applied to the three caller-authored
free-text fields only. Excerpt text stays on `esc` alone: already redacted upstream, a
second pass would be redundant. Redaction, not suppression — the finding still renders.
Pinned by a test confirmed red on `6624901`, plus a guard that ordinary prose survives.

### Accepted residue

- **TOCTOU between `_guard_reports_dir` and the write.** Containment is checked, then
  `mkdir` and `open` run. An attacker with write access to the *target* repository
  could swap `reports/` for a symlink in that window. `O_CREAT|O_EXCL` still protects
  the final component (attack 5), so the exposure is the directory, not the file. Not
  fixed: the attacker already has write access to the repository being evaluated, so
  this grants nothing they lack, and closing it properly needs `O_DIRECTORY`/`openat`
  plumbing well beyond this task's scope. **Recorded, not hidden.**
- **DDR-0001's premise is now load-bearing.** The unsalted-fingerprint decision rests
  on reports staying inside the evaluated repo. They still do — nothing here transmits
  — but the NFR-011 advisory explicitly tells the reader the file may travel. If a
  future task makes reports travel *by design*, salting must be reconsidered first, as
  the guide's note requires.
