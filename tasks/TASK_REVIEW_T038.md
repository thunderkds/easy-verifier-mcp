# TASK_REVIEW — T038: User review gate for researched entries (good / needs improvement / reject)

> Sibling of `tasks/TASK_GUIDE_T038.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t038_review_gate.py` (new; 47 tests after the Stage 4 fixes). AC1: `test_new_local_entry_starts_pending_in_the_file`, `test_file_without_status_loads_pending_and_bad_status_is_rejected`, `test_curated_entries_carry_no_review_status`, `test_pending_entry_scores_immediately`. AC2: `test_mcp_lists_each_pending_entry_once_with_value_and_link`, `test_review_is_mcp_only`, `test_review_list_is_capped_and_overflow_counted`, `test_valid_review_shapes_accepted`, `test_invalid_reviews_rejected`, `test_secret_shaped_comment_refused`. AC3: `test_good_approves_and_retags_everywhere` (SC1), `test_improve_keeps_scoring_and_returns_comment_in_reference_gate`, `test_replacement_supersedes_improved_entry_and_second_round_asks_user`, `test_reject_removes_entry_and_dependent_rule_abstains` (SC2), `test_rejection_record_replays_byte_equal_on_empty_machine`. AC4: `test_reviewed_entry_never_asked_again_even_if_resubmitted`, `test_second_answer_for_a_reviewed_entry_is_ignored_with_note`. Stage 4 fixes: TOML round-trip (emoji/control chars/lone surrogates) and `test_improve_past_the_round_cap_keeps_the_file_loadable`. `tests/test_t036_local_registry.py` has one expected dict updated for AC1's `review_status = "pending"`. Implementer red-first: 36/38 failed before the implementation. Sabotage: 8 guards plus 3 more for the P1 fix and 1 for the P3, each failing its targeted tests |
| Verification command run | ☑ pass | Supervisor 2026-09-29, at HEAD `711842c` (pre-P3 run at `0e86ea3`): pytest `1388 passed, 2 skipped` (exit 0); implementer after the P3 fix `1389 passed, 2 skipped` (exit 0); `ruff check src tests` gives `All checks passed!` (exit 0) |
| Negative cases hold | ☑ pass | A rejection does not abstain in a repo without that language (`test_rejection_does_not_touch_a_repo_without_that_language`) or when other data exists for the field (`test_rejection_with_other_data_for_the_field_does_not_abstain`). An unknown id or a second answer is ignored with a registry note. The replay key accepts only `review_status: "rejected"`. A secret-shaped comment is refused. More than 20 answers are refused |
| verify | ☑ pass | Supervisor 2026-09-29T05:39Z, real MCP stdio server (worktree src) on a committed zig fixture repo, `--scope project`. Call 1 listed 5 pending ids under `needs_input.review`. `reviews` {assertions: reject, manifests: good} left 3 listed. The reference gate re-asked `zig.assertions` with `rejected: ["expect("]`. `assertion_density_per_test` abstains with "registry field zig.assertions was rejected by the user and no other data exists for it…". Embedded entries carry `review_status: rejected` and tag `agent-researched (user-approved)` for manifests. CLI `score` on machine A (live layer) vs machine B (empty layer + `--agent-input replay.json` of the embedded entries): **BYTE-EQUAL** (`cmp`). The CLI payload has no `review` key, and the CLI run left machine A's layer unchanged — pass. Note: at `--scope worktree` on a fully committed repo the pack reads nothing, so correctly no abstention |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Code review of the full `6e0e723..HEAD` src diff (registry, gate, roles, score, metric_tables, judge, report, mcp_server) and its callers. P1 (confidence 100, reproduced): `json.dumps` surrogate-pair escapes wrote invalid TOML (one emoji in a comment made the local-layer file unloadable) — fixed `0e86ea3`. P3 (CLI walk) refuted: `review_requests` sits after the detect-gates early return. Security review (built-in skill unavailable: no `origin/HEAD`; done manually): no P0/P1. P3 unbounded `improve_rounds` vs load cap 100 — fixed `711842c` (user decision). The out-of-list `report.py` change was accepted by the Supervisor (AC-driven) |
| Full smoke suite still green (no regression) | ☑ pass | full suite 1389 passed, 2 skipped, exit 0 |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend task; the report gains a single text marker, covered by `test_report_marks_the_rejection_record_as_not_used` |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Pure backend task, no UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | Pure backend task, no UI |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured by backend-developer in worktree `easy-verifier-mcp-T038` at HEAD `6e0e723`, before any
T038 implementation commit; no review status exists and the agent-input `reviews` key is refused):

```text
$ date -u; git rev-parse --short HEAD
2026-09-29T03:28:35Z
6e0e723
$ grep -rn 'review_status\|user-approved\|reviews' src/easy_verifier/core/{registry,gate,roles}.py
(exit 1: no matches)
$ PYTHONPATH=src python -c 'validate_agent_input({"reviews": {"kotlin.test_name_patterns.x": "good"}}, ".")'
RoleInputError: agent input: 1 error(s): reviews: unknown key; only picks, gate_evaluations and registry_entries are accepted
```

**AFTER** (Supervisor, 2026-09-29T05:39Z, HEAD `711842c`, real MCP stdio + CLI on the zig fixture):

```text
CALL1 review listed: ['zig.assertions.956740e5edbf', 'zig.manifests.a8e496cdcbd5', 'zig.source_extensions.d89c8217e5fe', 'zig.test_declarations.bcbea60e8980', 'zig.test_name_patterns.24b8f6487ab9']
AFTER review still listed: ['source_extensions', 'test_declarations', 'test_name_patterns']
REFERENCE re-ask: [{'language': 'zig', 'field': 'assertions', 'why': 'rules: test-strategy.assertion_density_per_test', 'rejected': ['expect(']}]
ABSTAIN reason: ...assertion_density_per_test", "registry field zig.assertions was rejected by the user and no other data exists for it; the me...
EMBEDDED: [('assertions', 'agent-researched (unreviewed)', 'rejected'), ('manifests', 'agent-researched (user-approved)', None), ...]
$ cmp a.json b.json   # machine A live layer vs machine B empty layer + --agent-input replay
BYTE-EQUAL
```

**DELTA**: The user now reviews each locally researched registry entry once, through the calling agent. good approves and retags it, improve sends it back for re-research with a comment, and reject removes it and makes its rules abstain, remembered across calls and replayable byte-equal, instead of copying data by hand.

**WITNESS**: Supervisor, 2026-09-29T05:39:30Z. `memory/event-trace/T038.jsonl` holds 63 records, including the Supervisor's MCP probe and CLI replay `cmp` runs, independent of the implementing agent's own runs.
