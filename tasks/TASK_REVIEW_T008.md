# TASK_REVIEW — T008: Security dimension

> Sibling of `tasks/TASK_GUIDE_T008.md`. Everything here is filled during Stage 4/5 review.

---

## Evidence

| Check | Result | Notes / output snippet |
|-------|--------|------------------------|
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☒ pass | `tests/test_t008_security.py` — 13 tests. Stage 4 remediation added two regressions pinning the confirmed P1s: `test_relevant_sources_outrank_alphabetically_earlier_filler` (AC #6, Critical Constraint 3) and `test_declared_sources_are_probed_so_miss_reasons_are_truthful` (AC #7/#11/#13). Both **failed on the pre-fix commit** (`29945d6`) and pass after: <br>`FAILED ...::test_relevant_sources_outrank_alphabetically_earlier_filler` <br>`FAILED ...::test_declared_sources_are_probed_so_miss_reasons_are_truthful` <br>`E  assert 'not examined...his dimension' == 'not found in...et repository'` <br>`2 failed, 11 deselected in 0.13s` |
| Verification command run | ☒ pass | `pytest tests/test_t008_security.py -q && python -m easy_verifier.adapters.cli security --repo . --scope project \| head -30` → `13 passed in 0.26s`, then a valid JSON pack (`"dimension": "security"`, `"mode": "kit-aware"`, `"scope": "project"`, 77 `files_read`). The trailing `BrokenPipeError` is `head` closing the pipe on the CLI, not a dimension failure — unchanged from before this task. |
| Negative cases hold | ☒ pass | Miss list on this repo is now truthful in all three states — 9 declared sources report `not found in the target repository` (previously all fabricated as `not examined: the byte budget was reached before this source was read`), `git history (out of scope for v1)` reports `out of scope for v1: git history is not searched by this dimension`, and a seeded `.env` reports `excluded: secret-bearing; operator approval required` with one `ApprovalRequest` and zero raw values in the serialized pack (AC #11/#12 gate re-verified, not regressed). |
| verify | ☒ pass | Ran the dimension live against this repo post-fix: `coverage 0.0909…`, `found ('pyproject.toml',)`, `files_read 77 excerpts 15`, and every one of the 10 misses carries a reason that reflects what was actually checked. Pre-fix the same run reported four non-existent files (`.env`, `Dockerfile`, `package.json`, `src/auth.py`) as budget-exhausted. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☒ pass | Reviewed: `src/easy_verifier/dimensions/security.py` (the only source file changed) and `tests/test_t008_security.py`. Deliberately **not** changed: `core/pipeline.py::_missing_sources` (its `not examined` default is correct for the doc dimensions — the defect was security.py never probing), `core/redact.py` and `dimensions/_doc_extract.py` (Files Must NOT Touch), `core/context.py` (no new API needed; the pseudo-source and out-of-scope reasons append to the public `context.sources_missing` record). No shared machinery was touched. |
| Full smoke suite still green (no regression) | ☒ pass | `PATH=…/.venv/bin:$PATH PYTHONPATH=src python -m pytest -q` → **`294 passed`**, exit code `0` read directly (not piped). Baseline before this task was 290; the delta is exactly the four new regression tests (two for the Stage 4 P1s, two for the Stage 5 scope-widening finding). `ruff check .` → `All checks passed!`, exit `0`. |
| **UI: Visual regression (diff or verdict pasted)** | ☒ N/A | Pure backend task; no UI exists in v1. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☒ N/A | Pure backend task; no UI exists in v1. |
| **UI: Responsiveness at target viewports** | ☒ N/A | Pure backend task; no UI exists in v1. |

---

## Demonstration

**BEFORE**: 2026-08-19T03:09:11Z — `PYTHONPATH=src PATH=/home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin:$PATH pytest tests/test_t008_security.py -q && python -m easy_verifier.adapters.cli security --repo . --scope project | head -30`

```text
ERROR: file or directory not found: tests/test_t008_security.py


no tests ran in 0.00s
```

Exit status: 4.

**AFTER**: 2026-08-20 — `PYTHONPATH=src PATH=/home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin:$PATH pytest tests/test_t008_security.py -q && python -m easy_verifier.adapters.cli security --repo . --scope project | head -30`

```text
.............                                                            [100%]
13 passed in 0.26s
{
  "dimension": "security",
  "mode": "kit-aware",
  "scope": "project",
  "files_read": [
    "pyproject.toml",
    "src/easy_verifier/dimensions/security.py",
    "AGENTS.md",
    ...
```

Exit status: 0 (the CLI's trailing `BrokenPipeError` is `head` closing the pipe, not a dimension failure).

Post-fix miss list on this repo (`scope=project`), which is the substance of the remediation:

```text
coverage 0.09090909090909091
found ('pyproject.toml',)
files_read 77 excerpts 15
 - requirements.txt :: not found in the target repository
 - package.json :: not found in the target repository
 - package-lock.json :: not found in the target repository
 - poetry.lock :: not found in the target repository
 - src/auth.py :: not found in the target repository
 - Dockerfile :: not found in the target repository
 - compose.yaml :: not found in the target repository
 - .github/workflows/ci.yml :: not found in the target repository
 - .env :: not found in the target repository
 - git history (out of scope for v1) :: out of scope for v1: git history is not searched by this dimension
```

**DELTA**: On a repository larger than the 200-file candidate cap the `security` dimension now returns its manifests, container and CI configuration instead of silently returning nothing, and every declared source in the miss list states what was actually checked — `not found`, `excluded: secret-bearing`, or `out of scope for v1` — rather than a fabricated "the byte budget was reached".

**WITNESS**: Supervisor, 2026-08-20. Both P1s were reproduced by the Supervisor independently of the implementing agent's fixtures — a 205-file alphabetical-filler repo plus `requirements.txt` and `zzz/Dockerfile` (pre-fix: `excerpts []`, `coverage 0.0`; post-fix: `['requirements.txt', 'zzz/Dockerfile']`), and a seeded repo asserting miss reasons directly. The full suite (`292 passed`, exit `0`) and `ruff check .` were re-run by the Supervisor in the assigned worktree, reading exit codes directly rather than through a pipe.

---

## Stage 4 — Review Gates

### code-review (mandatory, every task)

Run by the Supervisor against `29945d6`. Scope bounded to the diff plus direct callers:
`dimensions/security.py`, `core/context.py`, `core/models.py`, `core/pipeline.py`, `adapters/cli.py`,
`tests/test_t008_security.py`.

**P0 0 / P1 2 (both fixed, `6c6d107`) / P2 2 (both fixed, same commit) / P3 1 (not taken).**

- **P1-1 — relevance-blind candidate cap** (conf 100). `collect()` took `sorted(scope.files)[:200]`,
  an alphabetical ordering, so on any repo above the cap real evidence was dropped. Reproduced: a repo
  of 205 `aaa_*.py` filler files plus a root `requirements.txt` and `zzz/Dockerfile` returned **zero
  excerpts**, `files_read 200`, `coverage 0.0`. Same defect class as T005's tier passes. The existing
  `test_security_candidate_reads_are_bounded` could not detect it — all 205 of its fixture files are
  identical, so no ordering is observable. Fixed by ranking candidates by category (credential
  material → dependency manifest → permission/container/CI config → auth/crypto code → generic
  scannable), ties broken by path for determinism.
- **P1-2 — declared sources were never probed** (conf 100). `collect()` iterated the resolved scope's
  file list and never called `read_source()` on any `SOURCES_SOUGHT` entry, so `pipeline._missing_sources`
  had no recorded reason for any of them and fell back to its `not examined` default. The result was a
  wholly fabricated miss list: on this repo `.env`, `Dockerfile`, `package.json` and `src/auth.py` —
  none of which exist — were all reported as `not examined: the byte budget was reached before this
  source was read`. Coverage read `0.09` after 77 files were read and 15 genuine excerpts produced;
  the only declared sources that ever counted as found were those whose literal names happened to
  collide with a scope entry. Violated AC #7, AC #11's three-way distinctness, and AC #13. Same class
  as T007's false-miss-reason defect. Fixed by probing each declared source explicitly at the head of
  `collect()`.
- **P2-1 — `_AUTH_MARKERS` matched the whole lowercased path** (fixed), so anything containing
  `auth`/`policy`/`security` produced a whole-file excerpt; `tests/test_t008_security.py` scored as
  auth code on this repo. Now matches non-test path *segments*; such files still surface via the
  generic tier if a detector actually hits.
- **P2-2 — `_category()`'s return value was computed but only compared to `None`** (fixed); it now
  selects the relevance rank, so the categorisation is load-bearing rather than decorative.
- **P3 (not taken)** — `resolved_scope` is typed `object | None` on `DimensionContext` and read via
  `getattr(resolved_scope, "files", ())`. An untyped seam across `models.py`/`pipeline.py`/`security.py`.
  Left as-is: tightening it is a shared-machinery change outside this task's blast radius.

**Test blind spot that let both P1s ship green**: the suite had no assertion on miss *reasons* at all,
and no fixture mixing relevant with irrelevant files under the cap. Both regressions now pin exactly
that.

### security-review (mandatory — Medium risk)

☐ **Skill could not run** — same blocker recorded for T005: the built-in resolves the diff via
`origin/HEAD` and this repo's remote is named `github`, not `origin`. **Substitution**, per the T005
precedent: the Supervisor reviewed the diff surface directly.

- No new filesystem, subprocess, or network primitive appears anywhere in the change. The only added
  import is `SourceMiss` from `core.models`; grepping the added lines for `open(`/`Path(`/`resolve(`/
  `walk`/`iterdir`/`glob`/`subprocess`/`socket`/`urllib`/`os.` yields a single hit, `PurePosixPath(...).parts`,
  which is pure string manipulation. **No file walk or path resolver was reimplemented** — every read
  still goes through `context.read_source` / `context.request_secret_source`, inheriting T002's
  containment check and T003's symlink-escape fix rather than reproducing them. This was the explicit
  trap from T003 and it was not repeated.
- The declared-source probe added in P1-2 uses literal relative paths from `SOURCES_SOUGHT` only; it
  introduces no caller-controlled path.
- The new miss reasons reach the pack through `pipeline.py`'s existing
  `redact_module.scan(miss.reason).text` seam, so a reason echoing an OS error string cannot leak.
- AC #11/#12 gate re-verified live post-fix and not regressed.

### blast-radius (mandatory — sensitive-data handling, Medium risk)

**Framing.** This project stores no user data of its own — no database, no accounts, no PII fields.
The sensitive material is the **target repository's** credential content, which T008 is the one
dimension that deliberately goes looking for. The inventory below is therefore of data *in transit
through the engine*, not data at rest in it.

| Data class | Tier | Where it enters | Protection at the boundary |
|---|---|---|---|
| Credential material in target-repo files (API keys, tokens, passwords) | T2 | `security.collect()` → `context.read_source` | Fingerprinted at `budget.py:204` (`redact()`), the single choke point every excerpt passes |
| Secret-bearing files (`.env`, `*.pem`, `id_rsa`) | T1 | Never read by default | Refused at `context.read_source`; contents reachable only through the T008 HITL gate, which **defaults to refuse** |
| Repository-relative paths | T4 | `files_read`, `sources_found`, `sources_missing` | `_redact_paths` / `scan(...).text` on every path and every miss reason |
| Exception messages (may echo a path) | T4 | `_redacting_exceptions` | `scan(str(exc)).text` |

**Exposure vectors, ranked.**

1. **Operator-approved secret read (new surface introduced by this task).** Before T008, secret-bearing
   files were never opened under any circumstance. The HITL gate makes their contents reachable for the
   first time. Mitigations hold — approval defaults to refuse, is requested per file, is cached per path
   so lazy budget passes cannot re-prompt, and a raising callback is caught and treated as refusal — and
   approved contents still pass through the same `budget.py` redaction seam, so a `.env` read under
   approval is fingerprinted in the pack rather than emitted raw. **Residual**: T004's two documented
   detector floors (a credential assignment followed by trailing prose with no comment marker; a
   single-character-class token of 12–31 chars) are now reachable *on purpose* rather than only
   incidentally. That is the honest delta of this task and is recorded, not hidden.
2. **Pack serialization to stdout.** `cli.py:76` prints the whole pack as JSON. Post-redaction, and the
   T008 tests assert zero raw values in `json.dumps(dataclasses.asdict(pack))` across five seeded
   secrets — but the operator's terminal scrollback and any shell redirection are outside the engine's
   control.
3. **No persistence, no egress.** The engine writes nothing to the target repo (NFR-007) and makes no
   network call (NFR-012, asserted structurally by
   `test_security_module_is_bespoke_lazy_and_has_no_execution_or_network_imports`). There is no logging
   framework anywhere in `src/` — grepping for `logging`/`logger` returns nothing — so no secondary sink
   can capture evidence behind the redaction seam. This is the single largest reason the blast radius
   stays small.

**Regulatory exposure**: none directly attributable to this codebase — it processes no personal data
and is operator-run against repositories the operator already controls. Consequence of a failure here
is *the operator's own* credential disclosure into a report or terminal, whose downstream cost depends
entirely on what those credentials protect and cannot be estimated from this repo. Not legal advice;
no DPIA is implied.

**Hardening candidates for the Supervisor** (not this task's scope):

1. Close T004's two documented detector floors, now that the HITL gate makes them reachable
   deliberately — a T004 follow-up, since `redact.py` is Files-Must-NOT-Touch here.
2. Wire the `secret_approval` callback through `run_dimension` and the adapters (see accepted residue
   below), so the gate is operable rather than structurally always-refuse.

### Stage 5 `verify` finding — P1, escaped the Stage 4 gates (fixed)

Recorded here rather than under `code-review` because it was **caught at Stage 5, after every Stage 4
gate above had already passed**. Both the Stage 4 code-review and the remediation's own regression
suite missed it; only exercising the real CLI surface exposed it.

**Finding.** Omitting a narrow scope's required selector silently widened the run to a whole-repo
declared-source probe, while the pack still labelled itself with the narrow scope's name.

```text
$ python -m easy_verifier.adapters.cli security --repo <tmp> --scope task
"scope": "task", "warnings": [], files_read: ["requirements.txt", "src/auth.py"]   # identical to --scope project
```

**Chain.** `resolve_scope` *raises* `ScopeError` when `task` scope receives no `task_id`
→ `pipeline.py:71`'s `except ScopeError: resolved_scope = None`
→ `security.py`'s `whole_repo = resolved_scope is None or scope_kind == "project"` read that failure
as "whole repository, every declared source is in bounds". This breaks the invariant `pipeline.py:60`
states in its own words: *"narrow scopes receive only the explicit selector their resolver requires
and never widen on failure."*

**Why it was a blocker, not residue.** Same class as the fabricated miss reasons this remediation
existed to fix — a pack asserting more than was checked. A calling agent reading `scope: task` would
reason about whole-repo excerpts as task-relevant evidence.

**Why the tests missed it.** The suite exercised only a *bogus* selector (`--task-id T999`, which
resolves to an empty scope and behaves correctly), never a *missing* one. The two narrow kinds also
diverged under the same user error: `changes` without `--ref` returns an empty scope instead of
raising, so it never widened and the symmetry hid the gap.

**Fix — seam chosen and why.** Fixed in `dimensions/security.py`, **not** in `pipeline.py`. The
requested scope name (`context.scope`) already distinguishes "unresolved" from "project", so no
shared-machinery change was required; `run_dimension` copies `context.warnings` onto the pack *after*
the budget drain, so the dimension can declare the failure through the existing seam. A narrow scope
that never resolved now gathers nothing, records every declared source with an explicit unresolved
reason, and emits a pack warning.

```text
$ python -m easy_verifier.adapters.cli security --repo <tmp> --scope task     # after
scope      task
files_read []
excerpts   0
coverage   0.0
warning    The task scope could not be resolved, most likely because its required selector was not
           supplied. No evidence was gathered; this pack is not whole-repository output.
miss[0]    {'source': 'requirements.txt', 'reason': 'not examined: the task scope could not be
            resolved (its required selector was not supplied)'}

$ ... --scope task --task-id T999     # contrast: present selector, unchanged
files_read []
miss[0]    {'source': 'requirements.txt', 'reason': 'not in the resolved task scope'}
```

**Regression.** `test_narrow_scope_without_its_selector_does_not_widen_to_the_whole_repo` — covers
both narrow kinds, asserts empty evidence, the warning, and that every declared source carries the
unresolved reason. Verified to **fail on the pre-fix module** (`Left contains 2 more items, first
extra item: Excerpt(path='requirements.txt', ...)`). Paired with
`test_bogus_task_selector_still_resolves_to_an_empty_scope`, which pins the contrast case so a future
fix cannot collapse the two.

Post-fix suite: **294 passed**, exit `0` read directly; `ruff check .` → `All checks passed!`.

### Accepted residue (recorded, not fixed)

- **A fourth miss reason beyond the three AC #11 names.** Under `changes`/`task`/`worktree`, a declared
  source outside the resolved file set is recorded `not in the resolved <kind> scope` rather than being
  probed. The implementing agent flagged this as a judgment call before shipping it, which is the
  behaviour the T005 spawn instruction asks for. **Supervisor decision: accepted.** Without the gate,
  declared-source probing reads outside the resolved scope and breaks Success Criterion 3 — verified by
  `test_changes_scope_reads_only_the_explicit_ref_file_set`, where `requirements.txt` leaked into a
  `changes` pack. AC #11 requires its three states be genuinely distinct; it does not cap the vocabulary,
  and a fourth truthful, distinct reason serves FR-016a's auditability rather than working against it.
- **`coverage_score` remains a weak signal for this dimension.** It reads `0.09` on this repo even after
  the fix, because `SOURCES_SOUGHT` is a fixed literal list (AC #7 requires it be declared statically)
  containing paths like `src/auth.py` that most repositories will not have. The number is now *truthful*
  — those files genuinely are absent — but it does not track the 15 real evidence excerpts the dimension
  produced. Not reopened here: changing it means changing what AC #7 declares.
- **The `secret_approval` callback is never threaded through `run_dimension` or either adapter.** In
  production the gate is therefore structurally always-refuse. AC #12's requirement ("defaults to
  refuse", surfaces a request) is satisfied — `approval_requests` reaches the pack and the operator sees
  it — but no operator can currently approve. Acceptable for v1; listed as a hardening candidate above.

---

## Stage 5 — verify (Supervisor, 2026-08-20)

**First run: FAIL.** Driven at the real CLI surface (`python -m easy_verifier.adapters.cli`), not
through the in-process API, against three repositories: a seeded standalone repo with a live `.env`,
a 205-file alphabetical-filler repo, and this repo. The two Stage 4 P1 fixes held at the CLI. One new
defect surfaced that all three Stage 4 gates had passed over — see the Stage 5 section above; fixed in
`4e4c07a`.

**Re-verified after the fix, by the Supervisor, at the CLI:**

| Probe | Result |
|---|---|
| `--scope task`, selector omitted | `files_read []`, `excerpts 0`, `coverage 0.0`, explicit warning on the pack, every declared source reasoned `not examined: the task scope could not be resolved (its required selector was not supplied)` |
| `--scope task --task-id T999` (bogus but present) | unchanged — `files_read []`, no warning, `not in the resolved task scope` |
| `--scope changes`, no `--ref` | unchanged — `files_read []`, `not in the resolved changes scope` |
| `--scope task --task-id T008` (valid) | resolves to the guide; no security-category evidence in it, so 0 excerpts — correct |
| 205-filler ordering repo | `['requirements.txt', 'zzz/Dockerfile']` — P1-1 fix holds |
| seeded `.env` | withheld, one `ApprovalRequest`, `AKIA…` absent from stdout; misses truthful in all three states |
| this repo, `--scope project` | zero `not examined` reasons anywhere; no verdict-shaped key |
| full suite / lint | `294 passed`, exit `0` read directly; `ruff check .` exit `0` |

**Verdict: PASS.**

### Note on the Evidence-table counts

The Stage 4 Evidence rows above quote `files_read 77 / excerpts 15 / untruncated`. At Stage 5 the same
command reports `75 / 14 / truncated True / omitted_count 1`. This is not a selection regression: this
task's own commits grew `security.py` and `test_t008_security.py`, and the target repository being
scanned **is this repository**, so the pack crossed the 120 KB budget. The overflow is declared through
`truncated`/`omitted_count`, which is the designed behaviour (T005). The Stage 4 numbers are left as
recorded — they were true when taken, and rewriting evidence after the fact is exactly what an audit
trail must not do.

### Pre-existing issues observed while verifying — not T008's, not fixed here

- `files_read` contains duplicate entries under `task` scope. Reproduces on `architecture` (3 dupes)
  and `code-quality` (1) at the same scope; `project` scope has none. T008's own bounded-reads test
  compares `len(set(pack.files_read))`, which is presumably why it was never noticed.
- `--budget-bytes 0` raises an uncaught `BudgetError` traceback at the CLI on every dimension —
  `cli.py` catches only `RepoPathError`.
- `scope.py` diverges on failure: `task` without a selector raises `ScopeError` while `changes` without
  one returns an empty scope. T008 now handles both correctly at its own boundary, but
  `pipeline.py:60`'s "never widen on failure" invariant is still enforced by convention rather than by
  construction for the other dimensions. Candidate follow-up task on `scope.py`/`pipeline.py`.
