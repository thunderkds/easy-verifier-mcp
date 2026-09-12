# TASK_REVIEW — T021: finding assessment and divergence

## Evidence

| Check | Result | Evidence |
|---|---|---|
| Requirement fidelity | Pass | User selected optional `Finding.severity` with a declared default on 2026-09-12. Omission remains `None` through validation; assessment applies `medium` and records each application in its inputs, count, and provenance. |
| Focused verification | Pass | `PATH=<main>/.venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest tests/test_assessment.py -q` → **18 passed in 0.08s**. |
| Findings compatibility | Pass | `tests/test_assessment.py tests/test_t006_findings.py` → **52 passed in 0.13s**. Existing positional `Finding` fields remain in place; optional severity was appended after `suggestion`. |
| Full regression | Pass with environment substitution | Compatible provisioned interpreter → **562 passed, 1 upstream warning in 11.20s**. The project `.venv` still lacks the pre-existing `mcp` dependency needed to collect T014/T015. |
| Lint and format | Pass | Ruff check: `All checks passed!`; Ruff format: all four scoped files formatted; `git diff --check` clean. |
| Review | Pass after remediation | Bounded manual P0-P3 review: P0 0 / P1 0 / P2 0. The named review skills are unavailable in this Codex session. |
| Security | Pass via direct substitution | AST regression permits only stdlib arithmetic/data imports plus existing core modules and forbids I/O, subprocess, network, environment, and model-client attributes. No new filesystem or egress primitive exists. |
| UI | N/A | Pure core arithmetic and schema work; no UI or rendered output is in T021 scope. |

## Declared arithmetic

- Severity penalties: low `5`, medium `15`, high `30` quality points.
- Confidence percentages: low `25`, medium `60`, high `100`.
- Default severity: `medium`, applied only when omitted and always disclosed.
- Assessment: `max(0, 100 - round(sum(severity_penalty * confidence_percentage) / 100))`.
- Divergence signed gap: `assessment - rating`; negative means the calling agent is harsher. The absolute gap and both inputs are carried beside it.

These are inspectable initial values, not inferred judgments. Findings supply the severity and
confidence; the engine only performs the declared arithmetic.

## Review findings and remediation

| Severity | Finding | Remediation |
|---|---|---|
| P1 | The first assessment input carried title/reference/weights but omitted finding detail and suggestion, so it did not satisfy the complete provenance claim. | `AssessmentInput` now carries and serializes the full finding content relevant to T021, plus supplied/effective severity and every arithmetic contribution. |
| P1 | Valid dataclass identities could be forged or combined with a divergence computed from different inputs. | Assessment sets, rating inputs, comparisons, absence objects, and comparison sets are reconstructed/revalidated at public aggregate boundaries; comparison constructors prove their divergence matches their side-by-side values. |
| P2 | Public divergence gap fields and `defaulted_severity_count` initially accepted numerically equal non-integer values. | Exact integer checks and adversarial constructor tests now reject those values. |

Post-remediation result: P0 0 / P1 0 / P2 0. No rating rule, metric contract,
report renderer, adapter, or T020 source file changed.

## Demonstration

Before T021, `easy_verifier.core.assessment` did not exist and `Finding` rejected `severity` as an
unknown field. After T021, `assess()` returns one canonical outcome for each of seven dimensions,
including a distinct absence where no findings were submitted. `compare()` retains independent
rating and assessment values and emits either a hand-checkable signed divergence or an explicit
absence containing the original abstention/absence reason. It never returns a merged quality value.
