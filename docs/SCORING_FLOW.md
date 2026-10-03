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

## Improvement plan

Every `score` result (CLI and MCP alike) carries `improvement_plan`, and the HTML report shows it
after the score panel. It lists every gap of every rated dimension, in three groups:

| Group | Meaning |
|---|---|
| P0 | near miss: the rule is unmet but its value is within ±10% (`BORDERLINE_BAND`) of the threshold; a threshold of 0 is never a near miss |
| P1 | clear failure: the rule is unmet and outside the band |
| P2 | not measurable yet: the rule's metric abstained |

Each item gives the metric, its value, the rule, the cited files, a static engine fix line
(`fix.source = "engine"`), and what fixing it is worth: `dimension_gain` and `overall_gain`. The
gain is **recomputed** with the rating arithmetic as if that one rule passed (rounded once, ties to
even), never read off the weight. A P2 gain is a range `[if it fails, if it passes]`, and the low
end may be negative. A gated dimension's items use its rules part (`gain_basis: "rules"`); the
agent half of a blend is never predicted. Inside a group items are ordered by overall gain (P2 by
the high end), then dimension, then metric name. A dimension without a rules rating gets one
`abstained` line with its reason code instead of items. When every group is empty the report says
"No gaps".
