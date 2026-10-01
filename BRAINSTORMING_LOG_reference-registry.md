# BRAINSTORMING_LOG.md — Reference registry (scoring source of truth)
**Generated**: 2026-09-28
**Task / Context**: Proposed PRD FR-041–FR-049 / US-015; `memory/decisions.md` "2026-09-28 — PROPOSED" + G1–G9
**Skill**: `Skill({ skill: "brainstorming" })` — tier **Deep** (changes the scoring source of truth)

---

## The Problem Space

The rating cites no standard: `judge.RATING_RULES` (11 binary rules, weights sum 100) and
`judge.COVERAGE_FLOORS` are our own choices, and the same 11 rules score all seven dimensions.
Language patterns live in three disagreeing tables (`core/roles.py` ECOSYSTEM_PATTERNS,
`core/metrics.py` `_SOURCE_SUFFIXES`, `metrics.py` test-name/declaration/assertion regexes),
producing wrong scores for Kotlin/PHP (no test-name candidates), idiomatic Go (no `assert`),
RSpec/C# (declarations unmatched), and C/C++/Swift/Scala/Elixir/Dart (not source at all).

**Non-negotiable constraints (verified):**
- NFR-001 / FR-040: no model call in the engine; all agent input arrives as MCP input.
- No outbound network: `compose.yaml:9` `network_mode: none`; container `read_only: true` (`compose.yaml:8`).
- Only runtime dependency is `mcp` (`pyproject.toml:17`); no parser exists (no `ast`, tree-sitter, radon in `src/`).
- FR-027: metrics derive only from the bounded evidence pack; whole-set metrics abstain on truncation, evidence-local metrics still compute.
- NFR-007: never write to the target repo outside `reports/`.
- `blast_radius.py` already mines local git co-change/hotspots and matches file-name tokens (`_reference_pattern`, line ~375) — churn and a fan-in proxy are reachable.

---

## Decisions locked in this session (brainstorming)

| # | Question | Decision | User words |
|---|---|---|---|
| B1 | How to measure structure (complexity, fan-in) | **Registry-driven tokens.** Each language entry declares branch keywords, comment/string delimiters, function-start syntax, import syntax; engine counts decision points (lizard-style approximate CCN) and import matches. No new dependency. | chose recommended A |
| B2 | Research bound | **≤2 lookups per field**, official docs first; not found → stop and ask the user (grill-style). Engine enforces ≤20 fields per call. Every field must cite a **clear link** (https URL to the primary source), shown beside the rule; engine validates presence + well-formed URL only (cannot fetch). | "2 lookups work fine, but please note that we will refer to the link to evaluate, look like the clear source" |
| B3 | Vendored sources | **GitHub Linguist `languages.yml` (MIT), OWASP ASVS (CC BY-SA 4.0), MITRE CWE (MITRE terms).** No Semgrep (2023 licence restricts reuse). Per-language security sink patterns written by us, each citing its CWE/ASVS link. | chose recommended |
| B4 | Local registry location | **`~/.easy-verifier-sot/`** (override `EASY_VERIFIER_SOT`). Not inside the installed package (site-packages not writable; image read-only). Docker bind-mounts the same host folder read-write → CLI and MCP share research. Never touches target repos. | "easy-verifier-sot for the right purpose" |

Consequence of B4: the PRD/README "never write into this repo" rule needs **no** exception —
writes go to the user's home, not the verifier repo. Supersedes the G2 `registry/local/` path;
`registry/curated/` stays shipped inside the package (read-only).

---

## Alternative Paths (architecture of the registry)

| Option | Name | Summary | Invasiveness | Code Volume | Regression Risk | Recommended? |
|--------|------|---------|-------------|------------|----------------|--------------|
| A | Data registry + token metrics | TOML/JSON files per language (curated in package, local in `~/.easy-verifier-sot/`); one loader; roles/metrics/judge read from it; per-dimension rule tables as data | Medium | ~900 lines + data | Medium (all scores change — acceptable, no users) | ✅ Yes |
| B | Python-module registry | Same content as Python dicts in `core/registry/*.py`; local layer still files | Medium | ~800 lines | Medium | |
| C | Minimal consolidation | Merge the three tables into one module, fix the gaps, add citations; keep the 11 shared rules | Low | ~250 lines | Low | |

### Option A — Data registry + token metrics
**Approach**: `registry/curated/<lang>.toml` + `<framework>.toml` shipped in the package; `~/.easy-verifier-sot/<lang|framework>.toml` for researched entries. Every field = `{value, citation_url, source_tag}`. One loader merges curated → local (curated wins; framework adds to language). Per-dimension `RATING_RULES` become data keyed by dimension, each rule with `metric_citation` and `threshold_citation` (or `project-default`).
**Pros**: the same schema the LLM fills is what the engine reads (no translation); inspectable without reading source (FR-028); diffable; one place per language.
**Cons**: loader + schema validation code; TOML parse of untrusted local files must be bounded (reuse `roles.py` MAX_CONFIG_BYTES style limits).
**Why it might fail**: token metrics miscount inside strings/comments or odd function syntax (Ruby blocks, Kotlin lambdas) → mitigated by registry-declared delimiters and labelling the metric "approximate CCN"; a malformed local file breaking every run → loader rejects the bad entry, reports it, falls back to generic patterns.

### Option B — Python-module registry
**Approach**: curated entries as Python data; local entries still files.
**Pros**: no parser code for curated data; type-checked.
**Cons**: two formats (Python for curated, files for local) — the thing the LLM writes differs from what we ship; FR-028 "readable without reading the engine's source" is weaker.
**Why it might fail**: drift between the two formats — exactly the three-table problem again.

### Option C — Minimal consolidation
**Approach**: one module, fixed gaps, citations as comments; rules unchanged.
**Pros**: smallest, lowest risk.
**Cons**: contradicts G1 (complete design) and G5 (per-dimension standards); no gate, no local layer.
**Why it might fail**: it solves the language bug, not the "no source of truth" problem the user raised.

---

## Proposed per-dimension rules (for user approval — Q1 below)

Each rule: metric → threshold → weight. `threshold_citation = project-default` where the standard names the metric but publishes no number. Weights per dimension sum to 100.

| Dimension | Rule (metric → threshold) | Weight | Metric cites | Threshold cites |
|---|---|---|---|---|
| code-quality | share of observed functions with approx. CCN > 10 → ≤ 0.10 | 40 | McCabe 1976; ISO/IEC 5055 | NIST SP 500-235 (10) |
| code-quality | max observed function CCN → ≤ 15 | 20 | McCabe; NIST SP 500-235 | NIST SP 500-235 (15 with justification) |
| code-quality | lint config present | 20 | ISO/IEC 5055 (automated analysis) | project-default |
| code-quality | format config present | 20 | ISO/IEC 5055 | project-default |
| security | secret hits → = 0 | 40 | CWE-798; ASVS V2/V6 | ASVS (none allowed) |
| security | dangerous-sink hits (eval/exec CWE-95, shell CWE-78, SQL concat CWE-89; per-language patterns) → = 0 | 40 | CWE Top 25 | CWE (none allowed) |
| security | lockfile present | 20 | ASVS V14 (dependencies) | ASVS |
| test-strategy | share of source files without covering test → ≤ 0.20 | 35 | ISO/IEC/IEEE 29119 | project-default |
| test-strategy | assertion density per test → ≥ 1.0 | 35 | Kudrjavets et al. 2006 | project-default |
| test-strategy | test config or CI workflow present | 30 | ISO/IEC/IEEE 29119 (test environment) | project-default |
| architecture | architecture description present | 30 | ISO/IEC/IEEE 42010 | 42010 (required) |
| architecture | decision records present | 30 | ISO/IEC/IEEE 42010 (rationale) | 42010 |
| architecture | import cycles between top-level modules → = 0 | 40 | Martin, Acyclic Dependencies Principle | Martin (zero) |
| requirement-fidelity | share of ACs traced to code → ≥ 0.80 | 50 | ISO/IEC/IEEE 29148 | project-default |
| requirement-fidelity | share of ACs traced to a test → ≥ 0.80 | 50 | ISO/IEC/IEEE 29148 | project-default |
| solution-fit | **no rules — abstains by design → evaluate gate (agent-rated)** | — | ISO/IEC 25010 functional suitability | — |
| blast-radius | max fan-in (reverse dependents) of changed files → ≤ 20 | 50 | Henry & Kafura 1981 | project-default |
| blast-radius | share of changed files in top-10% churn hotspots → ≤ 0.20 | 50 | Nagappan & Ball 2005 | project-default |

Notes: Martin's abstractness/distance metrics dropped — "abstract type" detection per language is not reliable with tokens. Solution-fit has no measurable static rule that isn't a guess; honest abstention routes it to the existing FR-036 gate. requirement-fidelity abstains in standalone mode (no ACs).

---

## 50% Rule Check

Half the code: skip the framework layer at first (G8 already makes frameworks on-demand, so the
loader only needs "framework adds to language" merge — ~40 lines); reuse `roles.py`'s bounded TOML
reading instead of a new parser; keep `judge.rate()` unchanged and only make `RATING_RULES` a
per-dimension lookup. Complexity and fan-in reuse one tokenizer driven by registry delimiters.

---

## Edge Case Checklist (for every TASK_GUIDE)

- Local entry file malformed / oversized / not UTF-8 → rejected with a warning, generic patterns used, never a crash.
- Local entry tries to override a curated field → ignored (curated wins), reported.
- Citation missing or not `https://` → entry rejected at intake (FR-046).
- Two frameworks add conflicting patterns → union (add-only), deterministic order.
- Same repo scored on two machines, one without local entries → report-embedded entries + `--agent-input` replay give byte-equal output (FR-022/DDR-0005).
- `~/.easy-verifier-sot/` missing or unwritable (read-only container without mount) → scoring works on curated only; the gate says research cannot be saved.
- CCN counting inside string/comment literals → stripped using registry delimiters; fixtures per language.
- Truncated pack → whole-set rules abstain (FR-027a); per-function CCN hits stay evidence-local.
- T029 redact.py false positive on ordinary filenames must be fixed first (it already breaks citations).

---

## Surgical Scope

**Should touch**: `core/roles.py` (read patterns from registry), `core/metrics.py` (suffix/test/assertion tables → registry; new CCN, sink, cycle, fan-in metrics), `core/judge.py` (per-dimension rule data with citations), `core/gate.py` (reference gate), `core/score.py` (needs_input merge), new `core/registry.py` + `registry/curated/*.toml`, `adapters/*` (agent-input `registry_entries`), report rendering (source tag + link), `compose.yaml`/Docker docs (mount `~/.easy-verifier-sot`), a build-time vendoring script under `scripts/`.
**Must not touch**: dimension evidence gathering beyond pattern lookup, `redact.py` (T029 owns it), adapter parity normalization (DDR-0005) except adding the new field, coverage floors (2026-09-26 decision).

---

## Recommended Path

**Option A — Data registry + token metrics**, rule table approved by the user (B5, 2026-09-28).

## Next Actions (Stage 2)

1. Land T029 (redact.py false positive) first.
2. DDR-0007 for the registry + reference gate; amend PRD FR-041–FR-049 (clear flags; B4 replaces the `registry/local/` path).
3. Slice via `to-issues`: registry schema + loader + curated 9 languages → metrics from registry (fix gaps) → per-dimension rules → reference gate + local layer + review gate → report source tags/links → vendoring script + Docker mount.
