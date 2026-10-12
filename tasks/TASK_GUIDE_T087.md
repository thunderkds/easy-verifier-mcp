# TASK_GUIDE — T087: Exclude third-party code from evaluation
**Date**: 2026-10-12
**Complexity Level**: C2
**Risk Level**: Medium
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
7. Read `docs/ddr/0012-recognize-by-behaviour-and-content-not-names.md` (§5) and `BRAINSTORMING_LOG_document-recognition.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-10-12), after the bryony retest: *"we are scoring the document related like architecture
like our definition of kit repos, but you know, we are not the judge"* led to DDR-0012. Grilling
decision G7 makes third-party exclusion a prerequisite: in the retest, `bryony/scraping-devops`
scored **architecture 0**. Its 1 import cycle and 8 layer violations all come from a full copy of
Harbor (Go) committed under `docker-registry/harbor/`. That copy has its own `LICENSE`, `NOTICE`,
`AUTHORS`, `README.md` and `vendor/`. `core/scope.py:_EXCLUDED_DIRS` excludes neither `vendor`
nor nested third-party projects.

**Restated intent**:
> Code the repository's team did not write never feeds a rating, layer, cycle or document
> recognition. Every exclusion is visible in the output, with the reason it was excluded, so nothing
> silently disappears.

**Out of scope**:
- Rating weights, floors or any rule logic
- Behaviour-based layers (T088), document recognition (T089)
- Judging whether vendoring is good practice

**Requirement Refs**:
- FR-074 (added 2026-10-12): third-party code excluded and disclosed
- US-021: owner of an ordinary repository not following this kit's conventions

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed (Supervisor, 2026-10-12; user approved Stage 2 with "go")
- [x] Domain terms align with `PROJECT_SPEC.md` (scope, source role, excluded)
- [x] Every Acceptance Criterion traces to the Requirement
- [x] FR-074 exists in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: None

**Entry point**: `scope._EXCLUDED_DIRS` / the repo file-set walk in `core/scope.py` (and `roles._in_excluded_dir`)

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Paths matching the **third-party categories** of GitHub Linguist's `vendor.yml` are excluded, vendored as a pinned, filtered, checksummed snapshot (commit `d0921d10`, MIT) with NOTICE listing kept and dropped categories. **Kept**: Node/Bower/Yarn-2/Go Godeps dependency dirs, `(3rd|third)[-_]?party/`, `vendors?/`, `[Vv]+endor/`, minified `(\.|-)min\.(js|css)$`, `Carthage/`, `*.framework`, `flow-typed/`, bundled-framework entries (jQuery, MathJax, …). **Dropped**: CI/editor configs, `.d.ts`, `dist/`, `cache/`, `env/`, fixtures, git config files, wrapper scripts, and `[Ee]xtern(als?)?/` (team code on bryony). There are **no default 'generated' patterns**: `generated.rb` is code and counts lockfiles. 'generated' comes only from `.gitattributes` (AC 2). *(Amended 2026-10-12 by the Supervisor after the implementer found that `vendor.yml` is a language-statistics list, not a third-party list; Option A.)* | third-party never feeds a rating |
| 2 | `.gitattributes` entries with `linguist-vendored` or `linguist-generated` (set, not `-` or `=false`) exclude their paths. A `-linguist-vendored` entry re-includes a path that a default pattern excluded | the repo's own declaration wins |
| 3 | `.easy-verifier.toml` can declare `exclude = ["glob", …]`. Paths are validated with the same bounds as role globs. An invalid glob is a rejected config, never silently ignored | declared by the project |
| 4 | **Nested third-party root**: a directory below the repo root that holds its own licence file (`LICENSE*`, `COPYING*`) **and** at least one of `NOTICE*`, `AUTHORS*` or `CONTRIBUTORS*` is excluded as third-party, together with everything below it. The repo root is never excluded this way | Harbor case |
| 5 | Every exclusion is disclosed in the payload as `excluded: third-party` with its reason kind (`linguist-pattern`, `gitattributes`, `declared`, `nested-project`) and the matched rule. The HTML report shows a folded count plus list | nothing silently disappears |
| 6 | Negative: a monorepo package with only its own `LICENSE` (no NOTICE/AUTHORS/CONTRIBUTORS) is **not** excluded. A test fixture shapes this as `packages/shared/{LICENSE,package.json}` | precision |
| 7 | **Real repos (paste evidence)**: scraping-devops excludes `docker-registry/harbor/**` (nested-project) and the architecture inputs no longer cite any Harbor file. bryony, kitchd, ai-training and coffee-shop-api exclude nothing they did not before, or each new exclusion is listed and justified by hand in the review | done means real-repo verified |
| 8 | CLI and MCP give byte-equal output after DDR-0005 normalization. The T068 snapshot changes only where an exclusion applies | parity |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | fixture with `vendor/lib.js` and `app/x.min.js` | both excluded, reason `linguist-pattern` | automated test |
| 2 | fixture `.gitattributes`: `gen/** linguist-generated` | `gen/` excluded, reason `gitattributes` | automated test |
| 3 | fixture `third/harbor/{LICENSE,NOTICE,api/a.go}` | `third/harbor/**` excluded, reason `nested-project` | automated test |
| 4 | fixture `packages/shared/{LICENSE,package.json,index.ts}` | not excluded | automated test |
| 5 | sabotage: delete the `NOTICE` from fixture 3 | it is no longer excluded (the test fails if the predicate is hard-wired) | automated test (pins both extremes) |
| 6 | scraping-devops real run | no `docker-registry/harbor/` path in any rating input | pasted output |

### Verification Command (exact, runnable)

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
.venv/bin/easy-verifier score --repo /home/hungnguyenhuu/workspace/project/bryony/scraping-devops --scope project > /tmp/sd.json   # run_in_background
```

### Evidence

> Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T087.md`.

---

## UI / Design Acceptance Criteria

> N/A: backend only. The HTML report reuses existing folded-list markup. All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `core/scope.py` `_EXCLUDED_DIRS` and its walk (exclusion point);
`registry/vendored/linguist.json` + `NOTICE` + `CHECKSUMS.sha256` (how vendored data is pinned and
cited); `roles.py` toml glob validation (bounds).

Apply exclusion through **one path predicate built once per repo** (pattern: `git_ignore_filter`), called by both existing walkers (`scope._walk_files` and `context._walk`), which today disagree (`context._EXCLUDED_DIRS` has `vendor`/`target`, `scope` does not). Never write a third walker, and never filter per
dimension. Carry the reason through to the payload in the same structure as the existing
`excluded: secret-bearing` disclosure (DDR-0002). The nested-root predicate is deliberately
conservative (licence **plus** NOTICE/AUTHORS/CONTRIBUTORS). Do not widen it without the
Supervisor's approval.

---

## Edge Case Checklist

- [ ] A symlinked directory that resolves outside the repo stays handled by the existing containment logic
- [ ] Nested third-party root inside an already-excluded dir: one disclosure, not two
- [ ] `.gitattributes` in a subdirectory applies only below it (git semantics)
- [ ] A secret-bearing file inside a third-party dir keeps the `secret-bearing` exclusion semantics (bytes never read)
- [ ] `--scope changes` / `task` / `worktree` also apply the exclusion
- [ ] Batches (DDR-0010): excluded files never count toward the source cap or batch totals

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/scope.py` | exclusion predicate + reasons |
| `src/easy_verifier/core/roles.py` | toml `exclude` key + validation; `_in_excluded_dir` reuse |
| `src/easy_verifier/registry/vendored/linguist_vendor.json` (+ NOTICE, CHECKSUMS) | filtered snapshot of Linguist `vendor.yml` third-party categories |
| `src/easy_verifier/core/judge.py` / `report.py` | disclosure in payload + report |
| `docs/SCORING_RULES.md`, `docs/EVALUATION_GUIDE.md` | one paragraph each |
| `tests/test_t083_third_party_exclusion.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `RATING_RULES` weights in `core/judge.py` | no weight change |
| `registry/curated/conventions.toml` `layer_paths` | T088 |

---

## Test Plan

Unit fixtures for every reason kind, including the both-extremes sabotage of the nested predicate
(AC 6, SC 5). One integration run through `score` on a fixture repo. Real-repo runs on all 5 repos,
in the background, one at a time.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review (Medium risk: path handling, config parsing)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T087.md`
- [ ] Real-repo runs pasted (AC 7)
- [ ] Supervisor notified: task ready for Stage 4 review
