# TASK_REVIEW — T042: infrastructure dimension (#11/#23/#24)

> Sibling of `tasks/TASK_GUIDE_T042.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t042_infrastructure.py` (23 tests): AC1 discovery, purpose names drift as not verifiable offline, 4 roles; role globs match their files and never source (`src/terraform.service.ts`, `src/k8s/client.go`, `src/main.tf.ts`, `src/template.ts`, `lib/pulumi.py`, ...), DR doc rule never matches `src/restore.service.ts`; AC2 rules cited per area (#11/#23/#24), weights 100, floor 0.25, DR documentation rule (REL13); AC3 module holds no IaC token (`0.0.0.0`, `aws_`, `dynamodb`, `multi_az`, `cidr_blocks`, `verbs`, ...), every generic fact cited; AC5 all rules met rates 100 (DR doc cited), no roles abstains naming all 4 misses, container config alone abstains (never 0). Sabotage pairs: 11 cases, each flips exactly its metric (HCL `actions = ["*"]`, RBAC block-list `- "*"`, CloudFormation JSON `"Action": "*"`, ingress `0.0.0.0/0` while egress/route `0.0.0.0/0` and Istio `hosts: - "*"` stay 0, `storage_encrypted = false` and missing, `backend "local"`, s3 without lock, no env tfvars, no backup, no multi-AZ). Plus s3+`use_lockfile` is locked, `multi_az = var.ha` not counted and named not verifiable offline, no DB resource abstains #24 rules, narrow scope abstains on presence, a secret in a `.tf` is never quoted. |
| Verification command run | ☑ pass | `PYTHONPATH=src .venv/bin/python -m pytest -q` (main-checkout interpreter, container tests against `easy-verifier-mcp:t042` via `COMPOSE_FILE=compose.yaml:<scratchpad>/compose.t042.yaml`, built after the last source change, commit 7ff5f64) → `2340 passed, 2 skipped in 264.48s (0:04:24)`, pytest_exit=0; `ruff check src tests` → `All checks passed!`. `easy-verifier-mcp:0.1.0` untouched (7f5c650966e7 before and after). |
| Negative cases hold | ☑ pass | no roles → `below_coverage_floor` naming terraform-file, k8s-manifest, cloud-template, container-config; container config only → abstains (`all_metrics_abstained` on four real repos), never 0; egress, route `cidr_block` and non-IAM `hosts: - "*"` not counted; variable-valued settings not counted. |
| verify | ☑ pass | Supervisor Stage 5, 2026-10-07 15:43 UTC, commit 0d524e7 — pass: list-dimensions → 13 dims incl. infrastructure; MCP tools/list → 17 tools incl. infrastructure; infrastructure on microservices-demo (shallow public clone, read-only) CLI vs MCP structuredContent identical (parity True), 72 excerpts, sources_missing ['cloud-template']. Independent full-suite re-run (t042 image override): 2340 passed, 2 skipped in 271.60s; ruff All checks passed. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Supervisor Stage 4 code-review over git diff c1b6d73..HEAD: dimensions/infrastructure.py, core roles (terraform-file, k8s-manifest, cloud-template + GENERIC_INFRASTRUCTURE_FACTS)/metrics/metric_tables/judge/improve/report, docs, tests. Role matchers probed (src/manifests/index.ts, src/charts/LineChart.tsx, src/template.yaml.ts → no match). P0/P1/P2 none. P3: k8s-manifest dir names (charts/) also match non-k8s YAML such as web/charts/config.yaml; cloud-template **/template.yaml is broad (SAM convention) — left as is. Weights 20/20/15/15/5/15/10 cited, sum 100, exact-50 exists, accepted under user policy. Security (manual): reads via read_source, regexes linear with 500-char line cap, secrets in .tf never quoted (tested). Pre-existing issues found (not this task): container-config **/k8s/** matches src/k8s/client.go; api breaking-changes metric crashes changes scope on non-code diffs → T083. |
| Full smoke suite still green (no regression) | ☑ pass | full suite 2340 passed, 2 skipped (t042 image); t068 under-cap snapshot regenerated with every existing rating and the overall (61) unchanged; real repos: four abstain with overall unchanged (80/62/56/59). |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | pure backend task, no UI component |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | pure backend task, no UI component |
| **UI: Responsiveness at target viewports** | ☑ N/A | pure backend task, no UI component |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured before any T042 commit (tip c1b6d73), command
`date -u; PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli list-dimensions` (JSON abridged to names):

```
Wed Oct  7 03:09:12 PM UTC 2026
12 ['api', 'architecture', 'blast-radius', 'code-quality', 'data', 'operations', 'reliability', 'requirement-fidelity', 'security', 'solution-fit', 'supply-chain', 'test-strategy']
```

No `infrastructure` entry exists.

**AFTER**: same command on commit 7ff5f64 (names, plus the new dimension's roles):

```
Wed Oct  7 03:37:51 PM UTC 2026
13 ['api', 'architecture', 'blast-radius', 'code-quality', 'data', 'infrastructure', 'operations', 'reliability', 'requirement-fidelity', 'security', 'solution-fit', 'supply-chain', 'test-strategy']
['terraform-file', 'k8s-manifest', 'cloud-template', 'container-config']
```

**DELTA**: A user can now have a repository's Terraform, Kubernetes and CloudFormation files rated for areas #11, #23 and #24 with cited rules (microservices-demo: infrastructure 70), and a repository with no IaC abstains instead of scoring 0.

### Weights (proposed by T042, accepted under user policy 2026-10-07)

| Rule | Area | Weight | Rationale |
|---|---|---|---|
| `iac_wildcard_iam_observed` | #11 | 20 | "*" grants everything; most direct breach path, exact to count |
| `iac_open_ingress_observed` | #11 | 20 | internet-open ingress exposes the service to every attacker |
| `iac_unencrypted_storage_observed` | #11 | 15 | limits a leak's impact rather than preventing access |
| `terraform_locked_remote_state_missing` | #23 | 15 | local/unlocked state is lost or corrupted by concurrent applies |
| `terraform_environment_separation_missing` | #23 | 5 | layout convention from paths and one token; weakest evidence |
| `database_backup_unconfigured` | #24 | 15 | data with no stated backup cannot be restored |
| `database_ha_unconfigured` | #24 | 10 | availability, not data loss, so less than backups |

20 + 15 + 15 rates exactly 50. Floor 0.25 inclusive (user decision 2026-10-07).

### Real repositories (CLI `score --scope project`, 2026-10-07 15:33 UTC, worktree src 7ff5f64)

"Before" = the same run's overall with the infrastructure rating excluded (no other rating changed by this task; ratings average contributors only).

| Repo | Roles found (of 4, floor 0.25) | wildcard IAM | open ingress | unencrypted | locked remote state | env separation | DB backup | DB HA | DR doc | infrastructure | Overall before → after |
|---|---|---|---|---|---|---|---|---|---|---|---|
| microservices-demo (shallow clone 38e7348, untrusted, only `--repo`) | terraform-file, k8s-manifest, container-config (3/4 = 0.75) | 0 | 0 | 0 | 0 (gcs backend, `.github/terraform/main.tf`) | 1 (no env folder/tfvars/workspace in 9 .tf files) | 1 (`terraform/memorystore.tf`, no persistence) | 1 (Basic tier) | missing | **70** | 59 → 60 |
| coffee-shop-api | container-config (1/4 = 0.25) | abstain | abstain | abstain | abstain | abstain | abstain | abstain | missing | abstains `all_metrics_abstained` | 80 → 80 |
| ai-training | container-config (1/4) | abstain | abstain | abstain | abstain | abstain | abstain | abstain | missing | abstains `all_metrics_abstained` | 62 → 62 |
| kitchd | container-config (1/4) | abstain | abstain | abstain | abstain | abstain | abstain | abstain | missing | abstains `all_metrics_abstained` | 56 → 56 |
| bryony | container-config (1/4) | abstain | abstain | abstain | abstain | abstain | abstain | abstain | missing | abstains `all_metrics_abstained` | 59 → 59 |

microservices-demo: 59 IaC files read (9 Terraform + 50 Kubernetes); the k8s-manifest role hit the resolver's 50-file cap (warned), so later `kustomize/components/**` files were not read. A grep of the whole clone shows no `0.0.0.0/0`, no RBAC wildcard and no IAM wildcard, so the zeros are not an artefact of the cap.

### Known limitations

- Only literal values count; a setting from a variable/expression is named as not verifiable offline. The `"*"` IAM search is per line (inline lists, or a lone block-list item under an IAM/RBAC key); a wildcard in the middle of a multi-line list or a policy built by string interpolation is missed (lower bound). `Resource = "*"` counts even where AWS requires it (describe-only actions).
- Open ingress direction is the nearest ingress/egress word within 15 lines above; a GCP firewall that states `direction = "EGRESS"` after `source_ranges` is counted as ingress.
- Remote-state check is repository level: one locked backend passes even if another Terraform root has local state (microservices-demo's `terraform/` has none, `.github/terraform/` has gcs).
- Database rules read Terraform resource blocks only (`aws_db_instance`, `aws_rds_cluster`, `google_sql_database_instance`, `google_redis_instance`); CloudFormation/Pulumi databases are not parsed (cut for scope). "Configured" means stated in code; a provider default (e.g. RDS 1-day retention) is not credited.
- Block extraction counts braces; a heredoc with unbalanced braces can end a block early (bounded to 400 lines).
- KMS key policies and plaintext secrets in IaC are not separate rules (#11 Partial); committed secrets remain the security dimension's.
- Live drift and restore drills are not verifiable offline: no rule, only the DR document is checked.
- Pre-existing, not fixed (out of scope): the shared `container-config` role glob `**/k8s/**` matches source such as `src/k8s/client.go`; and `score --scope changes` crashes with `MetricCitationError: breaking_api_changes_observed (api) reports a value but cites no evidence` when the diff touches no source file (reproduced on base c1b6d73 with a repo whose only change is a `.tfvars`).

**WITNESS**: Supervisor (independent of the implementer), 2026-10-07 15:43 UTC — re-ran list-dimensions, CLI+MCP infrastructure on microservices-demo, and the full suite with active_task=T042.
