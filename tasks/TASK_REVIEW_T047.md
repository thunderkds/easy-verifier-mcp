# TASK_REVIEW — T047: [Short Title]

> Sibling of `tasks/TASK_GUIDE_T047.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE**: captured on develop f7994d3 (no T047 commit yet) against a scratch git repo with `tests/fixtures/patient.json` = `{"name": "Jane", "ssn": "<SSN-shaped value>"}`. With the pack configured the config is rejected; without the config, #9 ("PHI minimization, retention, test-data safety") and #28 ("Vendor, BAA, data classification, residency") are in `areas_without_rule`:

```text
2026-10-06T05:11:38Z
$ cat .easy-verifier.toml
packs = ["healthcare"]
$ python -m easy_verifier.adapters.cli score --repo <demo>
validation error: .easy-verifier.toml: 1 error(s): packs: unknown key; only [roles] and [conventions] are accepted, and they may only add paths to existing roles or patterns to conventions (no floors, rules or removals)
exit=2

2026-10-06T05:11:44Z
$ python -m easy_verifier.adapters.cli score --repo <demo without .easy-verifier.toml> | jq areas_without_rule
exit=0
.areas_without_rule ["Financial integrity & historical reconstruction", "Data model, constraints, migrations", "Transactions, concurrency, idempotency", "API contracts, validation, versioning", "PHI minimization, retention, test-data safety", "Infra security: IAM, networking, KMS, secrets", "Observability, auditing, SLOs, error budgets", "Accessibility, responsive UX, browser compat", "CI quality & reproducibility", "Artifact provenance, SBOM, signing, promotion, rollback", "Terraform state, environment, account, drift", "Database HA, backups, restore, DR", "Incident response, change mgmt, access review", "Configuration ownership & operational readiness", "Vendor, BAA, data classification, residency", "AI-assisted-development safety", "Developer experience & deterministic local setup"]
```

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T047.jsonl`, never the
implementing agent alone]
