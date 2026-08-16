# TASK_REVIEW — T004: redact.py — evidence-layer secret fingerprinting

> Sibling of `tasks/TASK_GUIDE_T004.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t004_redact.py` — 53 tests written as part of T004, covering AC #1–#10. Includes the AC #5 DEBUG-logging capture, the AC #6 exception-message test parameterised over all three `collect` shapes, AC #2's assertion that no salt is read from config/env/disk, and AC #7's cross-file fingerprint-stability check. Supporting fixture changes in `tests/conftest.py`; `tests/test_t001_pipeline.py` updated for the widened `_budget` return. Output:<br>`$ pytest tests/test_t004_redact.py -q -p no:randomly`<br>`..... [100%]`<br>`53 passed in 0.06s` |
| Verification command run | ☑ pass | Exact command from the guide, run by the Supervisor in the T004 worktree:<br>`$ CLAUDE_ACTIVE_TASK=T004 PATH=.venv/bin:$PATH python -m pytest tests/test_t004_redact.py -q -p no:randomly`<br>`53 passed in 0.06s` |
| Negative cases hold | ☑ pass | Confirmed by direct execution, not inspection. Ordinary prose is untouched (`the secret sauce is good documentation` → 0 hits), and this repo's own absolute paths survive unfingerprinted (`/home/…/easy-verifier-mcp/src/x.py` → 0 hits) — the `_PATHISH` and mixed-char-class rules that keep the tool usable when it evaluates itself. Empty string and whitespace-only input return unchanged with 0 hits. Surrogate/non-UTF-8 bytes adjacent to a match do not raise (`surrogatepass` on encode). Two **confirmed misses** are recorded as P2 findings below rather than hidden. |
| verify | ☑ pass | Supervisor re-ran the suite independently in the worktree — feature confirmed working, redaction observed end-to-end on a seeded repo — **pass**. Full suite: `102 passed in 0.24s`. Lint clean: `ruff check src/ tests/` → `All checks passed!` (one E501 introduced during review was fixed in `d7f9609`). |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed: `core/redact.py`, `core/pipeline.py`, `core/models.py` and their direct tests — the files in `git diff 9f10d7f^..HEAD` touching product code. Skipped: all 17 TASK_GUIDEs, templates, and memory files present in the branch diff (planning artifacts, not this task's change), and `dimensions/architecture.py` (unmodified by T004; consumes the seam without changing it). |
| Full smoke suite still green (no regression) | ☑ pass | `$ CLAUDE_ACTIVE_TASK=T004 PATH=.venv/bin:$PATH python -m pytest tests/ -q`<br>`102 passed in 0.21s` — includes T001's pipeline suite and T001's LLM-marker scan, both green after `_budget`'s signature widened to return redaction hits. |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | Pure-backend task. T004 touches only `core/`; no UI component exists in this repo yet (HTML report rendering is T013). |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | As above — no UI surface in T004. |
| **UI: Responsiveness at target viewports** | ☐ N/A | As above — no UI surface in T004. |

### Stage 4 skill results

| Skill | Result |
|---|---|
| `code-review` | P0 **0** / P1 **0** / P2 **2** / P3 **2**. Both P2s share one root cause — material below *both* detector floors. (a) `password=hunter2 and then some prose` → 0 hits: the `credential_assignment` lookahead requires the value to end at EOL/delimiter/comment; admitted in a module comment but not pinned by a test. (b) `Bearer abcdefghijklmnopqrst` (single char-class, 20 chars) → 0 hits: falls between `_KEY_MATERIAL_CLASSES` (needs lower+upper+digit) and `_ENTROPY_CANDIDATE` (needs ≥32 chars); not documented anywhere. P3s: `sources_sought`/`sources_found` discard their redaction hits via `[0]` while `files_read` keeps them (cannot leak — those are first-party static descriptor strings — but the asymmetry is silent); and `RedactionHit.line` is file-absolute while `offset` stays excerpt-relative after remapping. No P0/P1, so no auto-fixes applied. |
| `security-review` | **0 HIGH, 0 MEDIUM.** No network I/O, subprocess, SQL, deserialization, `eval`, or template rendering in the diff — most categories are structurally inapplicable. The detector misses were considered and deliberately *not* raised as security findings: T004 replaces an identity passthrough, so the change is strictly a net reduction in exposure, and incomplete coverage of a newly added control is not a newly introduced vulnerability. Unsalted fingerprinting was considered and holds on its recorded premise (reports stay inside the evaluated repo, where the raw value is already greppable). |
| `blast-radius` | No PII/PHI/payment data and no data-subject population, so GDPR/CCPA/HIPAA per-record models are **not applicable**; fabricated figures were deliberately not produced. The real exposure is transited third-party data: **top vector is the evidence pack reaching a hosted LLM via the calling agent** — NFR-012's local-only transport protects the wire, not the destination, and T004 is the only control on that path. Second vector is T013 writing reports into the target repo, which is exactly the premise the unsalted-fingerprint decision rests on. Top hardening item: keep T013 blocked behind T004. |

### Open follow-ups (non-blocking)

- The two P2 detector misses: close them, or pin them with tests as accepted residue. Recommend the latter for (a) — the anchor exists to stop false positives when the tool evaluates its own docs — and documenting (b) alongside it.
- `blast-radius` recommends NFR-011's first-write advisory explicitly name the "pack may reach a hosted model" vector, not merely state that redaction occurred. Belongs to T013.

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** — captured `2026-08-16 03:23:23Z` by running the pre-T004 `redact()` body (verbatim from
`git show 9f10d7f^:src/easy_verifier/core/redact.py`, whose docstring reads *"SEAM ONLY — identity
passthrough until T004"*) over a seeded `.env`:

```
$ python -c "... redact = lambda t: t ...; print(redact(open('repo/.env').read()))"
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
DATABASE_URL=postgres://svc:pB4kQ9zXmR7t@db.internal/prod
```

Every credential passes through verbatim — this is the state the Kanban recorded as *"evidence packs
can contain live secrets."*

**AFTER** — same input, same timestamp, T004's `scan()`:

```
$ python -c "from easy_verifier.core.redact import scan; r=scan(open('repo/.env').read()); print(r.text)"
AWS_ACCESS_KEY_ID=AKIA…****:1a5d44a2dca1
aws_secret_access_key=wJal…****:78314b11be2e
DATABASE_URL=postgres://svc:pB4k…****:df64c9a7ff9a@db.internal/prod

hits: [('aws_access_key_id', 1), ('aws_secret_access_key', 2), ('key_material_segment', 3)]
```

Note the third line: the password sits **inside a connection URI**, where no `key=value` anchor
exists. It is caught because `_KEY_MATERIAL_CANDIDATE` is path-blind by design and judges each
segment between separators on its own — while `db.internal/prod` stays readable, so the finding
remains actionable.

**DELTA**: Evidence leaving the engine can no longer carry a live credential. A user can now point
the tool at a repo holding real secrets and share the output — pack, log, report, or exception
message — without disclosing them, and can still correlate "this same key appears in three files"
because the fingerprint is stable.

**WITNESS**: Supervisor, `2026-08-16 03:23Z` — implementation and tests by the backend-developer
agent across commits `0626a84`…`8105a8b`; the eager-`collect()` hardening (`78fc723`), the E501 fix
(`d7f9609`), and all Stage 4/5 verification, negative-case probing, and the BEFORE/AFTER capture
above run independently by the Supervisor in the main session, not by the implementing agent.
