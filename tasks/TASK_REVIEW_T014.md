# TASK_REVIEW — T014: FastMCP adapter

## Evidence

| Check | Result | Notes / output snippet |
|-------|--------|------------------------|
| Acceptance tests | pass | `PYTHONPATH=src python -m pytest tests/test_t014_mcp_server.py -q` -> `9 passed` |
| Full regression suite | pass | `PYTHONPATH=src python -m pytest -q` -> `427 passed` |
| Lint and formatting | pass | `ruff check src tests` and `ruff format --check src tests` both pass |
| Tool surface | pass | Seven descriptor-derived dimension tools plus `list_dimensions`, `combined`, and `write_report` |
| Transport boundary | pass | No-argument startup selects stdio; `--http` is the only HTTP/SSE opt-in; host is hard-wired to `127.0.0.1` |
| Thin-adapter review | pass | No target file reads, rendering, outbound client, or evaluation logic in the adapter |

The tests ran with the locally available `mcp` 1.29.0 SDK. Its emitted
`IncompleteFieldDefinitionWarning` is upstream and does not fail the suite.

## Demonstration

**BEFORE** (captured 2026-09-02T04:19:29Z at the T011 base):

```text
$ pytest tests/test_t014_mcp_server.py -q
ERROR: file or directory not found: tests/test_t014_mcp_server.py
no tests ran
```

**AFTER**:

```text
$ PYTHONPATH=src python -m pytest tests/test_t014_mcp_server.py -q
.........                                                                [100%]
9 passed, 1 warning in 1.26s
```

**DELTA**: the shared evidence and report core is now exposed as exactly ten
structured MCP tools. Stdio remains the default; the optional legacy SSE path is
loopback-only and cannot inherit a routable host from the environment.

## Review notes

- The initial implementation read an adapter-specific environment variable for
  HTTP opt-in. Full-suite review caught that this violated the package-wide rule
  that application code never reads environment variables. The opt-in is now the
  explicit `--http` flag only.
- A live subprocess handshake could not be completed in this restricted runner:
  the borrowed SDK environment also hangs on `initialize` for an independent
  five-line FastMCP sample. In-process SDK calls, registration, structured tool
  errors, default transport selection, and clean stdout are covered and passing.
- The self-review and security review were performed directly because the Claude
  `code-review`, `security-review`, and `verify` skills are not available to this
  Codex session. No routable bind address, network client, target file access, or
  stdout logging path was found.
