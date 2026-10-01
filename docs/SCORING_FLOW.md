# Scoring session flow (MCP)

A scoring session is one to three `score` calls from the calling agent, then an optional
`write_report`. The engine never calls an LLM: every judgment in the flow comes from the calling
agent or the user, and every number is shown with its parts.

Source: `src/easy_verifier/adapters/mcp_server.py` (`score`) and
`src/easy_verifier/core/score.py` (`score_repository`).
The rules applied in the "Compute metrics" step are listed in
[`SCORING_RULES.md`](SCORING_RULES.md).

## Flow

```mermaid
flowchart TD
    A([Agent calls score]) --> B[Parse agent_input<br/>picks, gate_evaluations,<br/>registry_entries, reviews]
    B --> C[Gather evidence for 7 dimensions<br/>fill source roles within byte budget<br/>secret files never read]
    C --> D[Detect stack<br/>languages + frameworks from manifests]
    D --> E[Compute metrics from declared rules<br/>rate each dimension 0-100 or abstain]
    E --> F[Blend gate_evaluations if sent<br/>rules x 1-w + agent x w, w = 0.5 x confidence]
    F --> G[Overall rating<br/>+ separate assessment of findings, if sent]
    G --> H{gate_evaluations<br/>in this call?}
    H -- yes --> Z([Final result])
    H -- no --> I[Attach reference or review<br/>if registry fields missing or<br/>saved entries await review]
    I --> J{First call<br/>no agent_input?}
    J -- yes --> K{Unfilled roles<br/>with candidate files?}
    K -- yes --> P[/needs_input.picks/]
    K -- no --> L
    J -- no --> L{Dimension abstained or<br/>metric within ±10% of threshold?}
    L -- yes --> Q[/needs_input.gate_evaluations/]
    L -- no --> R{reference or review<br/>attached?}
    R -- yes --> S[/needs_input.reference or review only/]
    R -- no --> Z
    P --> T[Agent picks files<br/>+ answers reference or review]
    Q --> U[Agent reads evidence_refs<br/>sends score, confidence, evidence_refs]
    S --> V[Agent answers<br/>registry_entries or reviews]
    T --> A
    U --> A
    V --> A
    Z --> W([Optional: write_report<br/>HTML report in reports/])
```

## The rounds

| Call | Agent sends | Engine may ask |
|---|---|---|
| 1 | nothing (or findings) | `picks` if roles are unfilled but candidates exist; otherwise `gate_evaluations` if a dimension is gated |
| 2 | `agent_input` with picks | `gate_evaluations` only (picks are never asked twice) |
| 3 | same `agent_input` + `gate_evaluations` | nothing: this call always returns the final result |

`reference` (registry fields the detected stack lacks) and `review` (saved registry entries for the
user to approve, improve, or reject) ride along with whichever round is asked and add no round of
their own. Answers go back as `agent_input.registry_entries` and `agent_input.reviews`, and are
saved to the local registry (`/sot` in the container) so they are researched once per machine.

Findings, when passed, get a separate **assessment**. It is shown next to the rating with any
divergence and is never blended into it.

The CLI runs the same core but never asks: one pass, rules-only ratings, no `needs_input`.
