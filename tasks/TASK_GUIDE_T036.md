# TASK_GUIDE — T036: Local registry layer at ~/.easy-verifier-sot/, registry_entries agent input, replay parity, Docker mount
**Date**: 2026-09-28
**Complexity Level**: C2
**Risk Level**: High
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Note the **Complexity Level** above and apply the matching process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md`
7. Read `docs/ddr/0007-cited-reference-registry-and-reference-gate.md` and `BRAINSTORMING_LOG_reference-registry.md` (approved rule table, edge cases)
8. Read `docs/ddr/0005-adapter-parity-is-byte-equality-after-declared-normalization.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-09-28): "create the folder in the local verifier" → "easy-verifier-sot for the right purpose"; "just scored by your research first, and we can use the flag, tag … to show that score depend on any resource"; "we will refer to the link to evaluate, look like the clear source".

**Restated intent**:
> Registry entries supplied by the agent are validated, saved to `~/.easy-verifier-sot/`, used immediately with a visible source tag and link, and embedded in the report so replay reproduces the score anywhere.

**Out of scope**:
- Deciding which fields are missing / needs_input (T037)
- Review statuses (T038)

**Requirement Refs**:
- FR-042 (local half)
- FR-046 (storage + tags)
- FR-048: source tags, embedded entries, replay parity
- FR-022 / DDR-0005 parity
- NFR-007: never write to target repo

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T035 — rules consume registry fields with tags

**Entry point**: `registry_entries`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Agent input accepts `registry_entries: [{language|framework, field, value, citation_url, source_tag}]` in MCP and CLI `--agent-input` | intake |
| 2 | Validation: `citation_url` must be `https://` and well-formed; field must be a known registry field; value bounded (size, pattern count, regex compiles with a timeout-safe subset); invalid entries rejected with a capped error list (≤20 lines) | untrusted input |
| 3 | Valid entries saved to `$EASY_VERIFIER_SOT` or `~/.easy-verifier-sot/` (atomic write); curated fields are never overridden (curated wins, reported) | local layer |
| 4 | Rule inputs using local data show `agent-researched (unreviewed)` or `user-supplied` + link in `score` and report | tags |
| 5 | Report embeds all registry entries used; replaying that report's agent input on a machine with an empty local layer yields byte-equal output (DDR-0005 normalization) | replay parity |
| 6 | `compose.yaml` bind-mounts `${EASY_VERIFIER_SOT:-~/.easy-verifier-sot}` read-write; with no mount/unwritable dir, scoring works on curated only and says research cannot be saved | Docker |
| 7 | No write ever lands under the target repo except `reports/` | NFR-007 |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | agent input with a valid Kotlin `assertions` entry | saved, used, tagged `agent-researched (unreviewed)` | automated test |
| 2 | entry with `citation_url: http://…` or catastrophic regex | rejected with reason | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
docker compose build && bash scripts/verify_container.sh
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T036.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T036.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `core/roles.py` `parse_agent_input` + `load_repo_config` — bounded parsing, capped errors (`MAX_ERROR_LINES`)

Reuse the agent-input parser; add a `registry_entries` section. ReDoS guard: reject patterns with nested quantifiers and cap length. Home-dir resolution via `Path.home()` with env override; never follow symlinks out of the SOT dir.

---

## Edge Case Checklist

- [ ] Two MCP calls writing the same entry concurrently → atomic replace, last writer wins, deterministic content
- [ ] SOT dir is a symlink to elsewhere → refuse
- [ ] Malicious field names (`../`) → rejected
- [ ] Container user 10001 permissions on the mount

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/registry.py` | local layer read/write + merge |
| `src/easy_verifier/core/roles.py` | agent-input `registry_entries` |
| `src/easy_verifier/adapters/*` | pass-through |
| `src/easy_verifier/core/report.py` | embed entries + tags |
| `compose.yaml` | SOT bind mount |
| `docs/DOCKER_MCP_GUIDE.md` | mount instructions |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| registry/curated/* | only changes on a release |
| target repo outside reports/ | NFR-007 |

---

## Test Plan

Intake validation tests (incl. ReDoS, path traversal, http URL); local write/merge tests; replay byte-parity test; Docker verify script with mount.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (High risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T036.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
