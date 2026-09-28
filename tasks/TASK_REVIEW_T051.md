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

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T051.jsonl`, never the
implementing agent alone]
