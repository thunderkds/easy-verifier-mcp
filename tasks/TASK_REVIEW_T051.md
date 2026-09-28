# TASK_REVIEW — T051: Redaction false positives: content hashes, long identifiers, git-ignored files

> Sibling of `tasks/TASK_GUIDE_T051.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE** (captured 2026-09-28T07:47Z on base `673a83a`, before any T051 implementation commit; backend-developer):

Command, per repo (stdin closed):
```
PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli score --repo <repo> --scope project </dev/null > before/<name>.json
```
Run log (UTC; repo HEAD; exit code):
```
2026-09-28T07:47:24Z start easy-verifier-mcp 673a83a
2026-09-28T07:47:25Z end easy-verifier-mcp exit=0
2026-09-28T07:47:25Z start kitchd 872cc92
2026-09-28T07:47:27Z end kitchd exit=0
2026-09-28T07:47:27Z start bryony 8df7b986f
2026-09-28T07:47:35Z end bryony exit=0
2026-09-28T07:47:35Z start ai-training 86c98d5
2026-09-28T07:47:36Z end ai-training exit=0
```
Security `redaction_hits_observed` (and security rating) extracted from each JSON:
```
easy-verifier-mcp {'redaction_hits_observed': 159} security rating: 20 overall: 68
kitchd {'redaction_hits_observed': 222} security rating: 60 overall: 90
bryony {'redaction_hits_observed': 132} security rating: 60 overall: 78
ai-training {'redaction_hits_observed': 271} security rating: 60 overall: 70
```
Where the hits come from (security pack via `run_dimension(security, repo, "project")`; lines shown are the already-redacted excerpt text, never raw values):
```
[self]
hits: 159
by file: [('.claude/harness-lock.json', 94), ('.claude/hooks/tests/test_diagnose_evidence_loop.py', 4), ('.claude/hooks/tests/test_memory_channel_and_budget.py', 4), ('.claude/hooks/tests/test_bugfix_evidence_parity.py', 2), ('.claude/hooks/tests/test_pre_agent_validate_guide.py', 2), ('.claude/hooks/tests/test_agent_guide_dedup.py', 1), ('.claude/hooks/tests/test_delivery_report_render.py', 1), (
by detector: [('high_entropy_hex', 96), ('high_entropy_string', 62), ('key_material_segment', 1)]
[kitchd]
hits: 222
by file: [('.claude/harness-lock.json', 111), ('.codex/harness-lock.json', 60), ('apps/api/src/auth/auth.e2e.spec.ts', 7), ('repo…****:e808c802ee27.html', 4), ('repo…****:4d10b85626cf.html', 4), ('repo…****:c1e88fe3b79e.html', 4), ('repo…****:80b8e26427f3.html', 4), ('repo…****:733ce35941d0.html', 4), ('repo…****:9a2cc977475d.html', 4), ('repo…****:60e7365a9573.html', 4), ('repo…**
by detector: [('high_entropy_hex', 171), ('high_entropy_string', 19), ('credential_assignment', 18), ('key_material_segment', 14)]
[bryony]
hits: 132
by file: [('backend/yarn.lock', 42), ('backend/package-lock.json', 38), ('backend/scripts/netwise/package-lock.json', 37), ('CHANGELOG.md', 3), ('backend/bin/ec2/fabric/fabfile.py', 3), ('frontend/app/scripts/modules/auth/views/register.itemview.js', 2), ('backend/Gruntfile.js', 2), ('backend/bin/fabric/fabfile.py', 2), ('backend/utils/elmongo/package.json', 1), ('nodes/package.json', 1), ('backen
by detector: [('high_entropy_string', 75), ('high_entropy_hex', 50), ('credential_assignment', 4), ('key_material_segment', 3)]
[ai-training]
hits: 271
by file: [('uv.lock', 237), ('tests/test_llm_factory.py', 6), ('tests/test_llm_payload_contracts.py', 5), ('src/core/llm/factory.py', 3), ('src/core/observability/langfuse.py', 3), ('src/core/subgraphs/research/research_agent.py', 2), ('src/docs/ragas-evaluation.md', 2), ('tests/test_e2e_happy_path.py', 2), ('tests/test_fitness_planner.py', 2), ('tests/test_llm_payload_gates.py', 2), ('src/core/pr
by detector: [('high_entropy_hex', 194), ('high_entropy_string', 70), ('credential_assignment', 7)]

[self sample]
by file: [('.claude/harness-lock.json', 94), ('.claude/hooks/tests/test_diagnose_evidence_loop.py', 4), ('.claude/hooks/tests/test_memory_channel_and_budget.py', 4), ('.claude/hooks/tests/test_bugfix_evidence_parity.py', 2), ('.claude/hooks/tests/test_pre_agent_validate_guide.py', 2), ('.claude/hooks/tests/test_agent_guide_dedup.py', 1), ('.claude/hooks/tests/test_delivery_report_render.py', 1), ('.claude/hooks/tests/test_guide_sections.py', 1), ('.claude/hooks/tests/test_verify_row_fill_detection.py', 1), ('.claude/settings.local.json', 1), ('.claude/skills/craft-spawn-prompt/SKILL.md', 1), ('.claude/skills/html-report/SKILL.md', 1)]
.claude/harness-lock.json:3 high_entropy_hex | ".claude/agents/backend.md": "3ba9…****:9e97d4ba813d",
.claude/harness-lock.json:4 high_entropy_hex | ".claude/agents/common-infrastructure.md": "1f7f…****:34a754ca55ac",
.claude/hooks/tests/test_agent_guide_dedup.py:127 high_entropy_string | def test…****:dd5bad659f09():
.claude/hooks/tests/test_bugfix_evidence_parity.py:177 high_entropy_string | def test…****:789bf4a886e2():
.claude/hooks/tests/test_delivery_report_render.py:175 high_entropy_string | def test…****:0eab24b84b6d():
.claude/hooks/tests/test_memory_channel_and_budget.py:8 high_entropy_string | (`docs…****:1dc8f8716d2f.md` §b: zero of 49 `Agent` records carried
.claude/hooks/tests/test_memory_channel_and_budget.py:60 high_entropy_string | "docs…****:3bda998323af.md",
.claude/hooks/.stat…****:6027350fa4f6.txt:1 high_entropy_string | 
.claude/hooks/.stat…****:62cc48bad1a5.txt:1 high_entropy_string | 
(... 46 hits are file *paths* under git-ignored .claude/hooks/.state/ fingerprinted by path redaction)
[bryony sample]
backend/package-lock.json:9 high_entropy_string | "integrity": "sha1…****:15562a0bc4ee",
backend/package-lock.json:15 high_entropy_string | "integrity": "sha1…****:0e1d5a7e3906",
by file: [('backend/yarn.lock', 42), ('backend/package-lock.json', 38), ('backend/scripts/netwise/package-lock.json', 37), ('CHANGELOG.md', 3), ('backend/bin/ec2/fabric/fabfile.py', 3), ('frontend/app
backend/yarn.lock:7 high_entropy_hex | resolved "https://registry.yarnpkg.com/Faker/-/Faker-0.5.12.tgz#c7d7…****:6fec7a6e308b"
[ai-training sample]
by file: [('uv.lock', 237), ('tests/test_llm_factory.py', 6), ('tests/test_llm_payload_contracts.py', 5), ('src/core/llm/factory.py', 3), ('src/core/observability/langfuse.py', 3), ('src/core/subgraph
uv.lock:17 high_entropy_hex | sdist = { url = "https://files.pythonhosted.org/packages/33/c6/61a2…****:89717eb5a29e/aiohappyeyeballs-2.6.2.tar.gz", hash = "sha256:e202…****:a28ff45
tests/integration/test_todos_gate.py:9 high_entropy_string | def test…****:3c618ee84c72(workspace_root: Path) -> None:
tests/test_e2e_happy_path.py:36 high_entropy_string | def test…****:e0e58f3005c2(
[kitchd sample]
by file: [('.claude/harness-lock.json', 111), ('.codex/harness-lock.json', 60), ('apps/api/src/auth/auth.e2e.spec.ts', 7), ('repo…****:e808c802ee27.html', 4), ('repo…****:4d10b85626cf.html', 4), ('repo…****:c1e88fe3b79e.html', 4), ('repo…****:80b8e26427f3.html', 4), ('repo…****:733ce35941d0.html', 4), ('repo…****:9a2cc977475d.html', 4), ('repo…****:60e7365a9573.html', 4), ('repo…****:7131be7be111.html', 4), ('apps/api/src/kitchens/kitchens-rbac.e2e.spec.ts', 3)]
.claude/harness-lock.json:3 high_entropy_hex | ".claude/hooks/lib/guide_sections.py": "b9e2…****:3929f5fe5361",
```
Observed: on this repo all 159 hits are in git-ignored `.claude/` (94 sha256 values in `.claude/harness-lock.json`, `def test_…` names, suffix-less paths, and 46 fingerprinted paths of `.claude/hooks/.state/*`). kitchd: 171 of 222 in git-ignored `.claude/`/`.codex/harness-lock.json`. bryony: 117 of 132 in lockfiles (`"integrity": "sha1-…"`, yarn `resolved "…tgz#<sha1>"`). ai-training: 237 of 271 in `uv.lock` (`hash = "sha256:…"` + pythonhosted URL digests) plus `def test_…` names.

**AFTER** (captured 2026-09-28T08:10:25Z on branch `feat/T051-redaction-fp` @ `10ba129`; same command, same 4 target repos; target-repo HEADs in the log — this repo's main checkout had moved to `3ff6dda` through concurrent Supervisor/T036 commits, which do not touch the scanned `.claude/` or lockfile content):
```
2026-09-28T08:10:25Z start easy-verifier-mcp 3ff6dda
2026-09-28T08:10:27Z end easy-verifier-mcp exit=0
2026-09-28T08:10:27Z start kitchd 872cc92
2026-09-28T08:10:30Z end kitchd exit=0
2026-09-28T08:10:30Z start bryony 8df7b986f
2026-09-28T08:10:40Z end bryony exit=0
2026-09-28T08:10:40Z start ai-training 86c98d5
2026-09-28T08:10:42Z end ai-training exit=0
easy-verifier-mcp {'redaction_hits_observed': 21} security rating: 50 overall: 75
kitchd {'redaction_hits_observed': 59} security rating: 60 overall: 90
bryony {'redaction_hits_observed': 14} security rating: 60 overall: 78
ai-training {'redaction_hits_observed': 31} security rating: 60 overall: 70
```
Before → after, security `redaction_hits_observed`: easy-verifier-mcp **159 → 21**, kitchd **222 → 59**, bryony **132 → 14**, ai-training **271 → 31**. Only rating change across all 4 repos × 7 dimensions: easy-verifier-mcp security 20 → 50 (overall 68 → 75). Other metric deltas on this repo only (from dropping git-ignored `.claude/`): `security.sink_hits_observed` 6 → 0 (the 6 sinks were in `.claude/hooks/*.py`), `security.lockfile_missing` 0 → abstained (`.claude/harness-lock.json` had been filling the lockfile role), `architecture.top_level_import_cycles` abstained → 0.

Remaining hits (redacted excerpt text, never raw values):
```
[self]
hits: 21
by file: [('src/easy_verifier/core/redact.py', 5), ('README.md', 4), ('CLAUDE.md', 3), ('PROJECT_KANBAN.md', 2), ('scripts/vendor_sources.py', 2), ('src/easy_verifier/core/metric_tables.py', 2), ('memory/learnings.md', 1), ('src/easy_verifier/core/judge.py', 1), ('src/easy_verifier/core/scope.py', 1
by detector: [('high_entropy_string', 11), ('key_material_segment', 5), ('credential_assignment', 3), ('aws_access_key_id', 1), ('high_entropy_hex', 1)]
[kitchd]
hits: 59
by file: [('apps/api/src/auth/auth.e2e.spec.ts', 7), ('repo…****:e808c802ee27.html', 4), ('repo…****:4d10b85626cf.html', 4), ('repo…****:c1e88fe3b79e.html', 4), ('repo…****:80b8e26427f3.html', 4), ('repo…****:733ce35941d0.html', 4), ('repo…****:9a2cc977475d.html', 4), ('repo…****:60e73
by detector: [('high_entropy_string', 22), ('credential_assignment', 18), ('key_material_segment', 18), ('high_entropy_hex', 1)]
[bryony]
hits: 14
by file: [('CHANGELOG.md', 3), ('backend/bin/ec2/fabric/fabfile.py', 3), ('frontend/app/scripts/modules/auth/views/register.itemview.js', 2), ('backend/Gruntfile.js', 2), ('backend/bin/fabric/fabfile.py', 2), ('nodes/package.json', 1), ('backend/server/dashboard/authenticate.js', 1)]
by detector: [('high_entropy_hex', 7), ('credential_assignment', 4), ('high_entropy_string', 2), ('key_material_segment', 1)]
[ai-training]
hits: 31
by file: [('tests/test_llm_payload_contracts.py', 4), ('src/core/llm/factory.py', 3), ('src/core/observability/langfuse.py', 3), ('src/core/subgraphs/research/research_agent.py', 2), ('src/docs/ragas-evaluation.md', 2), ('tests/test_llm_factory.py', 2), ('tests/test_llm_payload_gates.py', 2), ('test
by detector: [('high_entropy_string', 24), ('credential_assignment', 7)]
[self sample]
CLAUDE.md:128 high_entropy_string | See [`docs…****:3bda998323af.md`](docs…****:3bda998323af.md) for full Step 1 / Step 1.5 (Ambiguity Resolution Protocol) / Step 2 d
CLAUDE.md:152 high_entropy_string | - **Stage 1.5** (Sub-Agent Architecture): design the sub-agent team; base team is always Comm…****:fb6035c79266; `Skill({ skill: "cr
PROJECT_KANBAN.md:64 key_material_segment | - [~] **T051** — Redaction false positives: content hashes, long identifiers, git-ignored files (T035 sign-off follow-up) | 
PROJECT_KANBAN.md:65 key_material_segment | - [~] **T036** — Local layer `~/.easy-verifier-sot/`, `registry_entries` intake, replay parity, Docker mount | backend-devel
README.md:128 high_entropy_string | | `security` | `redaction_hits_observed` | ≤ 0 | 40 | [CWE-798 Use of Hard-coded Credentials](https://cwe.mitre.org/data/definitions
README.md:130 high_entropy_string | | `security` | `lockfile_missing` | ≤ 0 | 20 | [OWASP ASVS 5.0.0 V15.1.2 (third-party component inventory)](https://github.com/OWASP
memory/learnings.md:139 aws_access_key_id | run_dimension(DESCRIPTOR, "/nonexistent/AKIA…****:1a5d44a2dca1/repo")
scripts/vendor_sources.py:58 high_entropy_string | "OWAS…****:e1b0aefbf060.0.0_en.flat.json"
[bryony sample]
nodes/package.json:29 key_material_segment | "license": "BSD-…****:248dd895a2f8"
frontend/app/scripts/modules/auth/views/register.itemview.js:19 credential_assignment | password: '#pas…****:a9ca1573cef4',
frontend/app/scripts/modules/auth/views/register.itemview.js:101 credential_assignment | password = this…****:fcad7430e71a),
backend/server/dashboard/authenticate.js:41 credential_assignment | const token = quer…****:12d09cfeec1f;
CHANGELOG.md:9 high_entropy_hex | - [#5dad3801](https://gitlab.asoft-python.com/bryony/bryony/commit/5dad…****:c7dce6c9ce19) Developer implement feature to allow user r
CHANGELOG.md:15 high_entropy_hex | - [#61d3ce17](https://gitlab.asoft-python.com/bryony/bryony/commit/61d3…****:1435d5caead0) To Be Added to LinkedIn List extract wrong
CHANGELOG.md:25 high_entropy_hex | - [#ec0d9d76](https://gitlab.asoft-python.com/bryony/bryony/commit/ec0d…****:d77f64a8c89c) Supports Company Tags feature: show compan
backend/Gruntfile.js:77 high_entropy_hex | login: '6b88…****:42332d012db5',
[ai-training sample]
src/core/profile/extraction.py:137 high_entropy_string | SystemMessage(cont…****:deed5ccff74a),
src/core/subgraphs/fitness/planner.py:155 high_entropy_string | SystemMessage(cont…****:bd58f154ce1d),
src/core/subgraphs/fitness/template_registry.py:60 high_entropy_string | sess…****:cf21321ce3cb(profile, constraints),
src/core/subgraphs/research/research_agent.py:113 credential_assignment | token = set_…****:4ce698f2e665)
src/core/subgraphs/research/research_agent.py:144 high_entropy_string | SystemMessage(cont…****:f7cd178577aa),
src/docs/ragas-evaluation.md:61 high_entropy_string | - Set `VERI…****:bf883de7139a` in your environment/`.env`.
[kitchd sample]
by detector: [('high_entropy_string', 22), ('credential_assignment', 18), ('key_material_segment', 18), ('high_entropy_hex', 1)]
apps/api/src/auth/auth.e2e.spec.ts:39 credential_assignment | password: 'corr…****:622493693890',
apps/api/src/auth/auth.e2e.spec.ts:65 credential_assignment | const password = 'corr…****:622493693890';
by detector: [('high_entropy_string', 22), ('credential_assignment', 18), ('key_material_segment', 18), ('high_entropy_hex', 1)]
repo…****:e808c802ee27.html:5 key_material_segment | <title>Code Review Report — task/T019…****:c69625c8230c</title>
```
What remains is (a) real secret shapes the suite is meant to flag — `credential_assignment` on test passwords/`api_key=` lines, a hex `login:` value in bryony `Gruntfile.js`, deliberate `FAKE…` fixtures in this repo's docs — and (b) false-positive classes outside T051's three: tracked report/URL paths with digit pieces (kitchd `reports/*-T019-…html`), commit SHAs in prose/URLs (`CHANGELOG.md`, `commit <sha>`), `key=CONSTANT` (`content=SYSTEM_PROMPT`), and `sha256sum`-format lines. Ruling items, not fixed here.

Runtime (bryony, same machine, back to back): pre-T051 `/tmp/claude-1000/-home-hungnguyenhuu-workspace-pets-hungnguyen111-easy-verifier-mcp/06633da9-85a5-4902-ba87-95dec4f60d5e/scratchpad/pre/src` 9.97 s vs T051 9.71 s; ignore listing = 16 `git ls-files` calls per score run, 82 ms total.

**DELTA**: security's `redaction_hits_observed` no longer counts sha/integrity digests in lock files, `def test_…`/SCREAMING_CASE identifiers, or anything in git-ignored files, so the 40-weight rule now reflects secret-shaped content (4-repo total 784 → 125) while every existing secret test still passes.

**WITNESS**: [reviewer — derive from `memory/event-trace/T051.jsonl`]
