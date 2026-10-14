# TASK_REVIEW — T087: Exclude third-party code from evaluation

> Sibling of `tasks/TASK_GUIDE_T087.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | Implementer: `tests/test_t087_third_party_exclusion.py`, 53 tests covering SC 1–5 and AC 1–8: each reason kind, `-linguist-vendored`/`=false` re-include, `!attr` does not re-include, last line and deeper `.gitattributes` win, subdirectory scoping, invalid `exclude` rejected (CLI exit 2), nested both extremes, root never nested, nested-in-excluded disclosed once, secret-bearing file inside third-party never read, symlink containment, `context._walk` and role resolution, third-party pick rejected, worktree/changes scope plus diff, payload/pack/report disclosure, CLI == MCP, churn ranking. `53 passed in 1.89s`. Sabotage pass (each restored afterwards): nested predicate always None → 10 failed; licence-only (NOTICE ignored) → 2 failed; unset re-include ignored → 2 failed; churn filter removed → 1 failed; `context._walk` filter removed → 1 failed. |
| Verification command run | ☑ pass | Implementer, worktree `src` on main `.venv` (imports confirmed from the worktree): `2 failed, 2609 passed, 2 skipped in 370.58s`. The 2 failures are the known stale-container tests (`test_container_parity_is_explicitly_verified`, `test_container_redaction_proof_is_not_silent_when_docker_is_missing`). `ruff check src tests` → `All checks passed!`. `scripts/vendor_sources.py --check` → `OK: 5 vendored file(s) match recorded checksums`. Real-repo runs: see Demonstration AFTER. |
| Negative cases hold | ☑ pass | Implementer: `packages/shared/{LICENSE,package.json,index.ts}` not excluded. Removing NOTICE un-excludes the Harbor fixture. Team files that `vendor.yml` lists are never excluded: `.github/workflows/ci.yml`, `*.d.ts`, `external/`, `bootstrap.conf.js`, `prototype.js`, `__import.scss`, `fabfile.py`, fixtures, `testdata/`, lockfiles, `Jenkinsfile`, `.gitignore`. On fullstack-ts, python-ml and nest-api nothing is excluded. |
| verify | ☑ pass | Supervisor 2026-10-12 drove the CLI surface from the branch (the `verify` skill can only be invoked by the user): `score --repo k8s-ops --scope project` → `excluded: [{path: docker-registry/harbor/, reason: nested-project, rule: LICENSE + AUTHORS}]`, `docker-registry/harbor/` cites in ratings = **0** (was 105), overall `rating_abstention` (none of the declared dimensions produced a rating) — pass. `pytest tests/test_t087_third_party_exclusion.py` → 53 passed. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Supervisor code-review on `develop...feat/T087` (20 files): `scope.third_party_filter` + its callers `context._walk`, `roles` pick check, `blast_radius` churn ranking, `score`/`report` disclosure. P0 0 · P1 0 · P2 0 · P3 1 (gitattributes pattern text echoed unredacted; bounded glob, accepted). Security review was done manually (the built-in skill needs `origin`; this remote is `github`): untrusted `.gitattributes` is read only when contained and within MAX_CONFIG_BYTES, toml globs are validated, symlinks outside the repo are rejected, only names are read for the nested check. Glob edge case checked: `**/*.min.js` matches root-level files. |
| Full smoke suite still green (no regression) | ☑ pass | 2609 passed, 2 failed, 2 skipped (both failures are the known stale-image container tests, `learnings.md`); ruff clean. |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Backend only; the report reuses the existing folded-list markup. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Backend only; the report reuses the existing folded-list markup. |
| **UI: Responsiveness at target viewports** | ☑ N/A | Backend only; the report reuses the existing folded-list markup. |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured by backend-developer on `feat/T087-third-party-exclusion` at `9e00f99`, before
any implementation commit; the guide's `-m easy_verifier` has no `__main__`, so the CLI module
behind the `easy-verifier` script was used):

```
$ date -u; PYTHONPATH=<worktree>/src <main>/.venv/bin/python -m easy_verifier.adapters.cli score \
    --repo <real-repos>/k8s-ops --scope project < /dev/null > sd.json
Mon Oct 12 09:18:12 AM UTC 2026
exit=0
Mon Oct 12 09:18:16 AM UTC 2026

$ python summ.py sd.json docker-registry/harbor/
overall 53 [['architecture', 0], ['security', 50], ['test-strategy', 40], ['reliability', 39], ['api', 60], ['data', 80], ['infrastructure', 100]]
architecture 0
  architecture_description_missing=1 passed=False cites=76 cites_docker-registry/harbor/=75
  decision_records_missing=1 passed=False cites=76 cites_docker-registry/harbor/=75
  top_level_import_cycles=1 passed=False cites=17 cites_docker-registry/harbor/=17
  layer_direction_violations=8 passed=False cites=8 cites_docker-registry/harbor/=8
all rating inputs citing docker-registry/harbor/: 105

top_level_import_cycles ['docker-registry/harbor/auth/authenticator.go', 'docker-registry/harbor/auth/db/db.go',
  'docker-registry/harbor/auth/ldap/ldap.go', 'docker-registry/harbor/dao/accesslog.go', 'docker-registry/harbor/dao/base.go',
  'docker-registry/harbor/dao/project.go', 'docker-registry/harbor/dao/register.go', 'docker-registry/harbor/dao/user.go',
  'docker-registry/harbor/service/notification.go', 'docker-registry/harbor/service/token/authutils.go',
  'docker-registry/harbor/service/token/token.go', 'docker-registry/harbor/service/utils/cache.go',
  'docker-registry/harbor/utils/registry/auth/authorizer.go', 'docker-registry/harbor/utils/registry/auth/challenge.go',
  'docker-registry/harbor/utils/registry/auth/tokenhandler.go', 'docker-registry/harbor/utils/registry/registry.go',
  'docker-registry/harbor/utils/registry/repository.go']
layer_direction_violations ['docker-registry/harbor/dao/accesslog.go', 'docker-registry/harbor/dao/base.go',
  'docker-registry/harbor/dao/project.go', 'docker-registry/harbor/dao/register.go', 'docker-registry/harbor/dao/user.go',
  'docker-registry/harbor/service/notification.go', 'docker-registry/harbor/service/token/authutils.go',
  'docker-registry/harbor/service/token/token.go']
```

Architecture = 0: every cycle and every layer violation is a Harbor file; 75 of the 76 files the two
document rules read are Harbor files (incl. `docker-registry/harbor/vendor/golang.org/x/crypto/...`
and `static/vendors/*.min.js`). The payload has no `excluded` key.

**AFTER** (backend-developer, commit `21bd791`; the same command, with `runall.sh` running the 5 repos
one after another; BEFORE for all 5 came from a frozen copy of the pre-change `src`):

```
== node-monorepo 09:48:57 UTC exit=0 | == sd 09:49:25 exit=0 | == fullstack-ts 09:49:30 exit=0
== python-ml 09:49:40 exit=0 | == nest-api 09:49:45 exit=0 (Mon Oct 12 2026)
```

| Repo | Overall BEFORE→AFTER | Architecture BEFORE→AFTER | Other dimensions changed | `excluded` in score JSON |
|---|---|---|---|---|
| node-monorepo | 59 → 59 | 83 → 83 | none | `[{"path": "frontend/app/scripts/vendor/", "reason": "linguist-pattern", "rule": "linguist vendor.yml: (^|/)vendors?/", "excluded": "third-party"}]` |
| k8s-ops | 53 → withheld (no contributor) | 0 → abstain `below_coverage_floor` (0.25 < 0.40) | api 60→abstain, data 80→abstain, infrastructure 100→abstain (`all_metrics_abstained`), reliability 39→abstain (`all_metrics_abstained`), security 50→abstain, test-strategy 40→abstain, requirement-fidelity `insufficient_measured_weight`→`below_coverage_floor` | `[{"path": "docker-registry/harbor/", "reason": "nested-project", "rule": "LICENSE + AUTHORS", "excluded": "third-party"}]` |
| fullstack-ts | 56 → 56 | 100 → 100 | none | absent (nothing excluded) |
| python-ml | 60 → 60 | 83 → 83 | none | absent |
| nest-api | 80 → 80 | 80 → 80 | none | absent |

k8s-ops: `rating-input citations of docker-registry/harbor/: 0` (AFTER; BEFORE: 105). Why
every dimension there abstains is explained under Implementer notes below.

Each newly excluded file, justified by hand (AC 7):
- **node-monorepo**: 19 files, all under `frontend/app/scripts/vendor/`: `MinFaker.js`, `auto.expand.input.js`,
  `bootstrap-tagsinput.js`, `canvg.min.js`, `infiniScroll.modified.js`, `jquery-browser.js`,
  `jquery.daterangepicker.js`, `jquery.geocomplete.js`, `jquery.numeric-input.js`, `jquery.rateyo.min.js`,
  `jquery.tablesorter.js`, `jquery.tablesorter.widgets.js`, `linkedin.js`, `map-google-api.js`,
  `numeric-input.js`, `nv.d3.js`, `rgbcolor.js`, `stackblur.js`, `typeahead.bundle.js`. These are
  third-party browser libraries in a vendor directory (the Supervisor expected 16; the right count is 19).
- **k8s-ops**: 195 files, all under `docker-registry/harbor/`, which holds Harbor's own LICENSE,
  AUTHORS, NOTICE and `vendor/`. Diffing the project file set BEFORE against AFTER shows nothing removed
  outside Harbor.
- fullstack-ts 718 → 718, python-ml 230 → 230, nest-api 158 → 158 files: nothing newly excluded.

HTML report: `write-report` was run on a scratch copy of k8s-ops, so nothing was written into
the real repo. Excerpt:

```
<details class="third-party-excluded"><summary>Excluded as third-party (1)</summary><ul class="miss-list"><li><code>docker-registry/harbor/</code> (nested-project: LICENSE + AUTHORS)</li></ul></details>
```

**Implementer notes**
- **k8s-ops withholds its overall, honestly.** Without Harbor, the repository's own files are 352
  `.yml` (Rancher 2 / Rancher / ELK), 7 `.sh` and a little config, with no source file in a registry
  language. BEFORE, every rating except security cited only Harbor:

  | Dimension | Rating | Files cited | Harbor files among them |
  |---|---|---|---|
  | architecture | 0 | 177 | 175 |
  | test-strategy | 40 | 160 | 160 |
  | reliability | 39 | 84 | 84 |
  | infrastructure | 100 | 27 | 27 |
  | data | 80 | 5 | 5 |
  | api | 60 | 2 | 2 |
  | security | 50 | 66 | 32 |

  Each abstention now names what is missing, e.g. "no in-scope source file of a registry language". This
  is the intended effect, not a defect. DDR-0012's expectation that k8s-ops "gains a documentation
  pass" depends on T089 (document recognition by content).
- **The two `_EXCLUDED_DIRS` sets now agree.** `scope.py` uses `context.py`'s set. The scope walk gains
  `target` (no change on the 5 repos). `vendor` moves out of the silent set: it is now excluded by the
  Linguist predicate and disclosed.
- **Accepted deviation 2:** blast-radius's churn ranking (`git ls-files`, which bypasses both walks) also
  skips third-party files, so a vendored file cannot feed `changed_files_in_churn_hotspots_share`.
- **Accepted deviations 1, 3 and 4:**
  - The test file is named `test_t087_*`.
  - The T068 fixture moved from `vendor/` to `generated/`.
  - The legacy-key lists in T055 and T071 gained the new keys.
  - Quoted, directory-only or over-bound `.gitattributes` lines are skipped. Skipping a line can only
    leave code in.

**DELTA**: a repository that commits someone else's code, such as k8s-ops's full Harbor copy, is
no longer scored on that code. Harbor's cycle, layer violations and 105 rating citations are gone. The
payload and report list each excluded root with its reason and matched rule, and a project can declare
or re-include paths itself (`.gitattributes`, `.easy-verifier.toml` `exclude`).

**WITNESS**: Supervisor, 2026-10-12. `memory/event-trace/T087.jsonl` (110 records) holds the implementer's test and real-repo runs. The Supervisor independently re-ran `tests/test_t087_third_party_exclusion.py` (53 passed) and `score` on k8s-ops from the branch (Harbor excluded, 0 Harbor citations in ratings).

**Supervisor follow-up (out of scope):** with Harbor excluded, k8s-ops' own code is about 350 Rancher/ELK compose YAML files plus 7 shell scripts, and every dimension abstains. The infrastructure dimension (rated 100 before, all from Harbor files) does not recognise the repo's own compose YAML. Candidate follow-up task.
