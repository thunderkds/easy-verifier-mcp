# Running easy-verifier directly as an MCP server

This is the no-container path. You install the package on the host, and your MCP client
starts `easy-verifier-mcp` on demand, talking to it over **stdio**. You do not keep a server
running, and no port is opened. For the hardened, read-only container, see
[`DOCKER_MCP_GUIDE.md`](DOCKER_MCP_GUIDE.md).

## 1. Install

Into a Python 3.11+ environment, from this repository:

```console
python -m pip install .
```

That installs two console entry points: `easy-verifier` (CLI) and `easy-verifier-mcp` (MCP
server). Find the server's absolute path, because GUI clients often don't inherit your shell's
`PATH`:

```console
which easy-verifier-mcp
```

## 2. Register the server with your MCP client

### Claude Code

```console
claude mcp add easy-verifier -- easy-verifier-mcp
```

Put `--scope project` before `--` (`claude mcp add --scope project easy-verifier -- ...`) to write it
to a shared `.mcp.json` instead of your local config.

### JSON-configured clients (Claude Desktop, Cursor, `.mcp.json`, …)

```json
{
  "mcpServers": {
    "easy-verifier": {
      "command": "/absolute/path/to/venv/bin/easy-verifier-mcp",
      "args": []
    }
  }
}
```

Use the path printed by `which easy-verifier-mcp` in step 1.

## 3. Point it at a repository

Every tool takes a `repo` argument, and it defaults to `.`, the server's working directory.
Claude Code starts the server in your project directory, so the default usually works. Other
clients may start it somewhere else. There, pass `repo` as an **absolute path** in the tool call.
Reports are written to `<repo>/reports/`, which must be writable by your user.

## Source roles and agent input

Each dimension seeks **source roles**, such as `lockfile`, `requirements-doc`, or `test-file`,
filled by language-agnostic patterns and extended by Python, JS/TS, Rust, and Java pattern sets.
`list_dimensions` returns every role with its patterns. The target repository may add globs to
existing roles in an optional `.easy-verifier.toml` (`[roles] requirements-doc = ["docs/specs/*.md"]`).
It cannot remove roles or change floors.

The `score` and `write_report` tools accept an optional `agent_input` argument,
`{"picks": {"<role>": ["<repo-relative path>", ...]}}`, to add files a role's patterns missed. The
CLI replays the same document with `--agent-input PATH`, and both adapters return identical output
for it. Every `score` result carries a per-dimension `provenance` entry: `sources` (`rules`,
`rules + config`, `rules + agent picks (N files)`) and `rating` (`rules`, `blended (w …)`,
`agent-rated`, `abstained`).

A `score` response may carry `needs_input`. `needs_input.picks` asks for files, and
`needs_input.gate_evaluations` names the dimensions whose rules abstained or sit within ±10% of a
threshold, with the evidence refs to read. To answer, call `score` again with the same
`agent_input` plus `"gate_evaluations": {"<dimension>": {"score": 0-100, "confidence": 0-1,
"evidence_refs": ["<ref>"]}}`. Each answer blends in with `w = 0.5 × confidence`, or stands alone
as `agent-rated` where the rules abstained. The result is always shown with its parts, for example
`74 = rules 68 + agent 88 (w 0.30)`. A call that carries `gate_evaluations` asks nothing further.

## 4. Check the connection

- Claude Code: `claude mcp list`, or `/mcp` inside a session.
- Other clients: the server should report as `easy-verifier` with 11 tools: the seven dimensions,
  `list_dimensions`, `combined`, `score`, and `write_report`.
- By hand: `easy-verifier-mcp` with no arguments waits silently on stdin. That is correct, since
  stdout is reserved for the protocol. Press Ctrl-C to exit.

## HTTP/SSE (opt-in, loopback only)

stdio is the default and recommended transport. For clients that can only reach a URL, there is a
legacy opt-in:

```console
easy-verifier-mcp --http
```

It binds to `127.0.0.1` only, never to a routable address.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `command not found: easy-verifier-mcp` in the client | The client doesn't see your venv. Use the absolute path from `which easy-verifier-mcp`. |
| Tools evaluate the wrong directory | The client started the server elsewhere. Pass `repo` as an absolute path. |
| Stray text breaks the client's connection | Something printed to stdout. Only the protocol may use it. Check any wrapper script you added. |
