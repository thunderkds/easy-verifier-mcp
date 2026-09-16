# TASK_REVIEW — T016: least-privilege container packaging

## Status

**Unblocked and passing.** Docker is reachable in this environment. The
container image itself was already correct (verified live by the Supervisor
on 2026-09-16); `scripts/verify_container.sh` had two independent defects of
its own that made the verification command fail even though the container
passed every hardening assertion. Both are fixed, scoped entirely to the
script (Dockerfile/compose untouched). The guide's exact Verification Command
now passes end-to-end.

## Evidence

| Check | Result | Notes / output snippet |
|-------|--------|------------------------|
| New static acceptance tests | pass | `PYTHONPATH=src python -m pytest tests/test_t016_container_config.py -q` -> `4 passed` |
| README truth tests | pass | `PYTHONPATH=src python -m pytest tests/test_t018_readme.py -q` -> `7 passed` |
| Compose expansion | pass | `docker compose config --quiet` exits 0 and static tests inspect its JSON form |
| Verifier shell syntax | pass | `bash -n scripts/verify_container.sh` exits 0 |
| Reproduced defect 1 (stale tool count) pre-fix | fail (expected) | `FAIL: tools/list did not return exactly 10 tools` |
| Reproduced defect 2 (dropped final response) pre-fix | fail (expected) | with defect 1 patched to `11` on a scratch copy, `KeyError: 3` raised at the `for request_id in (3, 4)` loop — confirms the harness could never have reached its own last assertion |
| Live container verification (`docker compose build && bash scripts/verify_container.sh`) | **pass** | see full output below; run twice for stability, both `exit=0` |
| Stage 4 P2 fix — timeout path names only the missing id(s) | pass (both extremes pinned) | see "Stage 4 P2 fix" section below: unmodified script passes; a copy with only the id-4 request deleted fails naming `4` alone, not `1 2 3 4` |

## Demonstration

**BEFORE (original packaging, captured 2026-09-02T09:45:37Z)**:

```text
missing Dockerfile
missing compose.yaml
missing .dockerignore
missing scripts/verify_container.sh
bash: scripts/verify_container.sh: No such file or directory
exit=127
```

**BEFORE (this harness-fix task, captured 2026-09-16T04:01:13Z, Docker now reachable)**:

```text
$ docker compose build && bash scripts/verify_container.sh
... (build output omitted, image builds cleanly) ...
 Image easy-verifier-mcp:0.1.0 Built
 Container easy-verifier-t016-25785-verifier-run-00139b150d77 Creating
 Container easy-verifier-t016-25785-verifier-run-00139b150d77 Created
FAIL: tools/list did not return exactly 10 tools
exit=1
```

Reproduction of defect 2 in isolation (scratch copy with the tool-count
assertion patched to 11, to get past defect 1 and reach the id-4 read):

```text
$ bash /tmp/verify_container_probe.sh
 Container easy-verifier-t016-26016-verifier-run-2cae9e29e16d Creating
 Container easy-verifier-t016-26016-verifier-run-2cae9e29e16d Created
 Container easy-verifier-t016-26016-verifier-run-37befbd76d49 Creating
 Container easy-verifier-t016-26016-verifier-run-37befbd76d49 Created
Traceback (most recent call last):
  File "<stdin>", line 13, in <module>
KeyError: 3
```

This confirms both defects independently: the script never reached its own
final assertion on the pre-fix commit, and the missing id is nondeterministic
(3 in this run, 4 in the Supervisor's earlier reordering test), consistent
with a race against `docker compose run`'s stdin-EOF-triggered exit rather
than a fixed off-by-one.

**CURRENT (fixed harness, run twice for stability)**:

```text
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-09-16T04:02:49Z
$ docker compose build && bash scripts/verify_container.sh
... (build output omitted — CACHED layers, image already built) ...
 Image easy-verifier-mcp:0.1.0 Built
 Container easy-verifier-t016-13212-verifier-run-a392cefa5492 Creating
 Container easy-verifier-t016-13212-verifier-run-a392cefa5492 Created
 Container easy-verifier-t016-13212-verifier-run-d3713fad5ef8 Creating
 Container easy-verifier-t016-13212-verifier-run-d3713fad5ef8 Created
PASS: uid=10001, tools=11, root=read-only, reports=writable, network=none, ports=none, caps=none
exit=0

$ bash scripts/verify_container.sh
 Container easy-verifier-t016-23416-verifier-run-3adc515ad9da Creating
 Container easy-verifier-t016-23416-verifier-run-3adc515ad9da Created
 Container easy-verifier-t016-23416-verifier-run-6d570f2e3628 Creating
 Container easy-verifier-t016-23416-verifier-run-6d570f2e3628 Created
PASS: uid=10001, tools=11, root=read-only, reports=writable, network=none, ports=none, caps=none
exit=0
```

That live gate checks the real MCP initialization, eleven-tool listing (by
name, not bare count — a future adapter addition now reports which tool
appeared rather than only that a number moved), two tool calls, non-root UID,
read-only target root, writable reports overlay, readable Git metadata,
disabled network, dropped capabilities, absent ports, read-only container
root, and report path normalization. The harness now blocks on a FIFO-backed
stdin held open by this shell (not the fixed pipe `docker compose run`
inherited before) and polls the response file until every issued request id
has a matching response — or fails loudly, naming the missing id(s), within a
90-second deadline — so the final assertion can no longer be reached on a
harness that silently dropped a response.

## What changed and why (scope: `scripts/verify_container.sh` only)

1. **Stale tool-count assertion.** The adapter now exposes 11 tools (T022
   added `score`). Replaced the bare `!= 10` count check with a set-equality
   check against the expected tool *names*, so a future drift reports exactly
   which tool is missing or unexpected instead of only that a number moved.
2. **Dropped final response.** `docker compose run --rm --no-tty verifier`
   was fed requests through a fixed pipe that closed as soon as the `printf`
   finished; the MCP server exits on stdin EOF before necessarily having
   flushed its last response(s), so the script's own final assertion
   (`for request_id in (3, 4)`) could raise `KeyError` before ever running
   to a real pass/fail. Replaced the pipe with a FIFO whose write end this
   shell holds open (`exec 3>...`) while polling the response file for every
   expected request id, closing the FIFO only once all ids are present (or
   failing loudly, naming the missing id(s), after a 90s deadline).

No changes were made to `Dockerfile`, `compose.yaml`, or `src/` — the
container itself was already verified correct.

## Stage 4 review — P2 fix

**P2 — the timeout path named every request id, not the missing one.** The
first version of the deadline branch did:

```bash
fail "timed out waiting for responses to request ids: ${request_ids[*]}"
```

which always names all four ids regardless of which one(s) actually never
arrived — the same "honest in its parts, uninformative in its headline"
shape this task exists to fix. Confirmed live by the reviewer with a
sabotaged copy missing only the id-4 request.

**Fix**: extracted `missing_response_ids()`, the same set-difference the
poll loop already computed, and had both the poll loop (`have_all_responses`)
and the timeout `fail` message call it, so the deadline path now names only
the request id(s) that are actually still missing. The 90s deadline and the
"do not wait for the container to exit" behavior are unchanged — only the
message on that path changed.

Pinned to both extremes, per the reviewer's instruction:

**1. Unmodified script → PASS, exit 0** (captured 2026-09-16T04:09:55Z):

```text
$ docker compose build --quiet && bash scripts/verify_container.sh
 Image easy-verifier-mcp:0.1.0 Built
 Container easy-verifier-t016-668-verifier-run-3657c864868d Creating
 Container easy-verifier-t016-668-verifier-run-3657c864868d Created
 Container easy-verifier-t016-668-verifier-run-b2769a246255 Creating
 Container easy-verifier-t016-668-verifier-run-b2769a246255 Created
PASS: uid=10001, tools=11, root=read-only, reports=writable, network=none, ports=none, caps=none
exit=0
```

**2. Sabotaged copy with only the id-4 (`write_report`) request line deleted
→ FAIL naming only id 4, exit 1** (captured 2026-09-16T04:10:11Z, `request_ids=(1 2 3 4)`
left unchanged so the script itself still expects all four):

```text
$ timeout 150 bash /tmp/verify_container_sabotage_id4.sh
 Container easy-verifier-t016-18551-verifier-run-bff2b68f2661 Creating
 Container easy-verifier-t016-18551-verifier-run-bff2b68f2661 Created
 Container easy-verifier-t016-18551-verifier-run-ecbf9249f8b5 Creating
 Container easy-verifier-t016-18551-verifier-run-ecbf9249f8b5 Created
FAIL: timed out waiting for response(s) to request id(s): 4
exit=1
```

Only id 4 is named, matching the single request actually deleted; the
deadline still fired at ~90s rather than waiting for `docker compose run`
to exit on its own.

**P3 (fixed, cheap) — the deciding heredoc's `json.loads` was less tolerant
than the poller's.** `have_all_responses`/`missing_response_ids` already
skip a line that fails `json.loads` with `try`/`except JSONDecodeError`;
the final pass/fail heredoc did not, so a torn last line would raise an
opaque traceback from the function that decides pass/fail while the poller
treated the same line as a clean skip. Made the deciding heredoc build its
`messages` dict with the same skip-on-`JSONDecodeError` loop instead of the
walrus-in-dict-comprehension that had no exception handling.

**P3 (accepted as residue, not changed) — `wait "$run_pid" || true` discards
the container's exit status.** A server that crashed after emitting all four
responses would still pass this harness; the payload assertions (tool set,
`isError`, report contents) cover most of the practical failure surface, but
a clean-exit-status check is not asserted separately. Per the reviewer's
scope guidance, left as-is to avoid scope creep into container/process
lifecycle handling beyond this task's charter (harness-fix only).

**Record, not a defect — the dropped response is not really
"nondeterministic".** Both observed drops (id 3 in this session's isolated
repro, id 4 in the Supervisor's reordering test, and now id 4 again in the
sabotage test above) are consistent with a single rule: it is always a
**trailing run** of responses that is lost when stdin hits EOF, and *how
many* trail off depends on how far behind the server's write buffer is at
that moment relative to how many requests were queued after the point where
the pipe closed. Calling this "nondeterministic" in the earlier handback
undersold how reliably it reproduces — it is not random which id drops, it
is always the tail of whatever hadn't been flushed yet.
