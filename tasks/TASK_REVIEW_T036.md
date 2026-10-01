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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t036_local_registry.py` — 30 tests (intake validation incl. http URL, `../` field/name, wildcard/globstar caps, secret-bearing values; symlinked SOT/entry refusal; SOT inside target refused; atomic temp-file swap; curated-wins value-by-value; cache refresh; replay byte-parity on empty SOT; unwritable → curated-only with note; per-input tag via field→metric map; least-reviewed tag wins; absent language doesn't tag; judge rejects tag/citation mismatch; report shows registry-data link). 11 + 4 sabotage breaks each caught. `test_package_never_reads_the_environment` narrowed to the single approved `EASY_VERIFIER_SOT` read (Supervisor ruling). Supervisor re-run `1157 passed, 2 skipped in 60.64s` |
| Verification command run | ☑ pass | Supervisor 2026-09-28: pytest `1157 passed, 2 skipped` (exit 0); `ruff check src tests` → `All checks passed!` (exit 0); `docker compose build && bash scripts/verify_container.sh` → `PASS: uid=10001, tools=11, root=read-only, reports=writable, network=none, ports=none, caps=none` (exit 0) |
| Negative cases hold | ☑ pass | Supervisor adversarial CLI probes (`--agent-input`, `</dev/null`): http citation → exit 2 'must be an https:// link'; language `../../etc` → exit 2; glob `/etc/passwd` → exit 2 'repository-relative glob'; spoofed `source_tag: curated` → exit 2; regex-shaped `(a+)+$` accepted only as an escaped literal token (no ReDoS, exit 0); symlinked SOT dir (→ /tmp) → refused, 'research cannot be saved', nothing written to /tmp |
| verify | ☑ pass | Real CLI (agent AFTER at 4891a3b, 08:09Z): Kotlin `assertions` entry → `assertion_density_per_test` input `source_tag: agent-researched (unreviewed)` + `registry_citations` kotest link; unrelated `test_config_and_ci_missing` stays `curated`; replay on empty SOT byte-equal (cmp); invalid entries exit 2 with reasons; target `git status` clean. Supervisor Docker verify pass — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed `core/registry.py` (local layer, intake validation, atomic writes, symlink/inside-repo refusal, LOCAL_TAGS), `core/roles.py`, `core/metric_tables.py` (FIELD_METRICS/ROLE_METRICS, cache keyed on registry object), `core/score.py`, `core/synthesis.py`, `core/judge.py` (input-level tag validation), `core/report.py`, adapters, compose.yaml, Docker guide, conftest. Round 1 P1: tags only once per run → fixed with per-input field→metric provenance (FR-048). Rulings: single env read exemption (PROJECT_SPEC constraint 5 reworded by Supervisor, commit on llm-integration); curated-wins value-by-value. Security review inline (High): intake fully validated + probed; P2 accepted: TOCTOU on final symlink check (same-user), calls without agent input don't reload registry, tagging by language may over-flag (never hides), Docker host dir created root-owned needs chown (documented) |
| Full smoke suite still green (no regression) | ☑ pass | full suite 1157 passed, 2 skipped |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend task, no UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Pure backend task, no UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | Pure backend task, no UI |

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

**DELTA**: The calling LLM can submit cited registry entries that are validated, saved once to `~/.easy-verifier-sot/`, reused across repos, flagged on every score input that depends on them, and replayed byte-equal anywhere.
validated, saved to the local layer, used in the same call with a visible `agent-researched (unreviewed)`
/ `user-supplied` tag and link, and embedded so replay on an empty machine gives byte-equal output.

**WITNESS**: Supervisor re-ran suite, ruff, adversarial intake probes and the Docker container verification on 2026-09-28, independent of the implementing agent.