# easy-verifier-mcp

A local, no-LLM engine that gathers **evidence** about a repository — file excerpts, citations,
lists of what it looked for and didn't find — so a calling agent (an MCP client, or a CLI script)
can reason about the change on its own. It performs no inference, holds no opinion, and never
returns a verdict. It requires no model API key: nothing here calls an LLM.

## What it refuses to do

- **No verdict, no score of "good"/"bad".** Every dimension returns evidence only; judgment is the
  calling agent's job, not this engine's.
- **No inventing context.** A source it did not find is reported as missing, never guessed at or
  filled in.
- **No coverage number without its miss list.** A "found 4/6" is always shown next to the two
  sources that weren't found, so the number is auditable rather than a bare percentage.
- **No execution of target-repository code**, ever — evaluation is read-only.
- **No writes outside the evaluated repo's `reports/` directory**, and never into this repo.
- **No outbound network requests.** Everything runs locally; secret values are redacted to a
  non-reversible fingerprint the moment they're read, never returned raw.

## The seven dimensions

Each dimension is a separate, independently callable unit — not one monolithic "evaluate" call.

| Dimension | What it looks at |
|---|---|
| `architecture` | Structural fit against the project's declared design |
| `solution-fit` | Whether the change addresses the stated problem |
| `requirement-fidelity` | Whether the change matches its requirement/spec |
| `code-quality` | Style, readability, and maintainability signals |
| `security` | Injection, secret handling, and other security-relevant evidence — available in every mode and scope |
| `test-strategy` | What is and isn't covered by tests |
| `blast-radius` | What else in the repo depends on, or is touched by, the change |

## Scopes

Every dimension runs against one of four scopes, and a narrow scope with no selector gathers **no
evidence** rather than silently widening to the whole repository:

| Scope | Selector | What it evaluates |
|---|---|---|
| `task` | `--task-id` | One task's `tasks/TASK_GUIDE_Txxx.md` and its acceptance criteria (kit-aware mode only) |
| `changes` | `--ref` (**required**) | A git diff/commit range/branch — no network remote required |
| `worktree` | none | Uncommitted working-tree changes |
| `project` | none | The whole repository |

A narrow scope with no selector is a refusal, not a fallback: `task` without `--task-id` and
`changes` without `--ref` both gather nothing and say so in a warning, rather than quietly
evaluating the whole project.

## Two modes: kit-aware and standalone

If the target repository carries kit artifacts (`PROJECT_SPEC.md`, `PRD.md`,
`PROJECT_KANBAN.md`, `tasks/TASK_GUIDE_*.md`, `memory/`), the engine runs in **kit-aware mode** and
treats those as ground truth. Otherwise it runs in **standalone mode**: it scans whatever
documentation exists (`README*`, `docs/`, ADRs, `CONTRIBUTING*`) first, and only falls back to
reading code where the docs are silent. Every standalone response and rendered report carries an
explicit warning that context is limited — it is never left implicit.

## Running it

Two adapters share one core; neither has evaluation logic of its own, so they cannot drift apart.

Install the package into a Python 3.11+ environment for both console entry points:

```console
python -m pip install .
```

### CLI — no server or container required

```bash
python -m easy_verifier.adapters.cli security --repo . --scope project
```

This prints one dimension's evidence pack as JSON to stdout (warnings, if any, go to stderr so
stdout stays parseable). `--scope` accepts `task`, `changes`, `worktree`, or `project`; `--ref` and
`--task-id` supply the `changes`/`task` selectors.

A discovery command lists every dimension with its purpose and declared sources, so a caller
doesn't need to already know the dimension names above:

```bash
python -m easy_verifier.adapters.cli list-dimensions
```

Run several dimensions in one call and receive an aggregate coverage summary:

```bash
python -m easy_verifier.adapters.cli combined --repo . --dimensions security,architecture
```

`write-report` accepts findings from `--findings PATH`, or from stdin when the flag is omitted.
The named file takes precedence when both are supplied:

```console
easy-verifier write-report --repo /path/to/repo --findings findings.json
```

Validation failures exit 2, operational failures exit 3, errors stay on stderr, and only the JSON
result is written to stdout.

### MCP — stdio by default

Run the local server directly with no arguments; stdout is reserved for the MCP protocol:

```console
easy-verifier-mcp
```

The MCP adapter exposes the same dimensions, discovery, combined pack, and `write_report` as MCP
tools. The default and required transport is **stdio**, spoken across the container boundary — no
port, no bind address, no server lifecycle to manage. An HTTP/SSE transport may be offered as an
opt-in convenience flag; when enabled it binds to `127.0.0.1` only and never to a routable address,
including inside a container.

### Docker — read-only target, writable reports only

The Compose service uses pinned Python and MCP versions, runs as UID/GID `10001`, drops all
capabilities, has no runtime network, publishes no ports, and mounts the target repository
read-only. Prepare a dedicated reports directory owned by that fixed non-root identity:

```console
mkdir -p /path/to/repo/reports
sudo chown 10001:10001 /path/to/repo/reports
```

Build and start one stdio session with host paths supplied only through environment variables:

```console
docker compose build
EASY_VERIFIER_REPO=/path/to/repo \
EASY_VERIFIER_REPORTS=/path/to/repo/reports \
docker compose run --rm --no-tty verifier
```

The loopback-only HTTP/SSE opt-in is deliberately not published by Compose; use stdio across the
container boundary. The target needs no package or executable installed. On SELinux hosts, add an
appropriate `:z`/`:Z` label to equivalent bind mounts. macOS and Windows Docker Desktop translate
bind-mount ownership differently, so confirm the reports directory is writable by UID `10001`.

To exercise the real MCP handshake, non-root UID, read-only root, writable reports overlay, Git,
network isolation, capabilities, ports, and container-path scrubbing in one pass:

```console
docker compose build && bash scripts/verify_container.sh
```

## Where reports go

Reports are written into the **evaluated repository's** `reports/` directory, never into this
repo's — even when the two happen to be the same checkout (as they will be if you point this tool
at itself). Nothing is overwritten; filenames are unique per scope and timestamp.

## License

See `LICENSE`.
