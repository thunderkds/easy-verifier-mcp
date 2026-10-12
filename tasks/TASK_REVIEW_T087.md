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

**BEFORE** (captured by backend-developer on `feat/T087-third-party-exclusion` at `9e00f99`, before
any implementation commit; the guide's `-m easy_verifier` has no `__main__`, so the CLI module
behind the `easy-verifier` script was used):

```
$ date -u; PYTHONPATH=<worktree>/src <main>/.venv/bin/python -m easy_verifier.adapters.cli score \
    --repo /home/hungnguyenhuu/workspace/project/bryony/scraping-devops --scope project < /dev/null > sd.json
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

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
