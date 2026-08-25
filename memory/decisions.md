# decisions.md — Architectural Decisions (the "why")

> Cold-tier memory. Supervisor-only writes. Indexed from `memory/MEMORY.md`.

---

## 2026-08-14 — Context-packer architecture: no LLM inside the engine

**Decision**: `easy-verifier-mcp` performs no model inference. Evaluation dimensions gather and
structure evidence; all reasoning is performed by the calling agent. In MCP mode the caller is the
main agent; in path/CLI mode the caller is the user's agent CLI.

**Why**: Removes API-key requirement and cost from the engine, and removes the engine as a
hallucination source entirely — it can only report what it actually read. Directly serves
`REQUIREMENT.md` NFR "must never invent missing context".

**Trade-off accepted**: the engine cannot produce a report unaided; a caller is always required.

---

## 2026-08-14 — Two adapters, one core

**Decision**: Two entry points over one shared core library — `mcp_server.py` (FastMCP, HTTP/SSE)
and `cli.py` (target repo by filesystem path). Adapters are thin and hold no evaluation,
context-loading, or rendering logic. Both must produce identical output for identical input.

**Why**: The two real usage cases are an agent calling the MCP, and a single agent running the
verifier directly against a repo path. Case B must work with no server process running, which is
what "works on any repository" requires.

---

## 2026-08-14 — Two-step report flow

**Decision**: Evidence packs are returned to the caller; the caller reasons; the caller submits
findings as structured JSON to `write_report`, which validates and renders the HTML into the target
repo's `reports/`.

**Why**: The only shape that keeps the engine free of reasoning (see above) while still producing a
report containing actual judgments, as `REQUIREMENT.md` §5 requires.

---

## 2026-08-14 — Redact secrets at the evidence layer, not the report layer

**Decision**: Detected secret values are replaced with a non-reversible fingerprint (masked prefix +
hash prefix) at the moment they enter an evidence pack. The raw value never reaches the calling
agent, a report, or a log. Detector name, file path, and line number are preserved.

**Why**: The security dimension greps a target repo for secrets and the result is rendered into an
HTML file written **inside that same repo** — likely to be committed. Without redaction the verifier
would materialize a plaintext secrets inventory that did not previously exist as a single document.
Redacting at the report layer alone still leaks through the agent's context and any transcript.

**Trade-off accepted**: the agent cannot inspect the raw value to judge whether a hit is a real
secret or a test fixture, so some false positives will survive to the report.

**DDR gate**: 3/3 (hard to reverse, surprising without context, genuine trade-off) — ADR-eligible;
user elected the lighter DDR tier. → see DDR-0001
(`docs/ddr/0001-redact-secrets-at-evidence-layer.md`)

---

## 2026-08-14 — Context-coverage score is an auditable checklist ratio

**Decision**: Each dimension declares the context sources it seeks as static data. Coverage =
unweighted `found / sought`. The score may never be rendered without the accompanying named list of
sources sought but not found.

**Why**: A bare percentage is exactly the unfounded precision this project exists to prevent — "62%"
invites trust it cannot justify. Unweighted keeps the engine free of importance judgments, which
would be opinions smuggled into a component defined as opinion-free.

---

## 2026-08-14 — Docker in v1 (user override)

**Decision**: Dockerfile + compose ship in the v1 milestone; target repo mounted as a volume, all
config via environment variables. The CLI adapter remains runnable with no container.

**Why**: User decision, overriding the Supervisor recommendation to defer to v1.1. Matches
`easy-ui-mcp` operational style from day one.

---

## 2026-08-14 — Dimension structure: pipeline function + descriptors (Option D)

**Decision**: One module-level `run_dimension(spec, repo, scope, budget)` owns the whole pipeline
(context → collect → redact → budget → coverage → pack). Each dimension supplies a `sources_sought`
data list plus a single `collect` callable. No base class, no registry, no decorators; `DIMENSIONS`
is an explicit dict. `collect` returns `Iterable[Excerpt]` and `budget()` consumes it lazily.

**Why**: The discriminator was NFR-010 enforcement, not elegance. Flat modules (Option C) make
redaction a convention an implementer can omit — the exact silent failure DDR-0001 forbids. A plugin
registry (Option B) enforces it but pays inheritance ceremony for extensibility nobody requested.
Pure declarative specs (Option A) cannot express blast-radius graph traversal or test-strategy
coverage parsing, and would grow an escape hatch and converge on D anyway. D puts every cross-cutting
rule in one unreachable-around place while leaving `collect` an ordinary function.

**Trade-off accepted**: one layer of indirection over flat modules; the redaction boundary needs its
own dedicated choke-point test.

**Also decided**: `collect` is lazily iterable from day one, because a monorepo large enough to need
budgeting is exactly the one where materialising all excerpts first exhausts memory.

**Migration note**: D→B is mechanical if third-party dimensions ever become a requirement.

→ see `BRAINSTORMING_LOG.md`

---

## 2026-08-14 — Shared extraction helper for document-shaped dimensions only

**Decision**: architecture, solution-fit, requirement-fidelity and code-quality share one
parameterised artifact-extraction helper driven by their `sources_sought` declarations. security,
test-strategy and blast-radius keep bespoke `collect` implementations.

**Why**: 50% Rule outcome. The four document-shaped dimensions genuinely are "locate artifacts,
extract excerpts" and compress well. The other three carry irreducible logic (entropy scanning,
coverage-report parsing, dependency-graph traversal); forcing them into a shared helper is Option A's
mistake. Real reduction is ~25–30%, not 50% — claiming 50% would mean pretending the analytical
dimensions are simpler than they are.

---

## 2026-08-14 — Local-only, stdio-first transport (user correction)

**Decision**: The harness connects to this MCP **locally, through a Docker container — never over
the internet**. stdio is the default and required transport, spoken across the container boundary
via `docker run -i`. HTTP/SSE is optional, opt-in, and must bind `127.0.0.1` only.

**Why**: The spec had inherited "HTTP/SSE" from `easy-ui-mcp`'s operational style without anyone
asking whether this project needs it. It does not. The engine is stateless — every call re-reads the
target repo from disk — so there is no warm cache or session that a long-running server would
protect, and a fresh process per call costs nothing. Against that, a network transport buys a port
to collide, a lifecycle to manage, and an unauthenticated local socket that reads arbitrary source
trees and returns file contents. `docker run -i` handles the container boundary fine, so Docker was
never a reason to need HTTP either.

**Consequences**: NFR-012 (local-only, no outbound requests, no externally reachable socket),
NFR-013 (non-root container, target repo mounted read-only except `reports/`), FR-021c (container
paths must not leak into reports). Authentication is out of scope *because* of locality — an
exclusion that must be revisited first if remote operation is ever added.

**Corrects**: the original `REQUIREMENT.md` line 33 reading, which the PRD had carried forward
unexamined.

---

## 2026-08-14 — Synthesis is aggregation in the engine, interpretation in the caller

**Decision**: The engine provides a combined-pack operation (run several dimensions in one call,
return an aggregate coverage summary) and renders multi-dimension reports with optional suggested
improvements per finding. Deciding what findings *mean together* remains the caller's work.

**Why**: `REQUIREMENT.md` §4 lists a "synthesis + suggestion layer" among the five internal layers,
and §1 asks for "improved suggestions" — but the PRD and the layer map had dropped it entirely.
Recovering it must not smuggle reasoning into an engine defined as reasoning-free, so the split is:
aggregation and presentation are mechanical and belong to the engine; interpretation is judgment and
belongs to the caller.

---

## 2026-08-14 — Evidence packs bounded by relevance-ordered byte budget

**Decision**: 120 KB default per dimension pack, overridable per call. Content ordered changed-files
→ spec-referenced → remainder, so truncation drops the least-relevant tail. Truncation is reported
as an explicit structured field and feeds the coverage miss-list.

**Why**: Byte-measured rather than token-measured keeps output deterministic and model-independent,
preserving the two-adapter parity guarantee; a tokenizer would make packs model-specific.

---

## 2026-08-15 — Redaction fingerprint is unsalted (DDR-0001 follow-up)

**Decision**: The secret fingerprint is an **unsalted** SHA-256, rendered as a 4-character masked
prefix of the raw value plus a 12-hex-character hash prefix (e.g. `AKIA…****:a3f9c2e18b04`).
Closes gap-audit open item #14, which had been carried as a HITL gate on T004.

**Why**: The choice is a trade between correlation and dictionary resistance. Unsalted, the same
secret fingerprints identically everywhere, so a report can state "this one credential appears in
three files" — which is what makes the finding actionable rather than three unrelated alarms.
Salted, that correlation is destroyed, and the salt itself becomes new surface needing a lifetime
and a storage location, which is precisely the kind of stored secret this tool exists to complain
about.

The dictionary-attack risk that salting defends against only matters if a report reaches somewhere
the repository does not. **The user confirmed (2026-08-15) that reports are not used outside the
evaluated repo.** A report therefore lands beside the credential it describes: anyone able to read
the fingerprint can already read the raw value with `grep`, so reversing a weak fingerprint
discloses nothing new.

**Trade-off accepted**: a low-entropy secret (`changeme`, `admin123`) is recoverable from its
fingerprint by anyone holding the report. Accepted because the report's audience is, by the user's
constraint, already inside the repo's trust boundary.

**Revisit if**: reports ever start travelling — committed to a shared branch, attached to a ticket,
pasted into a PR, or sent anywhere outside the evaluated repo. That change invalidates the reasoning
above, and salting should be reconsidered before it happens. NFR-011's first-write advisory is the
existing mitigation and stays.

**Settings fixed alongside**: SHA-256; 12-hex-char hash prefix (collision-safe within a report,
useless in isolation); 4-char mask retained so `AKIA…` remains recognisable as an AWS key without
disclosing meaningful material.

---

## 2026-08-15 — Truncation is rejection-triggered; omitted_count is a lower bound

**Decision**: `run_dimension()` pulls from `collect` until one excerpt does not fit, drops that
excerpt, and stops. `truncated` is set by that rejection — never by `used >= budget`.
`omitted_count` counts only items actually pulled and rejected, and the field documents itself as a
**lower bound**, not a total.

**Why**: T001's guide contained a contradiction the implementing agent caught before writing code.
Its Success Criterion 3 demanded `omitted_count == 7` for a 10-item stream under a 3-item cap, while
the same sentence demanded the generator never be advanced past what the cap needed. Knowing seven
remain requires draining the stream; not draining it means you cannot know. Both cannot hold.

Draining to count is the tempting fix and is the wrong one: for a file-reading `collect`, "just
counting" means opening every remaining file, which is exactly the monorepo cost that budgeting
exists to avoid. The lazy-consumption constraint would survive in letter and die in effect.

Rejection-triggering also removes a false positive that the alternative (`stop when used >= budget`)
carries: a stream ending exactly at the boundary would report `truncated=True` having omitted
nothing.

**Trade-off accepted**: the pipeline advances exactly one item past the admitted set, and callers
learn "at least one item was dropped" rather than how many. Bounded overshoot, honest field.

**Consistency note**: T005's guide had already specified the correct semantics independently
(its edge-case checklist required `omitted_count` be "honest about being a lower bound if the
remainder was not counted"). T001's criterion was the outlier; this decision aligns the two rather
than introducing a new rule. Both guides updated.

**Supervisor error worth naming**: this was a planning defect, not an implementation one — an
acceptance criterion that no correct implementation could satisfy. It survived because the two
halves of the contradiction sat in different sections of the guide (Success Criteria vs. Test Plan)
and were individually reasonable. Cross-check numeric criteria against the constraints they
interact with when writing future guides.

---

## 2026-08-15 — Integration strategy: local merges, one PR at the end

**Decision** (user, 2026-08-15): Stage 3 task branches merge **locally** into
`plan/stage2-task-breakdown`. Nothing is pushed per-task. The accumulated branch goes up once, as a
single PR into `develop`, at a point of the user's choosing.

**Why**: the user is the sole operator and reviewer. Per-task review already happens at Stage 4
(`code-review`, plus `security-review` on Medium/High risk) and at Stage 5 (`verify`) before each
local merge, so the PR is a record of what landed rather than the mechanism by which it is reviewed.
Pushing seventeen branches to get seventeen PRs nobody else reads would add ceremony without adding
scrutiny.

**Consequences accepted**:
- Nothing is reviewable off-machine until the single push. A machine loss before then loses all of
  it — the branch is the only copy.
- The final PR is large by construction. It is a changelog, not a review surface.
- Every Stage 3 branch stacks on an unpushed base, so a later guide revision means a rebase for
  each stacked branch still open.

**What this changes operationally**: the merge gate
(`pre_bash_block_unsafe_merge.py`) now fires on the **first local merge**, imminently, rather than
at some distant push. That made the trace-attribution defect load-bearing immediately — see
`learnings.md` for the resolved Stage 5 procedure that satisfies it honestly.

---

## 2026-08-15 — T001 shipped: the run_dimension() contract is now fixed

**Decision**: the pipeline contract landed and is no longer open for casual revision. Sixteen tasks
are written against it. Signatures, as merged:

- `Excerpt(path, start_line, end_line, text)` — 1-indexed, inclusive line numbers
- `SourceMiss(source, reason)` — a miss always carries *why*
- `DimensionDescriptor(name, purpose, sources_sought, collect)` — plain data, no base class
- `run_dimension(descriptor, repo_path, scope="project", budget_bytes=120_000)` — sole choke point
- `redact(text: str) -> str` — identity passthrough until T004 fills it
- `coverage_score is None` when `sources_sought` is empty (never `0.0`, which would read as failure)

**Two design points that emerged during the task and are now binding**:

1. **File reading lives in the context, not the dimension** (`ctx.read_source()`). A dimension that
   calls `open()` would own symlink escape, invalid UTF-8, permissions and empty-file semantics —
   and Option D's thesis is that a dimension cannot bypass a cross-cutting rule because it never
   owns one. `files_read` / `sources_found` / `sources_missing` are recorded as a side effect of
   actually reading, so a dimension cannot claim it read something it did not.

2. **`sources_found` is clamped to `sources_sought`.** Found by Stage 4 review: coverage_score
   reached **3.0** because every read was counted. `sources_found` and `sources_missing` now
   partition `sources_sought` exactly, which is what makes the miss list auditable under FR-016a.
   Undeclared reads stay visible in `files_read` — they happened, and hiding them would be its own
   dishonesty.

**Consequence the clamp exposed, now part of the contract**: a declared source the dimension never
*attempted* belongs to neither list, and under lazy consumption that is ordinary rather than
exceptional — when the budget stops the pull, later sources go unprobed. Those are reported as
`not examined`, distinct from `not found`. Reporting an unprobed source as absent would be exactly
the unfounded claim this project exists to catch.

**Operational caveat until T004**: `redact()` is a passthrough, so evidence packs can contain live
secrets. Harmless while output reaches only the terminal of whoever ran the CLI on their own repo.
It becomes material at T013, when reports start being written into a target repository. Recorded on
the Kanban.

**Tooling now pinned**: `ruff` in the `[dev]` extra with a minimal `[tool.ruff]` section, so "Lint
passes" on every task checklist is verifiable rather than nominal. `PLR` is deliberately excluded —
its magic-value rule fires on nearly every test assertion; `PLE`/`PLW` are in.

### 2026-08-16 — T004 shipped: redaction residue accepted rather than closed

The detector stack is layered — named patterns (AWS key IDs and secret keys, PEM private-key blocks,
JWTs, `key=value` credential assignments) over a catch-all entropy rule over a per-segment
key-material rule. The per-segment rule is what makes paths and URIs safe: it scans the runs
*between* `/ : @ .`, so a token in a URL path and the password inside `postgres://user:pw@host` are
each caught on their own, while `db.internal/prod` stays readable.

**Two confirmed misses are accepted, not fixed** (verified by execution at Stage 4, recorded in
`tasks/TASK_REVIEW_T004.md`):

1. A credential assignment whose value is followed by trailing prose on the same line with no
   comment marker — `password=hunter2 and then some prose`.
2. Single-character-class tokens of 12–31 chars — `Bearer abcdefghijklmnopqrst`. Below the
   mixed-class bar of the segment rule and below the 32-char bar of the entropy rule.

**Why accepted**: both anchors exist to stop false positives when the tool evaluates *its own
repository*, which is its own test fixture. The module is deliberately tuned toward over-redaction
elsewhere ("a false positive costs a reader one confusing fingerprint, a false negative costs a
credential") — these two are the places where that trade was taken the other way, on purpose, and
the cost of removing them is that the tool fingerprints its own prose and paths into unreadability.

**Revisit condition**: same as the salting decision — if reports ever leave the evaluated repo, both
the residue and the unsalted fingerprint need re-examination together.

### 2026-08-16 — `develop` is the Stage 3 integration branch

Superseding the earlier "merge into `plan/stage2-task-breakdown`, one PR at the end" plan: that
branch was pushed and merged via PR #2 (`e185baa`). Task branches now merge locally into `develop`,
still one-at-a-time and still with the full Stage 4 + Stage 5 gate per task. T004 → T006 → T002
merged in that order on 2026-08-16 (166 tests green, ruff clean).

The serialization is not ceremony: the merge gate blocks while *any* task sits In Progress, and the
T002/T004 collision (see `learnings.md`) is a live demonstration that concurrent branches touching
the same core files need resolving one at a time, with a semantic re-probe after each.

### 2026-08-16 — DDR-0002: never read secret-bearing files; HITL gate for T008

User's proposal during T004's review, and a better control than what we had:
don't ingest the secret at all, rather than ingest-and-redact. Full record in
`docs/ddr/0002-never-read-secret-bearing-files.md`.

Hard exclusion list (`.env*`, `*.pem`, `*.key`, `id_rsa`, `.netrc`, `.pgpass`,
`credentials`, `.npmrc`, `.pypirc`, `secrets.*`, …) enforced in
`RepoContext.read_source()` — the choke point every dimension already uses, same
reasoning as Critical Constraint 4. Existence is still reported
(`excluded: secret-bearing`, distinct from `not found` / `not examined`); only
the bytes are withheld. T008 gets a per-file operator approval gate defaulting to
refuse; no other planned dimension has a reason to ask.

**Timing is the point**: the engine reads only doc extensions today, so this
costs nothing now and would mean retrofitting three dimensions if decided after
T007/T008/T013 are written. Landed as `PROJECT_SPEC.md` Constraint 4a plus AC
rows on all three guides before any of them is picked up.

**This does not replace redaction.** Demonstrated during the same session: a
live-key-shaped Stripe token sat in a `README.md` setup section — a file type the
engine reads and always will. Exclusion shrinks the intake; redaction covers the
residue. Describing either as sufficient alone would be false.

**Watch for**: the rubber-stamped HITL gate. Operators who approve without
reading make the gate worse than useless, because it manufactures a record of
consent that was never really given.

### 2026-08-16 — T003 merged; the "Files to Change" table is a prediction, not a contract

`resolve_scope(kind, repo_path, context, **args)` → `Scope(kind, files, changed_files, diff,
task_ref, notes)`. Four kinds: `project` (filesystem walk, works without git), `worktree`
(uncommitted), `changes` (range/commit/branch via local git, parent-normalised, empty-tree base for
a root commit), `task` (guide + parsed acceptance criteria). `Scope`/`TaskRef` live in `scope.py`,
not `models.py`, while nothing else imports them.

**Waiver recorded**: the agent skipped the guide's predicted edits to `models.py`, `pipeline.py` and
`cli.py`, flagged it, and the Supervisor waived it. The guide's Files to Change table is a Stage 2
*prediction*; the Acceptance Criteria are the contract, and all nine pass without the wiring.
Wiring `Scope` into `run_dimension()` here would be the same unrequested cross-cutting change that
produced the T002/T004 collision. T005 is the declared consumer; T015 owns the CLI surface.

**Accepted cost**: `resolve_scope` is unreachable as merged — dead code until T005 lands. Revisit
the waiver if T005 slips.

**Precedent worth reusing**: an agent flagging a deviation for sign-off rather than silently
following a stale prediction is the behaviour we want. Judge deviations against the ACs, not the
file table.

### 2026-08-17 — T005 merged; relevance tiering costs a pass per tier, and `resolve_scope` is finally reachable

`budget(collect, scope, limit_bytes)` — note `collect` is a **zero-arg callable**, not an iterable.
It is invoked once per *non-empty* tier (never more than three times), each pass admitting only that
tier's excerpts and stopping every remaining pass the instant one excerpt does not fit. Tier
membership is knowable from `scope` alone before any excerpt exists, which is what makes tiering
possible without sorting the stream. A scope carrying nothing keeps the caller to the single tier-3
pass the pipeline always ran.

**The design tension, resolved the expensive way on purpose**: perfect relevance ordering wants the
whole candidate set in hand; laziness forbids it. Single-pass admission cannot resolve this — see the
learnings entry on T005's P1. The accepted cost is that a pass which never hits a misfit drains its
stream fully, so a file-reading `collect` can be traversed up to three times. Chosen by the user over
waiving AC #2 or a bounded lookahead buffer.

**`resolve_scope` is now wired into `run_dimension`** (T003's waived debt, closed as predicted).
`project`/`worktree` resolve for real; `changes`/`task` still fall back to `scope=None` for tiering
because `run_dimension`'s signature has no way to accept a `ref`/`task_id` — a caller wanting those
resolves its own `Scope` and calls `budget()` directly.

**Tier 2 narrowed to `scope.task_ref.guide_path` only** — kit-artifact names (`PROJECT_SPEC.md` etc.)
were dropped from it. A fixed, non-empty tier-2 set makes that tier reachable on *every* call, forcing
a `collect()` pass and usually a full drain even for callers with no scope; it broke 5 T001 tests
pinning the single-pass contract. **Cost to revisit**: under `project`/`worktree` scope the spec now
ranks tier 3 alongside ordinary source, so a tight budget can drop it ahead of unrelated code. **T007
(four doc-shaped dimensions) is the task that should re-open this rather than inherit it silently.**

**No per-excerpt byte-overhead constant**, against the guide's Approach text: adding one would move
every existing T001 byte threshold. AC #8's "documented tolerance" is satisfied by a zero tolerance.

---

## 2026-08-18 — T007 doc dimensions: direct kit declarations, docs-first standalone fallback

**Decision**: the four document-shaped dimensions share one narrow extractor. Kit-aware mode reads
each descriptor's declared sources, including the generic `tasks/TASK_GUIDE_*.md` source for
acceptance criteria. Standalone mode reads `RepoContext.doc_sources` first and consults a bounded,
containment-safe code inventory only when the documents yield no relevant evidence.

**Tier-2 outcome**: T005's narrowing was re-opened but `budget.py` remains unchanged. Relevance
tiering and source selection are separate concerns; T007 makes the important kit sources candidates
inside collection rather than forcing a permanent second budget pass on every dimension call.
**Security boundary**: secret-file exclusion checks both the requested path and the resolved target,
so a safe-name symlink cannot alias `.env` bytes into an evidence pack.


### 2026-08-20 — T008 merged; the HITL secret gate, and `resolve_scope` failure is not "whole repo"

`security` is bespoke as Constraint 8 requires — it does not import `_doc_extract`. Its evidence is
selected in two passes inside `collect()`: declared sources from `SOURCES_SOUGHT` are probed first and
explicitly, then the resolved scope's remaining files are swept in category-ranked order (credential
material → dependency manifest → permission/container/CI config → auth/crypto code → generic
scannable) up to `MAX_SECURITY_SOURCES` (200).

**Why declared sources are probed separately.** `pipeline._missing_sources` can only report a reason
that some `read_source` call actually recorded. A dimension that never probes its own declared
checklist gets the `not examined` default for every entry, which is a claim the engine did not check.
T008 shipped that way and reported `.env`, `Dockerfile`, `package.json` and `src/auth.py` — none of
which exist in this repo — as `not examined: the byte budget was reached`. The shared default is
correct for the doc dimensions, which do probe; the fix belongs in the dimension, not in `pipeline.py`.
**Any future dimension that selects by walking a scope rather than by reading its declared list must
probe the list explicitly, or its miss list is fiction.**

**The HITL gate (DDR-0002) lives only in `security`.** `context.read_source` refuses secret-bearing
paths unconditionally for every dimension. `context.request_secret_source` is the only door, it
defaults to refuse, it requests approval per file, it caches the decision per path so lazy budget
passes cannot re-prompt, and a raising approval callback is caught and treated as refusal. Approved
contents still pass through `budget.py:204`'s redaction seam, so an approved `.env` is fingerprinted
in the pack rather than emitted raw. **Accepted for v1**: `secret_approval` is never threaded through
`run_dimension` or either adapter, so the gate is structurally always-refuse in production — the
operator sees `approval_requests` on the pack but cannot consent. Hardening candidate, with closing
T004's two documented detector floors, which the gate now makes reachable on purpose.

**A failed scope resolution is not the same as `project` scope.** `run_dimension` collapses
`ScopeError` to `resolved_scope = None`, and T008 initially read that as "whole repository", so
`--scope task` with no `--task-id` read repository-root files while labelling the pack `scope: task`
with empty warnings — contradicting `pipeline.py:60`'s own stated "never widen on failure" invariant.
A dimension must distinguish *unresolved* from *project* using `context.scope` (the requested name,
always present) rather than `resolved_scope` alone, and declare the failure through `context.warnings`,
which `run_dimension` copies onto the pack after the budget drain.

**Known divergence, deliberately not fixed in T008**: `scope.py` fails two different ways — `task`
without a selector *raises*, `changes` without one returns an empty scope. Each dimension currently
absorbs that at its own boundary. Candidate follow-up on `scope.py`/`pipeline.py` to make the
invariant structural rather than conventional.


---

## T009 — `test-strategy` dimension (merged 2026-08-24)

**A declared source is a checklist label, not a path.** `SOURCES_SOUGHT` lists bare filenames
(`conftest.py`, `pytest.ini`, `package.json`); `RepoContext.read_source` resolves a bare name at the
repo root only. T009 shipped probing those names literally, so any project keeping its config in a
subdirectory got a miss reason its own `files_read` and `excerpts` contradicted.

Fixed by `_resolve_declared_source(source, scope_files)`: for a bare name absent at the root, look up
a basename match inside the **already-computed** `scope_files` — no new walk, no new resolver, so the
existing containment check is inherited rather than re-implemented. `core/pipeline.py` matches
`sources_sought` against `sources_found` by literal string equality, so when the resolved path differs
from the declared name the declared name is *additionally* appended to `sources_found`; the concrete
path is already recorded there by `read_source` for honest citation.

`.github/workflows/ci.yml` is the one entry deliberately left root-anchored — GitHub Actions only ever
reads that exact path, so a match elsewhere would be meaningless.

**Consequence to watch**: the basename fallback inherits whatever `core/scope.py:_EXCLUDED_DIRS`
misses. `node_modules` is in that set, `vendor/` is not — so in a repo with no config of its own, a
vendored dependency's `package.json` is credited as the project's declared source. Filed against
`scope.py` (one-line fix, benefits every dimension); not charged to T009.

## T010 — `blast-radius` dimension (merged 2026-08-25)

*Code-dependency* reach, deliberately not the kit's `blast-radius` **skill** (data-breach impact).
Three cheap sources, none of which parses, imports or executes target code: a **textual** reference
search (one alternation over every scope file's path, dotted module path and stem, one lazy pass over
the repository), **git co-change** history from a single `git log --name-only` over the last 200
commits, and **declared entry points** cited from packaging manifests.

Two design commitments worth keeping straight:

* **Textual, and it says so.** `METHOD_WARNING` ships on every pack: over-reporting on same-named
  symbols, under-reporting on aliases and dynamic references. A real resolver would be per-ecosystem,
  enormous, and would still miss the dynamic cases. That admission *is* the product (AC #5) — which is
  why a silently truncated sweep is the one unacceptable failure, and became the Stage 4 P1.
* **`project` scope reports repository hotspots, not references.** Expanding every file against every
  other is quadratic, so references and co-change are declared out of scope there with a stated reason.
  Consequence recorded as residue (d): under `project` scope the pack has **zero citable excerpts**
  unless the repo declares an entry point, and in a non-git directory it is entirely empty — every
  source honestly refused, but no evidence path exists for that combination.

`MAX_SCAN_FILES = 400` is what bounds the tier-1 drain, not the byte budget: `core/budget.py` runs a
tier-1 pass first, and a referencing file is almost never itself a changed file, so that pass usually
admits nothing and drains its stream by construction.

**All seven of FR-010's dimensions are now wired.** Wave 2 is complete; Wave 3 (T012 synthesis, T013
report) is next.


---

## DDR-0003 — T012/T013 seam contract, locked by the Supervisor (2026-08-25)

**Context.** The user elected to run T012 (`synthesis.py`) and T013 (`report.py`) **in parallel**,
against the Supervisor's recommendation to sequence them. T013's declared input is exactly T012's
declared output (`CombinedPack` / `CoverageSummary`). Two agents in two worktrees, each inventing
half of a seam, is the rework this project has already paid for once (T002/T004's redaction seam,
caught only at Stage 5 integration because each branch's tests passed alone).

**Decision.** The seam is **not** an agent design choice. The Supervisor fixes it here, at Stage 2
authority, and hands the identical text to both spawns. T012 **implements** these types in
`core/models.py`; T013 **imports** them and does not define, widen, or shadow them. If either agent
believes the contract is wrong, it stops and reports to the Supervisor **before** building — it does
not adapt around it.

```python
@dataclass(frozen=True)
class DimensionSlot:
    dimension: str
    pack: EvidencePack | None      # None iff error is set
    error: str | None              # structured failure; T012 AC #6

@dataclass(frozen=True)
class CoverageSummary:
    per_dimension: tuple[tuple[str, float | None], ...]        # deterministic order
    combined: float | None                                     # None, never 0.0, when nothing sought
    method: str                                                # states how `combined` was derived; T012 AC #2
    misses: tuple[tuple[str, tuple[SourceMiss, ...]], ...]     # union, named per dimension; T012 AC #3

@dataclass(frozen=True)
class CombinedPack:
    slots: tuple[DimensionSlot, ...]   # deterministic order regardless of request order; T012 AC #10
    coverage: CoverageSummary
    budget_model: str                  # literal "per-dimension"; see below
```

**Rationale for the shape.**
- `coverage_score` on `EvidencePack` is already `float | None` with `None` meaning "nothing sought",
  explicitly *not* `0.0`. `CoverageSummary.combined` inherits that rule rather than inventing a
  second convention for the same idea.
- `misses` is carried **inside** `CoverageSummary`, not beside it, so FR-016a ("coverage is never
  presented without its miss list") is structural rather than conventional. A renderer cannot reach
  a score without having the miss list in hand. This directly answers T013 AC #6, which otherwise
  depends on the renderer remembering.
- `error` is a plain `str` slot rather than an exception: T012 AC #6 requires one dimension's failure
  not to abort the call, and T013 must be able to render that failure as a visible gap rather than
  as a missing section a reader cannot distinguish from "this dimension had nothing to say".

**Budget model: per-dimension (user decision, 2026-08-25).** Each dimension in a combined call gets
the full byte budget independently, and truncation is reported per dimension (T012 AC #5). This is
what makes T012 AC #9 exact — a one-dimension `combined_pack` is genuinely equivalent to calling
`run_dimension` directly, with no special case. The accepted cost is that NFR-009's boundedness on a
seven-dimension call now rests on the caller asking for fewer dimensions rather than on an engine
ceiling; `budget_model` is carried on the pack so the report states which regime produced it and a
future total-budget mode is a value change, not a schema change.

**Standing instruction to both agents.** T013 must not wait for T012's code to exist. Write against
this contract and construct fixtures directly. Where T013's tests need a `CombinedPack`, they build
one literally — that is a feature, not a workaround: it keeps T013's suite from depending on T012's
dimension execution, which is the same isolation that let T007's tests survive T005's rework.
