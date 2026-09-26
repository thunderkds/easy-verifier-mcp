# Running the Docker container as an MCP server

easy-verifier speaks MCP over **stdio**. You do not start the container yourself and leave it
running: your MCP client launches `docker run -i` on demand, talks to it through stdin/stdout, and
the container exits (`--rm`) when the session ends. No port is published and the container has no
network.

## 1. Build the image (once)

From this repository:

```console
docker compose build
```

This produces the image `easy-verifier-mcp:0.1.0`.

## 2. Prepare the target repository

The repository you want to evaluate is mounted **read-only**. Only its `reports/` directory is
writable, and it must be owned by the container's fixed non-root UID/GID `10001`:

```console
mkdir -p /path/to/repo/reports
sudo chown 10001:10001 /path/to/repo/reports
```

Use absolute host paths everywhere below — MCP clients do not expand `~` or relative paths.

## 3. Register the server with your MCP client

The command every client runs is the same. Its flags mirror the hardening in `compose.yaml`:

```console
docker run -i --rm \
  --read-only --network none --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=16m \
  -v /path/to/repo:/workspace:ro \
  -v /path/to/repo/reports:/workspace/reports \
  easy-verifier-mcp:0.1.0
```

### Claude Code

```console
claude mcp add easy-verifier -- docker run -i --rm \
  --read-only --network none --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=16m \
  -v /path/to/repo:/workspace:ro \
  -v /path/to/repo/reports:/workspace/reports \
  easy-verifier-mcp:0.1.0
```

Put `--scope project` before `--` (`claude mcp add --scope project easy-verifier -- ...`) to write it
to a shared `.mcp.json` instead of your local config.

### JSON-configured clients (Claude Desktop, Cursor, `.mcp.json`, …)

```json
{
  "mcpServers": {
    "easy-verifier": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "--read-only", "--network", "none", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges:true",
        "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=16m",
        "-v", "/path/to/repo:/workspace:ro",
        "-v", "/path/to/repo/reports:/workspace/reports",
        "easy-verifier-mcp:0.1.0"
      ]
    }
  }
}
```

### Alternative: let Compose supply the flags

If you prefer to keep the hardening in one place, point the client at `compose.yaml` and pass the
paths through the environment:

```json
{
  "mcpServers": {
    "easy-verifier": {
      "command": "docker",
      "args": [
        "compose", "-f", "/path/to/easy-verifier-mcp/compose.yaml",
        "run", "--rm", "--no-tty", "verifier"
      ],
      "env": {
        "EASY_VERIFIER_REPO": "/path/to/repo",
        "EASY_VERIFIER_REPORTS": "/path/to/repo/reports"
      }
    }
  }
}
```

## Source roles and agent input

Each dimension seeks **source roles**, such as `lockfile`, `requirements-doc`, or `test-file`,
filled by language-agnostic patterns and extended by Python, JS/TS, Rust, and Java pattern sets.
`list_dimensions` returns every role with its patterns. The target repository may add globs to
existing roles in an optional `.easy-verifier.toml` (`[roles] requirements-doc = ["docs/specs/*.md"]`).
It cannot remove roles or change floors.

The `score` and `write_report` tools accept an optional `agent_input` argument,
`{"picks": {"<role>": ["<path relative to /workspace>", ...]}}`, to add files a role's patterns missed. The
CLI replays the same document with `--agent-input PATH`, and both adapters return identical output
for it. Every `score` result carries a per-dimension `provenance` entry (`rules`,
`rules + config`, `rules + agent picks (N files)`).

## 4. Check the connection

- Claude Code: `claude mcp list`, or `/mcp` inside a session.
- Other clients: the server should report as `easy-verifier` with 11 tools: the seven dimensions,
  `list_dimensions`, `combined`, `score`, and `write_report`.
- By hand, start one stdio session with the host paths passed only through environment variables:

  ```console
  EASY_VERIFIER_REPO=/path/to/repo \
  EASY_VERIFIER_REPORTS=/path/to/repo/reports \
  docker compose run --rm --no-tty verifier
  ```

Inside the container, tools evaluate `/workspace`, which is the default `repo`. Leave that argument
unset. Compose deliberately doesn't publish the loopback-only HTTP/SSE opt-in, so use stdio across
the container boundary.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Client hangs or reports a parse error on connect | Remove `-t` / `-it`. A TTY mangles the stdio protocol; use `-i` only. |
| `write_report` fails with permission denied | `reports/` is not owned by UID `10001` — rerun the `chown` in step 2. |
| Mount errors on Fedora/RHEL | SELinux: append `:z` to each `-v` (`...:/workspace:ro,z`, `...:/workspace/reports:z`). |
| Reports not writable on macOS/Windows Docker Desktop | Bind-mount ownership is translated differently; confirm UID `10001` can write the directory. |
| `Unable to find image` | Build it first (step 1); the client will not build it for you. |

To verify the image end-to-end (handshake, non-root UID, read-only root, network isolation,
capabilities, path scrubbing), run `docker compose build && bash scripts/verify_container.sh`.
