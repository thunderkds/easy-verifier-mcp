# TASK_REVIEW — T032: Build-time vendoring of Linguist, OWASP ASVS and MITRE CWE (version-pinned)

> Sibling of `tasks/TASK_GUIDE_T032.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t032_vendor_sources.py` — checksum/`--check` tests incl. tampered-snapshot sabotage (exit 1), AST no-network-import scan of `src/`, no `src/` reference to the script, and 14 `TestValidatorsFailLoudlyOnFormatDrift` tests (degraded Linguist/ASVS/CWE inputs raise `UpstreamFormatError` before any write). Supervisor re-run: `840 passed, 2 skipped in 25.86s` |
| Verification command run | ☑ pass | Supervisor 2026-09-28 05:31 UTC: pytest `840 passed, 2 skipped` (exit 0); `ruff check src tests scripts` → `All checks passed!` (exit 0); `python scripts/vendor_sources.py --check` → `OK: 4 vendored file(s) match recorded checksums` (exit 0) |
| Negative cases hold | ☑ pass | Tampered snapshot → `--check` exit 1 naming the file; degraded upstream (≤10 ASVS items, CWE missing 89, reformatted languages.yml) → `UpstreamFormatError`; `grep` for socket/urllib.request/http.client imports under `src/` → none |
| verify | ☑ pass | Maintainer surface driven by Supervisor: `--check` pass; vendored content spot-checked — Linguist commit d0921d10 (830 langs; Kotlin .kt/.kts, C++ .cpp, Swift, Dart, Elixir, Scala present), ASVS v5.0.0_release (345 reqs, CC-BY-SA-4.0 meta), CWE 4.20 (78/89/95/798 with per-id URLs); total 423,062 bytes < 500 KB — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed `scripts/vendor_sources.py`, `registry/vendored/*` (meta/licence/NOTICE/checksums), pyproject package data, new tests. Code review: P1 1 fixed in round 2 (Linguist parser degraded quietly on upstream format drift; guide requires fail-loud → validators added, commit 7f8146b). P3 noted: ASVS export has no per-requirement anchors, so every requirement shares one canonical URL — T035 cites ASVS by requirement id + that URL. Security N/A (Low risk); no runtime network confirmed |
| Full smoke suite still green (no regression) | ☑ pass | full suite 840 passed, 2 skipped |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend task, no UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Pure backend task, no UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | Pure backend task, no UI |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: (captured 2026-09-28T05:19:06Z, in worktree `easy-verifier-mcp-T032`, before any T032
implementation commit)

```
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-09-28T05:19:06Z
$ ls scripts/vendor_sources.py
ls: cannot access 'scripts/vendor_sources.py': No such file or directory
$ ls src/easy_verifier/registry/vendored
ls: cannot access 'src/easy_verifier/registry/vendored': No such file or directory
$ python3 -c "import scripts.vendor_sources"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'scripts.vendor_sources'
```

**AFTER**: (captured 2026-09-28T05:25:54Z, same worktree, after implementation)

```
$ ls scripts/vendor_sources.py
scripts/vendor_sources.py
$ ls src/easy_verifier/registry/vendored/
asvs.json  CHECKSUMS.sha256  cwe.json  linguist.json  NOTICE
$ du -sh src/easy_verifier/registry/vendored/
428K    src/easy_verifier/registry/vendored/
$ python scripts/vendor_sources.py --check
OK: 4 vendored file(s) match recorded checksums
```

**DELTA**: Linguist, OWASP ASVS and MITRE CWE are available offline inside the package as pinned, licensed snapshots, refreshable by one maintainer script that refuses to write drifted data.
snapshots of Linguist/ASVS/CWE into the package (428 KB, under the 500 KB target), and CI or any
offline environment can run `--check` to confirm the committed snapshots still match their recorded
checksums with zero network access — neither existed before this task.

**WITNESS**: Supervisor re-ran suite, ruff, `--check`, the network-import grep and content spot-checks on 2026-09-28 (05:31 UTC), independent of the implementing agent.