# TASK_REVIEW — T036: Local registry layer, registry_entries agent input, replay parity, Docker mount

> Sibling of `tasks/TASK_GUIDE_T036.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE**: captured by backend-developer on commit `673a83a` (no implementation commit yet), 2026-09-28T07:51:23Z.
Fixture: a one-file Kotlin repo (`build.gradle.kts`, `src/test/kotlin/FooTest.kt` using `shouldBe`), an
empty temp SOT dir via `EASY_VERIFIER_SOT`, and an agent-input file carrying one `registry_entries` item.

```
$ cat agent.json
{"registry_entries": [{"language": "kotlin", "field": "assertions", "value": ["shouldBe"], "citation_url": "https://kotest.io/docs/assertions/assertions.html", "source_tag": "agent-researched"}]}
$ date -u +%Y-%m-%dT%H:%M:%SZ && git rev-parse --short HEAD
2026-09-28T07:51:23Z
673a83a
$ EASY_VERIFIER_SOT=$S/demo/sot PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli score --repo $S/demo/repo --scope worktree --agent-input $S/demo/agent.json </dev/null; echo "exit=$?"
validation error: agent input: 1 error(s): registry_entries: unknown key; only picks and gate_evaluations are accepted
exit=2
$ ls -A $S/demo/sot            # nothing written: no local layer exists
$ grep -rn "easy-verifier-sot\|EASY_VERIFIER_SOT" src | wc -l
0
```

**AFTER**: captured by backend-developer on commit `91f6dc8`, 2026-09-28T08:01:39Z. Same fixture repo;
each run uses its own temp `EASY_VERIFIER_SOT` (the real `~/.easy-verifier-sot/` is never touched).
`--scope project` is used because the fixture has no working-tree changes (worktree scope is empty).

```
--- 1. valid entry, empty SOT (machine A)
$ EASY_VERIFIER_SOT=$S/demo/sot PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli score --repo $S/demo/repo --scope project --agent-input $S/demo/agent.json </dev/null > A.json
exit=0
registry_entries: [{"language": "kotlin", "field": "assertions", "value": ["shouldBe"], "citation_url": "https://kotest.io/docs/assertions/assertions.html", "source_tag": "agent-researched (unreviewed)"}]
assertions_observed(test-strategy): [{'abstained': False, 'value': 1}] overall: 100
$ cat $S/demo/sot/kotlin.toml
# easy-verifier local reference registry entry (T036).

[[assertions]]
value = ["shouldBe"]
citation_url = "https://kotest.io/docs/assertions/assertions.html"
source_tag = "agent-researched (unreviewed)"
    (same repo, empty SOT, agent input {}: assertions_observed value 0, overall 46)
--- 2. invalid entries (http link + 3-wildcard token; '../etc' field)
validation error: agent input: 2 error(s): registry_entries[0]: value: 'a*b*c*d': at most 2 '*' wildcards in a token; registry_entries[1]: field '../etc': unknown field; known: manifests, source_extensions, test_name_patterns, test_candidates, test_declarations, assertions, branch_keywords, comment_delimiters, string_delimiters, function_start, import_syntax, security_sinks, interpolating_strings, roles.<role>
exit=2
ls: cannot access '.../demo/sotB': No such file or directory      (nothing written)
--- 3. replay A's embedded registry_entries on empty machine B
exit=0
A.json == B.json byte-equal            (cmp, no normalization applied)
--- 4. unwritable SOT (chmod 500)
registry_entries in payload: False  overall: 46   exit=0
warning [registry]: research cannot be saved: 1 registry entry not saved (the local layer directory is not writable); scoring used only the registry data already on this machine
$ git -C $S/demo/repo status --short     (empty: nothing written into the target repo)
```

**AFTER (per rule input tagging, Stage 4 P1 fix)**: backend-developer, commit `4891a3b`, 2026-09-28T08:09:01Z.
Same fixture, fresh temp SOT; test-strategy rating inputs from the real CLI payload:

```
$ EASY_VERIFIER_SOT=$S/demo/sot PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli score --repo $S/demo/repo --scope project --agent-input $S/demo/agent.json </dev/null > A.json
exit=0
{"metric_name": "assertion_density_per_test", "metric_value": 1.0, "source_tag": "agent-researched (unreviewed)", "registry_citations": [{"label": "kotlin.assertions", "url": "https://kotest.io/docs/assertions/assertions.html"}]}
{"metric_name": "test_config_and_ci_missing", "metric_value": 0, "source_tag": "curated"}
$ (replay A's registry_entries with EASY_VERIFIER_SOT=$S/demo/sotB, empty) > B.json
exit=0
A.json == B.json byte-equal
```

**DELTA**: an agent can now hand the verifier cited registry research (`registry_entries`); it is
validated, saved to the local layer, used in the same call with a visible `agent-researched (unreviewed)`
/ `user-supplied` tag and link, and embedded so replay on an empty machine gives byte-equal output.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T036.jsonl`, never the
implementing agent alone]
