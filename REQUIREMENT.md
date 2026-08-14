easy-verifier-mcp — High-Level Plan
(Requirements · Acceptance Criteria · Solution Approach · References)

1. Goal
Build an MCP server (easy-verifier-mcp) that performs deep evaluation of code and features.
It must:

Prefer rich context from the personal-agentic-claude kit when available
Work on any repository in standalone mode
Treat security as mandatory
Surface low-confidence / hallucination risks with improved suggestions
Write self-contained HTML reports into the target repository

It is designed as a pluggable capability for the personal-agentic harness (alongside easy-ui-mcp) and as a standalone verifier.

2. Requirements
Functional

Detect whether the target repo contains kit context (PROJECT_SPEC.md, tasks/, memory/, etc.)
Load appropriate context (kit-aware or degraded)
Support evaluation scopes: single task/feature, PR/commits/branch, working tree, whole project
Expose multiple focused evaluation tools (architecture, solution fit, requirement fidelity, test strategy, security, blast radius, code quality)
Synthesize results and suggest improvements
Write HTML reports into the target repo under reports/
Clearly warn when running with limited context

Non-functional

Must never invent missing context
Security evaluation is mandatory on non-trivial changes
Hallucination / low-confidence claims must be explicitly flagged
Usable both inside the personal-agentic harness and on arbitrary repositories
Follow the same operational style as easy-ui-mcp (local MCP, HTTP/SSE, Docker-friendly)


3. Acceptance Criteria

When kit artifacts are present, the system uses them as ground truth for architecture, solution-fit, and requirement-fidelity evaluation.
When kit artifacts are absent, the system first scans available docs (README, docs/, ADRs…), then falls back to code, and emits a clear limited-context warning.
All major evaluation dimensions are available as separate tools.
Security evaluation is always available and expected.
Every evaluation that makes a judgment includes evidence or an explicit low-confidence warning.
HTML reports are written into the target repository.
The MCP can be registered and called from Claude Code (and from the personal-agentic harness).
The same MCP works on both kit-managed projects and ordinary repositories.


4. Solution Approach (for implementing agent)
Architecture style

Follow the same pattern as easy-ui-mcp: focused MCP server that exposes tools over HTTP/SSE.
Treat personal-agentic-claude as the center/harness; this MCP is a pluggable capability.
Context contract is owned by the harness. This MCP only consumes the standard kit artifacts (or falls back).

Core design

Two modes, same binary:
Kit-aware: full-depth evaluation against PROJECT_SPEC, TASK_GUIDEs, memory/*, etc.
Standalone: docs-first, then code. Explicit degradation warning.

Multi-tool surface (not one giant evaluate tool).
Reports are HTML, written into the evaluated repository.
Scope is flexible (task / PR / branch / working tree / project).

Recommended internal structure

Context detection & loading layer
Individual evaluation dimension modules
Synthesis + suggestion layer
HTML report generator
MCP tool registration layer

Key references the implementing agent must use

https://github.com/thunderkds/personal-agentic-claude — harness, context artifacts, Stage 4 patterns, report conventions
https://github.com/thunderkds/easy-ui-mcp — existing MCP style, Docker/HTTP transport, report handling, project layout
DeepSeek Harness design philosophy (“everything is a plugin”) as conceptual reference for how this MCP plugs into the center

Out of scope for v1

Replacing the kit’s own Stage 4 skills (it should augment / be callable by them)
Training or fine-tuning models
Automatic fixing of issues (suggestions only)


5. Success Definition
A developer (or the personal-agentic supervisor) can point easy-verifier-mcp at any repository and receive an honest, evidence-based HTML evaluation report.
When the repository was built with the personal-agentic kit, the evaluation is deep and architecture-aware.
When it was not, the system still provides useful review signals and clearly states its limits.