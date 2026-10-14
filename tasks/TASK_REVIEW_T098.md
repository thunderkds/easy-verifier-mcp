# TASK_REVIEW — T098: The score payload discloses capped inputs

> Sibling of `tasks/TASK_GUIDE_T098.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE**: captured by backend-developer on `feat/T098-capped-disclosure` at `2452bcf` (= develop, no
implementation commit yet), 2026-10-14T03:06:56Z-03:07:01Z UTC. Command, from the worktree:
`PYTHONPATH=src <main>/.venv/bin/python -m easy_verifier.adapters.cli score --repo /home/hungnguyenhuu/workspace/project/bryony/scraping-devops </dev/null`
(rc 0), summarised by a read-only JSON script:

```
== scraping  start 2026-10-14T03:06:56Z end 2026-10-14T03:07:01Z rc 0
ratings: {'api': 'abstain:below_coverage_floor', 'architecture': 'abstain:insufficient_measured_weight', 'blast-radius': 'abstain:all_metrics_abstained', 'code-quality': 'abstain:below_coverage_floor', 'data': 'abstain:below_coverage_floor', 'infrastructure': 100, 'operations': 'abstain:below_coverage_floor', 'reliability': 'abstain:all_metrics_abstained', 'requirement-fidelity': 'abstain:below_coverage_floor', 'security': 'abstain:below_coverage_floor', 'solution-fit': 'abstain:no_static_rule', 'supply-chain': 'abstain:below_coverage_floor', 'test-strategy': 'abstain:below_coverage_floor'}
overall: 100
capped key: False None
'exceed the cap' in json: False | 'matched more than' in json: False
```

infrastructure inputs and their `computed_from` sizes:
`[('iac_wildcard_iam_observed', 50), ('iac_open_ingress_observed', 50), ('iac_unencrypted_storage_observed', 50)]`

True role match count with the 50-file role cap lifted (probe: `roles.MAX_ROLE_FILES = 10**6`, then
`roles.resolve(repo, infrastructure.ROLES)`), 2026-10-14T03:08:46Z:
`{'terraform-file': 0, 'k8s-manifest': 197, 'cloud-template': 0, 'container-config': 45}`

So infrastructure is rated 100 from 50 of 197 k8s manifests and the score payload says nothing about it.

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T098.jsonl`, never the
implementing agent alone]
