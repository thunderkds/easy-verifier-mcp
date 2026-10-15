# TASK_REVIEW — T103: Shared container as the primary documented path

> Sibling of `tasks/TASK_GUIDE_T103.md`. Everything here is **filled by the reviewer at Stage
> 4/5** — it is deliberately NOT in the guide, because the implementing agent re-reads the guide on
> every turn and never fills these two sections.
>
> Consumers resolve each section **guide first, this file second** (`.claude/hooks/lib/guide_sections.py`):
> a legacy guide that still carries these sections inline keeps working unchanged, and a stray
> review file can never override an inline section.

---

## Evidence

| Check | Result | Notes / output snippet |
|-------|--------|------------------------|
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☐ pass / ☐ fail | [test file path(s) — required before Done] |
| Verification command run | ☐ pass / ☐ fail | [paste actual output] |
| Negative cases hold | ☐ pass / ☐ fail | |
| verify | ☐ pass / ☐ fail / ☐ N/A | [what was observed — must literally state "pass" or "fail" here too, e.g. "skill run, feature confirmed working — pass": the merge gate scans this Notes column for the word "pass", not just the Result column] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [what was reviewed vs. skipped, and why] |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail | |
| **UI: Visual regression (diff or verdict pasted)** | ☐ pass / ☐ fail / ☐ N/A | [screenshot path or LLM verdict — required for UI tasks, Hard-Stop Gate 6] |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ pass / ☐ fail / ☐ N/A | [method used + output] |
| **UI: Responsiveness at target viewports** | ☐ pass / ☐ fail / ☐ N/A | [viewports tested, any overflow findings] |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: Captured 2026-10-15 (UTC 03:05:48Z) from branch feat/T103-docs-shared-container at 7dbed28, before any implementation commit. Verbatim:

PRD.md: | FR-017 | Reports must be written into the **evaluated** repository under `reports/`, never into the verifier's own repository. | US-008 |

PRD.md: | FR-019a | The default and required transport is **stdio**, spoken across the container boundary (`docker run -i`). This needs no port, no bind address, and no server lifecycle to manage. | US-001 |

PRD.md: | FR-019b | An HTTP transport may be offered as an opt-in flag. When enabled it must bind to the loopback interface (`127.0.0.1`) only, and must never bind `0.0.0.0` or any routable address, including inside a container. **Amended 2026-10-14 (DDR-0013)**: streamable HTTP at `/mcp` is supported for **one shared, long-running container** (`network_mode: host`, loopback bind, `EASY_VERIFIER_PORT` default 8766) that every repo registers with `claude mcp add --transport http`. Repos are mounted read-only at their host path under one workspace root, reports go to `EASY_VERIFIER_REPORTS_DIR/<repo>/` when set, and tool calls are serialised. | US-001 |

PRD.md: | NFR-006 | The system must follow `easy-ui-mcp` operational style: a local MCP server with Docker packaging. Transport is stdio by default (FR-019a); HTTP/SSE is optional and loopback-bound (FR-019b). | Consistency |

PRD.md: | NFR-007 | The system must never write to the target repository outside `reports/`, and must never execute code from the target repository. | Safety |

PRD.md: | NFR-013 | The container must run as a non-root user, mount the target repository read-only except for its `reports/` directory, and require no elevated capabilities. A tool that reads arbitrary source trees and scans them for credentials must hold the least privilege that still does the job. | Security |

PROJECT_SPEC.md: - **Deployment target**: Local Docker container, stdio transport, reached by the operator's agent harness. Never internet-exposed (NFR-012).

PROJECT_SPEC.md: 5. **Write nothing outside the target repo's `reports/`**, with one exception: the local reference-registry layer at `$EASY_VERIFIER_SOT` or `~/.easy-verifier-sot/` (DDR-0007, FR-042), which must never be inside the target repo. Never execute code from the target repo (NFR-007).

PROJECT_SPEC.md: 6. **stdio is the default and required transport** (FR-019a). HTTP/SSE is opt-in and must bind `127.0.0.1` only — never `0.0.0.0`, including inside a container (FR-019b, NFR-012).

docs/LOCAL_MCP_GUIDE.md HTTP section:
## HTTP/SSE (opt-in, loopback only)

stdio is the default and recommended transport. For clients that can only reach a URL, there is a
legacy opt-in:

```console
easy-verifier-mcp --http
```

It binds to `127.0.0.1` only, never to a routable address.



docs/LOCAL_MCP_GUIDE.md reports line: 'Reports are written to `<repo>/reports/`, which must be writable by your user.'

docs/RELEASE_GUIDE.md Supplemental checks list ended at `python -m pytest tests/test_t018_readme.py -q`; no statement that the gate covers stdio only; no shared-container check.

.claude/skills/verify/SKILL.md (untracked, in main checkout only): surfaces table lists CLI, MCP (stdio_client), HTML report; no 'Shared container (HTTP)' surface.


**RED (new test on pre-change docs, 2026-10-15)**: `14 failed, 4 passed, 1 skipped` — failing: test_ac1_fr019a_shared_container_primary_stdio_alternative, test_ac2_reports_dir_exception_named[FR-017|NFR-007|NFR-013], test_ac2_nfr013_fully_read_only_in_shared_container, test_ac2_nfr006_matches_ac1, test_ac3_spec_deployment_target, test_ac3_spec_constraint_5_reports_dir_exception, test_ac3_spec_constraint_6_matches_prd, test_ac3_spec_insight_row_dated_t103, test_ac4_local_guide_streamable_http_before_legacy, test_ac4_local_guide_reports_line, test_ac6_release_guide_stdio_boundary_only_and_shared_checks, test_ac7_no_doc_calls_stdio_required (matched PRD FR-019a "default and required transport is **stdio**").

**GREEN**: `18 passed, 1 skipped` (the skip is AC5: `.claude/` is git-ignored, the verify skill is not in this checkout).

**AFTER**: PRD.md FR-019a now reads "The **primary** deployment is the one shared streamable-HTTP container (FR-019b, DDR-0013). Per-session **stdio** ... is the supported alternative and the default transport of the bare `easy-verifier-mcp` command ... **Amended 2026-10-15 (T103)**: stdio is no longer the sole transport." PROJECT_SPEC.md constraint 6: "The shared streamable-HTTP container is the primary deployment; per-session stdio is the supported alternative and the bare-command default ... bind `127.0.0.1` only — never `0.0.0.0`". See `git diff` of the commit for the rest.

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T103.jsonl`, never the
implementing agent alone]
