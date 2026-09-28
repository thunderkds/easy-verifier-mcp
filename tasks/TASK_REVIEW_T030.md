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

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T030.jsonl`, never the
implementing agent alone]
