# TASK_REVIEW — T034: Security sink patterns per language (CWE-95/78/89)

> Sibling of `tasks/TASK_GUIDE_T034.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t034_security_sinks.py` — 76 tests: 30 original safe/unsafe twins (every language × declared CWE, incl. f-string `execute` → 1 CWE-89, parameterised `%s` → 0), 10 interpolated-string twins (JS/TS template literals, Kotlin, Ruby, PHP) each with a placeholder-off sabotage, comment/string-blanking sabotage, not-after-`.` guard sabotage, sink-excerpt sabotage, per-file cap + warning, truncation, abstention, bad/missing `cwe` rejected, CWE URLs checked against vendored cwe.json, CLI subprocess. Noise check: 74 tracked source files → 0 hits. Supervisor re-run `1084 passed, 2 skipped in 27.11s` |
| Verification command run | ☑ pass | Supervisor 2026-09-28 07:11 UTC: pytest `1084 passed, 2 skipped` (exit 0); `ruff check src tests` → `All checks passed!` (exit 0) |
| Negative cases hold | ☑ pass | Supervisor JS repo: constant template `db.query(`SELECT 1`)` → no hit; the same interpolated call inside a `//` comment → no hit; tagged template, Kotlin `"$5"`, Ruby/PHP single-quoted strings → no hit (tests) |
| verify | ☑ pass | Real CLI 07:11 UTC (stdin closed) on a fresh Node repo `src/users.js`: security `sink_hits_observed` = 3 → `src/users.js:3` CWE-89 (template literal `${id}`), `:5` CWE-89 (string concat), `:7` CWE-95 (`eval`), each citing its CWE page; line 4 constant template and line 1 comment not hit — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed `core/registry.py` (`security_sinks` with required `cwe`, `interpolating_strings`), `core/metric_tables.py` (token compile, `<INTERP>`, not-after-`.`/`>`/`$` guard), `core/tokens.py` (`strip(mark_interpolation=True)`, NUL placeholder, length-preserving, default off so T033 unchanged), `core/metrics.py` (`sink_hits_observed`, evidence-local), `dimensions/security.py` (sink-line excerpts via `read_source`, ≤20/file + warning), 9 curated TOML. Round 1 P1: interpolated-string SQL (AC1 'template string into query(') undetectable because blanking removed interpolation → fixed with the placeholder mechanism (Supervisor ruling on AC1 vs AC3). Ruling (b): CWE-only citation per item accepted. P2 carried: `require('child_process').exec(...)`/destructured `exec` missed (pattern needs `child_process.exec(`); fully qualified calls missed by the guard; bracket-less Ruby calls and prefixed templates missed; no data flow; a literal NUL in code would read as the placeholder. Security inline (Med): values escaped before regex; line cap bounds cost; redact.py and judge.py untouched |
| Full smoke suite still green (no regression) | ☑ pass | full suite 1084 passed, 2 skipped |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend task, no UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Pure backend task, no UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | Pure backend task, no UI |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured 2026-09-28T06:22:07Z on `13cef1c` (no T034 implementation commit exists; working-tree edits were stashed for the run). A real CLI `score` over a scratch git repo whose `app/db.py` holds an f-string SQL `cursor.execute(...)` (CWE-89) and `subprocess.run(cmd, shell=True)` (CWE-78): no metric named `*sink*` exists, the security pack quotes only `pyproject.toml:1-2`, and neither sink line appears anywhere in the output.

```text
$ date -u; git -C /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp-T034 rev-parse --short HEAD
2026-09-28T06:22:07Z
13cef1c
$ cat -n app/db.py (scratch repo)
     1	import sqlite3
     2	import subprocess
     3	
     4	
     5	def find_user(cursor, user):
     6	    cursor.execute(f"SELECT * FROM users WHERE name = '{user}'")
     7	    return cursor.fetchall()
     8	
     9	
    10	def run(cmd):
    11	    return subprocess.run(cmd, shell=True)
$ PYTHONPATH=src .venv/bin/python -c 'main(["score","--repo","<scratch>/sinkrepo","--scope","project"])' > out.json
exit=0
security metric names: ['test_to_source_ratio', 'source_files_without_covering_test', 'assertion_density_per_test', 'assertions_observed', 'redaction_hits_observed', 'redacted_file_share', 'excerpts_observed', 'declared_source_coverage', 'evidence_lines_observed', 'mean_excerpt_lines', 'source_file_share', 'functions_over_ccn_10_share', 'max_function_ccn', 'top_level_import_cycles', 'max_fan_in_changed']
any metric named *sink*: []
excerpts_observed: value=1 abstained=False computed_from=['pyproject.toml:1-2']
occurrences of 'execute(' / 'shell=True' in output: 0 0
```

**AFTER**: re-captured after the Supervisor's AC1/AC3 ruling, on `bdfb0c8` (interpolation mark included). Same scratch repo and command as BEFORE: `sink_hits_observed` = 2 on the security dimension, one hit per sink line with path:line, CWE id and the vendored CWE page; the security pack now quotes `app/db.py:6-6` and `app/db.py:11-11` (excerpts_observed 1 -> 3). The `score` payload carries metrics, not excerpt text, so the literal sink lines still do not appear in it; they are in the pack the metric cites. The security *rating* still abstains (coverage floor) and no rule reads the metric yet -- rules/weights are T035.

```text
$ date -u; git -C /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp-T034 rev-parse --short HEAD
2026-09-28T07:10:31Z
bdfb0c8
$ cat -n app/db.py (scratch repo)
     1	import sqlite3
     2	import subprocess
     3	
     4	
     5	def find_user(cursor, user):
     6	    cursor.execute(f"SELECT * FROM users WHERE name = '{user}'")
     7	    return cursor.fetchall()
     8	
     9	
    10	def run(cmd):
    11	    return subprocess.run(cmd, shell=True)
$ PYTHONPATH=src .venv/bin/python -c 'main(["score","--repo","<scratch>/sinkrepo","--scope","project"])' > out.json
exit=0
security metric names: ['test_to_source_ratio', 'source_files_without_covering_test', 'assertion_density_per_test', 'assertions_observed', 'redaction_hits_observed', 'redacted_file_share', 'excerpts_observed', 'declared_source_coverage', 'evidence_lines_observed', 'mean_excerpt_lines', 'source_file_share', 'functions_over_ccn_10_share', 'max_function_ccn', 'top_level_import_cycles', 'max_fan_in_changed', 'sink_hits_observed']
any metric named *sink*: ['sink_hits_observed']
excerpts_observed: value=3 abstained=False computed_from=['app/db.py:11-11', 'app/db.py:6-6', 'pyproject.toml:1-2']
sink_hits_observed: value=2 abstained=False computed_from=['app/db.py:11-11', 'app/db.py:6-6']
  derivation: 2 dangerous-sink hit(s) in 2 excerpt(s): app/db.py:6 CWE-89 (https://cwe.mitre.org/data/definitions/89.html), app/db.py:11 CWE-78 (https://cwe.mitre.org/data/definitions/78.html); dangerous sinks are the registry's security_sinks tokens (each citing its CWE page), matched textually after the registry's comment and string delimiters are blanked (a string that interpolates keeps one mark at its start) -- no data flow is traced, so a hit is a place to look, not a proven vulnerability; test-path hits are counted and tagged; a lower bound on the repository, since only these excerpts were read
occurrences of 'execute(' / 'shell=True' in output: 0 0
```

Second scratch repo (the ruling's case): a JS template literal with `${id}` passed to `db.query(` hits once as CWE-89; the constant template on line 6 does not.

```text
$ date -u; git rev-parse --short HEAD
2026-09-28T07:10:31Z
bdfb0c8
$ cat -n app/users.js (scratch repo 2, package.json + this file)
     1	async function findUser(db, id) {
     2	  return db.query(`SELECT * FROM users WHERE id = ${id}`);
     3	}
     4	
     5	async function listUsers(db) {
     6	  return db.query(`SELECT * FROM users`);
     7	}
$ PYTHONPATH=src .venv/bin/python -c main(["score","--repo","<scratch>/tplrepo","--scope","project"]) > tpl.json
exit=0
sink_hits_observed: {'abstained': False, 'value': 1} ['app/users.js:2-2']
  derivation: 1 dangerous-sink hit(s) in 1 excerpt(s): app/users.js:2 CWE-89 (https://cwe.mitre.org/data/definitions/89.html); dangerous sinks are the registry's security_sinks tokens (each citing its CWE page), matched textually after the registry's comment and string delimiters are blanked (a string that interpolates keeps one mark at its start) -- no data flow is traced, so a hit is a place to look, not a proven vulnerability; test-path hits are counted and tagged; a lower bound on the repository, since only these excerpts were read
```

**DELTA**: The security dimension now finds eval/exec, shell and string-built SQL sinks — including JS/TS template-literal SQL — in 9 languages, each hit cited with path:line and its CWE page.

**WITNESS**: Supervisor re-ran suite, ruff and a real CLI score on a fresh Node repo on 2026-09-28 (07:11 UTC), independent of the implementing agent.