# NEXT-SESSION — Resume Point

**Written**: 2026-08-14 · **Branch**: `plan/stage2-task-breakdown` · **Commit at handoff**: see `git log -1`

> Read this after `wake`. It exists because `PROJECT_KANBAN.md` does not yet — `wake` has no board to
> report from, so this file is the state. **Delete it once Stage 2 creates the Kanban**, which then
> becomes the live source of truth. Two sources of in-flight state is a tracking violation.

---

## One-line status

Phase 0, Stage 0.5 and Stage 1 are **complete and gated**. Stage 2 (`/plan`) is **queued, not
started**. No product code exists yet — implementation begins at Stage 3.

---

## Where the work lives

| Branch | Contains | State |
|---|---|---|
| `develop` | Original scaffold only | Untouched since `fffabf1` |
| `docs/phase0-stage1-foundation` | Phase 0 + Stage 0.5/1 output | **Committed, never pushed.** Awaiting user review. |
| `plan/stage2-task-breakdown` | Branched from the above; gap-audit corrections | **Current branch.** Stage 2 output goes here. |

Neither branch has an upstream. The git guardrail hook blocks `git push` unconditionally by user
choice, so **the user pushes, not the Supervisor** — `! git push -u origin <branch>`.

---

## What is decided (do not relitigate)

Read `memory/decisions.md` for full rationale; all nine entries are indexed in `MEMORY.md`.

- **Python + FastMCP.** Context-packer: the engine performs **no LLM inference** — reasoning always
  comes from the calling agent.
- **Two adapters, one core**: MCP (Case A: an agent calls the tools) and CLI (Case B: an agent runs
  it against a repo path). Adapters are thin; identical output required.
- **Transport: stdio by default and required**, across the container boundary via `docker run -i`.
  HTTP/SSE is opt-in and must bind `127.0.0.1` only. The harness connects **locally via Docker, never
  the internet**.
- **Dimension structure = Option D**: one `run_dimension()` pipeline owns redaction, budgeting,
  coverage and truncation; each dimension supplies `sources_sought` data + a `collect` callable. No
  base class, no registry. `collect` returns `Iterable[Excerpt]`, consumed lazily.
- **Secrets are redacted at the evidence layer** (DDR-0001, `docs/ddr/0001-*.md` — *local-only, not
  tracked in git*). Raw values never reach the agent, a report, or a log.
- **Docker ships in v1** (user decision, overriding the recommendation to defer).
- **All 7 dimensions ship in v1**: architecture, solution-fit, requirement-fidelity, test-strategy,
  security, blast-radius, code-quality.

---

## Authoritative documents

| File | Role | Tracked? |
|---|---|---|
| `PRD.md` | 35 FRs, 13 NFRs, 11 user stories, all traced. Gate: **PASS** | yes |
| `BRAINSTORMING_LOG.md` | Option D rationale + ~51 edge cases (incl. amendment) | yes |
| `memory/decisions.md` | 9 architectural decisions with rationale | yes |
| `memory/codebase-map.md` | Baseline at `fffabf1` — 0 entry points, hotspots are noise | yes |
| `docs/ddr/0001-redact-secrets-at-evidence-layer.md` | The highest-stakes decision | **no — gitignored** |
| `REQUIREMENT.md` | Original brief; superseded by `PRD.md`, kept as history | yes |

---

## Resume here — Stage 2 (`/plan`)

Run `Skill({ skill: "wake" })` first (mandatory), then:

### Step 1 — `PROJECT_SPEC.md`
From `templates/PROJECT_SPEC_template.md`. Lock in: Option D architecture, the layer map below,
stdio-first transport, and the domain glossary (evidence pack, dimension, coverage score, kit-aware
vs. standalone, scope, finding, fingerprint).

**Layer map** (from `BRAINSTORMING_LOG.md` § Surgical Scope + amendment):

```
src/easy_verifier/
  adapters/mcp_server.py    FastMCP, stdio default          FR-019, 019a/b
  adapters/cli.py           path mode, no server             FR-020, 021b
  core/pipeline.py          run_dimension() — the choke point   Option D
  core/context.py           kit detection, kit-aware|standalone FR-001..005
  core/scope.py             task|changes|worktree|project       FR-006..008
  core/redact.py            evidence-layer fingerprinting       NFR-010, DDR-0001
  core/budget.py            relevance order, lazy truncation    FR-011a/b
  core/findings.py          schema + write_report validation    FR-015, 015a
  core/synthesis.py         combined pack, aggregate coverage   FR-025, 026
  core/report.py            self-contained multi-dim HTML       FR-014, 017, 018, 018a/b
  dimensions/*.py           seven descriptors                   FR-010
```

### Step 2 — `Skill({ skill: "to-issues" })`
Tracer-bullet vertical slices. **Dependency order matters**: the pipeline contract must land before
the dimensions that implement against it.

| Wave | Tasks | Notes |
|---|---|---|
| 1 — Foundation | scaffold + `pyproject.toml`; `pipeline.py` (C2); `context.py` (C2); `scope.py` (C1); **`redact.py` (C2 / High Risk)**; `findings.py` (C1) | Blocking. Nothing else starts until the pipeline contract is fixed. |
| 2 — Dimensions | shared extraction helper + 4 doc-shaped dimensions (C1 each); security (C2); test-strategy (C2); blast-radius (C2) | Parallelizable once Wave 1 is stable |
| 3 — Output | `synthesis.py` (C1); `report.py` (C2) | |
| 4 — Adapters | `mcp_server.py` (C1); `cli.py` (C1); Docker + compose (C1) | |
| 5 — Verification | two-mode integration; FR-022 parity; **NFR-010 redaction proof test** | QA-owned |

Roughly 16–18 tasks.

### Step 3 — `PROJECT_KANBAN.md` + every `tasks/TASK_GUIDE_Txxx.md`
From `templates/`. Per task: Complexity (C0–C3), Risk, Priority, acceptance criteria drawn from the
edge-case checklists, and the Evidence table.

**The user asked to review the slicing before the guides are generated.** Present
`PROJECT_SPEC.md` + the task breakdown, stop, then generate guides on approval.

---

## Binding constraints for Stage 2 (carry into the guides)

1. **`collect` returns `Iterable[Excerpt]`, consumed lazily by `budget()`.** Non-negotiable — a
   `list` forces full materialisation on exactly the monorepo size that most needs budgeting.
2. **Redaction task is High Risk** → mandatory `security-review` at Stage 4. Its proof test (no raw
   detected value in any pack, report, log, or error message) is the Evidence-Gate artifact for
   NFR-010.
3. **Shared extraction helper for the four document-shaped dimensions only.** security,
   test-strategy and blast-radius stay bespoke — forcing them into the helper is the mistake that
   sank Option A.
4. **Every task is backend/infra — there is no UI.** Delete the UI/Design AC section from each
   TASK_GUIDE and mark all three UI Evidence rows ☐ N/A (Hard-Stop Gate 6).
5. **Test fixtures are free**: this repo is the kit-aware fixture; any installed pip package is the
   standalone fixture. No synthetic fixtures needed.
6. **Complexity floor**: anything named refactor/restructure/QA-suite/test-coverage starts at C2 /
   Medium Risk (Hard-Stop Gate 2).

---

## Open items to close during Stage 2

| # | Item | Where |
|---|---|---|
| 14 | **Is the redaction fingerprint hash salted?** Unsalted enables cross-scan correlation of the same secret; salted resists dictionary attacks on low-entropy values. | Redaction task planning; DDR-0001 follow-up |
| 15 | **FR-022 says "identical", the KPI says "byte-equal"** — timestamps and absolute paths differ between host and container runs, so byte-equality is currently unachievable as written. Needs a defined normalization or a weaker, precise word. | Parity test spec |
| — | Fingerprint format: mask width, hash algorithm, prefix length | DDR-0001 follow-up |
| — | Per-dimension vs. total byte budget in a combined pack call | `synthesis.py` task |

---

## Known issues, deliberately not fixed

- **The git guardrail hook blocks command *mentions*, not just invocations.** `grep -r 'git push'
  docs/` is blocked. Fails safe; workaround is to put such commands in a script file. Left alone
  because `.claude/hooks/**` is marked must-not-touch. Fix as a separate task if it becomes annoying.
- **`pre_bash_block_unsafe_merge.py` currently fails open** — it `exit(0)`s when `PROJECT_KANBAN.md`
  is missing, and it is missing. The gate starts working the moment Stage 2 creates the board.
- **`docs/` is gitignored by user decision**, so DDR-0001 is local-only and will not survive a clone.
  `memory/decisions.md` duplicates its rationale, but the `→ see DDR-0001` pointers in
  `decisions.md` and `MEMORY.md` will dangle for anyone else. The user was offered removal of those
  pointers and has not decided.
