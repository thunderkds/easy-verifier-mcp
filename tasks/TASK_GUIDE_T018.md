# TASK_GUIDE — T018: README documenting the intended v1 surface, with a doc-truth test
**Date**: 2026-08-25
**Complexity Level**: C1
**Risk Level**: Low
**Priority**: P2
**Assigned agent**: Backend-Implementer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. **C1** — apply the C1 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `PRD.md` — it is the source of truth for the surface being documented, and every claim in the
   README must trace to a line in it. Skim `memory/codebase-map.md` for what actually exists today.

---

## Requirement (Pillar 1 — Adapt the requirement)

Original user request: *"update the README"* — with two scoping decisions taken by the user at
Stage 2:

1. Document the **full intended v1 surface** (install, Docker, MCP registration, the complete CLI),
   not only what runs today.
2. Add a **doc-truth test** that extracts commands from the README and asserts they actually run.

**Restated intent**:
> `README.md` is currently a single line with no body. It must become the document that explains what
> easy-verifier-mcp is, what it refuses to do, and how an operator runs it — covering the full v1
> surface described in `PRD.md`, including the adapters that are not built yet — while making it
> impossible for the README to claim that an unbuilt command works.

**The tension, and how it is resolved.** The user asked for the full v1 surface *and* for commands
pinned by a test. Most of that surface (`docker run`, the MCP server, the full CLI of T015) does not
exist, so a test asserting exit 0 on every documented command cannot pass. The resolution is **not**
to narrow the README and **not** to weaken the test:

- Every command in the README is either **runnable today** or **explicitly marked as planned**.
- The doc-truth test does two jobs: runnable commands must exit 0, and any command that is not
  runnable must carry the planned marker. A command that is neither is a test failure.

This is the project's own standard applied to its documentation: state what is bounded, and never let
an absence read as a capability (NFR-002, FR-005).

**Out of scope**:
- Implementing any part of the missing surface — no MCP server, no Dockerfile, no new CLI flags.
  T014/T015/T016 own those. If the README needs a command to exist, it is marked planned, not built.
- Contributor/architecture documentation (how to add a dimension, the `run_dimension()` contract, the
  5-stage pipeline). This README is operator-facing.
- `CONTRIBUTING.md`, `docs/`, or any other file. README only.
- Changing the CLI's `--help` text, argparse surface, or any behaviour to match the docs. If the docs
  and the code disagree about what exists today, that is a finding to report, not a thing to fix.

**Requirement Refs**:
- FR-010: all seven dimensions must be named
- FR-013 / NFR-001: evidence only, no verdict, no LLM in the engine, no API key
- FR-013a: the discovery operation
- FR-016 / FR-016a: coverage score never presented without its miss list
- FR-019 / FR-019a / FR-019b: MCP adapter, stdio default, opt-in loopback-only HTTP/SSE
- FR-020 / FR-021b: CLI adapter, no server or container required
- FR-021a: Dockerfile + compose, env-var configuration, repo mounted as a volume
- FR-017: reports land in the evaluated repo's `reports/`, never the verifier's
- NFR-005: works on arbitrary repos with no setup in the target
- NFR-007 / NFR-012: never executes target code, never writes outside `reports/`, local-only
- NFR-010: secret values redacted to a fingerprint at the evidence layer
- FR-003 / FR-004: standalone mode and its limited-context warning

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (Supervisor, 2026-08-25) — including both
      scoping answers, and the stated resolution of the tension between them
- [x] Domain terms align with `PROJECT_SPEC.md` glossary — "evidence pack", "dimension", "scope",
      "kit-aware"/"standalone mode", "coverage score", "sources sought/missing" used as the kit
      defines them; the README must not coin new vocabulary for existing concepts
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] All Requirement Refs exist in `PRD.md` — verified by grep against the FR/NFR tables

> **Note for the implementer**: `README*` is itself an input to this tool in standalone mode (FR-003),
> and `docs/solutions/` may reference it. Writing this README changes what `solution-fit` and
> `requirement-fidelity` read when they run against this repo. That is expected, not a problem — but
> do not tune the prose to flatter the tool's own output.

---

## Dependencies & Reachability

**Depends on**: `None` — every documented behaviour either exists (`cli.py`, the seven dimensions) or
is explicitly marked planned. This task must not wait on T014/T015/T016.

**Entry point**: `README.md`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `README.md` documents what the tool is and states plainly that the engine performs **no** LLM inference, needs **no** API key, and returns **no** verdict — reasoning belongs to the calling agent | FR-013, NFR-001 |
| 2 | All **seven** dimension names appear, each with a one-line purpose; the list is asserted against the `DIMENSIONS` registry, not hand-copied | FR-010, FR-013a |
| 3 | Both adapters are documented: CLI (runnable now, no server, no container) and MCP (stdio default, opt-in loopback-only HTTP/SSE, Docker-mounted repo) | FR-019, FR-019a, FR-019b, FR-020, FR-021a, FR-021b |
| 4 | Every command block is either runnable today or carries an explicit planned marker; **no command is unmarked and unrunnable** | the stated resolution above; FR-005, NFR-002 |
| 5 | The four scopes (`task`, `changes`, `worktree`, `project`) are documented with the selector each requires, including that a narrow scope missing its selector gathers **no** evidence rather than widening | FR-006, FR-008 |
| 6 | The safety posture is stated: never executes target code, never writes outside `reports/`, local-only with no outbound request, secrets fingerprinted at the evidence layer | NFR-007, NFR-010, NFR-012, FR-017 |
| 7 | Coverage score is never shown or described without its accompanying miss list | FR-016, FR-016a |
| 8 | Standalone mode and its limited-context warning are documented, as is kit-aware detection | FR-003, FR-004 |
| 9 | A doc-truth test extracts fenced command blocks from `README.md` and asserts: runnable ones exit 0, unrunnable ones are marked planned | user decision (doc test) |
| 10 | The test fails if a documented dimension name is not in the registry, or a registry dimension is undocumented — drift in either direction | FR-010 |
| 11 | Nothing outside `README.md` and the new test file changes — no source, no CLI behaviour, no other doc | Scope Locking |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | The README's runnable command blocks, executed against this repo | every one exits 0 | automated test |
| 2 | A command block naming an unbuilt surface (`docker run`, MCP server) | present in the README **and** carrying the planned marker | automated test |
| 3 | A dimension added to or removed from `DIMENSIONS` without a README edit | the doc-truth test fails, naming the drifted dimension | automated test |
| 4 | An unmarked command block that does not run, injected into a copy of the README | the test fails — the marker cannot be omitted silently | automated test |
| 5 | A newcomer reading only the README | can tell which commands work today and which are planned, without consulting the KANBAN | manual, at review |

### Verification Command (exact, runnable)

```bash
pytest tests/test_t018_readme.py -q
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T018.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T018.md`.

---

## Approach

**Pattern reference**: `tests/test_t001_pipeline.py::test_registry_is_a_plain_dict_of_descriptors` for
asserting against the `DIMENSIONS` registry rather than a hand-copied list; `PROJECT_SPEC.md` and
`PRD.md` for the vocabulary and the surface being described.

Write the README from `PRD.md`, not from the code — the code is a partial implementation of it, and
documenting the code would produce the narrower README the user explicitly declined. Then reconcile:
for each command, decide runnable-today or planned, and mark accordingly.

**Suggested marker convention** (pick one and apply it uniformly; the test enforces whatever you
choose, so define it in one constant used by both the README and the test): a fenced block whose
info string or immediately preceding line carries a literal `planned` token, e.g. a line reading
`> **Planned (T014).**` directly above the block. Name the owning task where you know it — a reader
who wants the timeline can then find it on the board.

The doc-truth test should parse the README once into `(marker, language, command)` triples and drive
two assertions over that list. Resist the urge to run *every* block: a block marked planned must
**not** be executed, and a block that is runnable must not be skipped for convenience. Run runnable
commands against a `tmp_path` copy or this repo with `--repo`, never in a way that writes anything.

Keep the prose short. This project's documents are dense because they are audit trails; a README is
not one. Aim for something a newcomer reads to the end.

---

## Edge Case Checklist

- [ ] A command that is runnable but slow (whole-repo `project` scope) → keep the documented examples
      cheap, or the test suite pays for it on every run
- [ ] A command containing a placeholder the reader must substitute (`/path/to/repo`) → it cannot be
      executed verbatim; decide whether it counts as runnable and make the test's rule explicit
- [ ] Multi-line commands with continuations → the parser must not split them into broken fragments
- [ ] A fenced block that is **output**, not a command (`console` showing a pack) → must not be
      executed; distinguish by info string, and state the convention
- [ ] Windows/PowerShell variants → out of scope, but do not write commands that only work in zsh
- [ ] A command that writes a report → must target a tmp dir; the test must not leave `reports/` in
      this repo (FR-017 is about the *evaluated* repo, and here they are the same repo)
- [ ] The README's own text matching a secret detector (an example token) → use the project's
      `FAKEfake…` convention, never a realistic credential shape
- [ ] `--budget-bytes 0` tracebacks (known open follow-up) → do not document it as an example
- [ ] A dimension name that appears in prose but not as a documented dimension (e.g. discussing
      "security" generally) → the drift test must not false-positive on it

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `README.md` | Rewrite from one line to the full operator-facing document |
| `tests/test_t018_readme.py` | New — doc-truth and registry-drift tests |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/**` | Documentation task. If docs and code disagree, report it — do not change code to match |
| `.claude/hooks/**` | Must-not-touch |
| `PRD.md`, `PROJECT_SPEC.md` | The sources being documented; Supervisor-owned |
| `memory/**`, `PROJECT_KANBAN.md` | Supervisor-only |
| `tasks/TASK_GUIDE_T0*.md` (other tasks) | Not yours |

---

## Test Plan

`tests/test_t018_readme.py` — parse `README.md` once, then:

1. every runnable block exits 0 (subprocess, against this repo or a `tmp_path`, writing nothing);
2. every non-runnable block carries the planned marker;
3. the documented dimension set equals `set(DIMENSIONS)`, failing in both directions and naming the
   offender;
4. a negative case: an unmarked, unrunnable block injected into a **copy** of the README must fail
   the rule — this is what stops the marker convention from being silently optional (Success
   Criterion 4). Without it, a future edit can drop a marker and the suite stays green.

Note the reviewer will re-run these against a README built to embarrass them, per this project's
standing review procedure.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: N/A (Low risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T018.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
