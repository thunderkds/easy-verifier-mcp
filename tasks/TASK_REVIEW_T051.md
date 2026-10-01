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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t051_redaction_false_positives.py` (41 tests: hash-context reproducers + secret-veto twins, word-only identifier exemption with guards, git-ignore filter incl. nested .gitignore/tracked-kept/never-read files still listed/no-git unchanged; 29 fail on pre-fix source) + `tests/test_t051_safe_git.py` (7 tests: armed fixture repo — fsmonitor, diff.external, textconv, clean/smudge filters, pager, hooks — positive control fires, real CLI project/worktree/changes + blast-radius never fire the marker; command-shape and env pins; grep test no subprocess outside core/git.py). `test_t010_blast_radius.py` structural test repointed to `run_git_text`. Sabotage: 17/18 exemption guards + runner defences caught (the uncatchable one documented). Supervisor re-run `1175 passed, 2 skipped in 40.98s` |
| Verification command run | ☑ pass | Supervisor 2026-09-28: pytest `1175 passed, 2 skipped` (exit 0); `ruff check src tests` → `All checks passed!` (exit 0); `grep subprocess|os.system|popen src/` outside core/git.py → only comments and curated sink data; `docker compose build && bash scripts/verify_container.sh` → PASS (uid=10001, read-only, network=none) |
| Negative cases hold | ☑ pass | `API_TOKEN = "<64 hex>"` and `token_sha256` still fingerprinted (secret veto); malicious repo config/attributes/hooks never execute through the CLI (marker absent) while plain `git status` does fire it (positive control) |
| verify | ☑ pass | Real CLI 4-repo redaction_hits_observed (agent, re-run 12:46Z after P0): easy-verifier 159→20, kitchd 222→59, bryony 132→14, ai-training 271→31; ratings otherwise identical. Supervisor in-container runs (`--entrypoint easy-verifier`, read-only mount, network none): worktree and project scope exit 0 with no git warnings; project ratings architecture 100, code-quality 50, security 50, test-strategy 100 — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed `core/redact.py` (hash-context + identifier exemptions, docstring residuals), `core/context.py` (`git_ignore_filter`), `core/scope.py`, new `core/git.py` (hardened runner: config overrides, filter blanking, --no-ext-diff/--no-textconv, no shell, stdin closed, 120s timeout, explicit env without HOME), `dimensions/blast_radius.py`. P0 found during review (existing git calls honoured repo-configured fsmonitor/filters → target code execution, NFR-007) → fixed in 75650d6. Rulings: AC4 partial → remaining classes + API_TOKEN detector gap moved to T053; once-per-walk git; ignore filter for all dimensions; listing in scope.py; line-wide secret veto; global git config ignored (safer; container unaffected, verified); extra `git config` call accepted. Security review inline (High): passed with the P0 fix |
| Full smoke suite still green (no regression) | ☑ pass | full suite 1175 passed, 2 skipped |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend task, no UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Pure backend task, no UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | Pure backend task, no UI |

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

**DELTA**: Security scores no longer drown in hashes, test names and git-ignored files (784→125 hits over 4 repos), and a hostile target repo can no longer make the verifier execute code through git config, filters or hooks.

**WITNESS**: Supervisor re-ran suite, ruff, the bypass grep, the Docker verification and in-container CLI runs on 2026-09-28, independent of the implementing agent.

### Stage 4 P0 follow-up — safe git runner (NFR-007), implementer evidence

Every git subprocess in `src/` now runs through `src/easy_verifier/core/git.py` (`run_git` / `run_git_text`), used by `scope._run_git`, `context.git_ignore_filter` and `blast_radius._run_git`. The runner adds `-c core.fsmonitor=false -c core.hooksPath=/dev/null -c diff.external= -c core.pager=cat -c protocol.allow=never`, blanks each configured `filter.<driver>.clean/smudge/process` (with `required=false`; driver names are read first with `git config --get-regexp`), puts `--no-ext-diff --no-textconv` on diff/log/show, and uses an explicit env (`GIT_CONFIG_NOSYSTEM=1`, `GIT_TERMINAL_PROMPT=0`, `GIT_OPTIONAL_LOCKS=0`, `PATH=os.defpath`, no `HOME`). It runs with no shell, stdin closed and a 120 s timeout. The commands that run and their parsed output are unchanged.

Tests (`tests/test_t051_safe_git.py`): an armed fixture repo (fsmonitor, diff.external, diff.<drv>.textconv/command, filter.<drv>.clean/smudge required, core.pager, index/checkout hooks → marker script outside the repo). A positive control shows plain `git status` fires the marker. The real CLI `score` for project, worktree and `changes --range HEAD` (all 7 dimensions, so blast-radius is included; `</dev/null`) must never create the marker. A command-shape pin, an env pin, and a grep test (no `subprocess`/`os.system`/`"git",` outside `core/git.py`). `tests/test_t010_blast_radius.py` structural test repointed: the one `subprocess.run` moved from `blast_radius.py` to `core/git.py`.

Sabotage (each defence removed on a copy, `tests/test_t051_safe_git.py` re-run):
```
CAUGHT | fsmonitor override removed | 4 failed, 3 passed in 0.72s | ['test_cli_score_never_executes_repo_config_programs[scope_args0]', 'test_cli_score_never_executes_repo_config_programs[scope_args1]', 'test_cli_score_n
CAUGHT | filter overrides removed | 1 failed, 6 passed in 0.60s | ['test_cli_score_never_executes_repo_config_programs[scope_args1]']
CAUGHT | --no-ext-diff/--no-textconv removed | 2 failed, 5 passed in 0.68s | ['test_cli_score_never_executes_repo_config_programs[scope_args2]', 'test_runner_command_carries_every_defence']
CAUGHT | diff.external override removed | 1 failed, 6 passed in 0.67s | ['test_runner_command_carries_every_defence']
CAUGHT | GIT_OPTIONAL_LOCKS removed | 1 failed, 6 passed in 0.66s | ['test_runner_environment_is_explicit_and_hardened']
CAUGHT | bypass: scope calls subprocess directly | 3 failed, 4 passed in 0.67s | ['test_cli_score_never_executes_repo_config_programs[scope_args1]', 'test_cli_score_never_executes_repo_config_programs[scope_args2]', 'tes
```
The CLI marker tests catch: fsmonitor (all 3 scopes), the filter blanking (worktree `status`, which re-hashes a same-size file with a new mtime), and `--no-textconv`/`--no-ext-diff` (changes-scope `diff`). `diff.external=`, `hooksPath` and `GIT_OPTIONAL_LOCKS` overlap with those as defence in depth, so only the shape/env pins catch their removal.

Verification: `pytest -q` → `1175 passed, 2 skipped in 41.79s` (exit 0); `ruff check src tests` → All checks passed! (exit 0).

4-repo sanity after the P0 fix (same CLI command, 2026-09-28T12:46Z):
```
2026-09-28T12:46:15Z start easy-verifier-mcp b6b67f0
2026-09-28T12:46:16Z end easy-verifier-mcp exit=0
2026-09-28T12:46:16Z start kitchd 872cc92
2026-09-28T12:46:18Z end kitchd exit=0
2026-09-28T12:46:18Z start bryony 8df7b986f
2026-09-28T12:46:25Z end bryony exit=0
2026-09-28T12:46:25Z start ai-training 86c98d5
2026-09-28T12:46:26Z end ai-training exit=0
easy-verifier-mcp {'redaction_hits_observed': 20} security rating: 50 overall: 75
kitchd {'redaction_hits_observed': 59} security rating: 60 overall: 90
bryony {'redaction_hits_observed': 14} security rating: 60 overall: 78
ai-training {'redaction_hits_observed': 31} security rating: 60 overall: 70
```
kitchd, bryony and ai-training are identical to the AFTER capture above in every metric and rating. easy-verifier-mcp shows 21 → 20, but only because the main checkout moved (`3ff6dda` → `b6b67f0`). Pre-P0 source (`728a435`) on the same `b6b67f0` checkout also gives **20**.
