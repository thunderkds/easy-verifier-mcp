# TASK_REVIEW — T015: complete CLI adapter

## Evidence

| Check | Result | Notes / output snippet |
|-------|--------|------------------------|
| Acceptance tests | pass | `PYTHONPATH=src python -m pytest tests/test_t015_cli.py -q` -> `10 passed` |
| Full regression suite | pass | `PYTHONPATH=src python -m pytest -q` -> `437 passed` |
| Lint and formatting | pass | `ruff check src tests` and `ruff format --check src tests` both pass |
| Installed console script | pass | Built into an isolated `/tmp` prefix, then `easy-verifier list-dimensions` returned 7 records and `easy-verifier architecture --repo . --scope project` exited 0 |
| MCP parity | pass | The architecture payload is compared with the sibling MCP tool's structured payload for identical arguments |
| Findings input parity | pass | Frozen-clock subprocess test proves `--findings PATH` and stdin use the same operation and emit byte-identical JSON |

The suite used the locally available `mcp` 1.29.0 SDK inherited from T014. Its
`IncompleteFieldDefinitionWarning` is upstream and does not fail the suite.

## Demonstration

**BEFORE** (T011 tracer-bullet CLI):

```text
$ pytest tests/test_t015_cli.py -q
F...FFFFF.
6 failed, 4 passed
```

The old CLI lacked descriptor purposes in help, the `--task` / `--range`
aliases, `write-report`, findings input, and distinct operational failures.

**AFTER**:

```text
$ PYTHONPATH=src python -m pytest tests/test_t015_cli.py -q
..........                                                               [100%]
10 passed, 1 warning in 1.38s

$ easy-verifier list-dimensions
# valid JSON containing 7 dimension records
$ easy-verifier architecture --repo . --scope project >/dev/null
# exit 0
```

**DELTA**: `easy-verifier` now exposes the same seven dimensions, discovery,
combined pack, and report operation as MCP. Results alone go to stdout; input
validation exits 2, operational failures exit 3, and caller-provided findings
can come from a named file or stdin.

## Review notes

- The legacy T001/T012 tests were narrowly updated because they encoded the
  superseded tracer-bullet contract: all failures exited 2 and the adapter was
  forbidden from reading even the explicitly required findings file.
- The CLI reads exactly one caller-selected input file. It does not inspect
  target-repository content; all evidence gathering, budgeting, validation,
  and report generation remain shared-core calls.
- `README.md` still labels the T014/T015 commands as planned. It is intentionally
  untouched because it is outside both guides' surgical file lists; the
  documentation-truth follow-up should remove those stale markers.
- The Claude `code-review` and `verify` skills are unavailable in this Codex
  session, so the bounded review and installed-entry-point verification were
  run directly.
