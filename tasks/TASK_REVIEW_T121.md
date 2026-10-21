# TASK_REVIEW — T121: Secret hits in context files must not lower a narrow-scope security score

> Sibling of `tasks/TASK_GUIDE_T121.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t121_context_secret_hits.py` (10 tests, new). AC1+AC6 `test_hits_only_in_an_unchanged_context_lockfile_are_not_counted` (changed `src/a.py` + unchanged `.claude/x-lock.json` of 64-hex digests → 0, cites only `src/a.py`); AC2+AC4 `test_a_secret_in_a_changed_file_is_still_counted`; AC3 `test_context_hits_stay_visible_and_redacted` (count + path in derivation; excerpt and serialized pack hold fingerprints, never a digest); AC5 `test_project_scope_counts_every_file_and_serializes_as_before` + existing project snapshot `tests/test_t068_priority_batches.py` (unchanged, passes) + `test_other_dimensions_packs_serialize_as_before`. `uv run --python 3.12 --extra dev pytest tests/test_t121_context_secret_hits.py -v` → `10 passed in 0.79s`, exit 0. Failed on pre-fix `d22c90c` (7 failed, 2 passed). Pins updated: `tests/test_t055_git_evidence_areas.py` (legacy key list), `tests/test_t071_evaluation_docs.py` (DECLARED `redacted_file_share`). |
| Verification command run | ☑ pass | `uv run --python 3.12 --extra dev pytest tests -k "redaction or context_role" -q` → `177 passed, 3102 deselected in 11.25s`, exit 0. (The `-k` filter does not select the new file by name; run explicitly above.) |
| Negative cases hold | ☑ pass | Changed lockfile is measured (`test_a_changed_lockfile_is_measured`); path-less hit still counted (`test_a_hit_without_a_path_is_counted_as_before`); empty narrow scope abstains (`test_empty_narrow_scope_still_abstains`); only-context pack abstains with a context reason (`test_only_context_files_read_abstains`). Sabotage: metric ignores `context_files` → 5 failed; security never records context files → 4 failed; security records every role file (in scope / project too) → 2 failed. |
| verify | ☑ pass | Real HUN-34 run (see Demonstration): `redaction_hits_observed` 123 → 5; the 118 hits from `.claude/harness-lock.json` and `web/package-lock.json` are named in the derivation and not counted; excerpts still fingerprinted. Metric behaviour confirmed — pass. Security rating stays 18: the 5 remaining hits are in the changed `tasks/TASK_REVIEW_HUN-34.md` (a branch name and an absolute path matched as key material / entropy), measured per AC2; their precision is out of scope (no new exemptions) — open question to Supervisor. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed: `core/metrics.py` (two secret metrics + helpers), `core/models.py` (`EvidencePack.context_files`, `_OMITTED_WHEN_ABSENT`), `core/pipeline.py` (one field, dedup + path redaction), `dimensions/security.py` (records context files read outside a narrow scope), docs. Only the security pack can carry the new key; every other pack and every project pack serializes as before. Manual security pass (built-in `security-review` cannot resolve `origin/HEAD` here): redaction untouched; `context_files` are paths run through `_redact_paths` like `files_read`; derivations list only already-redacted paths; canary asserts no digest in the serialized pack. |
| Full smoke suite still green (no regression) | ☑ pass | At `b76dcf2`: `uv run --python 3.12 --extra dev pytest tests -q` → `3276 passed, 3 skipped in 672.08s (0:11:12)`, exit 0 (3266 before + 10 new). An earlier run at `4716042` failed 4: two T055 pack-key pins (fixed by narrowing `context_files` to the security pack), the T071 doc identifier pin (declared), and `test_adapter_parity` under 3 concurrent suites (passes alone and in this run). `test_container_parity_is_explicitly_verified` passed here. ruff check clean. |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | No UI (Critical Constraint 11); pure backend metric change. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | No UI (Critical Constraint 11); pure backend metric change. |
| **UI: Responsiveness at target viewports** | ☐ N/A | No UI (Critical Constraint 11); pure backend metric change. |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured by backend-developer in the T121 worktree on branch `fix/T121-context-secret-hits` at `5a19bd2` (no implementation commit yet). Script: security pack via `combined_pack(["security"], repo, "changes", 120000, ref="3f4aceb^1...3f4aceb^2")`, hits grouped by (path, detector), then MCP `score(...)` security rating on `easy-personal-mcp` (not modified).

```
$ PYTHONPATH=src <main>/.venv/bin/python scratchpad/hun34.py < /dev/null
captured: 2026-10-21T10:58:07+00:00
easy-verifier HEAD: 5a19bd2
pack.redactions: 123
   116  .claude/harness-lock.json  high_entropy_hex
     3  tasks/TASK_REVIEW_HUN-34.md  key_material_segment
     2  tasks/TASK_REVIEW_HUN-34.md  high_entropy_string
     2  web/package-lock.json  high_entropy_string
security rating: 18
  redaction_hits_observed = 123 FAILED
  redaction_hits_observed derivation: 123 secret redaction(s) recorded while building this pack from the 18 file(s) listed here; a lower bound on the repository, since only these files were read
  redacted_file_share derivation: 3 file(s) with at least one redaction (.claude/harness-lock.json, tasks/TASK_REVIEW_HUN-34.md, web/package-lock.json) / 18 file(s) read
```

Only `tasks/TASK_REVIEW_HUN-34.md` is changed by HUN-34; `.claude/harness-lock.json` and `web/package-lock.json` are context-role (lockfile) files read repo-wide, yet they supply 118 of the 123 counted hits.

**AFTER**: same script, same repo and ref, at `b76dcf2`:

```
$ PYTHONPATH=src <main>/.venv/bin/python scratchpad/hun34.py < /dev/null
captured: 2026-10-21T11:27:54+00:00
easy-verifier HEAD: b76dcf2
pack.redactions: 123
   116  .claude/harness-lock.json  high_entropy_hex
     3  tasks/TASK_REVIEW_HUN-34.md  key_material_segment
     2  tasks/TASK_REVIEW_HUN-34.md  high_entropy_string
     2  web/package-lock.json  high_entropy_string
security rating: 18
  redaction_hits_observed = 5 FAILED
  redaction_hits_observed derivation: 5 secret redaction(s) recorded while building this pack from the 14 file(s) listed here; a lower bound on the repository, since only these files were read; 118 more in 2 context file(s) read from the whole repository are redacted but not counted, since context is cited, not measured: .claude/harness-lock.json, web/package-lock.json
  redacted_file_share derivation: 1 file(s) with at least one redaction (tasks/TASK_REVIEW_HUN-34.md) / 14 file(s) read; 118 more in 2 context file(s) read from the whole repository are redacted but not counted, since context is cited, not measured: .claude/harness-lock.json, web/package-lock.json
```

**DELTA**: At a narrow scope, secret hits in unchanged context files (here 118 of 123, from `.claude/harness-lock.json` and `web/package-lock.json`) no longer count against security; they stay redacted and are named in the derivation. HUN-34 still rates 18 because 5 false-positive hits sit in the changed `tasks/TASK_REVIEW_HUN-34.md`, which is measured by design.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
