# TASK_REVIEW — T037: [Short Title]

> Sibling of `tasks/TASK_GUIDE_T037.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☐ pass / ☐ fail | [test file path(s) — required before Done] |
| Verification command run | ☐ pass / ☐ fail | [paste actual output] |
| Negative cases hold | ☐ pass / ☐ fail | |
| verify | ☐ pass / ☐ fail / ☐ N/A | [what was observed — must literally state "pass" or "fail" here too, e.g. "skill run, feature confirmed working — pass": the merge gate scans this Notes column for the word "pass", not just the Result column] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [what was reviewed vs. skipped, and why] |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail | |
| **UI: Visual regression (diff or verdict pasted)** | ☐ pass / ☐ fail / ☐ N/A | [screenshot path or LLM verdict — required for UI tasks, Hard-Stop Gate 6] |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ pass / ☐ fail / ☐ N/A | [method used + output] |
| **UI: Responsiveness at target viewports** | ☐ pass / ☐ fail / ☐ N/A | [viewports tested, any overflow findings] |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured 2026-09-28T12:56:57Z on HEAD `7de1e21` (before any T037 implementation commit),
by backend-developer. Real MCP stdio server (`python -m easy_verifier.adapters.mcp_server`, worktree
`PYTHONPATH=src`) driven by an `mcp` `stdio_client`, tool `score` with `repo=<scratch>/node-express`,
`scope=project`, temp `EASY_VERIFIER_SOT` (empty). Scratch repo: `package.json` with
`"dependencies": {"express": "^4.19.2"}`, `src/app.js`, `README.md`; `ls src/easy_verifier/registry/curated | grep express`
→ `no curated express entry`.

```
payload keys: ['metrics', 'needs_input', 'overall', 'provenance', 'ratings']
detected_stack: null
needs_input keys: ['gate_evaluations']
needs_input.reference: None
needs_input bytes: 586
overall: {"kind": "overall_rating", "value": 46, "contributor_count": 1, "total_dimension_count": 7, "contributors": ["test-strategy"], "contributor_values": [["test-str
exit=0
```

No `detected_stack` / framework detection anywhere in the payload, and `needs_input` carries only
`gate_evaluations` — no `needs_input.reference`.

**AFTER**: captured 2026-09-28T13:07:12Z on HEAD `f9854eb` by backend-developer — same driver,
same scratch repo, same arguments, fresh empty temp `EASY_VERIFIER_SOT`:

```
payload keys: ['detected_stack', 'metrics', 'needs_input', 'overall', 'provenance', 'ratings']
detected_stack: {"languages": ["js-ts"], "frameworks": [{"name": "express", "language": "js-ts"}]}
needs_input keys: ['gate_evaluations', 'reference']
needs_input.reference: {
 "requests": [
  {
   "framework": "express",
   "extends": "js-ts",
   "field": "source_extensions",
   "why": "rules: architecture.top_level_import_cycles, blast-radius.max_fan_in_changed, code-quality.functions_over_ccn_10_share, code-quality.max_function_ccn, security.sink_hits_observed, test-strategy.source_files_without_covering_test_share"
  },
  {
   "framework": "express",
   "extends": "js-ts",
   "field": "test_name_patterns",
   "why": "rules: test-strategy.assertion_density_per_test, test-strategy.source_files_without_covering_test_share"
  },
  {
   "framework": "express",
   "extends": "js-ts",
   "field": "test_candidates",
   "why": "rules: test-strategy.source_files_without_covering_test_share"
  },
  {
   "framework": "express",
   "extends": "js-ts",
   "field": "test_declarations",
   "why": "rules: test-strategy.assertion_density_per_test"
  },
  {
   "framework": "express",
   "extends": "js-ts",
   "field": "assertions",
   "why": "rules: test-strategy.assertion_density_per_test"
  },
  {
   "framework": "express",
   "extends": "js-ts",
   "field": "branch_keywords",
   "why": "rules: code-quality.functions_over_ccn_10_share, code-quality.max_function_ccn"
  },
  {
   "framework": "express",
   "extends": "js-ts",
   "field": "comment_delimiters",
   "why": "rules: architecture.top_level_import_cycles, blast-radius.max_fan_in_changed, code-quality.functions_over_ccn_10_share, code-quality.max_function_ccn, security.sink_hits_observed"
  },
  {
   "framework": "express",
   "extends": "js-ts",
   "field": "string_delimiters",
   "why": "rules: architecture.top_level_import_cycles, blast-radius.max_fan_in_changed, code-quality.functions_over_ccn_10_share, code-quality.max_function_ccn, security.sink_hits_observed"
  },
  {
   "framework": "express",
   "extends": "js-ts",
   "field": "function_start",
   "why": "rules: code-quality.functions_over_ccn_10_share, code-quality.max_function_ccn"
  },
  {
   "framework": "express",
   "extends": "js-ts",
   "field": "import_syntax",
   "why": "rules: architecture.top_level_import_cycles, blast-radius.max_fan_in_changed"
  },
  {
   "framework": "express",
   "extends": "js-ts",
   "field": "security_sinks",
   "why": "rules: security.sink_hits_observed"
  },
  {
   "framework": "express",
   "extends": "js-ts",
   "field": "interpolating_strings",
   "why": "rules: security.sink_hits_observed"
  }
 ],
 "omitted": 0,
 "instructions": "Each request names a registry field the rating rules read that this language or framework lacks. For each, in order: do at most 2 lookups, official documentation first. If found, send it on the next score call as an agent_input.registry_entries item: {language or framework (with extends), field, value: [...], citation_url: a clear https link to the primary source, source_tag: \"agent-researched\"}. If 2 lookups do not find it, ask the user, one question at a time, giving your recommended answer, and send their answer with source_tag \"user-supplied\" and the https link they confirm. Until answered, every listed field and the omitted count of further missing fields are scored with generic patterns only; omitted fields are listed once these are answered."
}
reference bytes: 2887
needs_input bytes: 3486
overall: {"kind": "overall_rating", "value": 46, "contributor_count": 1, "total_dimension_count": 7, "contributors": ["test-strategy"], "contributor_values": [["test-str
exit=0
```

Round 2 (13:07:26Z): same call plus `agent_input.registry_entries` = the 12 express fields
(`source_tag: "user-supplied"`, https citation) — saved to the temp layer (`express.toml`), gate closes:

```
payload keys: ['detected_stack', 'metrics', 'needs_input', 'overall', 'provenance', 'ratings', 'registry_entries']
detected_stack: {"languages": ["js-ts"], "frameworks": [{"name": "express", "language": "js-ts"}]}
needs_input keys: ['gate_evaluations']
needs_input.reference: None
needs_input bytes: 586
overall: {"kind": "overall_rating", "value": 46, "contributor_count": 1, "total_dimension_count": 7, "contributors": ["test-strategy"], "contributor_values": [["test-str
exit=0
```

CLI, same repo (`easy-verifier score --repo <scratch>/node-express --scope project </dev/null`, exit 0):

```
cli keys: ['detected_stack', 'metrics', 'overall', 'provenance', 'ratings']
detected_stack: {'languages': ['js-ts'], 'frameworks': [{'name': 'express', 'language': 'js-ts'}]}
needs_input in stdout: False | "reference" in stdout: False
```

Container (`docker compose build` + MCP stdio into `docker compose run verifier`, repo bind-mounted
at `/workspace`, temp SOT mount, 13:09:31Z):

```
detected_stack: {"languages": ["js-ts"], "frameworks": [{"name": "express", "language": "js-ts"}]}
needs_input keys: ['gate_evaluations', 'reference']
reference requests: [('express', 'source_extensions'), ('express', 'test_name_patterns'), ('express', 'test_candidates'), ('express', 'test_declarations'), ('express', 'assertions'), ('express', 'branch_keywords'), ('express', 'comment_delimiters'), ('express', 'string_delimiters'), ('express', 'function_start'), ('express', 'import_syntax'), ('express', 'security_sinks'), ('express', 'interpolating_strings')]
reference bytes: 2887
exit=0
```

Real repo, MCP stdio, kitchd `--scope worktree` (13:07:58Z; request list elided):

```
payload keys: ['detected_stack', 'metrics', 'needs_input', 'overall', 'provenance', 'ratings']
detected_stack: {"languages": ["js-ts"], "frameworks": [{"name": "react", "language": "js-ts"}]}
needs_input keys: ['gate_evaluations', 'reference']
needs_input.reference: {
reference bytes: 2863
needs_input bytes: 5229
overall: {"kind": "overall_rating", "value": 56, "contributor_count": 5, "total_dimension_count": 7, "contributors": ["architecture", "code-quality", "security", "test-s
exit=0
```

Payload bytes (`needs_input.reference`, compact JSON, empty local layer): scratch express 2887;
kitchd (react) 2863; bryony (express) 2887; ai-training (python+django, 13 requests) 2984;
easy-verifier itself (python, 1 request: `python.interpolating_strings`) 903.

**DELTA**: Over MCP a caller now sees the detected stack (languages + manifest-detected frameworks)
and a capped, ordered list of exactly the registry fields the rules read that the stack lacks, with
fixed bounded-research instructions — and answering them via `registry_entries` closes the gate
and feeds the framework's fields into the rules; the CLI shows the stack but never the gate.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T037.jsonl`, never the
implementing agent alone]
