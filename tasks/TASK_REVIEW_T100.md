# TASK_REVIEW — T100: No personal repository identifiers in tracked files

> Sibling of `tasks/TASK_GUIDE_T100.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t100_no_personal_identifiers.py` (tokens stored reversed; red with 1004 lines before the scrub, green after). Supervisor rerun 2026-10-14 of T100 plus the doc-truth and renamed-helper suites (t058/t067/t069/t071/t080): `180 passed in 6.84s` |
| Verification command run | ☑ pass | Agent: `2 failed, 2854 passed, 2 skipped in 556.92s`. The only failures are the 2 known container tests (stale Docker image). `ruff check src tests scripts`: All checks passed! (Supervisor rerun). `vendor_sources.py --check`: OK |
| Negative cases hold | ☑ pass | Supervisor's broader search (the AC1 pattern widened with name fragments, the email domain and `gitlab.`; full list in `.local/real-repos.md`) finds only public `docs.gitlab.com` / `gitlab.example.com` links. The `/home/` search finds only generic fixtures. LICENSE copyright holder left as is (legal attribution, not a repo) |
| verify | ☑ pass | AC6: `score --scope project` payloads byte-identical (`cmp`) before and after on k8s-ops (100) and fullstack-ts (56). No behaviour change — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | code-review: 146-file diff, mostly text renames. Spot-checked README, docs, the release-gate script, `.gitignore` and the agent's judgement-call list. P0–P3: none. Security review by hand: the release script now fails closed when `EV_RELEASE_PYTHON` is unset; no secrets touched. Pass |
| Full smoke suite still green (no regression) | ☑ pass | No new failures |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | No UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | No UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | No UI |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (backend-developer, worktree `chore/T100-privacy-scrub` at `3c8075b`, no implementation
commit yet; the AC1 pattern is the guide's 13-token list, not repeated here; per-file counts summed
per top-level directory so no matching line is reproduced):

```
$ date -u; git grep -cIiE '<AC1 pattern>' | <sum per top-level dir>
2026-10-14T08:03:24Z
docs/        files=2 lines=5
memory/      files=3 lines=52
(root)       files=8 lines=83
scripts/     files=2 lines=8
src/         files=5 lines=18
tasks/       files=106 lines=792
tests/       files=16 lines=46
TOTAL files=142 lines=1004

$ git grep -cIE '/home/' | <sum per top-level dir>
docs/        files=1 lines=1
memory/      files=1 lines=2
(root)       files=1 lines=1
scripts/     files=1 lines=1
src/         files=1 lines=2
tasks/       files=59 lines=115
tests/       files=1 lines=1
TOTAL files=65 lines=123
(of these 123, all but 8 lines are under the user's own home directory; the 8 are generic:
/home/you/..., /home/user/keys/..., /home/<user>/..., /home/.../easy-verifier-mcp)

$ date -u; pytest tests/test_t100_no_personal_identifiers.py -q   # new guard test, before the scrub
2026-10-14T08:05:45Z
E       AssertionError: 1004 line(s) name a personal identifier: [...file:line list elided...]
FAILED tests/test_t100_no_personal_identifiers.py::test_no_tracked_file_contains_a_personal_identifier
1 failed, 1 passed in 1.51s
exit 1
```

**AFTER** (backend-developer, worktree at `4a09b39`):

```
$ date -u; git grep -nIiE '<AC1 pattern>' ; echo "AC1 exit $?"
2026-10-14T08:20:22Z
AC1 exit 1

$ git grep -nIE '/home/' ; echo "AC2 exit $?"      # generic fixtures / placeholder text only
docs/DOCKER_MCP_GUIDE.md:53:... -v /home/you/.easy-verifier-sot:/sot`.
src/easy_verifier/core/redact.py:198:is what pinned it — `/home/<user>/…/easy-verifier-mcp` in an ordinary prose line
src/easy_verifier/core/redact.py:203:(`/home/user/keys/FAKEfake9f2Ba7Qz1XcV8mNp` still fingerprints), and
tasks/TASK_GUIDE_T100.md:36:| `<repo>` | ... `/home/user/work/easy-verifier-mcp` |
tasks/TASK_GUIDE_T100.md:40:like `/home/user/keys/` and `/home/you/.easy-verifier-sot`.
tasks/TASK_GUIDE_T100.md:71:| 2 | `git grep -nIE '/home/' ` returns only the generic fixtures (`/home/user/...`, `/home/you/...`); paste the output |
tasks/TASK_REVIEW_T004.md:19:| ... (`/home/…/easy-verifier-mcp/src/x.py` → 0 hits) ...
tasks/TASK_REVIEW_T053.md:213:  ... (`/home/user/keys/FAKE…****:5252c44014f7` still fingerprints), and
tasks/TASK_REVIEW_T053.md:412:  ... (`/home/user/keys/FAKE…****:5252c44014f7` still fingerprints), and
tasks/TASK_REVIEW_T100.md:52/62: (this Demonstration block)
tests/test_t004_redact.py:195:        "- **Repo**: `/home/user/work"
AC2 exit 0

$ git check-ignore -v .local/real-repos.md
.gitignore:13:/.local/	.local/real-repos.md

$ pytest -q   # full suite, worktree src, main-checkout interpreter
FAILED tests/integration/test_adapter_parity.py::test_container_parity_is_explicitly_verified
FAILED tests/integration/test_redaction_proof.py::test_container_redaction_proof_is_not_silent_when_docker_is_missing
2 failed, 2854 passed, 2 skipped in 556.92s (0:09:16)      # the 2 known stale-Docker-image failures only
$ ruff check src tests
All checks passed!
$ python scripts/vendor_sources.py --check
OK: 5 vendored file(s) match recorded checksums

AC6: score --repo <real-repos>/<alias> --scope project </dev/null, before (3c8075b) vs after (working tree = 4a09b39)
k8s-ops       before 08:06:00Z exit=0  after 08:19:42Z exit=0  cmp: byte-identical (sha256 c40cb77c0be3e7ed…)
              overall 100 -> 100; infrastructure 100 -> 100; the other 12 dimensions abstain, same reasons
fullstack-ts  before 08:05:55Z exit=0  after 08:19:36Z exit=0  cmp: byte-identical (sha256 98b9346acfd54190…)
              overall 56 -> 56; api 38, architecture 100, code-quality 70, data 70, operations 50,
              reliability 0, requirement-fidelity 60, security 59, supply-chain 55 (all unchanged);
              blast-radius / infrastructure / solution-fit / test-strategy abstain both times
```

**DELTA**: The branch can be pushed without exposing the user's or their clients' repository names,
absolute paths or other people's handles, and a guard test fails if any of them reappears in a
tracked file.

**WITNESS**: Supervisor (not the implementing agent), 2026-10-14: independent identifier search, test rerun and diff spot-check; the trace is in `memory/event-trace/T100.jsonl`.