# TASK_REVIEW — T032: [Short Title]

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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t032_vendor_sources.py` — 16 tests covering AC1 (script + filtered snapshot fields), AC2 (per-file source URL/version/commit/retrieval/licence/attribution), AC3 (AST scan of every file under `src/` for `socket`/`http.client`/`urllib.request`; no module under `src/` imports the script), AC4 (total-size budget, `--check` pass/tamper-fail sabotage test) |
| Verification command run | ☑ pass | `python -m pytest -q` → `828 passed, 2 skipped in 27.82s`. `python -m ruff check src tests scripts` → `All checks passed!`. `python scripts/vendor_sources.py --check` → `OK: 4 vendored file(s) match recorded checksums` |
| Negative cases hold | ☑ pass | Sabotage test `test_check_fails_on_tampered_snapshot` copies the vendored tree, corrupts `cwe.json`'s bytes, and confirms `--check` returns exit code 1; also manually verified interactively (appended a byte to `cwe.json`, ran `--check`, got `FAIL: ... checksum mismatch`, exit 1) before writing the test |
| verify | ☑ pass | `python scripts/vendor_sources.py` run live against the real network (Linguist raw GitHub commit `d0921d10bb68a1249fc9eac64e472759f36e2fd8`, OWASP ASVS tag `v5.0.0_release` flat JSON, MITRE CWE `cwec_v4.20.xml.zip`) — surface actually driven, not just unit-tested; produced 4 files, 423062 bytes (428 KB on disk), `--check` re-run and passed — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Touched only `scripts/vendor_sources.py` (new), `src/easy_verifier/registry/vendored/*` (new), `pyproject.toml` (one line, package-data), `tests/test_t032_vendor_sources.py` (new). No file under `Files Must NOT Touch` (`src/easy_verifier/core/*`) was edited |
| Full smoke suite still green (no regression) | ☑ pass | Full suite: 828 passed, 2 skipped (pre-existing skips, unrelated to T032) |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | pure backend/infra task, no UI component (guide's UI AC section already marked N/A) |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | same as above |
| **UI: Responsiveness at target viewports** | ☑ N/A | same as above |

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

**DELTA**: A maintainer can run `python scripts/vendor_sources.py` to pull pinned, filtered
snapshots of Linguist/ASVS/CWE into the package (428 KB, under the 500 KB target), and CI or any
offline environment can run `--check` to confirm the committed snapshots still match their recorded
checksums with zero network access — neither existed before this task.

**WITNESS**: common-infrastructure agent, T032 worktree, 2026-09-28.
