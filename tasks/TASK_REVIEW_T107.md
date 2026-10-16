# TASK_REVIEW — T107: change-risk slice 1

> Sibling of `tasks/TASK_GUIDE_T107.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☐ pass / ☐ fail / ☐ N/A | |
| Verification command run | ☐ pass / ☐ fail / ☐ N/A | |
| Negative cases hold | ☐ pass / ☐ fail / ☐ N/A | |
| verify | ☐ pass / ☐ fail / ☐ N/A | |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail / ☐ N/A | |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail / ☐ N/A | |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | No UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | No UI |
| **UI: Responsiveness at target viewports** | ☐ N/A | No UI |

---

## Demonstration

**BEFORE**: captured 2026-10-16T11:16:34Z–11:16:44Z on develop `29ef8fe` (no T107 code), py3.12 venv,
`python -m easy_verifier.adapters.cli score --repo <real-repos>/node-monorepo --scope changes --ref 09be767d0 < /dev/null`
(payload under the worktree's git-ignored `.local/t107/before/`; summary = overall + per-dimension rating/abstention,
with every `"not in the resolved … scope"` miss listed):

```
overall: 97 (3 of 13 rated: architecture, code-quality, blast-radius)
  api: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.25)
  architecture: 90
  blast-radius: 100
  code-quality: 100
  data: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.25)
  infrastructure: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.25)
      - container-config: not in the resolved changes scope
  operations: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.25)
      - dev-environment: not in the resolved changes scope
  reliability: ABSTAIN insufficient_measured_weight (coverage 0.25 / floor 0.25)
      - readme: not in the resolved scope
  requirement-fidelity: ABSTAIN below_coverage_floor (coverage 0.2 / floor 0.5)
  security: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.25)
      - package-manifest: not in the resolved changes scope
      - lockfile: not in the resolved changes scope
      - auth-code: not in the resolved changes scope
      - container-config: not in the resolved changes scope
      - ci-workflow: not in the resolved changes scope
  solution-fit: ABSTAIN no_static_rule (coverage 0.0 / floor 0.5)
  supply-chain: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.4)
      - package-manifest: not in the resolved changes scope
      - lockfile: not in the resolved changes scope
      - ci-workflow: not in the resolved changes scope
      - licence-file: not in the resolved changes scope
  test-strategy: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.2)
      - test-config: not in the resolved changes scope
      - test-file: not in the resolved changes scope
      - ci-workflow: not in the resolved changes scope
```

Note: requirement-fidelity's stated misses here are `requirements-doc`/`spec-doc` "not found: no file in the
repository matched", route handlers not found in the 1 in-scope source file, and "no in-scope test file" —
none is a context role outside the diff.

**AFTER**: captured 2026-10-16T11:34:26Z–11:34:42Z, same command, T107 working tree (uncommitted at run time;
code identical to the T107 commit):

```
overall: 85 (5 of 13 rated: architecture, code-quality, security, blast-radius, supply-chain)
  api: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.25)
  architecture: 90
  blast-radius: 100
  code-quality: 100
  data: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.25)
  infrastructure: ABSTAIN all_metrics_abstained (coverage 0.25 / floor 0.25)
  operations: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.25)
      - dev-environment: not in the resolved changes scope
  reliability: ABSTAIN insufficient_measured_weight (coverage 0.5 / floor 0.25)
  requirement-fidelity: ABSTAIN below_coverage_floor (coverage 0.2 / floor 0.5)
  security: 100
  solution-fit: ABSTAIN no_static_rule (coverage 0.0 / floor 0.5)
  supply-chain: 35
  test-strategy: ABSTAIN insufficient_measured_weight (coverage 0.5 / floor 0.2)
      - test-file: not in the resolved changes scope
```

The test-strategy pack (CLI `test-strategy`, same repo/ref) carries the AC3 note:
`Read as repository context at the changes scope, not as changed files: test-config, ci-workflow. …`

**DELTA**: every `"not in the resolved … scope"` miss for a context role is gone (security and supply-chain now
rate, test-strategy/reliability/infrastructure clear their coverage floor); the two remaining are measured or
non-FR-078 roles (`test-file`, `dev-environment`), and overall moves 97 → 85.

**WITNESS**: backend-developer agent (T107), 2026-10-16, py3.12 venv in the T107 worktree.

**AC4 (project scope, before 11:16Z vs after 11:34Z)** — raw payload bytes and the DDR-0005 normalization
(`tests/integration/test_adapter_parity.normalize`) both compared:

```
self: raw EQUAL (1145004 vs 1145004 bytes); normalized EQUAL
fullstack-ts: raw EQUAL (1866660 vs 1866660 bytes); normalized EQUAL
python-ml: raw EQUAL (1470414 vs 1470414 bytes); normalized EQUAL
node-monorepo: raw EQUAL (2264964 vs 2264964 bytes); normalized EQUAL
```

`self` = a clone of this repo pinned at develop `29ef8fe`, scored by the old and the new code (scoring the live
worktree would differ only because its own source changed).
