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

### CLI — runnable today, no server or container required

```bash
python -m easy_verifier.adapters.cli security --repo . --scope worktree
```

This prints one dimension's evidence pack as JSON to stdout (warnings, if any, go to stderr so
stdout stays parseable). `--scope` accepts `task`, `changes`, `worktree`, or `project`; `--ref` and
`--task-id` supply the `changes`/`task` selectors.

> **Planned (T011).** A discovery command listing every dimension with its purpose and its
> declared sources, so a caller doesn't need to already know the dimension names above:
```bash
python -m easy_verifier.adapters.cli discover
```

> **Planned (T012).** A combined-pack command that runs several dimensions in one call and returns
> an aggregate coverage summary, instead of issuing one call per dimension:
```bash
python -m easy_verifier.adapters.cli combined --repo . --dimensions security,architecture
```

> **Planned (T013, T015).** A `write_report` command accepting a calling agent's findings as JSON
> and rendering them into a self-contained HTML report under the evaluated repo's `reports/` —
> never this repo's:
```bash
python -m easy_verifier.adapters.cli write-report --repo . --findings findings.json
```

### MCP — planned (T014), stdio by default

> **Planned (T014).** No MCP server exists yet. Once shipped, registration will run the container
> over stdio, no port published:
```bash
docker run -i --rm -v "$(pwd)":/workspace easy-verifier-mcp
```

The MCP adapter will expose the same dimensions, discovery, and `write_report` as MCP tools. The
default and required transport is **stdio**, spoken across the container boundary — no port, no
bind address, no server lifecycle to manage. An HTTP/SSE transport may be offered as an opt-in
convenience flag; when enabled it binds to `127.0.0.1` only and never to a routable address,
including inside a container.

### Docker — planned (T016)

> **Planned (T016).** No Dockerfile exists yet:
```bash
docker compose up
```

The container will run as a non-root user, mount the target repository read-only except for its
`reports/` directory, take all configuration from environment variables, and speak stdio by
default. The repository being evaluated is mounted as a volume — this tool never needs anything
installed inside the target.

## Where reports go

Reports are written into the **evaluated repository's** `reports/` directory, never into this
repo's — even when the two happen to be the same checkout (as they will be if you point this tool
at itself). Nothing is overwritten; filenames are unique per scope and timestamp.

## License

See `LICENSE`.
