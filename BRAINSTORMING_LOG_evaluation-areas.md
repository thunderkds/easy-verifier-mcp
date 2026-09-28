# BRAINSTORMING_LOG.md — 32 evaluation areas vs. the verifier
**Generated**: 2026-09-28
**Task / Context**: User-supplied list of 32 evaluation areas to apply on top of the reference registry (`BRAINSTORMING_LOG_reference-registry.md`, PRD FR-041–FR-049)
**Skill**: `Skill({ skill: "brainstorming" })` — tier **Deep** (scope grows from 7 dimensions)

---

## The Problem Space

The user wants the registry's criteria applied to 32 evaluation areas. The engine's hard limits
decide what each area can honestly become:

- **Static only**: reads files and local git history; never executes target code (NFR-007).
- **No network** (`compose.yaml` `network_mode: none`): no live vulnerability DB, no cloud state.
- **No model** (NFR-001): judgment comes only from the calling agent at a hard gate (FR-036).
- **No invented context** (NFR-002): an area the repo cannot evidence must say so, not score.

So every area falls into one of three classes:

| Class | Meaning | What the engine does |
|---|---|---|
| **S** — Static rule | Measurable from code/config with a cited rule | Rules rate it (registry-driven) |
| **G** — Gate | Evidence is gatherable, but correctness needs judgment | Engine gathers evidence, rules abstain or are partial → agent evaluate gate |
| **X** — Not in the repo | Process, legal, or live-system facts | Engine only checks the *documentation* exists and cites it; never scores the practice itself |

---

## Mapping (32 areas)

| # | Area | Class | Measurable signal (static) | Standard to cite | Home dimension |
|---|---|---|---|---|---|
| 1 | Architecture & dependency direction | S | import graph: cycles, layer direction violations | Martin ADP/SDP; ISO/IEC/IEEE 42010 | architecture |
| 2 | Business-rule correctness | G | AC ↔ code ↔ test traceability; rule logic needs judgment | ISO/IEC/IEEE 29148 | requirement-fidelity |
| 3 | Financial integrity & historical reconstruction | G | float used for money; mutable ledger rows; missing audit columns | ISO/IEC 5055 (reliability); domain | *domain pack: finance* |
| 4 | Data model, constraints, migrations | S | migrations present; down/rollback present; FK/NOT NULL/unique in schema | ISO/IEC 5055; project `migration-safety` checklist | **new: data** |
| 5 | Backward compatibility & upgrade safety | S (changes scope) | removed/renamed public symbols; destructive migration ops | SemVer 2.0 | blast-radius |
| 6 | Transactions, concurrency, idempotency | G | transaction blocks, idempotency keys, locks present near writes | ISO/IEC 5055 (reliability) | **new: reliability** |
| 7 | API contracts, validation, versioning | S | OpenAPI/GraphQL/proto spec present; versioned routes; schema validation at entry | OpenAPI 3.x; OWASP ASVS V5 | **new: api** |
| 8 | AuthN/Z, sessions, offboarding | S / X | auth code present; session config (secure/httponly/expiry); offboarding = X | OWASP ASVS V2–V4 | security |
| 9 | PHI minimization, retention, test-data safety | S / X | PII/PHI-shaped data in fixtures & logs; retention policy = X | HIPAA §164.514 (de-identification); ASVS V8 | *domain pack: healthcare* |
| 10 | Threat modeling, abuse cases, appsec | S | CWE sink patterns; threat-model doc present | CWE Top 25; OWASP ASVS; STRIDE | security |
| 11 | Infra security: IAM, networking, KMS, secrets | S | IaC: wildcard IAM, `0.0.0.0/0`, unencrypted storage, plaintext secrets | CIS Benchmarks; ASVS V6 | **new: infrastructure** |
| 12 | Error handling & safe degradation | S | empty/bare catch, swallowed errors | CWE-390, CWE-396; ISO/IEC 5055 | **new: reliability** |
| 13 | Retries, deadlines, unknown outcomes, vendor outages | S / G | outbound HTTP/DB calls without timeout; retries without backoff | CWE-400; Google SRE book | **new: reliability** |
| 14 | Observability, auditing, SLOs, error budgets | S / X | logging/tracing libs used; audit log writes; SLO doc = X | Google SRE (SLO); OpenTelemetry | **new: operations** |
| 15 | Performance, scalability, capacity, cost | G / X | query-in-loop patterns only; capacity & cost = X | ISO/IEC 5055 (performance efficiency) | **new: reliability** (partial) |
| 16 | Test strategy, coverage, false confidence, isolation | S | tests without assertions, skipped tests, network in unit tests, mock-only tests | ISO/IEC/IEEE 29119; Kudrjavets 2006 | test-strategy |
| 17 | Type safety & code quality | S | strict type config (mypy strict, tsconfig strict); `any`/ignore counts | ISO/IEC 5055 | code-quality |
| 18 | Maintainability, reuse, library judgment, patterns | S / G | approx. CCN, duplication; pattern judgment = G | ISO/IEC 5055; McCabe | code-quality |
| 19 | Accessibility, responsive UX, browser compat | S | img alt, labels, aria misuse; viewport meta; browserslist | WCAG 2.2 | *framework pack: frontend* (on-demand, G8) |
| 20 | Dependencies, vulns, licenses, obsolescence | S / X | lockfile, pinned versions, licence fields; live CVE lookup = X (no network) | OpenSSF Scorecard; SPDX | **new: supply-chain** |
| 21 | CI quality & reproducibility | S | CI present; actions pinned by SHA; lockfile install (`npm ci`, `--frozen-lockfile`) | OpenSSF Scorecard (Pinned-Dependencies) | **new: supply-chain** |
| 22 | Artifact provenance, SBOM, signing, promotion, rollback | S | SBOM/signing/provenance steps in CI (syft, cosign, SLSA generator); rollback doc | SLSA v1.0; CycloneDX/SPDX | **new: supply-chain** |
| 23 | Terraform state, environment, account, drift | S / X | remote backend + state locking; per-env separation; live drift = X | HashiCorp Terraform docs | **new: infrastructure** |
| 24 | Database HA, backups, restore, DR | S / X | IaC flags (multi-AZ, backup retention, PITR); restore tested = X | CIS Benchmarks; AWS Well-Architected (Reliability) | **new: infrastructure** |
| 25 | Incident response, change mgmt, access review | X | runbook/incident doc presence only | NIST SP 800-61 | **new: operations** (doc presence) |
| 26 | Configuration ownership & operational readiness | S | CODEOWNERS; env config documented; runbooks | Google SRE (production readiness) | **new: operations** |
| 27 | Documentation source-of-truth governance | S | single spec/PRD; docs updated alongside code (git co-change) | ISO/IEC/IEEE 26514 | requirement-fidelity |
| 28 | Vendor, BAA, data classification, residency | X | classification/vendor docs present only | HIPAA BAA; ISO/IEC 27001 A.5 | *domain pack: healthcare* (doc presence) |
| 29 | AI-assisted-development safety | S | agent instruction files, guardrail hooks, no secrets in prompts/agent config | OWASP Top 10 for LLM Apps | **new: operations** |
| 30 | Developer experience & deterministic local setup | S | lockfile, tool-version pin (`.tool-versions`, `.nvmrc`), devcontainer, one-command setup | OpenSSF Scorecard; 12-Factor (dev/prod parity) | **new: operations** |
| 31 | Technical-debt lifecycle & closure evidence | S | TODO/FIXME with vs. without a ticket ref; age via git blame | ISO/IEC 5055 (SQALE debt) | code-quality |
| 32 | Business continuity & degraded modes | X / G | feature flags, fallback paths; BCP doc = X | ISO 22301 | **new: reliability** (partial) |

**Counts**: S ≈ 16, S/X or S/G mixes ≈ 11, G ≈ 3, X ≈ 2 (plus X halves in the mixes).
About **7 areas are mostly not verifiable from a repository** (#3 partly, #15, #24, #25, #28, #32, parts of #8/#9/#14/#20/#23) — for those the engine can only confirm a document exists.

---

## Alternative Paths

| Option | Name | Summary | Invasiveness | Code Volume | Regression Risk | Recommended? |
|--------|------|---------|-------------|------------|----------------|--------------|
| A | 32 dimensions | Every area becomes its own dimension | Very high | ~6,000+ lines | High | |
| B | 13 dimensions + packs | 7 existing + 6 new (data, api, reliability, infrastructure, supply-chain, operations); areas become **rule groups** inside them; domain packs (finance, healthcare) and framework packs (frontend a11y) activate only when detected | High | ~2,500 lines + data | Medium | ✅ Yes |
| C | Keep 7 dimensions | Fold all areas as rule groups into today's 7 | Medium | ~1,500 lines | Medium | |

### Option A — 32 dimensions
**Pros**: one-to-one with the user's list; easy to explain.
**Cons**: 32 × coverage floors × evidence packs; the agent gets 32 packs (context explosion, NFR-009); many dimensions would be pure "doc exists" checks.
**Why it might fail**: token cost per run explodes; most dimensions abstain on typical repos, so the overall rating averages a handful of real numbers under 32 labels — false precision.

### Option B — Dimensions + on-demand packs (recommended)
**Approach**: add the new dimensions (data, api, reliability, infrastructure, supply-chain, operations) — each a normal dimension with roles, coverage floor, and cited rules. Each of the 32 areas is a **named rule group** inside one dimension, so the report still shows the user's 32 labels. **Domain packs** (finance: #3; healthcare: #9, #28) and the **frontend pack** (#19) follow the G8 on-demand rule: active only when detected (manifest deps, IaC files, schema names), researched once.
**Pros**: every area visible by name; token cost scales with what the repo actually has; reuses the registry + gate design unchanged.
**Cons**: 6 new dimensions = 6 new evidence gatherers; overall-rating semantics change (more contributors).
**Why it might fail**: detection of a domain (is this a healthcare app?) is fuzzy → must be a detect-gate pick (FR-035) or config, never guessed.

### Option C — Fold into the existing 7
**Pros**: no new dimensions, smallest change.
**Cons**: "security" would absorb IaC, supply chain, and PHI — packs become huge and coverage floors meaningless; infrastructure and operations have no natural home.
**Why it might fail**: one dimension's evidence budget (NFR-009) cannot hold code sinks + IaC + CI + SBOM at once → truncation → whole-set rules abstain.

---

## 50% Rule Check

Ship only the **S** rule groups first; represent every **X** area as a single shared "documented?"
rule type (one implementation, 10 uses) rather than bespoke code; defer domain packs until a repo
needs one (they are on-demand anyway). That halves the first delivery without dropping any area
from the report — X areas show "documentation only: present / missing".

---

## Edge Case Checklist

- An X area must never show a quality number — only "documented: yes/no" with the cited file.
- Domain detection (finance/healthcare) is a pick, not a guess (FR-035 detect gate or `.easy-verifier.toml`).
- IaC-only repo (no app code) → code dimensions abstain; infrastructure/supply-chain rate.
- Monorepo with Terraform + app + frontend → evidence budget per dimension, not pooled (existing decision).
- Live facts (CVE status, cloud drift, restore drills) → reported as "not verifiable offline", never inferred.
- New dimensions need coverage floors; the 2026-09-26 "keep floors as is" decision covers only the existing 7.

---

## Questions for the User

1. Structure: Option B (dimensions + on-demand packs, 32 areas shown as named rule groups)?
2. Target domain: the list mentions PHI, BAA and financial integrity — is the main target a healthcare/fintech platform, or should those stay optional packs?
3. X areas: show as "documentation present/missing", or leave them out of the verifier entirely?

---

## Decisions (2026-09-28)

- **E1** Domain packs optional (healthcare #9/#28, finance #3, frontend a11y #19) — active only when detected or configured.
- **E2** Option B: 13 dimensions (7 + data, api, reliability, infrastructure, supply-chain, operations); 32 areas = named rule groups.
- **E3** X areas shown as "documentation present / missing" with the cited file; never scored.

## Recommended Path

**Option B**, delivered with the 50% rule: S rule groups + the shared "documented?" rule first; domain packs on demand.

## Next Actions (Stage 2)

1. T029 (redact.py false positive) first.
2. DDR-0007 (registry + reference gate) and DDR-0008 (13 dimensions + rule groups + packs); PRD amendments.
3. `to-issues` slicing: registry core → per-dimension rules for existing 7 → 6 new dimensions (one slice each) → X "documented?" rule → packs (on demand) → report labels for 32 areas.
