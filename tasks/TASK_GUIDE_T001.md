# TASK_GUIDE — T001: Tracer bullet — scaffold, pipeline contract, architecture dimension, minimal CLI
**Date**: 2026-08-15
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P0
**Assigned agent**: Common-Infrastructure-Agent
**Agent guide**: `.claude/agents/common-infrastructure.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/common-infrastructure.md`
5. Note the **Complexity Level** above and apply the matching process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. **C2** — read `memory/codebase-map.md` (baseline snapshot; the repo has no product code yet, so expect it to be near-empty)

Also read `BRAINSTORMING_LOG.md` § Option D — this task implements that decision literally.

---

## Requirement (Pillar 1 — Adapt the requirement)

Stand up the project skeleton and prove the Option D architecture end-to-end with one thin vertical
slice: a real repository goes in, a real evidence pack comes out, through the same
`run_dimension()` function that all seven dimensions will later use.

**Restated intent**:
> After this task, `python -m easy_verifier.adapters.cli architecture --repo .` prints a structured
> evidence pack for the architecture dimension of a real repo — files actually read, citable
> excerpts with line references, sources sought but not found, and a coverage score. The pipeline
> contract that produced it is now fixed, and every later dimension is written against it.

**Out of scope**:
- Real secret redaction — this task ships the **seam** (a mandatory `redact` call inside
  `run_dimension()`), and T004 fills it with the real detector. Ship an identity-passthrough
  placeholder that is clearly marked and unit-tested as a seam, not as redaction.
- Kit/standalone mode detection (T002) — assume kit-aware, probe for `PROJECT_SPEC.md` only.
- Scope selection (T003) — assume `project` scope.
- Real relevance ordering and budgeting (T005) — a naive byte cap with a truncation field is enough.
- MCP adapter, Docker, HTML reports, the other six dimensions.

**Requirement Refs**:
- FR-009: each dimension is a separate callable unit, not a monolithic `evaluate`
- FR-010 (partial): the `architecture` dimension, 1 of 7
- FR-011: evidence pack returns files read, citable excerpts with path + line refs, sources sought but not found
- FR-013: no verdict, score, or judgment produced by the engine
- FR-016: coverage score = unweighted `found / sought`
- FR-020, FR-021 (partial): CLI adapter delegating to a shared core, no logic of its own
- NFR-001: no LLM call, no model API key
- NFR-008: Python + `mcp` SDK (FastMCP) is the mandated runtime

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: `None` — this is the first task; it creates the tree everything else lands in.

**Entry point**: `run_dimension`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `pip install -e .` succeeds from a clean venv on Python 3.11+; `easy_verifier` is importable | Scaffold |
| 2 | `run_dimension(descriptor, repo_path)` returns an `EvidencePack` with fields: `dimension`, `mode`, `scope`, `files_read`, `excerpts`, `sources_sought`, `sources_found`, `sources_missing`, `coverage_score`, `truncated`, `omitted_count` | FR-011, FR-016 |
| 3 | Each excerpt carries `path`, `start_line`, `end_line`, `text` — no excerpt may exist without a resolvable path and line range | FR-011 |
| 4 | The `architecture` dimension is expressed as static descriptor data (`name`, `purpose`, `sources_sought`) plus a `collect` callable — **no base class, no registry, no subclassing** | Option D, FR-009 |
| 5 | `collect` returns an `Iterable[Excerpt]` and is consumed lazily — a test proves a generator that raises on item N+2 still yields N excerpts through a cap admitting N (the pipeline pulls item N+1, rejects it, and stops; it never reaches N+2) | Critical Constraint 3 |
| 5a | `omitted_count` counts **only items actually pulled and rejected** and is documented in the field itself as a lower bound. The pipeline must never drain the remainder to produce an exact total — for a file-reading `collect`, "just counting" means reading every file, which is the exact monorepo cost budgeting exists to avoid | Critical Constraint 3, FR-011b |
| 6 | `coverage_score == len(sources_found) / len(sources_sought)`, unweighted, and the pack always carries the named `sources_missing` list alongside it | FR-016, FR-016a |
| 7 | The `EvidencePack` contains **no** verdict, rating, grade, pass/fail, or severity field | FR-013 |
| 8 | `run_dimension()` calls the redaction seam on every excerpt before it enters the pack; a test asserts a dimension cannot construct a pack without passing through the seam | NFR-010 (seam only) |
| 9 | A source listed in `sources_sought` that does not exist in the target repo appears in `sources_missing` and is **never** substituted with invented content | FR-005, NFR-002 |
| 10 | `cli.py` contains no file reading, no excerpt building, and no coverage arithmetic — it parses args, calls the core, and serializes | FR-021 |
| 11 | Nothing in `easy_verifier` imports an LLM client or reads a model API key; a test greps the package for such imports | NFR-001 |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | This repo (`easy-verifier-mcp`) as target, `architecture` dimension | Pack lists `PROJECT_SPEC.md` in `files_read`, excerpts cite it with real line numbers, `coverage_score` is between 0 and 1 | automated test |
| 2 | A temp dir containing no docs at all | Pack returns successfully with empty `excerpts`, `coverage_score == 0.0`, and every declared source in `sources_missing` — no crash, no invented content | automated test |
| 3 | A `collect` generator yielding 10 excerpts with a byte cap that admits 3 | `truncated is True`; `omitted_count == 1` — the one item pulled and rejected — documented as a **lower bound**, not a total; the generator is advanced exactly one item past the admitted set and no further | automated test |
| 4 | A dimension descriptor whose `collect` yields an excerpt containing a fake secret | The seam was invoked on it (assert via spy/monkeypatch) | automated test |

### Verification Command (exact, runnable)

```bash
pip install -e ".[dev]" && pytest tests/test_t001_pipeline.py -q && \
  python -m easy_verifier.adapters.cli architecture --repo . | head -40
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T001.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T001.md`.

---

## Approach

**Pattern reference**: `None — no comparable prior art in this repo` (this task creates the first product code; imitate the repo's existing Markdown/tooling conventions and standard `src/` layout).

Implement Option D exactly as decided in `BRAINSTORMING_LOG.md`:

- `run_dimension(descriptor, repo_path, scope, budget_bytes=120_000)` is **the single choke point**.
  It owns redaction, ordering, budgeting, truncation reporting and coverage arithmetic. A dimension
  never touches any of those.
- A dimension is a plain module exposing a descriptor: `name`, `purpose`, `sources_sought` (static
  list of strings), and `collect(ctx) -> Iterable[Excerpt]`. That is the entire contract. Resist any
  urge to add a `Dimension` base class, an `@register` decorator, or a plugin loader — the whole
  point of Option D is that dimensions cannot bypass the pipeline because they never own it.
- Use dataclasses for `Excerpt` and `EvidencePack`. No ORM, no pydantic unless the MCP SDK already
  requires it for tool schemas — check before adding a dependency.
- The redaction seam should be a module-level function in `core/redact.py` with the real signature
  T004 will implement (`redact(text: str) -> str`), shipping as a documented passthrough. Do **not**
  invent a partial detector now — a half-built detector is worse than an obvious placeholder,
  because it looks finished.

Get the whole path working thin before making any part of it good. That is the point of a tracer
bullet: the contract is what this task delivers, not the quality of the architecture dimension.

---

## Edge Case Checklist

- [ ] Target repo path does not exist, or is not a directory → clear error, no traceback dump
- [ ] Target repo is not a git repository → must still work for `project` scope (git is only needed for `changes`)
- [ ] A declared source exists but is empty (0 bytes) → counts as found, contributes no excerpt
- [ ] A declared source exists but is unreadable (permissions) → treated as missing, with a stated reason; never crashes the run
- [ ] A file is binary or has invalid UTF-8 → skipped, not decoded with replacement characters into an excerpt
- [ ] A symlink points outside the repo → not followed
- [ ] `sources_sought` is empty → coverage score is `None`, not a ZeroDivisionError, and is not rendered as `0.0` (which would falsely read as total failure)
- [ ] Byte cap smaller than the first excerpt → `truncated is True`, `excerpts` empty, `omitted_count == 1` — not an infinite loop or a negative remainder
- [ ] Stream ends exactly at the budget boundary → `truncated is False`, `omitted_count == 0`. The rejected-item rule gives this for free (nothing was pulled and rejected), which is why it is preferred over "stop when used >= budget", whose `truncated` would be a false positive here
- [ ] Extremely long single line (minified file) → excerpt is bounded, not a 5 MB string
- [ ] Line numbers are 1-indexed and match what an editor shows (off-by-one here poisons every citation downstream)

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `pyproject.toml` | New — package metadata, Python 3.11+, deps (`mcp`), `[dev]` extra (pytest), src layout |
| `src/easy_verifier/__init__.py` | New — version only |
| `src/easy_verifier/core/models.py` | New — `Excerpt`, `EvidencePack`, `DimensionDescriptor` dataclasses |
| `src/easy_verifier/core/pipeline.py` | New — `run_dimension()`, the choke point |
| `src/easy_verifier/core/redact.py` | New — documented passthrough seam with T004's final signature |
| `src/easy_verifier/dimensions/architecture.py` | New — descriptor + `collect` |
| `src/easy_verifier/adapters/cli.py` | New — minimal argparse entry, serialize pack to JSON |
| `tests/test_t001_pipeline.py` | New — acceptance tests |
| `.gitignore` | Add Python artifacts (`__pycache__`, `*.egg-info`, `.venv`, `.pytest_cache`) |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `.claude/hooks/**` | Marked must-not-touch (`PROJECT_SPEC.md` Critical Constraint 10) |
| `PRD.md`, `REQUIREMENT.md`, `BRAINSTORMING_LOG.md` | Requirement history — changes go through the Supervisor |
| `memory/**` | Supervisor-only writes (Memory Write Protocol) |
| `PROJECT_KANBAN.md` | Supervisor updates task status, not the implementing agent |

---

## Test Plan

Unit + integration in one file, `tests/test_t001_pipeline.py`:

1. **Pack shape** — every field in AC #2 present with the right type; assert no verdict-shaped field exists (AC #7) by name-checking the dataclass fields against a forbidden list.
2. **Laziness** — a generator that raises `AssertionError` on item **N+2**, under a cap admitting **N**, proves the pipeline pulled N+1 (rejected it, set `truncated`) and stopped without reaching N+2. This is the test that stops constraint 3 from silently regressing. The one-item overshoot is deliberate and bounded: it is what makes `truncated` honest without draining the stream.
3. **Coverage arithmetic** — parameterised over found/sought combinations including empty-sought.
4. **No-invention** — run against an empty temp dir; assert every excerpt's `path` exists on disk.
5. **Redaction seam** — monkeypatch `redact` to a spy; assert it saw every excerpt's text.
6. **No-LLM** — walk the package source, assert no `import openai|anthropic|google.generativeai` and no `API_KEY` env read.
7. **CLI thinness** — a structural test asserting `adapters/cli.py` contains no `open(` / `Path.read_text` call.

This is C2 with a Medium risk: the implementing agent writes the tests, but the Supervisor signs off
on this Test Plan as the oracle before the spawn, per the Evaluation rule.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk — required)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T001.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — CLI confirmed producing a real pack against this repo
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
