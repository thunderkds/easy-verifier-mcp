# TASK_GUIDE — T094: Infrastructure recognises Kubernetes manifests and Compose files by content
**Date**: 2026-10-13
**Complexity Level**: C2
**Risk Level**: Medium (changes which files fill four source roles; infrastructure, operations and reliability read them)
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Apply the C2 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md`
7. Read `docs/ddr/0012-recognize-by-behaviour-and-content-not-names.md` (local, gitignored — read it from the main checkout if the worktree lacks it) and `tasks/TASK_GUIDE_T089.md` (documents recognised by content — the pattern this task follows for YAML)

---

## Requirement (Pillar 1 — Adapt the requirement)

The KANBAN follow-up from T087 says the infrastructure dimension does not read a repo's own Rancher, ELK or Compose YAML. k8s-ops' old "infrastructure 100" came entirely from Harbor files. Once T087 excluded Harbor as third-party, every rating abstains.

The cause is names. `core/roles.py` `GENERIC_PATTERNS`:
- `k8s-manifest` matches YAML only under conventional folders (`k8s/`, `kubernetes/`, `manifests/`, `helm/`, `charts/` and so on) or with names such as `kustomization.yaml` and `Chart.yaml`.
- `container-config` matches Compose only as `compose.y*ml` or `docker-compose*.y*ml`.

So k8s-ops' files fill no role:
- `rancher2/cb/nifi.yml` is a Kubernetes manifest (`apiVersion: apps/v1`, `kind: Deployment`).
- `rancher/scraping.dev.stable.compose.yml` is a Compose v1 file (top-level service names, each with `image:`).

DDR-0012 says to recognise code by behaviour and documents by content, never by names alone.

**Restated intent**:
> A walked `.yml`/`.yaml` file that no name pattern already places, outside third-party exclusions, fills a role by its **content**:
> - **k8s-manifest**: any YAML document in the file (split on `---`) has top-level `apiVersion:` and `kind:` keys.
> - **container-config (Compose)**:
>   - either a top-level `services:` mapping whose entries have an `image:` or `build:` key,
>   - or, for Compose v1, at least one top-level key whose direct child keys include `image:` or `build:`.
> - **cloud-template**: top-level `AWSTemplateFormatVersion:`, or `Resources:` whose entries carry `Type: AWS::…`.
>
> Existing name patterns stay; this only adds what they miss. Precedence: a name match wins, and content fills a role only when the name matched none of these roles. The content check uses the same read limits as other role files and reads each candidate file once.
>
> The infrastructure dimension's existing rule metrics then apply unchanged to these files. A Compose v1 file's `ports:` is read like a v2/v3 one where the rule already reads Compose ports.

**Out of scope**:
- new infrastructure rules or rating changes;
- Rancher-specific `rancher-compose.yml` semantics (it has no `image:`, so it stays unplaced);
- Ansible and Vagrant;
- JSON manifests.

**Requirement Refs**: FR-050, FR-051, FR-052 (infrastructure), FR-076 (content, not names — extended to IaC YAML; add one sentence to FR-076 in `PRD.md`), DDR-0012.

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed (user "yes" 2026-10-13 to "continue with the follow-ups", the follow-up stated as above)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary (source role, third-party exclusion)
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] All Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T087, T089 (merged)

**Entry point**: role resolution in `core/roles.py` (the walk that fills `resolution.files`). The infrastructure, operations and reliability dimensions read `k8s-manifest`, `container-config` and `cloud-template`.

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Temp repo: `ops/app.yml` with `apiVersion: apps/v1` + `kind: Deployment` fills `k8s-manifest`; the same file with `kind:` removed does not | k8s by content |
| 2 | Multi-document YAML (`---`) where only the 2nd document has `apiVersion`+`kind` fills `k8s-manifest` | k8s by content |
| 3 | Temp repo: `deploy/stack.yml` with `services: {web: {image: nginx}}` fills `container-config`; a Compose v1 `stack.dev.yml` (`web: {image: nginx, ports: ["80:80"]}`) fills it too | compose by content |
| 4 | Negative: a CI file, an OpenAPI YAML, a `.eslintrc.yml`, a Helm `values.yaml` without `apiVersion`/`kind`, and a GitHub Actions workflow fill none of these roles | precision |
| 5 | `cloud-template` filled by `AWSTemplateFormatVersion:` or `Resources:` with `Type: AWS::…` content in an arbitrarily named YAML | cfn by content |
| 6 | A name-matched file keeps its role and origin unchanged; payloads of nest-api, fullstack-ts and python-ml are sha256-identical BEFORE/AFTER **unless** a newly placed file is listed and checked by hand as a real manifest/Compose file (paste the list) | no regression |
| 7 | Files under a third-party exclusion (T087 `third_party_filter`) are never content-placed (k8s-ops Harbor stays excluded) | exclusion first |
| 8 | k8s-ops: `infrastructure` no longer abstains; its derivation cites `rancher2/…` manifests and `rancher/…compose.yml` files; any rule metric it reports is cited by file:line. Paste the dimension card before/after | real-repo goal |
| 9 | Content placement adds no second walk and reads each candidate at most once (test: count reads via a context spy) | performance |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | AC 1–5 temp repos | roles filled/not filled as stated | automated tests |
| 2 | k8s-ops | infrastructure rated, cited | real-repo run (background) |
| 3 | nest-api/fullstack-ts/python-ml | sha256 equal or justified list | real-repo run (background) |

### Verification Command (exact, runnable)

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T094.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T094.md`.

BEFORE commands (before any code change; paste timestamped output):
1. k8s-ops `score --scope project </dev/null`, showing the `infrastructure` card abstains;
2. nest-api, fullstack-ts and python-ml `--scope project </dev/null | sha256sum` baselines (background).

---

## UI / Design Acceptance Criteria

> N/A — pure backend task. All three UI Evidence rows are ☐ N/A.

---

## Real repos

Absolute paths: `.local/real-repos.md` (local, git-ignored).

Real repos (read-only, `--repo` only):
- k8s-ops `<real-repos>/k8s-ops`
- node-monorepo `<real-repos>/node-monorepo`
- nest-api `<real-repos>/nest-api`
- fullstack-ts `<real-repos>/fullstack-ts`
- python-ml (path in `memory/learnings.md`)

Run real-repo scores with `run_in_background` and `</dev/null`, using worktree code via `PYTHONPATH=<worktree>/src`.

CLI: `.venv/bin/python -m easy_verifier.adapters.cli score --repo R --scope project </dev/null`.

---

## Approach

**Pattern reference**: T089 `core/documents.py`, where candidates are recognised by content after name matches. Use `scope.third_party_filter` for exclusion.

Keep the YAML recognition as line-based top-level-key checks, with no YAML parser dependency (NFR: no new dependency). A line that starts at column 0 is a top-level key. A child key is the first indented level under it. Put the content predicates beside the generic patterns in `core/roles.py`, or in a small new `core/iac_content.py` if `roles.py` would grow by more than ~80 lines. Smallest change.

Bound reads by the existing per-file read limits. Candidates are walked `.yml`/`.yaml` files that are not name-placed and not excluded.

---

## Edge Case Checklist

- [ ] YAML with BOM / CRLF line endings
- [ ] `apiVersion` only inside a nested block (indented) → not a manifest
- [ ] Compose v1 file whose top-level keys include `version:` only → not Compose
- [ ] Huge YAML (data dump) → read bounded, not placed
- [ ] Kubernetes Secret manifests (`kind: Secret`) → placed; their values still pass through `redact()` in every excerpt

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/roles.py` (or new `core/iac_content.py`) | content predicates; placement after name matching |
| `src/easy_verifier/dimensions/infrastructure.py` | only if a rule must read Compose v1 `ports:` |
| `PRD.md` | one sentence on FR-076 |
| `tests/test_t094_iac_by_content.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `core/redact.py` | T095 in parallel |
| `core/documents.py` | T096 in parallel |
| `core/judge.py` weights / RATING_RULES | no rating change |

---

## Test Plan

Unit tests for each predicate (positive and negative, AC 1–5), role-resolution tests on temp repos (AC 6, 7, 9), and a real-repo run for k8s-ops plus sha256 checks on the other three repos.

## Completion Checklist

- [ ] Implementation done
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T094.md` Evidence (Hard-Stop Gate 5)
- [ ] Real-repo BEFORE/AFTER pasted in Demonstration
- [ ] Supervisor notified: task ready for Stage 4 review
