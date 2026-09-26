# TASK_REVIEW — T024: MCP client setup guides (Docker + direct)

## Status

**Complete.** Docs-only; no `src/`, `Dockerfile`, `compose.yaml`, or `scripts/` change.

## Evidence

| Check | Result | Evidence |
|---|---|---|
| New test(s) cover acceptance criteria | pass | `PYTHONPATH=src python -m pytest tests/test_t024_mcp_guides.py -q` -> `8 passed` (ACs 1–4, 6) |
| Test can fail (sabotage probe) | pass | Each mutation, restored afterwards: drop `--network none` from JSON config -> `1 failed, 5 passed`; `-i` -> `-it` -> `1 failed, 5 passed`; drop `:ro` from target mount -> `1 failed, 5 passed`; remove README link -> `1 failed, 5 passed`; restored -> `6 passed`. Local guide (after scope extension): `-- easy-verifier-mcp` -> `-- easy-verifier` -> `1 failed, 7 passed`; `--http` -> `--sse` -> `1 failed, 7 passed`; remove README link to LOCAL guide -> `1 failed, 7 passed`; restored -> `8 passed` |
| Live MCP handshake, documented `docker run` (AC 5) | pass | `initialize` + `tools/list` piped into the exact guide command against `easy-verifier-mcp:0.1.0` -> `server: {'name': 'easy-verifier', 'version': '1.29.1'}`, `tools: ['architecture', 'blast-radius', 'code-quality', 'requirement-fidelity', 'security', 'solution-fit', 'test-strategy', 'list_dimensions', 'combined', 'score', 'write_report']` (11) |
| Live MCP handshake, documented Compose variant | pass | `docker compose -f <abs>/compose.yaml run --rm --no-tty verifier` with `EASY_VERIFIER_REPO`/`EASY_VERIFIER_REPORTS` -> `{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-06-18",...` |
| Live MCP handshake, host-direct | pass | `initialize` + `tools/call list_dimensions` piped into `python -m easy_verifier.adapters.mcp_server` from an unrelated cwd -> `{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-06-18",...` and `id:2` returned the `architecture` dimension entry |
| README doc-truth regression | pass | `tests/test_t018_readme.py` still passes alongside T024 (`14 passed, 1 skipped` after trimming README §MCP/§Docker (net −29 lines)) |
| Full regression | pass | `PYTHONPATH=src python -m pytest -q --tb=short` -> `596 passed, 2 skipped, 1 warning in 26.93s` |
| Ruff | pass | `ruff check src tests` -> `All checks passed!`; `ruff format --check` on new test -> unchanged |
| security-review | N/A | Low risk, docs + test only; no new runtime primitive |
| UI: visual regression | ☐ N/A | No UI component |
| UI: design-system compliance | ☐ N/A | No UI component |
| UI: responsiveness | ☐ N/A | No UI component |

## Residue

- `claude mcp add` itself was not executed. Running it would change the user's Claude Code config.
  Its argument list after `--` is the same token list the live probe ran.
