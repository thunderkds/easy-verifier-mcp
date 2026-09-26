# easy-verifier-mcp

A local, no-LLM engine that gathers **evidence** about a repository — file excerpts, citations,
lists of what it looked for and didn't find — and computes inspectable quality ratings from
declared rules over measured facts. A calling agent can optionally submit its own findings for a
separate assessment and divergence. The engine performs no inference and requires no model API
key: nothing here calls an LLM.

## What it refuses to do

- **No inferred verdict.** Ratings are deterministic arithmetic over cited metrics. Caller findings
  produce a separate assessment; the engine never blends the two or invents a judgment.
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

Rate all seven dimensions in one call. The result includes every cited metric and an overall
disclosure naming which dimensions contributed or abstained:

```bash
python -m easy_verifier.adapters.cli score --repo . --scope project
```

Pass optional findings through `--findings PATH` or stdin to add the caller-derived assessments and
rating-to-assessment divergences to the same JSON output.

`write-report` accepts findings from `--findings PATH`, or from stdin when the flag is omitted.
The named file takes precedence when both are supplied:

```console
easy-verifier write-report --repo /path/to/repo --findings findings.json
```

Validation failures exit 2, operational failures exit 3, errors stay on stderr, and only the JSON
result is written to stdout.

### MCP — stdio by default

The MCP adapter exposes the same dimensions, discovery, combined pack, `score`, and `write_report`
as MCP tools. The default transport is **stdio**, so there is no port and no server lifecycle to
manage: your MCP client starts the server on demand. An HTTP/SSE opt-in exists, and it binds to
`127.0.0.1` only.

Setup for Claude Code, Claude Desktop, Cursor, and other clients:
[`docs/LOCAL_MCP_GUIDE.md`](docs/LOCAL_MCP_GUIDE.md).

### Docker — read-only target, writable reports only

The container runs with pinned Python and MCP versions as UID/GID `10001`. It drops all
capabilities, has no network, publishes no ports, and mounts the target repository read-only.
Only `reports/` is writable. The target needs no package or executable installed.

```console
docker compose build
```

Registering the container with an MCP client, preparing `reports/`, and troubleshooting:
[`docs/DOCKER_MCP_GUIDE.md`](docs/DOCKER_MCP_GUIDE.md).

### Final release gate

Run the repository's fail-closed release gate from a clean, published candidate:

```console
bash scripts/verify_release_gate.sh
```

The command runs the host integration suite, requires the container integration tests, runs the
container verifier, and emits the KPI summary only after those checks pass. A zero exit status is
required for release. Docker, MCP stdio, or another required boundary that is unavailable is
reported as `NOT VERIFIED` and causes a non-zero exit; skipped or historical output is not release
evidence. Record the exact commit, environment, command output, and any unavailable proof in
`tasks/TASK_REVIEW_T023.md`.

## Where reports go

Reports are written into the **evaluated repository's** `reports/` directory, never into this
repo's — even when the two happen to be the same checkout (as they will be if you point this tool
at itself). Nothing is overwritten; filenames are unique per scope and timestamp.

Each full seven-dimension report includes a score panel with the rule-based rating, optional caller
assessment, divergence where both exist, and the cited metrics. A withheld rating is displayed as
an abstention with its coverage boundary, never as zero or a low score.

## License

See `LICENSE`.
