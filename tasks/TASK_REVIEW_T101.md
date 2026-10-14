# TASK_REVIEW — T101: One shared scoring container over loopback HTTP

> Sibling of `tasks/TASK_GUIDE_T101.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t101_shared_container.py` (33 tests; 17 red before the implementation; sabotage checks of host reset, lock and reports dir each fail tests; a negative control shows calls interleave without the lock). Supervisor rerun with t100 and t001: `83 passed in 12.41s` |
| Verification command run | ☑ pass | Agent: `2888 passed, 2 skipped in 434.22s`, exit 0. The 2 container tests that had been failing now pass after the image rebuild (AC7). ruff: All checks passed! |
| Negative cases hold | ☑ pass | A wrong Host header gets 421 and a wrong Origin gets 403 (FastMCP DNS-rebinding guard). LAN IPs are refused on 8766. `FASTMCP_HOST` cannot move the bind. An invalid `EASY_VERIFIER_PORT` exits 2. With `EASY_VERIFIER_REPORTS_DIR` unset, report behaviour is byte-identical; a relative value raises `ReportWriteError` |
| verify | ☑ pass | Agent AC6, real container: one `scorer` container (`net=host`, ro rootfs, caps dropped, UID 10001), listening on 127.0.0.1:8766 only. Two concurrent HTTP sessions scored fullstack-ts 56 (byte-identical to the host CLI after DDR-0005 normalisation) and k8s-ops 100; the report landed in the central dir and the repo was untouched; container-internal `/workspace` appears 0 times. Supervisor live probe 2026-10-14T11:29Z: streamable-http on 127.0.0.1:8799, 17 tools listed, `list_dimensions` ok, `ss` shows a loopback-only listener — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | code-review covered `mcp_server.py` (lock and worker thread, transport flag, host reassert, port parse), the `report.py` reports dir, `compose.yaml`, `Dockerfile`, the verify script, docs and tests. P0 0, P1 0, P2 0, P3 2: the report advisory still says 'inside the evaluated repository' when the central dir is used; the compose project name follows the checkout dir. security-review by hand (High risk): bind fixed to loopback and reasserted at run time; DNS-rebinding guard active; repos read-only; exposure to local processes documented (DDR-0013). The Dockerfile git wrapper (`-c safe.directory=*`) is **accepted**: `core/git.py` already forces `core.fsmonitor=false` and `core.hooksPath=/dev/null` and disables external diff and textconv, which neutralises the config-execution risk that safe.directory guards, and the wrapper exists only inside the container image. Pass |
| Full smoke suite still green (no regression) | ☑ pass | Full suite green, including the 2 previously failing container tests |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | No UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | No UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | No UI |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured by the implementing agent (common-infrastructure) on branch
`feat/T101-shared-container` at `2af7c41`, before any implementation commit. `easy-verifier-mcp` is
run as `PYTHONPATH=src <repo>/.venv/bin/python -m easy_verifier.adapters.mcp_server`.

```console
$ date -u
2026-10-14T10:55:04Z
$ git rev-parse --short HEAD
2af7c41
$ easy-verifier-mcp --help
usage: easy-verifier-mcp [-h] [--http]

options:
  -h, --help  show this help message and exit
  --http      opt in to legacy HTTP/SSE on 127.0.0.1; default is stdio
$ easy-verifier-mcp --transport streamable-http
usage: easy-verifier-mcp [-h] [--http]
easy-verifier-mcp: error: unrecognized arguments: --transport streamable-http
exit 2
$ docker compose config --services
verifier
$ grep -n network_mode compose.yaml
10:    network_mode: none
$ grep -n '"reports"' src/easy_verifier/core/report.py
75:REPORTS_DIRNAME = "reports"
```

```console
$ date -u
2026-10-14T10:59:13Z
$ EASY_VERIFIER_REPORTS_DIR=<scratchpad>/before/shared python -c "mcp write_report(repo=<scratchpad>/before/demo-repo)"
{"path": "reports/evidence-report-project-20261014T105914-185184Z.html"}
$ find <scratchpad>/before -name "*.html"
<scratchpad>/before/demo-repo/reports/evidence-report-project-20261014T105914-185184Z.html
```

So today: no streamable-HTTP transport, the only compose service is the per-session `verifier`
(`network_mode: none`), and `write_report` always writes into `<repo>/reports/` (the variable is
ignored).

**AFTER**: Supervisor 2026-10-14T11:29:36Z, `EASY_VERIFIER_PORT=8799 easy-verifier-mcp --transport streamable-http`, then an MCP streamable-HTTP client:

```
tools 17
list_dimensions isError False
LISTEN 0      2048       127.0.0.1:8799       0.0.0.0:*
```
Agent real container (AC6): one `scorer` container; two concurrent sessions gave fullstack-ts overall 56 and k8s-ops 100; the report was written under `$HOME/.easy-verifier-reports-t101/<repo>/`.

**DELTA**: The user starts one container once (`docker compose up -d scorer`) and points any repo at it with `claude mcp add --transport http easy-verifier http://127.0.0.1:8766/mcp`, instead of a new container per Claude session.

**WITNESS**: Supervisor (not the implementing agent), 2026-10-14T11:29Z: test rerun and live streamable-http probe; the agent ran the real-container evidence; the trace is in `memory/event-trace/T101.jsonl`.