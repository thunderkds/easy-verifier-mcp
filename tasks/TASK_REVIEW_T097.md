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
| Negative cases hold | ☑ pass | Supervisor probe on `7914444`: a Slack webhook `…/aB3x…`, `AKIA…`, a postgres userinfo password and a `ghp_` token are all still fingerprinted. Implementer negatives: digits-first hex artefact, interleaved, mixed-case, and the 31-letter bound. |
| verify | ☑ pass | Supervisor 2026-10-13: t097 + t029/t051/t053/t091/t095/redaction -> `231 passed in 3.19s`. k8s-ops: 597 tracked paths, and only `bin/build-push-kibana-docker-image` is still changed by `redact()` (an extensionless word name, a different shape; KANBAN 💡). pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | One regex bound (`{1,6}` -> `{1,30}`, both cases) in an entropy exemption, with the residue documented. The two T091/T095 boundary pins were moved from a 7-letter to a 31-letter piece by design: the boundary itself moved under the user-approved fix. Their mixed-case and digits-first twins are unedited. P0 0 · P1 0. |
| Full smoke suite still green (no regression) | ☑ pass (implementer) | `2 failed, 2824 passed, 2 skipped`; the 2 failures are the known container tests. |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Backend only. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Backend only. |
| **UI: Responsiveness at target viewports** | ☑ N/A | Backend only. |
| Repro loop | pass (implementer) | trigger printed ranc…****:bdeabc3ea4ad.yml before; unchanged path after |
| Regression test | pass (implementer) | tests/test_t097_long_letter_digit_pieces.py (6 of 15 failed before the fix) |
| Smoke suite | ☑ pass | Real repos: `redaction_hits_observed` and every rating are unchanged on node-monorepo 11, fullstack-ts 62, nest-api 26, python-ml 28 and this repo 3. On k8s-ops the infrastructure rating stays 100, and 51 → 1 of its tracked paths are changed by `redact()`. |

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
$ (count of tracked paths where redact(p) != p, k8s-ops, via ls-files)
597 tracked; 51 changed
```
(The repo has grown since the guide's 371/50; 51 changed now, one of which, `bin/build-push-kibana-docker-image`, is a separate shape.)

**AFTER**: 2026-10-13T11:35:50Z (implementer)
```
rancher2/cb-ppl/gateway-prod-ingress.yml
k8s-ops: 597 tracked; 1 changed  (bin/build-push-kibana-docker-image, extensionless all-word name, no digits: a different shape, out of scope)
```

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: Supervisor re-ran the redaction test set, secret probes and the k8s-ops path sweep on the branch, 2026-10-13 (event trace T097).
implementing agent alone]
