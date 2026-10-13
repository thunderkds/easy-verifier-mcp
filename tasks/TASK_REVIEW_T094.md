# TASK_REVIEW — T094: Infrastructure recognises Kubernetes manifests and Compose files by content

> Sibling of `tasks/TASK_GUIDE_T094.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | pass (implementer) | `tests/test_t094_iac_by_content.py`, 37 tests: `37 passed in 0.62s`. With the predicates present but `resolve()` not yet hooked, 10 of 37 failed (the resolve-level AC 1, 3, 5, 6, 7, 9 tests); before `core/iac_content.py` existed the file failed at import. |
| Verification command run | pass (implementer) | `ruff check src tests`: `All checks passed!`. `pytest -q`: `2 failed, 2809 passed, 2 skipped in 509.03s`; the 2 failures are `tests/integration/test_adapter_parity.py::test_container_parity_is_explicitly_verified` and `tests/integration/test_redaction_proof.py::test_container_redaction_proof_is_not_silent_when_docker_is_missing` (stale local Docker image, `missing=['api','data','infrastructure','operations','supply-chain']`; the known failure on clean develop per MEMORY.md). |
| Negative cases hold | pass (implementer) | GitLab CI, CircleCI, GitHub Actions, OpenAPI, `.eslintrc.yml`, Helm `values.yaml`, `rancher-compose.yml` classify as nothing and fill no role in a repo; `apiVersion` nested, `kind` missing, `version:`-only, `image` two levels down, Resources without `AWS::`, a 4 MB dump with the manifest past 256 KB: not placed. |
| verify | ☐ pass / ☐ fail / ☐ N/A | [what was observed — must literally state "pass" or "fail" here too, e.g. "skill run, feature confirmed working — pass": the merge gate scans this Notes column for the word "pass", not just the Result column] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [what was reviewed vs. skipped, and why] |
| Full smoke suite still green (no regression) | pass (implementer), except the 2 stale-Docker failures above | coffee, kitchd and ai-training payloads sha256-identical before/after; bryony ratings identical, payload differs only in file/line counts (3 Compose files newly placed, listed in the report). |
| **UI: Visual regression (diff or verdict pasted)** | N/A | [screenshot path or LLM verdict — required for UI tasks, Hard-Stop Gate 6] |
| **UI: Design-system compliance (tokens/colors/typography verified)** | N/A | [method used + output] |
| **UI: Responsiveness at target viewports** | N/A | [viewports tested, any overflow findings] |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (implementer, 2026-10-13T11:04Z-11:05Z UTC, worktree HEAD `0390b3a`, no implementation commit yet; command per repo:
`PYTHONPATH=<worktree>/src .venv/bin/python -m easy_verifier.adapters.cli score --repo <R> --scope project </dev/null`, background):

scraping-devops (overall: `rating_abstention no_dimension_rated`; every dimension abstains). Infrastructure card:
```
infrastructure rating_abstention all_metrics_abstained, achieved_coverage 0.25, floor 0.25
sources_missing: terraform-file / k8s-manifest / cloud-template: "not found: no file in the repository matched this role's patterns"
unavailable_metrics (all 7): iac_wildcard_iam_observed, iac_open_ingress_observed, iac_unencrypted_storage_observed
  -> "no Terraform file, Kubernetes manifest or CloudFormation/Pulumi template in scope, so there is no infrastructure code to examine"
  terraform_locked_remote_state_missing, terraform_environment_separation_missing, database_backup_unconfigured, database_ha_unconfigured
```
Other repos, overall / architecture (matches the stated develop baselines), with payload sha256:
```
kitchd  56 / 100  e54e9bb5cce80c820fe20559b25d82af60abbc6f22653c36ea6f9ec3cbefae27
bryony  59 / 83   7037a217730e260c3d458c80794d4f05f16b4ffdd78bcba1d47c14a28b7634d3
coffee  81 / 90   4ba27c3328c02104df8c8b76cda8598305bc70ee50319d787206f669edbc08d5
ai      64 / 83   7edde78145b50a701279a35342298510f5236c2ac25904fda02636528b893db9
scraping-devops   0927d37e1aad96b381a6f64d49219dea9bb66701f8cde6b9bd71ff38485b8b8a
```
(infrastructure abstains on all four others too: all_metrics_abstained, coverage 0.25.)

**AFTER** (implementer, 2026-10-13T11:08Z-11:09Z UTC, same command, worktree code):
```
scraping-devops: overall 100 (only infrastructure is rated)
infrastructure rating 100: iac_wildcard_iam_observed 0 (w20, at_most 0, passed), iac_open_ingress_observed 0 (w20, passed),
  iac_unencrypted_storage_observed 0 (w15, passed); each computed_from 50 rancher2/... manifests (the 50-file role cap, shallowest first;
  hand check: 197 manifests, grep for 0.0.0.0/0, "*" verbs/resources/Action, encrypted: false finds nothing outside harbor)
  4 Terraform/database metrics still unavailable ("no Terraform file in scope")
kitchd / coffee / ai-training payload sha256 identical to BEFORE; bryony overall 59, every rating identical.
```

**DELTA**: a repo's own Kubernetes manifests, Compose files (v1 and v2/v3) and CloudFormation templates are read by the infrastructure dimension whatever their folder or file name, so scraping-devops is rated instead of abstaining.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T094.jsonl`, never the
implementing agent alone]
