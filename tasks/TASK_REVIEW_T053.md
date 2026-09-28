# TASK_REVIEW — T053: Remaining redaction noise + API_TOKEN detector gap

> Sibling of `tasks/TASK_GUIDE_T053.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE** (captured 2026-09-28T12:54Z on `feat/T053-redaction-noise` @ `7de1e21`, before any T053 implementation commit; backend-developer):

Command, per repo (stdin closed; worktree `src` on PYTHONPATH, main-checkout venv):
```
cd <worktree> && PYTHONPATH=src <main>/.venv/bin/python -m easy_verifier.adapters.cli score --repo <repo> --scope project </dev/null > before/<name>.json
```
Run log (UTC; repo HEAD; exit code) and security `redaction_hits_observed` extracted from each JSON:
```
worktree HEAD 7de1e21
2026-09-28T12:54:11Z start easy-verifier-mcp 7de1e21
2026-09-28T12:54:12Z end easy-verifier-mcp exit=0
2026-09-28T12:54:12Z start kitchd 872cc92
2026-09-28T12:54:14Z end kitchd exit=0
2026-09-28T12:54:14Z start bryony 8df7b986f
2026-09-28T12:54:21Z end bryony exit=0
2026-09-28T12:54:21Z start ai-training 86c98d5
2026-09-28T12:54:22Z end ai-training exit=0
easy-verifier-mcp {'redaction_hits_observed': 19} security rating: 50
kitchd {'redaction_hits_observed': 59} security rating: 60
bryony {'redaction_hits_observed': 14} security rating: 60
ai-training {'redaction_hits_observed': 31} security rating: 60
```
Every hit in each security pack (`run_dimension(security, repo, "project")`; path:line detector fingerprint — never raw values):
```
[easy-verifier-mcp] hits=19 by detector=[('high_entropy_string', 11), ('key_material_segment', 5), ('credential_assignment', 2), ('aws_access_key_id', 1)]
  CLAUDE.md:128 high_entropy_string docs…****:3bda998323af
  CLAUDE.md:128 high_entropy_string docs…****:3bda998323af
  CLAUDE.md:152 high_entropy_string Comm…****:fb6035c79266
  PROJECT_KANBAN.md:62 key_material_segment easy…****:4f53ff0a00e7
  PROJECT_KANBAN.md:63 key_material_segment easy…****:34de13ddd1fc
  PROJECT_KANBAN.md:64 key_material_segment easy…****:d86ad9bc15b6
  README.md:128 high_entropy_string 0/do…****:a4f7f44d1d6a
  README.md:128 high_entropy_string 0/do…****:a4f7f44d1d6a
  README.md:130 high_entropy_string 0/do…****:a4f7f44d1d6a
  README.md:130 high_entropy_string 0/do…****:a4f7f44d1d6a
  memory/learnings.md:139 aws_access_key_id AKIA…****:1a5d44a2dca1
  scripts/vendor_sources.py:58 high_entropy_string OWAS…****:e1b0aefbf060
  scripts/vendor_sources.py:62 high_entropy_string OWAS…****:e1b0aefbf060
  src/easy_verifier/core/judge.py:95 high_entropy_string OWAS…****:e1b0aefbf060
  src/easy_verifier/core/metric_tables.py:125 credential_assignment toke…****:3c469e9d6c58
  src/easy_verifier/core/redact.py:8 key_material_segment FAKE…****:5252c44014f7
  src/easy_verifier/core/redact.py:137 credential_assignment hunt…****:f52fbd32b2b3
  src/easy_verifier/core/redact.py:163 key_material_segment FAKE…****:5252c44014f7
  src/easy_verifier/core/redact.py:189 high_entropy_string BRAI…****:54e5675171d4
[kitchd] hits=59 by detector=[('high_entropy_string', 22), ('credential_assignment', 18), ('key_material_segment', 18), ('high_entropy_hex', 1)]
  pnpm-lock.yaml:145 high_entropy_hex de2b…****:3333781a5f84
  apps/api/src/auth/auth.e2e.spec.ts:39 credential_assignment corr…****:622493693890
  apps/api/src/auth/auth.e2e.spec.ts:65 credential_assignment corr…****:622493693890
  apps/api/src/auth/auth.e2e.spec.ts:100 credential_assignment corr…****:622493693890
  apps/api/src/auth/auth.e2e.spec.ts:113 credential_assignment corr…****:622493693890
  apps/api/src/auth/auth.e2e.spec.ts:121 credential_assignment wron…****:6786324d7148
  apps/api/src/auth/auth.e2e.spec.ts:134 credential_assignment corr…****:622493693890
  apps/api/src/auth/auth.e2e.spec.ts:144 credential_assignment corr…****:622493693890
  apps/api/src/auth/guards/jwt-auth.guard.spec.ts:15 credential_assignment test…****:9caf06bb4436
  apps/api/src/auth/guards/jwt-auth.guard.ts:21 credential_assignment this…****:02df8ee47c46
  apps/api/src/auth/guards/jwt-auth.guard.ts:40 credential_assignment unde…****:eb045d78d273
  packages/shared/src/auth.dto.ts:5 credential_assignment stri…****:473287f8298d
  packages/shared/src/auth.dto.ts:12 credential_assignment stri…****:473287f8298d
  apps/api/src/kitchens/kitchens-rbac.e2e.spec.ts:38 credential_assignment corr…****:622493693890
  apps/api/src/kitchens/kitchens-rbac.e2e.spec.ts:66 credential_assignment invi…****:3fda7191ae55
  apps/api/src/kitchens/kitchens-rbac.e2e.spec.ts:66 credential_assignment memb…****:0f0a12ce80c2
  apps/api/src/rbac-audit/rbac-matrix.e2e.spec.ts:51 credential_assignment corr…****:622493693890
  apps/api/src/rbac-audit/rbac-matrix.e2e.spec.ts:79 credential_assignment invi…****:3fda7191ae55
  apps/api/src/rbac-audit/rbac-matrix.e2e.spec.ts:79 credential_assignment memb…****:0f0a12ce80c2
  repo…****:e808c802ee27.html:1 high_entropy_string repo…****:e808c802ee27
  repo…****:e808c802ee27.html:5 key_material_segment T019…****:c69625c8230c
  repo…****:e808c802ee27.html:172 key_material_segment T019…****:c69625c8230c
  repo…****:4d10b85626cf.html:1 high_entropy_string repo…****:4d10b85626cf
  repo…****:4d10b85626cf.html:5 key_material_segment T001…****:5c93152897b9
  repo…****:4d10b85626cf.html:172 key_material_segment T001…****:5c93152897b9
  repo…****:c1e88fe3b79e.html:1 high_entropy_string repo…****:c1e88fe3b79e
  repo…****:c1e88fe3b79e.html:5 key_material_segment T008…****:b14f995e21e7
  repo…****:c1e88fe3b79e.html:172 key_material_segment T008…****:b14f995e21e7
  repo…****:80b8e26427f3.html:1 high_entropy_string repo…****:80b8e26427f3
  repo…****:80b8e26427f3.html:5 high_entropy_string task…****:c73c56dd7956
  repo…****:80b8e26427f3.html:172 high_entropy_string task…****:c73c56dd7956
  repo…****:733ce35941d0.html:1 high_entropy_string repo…****:733ce35941d0
  repo…****:733ce35941d0.html:5 key_material_segment T015…****:5219e84d5507
  repo…****:733ce35941d0.html:172 key_material_segment T015…****:5219e84d5507
  repo…****:9a2cc977475d.html:1 high_entropy_string repo…****:9a2cc977475d
  repo…****:9a2cc977475d.html:5 key_material_segment T019…****:c69625c8230c
  repo…****:9a2cc977475d.html:172 key_material_segment T019…****:c69625c8230c
  repo…****:60e7365a9573.html:1 high_entropy_string repo…****:60e7365a9573
  repo…****:60e7365a9573.html:5 key_material_segment T027…****:112d0072ee96
  repo…****:60e7365a9573.html:172 key_material_segment T027…****:112d0072ee96
  repo…****:7131be7be111.html:1 high_entropy_string repo…****:7131be7be111
  repo…****:7131be7be111.html:5 key_material_segment T039…****:022c6201c8ff
  repo…****:7131be7be111.html:181 key_material_segment T039…****:022c6201c8ff
  repo…****:f16d4e14804c.html:1 high_entropy_string repo…****:f16d4e14804c
  repo…****:f16d4e14804c.html:5 key_material_segment T040…****:483b0d2ad989
  repo…****:f16d4e14804c.html:181 key_material_segment T040…****:483b0d2ad989
  repo…****:5bdb8e4dda09.html:1 high_entropy_string repo…****:5bdb8e4dda09
  repo…****:5bdb8e4dda09.html:5 key_material_segment T043…****:c0dd93e6c79b
  repo…****:5bdb8e4dda09.html:181 key_material_segment T043…****:c0dd93e6c79b
  repo…****:e808c802ee27.html:1 high_entropy_string repo…****:e808c802ee27
  repo…****:4d10b85626cf.html:1 high_entropy_string repo…****:4d10b85626cf
  repo…****:c1e88fe3b79e.html:1 high_entropy_string repo…****:c1e88fe3b79e
  repo…****:80b8e26427f3.html:1 high_entropy_string repo…****:80b8e26427f3
  repo…****:733ce35941d0.html:1 high_entropy_string repo…****:733ce35941d0
  repo…****:9a2cc977475d.html:1 high_entropy_string repo…****:9a2cc977475d
  repo…****:60e7365a9573.html:1 high_entropy_string repo…****:60e7365a9573
  repo…****:7131be7be111.html:1 high_entropy_string repo…****:7131be7be111
  repo…****:f16d4e14804c.html:1 high_entropy_string repo…****:f16d4e14804c
  repo…****:5bdb8e4dda09.html:1 high_entropy_string repo…****:5bdb8e4dda09
[bryony] hits=14 by detector=[('high_entropy_hex', 7), ('credential_assignment', 4), ('high_entropy_string', 2), ('key_material_segment', 1)]
  nodes/package.json:29 key_material_segment BSD-…****:248dd895a2f8
  frontend/app/scripts/modules/auth/views/register.itemview.js:19 credential_assignment #pas…****:a9ca1573cef4
  frontend/app/scripts/modules/auth/views/register.itemview.js:101 credential_assignment this…****:fcad7430e71a
  backend/server/dashboard/authenticate.js:41 credential_assignment quer…****:12d09cfeec1f
  CHANGELOG.md:9 high_entropy_hex 5dad…****:c7dce6c9ce19
  CHANGELOG.md:15 high_entropy_hex 61d3…****:1435d5caead0
  CHANGELOG.md:25 high_entropy_hex ec0d…****:d77f64a8c89c
  backend/Gruntfile.js:77 high_entropy_hex 6b88…****:42332d012db5
  backend/Gruntfile.js:84 credential_assignment sona…****:48ce1a75f189
  backend/bin/ec2/fabric/fabfile.py:19 high_entropy_string ssh/…****:d13e7d3f0968
  backend/bin/ec2/fabric/fabfile.py:129 high_entropy_hex 5edf…****:d2f648993e74
  backend/bin/ec2/fabric/fabfile.py:148 high_entropy_hex 5edf…****:d2f648993e74
  backend/bin/fabric/fabfile.py:29 high_entropy_string ssh/…****:d13e7d3f0968
  backend/bin/fabric/fabfile.py:188 high_entropy_hex 5edf…****:d2f648993e74
[ai-training] hits=31 by detector=[('high_entropy_string', 24), ('credential_assignment', 7)]
  src/core/llm/factory.py:164 credential_assignment sett…****:7a417f6aeac4
  src/core/llm/factory.py:180 credential_assignment sett…****:7a417f6aeac4
  src/core/llm/factory.py:196 credential_assignment sett…****:fd8e43297e05
  src/core/observability/langfuse.py:54 credential_assignment str…****:8c25cb368646
  src/core/observability/langfuse.py:66 credential_assignment sett…****:f0adf194c81b
  src/core/observability/langfuse.py:104 credential_assignment reso…****:afe323a3d0c5
  src/core/profile/extraction.py:137 high_entropy_string cont…****:deed5ccff74a
  src/core/subgraphs/fitness/planner.py:155 high_entropy_string cont…****:bd58f154ce1d
  src/core/subgraphs/fitness/template_registry.py:60 high_entropy_string sess…****:cf21321ce3cb
  src/core/subgraphs/research/research_agent.py:113 credential_assignment set_…****:4ce698f2e665
  src/core/subgraphs/research/research_agent.py:144 high_entropy_string cont…****:f7cd178577aa
  src/docs/ragas-evaluation.md:61 high_entropy_string VERI…****:bf883de7139a
  src/docs/ragas-evaluation.md:64 high_entropy_string VERI…****:bf883de7139a
  tests/test_fitness_planner.py:170 high_entropy_string stru…****:a1b4317b6b6e
  tests/test_llm_factory.py:16 high_entropy_string plan…****:fd2215214350
  tests/test_llm_factory.py:34 high_entropy_string plan…****:1719153cf389
  tests/test_llm_payload_contracts.py:39 high_entropy_string plan…****:fd2215214350
  tests/test_llm_payload_contracts.py:47 high_entropy_string plan…****:1719153cf389
  tests/test_llm_payload_contracts.py:88 high_entropy_string plan…****:fd2215214350
  tests/test_llm_payload_contracts.py:96 high_entropy_string plan…****:1719153cf389
  tests/test_llm_payload_gates.py:30 high_entropy_string plan…****:fd2215214350
  tests/test_llm_payload_gates.py:38 high_entropy_string plan…****:1719153cf389
  tests/test_llm_serializers.py:29 high_entropy_string plan…****:fd2215214350
  tests/test_llm_serializers.py:37 high_entropy_string plan…****:1719153cf389
  tests/test_planning_agent.py:12 high_entropy_string plan…****:fd2215214350
  tests/test_planning_agent.py:22 high_entropy_string plan…****:1719153cf389
  tests/test_rate_limit_api.py:18 high_entropy_string rate…****:59dfe3918dfb
  tests/test_research_agent.py:34 high_entropy_string plan…****:fd2215214350
  tests/test_research_agent.py:52 high_entropy_string plan…****:1719153cf389
  tests/test_research_payload.py:15 high_entropy_string plan…****:fd2215214350
  tests/test_research_payload.py:23 high_entropy_string plan…****:1719153cf389
```
Tracked-file sweep of this repo (`git ls-files`, every UTF-8 file through `scan`; sample = first 3 hits per file, lines shown already redacted):
```
[sweep /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp-T053] tracked files=252 total hits=529 files with hits=53
 by detector: [('high_entropy_string', 422), ('credential_assignment', 45), ('key_material_segment', 39), ('high_entropy_hex', 11), ('aws_access_key_id', 10), ('aws_secret_access_key', 1), ('jwt', 1)]
 by file: [('src/easy_verifier/registry/vendored/asvs.json', 346), ('tests/test_t004_redact.py', 35), ('tasks/TASK_REVIEW_T016.md', 18), ('tests/test_t005_budget.py', 10), ('tests/test_t051_redaction_false_positives.py',
  CLAUDE.md:128 high_entropy_string | See [`docs…****:3bda998323af.md`](docs…****:3bda998323af.md) for full Step 1 / Step 1.5 (Ambiguity Resolution Protocol) / Step 2 detail.
  CLAUDE.md:128 high_entropy_string | See [`docs…****:3bda998323af.md`](docs…****:3bda998323af.md) for full Step 1 / Step 1.5 (Ambiguity Resolution Protocol) / Step 2 detail.
  CLAUDE.md:152 high_entropy_string | - **Stage 1.5** (Sub-Agent Architecture): design the sub-agent team; base team is always Comm…****:fb6035c79266; `Skill({ skill: "craft-agent" })` onl
  PROJECT_KANBAN.md:62 key_material_segment | - [~] **T053** — Remaining redaction noise (versioned URL paths, commit SHAs, checksum lines) + API_TOKEN detector gap (T051 follow-up) | backend-deve
  PROJECT_KANBAN.md:63 key_material_segment | - [~] **T052** — Make requirement-fidelity and blast-radius rate: AC tracing + churn-hotspot evidence (T035 sign-off follow-up) | backend-developer |
  PROJECT_KANBAN.md:64 key_material_segment | - [~] **T037** — MCP reference gate: framework detection + `needs_input` for missing fields only (≤20) | backend-developer | C2 | Risk: Med | P1 | 🔄 s
  README.md:128 high_entropy_string | | `security` | `redaction_hits_observed` | ≤ 0 | 40 | [CWE-798 Use of Hard-coded Credentials](https://cwe.mitre.org/data/definitions/798.html); [OWASP
  README.md:128 high_entropy_string | | `security` | `redaction_hits_observed` | ≤ 0 | 40 | [CWE-798 Use of Hard-coded Credentials](https://cwe.mitre.org/data/definitions/798.html); [OWASP
  README.md:130 high_entropy_string | | `security` | `lockfile_missing` | ≤ 0 | 20 | [OWASP ASVS 5.0.0 V15.1.2 (third-party component inventory)](https://github.com/OWASP/ASVS/blob/v5.0.0_
  memory/learnings.md:139 aws_access_key_id | run_dimension(DESCRIPTOR, "/nonexistent/AKIA…****:1a5d44a2dca1/repo")
  scripts/vendor_sources.py:58 high_entropy_string | "OWAS…****:e1b0aefbf060.0.0_en.flat.json"
  scripts/vendor_sources.py:62 high_entropy_string | "OWAS…****:e1b0aefbf060.0.0_en.json"
  scripts/vendor_sources.py:311 high_entropy_string | ling…****:88781611f7e7,
  src/easy_verifier/core/judge.py:95 high_entropy_string | "OWAS…****:e1b0aefbf060.0.0_en.json"
  src/easy_verifier/core/metric_tables.py:125 credential_assignment | token=toke…****:3c469e9d6c58,
  src/easy_verifier/core/metric_tables.py:257 credential_assignment | def token_regex(token: str…****:8c25cb368646) -> str:
  src/easy_verifier/core/metrics.py:276 credential_assignment | token: str…****:8c25cb368646
  src/easy_verifier/core/models.py:342 high_entropy_string | ``repo…****:51117f288d24.html``.
  src/easy_verifier/core/redact.py:8 key_material_segment | FAKE…****:5252c44014f7  ->  FAKE…****:a3f9c2e18b04
  src/easy_verifier/core/redact.py:137 credential_assignment | # whether `password=hunt…****:f52fbd32b2b3  # dev` was covered elsewhere: it was
  src/easy_verifier/core/redact.py:163 key_material_segment | (`/home/user/keys/FAKE…****:5252c44014f7` still fingerprints), and
  src/easy_verifier/core/scope.py:42 high_entropy_hex | _EMPTY_TREE = "4b82…****:abe5b4848301"
  src/easy_verifier/core/tokens.py:189 credential_assignment | token = matc…****:7b72b24b7a0d)
  src/easy_verifier/dimensions/blast_radius.py:387 credential_assignment | ordered = sorted(tokens, key=lambda token: (-le…****:2cbf685d3855), token))
  src/easy_verifier/dimensions/security.py:295 high_entropy_string | SINK_CAP_WARNING.format(path=path, limi…****:fb2621026f7e),
  src/easy_verifier/registry/curated/php.toml:25 high_entropy_string | citation_url = "https://github.com/…****:832c5b7ddcbf"
  src/easy_verifier/registry/vendored/CHECKSUMS.sha256:1 high_entropy_hex | 154e…****:0f16bae84382  NOTICE
  src/easy_verifier/registry/vendored/CHECKSUMS.sha256:2 high_entropy_hex | 275f…****:345da886d432  asvs.json
  src/easy_verifier/registry/vendored/CHECKSUMS.sha256:3 high_entropy_hex | 842d…****:0c961fcf2ea7  cwe.json
  src/easy_verifier/registry/vendored/NOTICE:6 high_entropy_hex | Source:  https://raw.githubusercontent.com/github-linguist/linguist/d092…****:13f24cee0fe0/lib/linguist/languages.yml
  src/easy_verifier/registry/vendored/NOTICE:7 high_entropy_hex | Pinned:  commit d092…****:13f24cee0fe0
  src/easy_verifier/registry/vendored/NOTICE:12 high_entropy_string | Source:  https://raw.githubusercontent.com/OWASP/ASVS/v5.0.0_release/5.0/do…****:a4f7f44d1d6a.0.0_en.flat.json
  src/easy_verifier/registry/vendored/asvs.json:8 high_entropy_string | "source_url": "https://raw.githubusercontent.com/OWASP/ASVS/v5.0.0_release/5.0/do…****:a4f7f44d1d6a.0.0_en.flat.json"
  src/easy_verifier/registry/vendored/asvs.json:15 high_entropy_string | "url": "https://github.com/OWASP/ASVS/blob/v5.0.0_release/5.0/do…****:a4f7f44d1d6a.0.0_en.json"
  src/easy_verifier/registry/vendored/asvs.json:21 high_entropy_string | "url": "https://github.com/OWASP/ASVS/blob/v5.0.0_release/5.0/do…****:a4f7f44d1d6a.0.0_en.json"
  src/easy_verifier/registry/vendored/linguist.json:10 key_material_segment | "2-Di…****:d5fb98afc34e Array": {
  src/easy_verifier/registry/vendored/linguist.json:6401 high_entropy_hex | "source_url": "https://raw.githubusercontent.com/github-linguist/linguist/d092…****:13f24cee0fe0/lib/linguist/languages.yml"
  tasks/TASK_GUIDE_T004.md:108 aws_access_key_id | | 1 | Text containing `AKIA…****:1a5d44a2dca1` and a matching fake secret key | Both replaced by fingerprints; hits name the AWS detectors; neither ra
  tasks/TASK_GUIDE_T004.md:163 aws_access_key_id | - [ ] Example/placeholder values (`AKIA…****:1a5d44a2dca1`, `xxx`, `changeme`) — still redacted; the engine does not judge whether a secret is real (F
  tasks/TASK_GUIDE_T004.md:200 aws_access_key_id | they exist (AWS publishes `AKIA…****:1a5d44a2dca1` for exactly this purpose).
  tasks/TASK_GUIDE_T017.md:30 high_entropy_string | | Decision | **A — byte-equal after a defined normalization.** Recorded by the user on 2026-09-16 as **DDR-0005** (`memory/decisions.md#ddr-…****:8237
  tasks/TASK_GUIDE_T025.md:66 high_entropy_string | **Depends on**: T024 — `docs/DOCKER_MCP_GUIDE.md` and `tests/test_t024_mcp_guides.py` must be committed (they are uncommitted on `docs…****:bdfde32a3f
  tasks/TASK_GUIDE_T029.md:66 high_entropy_string | | 3 | Every existing redaction test still passes; a mixed-case+digit high-entropy token (e.g. `pB4k…****:264aeebb1563`) is still fingerprinted, includ
  tasks/TASK_GUIDE_T053.md:26 key_material_segment | T051 Stage 4 (2026-09-28): after the three T051 exemptions, 125 hits remain over 4 repos. Remaining false-positive classes: digit-bearing URL path seg
  tasks/TASK_GUIDE_T053.md:80 key_material_segment | | 2 | `https://hooks.slack.com/services/T0A1B2C3/B4D5E6F7/aB3x…****:c94b5c1636c7` | token segment fingerprinted | automated test |
  tasks/TASK_REVIEW_T004.md:55 aws_access_key_id | AWS_ACCESS_KEY_ID=AKIA…****:1a5d44a2dca1
  tasks/TASK_REVIEW_T004.md:56 aws_secret_access_key | aws_secret_access_key=wJal…****:78314b11be2e
  tasks/TASK_REVIEW_T004.md:57 key_material_segment | DATABASE_URL=postgres://svc:pB4k…****:df64c9a7ff9a@db.internal/prod
  tasks/TASK_REVIEW_T005.md:17 key_material_segment | | **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t005_budget.py` — 26 tests covering AC #1-#9 and the Edge Case
```
Named-detector gap (`scan(...)` at 2026-09-28T12:54:22Z; a short low-entropy value has only `credential_assignment` as cover):
```
'API_TOKEN = "abc"' -> 'API_TOKEN = "abc"' []
'API_TOKEN = "hunter2"' -> 'API_TOKEN = "hunter2"' []
'SERVICE_API_KEY=hunter2' -> 'SERVICE_API_KEY=hunter2' []
'db_password: hunter2' -> 'db_password: hunter2' []
'api_token = "hunter2"' -> 'api_token = "hunter2"' []
```
Observed: 123 hits over 4 repos at the CLI (19 + 59 + 14 + 31); the tracked-file sweep of this repo has 529 hits in 53 files, 346 of them in `registry/vendored/asvs.json` (the `v5.0.0_release/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json` URL tail), plus `CHECKSUMS.sha256` lines, commit SHAs in `NOTICE`/`linguist.json` URLs, bryony `CHANGELOG.md` `/commit/<sha>` links, `license: BSD-3-Clause`, `content=SYSTEM_PROMPT`-style shapes, `docs/claude-md/*.md` paths, `T0xx`-bearing report/worktree names. `API_TOKEN`, `api_token`, `SERVICE_API_KEY`, `db_password` assignments are not caught by `credential_assignment` (no `\b` between `_` and the secret word).

**AFTER** (captured 2026-09-28T13:17Z on `feat/T053-redaction-noise` @ `1b341e0` — the last code/docstring change; `3f719ad` after it only re-wraps one docstring line; same command, same 4 target repos, target HEADs in the log; backend-developer):
```
worktree HEAD 1b341e0
2026-09-28T13:17:06Z start easy-verifier-mcp 7de1e21
2026-09-28T13:17:07Z end easy-verifier-mcp exit=0
2026-09-28T13:17:07Z start kitchd 872cc92
2026-09-28T13:17:10Z end kitchd exit=0
2026-09-28T13:17:10Z start bryony 8df7b986f
2026-09-28T13:17:18Z end bryony exit=0
2026-09-28T13:17:18Z start ai-training 86c98d5
2026-09-28T13:17:20Z end ai-training exit=0
easy-verifier-mcp {'redaction_hits_observed': 16} security rating: 50
kitchd {'redaction_hits_observed': 62} security rating: 60
bryony {'redaction_hits_observed': 10} security rating: 60
ai-training {'redaction_hits_observed': 28} security rating: 60
```
Before → after, security `redaction_hits_observed`: easy-verifier-mcp **19 → 16**, kitchd **59 → 62**, bryony **14 → 10**, ai-training **31 → 28** (123 → 116). No rating changed. The two rises are the AC 4 detector fix catching real hard-coded credentials that `\b` used to hide: ai-training `credential_assignment` 7 → 23 (`POSTGRES_PASSWORD: pt_a…` in docker-compose.yml, `postgres_password="pass…"`, `langfuse_secret_key="sk-t…"`, `openai_api_key = "open…"` / `anthropic_api_key = "anth…"` test fixtures); kitchd 18 → 21 (`POSTGRES_PASSWORD: kitc…` in docker-compose.yml and ci.yml, `JWT_SECRET: "ci-t…"` in ci.yml). The false positives removed: ai-training `content=…_SYSTEM_PROMPT` ×3 and `plan_…=_MIN_PLAN_…` ×16, bryony CHANGELOG `/commit/<sha>` ×3 and `"license": "BSD-3-Clause"`, this repo's `README.md` ×4 / `judge.py` / `vendor_sources.py` ASVS URL and file-name hits.

Every hit in each security pack after the change:
```
[easy-verifier-mcp] hits=16 by detector=[('key_material_segment', 6), ('high_entropy_string', 5), ('credential_assignment', 3), ('aws_access_key_id', 1), ('high_entropy_hex', 1)]
  CLAUDE.md:128 high_entropy_string docs…****:3bda998323af
  CLAUDE.md:128 high_entropy_string docs…****:3bda998323af
  CLAUDE.md:152 high_entropy_string Comm…****:fb6035c79266
  PROJECT_KANBAN.md:62 key_material_segment easy…****:4f53ff0a00e7
  PROJECT_KANBAN.md:63 key_material_segment easy…****:34de13ddd1fc
  PROJECT_KANBAN.md:64 key_material_segment easy…****:d86ad9bc15b6
  memory/learnings.md:139 aws_access_key_id AKIA…****:1a5d44a2dca1
  src/easy_verifier/core/metric_tables.py:125 credential_assignment toke…****:3c469e9d6c58
  src/easy_verifier/core/redact.py:8 key_material_segment FAKE…****:5252c44014f7
  src/easy_verifier/core/redact.py:137 credential_assignment hunt…****:f52fbd32b2b3
  src/easy_verifier/core/redact.py:163 key_material_segment FAKE…****:5252c44014f7
  src/easy_verifier/core/redact.py:189 high_entropy_string BRAI…****:54e5675171d4
  src/easy_verifier/core/scope.py:42 high_entropy_hex 4b82…****:abe5b4848301
  src/easy_verifier/core/tokens.py:189 credential_assignment matc…****:7b72b24b7a0d
  src/easy_verifier/registry/curated/php.toml:25 high_entropy_string com/…****:832c5b7ddcbf
  src/easy_verifier/registry/vendored/linguist.json:10 key_material_segment 2-Di…****:d5fb98afc34e
[kitchd] hits=62 by detector=[('high_entropy_string', 22), ('credential_assignment', 21), ('key_material_segment', 18), ('high_entropy_hex', 1)]
  pnpm-lock.yaml:145 high_entropy_hex de2b…****:3333781a5f84
  apps/api/src/auth/auth.e2e.spec.ts:39 credential_assignment corr…****:622493693890
  apps/api/src/auth/auth.e2e.spec.ts:65 credential_assignment corr…****:622493693890
  apps/api/src/auth/auth.e2e.spec.ts:100 credential_assignment corr…****:622493693890
  apps/api/src/auth/auth.e2e.spec.ts:113 credential_assignment corr…****:622493693890
  apps/api/src/auth/auth.e2e.spec.ts:121 credential_assignment wron…****:6786324d7148
  apps/api/src/auth/auth.e2e.spec.ts:134 credential_assignment corr…****:622493693890
  apps/api/src/auth/auth.e2e.spec.ts:144 credential_assignment corr…****:622493693890
  apps/api/src/auth/guards/jwt-auth.guard.spec.ts:15 credential_assignment test…****:9caf06bb4436
  apps/api/src/auth/guards/jwt-auth.guard.ts:21 credential_assignment this…****:02df8ee47c46
  apps/api/src/auth/guards/jwt-auth.guard.ts:40 credential_assignment unde…****:eb045d78d273
  packages/shared/src/auth.dto.ts:5 credential_assignment stri…****:473287f8298d
  packages/shared/src/auth.dto.ts:12 credential_assignment stri…****:473287f8298d
  docker-compose.yml:8 credential_assignment kitc…****:405ee4ebc4dd
  .github/workflows/ci.yml:52 credential_assignment kitc…****:405ee4ebc4dd
  .github/workflows/ci.yml:63 credential_assignment ci-t…****:c7b3aa058ed8
  apps/api/src/kitchens/kitchens-rbac.e2e.spec.ts:38 credential_assignment corr…****:622493693890
  apps/api/src/kitchens/kitchens-rbac.e2e.spec.ts:66 credential_assignment invi…****:3fda7191ae55
  apps/api/src/kitchens/kitchens-rbac.e2e.spec.ts:66 credential_assignment memb…****:0f0a12ce80c2
  apps/api/src/rbac-audit/rbac-matrix.e2e.spec.ts:51 credential_assignment corr…****:622493693890
  apps/api/src/rbac-audit/rbac-matrix.e2e.spec.ts:79 credential_assignment invi…****:3fda7191ae55
  apps/api/src/rbac-audit/rbac-matrix.e2e.spec.ts:79 credential_assignment memb…****:0f0a12ce80c2
  repo…****:e808c802ee27.html:1 high_entropy_string repo…****:e808c802ee27
  repo…****:e808c802ee27.html:5 key_material_segment T019…****:c69625c8230c
  repo…****:e808c802ee27.html:172 key_material_segment T019…****:c69625c8230c
  repo…****:4d10b85626cf.html:1 high_entropy_string repo…****:4d10b85626cf
  repo…****:4d10b85626cf.html:5 key_material_segment T001…****:5c93152897b9
  repo…****:4d10b85626cf.html:172 key_material_segment T001…****:5c93152897b9
  repo…****:c1e88fe3b79e.html:1 high_entropy_string repo…****:c1e88fe3b79e
  repo…****:c1e88fe3b79e.html:5 key_material_segment T008…****:b14f995e21e7
  repo…****:c1e88fe3b79e.html:172 key_material_segment T008…****:b14f995e21e7
  repo…****:80b8e26427f3.html:1 high_entropy_string repo…****:80b8e26427f3
  repo…****:80b8e26427f3.html:5 high_entropy_string task…****:c73c56dd7956
  repo…****:80b8e26427f3.html:172 high_entropy_string task…****:c73c56dd7956
  repo…****:733ce35941d0.html:1 high_entropy_string repo…****:733ce35941d0
  repo…****:733ce35941d0.html:5 key_material_segment T015…****:5219e84d5507
  repo…****:733ce35941d0.html:172 key_material_segment T015…****:5219e84d5507
  repo…****:9a2cc977475d.html:1 high_entropy_string repo…****:9a2cc977475d
  repo…****:9a2cc977475d.html:5 key_material_segment T019…****:c69625c8230c
  repo…****:9a2cc977475d.html:172 key_material_segment T019…****:c69625c8230c
  repo…****:60e7365a9573.html:1 high_entropy_string repo…****:60e7365a9573
  repo…****:60e7365a9573.html:5 key_material_segment T027…****:112d0072ee96
  repo…****:60e7365a9573.html:172 key_material_segment T027…****:112d0072ee96
  repo…****:7131be7be111.html:1 high_entropy_string repo…****:7131be7be111
  repo…****:7131be7be111.html:5 key_material_segment T039…****:022c6201c8ff
  repo…****:7131be7be111.html:181 key_material_segment T039…****:022c6201c8ff
  repo…****:f16d4e14804c.html:1 high_entropy_string repo…****:f16d4e14804c
  repo…****:f16d4e14804c.html:5 key_material_segment T040…****:483b0d2ad989
  repo…****:f16d4e14804c.html:181 key_material_segment T040…****:483b0d2ad989
  repo…****:5bdb8e4dda09.html:1 high_entropy_string repo…****:5bdb8e4dda09
  repo…****:5bdb8e4dda09.html:5 key_material_segment T043…****:c0dd93e6c79b
  repo…****:5bdb8e4dda09.html:181 key_material_segment T043…****:c0dd93e6c79b
  repo…****:e808c802ee27.html:1 high_entropy_string repo…****:e808c802ee27
  repo…****:4d10b85626cf.html:1 high_entropy_string repo…****:4d10b85626cf
  repo…****:c1e88fe3b79e.html:1 high_entropy_string repo…****:c1e88fe3b79e
  repo…****:80b8e26427f3.html:1 high_entropy_string repo…****:80b8e26427f3
  repo…****:733ce35941d0.html:1 high_entropy_string repo…****:733ce35941d0
  repo…****:9a2cc977475d.html:1 high_entropy_string repo…****:9a2cc977475d
  repo…****:60e7365a9573.html:1 high_entropy_string repo…****:60e7365a9573
  repo…****:7131be7be111.html:1 high_entropy_string repo…****:7131be7be111
  repo…****:f16d4e14804c.html:1 high_entropy_string repo…****:f16d4e14804c
  repo…****:5bdb8e4dda09.html:1 high_entropy_string repo…****:5bdb8e4dda09
[bryony] hits=10 by detector=[('credential_assignment', 4), ('high_entropy_hex', 4), ('high_entropy_string', 2)]
  frontend/app/scripts/modules/auth/views/register.itemview.js:19 credential_assignment #pas…****:a9ca1573cef4
  frontend/app/scripts/modules/auth/views/register.itemview.js:101 credential_assignment this…****:fcad7430e71a
  backend/server/dashboard/authenticate.js:41 credential_assignment quer…****:12d09cfeec1f
  backend/Gruntfile.js:77 high_entropy_hex 6b88…****:42332d012db5
  backend/Gruntfile.js:84 credential_assignment sona…****:48ce1a75f189
  backend/bin/ec2/fabric/fabfile.py:19 high_entropy_string ssh/…****:d13e7d3f0968
  backend/bin/ec2/fabric/fabfile.py:129 high_entropy_hex 5edf…****:d2f648993e74
  backend/bin/ec2/fabric/fabfile.py:148 high_entropy_hex 5edf…****:d2f648993e74
  backend/bin/fabric/fabfile.py:29 high_entropy_string ssh/…****:d13e7d3f0968
  backend/bin/fabric/fabfile.py:188 high_entropy_hex 5edf…****:d2f648993e74
[ai-training] hits=28 by detector=[('credential_assignment', 23), ('high_entropy_string', 5)]
  docker-compose.yml:6 credential_assignment pt_a…****:cfe88c2ad7e2
  src/core/llm/factory.py:164 credential_assignment sett…****:7a417f6aeac4
  src/core/llm/factory.py:180 credential_assignment sett…****:7a417f6aeac4
  src/core/llm/factory.py:196 credential_assignment sett…****:fd8e43297e05
  src/core/observability/langfuse.py:54 credential_assignment str…****:8c25cb368646
  src/core/observability/langfuse.py:66 credential_assignment sett…****:f0adf194c81b
  src/core/observability/langfuse.py:104 credential_assignment reso…****:afe323a3d0c5
  src/core/subgraphs/fitness/template_registry.py:60 high_entropy_string sess…****:cf21321ce3cb
  src/core/subgraphs/research/research_agent.py:113 credential_assignment set_…****:4ce698f2e665
  src/docs/ragas-evaluation.md:61 high_entropy_string VERI…****:bf883de7139a
  src/docs/ragas-evaluation.md:64 high_entropy_string VERI…****:bf883de7139a
  tests/test_e2e_happy_path.py:26 credential_assignment sk-t…****:f3abf2a6cc4f
  tests/test_fitness_planner.py:170 high_entropy_string stru…****:a1b4317b6b6e
  tests/test_langfuse_spans.py:89 credential_assignment sk-t…****:f3abf2a6cc4f
  tests/test_langfuse_spans.py:114 credential_assignment sk-t…****:f3abf2a6cc4f
  tests/test_llm_factory.py:47 credential_assignment open…****:97aba22fd3c8
  tests/test_llm_factory.py:48 credential_assignment anth…****:6e2c8215fd88
  tests/test_llm_factory.py:77 credential_assignment open…****:97aba22fd3c8
  tests/test_llm_factory.py:78 credential_assignment anth…****:6e2c8215fd88
  tests/test_llm_factory.py:112 credential_assignment open…****:97aba22fd3c8
  tests/test_llm_factory.py:113 credential_assignment anth…****:6e2c8215fd88
  tests/test_llm_factory.py:140 credential_assignment open…****:97aba22fd3c8
  tests/test_llm_factory.py:141 credential_assignment anth…****:6e2c8215fd88
  tests/test_llm_factory.py:164 credential_assignment open…****:97aba22fd3c8
  tests/test_llm_factory.py:185 credential_assignment open…****:97aba22fd3c8
  tests/test_llm_factory.py:186 credential_assignment anth…****:6e2c8215fd88
  tests/test_rate_limit_api.py:18 high_entropy_string rate…****:59dfe3918dfb
  tests/test_settings.py:11 credential_assignment pass…****:d74ff0ee8da3
```
Tracked-file sweep of this repo after (253 files — `tests/test_t053_redaction_noise.py` added; `tests/` and `tasks/` lines left out of the sample below, they hold deliberate fixtures and pasted evidence):
```
[sweep /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp-T053] tracked files=253 total hits=194 files with hits=46
 by detector: [('credential_assignment', 74), ('high_entropy_string', 59), ('key_material_segment', 47), ('aws_access_key_id', 10), ('jwt', 2), ('high_entropy_hex', 1), ('aws_secret_access_key', 1)]
 by file: [('tests/test_t004_redact.py', 37), ('tests/test_t053_redaction_noise.py', 26), ('tasks/TASK_REVIEW_T016.md', 18), ('tests/test_t008_security.py', 11), ('tests/test_t051_redaction_false_positives.py', 11), ('ta
  CLAUDE.md:128 high_entropy_string | See [`docs…****:3bda998323af.md`](docs…****:3bda998323af.md) for full Step 1 / Step 1.5 (Ambiguity Resolution Protocol) / Step 2 detail.
  CLAUDE.md:128 high_entropy_string | See [`docs…****:3bda998323af.md`](docs…****:3bda998323af.md) for full Step 1 / Step 1.5 (Ambiguity Resolution Protocol) / Step 2 detail.
  CLAUDE.md:152 high_entropy_string | - **Stage 1.5** (Sub-Agent Architecture): design the sub-agent team; base team is always Comm…****:fb6035c79266; `Skill({ skill: "craft-agent" })` onl
  PROJECT_KANBAN.md:62 key_material_segment | - [~] **T053** — Remaining redaction noise (versioned URL paths, commit SHAs, checksum lines) + API_TOKEN detector gap (T051 follow-up) | backend-deve
  PROJECT_KANBAN.md:63 key_material_segment | - [~] **T052** — Make requirement-fidelity and blast-radius rate: AC tracing + churn-hotspot evidence (T035 sign-off follow-up) | backend-developer |
  PROJECT_KANBAN.md:64 key_material_segment | - [~] **T037** — MCP reference gate: framework detection + `needs_input` for missing fields only (≤20) | backend-developer | C2 | Risk: Med | P1 | 🔄 s
  memory/learnings.md:139 aws_access_key_id | run_dimension(DESCRIPTOR, "/nonexistent/AKIA…****:1a5d44a2dca1/repo")
  src/easy_verifier/core/metric_tables.py:125 credential_assignment | token=toke…****:3c469e9d6c58,
  src/easy_verifier/core/metric_tables.py:257 credential_assignment | def token_regex(token: str…****:8c25cb368646) -> str:
  src/easy_verifier/core/metrics.py:276 credential_assignment | token: str…****:8c25cb368646
  src/easy_verifier/core/models.py:342 high_entropy_string | ``repo…****:51117f288d24.html``.
  src/easy_verifier/core/redact.py:8 key_material_segment | FAKE…****:5252c44014f7  ->  FAKE…****:a3f9c2e18b04
  src/easy_verifier/core/redact.py:160 credential_assignment | # whether `password=hunt…****:f52fbd32b2b3  # dev` was covered elsewhere: it was
  src/easy_verifier/core/redact.py:186 key_material_segment | (`/home/user/keys/FAKE…****:5252c44014f7` still fingerprints), and
  src/easy_verifier/core/scope.py:42 high_entropy_hex | _EMPTY_TREE = "4b82…****:abe5b4848301"
  src/easy_verifier/core/tokens.py:189 credential_assignment | token = matc…****:7b72b24b7a0d)
  src/easy_verifier/dimensions/blast_radius.py:387 credential_assignment | ordered = sorted(tokens, key=lambda token: (-le…****:2cbf685d3855), token))
  src/easy_verifier/registry/curated/php.toml:25 high_entropy_string | citation_url = "https://github.com/…****:832c5b7ddcbf"
  src/easy_verifier/registry/vendored/linguist.json:10 key_material_segment | "2-Di…****:d5fb98afc34e Array": {
  templates/LEARNING-RECORD-FORMAT.md:69 key_material_segment | - LR-0…****:83dd659d1e0c
  templates/LEARNING-RECORD-FORMAT.md:89 key_material_segment | name: LR-0…****:01a798ba324b
```
Sweep before → after: **529 → 194** hits; `registry/vendored/asvs.json` **346 → 0**, `vendored/NOTICE` 4 → 0, `vendored/CHECKSUMS.sha256` 4 → 0, `vendored/linguist.json` 2 → 1 (`"2-Dimensional Array"` key, no anchor). `credential_assignment` 45 → 74: the new catches are in test/review files that carry deliberate `_`-joined fixtures.

Named detector after:
```
'API_TOKEN = "abc"' -> 'API_TOKEN = "abc…****:ba7816bf8f01"' ['credential_assignment']
'API_TOKEN = "hunter2"' -> 'API_TOKEN = "hunt…****:f52fbd32b2b3"' ['credential_assignment']
'SERVICE_API_KEY=hunter2' -> 'SERVICE_API_KEY=hunt…****:f52fbd32b2b3' ['credential_assignment']
'db_password: hunter2' -> 'db_password: hunt…****:f52fbd32b2b3' ['credential_assignment']
'api_token = "hunter2"' -> 'api_token = "hunt…****:f52fbd32b2b3"' ['credential_assignment']
2026-09-28T13:19:08Z
```

**DELTA**: A security score no longer fingerprints version-labelled URLs, commit SHAs, checksum lines, `key=CONSTANT` and SPDX ids (vendored `asvs.json` 346 → 0 hits), and `API_TOKEN = …` / `db_password: …` style hard-coded credentials are now caught by name.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T053.jsonl`, never the
implementing agent alone]
