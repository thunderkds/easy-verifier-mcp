# TASK_REVIEW — T097: Redaction masks paths whose name pieces have more than 6 letters before digits

> Sibling of `tasks/TASK_GUIDE_T097.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | pass (implementer) | tests/test_t097_long_letter_digit_pieces.py; with T091/T095: 40 passed |
| Verification command run | pass (implementer), 2 env failures | full pytest: 2 failed, 2824 passed, 2 skipped; the 2 failures are Docker container tests (test_adapter_parity::test_container_parity_is_explicitly_verified, test_redaction_proof::test_container_redaction_proof_is_not_silent_when_docker_is_missing), unrelated to redact; ruff: All checks passed |
| Negative cases hold | ☐ pass / ☐ fail | |
| verify | ☐ pass / ☐ fail / ☐ N/A | [what was observed — must literally state "pass" or "fail" here too, e.g. "skill run, feature confirmed working — pass": the merge gate scans this Notes column for the word "pass", not just the Result column] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [what was reviewed vs. skipped, and why] |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail | |
| **UI: Visual regression (diff or verdict pasted)** | ☐ pass / ☐ fail / ☐ N/A | [screenshot path or LLM verdict — required for UI tasks, Hard-Stop Gate 6] |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ pass / ☐ fail / ☐ N/A | [method used + output] |
| **UI: Responsiveness at target viewports** | ☐ pass / ☐ fail / ☐ N/A | [viewports tested, any overflow findings] |
| Repro loop | pass (implementer) | trigger printed ranc…****:bdeabc3ea4ad.yml before; unchanged path after |
| Regression test | pass (implementer) | tests/test_t097_long_letter_digit_pieces.py (6 of 15 failed before the fix) |
| Smoke suite | ☐ pass / ☐ fail | [bug-specific smoke check beyond the full suite row above] |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured 2026-10-13T11:22:15Z on develop b496ffc, before any implementation commit.
```
$ PYTHONPATH=src python -c "from easy_verifier.core.redact import redact; print(redact('rancher2/cb-ppl/gateway-prod-ingress.yml'))"
ranc…****:bdeabc3ea4ad.yml
$ (count of tracked paths where redact(p) != p, scraping-devops, via ls-files)
597 tracked; 51 changed
```
(The repo has grown since the guide's 371/50; 51 changed now, one of which, `bin/build-push-kibana-docker-image`, is a separate shape.)

**AFTER**: 2026-10-13T11:35:50Z (implementer)
```
rancher2/cb-ppl/gateway-prod-ingress.yml
scraping-devops: 597 tracked; 1 changed  (bin/build-push-kibana-docker-image, extensionless all-word name, no digits: a different shape, out of scope)
```

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T097.jsonl`, never the
implementing agent alone]
