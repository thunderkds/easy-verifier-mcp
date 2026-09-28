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

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T031.jsonl`, never the
implementing agent alone]
