# TASK_REVIEW — T031: Metrics read test naming, declarations and assertions from the registry

> Sibling of `tasks/TASK_GUIDE_T031.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t031_metrics_registry.py` — 114 tests: Kotlin/PHP/Go/RSpec/C# fixture ACs; former-table oracle parity for Python/JS/Java/Rust classification + assertion counts (metrics and test_strategy, 39 paths); registry-copy sabotage (Kotlin candidates removed → uncovered); token compiler cannot inject regex; framework merge add-only; source-read cap pair (cap 4 → none read + warning, cap 5 → both read). `tests/test_metrics.py` harness-only change (Supervisor ruling (a)). Supervisor re-run: `926 passed, 2 skipped in 25.13s` |
| Verification command run | ☑ pass | Supervisor 2026-09-28 05:43 UTC: pytest `926 passed, 2 skipped` (exit 0); `ruff check src tests` → `All checks passed!` (exit 0) |
| Negative cases hold | ☑ pass | Uncovered source counted as 1 (not 0 by construction); source reads all-or-none against `MAX_TEST_SOURCES` with `UNREAD_SOURCES_WARNING`; malformed registry metric values rejected at intake; token compiler escapes everything except `*`, `?`, `<A-Z>`, space |
| verify | ☑ pass | Real CLI 05:43 UTC, fresh Kotlin repo (`build.gradle.kts`, `src/main/kotlin/Foo.kt`, `src/test/kotlin/FooTest.kt`): `cli score --scope project` test-strategy → `source_files_without_covering_test` 0 (Foo.kt), `test_to_source_ratio` 1.0, `assertions_observed` 1 (FooTest.kt) — abstained before T031 per BEFORE/agent CLI table; Go repo same result in agent's AFTER — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed `core/metrics.py` (tables removed, `compute_metrics(pack, tables)`, public `expected_test_names`), new `core/metric_tables.py`, `core/registry.py` (5 new ENTRY_FIELDS), `core/score.py`, `dimensions/test_strategy.py`, 9 curated TOML. Code review round 1: P1 — `dimensions/test_strategy.py` kept a second copy of test-name/source tables (FR-041) and never read sources, so the fix was invisible at the real surface → fixed in d6ad17c (shared compiled tables; sources read after test evidence, no excerpt, capped). Rulings: signature change accepted; Rust `?*_test.rs` kept for parity; `_MANIFEST_NAMES` left hard-coded (boundary regression risk); wider test-strategy `files_read` accepted (G1: no score backward-compat). Residual: test_strategy vs metrics `_is_test_file` algorithms still differ (T019 residue; tables now shared). Security inline (Med): source reads go through `context.read_source` (secret-bearing guard intact), no excerpt → redaction/budget unaffected |
| Full smoke suite still green (no regression) | ☑ pass | full suite 926 passed, 2 skipped |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend task, no UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Pure backend task, no UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | Pure backend task, no UI |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured by backend-developer on the pre-implementation commit (`ee5b2ac`), driving
`core.metrics.compute_metrics` over hand-built packs per language
(script: one pack per fixture, printing three test-strength metrics):

```text
$ date -u; git rev-parse --short HEAD; PYTHONPATH=src python demo_t031.py
2026-09-28T05:26:14Z
ee5b2ac
Kotlin Foo.kt + src/test/kotlin/FooTest.kt: {'source_files_without_covering_test': 1, 'assertions_observed': 1, 'assertion_density_per_test': 1.0}
PHP src/Foo.php + tests/FooTest.php: {'source_files_without_covering_test': 1, 'assertions_observed': 1, 'assertion_density_per_test': 'ABSTAINED'}
Go calc.go + calc_test.go (t.Errorf): {'source_files_without_covering_test': 0, 'assertions_observed': 0, 'assertion_density_per_test': 0.0}
RSpec spec/calc_spec.rb (it "x" do): {'source_files_without_covering_test': 0, 'assertions_observed': 1, 'assertion_density_per_test': 'ABSTAINED'}
C# tests/CalcTests.cs ([Fact]): {'source_files_without_covering_test': 0, 'assertions_observed': 1, 'assertion_density_per_test': 'ABSTAINED'}
exit=0
```

Gaps visible above: Kotlin `Foo.kt` reported uncovered (1) although `src/test/kotlin/FooTest.kt`
exists; PHP `src/Foo.php` uncovered (1) and `public function testAdds` not a declaration
(density abstains); Go `t.Errorf` counts 0 assertions (density 0.0); RSpec `it "adds" do` and
C# `[Fact]` are not test declarations (density abstains).

**AFTER**: captured by backend-developer (implementer; reviewer to re-run), same script, T031 changes
applied (commit follows this capture):

```text
$ date -u; git rev-parse --short HEAD; PYTHONPATH=src python demo_t031.py
2026-09-28T05:35:02Z
2ca23cb + T031 working tree
Kotlin Foo.kt + src/test/kotlin/FooTest.kt: {'source_files_without_covering_test': 0, 'assertions_observed': 1, 'assertion_density_per_test': 1.0}
PHP src/Foo.php + tests/FooTest.php: {'source_files_without_covering_test': 0, 'assertions_observed': 1, 'assertion_density_per_test': 1.0}
Go calc.go + calc_test.go (t.Errorf): {'source_files_without_covering_test': 0, 'assertions_observed': 1, 'assertion_density_per_test': 1.0}
RSpec spec/calc_spec.rb (it "x" do): {'source_files_without_covering_test': 0, 'assertions_observed': 1, 'assertion_density_per_test': 1.0}
C# tests/CalcTests.cs ([Fact]): {'source_files_without_covering_test': 0, 'assertions_observed': 1, 'assertion_density_per_test': 1.0}
exit=0
```

Real surface (CLI `score --scope project`) on a scratch repo with `go.mod`, `calc.go`, `calc_test.go`
(`t.Errorf`), `Foo.kt`, `src/test/kotlin/FooTest.kt` (`assertEquals`), 2026-09-28T05:32:47Z,
test-strategy dimension:

```text
--- AFTER (2ca23cb + T031 changes)
exit=0
source_files_without_covering_test = ABSTAINED
assertion_density_per_test = 1.0
assertions_observed = 2
--- BEFORE (2ca23cb, T031 changes stashed)
exit=0
source_files_without_covering_test = ABSTAINED
assertion_density_per_test = 0.5
assertions_observed = 1
```

The correspondence metric abstains at the CLI both before and after because the test-strategy
pack never reads `calc.go` / `Foo.kt` (`source_file_share` 0 of 4 files read) — evidence selection
in `dimensions/test_strategy.py`, outside T031; the correspondence fix is proven on hand-built packs.

**AFTER — Stage 4 P1 fix** (`dimensions/test_strategy.py` now classifies and ranks with the same
registry `LanguageTables`, and reads the scope's source files after the test evidence, without an
excerpt, all-or-none within `MAX_TEST_SOURCES`). Real CLI, scratch repos per the review:
Kotlin = `build.gradle.kts` + `src/main/kotlin/Foo.kt` + `src/test/kotlin/FooTest.kt`;
Go = `go.mod` + `calc.go` + `calc_test.go` (`t.Errorf`). Test-strategy metrics shown; `source_file_share`'s
`computed_from` is the deduplicated `files_read` of the test-strategy pack.

```text
=== BEFORE: e2daf07 (branch HEAD), 2026-09-28T05:40:23Z
$ python -m easy_verifier.adapters.cli score --repo <ktrepo> --scope project
  exit=0
  source_files_without_covering_test = ABSTAINED  computed_from=[]
  assertions_observed = 1  computed_from=['src/test/kotlin/FooTest.kt:1-4']
  source_file_share = 0.0  computed_from=['build.gradle.kts', 'src/test/kotlin/FooTest.kt']
$ python -m easy_verifier.adapters.cli score --repo <gorepo2> --scope project
  exit=0
  source_files_without_covering_test = ABSTAINED  computed_from=[]
  assertions_observed = 1  computed_from=['calc_test.go:1-9']
  source_file_share = 0.0  computed_from=['calc_test.go', 'go.mod']
=== AFTER: e2daf07 + P1 fix, 2026-09-28T05:40:24Z
$ python -m easy_verifier.adapters.cli score --repo <ktrepo> --scope project
  exit=0
  source_files_without_covering_test = 0  computed_from=['src/main/kotlin/Foo.kt']
  assertions_observed = 1  computed_from=['src/test/kotlin/FooTest.kt:1-4']
  source_file_share = 0.3333333333333333  computed_from=['build.gradle.kts', 'src/main/kotlin/Foo.kt', 'src/test/kotlin/FooTest.kt']
$ python -m easy_verifier.adapters.cli score --repo <gorepo2> --scope project
  exit=0
  source_files_without_covering_test = 0  computed_from=['calc.go']
  assertions_observed = 1  computed_from=['calc_test.go:1-9']
  source_file_share = 0.3333333333333333  computed_from=['calc.go', 'calc_test.go', 'go.mod']
```

BEFORE = branch HEAD `e2daf07` with the fix stashed; AFTER = the same tree with the fix applied
(committed right after this capture). The earlier abstention note above is superseded by this block.

**DELTA**: Kotlin, PHP, Go (t.Errorf), RSpec and C# test suites are now recognised and measured, from one cited registry shared by metrics and the test-strategy dimension.
and PHPUnit `public function test*` declarations now count, and Kotlin/PHP sources are matched to
their `FooTest` files — all from cited registry data rather than code tables.

**WITNESS**: Supervisor re-ran suite, ruff and the real CLI on a fresh Kotlin repo on 2026-09-28 (05:43 UTC), independent of the implementing agent.