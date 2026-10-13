"""T092 - sink hits in test files are listed and cited but not counted.

Both extremes of the test-file predicate are hardwired: a predicate that
calls nothing a test file counts the test hit (2); one that calls everything a
test file leaves nothing to count, so the metric abstains instead of reporting 0.
"""

from __future__ import annotations

from test_t034_security_sinks import SAFE, UNSAFE, pack, sink_metric

from easy_verifier.core import metrics as metrics_module

URL = "https://cwe.mitre.org/data/definitions/89.html"
BOTH = {"app/db.py": UNSAFE, "tests/test_db.py": UNSAFE}


def test_only_the_production_hit_is_counted():
    found = sink_metric(pack(BOTH))
    assert found.outcome == 1
    assert not found.abstained


def test_test_hit_is_listed_tagged_and_stated_as_not_counted():
    found = sink_metric(pack(BOTH))
    assert f"tests/test_db.py:2 CWE-89 ({URL}) [test path]" in found.derivation
    assert f"app/db.py:2 CWE-89 ({URL})" in found.derivation
    assert f"app/db.py:2 CWE-89 ({URL}) [test path]" not in found.derivation
    assert "1 test-path hit(s) are listed and not counted" in found.derivation
    assert found.derivation.startswith("1 dangerous-sink hit(s) in non-test files")


def test_test_hit_is_still_cited():
    found = sink_metric(pack(BOTH))
    assert set(found.computed_from) == {"app/db.py:1-2", "tests/test_db.py:1-2"}


def test_only_a_test_hit_counts_zero_and_is_still_cited():
    found = sink_metric(pack({"app/db.py": SAFE, "tests/test_db.py": UNSAFE}))
    assert found.outcome == 0
    assert "tests/test_db.py:2 CWE-89" in found.derivation
    assert "tests/test_db.py:1-2" in found.computed_from


def test_no_test_hit_means_no_not_counted_sentence():
    found = sink_metric(pack({"app/db.py": UNSAFE}))
    assert "test-path hit(s) are listed" not in found.derivation


def test_only_test_files_scanned_abstains_never_zero():
    found = sink_metric(pack({"tests/test_db.py": UNSAFE}))
    assert found.abstained
    assert "only test files were scanned for sinks" in found.abstention.reason


def test_sabotage_predicate_never_test_counts_two(monkeypatch):
    monkeypatch.setattr(metrics_module, "_is_test_file", lambda *_a, **_k: False)
    assert sink_metric(pack(BOTH)).outcome == 2


def test_sabotage_predicate_always_test_abstains(monkeypatch):
    monkeypatch.setattr(metrics_module, "_is_test_file", lambda *_a, **_k: True)
    found = sink_metric(pack(BOTH))
    assert found.abstained
