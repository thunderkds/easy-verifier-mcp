# Running the Docker container as an MCP server

easy-verifier speaks MCP over **stdio**. You do not start the container yourself and leave it
running: your MCP client launches `docker run -i` on demand, talks to it through stdin/stdout, and
the container exits (`--rm`) when the session ends. No port is published and the container has no
network.

The container lives exactly as long as the client session: it starts when the session starts (not
per tool call), and each open session gets its own container, scoped to its own repository. There is
no shared, always-on server for other services to point at.

> **Warning — always pass `--init`.** Without it the server runs as PID 1 inside the container, and
> PID 1 ignores `SIGTERM`. When the client exits it signals `docker run`, the signal is forwarded,
> nothing happens, and the container keeps running with nobody attached. Every closed session (and
> every `claude mcp list` health check) then leaves an orphaned container behind. `--init` puts a
> tiny init process in front of the server so the signal stops it and `--rm` removes it.

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

### Local reference registry (optional, read-write)

Registry fields your agent researches (`agent_input.registry_entries`) are saved to a local layer so
they are researched once per machine. The host CLI uses `~/.easy-verifier-sot/` (override with
`EASY_VERIFIER_SOT`); the container reads and writes the same directory mounted at `/sot`.
`compose.yaml` bind-mounts `${EASY_VERIFIER_SOT:-~/.easy-verifier-sot}` read-write. It must be
writable by UID `10001`:

```console
mkdir -p ~/.easy-verifier-sot
sudo chown 10001:10001 ~/.easy-verifier-sot   # or: chmod o+rwx, if you share it with the host CLI
```

For a raw `docker run`, add `-e EASY_VERIFIER_SOT=/sot -v /home/you/.easy-verifier-sot:/sot`.
Without the mount, or with a directory the container cannot write, scoring still works on the
curated registry only, and the `score` response carries a `registry_notes` line saying research
cannot be saved. A symlinked directory is refused, and the directory must never sit inside the
repository being evaluated.

## 3. Register the server with your MCP client

The command every client runs is the same. Its flags mirror the hardening in `compose.yaml`:

```console
docker run -i --rm --init \
  --read-only --network none --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=16m \
  -v /path/to/repo:/workspace:ro \
  -v /path/to/repo/reports:/workspace/reports \
  easy-verifier-mcp:0.1.0
```

### Claude Code

```console
claude mcp add easy-verifier -- docker run -i --rm --init \
  --read-only --network none --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=16m \
  -v /path/to/repo:/workspace:ro \
  -v /path/to/repo/reports:/workspace/reports \
  easy-verifier-mcp:0.1.0
```

Put `--scope project` before `--` (`claude mcp add --scope project easy-verifier -- ...`) to write it
to a shared `.mcp.json` instead of your local config.

### Claude Code: one registration for every repository

The commands above hard-code one repository path. To use easy-verifier from any repository, register
a small launcher once at user scope; it mounts whatever directory Claude Code was started in.

1. Create `~/bin/easy-verifier-docker`:

   ```sh
   #!/bin/sh
   mkdir -p "$PWD/reports" "$HOME/.easy-verifier-sot"
   exec docker run -i --rm --init --read-only --user "$(id -u):$(id -g)" \
     --network none --cap-drop ALL \
     --security-opt no-new-privileges:true \
     --tmpfs /tmp:rw,noexec,nosuid,nodev,size=16m \
     -e EASY_VERIFIER_SOT=/sot \
     -v "$PWD":/workspace:ro -v "$PWD/reports":/workspace/reports \
     -v "$HOME/.easy-verifier-sot":/sot \
     easy-verifier-mcp:0.1.0
   ```

   `--user "$(id -u):$(id -g)"` runs the server as you, so the `chown 10001` steps in section 2 are
   not needed for `reports/` or `~/.easy-verifier-sot`.

2. Make it executable and register it:

   ```console
   chmod +x ~/bin/easy-verifier-docker
   claude mcp add --scope user easy-verifier -- ~/bin/easy-verifier-docker
   ```

3. In any repository: `cd /path/to/repo && claude`, run `/mcp` to confirm `easy-verifier` is
   listed, then ask the agent to use it (for example, "score this repo with easy-verifier and write
   a report"). Reports land in that repository's `reports/`.

> **Warning — one registration per Claude config directory.** `--scope user` writes to the config
> of the Claude Code profile you ran it with. If you switch profiles with `CLAUDE_CONFIG_DIR` (for
> example shell aliases such as `claude-personal` / `claude-work`), register in each one:
> `CLAUDE_CONFIG_DIR=~/.claude-work claude mcp add --scope user easy-verifier -- ~/bin/easy-verifier-docker`.
> A registration made with plain `claude` lands in `~/.claude.json` and is invisible to the others.
> A `local`-scope registration in a repository also overrides the user-scope one there.

### JSON-configured clients (Claude Desktop, Cursor, `.mcp.json`, …)

```json
{
  "mcpServers": {
    "easy-verifier": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm", "--init",
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

The full round-by-round flow of a scoring session is drawn in
[`SCORING_FLOW.md`](SCORING_FLOW.md).

Each dimension seeks **source roles**, such as `lockfile`, `requirements-doc`, or `test-file`,
filled by language-agnostic patterns and extended by Python, JS/TS, Rust, and Java pattern sets.
`list_dimensions` returns every role with its patterns. The target repository may add globs to
existing roles in an optional `.easy-verifier.toml` (`[roles] requirements-doc = ["docs/specs/*.md"]`).
It cannot remove roles or change floors.

The `score` and `write_report` tools accept an optional `agent_input` argument,
`{"picks": {"<role>": ["<path relative to /workspace>", ...]}}`, to add files a role's patterns missed. The
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

`needs_input.reference` (reference gate) rides along with either question. Every `score` response
lists `detected_stack`: the languages found by manifest and the frameworks found by a manifest
dependency (for example `express` in `package.json`), using the registry's cited detection keys.
When a detected language or framework lacks a registry field the rating rules read, `reference`
lists only those fields as `{language | framework + extends, field, why}` (`why` names the rules
that read it; a framework is only asked what a framework can add — test naming, test
declarations, assertions, security sinks — and optional fields are never asked), at most 20 per call, languages first, with an `omitted` count and fixed
instructions: at most 2 lookups per field, official docs first, cite a clear https link; otherwise
ask the user one question at a time with a recommended answer and send it as `user-supplied`.
Answers go back as `agent_input.registry_entries`. Until then those fields are scored with
generic patterns only. The CLI never shows `reference`.

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
| Containers keep running after the client closes | `--init` is missing (see the warning at the top). Add it, then clean up: `docker ps -q --filter ancestor=easy-verifier-mcp:0.1.0 \| xargs -r docker stop`. |
| `/mcp` does not list `easy-verifier` | Registered under a different Claude config directory or scope — see the warning in section 3. Restart the session after registering. |
| `docker compose up` sits at `Attaching to verifier-1` | Expected: the server is waiting for an MCP client on stdin. Don't run it with `up`; let the client launch it, or use the `docker compose run` check in section 4. |
| Changes on your branch don't show up | The image is a snapshot. Rerun `docker compose build` after changing `src/`. |

To verify the image end-to-end (handshake, non-root UID, read-only root, network isolation,
capabilities, path scrubbing), run `docker compose build && bash scripts/verify_container.sh`.
