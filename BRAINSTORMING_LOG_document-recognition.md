# BRAINSTORMING_LOG_document-recognition.md
**Generated**: 2026-10-12
**Task / Context**: Post-T048 real-repo retest (bryony/scraping-devops). The document rules mean a match against our kit's names, but they score the repo as if the document were absent.
**Skill**: `Skill({ skill: "brainstorming" })`
**Scope tier**: Deep. It decides what the engine may treat as absence, and that affects 2 dimensions and the overall.

---

## The Problem Space

**Trigger.** In the scraping-devops scan (2026-10-12, `develop` c527e35), architecture scored **0**.
`architecture_description_missing` failed. The README does describe the structure, under the headings
"Folder structures" and "Concepts", but the rule accepts only a heading containing the word
*architecture* or a file on our pattern list.

**User's framing (2026-10-12):** *"How can we know what kind of document a project covers? Some
cover A, some B or C. We only cover A. The risk comes from B and C."*

**What the code does (verified):**
- `core/metrics.py:918` `_document_rule`: if no file matches the role's patterns and the search ran
  to completion, it returns **1 = "the document is missing"**. "Not matched by our list" is reported
  as "does not exist".
- `core/roles.py:103` `GENERIC_PATTERNS["architecture-doc"]` includes **`PROJECT_SPEC.md`**.
  `decision-record` includes **`BRAINSTORMING_LOG*.md`**. Both are names from this harness kit, so
  the kit's own repos pass partly because they are the kit.
- Rules this affects (`core/judge.py`):
  - `architecture_description_missing` 10 and `decision_records_missing` 10 (architecture, DDR-0011
    20/80 split)
  - `requirements_doc_missing` 10 (requirement-fidelity)
- Escape hatches already exist, but neither reaches the plain CLI run:
  - `.easy-verifier.toml` declarations are add-only (DDR-0006).
  - The MCP detect gate (`core/gate.py:81` `_DOC_ROLES`) lets the agent assign any unmatched `.md`
    to a document role. A CLI run with no toml and no `--agent-input` gets only our closed list.
- Spec already distinguishes these: a **documentation rule** is "present (cited file) / missing;
  never a number" (PROJECT_SPEC glossary; offboarding, continuity and retention follow it). The 3
  rules above are the exception, because they are scored.

**Core point.** A closed list of names can prove a document is **present**. It cannot prove one is
**absent**. Reporting a non-match as absence breaks Constraint 2 (no invention, absence must be
real) and has the shape of Constraint 1b (a state encoded as a value). Broadening the list does not
fix this; it only moves the boundary of B and C.

**Non-negotiables:** NFR-001 (no LLM in the engine, so no "read the README and decide"), 1a (a
rating can be recomputed by hand), 1b (abstention is a state, never a value).

---

## Round 2: user redirect (2026-10-12)

> *"We should find a way, not the way we can not do, we bypass it."*

Options A and C stop judging instead of finding out, so they are bypasses. The new goal is to
**recognize what a project actually documents, whatever its name or shape**, deterministically (no
LLM, NFR-001) and with a citation.

### Probe: recognize documents by content shape, anchored to the real repo tree

The scratchpad script (`doc_probe.py`, `probe2.py`) ignores file names. It looks for list items,
table rows or tree lines whose leading token is a **directory that really exists in the repo**,
followed by an explanation (two or more words). Results on real repos (2026-10-12):

| Repo | Today (name list) | Content shape | Ground truth (read by hand) |
|---|---|---|---|
| scraping-devops | **missing** (fail) | README.md: 5 described (`- bin: helper scripts`, `- elk: …`, `- vagrant: …`) | Has one, under "Folder structures". **The name list gives a false negative.** |
| ai-training | (not re-run) | travel_chatbot/README.md: 4 described (`├── eval/  # Evaluation set…`) | Has a structure tree |
| bryony | **pass**, through `backend/docs/event_design.md` (matches `*design*`) | at most 1 described entry in any document | README is product description plus deploy steps. `event_design.md` documents event payloads. **The name list gives a false positive.** |
| coffee-shop-api | — | 1 described, a false hit (`- test → vitest run` is an npm script) | below any threshold of 3 or more |
| kitchd, easy-verifier | pass through `PROJECT_SPEC.md` (kit name) | missed: module tables sit in code blocks and use file paths | Has one. The probe's parser needs code-block trees and file-path entries. |

**Finding:** name matching fails in **both** directions on real repos. Content shape anchored to the
repo's actual directories recognizes descriptions under any name, and an entry has to point at
something that exists, which is a fact the engine can check rather than a house convention.

### Option D — Evidence-based recognition (recommended, replaces A)

A document role is filled by **any** of these, each one cited. The first match wins, and the
evidence kind is reported:
1. **Declared**: `.easy-verifier.toml` `[roles]` or an MCP detect-gate pick (exists today).
2. **Content shape** (new), per role:
   - *architecture-doc*: 3 or more described entries naming real repo directories or files (list,
     table, tree, or a code-block tree).
   - *decision-record*: decision structure (Context / Decision / Consequences or Status fields, or
     dated "decided / chose X over Y because").
   - *requirements-doc*: requirement items, reusing the existing `requirement_item_patterns`
     (ids, Gherkin, "As a … I want", shall/must).
3. **Name / heading conventions**: today's list with the kit names removed. Weakest evidence; it
   counts only when shape (2) or declaration (1) agrees, or always, depending on Q3 below.

"Missing" is then a measured statement: *"no document in the repository describes any of its N real
components; searched M documents"*. That is a fact about the repo's content, not about our file
names. The 20/80 weights from DDR-0011 stay.

**Why D might fail:** (a) prose-only descriptions such as "The backend talks to Mongo via the
platform layer…" have no list shape. Mitigation: also count paragraphs that name 3 or more real
components; measure the false-positive rate on all repos first. (b) Thresholds (3 or more) are a
declared constant, so they need a cited rationale or user sign-off. (c) Generated or vendored docs
(Harbor's own docs) can fill the role for the host project, so the vendored-code exclusion becomes a
prerequisite. (d) Cost: reading every `.md` on large repos (kitchd has 90 docs, easy-verifier 180)
must stay within the read cap and batches.

---

## Round 3: user redirect (2026-10-12)

> *"With the architecture, we don't check the document only. It relates to the code structure,
> the life cycle of a request, or anything from the code overview, code architecture, ..."*

**The code rules have the same closed-list problem.** `layer_direction_violations` (40) assigns a
file to a layer by **folder name**: `registry/curated/conventions.toml:19+` lists `controllers/`,
`routes/`, `services/`, `repositories/`, `dao/` and similar. A project using its own layout (bryony:
`backend/server/*/router.js`, `backend/platform/core/models/`) is mostly unclassified, so the rule
measures our naming conventions rather than the code's architecture.

### Option E — Code-derived architecture: classify by behaviour, trace the request lifecycle

Assign roles from **what the code does**. The facts come from framework and ORM APIs that the
registry can cite per framework, not from folder names:
- **Entry**: registers a route. The call shape is `<any receiver>.get|post|…('/path', handler)`,
  `@Get()/@Controller()`, `@app.get(...)`, Django `path(...)`.
- **Data**: calls a DB or ORM API, such as Mongoose models (`Model.find`, `mongoose.model`),
  `prisma.x.y()`, TypeORM `getRepository` / `@InjectRepository`, SQLAlchemy `session.execute`, or
  raw `pool.query`.
- **Intermediate**: everything on the import path between them.

Metrics this enables, all citable by file:line:
1. **Request path**: for each route, the import path from handler to data access. Report the share
   of routes whose handler queries the DB directly, and the path depth.
2. **Layering by behaviour**: replaces the folder-name layer classification. A data-access file
   importing an entry file is a violation, whatever the folders are called.
3. **Structure**: import cycles (existing); possibly fan-in and fan-out hotspots, and god modules.
4. **Documents**: Option D, content shape, as a small part of the weight.

**Probe (`arch_probe.py`, crude regexes) on real repos, 2026-10-12:**

| Repo | Result | What it teaches |
|---|---|---|
| kitchd | 17 route files, 16 reach data | Most were flagged as "querying the DB directly" because the data regex matched `Array.find(`. **The data pattern must be ORM-specific, keyed to an imported model or client.** |
| coffee-shop-api | 4 route files, 3 "direct" | Same false positive. Nest controllers inject services. |
| bryony | only 1 route file found | Real routes use `webapp.get('/api/master/clients', …)` in `backend/server/*/routers/*.js`. **Entry detection must key on the call shape, not the receiver name.** |
| ai-training | 0 entry, 0 data | Its framework (FastAPI / LangGraph) is not covered. Coverage per framework must be measured and disclosed. |

**Verdict:** feasible and name-independent, but precision lives in per-framework patterns.
Those belong in the cited registry (DDR-0007), scoped to the stacks already in use (Express, Nest,
FastAPI, Django). An unknown framework is disclosed as "framework not recognized", and stays
distinct from "no routes".

**Why E might fail:** (a) dynamic route registration (loops over a route table, or decorators built
at runtime); (b) dependency injection hides the call path (Nest gives a constructor-injected service
with no relative import of the data file, so DI tokens must be resolved); (c) cost: a full import
graph and a scan of every file for both patterns on large repos; (d) false data positives from
generic method names. Mitigation: require the receiver to be an imported model or client symbol.

---

## Grilling decisions (2026-10-12)

User rule for this session: ask only when genuinely unsure **and** the answer materially moves
scores. Everything else is decided here.

| # | Decision | By | Score impact |
|---|---|---|---|
| G1 | **Layer** is assigned by observed behaviour (api = route registration through a recognised framework API; data = DB/ORM API call; service = on the import path between them). Path conventions are a declared hint only, and behaviour wins on disagreement. The term stays *layer*, never "role" (that is *source role*). PROJECT_SPEC glossary updated. | user (agreed) | high |
| G2 | Behaviour patterns live in the cited registry (DDR-0007), per framework. First set: Express, NestJS, FastAPI, Django, matching the stacks of the real repos. | Supervisor | low (scope only) |
| G3 | Entry detection keys on **call shape** (`<any>.get('/path', handler)`, decorators), never on receiver names. Data detection requires the receiver to be an **imported model or client symbol**, never bare method names like `.find(` (probe false positive). | Supervisor | precision |
| G4 | Framework not recognised → the behaviour rules fall back to the declared path hints. With no hints either, they abstain with `framework_not_recognized`, which stays distinct from "no routes". Disclosed in the payload. | Supervisor | low |
| G5 | Documents (Option D): a file-name match alone does **not** fill a document role. Content shape or a declaration is required. Conventional names only raise the scan priority. Kit names (`PROJECT_SPEC.md`, `BRAINSTORMING_LOG*.md`) leave `GENERIC_PATTERNS`, and kit repos pass on content or declare in `.easy-verifier.toml`. | Supervisor (round-2 Q2/Q3 closed) | bryony −10 on architecture docs (false pass removed) |
| G6 | Content-shape threshold: 3 or more described entries that name real repo paths (list, table, tree, or code-block tree). A declared constant, documented in SCORING_RULES. | Supervisor | low |
| G7 | Vendored or third-party code exclusion (Harbor in scraping-devops) is a **prerequisite** task, so third-party code never feeds layers, cycles or document recognition. | Supervisor | high on scraping-devops, but correctness, not policy |

---

## Questions for the User

1. ~~Which path, A / B / C?~~ Superseded by round 2. A and C are bypasses; D is recommended.
2. Remove the kit-specific names (`PROJECT_SPEC.md`, `BRAINSTORMING_LOG*.md`) from
   `GENERIC_PATTERNS`? Under D, kit repos would pass on content.
3. **Under D, does a name or heading match alone still fill the role?** If yes, bryony keeps passing
   through `event_design.md`. If no, a name match must be confirmed by content shape or a
   declaration.

---

## Alternative Paths

| Option | Name | Summary | Invasiveness | Code Volume | Regression Risk | Recommended? |
|--------|------|---------|-------------|------------|----------------|--------------|
| A | Not matched ≠ missing | A match passes, with a citation. No match means the rule abstains, says which patterns it searched, and explains how to declare the document. Weight drops out. | Low | ~20 src + tests/doc rows | Low–Med (snapshots, overall can move up) | ✅ Yes |
| B | Declare-or-abstain, neutral list | A, plus remove kit names from the patterns and keep only conventions used widely across the ecosystem. The project declares its own documents in toml or through the MCP pick. | Medium | ~40 src + toml for our repos | Medium (this repo's score changes; needs its own toml) | |
| C | Demote to documentation rules | The 3 rules stop scoring and show present/missing only. Their 30 weight moves to code rules. | Medium | ~15 src + weight table | Medium (re-sign DDR-0011, all numbers shift) | |

Rejected without a full option: **broaden the patterns** (README headings such as "structure",
"design" or "concepts", any `docs/*.md`). It is still a closed list, so B and C stay unknown, and
every added keyword brings new false positives.

### Option A — Not matched ≠ missing
**Approach**: In `_document_rule`, the branch that returns `1` when a search completed with no match
returns a `MetricAbstention` instead. Reason: *"no file matched the recognized patterns for
'architecture-doc' (…list…); this does not establish absence. Declare it in .easy-verifier.toml
`[roles]` or pick it at the MCP detect gate."* A match still returns 0 (pass) with its citation.
**Pros**: Smallest change. Applies Constraints 1b and 2 directly. The existing measured-weight floor
(DDR-0010) and the abstention disclosure already handle the dropped weight. No new mechanism.
**Cons**: A repo that really has no architecture document is never penalized, so these rules can
only pass or stay silent. Kit names stay on the list and only grant credit.
**Why it might fail**: (1) When the 20 document points abstain, architecture is rated on code rules
alone. scraping-devops would go 0 → 0, since the code rules fail on the vendored Harbor (a separate
issue). A repo with clean code and no documents goes up. That is the known "abstention can raise the
overall" residue (T022 (a)), disclosed but not elevated. (2) requirement-fidelity is already near its
floor on some repos (scraping-devops measured 40%), so more of them will abstain completely.

### Option B — Declare-or-abstain with a neutral list
**Approach**: A, plus remove `PROJECT_SPEC.md` and `BRAINSTORMING_LOG*.md` from `GENERIC_PATTERNS`
and keep only cross-ecosystem conventions (`ARCHITECTURE.md`, `docs/architecture*`, `docs/adr/**`,
`doc/adr`, `docs/decisions/**`). Our kit repos declare their documents in `.easy-verifier.toml` like
any other project.
**Pros**: The engine stops favouring our house style. The same rule applies to every repo.
**Cons**: This repo and other kit repos need a toml, or their scores drop. Every kit-installed repo
has to remember to add it.
**Why it might fail**: "Cross-ecosystem convention" is itself a judgment about which names are
neutral enough. It narrows our bias but does not remove it.

### Option C — Demote to documentation rules
**Approach**: Move the 3 rules to `DocumentationRule` (present/missing, cited, never a number) and
redistribute the 30 weight among code rules. This needs a DDR-0011 amendment signed by the user.
**Pros**: Most consistent with "we are not the judge". Documents are reported but never scored.
**Cons**: Documents have no influence on the number at all, which reverses DDR-0011's 20/80 split.
Every rating shifts, so the real-repo baselines must be re-run and the weights re-signed.
**Why it might fail**: It still shows "missing" in the documentation list, so the same false
statement appears (in text rather than in a number) unless C also takes A's wording.

---

## 50% Rule Check

Option A is already the 50% version: one return statement in `_document_rule` changes from `1` to an
abstention. The reason text, test updates and the two `SCORING_RULES.md` rows are the rest. The
abstention machinery, disclosure, warnings and improvement-plan "abstained" groups all exist already.

---

## Recommended Path

**Option E — Code-derived architecture** (round 3), with Option D as its documents component.
Build order: (1) behaviour-based entry and data detection for Express, Nest, FastAPI and Django, in
the registry; (2) a request-path metric plus the layer rule by behaviour, replacing folder-name
classification; (3) Option D document recognition. Each step is verified on bryony, kitchd,
ai-training and coffee-shop-api before the next.

**(Round 2) Option D — Evidence-based recognition** (see above). The original round-1 text follows
for the record.

**(Round 1) Option A — Not matched ≠ missing.** It answers the user's point directly. The engine can say "I
found A here", and it can say "I did not find A". It must not say "the project has no A" on the
strength of a closed list. Option B's removal of kit names is worth taking too (question 2), since it
costs one edit to a pattern table plus a toml for this repo.

---

## Surgical Scope

Files that **should** be touched:
- `src/easy_verifier/core/metrics.py`: `_document_rule` turns "not matched" into an abstention, with
  the reason text.
- `docs/SCORING_RULES.md`: rows for the 3 rules (pass / abstain, never fail).
- Tests for `_document_rule`, plus the T068 snapshot when an abstention changes it.
- (If Q2 = yes) `src/easy_verifier/core/roles.py:103` kit names, plus `.easy-verifier.toml` for this
  repo.

Files that **must not** be touched:
- `src/easy_verifier/core/gate.py`: the MCP pick already works.
- `src/easy_verifier/core/judge.py` weights. Option A keeps DDR-0011's 20/80; only C changes weights.
- `_role_presence` for tool-config rules (lint, format, lockfile, CI). This is a separate question
  and out of scope unless the user widens it.

---

## Edge Case Checklist for TASK_GUIDE

- [ ] A README heading naming "Architecture" still passes, with a citation.
- [ ] A toml-declared or MCP-picked document passes. A declared path that does not exist stays a
      validation error and does not count as a pass.
- [ ] A role search cut off by batches or the cap abstains, as it does today. It is not "missing".
- [ ] The abstention reason lists the patterns searched and how to declare. No repo text is echoed
      (redaction path unchanged).
- [ ] An overall that rises because the document weight abstained is disclosed. Check the
      `disclosure` string on scraping-devops and bryony.
- [ ] requirement-fidelity hitting `insufficient_measured_weight` because of this change is reported,
      not hidden.
- [ ] CLI/MCP parity (DDR-0005) holds for the new abstention.
- [ ] Real-repo before/after on bryony, scraping-devops, kitchd and ai-training is pasted into
      Evidence (feedback: done means real-repo verified).

---

## Next Actions

1. User picks a path and answers Q2.
2. Stage 2: TASK_GUIDE (C2 / Risk Med / P1; it touches rating semantics). Record a DDR that amends
   DDR-0011's "a missing document fails (1)" clause.
3. Separately (not this task): exclude vendored or third-party code (the Harbor copy in
   scraping-devops), which is what really drives the architecture 0 there.

---

## User Selection

> **Approved direction**: Option E (code-derived architecture) + D (documents by content), with grilling decisions G1–G7 and Q2 (request path reported, not scored; only in-repo code scored). Approved by user on 2026-10-12. → DDR-0012
