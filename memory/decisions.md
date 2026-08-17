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
