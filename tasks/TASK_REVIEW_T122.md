# TASK_REVIEW — T122: MCP score reply is a summary by default; full metric detail on request

> Sibling of `tasks/TASK_GUIDE_T122.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | pass | `tests/test_t122_score_summary.py` (11 cases: AC1 default/explicit summary vs full, AC2 full equals unfiltered payload, AC3 five bad `detail` values, AC4 gate refs accepted on the next call without metric rows, AC5 description, AC6 CLI still carries `metrics.metrics` and equals the core payload). Written first: before the change 9 of 11 failed (the 2 passing were the explicit-summary and CLI guards); after: `11 passed in 2.26s` |
| Verification command run | pass | `uv run --python 3.12 --extra dev python -m pytest tests -k "score and (detail or summary)" -q` -> `15 passed, 3264 deselected in 3.39s` |
| Negative cases hold | pass | `detail` in `brief`, `""`, `FULL`, `None`, `1` each raise `ToolError` whose message names `summary` and `full` (pydantic `Literal` validation) |
| verify | pass | Real run on easy-personal-mcp HUN-34 (changes, `3f4aceb^1...3f4aceb^2`): summary 93,557 chars vs full 832,501 in the same session (see Demonstration); all keys except `metrics` equal. Skill `verify` itself not invoked by the implementer: Supervisor Stage 5 — pass for the run above |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | pass | Diff reviewed directly: one function in `adapters/mcp_server.py` (no hub file, core and CLI untouched), its callers in tests (every `score` call site grepped), README and EVALUATION_GUIDE lines. `security-review`/`code-review` skills not run by the implementer; no new input surface beyond a `Literal` parameter |
| Full smoke suite still green (no regression) | pass | `3276 passed, 3 skipped in 672.08s (0:11:12)`, exit 0. `ruff check .` clean. An earlier full run had 4 failures (parity combined test, which I had not yet updated, plus `test_t055` x2 and `test_t071_evaluation_docs`); the three non-parity ones pass in isolation, on the stashed baseline and in the final full run, and I could not attribute them (not reproduced) |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | backend-only task, no UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | backend-only task, no UI |
| **UI: Responsiveness at target viewports** | ☐ N/A | backend-only task, no UI |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured 2026-10-21T10:57:34Z on branch feat/T122-score-summary at 5a19bd2 (no implementation commit yet), `uv run --python 3.12 python size.py` calling `mcp_server.score(repo=<easy-personal-mcp>, scope="changes", ref="3f4aceb^1...3f4aceb^2", budget_bytes=120000)`, printing `len(json.dumps(payload))` and per-key sizes:

```
2026-10-21T10:57:34.802028+00:00 total 809449
  ratings 44669
  overall 14520
  change_risk 3261
  areas_measured 815
  areas_without_rule 237
  improvement_plan 15596
  warnings 4697
  metrics 717819
  provenance 921
  detected_stack 90
  needs_input 6635
```

**AFTER**: same script and arguments, `detail` omitted (default), 2026-10-21T11:14:49Z, with the change:

```
total 93557
  ratings 45031
  overall 14519
  change_risk 3261
  areas_measured 815
  areas_without_rule 237
  improvement_plan 16831
  warnings 4697
  metrics 31          <- {"dimensions_without_pack": []}
  provenance 921
  detected_stack 90
  needs_input 6935
```

Same run with `detail="full"` (11:14:53Z): total 832,501. Reply 809,449 -> 93,557 (-88%). The full
total differs from the BEFORE total because easy-personal-mcp's state changed between the two captures (ratings
44,669 -> 45,031, improvement_plan 15,596 -> 16,831), not because of this change; compare summary against
the same-session full (832,501).

**DELTA**: An agent can call MCP `score` on a large change and get a reply that fits inline (about 94k characters instead of about 830k), and ask for `detail="full"` only when it needs the metric rows.

**WITNESS**: backend-developer agent, 2026-10-21 (BEFORE 10:57Z, AFTER 11:14Z), traced in `memory/event-trace/T122.jsonl`; Supervisor (main session) re-ran MCP stdio `score` on HUN-34 at 2026-10-21 ~12:15Z: reply 93,557 chars, `metrics` keys `['dimensions_without_pack']` — pass.

---

### Changed existing assertions

No assertion was weakened or removed. Every change adds `detail="full"` to an existing MCP `score` call,
because default `score` no longer carries `metrics.metrics` and these tests compare the MCP payload
byte-for-byte with the CLI payload (which still carries it), or read the rows:

| File | Call | Why |
|------|------|-----|
| `tests/test_score_operation.py` | `_mcp_score` helper | CLI/MCP payload equality |
| `tests/test_t028_evaluate_gate.py` | `_mcp` helper | CLI replay byte-equal to MCP |
| `tests/test_t109_change_kind_gate.py` | `_mcp` helper | CLI/MCP byte-equal |
| `tests/test_t112_test_symbol_pairs.py` | `_mcp` helper | CLI/MCP byte-equal |
| `tests/test_t035_cited_rules.py` | `call_tool("score", ...)` | CLI/MCP payload equality |
| `tests/test_t068_priority_batches.py` | `mcp_server.score` in `test_mcp_and_cli_payloads_agree_apart_from_needs_input` | CLI/MCP equality (other calls in the file read only `needs_input`, left as the default) |
| `tests/test_t078_repo_conventions.py` | `call_tool` in the toml parity test; `mcp_server.score` in `test_no_leak_between_back_to_back_mcp_calls` | CLI/MCP equality; the leak test reads `layer_violations` from `metrics.metrics` |
| `tests/test_t084_breaking_read_only.py` | `mcp_call("score", ...)` | reads the `api_breaking` metric row |
| `tests/test_t087_third_party_exclusion.py` | `mcp_server.score` | CLI/MCP equality |
| `tests/test_t098_capped_disclosure.py` | `mcp_server.score` | CLI/MCP equality |
| `tests/test_t101_shared_container.py` | three `score` calls | stdio/HTTP payload comparison; the lock tests' fake core returns no `metrics`, so they ask for `full` (no filtering) |
| `tests/integration/test_adapter_parity.py` | two `score` calls | CLI/MCP payload equality (the per-dimension call is untouched) |

Not a regression: `test_container_parity_is_explicitly_verified` passed in the final run here.

## Stage 4 — Supervisor review (2026-10-21)

- code-review: P0 0 · P1 0 · P2 1 (fixed: `del payload["metrics"]["metrics"]` raised KeyError on a payload without `metrics`; now `payload.get("metrics", {}).pop("metrics", None)`; T122/T101/score tests 51 passed) · P3 0. `metrics.dimensions_without_pack` kept, as the guide specified.
- security-review (Medium; done by hand): output-only reduction, no new input beyond a pydantic-validated `Literal`; CLI and core untouched. — pass
