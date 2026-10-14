# TASK_REVIEW — T095: Redaction masks URL path segments whose pieces are upper-case letters then digits

> Sibling of `tasks/TASK_GUIDE_T095.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass (implementer) | tests/test_t095_upper_digit_pieces.py: 14 passed; 7 of them failed on pre-fix code (trigger line, 5 pieces x URL/suffix, README) |
| Verification command run | ☑ pass (implementer) | pytest: 2 failed, 2742 passed, 2 skipped (the 2 failures are the known stale-Docker-image container tests, tests/integration/test_adapter_parity.py::test_container_parity_is_explicitly_verified and test_redaction_proof.py::test_container_redaction_proof_is_not_silent_when_docker_is_missing, unrelated); ruff check src tests: All checks passed |
| Negative cases hold | ☑ pass | Supervisor probe 2026-10-13, develop vs branch output identical: realistic Slack webhook `…/T024BE7LD/B01ABCD2EFG/aB3x…` still fingerprinted; `AKIA…` still fingerprinted; implementer tests: interleaved, `main-3F9A2B1C.js`, base64url, userinfo, `?token=` still fingerprint. |
| verify | ☑ pass | Supervisor 2026-10-13 on the branch: `test_t095` + t029/t051/t053/t091/redaction tests -> `216 passed in 3.26s`; trigger line survives; README W3C URL kept. pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Supervisor code + security review: one regex (`_LETTER_DIGIT_PIECE`) feeding entropy exemptions only; named detectors untouched; residue (`ABC123-DEF456.txt`) documented in the module docstring; linear pattern, bounded quantifiers (no ReDoS). P0 0 · P1 0. |
| Full smoke suite still green (no regression) | ☑ pass (implementer) | `2 failed, 2742 passed, 2 skipped`; the 2 failures are the known stale-image container tests. |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Backend only. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Backend only. |
| **UI: Responsiveness at target viewports** | ☑ N/A | Backend only. |
| Repro loop | ☑ pass (implementer) | Intake trigger printed `…****:458fc23ebb1e.html` before the fix; the same text now unchanged |
| Regression test | ☑ pass (implementer) | tests/test_t095_upper_digit_pieces.py |
| Smoke suite | ☑ pass | Real repos: security hits bryony 11→11, coffee 26→26, kitchd 62→62, this repo 7→3 (21 vanished hits all `w3.org/WAI/WCAG22/Understanding/*.html`); overall unchanged on all four. |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: (implementer, 2026-10-13T10:19:10Z, worktree at HEAD 278c963, no implementation commit yet)
```
$ PYTHONPATH=src .venv/bin/python -c "from easy_verifier.core.redact import redact; print(redact('See https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html for details'))"
See https://www.w3.org/…****:458fc23ebb1e.html for details
```

**AFTER**: (implementer, post-change)
```
See https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html for details
```

AC 6 real repos, `score --scope project`, security-bearing `redaction_hits_observed` before -> after (overall in brackets):
- bryony: security 11 -> 11 [59 -> 59]
- coffee-shop-api: security 26 -> 26 [81 -> 81]
- kitchd: security 62 -> 62 [56 -> 56]
- this repo: security 7 -> 3, reliability 4 -> 0, architecture 5 -> 1 [43 -> 43]
Hits that disappeared (21 over all tracked files, none new): every one is a w3.org/WAI/WCAG22/Understanding/<slug>.html URL path, in README.md (6), src/easy_verifier/core/judge.py (5), registry/packs/frontend-a11y.toml (2), tasks/TASK_GUIDE_T095.md (2), tasks/TASK_REVIEW_T095.md (1), tests/test_t049_a11y_pack.py (1), tests/test_t095_upper_digit_pieces.py (4). All checked by hand as plain W3C citation paths, not secrets.

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: Supervisor re-ran the trigger and redaction test set on the branch, 2026-10-13 (event trace T095).
implementing agent alone]
