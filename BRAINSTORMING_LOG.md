# BRAINSTORMING_LOG.md
**Generated**: 2026-08-14
**Task / Context**: Phase 0 + Stage 0.5 — `easy-verifier-mcp` v1 architecture
**Skill**: `Skill({ skill: "brainstorming" })`
**Scope tier**: Standard

---

## The Problem Space

Build an MCP server + CLI that evaluates code and features honestly — grounded in real repository
evidence, explicit about what it could not see, and never inventing missing context.

**Non-negotiable constraints** (locked in Phase 0 and Stage 0.5 grilling):

| Constraint | Source |
|---|---|
| Engine performs **no** LLM inference; reasoning always comes from the caller | NFR-001 |
| Two entry points — MCP (agent calls tools) and CLI (agent runs against a repo path) — over one core, producing identical output | FR-019…FR-022 |
| Seven dimensions ship in v1, each separately callable | FR-009, FR-010 |
| Secret values redacted at the evidence layer, structurally not conventionally | NFR-010, DDR-0001 |
| Reports are self-contained HTML written into the **target** repo's `reports/` | FR-014…FR-018 |
| Docker ships in v1 | FR-021a |
| Python + `mcp` SDK (FastMCP) | NFR-008 |

**The actual design challenge** is narrower than it first appears. The big forks are already
closed. What remains open — and what drives the shape of seven-plus implementation tasks — is how
the dimensions are structured such that cross-cutting rules (redaction, byte budgeting, coverage
scoring, truncation reporting) are **impossible to bypass** rather than merely documented.

That framing makes NFR-010 the discriminator between options, not elegance or line count.

**Verified codebase state** (checked with `find`/`ls`, not assumed): zero product source. All 35
`.py` files are harness hooks under `.claude/hooks/` and skill scripts under `.claude/skills/`. No
`STRATEGY.md`, no `PROJECT_SPEC.md` (Stage 2 produces it), no `docs/legacy/` — Legacy Mode does not
apply. Implementation is greenfield.

**Free test fixture discovered**: this repository is itself kit-managed (`PRD.md`, `tasks/`,
`memory/`, `templates/`). It can serve as the kit-aware integration fixture, with any installed pip
package as the standalone fixture — no synthetic fixtures needed for the two-mode parity test.

---

## Questions for the User

All Phase 0 and grilling ambiguities are resolved (PRD Open Questions table, items 1–8). The single
open architectural question was dimension structure — **answered: Path D** (see User Selection).

Deferred to Stage 2, not blocking:

1. Fingerprint format for redaction — mask width, hash algorithm, prefix length (DDR-0001 follow-up).
2. Whether the redaction hash is salted — unsalted enables cross-scan correlation, salted resists
   dictionary attacks on low-entropy values (DDR-0001 follow-up).
3. Exact relevance-ranking function for budget ordering beyond the three declared tiers.

---

## Alternative Paths

| Option | Name | Summary | Invasiveness | Code Volume | Regression Risk | Recommended? |
|--------|------|---------|-------------|------------|----------------|--------------|
| A | The Minimalist Path | Dimensions are pure data; one generic runner | Low | ~400 lines | Medium | |
| B | The Scalable Path | Plugin registry + abstract base class | Medium | ~900 lines | Low | |
| C | The Simple Path | Seven flat modules calling shared helpers | Low | ~600 lines | **High** | |
| D | The Hybrid Path | Pipeline function + dimension descriptors | Low | ~550 lines | Low | ✅ Yes |

### Option A — The Minimalist Path (declarative specs)

**Approach**: Each dimension is a `DimSpec` data object — sources sought, glob patterns, regex
extractors, extraction mode. A single generic runner interprets all seven. No custom code per
dimension.

**Pros**: Smallest possible surface. Cross-cutting rules trivially enforced (one runner). New
dimensions are config, not code. Highly testable — specs are inspectable data.

**Cons**: Assumes every dimension reduces to "glob, match, extract". Expressiveness ceiling is low
and hit early.

**Why it might fail**: Two of the seven dimensions do not fit the shape. **Blast-radius** requires
import/dependency-graph traversal to determine what a change reaches. **Test-strategy** requires
parsing coverage reports and mapping tests to acceptance criteria. Neither is a glob-and-match.
The predictable outcome is an `escape_hatch: Callable` field on `DimSpec`, at which point the
design has silently become Option D but with a vestigial declarative layer nobody can delete — the
worst of both. Rejecting A is really rejecting the *pretence* that seven heterogeneous analyses are
homogeneous.

### Option B — The Scalable Path (plugin registry + base class)

**Approach**: Abstract `Dimension` class with a `final` `run()` template method owning the
pipeline; subclasses override `collect()`. A decorator-based registry auto-populates the MCP tool
list and CLI subcommands.

**Pros**: Structurally enforces NFR-010 — `run()` is final, subclasses cannot bypass redaction.
Directly serves the "everything is a plugin" conceptual reference (REQUIREMENT.md line 77).
Genuinely the right answer *if* third-party dimensions are ever expected.

**Cons**: Inheritance ceremony, decorator magic, and registry indirection bought for extensibility
nobody has requested. Import-time registration makes test isolation and error messages worse.

**Why it might fail**: It is a plugin system for seven known plugins that all ship simultaneously in
the same release, written by the same team. YAGNI in its textbook form. The registry adds a
failure mode that flat wiring does not have — a dimension silently missing because its module was
never imported. Worth revisiting only if third-party dimensions become a real requirement; the
migration from D to B is mechanical.

### Option C — The Simple Path (flat modules + shared helpers)

**Approach**: Seven plain modules, each exporting `collect(repo, scope, budget) -> EvidencePack`,
calling shared helper functions for context loading, redaction, budgeting and coverage. Adapters
hold an explicit name→function dict.

**Pros**: Zero indirection. Easiest possible code to read, debug, and step through. Each dimension
is independently comprehensible with no framework knowledge.

**Cons**: Every cross-cutting rule is a convention the dimension author must remember to honour.

**Why it might fail**: This is the option that fails **silently and in production**. Redaction
becomes a line an implementer can omit — and omitting it violates NFR-010 and DDR-0001 without any
test necessarily catching it, because the dimension still returns a perfectly valid-looking pack.
The failure surfaces as a committed HTML file containing a live credential. DDR-0001 exists
specifically to make that outcome structurally impossible; Option C reintroduces it as a code-review
responsibility. Rejected on those grounds despite being the most pleasant code to read.

### Option D — The Hybrid Path (pipeline function + descriptors) — **SELECTED**

**Approach**: One module-level `run_dimension(spec, repo, scope, budget)` function owns the full
pipeline: resolve context → call `spec.collect(ctx)` → redact → budget and truncate → compute
coverage → assemble `EvidencePack`. Each dimension supplies a descriptor: a `sources_sought` data
list plus a single `collect` callable returning raw excerpts. No base class, no registry, no
decorators — `DIMENSIONS` is an explicit dict.

```
run_dimension(spec, repo, scope, budget) ->
    ctx      = load_context(repo, scope)        # kit-aware | standalone
    sources  = spec.sources_sought              # data, declared per dimension
    raw      = spec.collect(ctx)                # the ONLY dimension-specific code
    safe     = redact(raw)                      # NFR-010 — unbypassable
    kept     = budget(safe, limit, order_by=relevance(scope))
    cov      = coverage(sources, ctx.found)     # FR-016 found/sought
    return EvidencePack(kept, cov, truncated=..., omitted=...)
```

**Pros**: Redaction, budgeting, coverage and truncation live in exactly one place a dimension author
cannot reach around — the NFR-010 guarantee is structural. `collect` is an ordinary function, so
blast-radius can traverse a graph and test-strategy can parse coverage reports without any escape
hatch. Both adapters call the same function, making FR-022 parity nearly free rather than a thing to
maintain. Descriptors are plain data and dimensions are plain functions, so both test trivially with
no framework scaffolding.

**Cons**: One layer of indirection more than Option C. `collect` returning raw unredacted excerpts
means the redaction boundary is a contract the pipeline enforces at one point — that point needs its
own dedicated test (already a DDR-0001 follow-up).

**Why it might fail**: If a future dimension needs to *stream* rather than return a complete list —
say, scanning a very large monorepo where materialising all excerpts before budgeting exhausts
memory — the `collect() -> list` signature forces a full materialisation before the budget stage
can discard 90% of it. This is a real ceiling, not a hypothetical one, and it is hit by exactly the
repo size that most needs budgeting. **Mitigation**: type `collect` as returning `Iterable[Excerpt]`
from day one and have `budget()` consume it lazily, so the pipeline can stop pulling once the byte
ceiling is reached. Costs nothing now; removes the ceiling entirely. This mitigation is carried into
Next Actions as a binding constraint on the core task, not an optional nicety.

---

## 50% Rule Check

**Can Option D's business goal be met with 50% less code?**

Partly, and the analysis is worth recording because it shapes the task breakdown.

The ~550-line estimate splits roughly into ~200 lines of shared pipeline (context loading,
redaction, budgeting, coverage, pack assembly) and ~350 across seven `collect` functions. The
pipeline half is irreducible — it is the NFR-010/FR-011a/FR-016 enforcement and every line does
required work.

The dimension half **is** compressible. Four of the seven — architecture, solution-fit,
requirement-fidelity, code-quality — are genuinely "locate these artifacts, extract relevant
excerpts". They can share one parameterised `collect` helper driven by their `sources_sought`
declarations, reducing four bespoke functions to four short declarations plus one shared helper.
That is Option A's insight, applied only where it actually holds, and it removes perhaps 150 lines.

The remaining three — security (regex + entropy scanning), test-strategy (coverage parsing), and
blast-radius (graph traversal) — carry irreducible bespoke logic. Forcing them into a shared helper
is precisely the mistake Option A makes.

**Conclusion**: adopt the shared artifact-extraction helper for the four document-shaped dimensions;
keep the other three bespoke. Roughly 25–30% reduction, not 50%. Claiming 50% here would require
pretending the three analytical dimensions are simpler than they are — the kind of unfounded
optimism this project exists to flag in others.

---

## Recommended Path

**Option D — The Hybrid Path (pipeline function + descriptors)**

It is the only option that satisfies the NFR-010 enforcement requirement *structurally* while
remaining proportionate to seven known dimensions shipping in one release.

Option C fails the enforcement requirement outright. Option A fails on expressiveness and would
converge on D anyway, having accumulated a vestigial layer. Option B satisfies enforcement but pays
registry-and-inheritance ceremony for extensibility that is not a requirement — and if it ever
becomes one, the D→B migration is mechanical (wrap the dict in a registry, promote descriptors to
classes) rather than a rewrite.

D also makes the two hardest guarantees cheap: FR-022 adapter parity falls out of both adapters
calling one function, and the DDR-0001 redaction proof becomes a single-choke-point test rather than
seven per-dimension tests.

---

## Surgical Scope

Files that **should** be created (all greenfield):
- `src/easy_verifier/core/pipeline.py` — `run_dimension()`; owns redaction, budgeting, coverage
- `src/easy_verifier/core/context.py` — kit detection, kit-aware vs. standalone loading (FR-001…005)
- `src/easy_verifier/core/scope.py` — task | changes | worktree | project resolution (FR-006…008)
- `src/easy_verifier/core/redact.py` — evidence-layer fingerprinting (NFR-010, DDR-0001)
- `src/easy_verifier/core/budget.py` — relevance ordering, lazy truncation (FR-011a/b)
- `src/easy_verifier/core/findings.py` — findings schema + `write_report` validation gate (FR-015)
- `src/easy_verifier/core/report.py` — self-contained HTML renderer (FR-014, FR-017, FR-018)
- `src/easy_verifier/dimensions/*.py` — seven descriptors (FR-010)
- `src/easy_verifier/adapters/mcp_server.py` — FastMCP HTTP/SSE (FR-019)
- `src/easy_verifier/adapters/cli.py` — path-mode entry point (FR-020)
- `Dockerfile`, `compose.yaml` — v1 packaging (FR-021a)
- `tests/` — unit, parity, and two-mode integration suites

Files that **must not** be touched:
- `.claude/hooks/*.py` — harness machinery, unrelated to the product; 8 hook scripts
- `.claude/skills/**` — harness skills; the verifier augments Stage 4, it does not replace it
- `templates/*` — kit templates consumed by the Supervisor, not product code
- `CLAUDE.md`, `AGENTS.md` — governance documents
- `REQUIREMENT.md` — the original brief; a historical record, superseded by `PRD.md`
- **Any file in a target repository other than `reports/`** — NFR-007, enforced at runtime

---

## Edge Case Checklist for TASK_GUIDE

Copy the relevant subset into each `TASK_GUIDE_Txxx.md` Edge Case section.

**Context detection**
- [ ] Target repo has `tasks/` but no `PROJECT_SPEC.md` — partial kit. Must not claim full kit-aware mode
- [ ] Target repo has kit files that are empty or template-placeholder text — present but worthless
- [ ] Target path is not a git repository at all — `changes` scope must fail clearly, not crash
- [ ] Target path does not exist, or is a file rather than a directory
- [ ] Target repo is a git worktree or submodule — git commands resolve unexpectedly
- [ ] Symlinks pointing outside the target repo — must not escape the repo boundary

**Scope resolution**
- [ ] `changes` scope on a repo with zero commits, or on the very first commit (no parent to diff)
- [ ] `changes` scope on a branch with no divergence from its base — empty diff, not an error
- [ ] `worktree` scope with no uncommitted changes — empty result must render a valid report
- [ ] `task` scope naming a task ID with no matching `TASK_GUIDE` file
- [ ] Detached HEAD state

**Redaction (NFR-010 / DDR-0001)**
- [ ] Secret appears in a filename or directory path, not only in file content
- [ ] Secret spans multiple lines, or is base64/JSON-embedded
- [ ] Secret appears in a binary file, or in a file with invalid UTF-8
- [ ] Detected value is a test fixture or documented placeholder — false positive is expected and acceptable
- [ ] Redaction must apply to the coverage list and truncation metadata, not only excerpts
- [ ] **Proof test**: no raw detected value appears in any pack, report, log, or error message

**Budget and truncation**
- [ ] A single file exceeds the whole 120 KB dimension budget on its own
- [ ] Budget is set to zero or a negative value
- [ ] Truncation occurs — `truncated` flag and `omitted` count must be present and accurate
- [ ] Relevance ordering with an empty changed-file set (`project` scope) — must still be deterministic
- [ ] Very large monorepo — `collect` must stream lazily, never materialise all excerpts (see Option D failure analysis)

**Findings validation and reporting**
- [ ] Finding submitted with an evidence ref but no confidence value — must be rejected
- [ ] Finding submitted with confidence but no evidence ref — must be rejected
- [ ] Finding whose evidence ref points to a file not present in the pack — dangling citation
- [ ] Empty findings list — must render a valid "no findings" report, not crash
- [ ] `reports/` does not exist, or exists and is read-only
- [ ] Two reports written in the same second — filename collision
- [ ] Target repo is read-only or mounted read-only in Docker — must fail with a clear message
- [ ] Rendered HTML contains no external URL (self-containment assertion, FR-018)
- [ ] Findings text containing HTML/script — must be escaped, not injected into the report

**Adapter parity (FR-022)**
- [ ] Same repo + scope + dimension via MCP and via CLI produce identical evidence packs
- [ ] Docker path mapping — container paths must not leak into reports written for the host
- [ ] CLI `write-report` accepts both `--findings <path>` and stdin JSON, with identical results

---

## Next Actions

For the Supervisor to incorporate into Stage 2 (`/plan` → `to-issues` → TASK_GUIDE generation).

1. Generate `PROJECT_SPEC.md` recording Option D as the locked architecture, with the layer map from
   Surgical Scope.
2. Break into vertical slices via `to-issues`. Sequence the core pipeline, context layer, redaction
   and findings-validation tasks **before** the seven dimension tasks — the dimensions depend on the
   pipeline contract.
3. Bind the lazy-streaming mitigation into the core pipeline task: `collect` returns
   `Iterable[Excerpt]` and `budget()` consumes it lazily. Non-negotiable, per Option D's failure
   analysis.
4. Apply the 50% Rule outcome: one shared artifact-extraction helper serving architecture,
   solution-fit, requirement-fidelity and code-quality; bespoke `collect` for security,
   test-strategy and blast-radius.
5. Mark the redaction task **High Risk** — it triggers mandatory `security-review` at Stage 4, and
   its proof test is the Evidence-Gate artifact for NFR-010.
6. Assign Complexity floors: core pipeline C2, redaction C2, blast-radius dimension C2, remaining
   dimensions C1, adapters C1, Docker C1.
7. Use this repository as the kit-aware integration fixture and an installed pip package as the
   standalone fixture — no synthetic fixtures required.
8. Close DDR-0001 follow-ups 1 and 2 (fingerprint format, salting) during redaction task planning.

---

## User Selection

> **Approved direction**: Option D — The Hybrid Path (pipeline function + dimension descriptors)
> Approved by user on 2026-08-14.

---

## Amendment — Stage 2 pre-flight gap audit (2026-08-14)

Appended after the session, not rewritten: the analysis above stands, but a gap audit against
`REQUIREMENT.md` found three things this log omitted. Option D is unaffected.

**1. A missing module.** `REQUIREMENT.md` §4 names a *synthesis + suggestion layer* among its five
internal layers. The Surgical Scope list above has no such module. Recovered as
`src/easy_verifier/core/synthesis.py` — the combined-pack operation (FR-025) and aggregate coverage
summary. It performs no interpretation: aggregation and presentation are mechanical and belong to
the engine, while deciding what findings mean together stays with the caller (FR-026).

**2. Transport corrected.** The log assumed HTTP/SSE throughout, inherited from `easy-ui-mcp`. The
harness in fact connects **locally through a Docker container, never the internet**. stdio is now the
default and required transport (FR-019a); HTTP/SSE is opt-in and loopback-bound (FR-019b). This
*reduces* adapter complexity — no port, no lifecycle, no bind-address decision by default.

**3. Report scope was undefined.** Reports must span multiple dimensions in one document (FR-018a),
which makes `report.py` a consumer of `synthesis.py` rather than of a single pack.

### Added to Surgical Scope

- `src/easy_verifier/core/synthesis.py` — combined pack, aggregate coverage (FR-025, FR-026)

### Additional Edge Cases for TASK_GUIDE

**Synthesis & multi-dimension reporting**
- [ ] Combined pack requesting a dimension name that does not exist — must name the bad one, not fail silently
- [ ] Combined pack where one dimension throws and the others succeed — partial result must be explicit, never silently dropped
- [ ] Aggregate coverage across dimensions with different `sources_sought` lists — must not double-count a shared source
- [ ] Per-dimension byte budgets in a combined call — does the budget apply per dimension or in total? Must be defined and tested
- [ ] Finding tagged with a dimension absent from the report's packs — dangling dimension reference
- [ ] Report rendering when every dimension returned zero findings

**Transport & container**
- [ ] stdio transport must not write anything to stdout except protocol frames — a stray `print()` corrupts the stream
- [ ] HTTP/SSE flag must refuse to bind a non-loopback address, including `0.0.0.0` inside a container
- [ ] Container path leakage: a repo mounted at `/workspace` must produce host paths in the report (FR-021c)
- [ ] Target repo mounted read-only with a writable `reports/` — the intended NFR-013 posture
- [ ] Container runs as non-root and cannot write outside `reports/`
- [ ] No outbound network request is made by any dimension (NFR-012) — assertable in test

**Findings validation (strengthened)**
- [ ] Finding missing confidence but carrying evidence — **rejected** (FR-015, corrected reading)
- [ ] Finding missing evidence but carrying confidence — **rejected**
- [ ] Evidence reference pointing at an item not in the cited pack — **rejected** (FR-015a)
- [ ] Suggested-improvement field absent — allowed; it is optional (FR-023)
