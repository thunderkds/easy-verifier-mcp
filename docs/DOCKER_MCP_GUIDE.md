# Running the Docker container as an MCP server

There are two ways to run easy-verifier in Docker:

- **One shared scoring container (recommended).** Start it once with `docker compose up -d scorer`;
  it keeps running, and every repository's MCP client points at it over streamable HTTP on
  `127.0.0.1:8766`. No container starts or stops with your sessions.
- **One container per session** (stdio). Your MCP client runs `docker run -i` on demand; the
  container has no network at all and exits when the session ends. See the alternative section
  below.

## Shared scoring container (recommended)

The `scorer` service in `compose.yaml` runs `easy-verifier-mcp --transport streamable-http`. It
mounts a workspace directory (the parent of the repositories you score) **read-only at the same
path** inside the container, so a tool's `repo` argument is simply the repository's absolute host
path, and every path in a response or report is a host path. Reports go to a separate reports
directory, never into the repository.

### 1. Build and start it (once)

From this repository:

```console
docker compose build scorer
mkdir -p ~/.easy-verifier-reports ~/.easy-verifier-sot
sudo chown 10001:10001 ~/.easy-verifier-reports ~/.easy-verifier-sot
EASY_VERIFIER_WORKSPACE=/home/you/code docker compose up -d scorer
```

| Variable | Meaning | Default |
|---|---|---|
| `EASY_VERIFIER_WORKSPACE` | Absolute host path holding the repositories to score; mounted read-only at the same path. **Required.** | none: `up` fails with a mount error naming `/EASY_VERIFIER_WORKSPACE-is-not-set` |
| `EASY_VERIFIER_REPORTS` | Absolute host path for reports, mounted read-write at the same path. A report for `/home/you/code/my-service` lands in `<this>/my-service/`. Must be writable by UID `10001`. | `~/.easy-verifier-reports` |
| `EASY_VERIFIER_SOT` | Local reference registry, mounted at `/sot` (see below). | `~/.easy-verifier-sot` |
| `EASY_VERIFIER_PORT` | Loopback port of the server. | `8766` |

Set the same variables again on later `docker compose` commands for this service (for example
export them in your shell profile), because Compose reads them on every command. The container has
`restart: unless-stopped`, so it comes back after a reboot until you stop it.

### 2. Register it, from any repository

```console
claude mcp add --transport http easy-verifier http://127.0.0.1:8766/mcp
```

Add `--scope user` to register it once for every repository (once per Claude config directory, as
the warning in the per-session section explains). JSON-configured clients use
`"type": "http", "url": "http://127.0.0.1:8766/mcp"` for the `easy-verifier` server.

### 3. Pass the absolute repository path

Ask the agent to score a repository and pass its absolute path as `repo`, for example
`/home/you/code/my-service`. The path must be inside `EASY_VERIFIER_WORKSPACE`; anything else does
not exist inside the container. Do not leave `repo` unset: the default `.` is an empty directory in
this container.

One process serves every session. Tool calls are taken one at a time, so a second session's
`score` waits until the first one finishes.

### Stop, restart and upgrade

```console
docker compose down scorer
docker compose build scorer
EASY_VERIFIER_WORKSPACE=/home/you/code docker compose up -d scorer
```

`docker compose down scorer` stops and removes it. To upgrade after pulling new code, rebuild with
`docker compose build scorer` and run the same `up -d scorer` command: Compose recreates the
container on the new image. `docker compose logs scorer` shows the server log.

### Exposure

> **Read this before you start it.** The server binds `127.0.0.1` only and nothing can change
> that; the service uses `network_mode: host`, so the container's loopback is the host's loopback
> and nothing is reachable from another machine. It has **no authentication**: while it runs,
> **any local process** on this machine (any user, any program) can call it and read, read-only,
> every repository under `EASY_VERIFIER_WORKSPACE`, and can write reports into the reports
> directory. Secret values are still redacted, and secret-bearing files are still never read. If
> that is not acceptable on this machine, use one container per session instead.

The rest of the hardening matches the per-session container: read-only root filesystem, all
capabilities dropped, `no-new-privileges`, non-root UID `10001`, a `noexec` tmpfs at `/tmp`, and
an init process.

## Alternative: one container per session (stdio)

easy-verifier speaks MCP over **stdio**. You do not start the container yourself and leave it
running: your MCP client launches `docker run -i` on demand, talks to it through stdin/stdout, and
the container exits (`--rm`) when the session ends. No port is published and the container has no
network.

The container lives exactly as long as the client session: it starts when the session starts (not
per tool call), and each open session gets its own container, scoped to its own repository.

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
- Other clients: the server should report as `easy-verifier` with 17 tools: the thirteen dimensions,
  `list_dimensions`, `combined`, `score`, and `write_report`.
- By hand, start one stdio session with the host paths passed only through environment variables:

  ```console
  EASY_VERIFIER_REPO=/path/to/repo \
  EASY_VERIFIER_REPORTS=/path/to/repo/reports \
  docker compose run --rm --no-tty verifier
  ```

Inside the per-session container, tools evaluate `/workspace`, which is the default `repo`. Leave
that argument unset. The per-session `verifier` service has no network, so it uses stdio across the
container boundary; the shared `scorer` service above is the HTTP way.

## 5. Check a feature or bugfix

Open the agent on the branch and ask *"score my changes against main with easy-verifier"*. The
`score` tool then takes `scope="changes"` and `ref="main...HEAD"`: three dots rate the whole branch
from the point it left `main`. A bare commit or branch name rates only that one commit. For
uncommitted work use `scope="worktree"`. The local `main` ref must exist in the mounted repository;
nothing is fetched.

A change score is partial today: test-strategy and security usually abstain, so a bugfix without a
regression test is not penalised. See "Checking a feature or bugfix" in the README before trusting the
number.

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
| Shared: `up -d scorer` fails with `bind source path does not exist: /EASY_VERIFIER_WORKSPACE-is-not-set` | Set `EASY_VERIFIER_WORKSPACE` to the absolute parent of your repositories. |
| Shared: `claude mcp list` shows `easy-verifier` failed to connect | The container is not running (`docker compose ps scorer`), or another program holds port `8766`; set `EASY_VERIFIER_PORT` and register that port instead. |
| Shared: a tool says the repository does not exist | The `repo` path is relative or outside `EASY_VERIFIER_WORKSPACE`. Pass the absolute host path of a repository inside it. |
| Shared: `write_report` fails with permission denied | The reports directory is not writable by UID `10001`; rerun the `chown` in step 1 of the shared section. |

To verify the image end-to-end (handshake, non-root UID, read-only root, network isolation,
capabilities, path scrubbing), run `docker compose build && bash scripts/verify_container.sh`.
