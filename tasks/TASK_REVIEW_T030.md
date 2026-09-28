# TASK_REVIEW — T030: Registry schema, loader, curated 9 languages

> Sibling of `tasks/TASK_GUIDE_T030.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t030_registry.py` — 54 tests: AC1 9 curated files, every field `{value, https citation_url, source_tag=curated}`; AC2 bad field/URL/tag/key/size/encoding/TOML rejected per entry with warning, never a crash; AC3 verbatim snapshot of removed ECOSYSTEM_PATTERNS equals registry + mixed-repo resolution parity; AC4 Go/Kotlin/C#/Ruby/PHP fixtures fill roles (withheld-entry control); AC5 add-only deterministic framework merge. 7 sabotage breakages each turned suite red. Two structural T026 tests repointed from the removed symbol to the registry (Supervisor ruling: AC3 intent = behaviour preserved; all behavioural fixture tests untouched) |
| Verification command run | ☑ pass | Supervisor 2026-09-28: `python -m pytest -q` → `812 passed, 2 skipped in 24.58s` (exit 0); `python -m ruff check src tests` → `All checks passed!` (exit 0) |
| Negative cases hold | ☑ pass | Field without citation_url, http:// URL, wrong tag, unknown role, `..`/absolute value, empty/oversized/non-UTF-8/bad-TOML file each rejected with a named warning (tests); case-sensitive globs preserved (`latest.json`, `Detekt.YML`) |
| verify | ☑ pass | Real CLI surface 2026-09-28 05:16 UTC on a fresh Go repo (`go.mod`, `.golangci.yml`, `a.go`): `cli code-quality --scope project` → files_read `['.golangci.yml']` (lint-config filled via registry go.toml; unfilled before T030 per BEFORE capture) — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed `core/registry.py` (new, loader + lookups), `core/roles.py` (table removed, `_registry()` lru_cache once per process), 9 curated TOML, pyproject package data, 2 repointed T026 tests. Code review: P0 0, P1 0; P2 carried to T036: (a) `_registry()` is cached per process — local-layer writes must invalidate it or a long-running MCP server won't see new entries; (b) loader accepts only `curated` tag and lacks glob-shape limits — T036 must widen tag and add `.easy-verifier.toml`-style glob limits before accepting user files. P3: PROJECT_SPEC glossary 'Ecosystem pattern set' stale (fixed by Supervisor). Citation URLs are official docs roots/pages, not fetched (no network) — spot-check list in agent report. Security inline (Med): no network, no target writes, warnings pass through redact |
| Full smoke suite still green (no regression) | ☑ pass | full suite 812 passed, 2 skipped |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend task, no UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Pure backend task, no UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | Pure backend task, no UI |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured by backend-developer on `feat/T030-registry-core` at `b4b81ba`, before any implementation commit. The demo script builds Go, Kotlin and C# fixture repos in a temp dir (Go: `go.mod`, `.golangci.yml`; Kotlin: `build.gradle.kts`, `detekt.yml`; C#: `App/App.csproj`, `stylecop.json`, `tests.runsettings`) and resolves every role with `core.roles.resolve`. None of the three fills `lint-config`, Go and C# also leave `test-config` unfilled, no Go/Kotlin/C# ecosystem activates (Kotlin fills test-config only because the Java table claims `build.gradle.kts`), `core/roles.py` still holds the hard-coded `ECOSYSTEM_PATTERNS` table, and no registry exists.

```text
$ date -u; git rev-parse --short HEAD
2026-09-28T05:07:34Z
b4b81ba
$ PYTHONPATH=src python demo.py
[go] ecosystems=()
  package-manifest  FILLED ('go.mod',)
  lint-config       UNFILLED
  test-config       UNFILLED
[kotlin] ecosystems=('java',)
  package-manifest  FILLED ('build.gradle.kts',)
  lint-config       UNFILLED
  test-config       FILLED ('build.gradle.kts',)
[csharp] ecosystems=()
  package-manifest  FILLED ('App/App.csproj',)
  lint-config       UNFILLED
  test-config       UNFILLED
$ grep -n 'ECOSYSTEM_PATTERNS: dict\|"manifests":' src/easy_verifier/core/roles.py
213:ECOSYSTEM_PATTERNS: dict[str, dict] = {
215:        "manifests": (
250:        "manifests": ("package.json",),
278:        "manifests": ("Cargo.toml",),
287:        "manifests": ("pom.xml", "build.gradle", "build.gradle.kts"),
$ ls src/easy_verifier/registry
ls: cannot access 'src/easy_verifier/registry': No such file or directory
```

**AFTER**: captured by Supervisor on `0cf1d2a` (fresh Go repo: `go.mod`, `.golangci.yml`, `a.go`):

```
$ date -u && PYTHONPATH=src python -m easy_verifier.adapters.cli code-quality --repo <gorepo> --scope project
Mon Sep 28 05:16:39 AM UTC 2026
files_read: ['.golangci.yml']
coverage: 0.3333333333333333
missing: contributing-guide, format-config
```
Implementing agent's AFTER run (05:14:03Z): Go fills `go.mod` / `.golangci.yml` / `go.mod`; Kotlin fills `build.gradle.kts` / `detekt.yml` / `build.gradle.kts`; C# fills `App/App.csproj` / `stylecop.json` / `tests.runsettings`; `ECOSYSTEM_PATTERNS` absent from `core/roles.py`.

**DELTA**: Go, Kotlin, C#, Ruby and PHP repos now fill manifest/lint/test roles from one cited registry, and every language pattern carries an https citation and a `curated` source tag.

**WITNESS**: Supervisor re-ran suite, ruff and the CLI on a fresh Go repo on 2026-09-28 (05:16 UTC), independent of the implementing agent.