"""T032 — build-time vendoring of Linguist, OWASP ASVS and MITRE CWE.

Every acceptance criterion in ``tasks/TASK_GUIDE_T032.md`` has at least one
test here. The vendoring script itself performs network I/O and is invoked
manually by a maintainer (see the script's docstring) — these tests exercise
the committed snapshots and the script's structure/parsing, never the network.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
SCRIPT_PATH = REPO_ROOT / "scripts" / "vendor_sources.py"
VENDORED_DIR = SRC_DIR / "easy_verifier" / "registry" / "vendored"

# Banned network-capable stdlib modules under src/ (AC 3).
_BANNED_NETWORK_MODULES = {"socket", "http.client", "urllib.request"}


def _imported_module_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


class TestNoRuntimeNetwork:
    """AC 3: runtime code never imports network modules or the vendor script."""

    def test_no_network_imports_under_src(self):
        offenders = []
        for path in SRC_DIR.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imported = _imported_module_names(tree)
            hit = imported & _BANNED_NETWORK_MODULES
            if hit:
                offenders.append((path, hit))
        assert offenders == [], f"network-capable imports found under src/: {offenders}"

    def test_no_module_under_src_imports_the_vendor_script(self):
        offenders = [
            path
            for path in SRC_DIR.rglob("*.py")
            if "vendor_sources" in path.read_text(encoding="utf-8")
        ]
        assert offenders == []


class TestVendoredSnapshotsExist:
    """AC 1, 4: snapshots are committed, filtered, and small."""

    def test_vendored_dir_exists_with_expected_files(self):
        expected = {
            "linguist.json",
            "asvs.json",
            "cwe.json",
            "NOTICE",
            "CHECKSUMS.sha256",
        }
        actual = {p.name for p in VENDORED_DIR.iterdir()}
        assert expected <= actual

    def test_total_size_under_budget(self):
        total = sum(p.stat().st_size for p in VENDORED_DIR.iterdir())
        assert total < 500 * 1024, f"vendored snapshot total is {total} bytes"

    def test_linguist_json_has_only_needed_fields(self):
        data = json.loads((VENDORED_DIR / "linguist.json").read_text(encoding="utf-8"))
        assert "languages" in data
        assert "Python" in data["languages"]
        python_entry = data["languages"]["Python"]
        assert set(python_entry) == {"extensions", "filenames"}
        assert ".py" in python_entry["extensions"]

    def test_asvs_json_has_only_needed_fields(self):
        data = json.loads((VENDORED_DIR / "asvs.json").read_text(encoding="utf-8"))
        assert "requirements" in data
        assert len(data["requirements"]) > 0
        req = data["requirements"][0]
        assert set(req) == {"id", "title", "chapter", "url"}
        assert req["url"].startswith("https://")

    def test_cwe_json_has_only_needed_fields(self):
        data = json.loads((VENDORED_DIR / "cwe.json").read_text(encoding="utf-8"))
        assert "weaknesses" in data
        assert len(data["weaknesses"]) > 0
        weakness = data["weaknesses"][0]
        assert set(weakness) == {"id", "name", "url"}
        assert weakness["url"].startswith("https://cwe.mitre.org/")


class TestSnapshotMetadata:
    """AC 2: each vendored file records source URL, version/commit, retrieval
    date and licence (SPDX id + attribution)."""

    @pytest.mark.parametrize("filename", ["linguist.json", "asvs.json", "cwe.json"])
    def test_meta_block_present(self, filename):
        data = json.loads((VENDORED_DIR / filename).read_text(encoding="utf-8"))
        meta = data["meta"]
        assert meta["source_url"].startswith("https://")
        assert meta["retrieved"]
        assert meta["license"]
        assert meta["attribution"]
        assert "pinned_commit" in meta or "pinned_version" in meta

    def test_notice_file_mentions_all_three_licenses(self):
        notice = (VENDORED_DIR / "NOTICE").read_text(encoding="utf-8")
        assert "MIT" in notice
        assert "CC-BY-SA-4.0" in notice or "CC BY-SA" in notice
        assert "MITRE" in notice


class TestCheckMode:
    """AC 1, 4 + Edge Case Checklist: --check verifies committed snapshots
    against recorded checksums without any network access."""

    def test_check_passes_against_committed_snapshots(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "OK" in result.stdout

    def test_check_fails_on_tampered_snapshot(self, tmp_path, monkeypatch):
        # Sabotage: copy the vendored tree, corrupt one file's bytes, point
        # the script's module-level path constants at the copy, and confirm
        # --check fails naming the tampered file.
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "vendor_sources_sabotage", SCRIPT_PATH
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        sabotage_dir = tmp_path / "vendored"
        sabotage_dir.mkdir()
        for p in VENDORED_DIR.iterdir():
            (sabotage_dir / p.name).write_bytes(p.read_bytes())

        cwe_path = sabotage_dir / "cwe.json"
        cwe_path.write_bytes(cwe_path.read_bytes() + b"\ntampered")

        module.VENDORED_DIR = sabotage_dir
        module.CHECKSUMS_FILE = sabotage_dir / "CHECKSUMS.sha256"

        exit_code = module.check()
        assert exit_code == 1


class TestLinguistParser:
    """The purpose-built languages.yml reader (not a general YAML parser)."""

    def _load_parser(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "vendor_sources_parser", SCRIPT_PATH
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_parses_extensions_and_filenames(self):
        module = self._load_parser()
        sample = (
            "Python:\n"
            "  type: programming\n"
            "  color: \"#3572A5\"\n"
            "  extensions:\n"
            "  - \".py\"\n"
            "  - \".pyi\"\n"
            "  filenames:\n"
            "  - \"wscript\"\n"
            "Go:\n"
            "  type: programming\n"
            "  extensions:\n"
            "  - \".go\"\n"
        )
        result = module._parse_languages_yml(sample)
        assert result["Python"]["extensions"] == [".py", ".pyi"]
        assert result["Python"]["filenames"] == ["wscript"]
        assert result["Go"]["extensions"] == [".go"]

    def test_language_with_no_extensions_or_filenames_is_dropped(self):
        module = self._load_parser()
        sample = "Empty Group:\n  type: programming\n  color: \"#000000\"\n"
        result = module._parse_languages_yml(sample)
        assert "Empty Group" not in result


class TestValidatorsFailLoudlyOnFormatDrift:
    """Stage 4 P1: post-extraction sanity assertions must fail loudly, before
    any file is written, when an upstream source drifts from its expected
    shape — never degrade quietly."""

    def _load_module(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "vendor_sources_validators", SCRIPT_PATH
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # --- Linguist -----------------------------------------------------

    def test_linguist_validator_passes_on_healthy_input(self):
        module = self._load_module()
        languages = {
            f"Lang{i}": {"extensions": [f".l{i}"], "filenames": []} for i in range(500)
        }
        languages["Python"] = {"extensions": [".py"], "filenames": []}
        languages["Kotlin"] = {"extensions": [".kt"], "filenames": []}
        languages["Go"] = {"extensions": [".go"], "filenames": []}
        languages["C++"] = {"extensions": [".cpp"], "filenames": []}
        module._validate_linguist(languages)  # must not raise

    def test_linguist_validator_fails_on_too_few_languages(self):
        module = self._load_module()
        languages = {"Python": {"extensions": [".py"], "filenames": []}}
        with pytest.raises(module.UpstreamFormatError, match="500"):
            module._validate_linguist(languages)

    def test_linguist_validator_fails_when_reformatted_yaml_yields_no_extensions(self):
        # Simulates the real degradation mode: a reformatted languages.yml
        # parses without a Python exception but the purpose-built line
        # parser silently extracts nothing useful.
        module = self._load_module()
        sample = "Python:\n  type: programming\n  color: \"#3572A5\"\n"
        languages = module._parse_languages_yml(sample)
        with pytest.raises(module.UpstreamFormatError):
            module._validate_linguist(languages)

    def test_linguist_validator_fails_when_required_language_missing(self):
        module = self._load_module()
        languages = {
            f"Lang{i}": {"extensions": [f".l{i}"], "filenames": []} for i in range(600)
        }
        # No Python/Kotlin/Go/C++ present.
        with pytest.raises(module.UpstreamFormatError, match="Python"):
            module._validate_linguist(languages)

    # --- ASVS -----------------------------------------------------------

    def test_asvs_validator_passes_on_healthy_input(self):
        module = self._load_module()
        requirements = [
            {"id": f"V1.1.{i}", "title": "t", "chapter": "c", "url": "https://x"}
            for i in range(300)
        ]
        module._validate_asvs(requirements)  # must not raise

    def test_asvs_validator_fails_on_too_few_requirements(self):
        module = self._load_module()
        requirements = [
            {"id": f"V1.1.{i}", "title": "t", "chapter": "c", "url": "https://x"}
            for i in range(10)
        ]
        with pytest.raises(module.UpstreamFormatError, match="300"):
            module._validate_asvs(requirements)

    def test_asvs_validator_fails_on_missing_field(self):
        module = self._load_module()
        requirements = [
            {"id": f"V1.1.{i}", "title": "t", "chapter": "c", "url": "https://x"}
            for i in range(300)
        ]
        requirements[5]["title"] = ""
        with pytest.raises(
            module.UpstreamFormatError, match="missing id/title/chapter"
        ):
            module._validate_asvs(requirements)

    # --- CWE --------------------------------------------------------------

    def test_cwe_validator_passes_on_healthy_input(self):
        module = self._load_module()
        weaknesses = [
            {"id": str(i), "name": "n", "url": "https://x"} for i in range(1000)
        ]
        weaknesses += [
            {"id": "78", "name": "n", "url": "https://x"},
            {"id": "89", "name": "n", "url": "https://x"},
            {"id": "95", "name": "n", "url": "https://x"},
            {"id": "798", "name": "n", "url": "https://x"},
        ]
        module._validate_cwe(weaknesses)  # must not raise

    def test_cwe_validator_fails_on_too_few_weaknesses(self):
        module = self._load_module()
        weaknesses = [
            {"id": str(i), "name": "n", "url": "https://x"} for i in range(10)
        ]
        with pytest.raises(module.UpstreamFormatError, match="900"):
            module._validate_cwe(weaknesses)

    def test_cwe_validator_fails_when_missing_required_id(self):
        module = self._load_module()
        # 900+ weaknesses, but 89 (SQL injection) is missing.
        weaknesses = [
            {"id": str(i), "name": "n", "url": "https://x"}
            for i in range(1, 1000)
            if i != 89
        ]
        with pytest.raises(module.UpstreamFormatError, match="89"):
            module._validate_cwe(weaknesses)

    # --- fetch_* wiring: validator runs before any file is written --------

    def test_fetch_linguist_raises_before_returning_on_degraded_input(
        self, monkeypatch
    ):
        module = self._load_module()
        degraded = b"Python:\n  type: programming\n"
        monkeypatch.setattr(module, "_fetch", lambda url: degraded)
        with pytest.raises(module.UpstreamFormatError):
            module.fetch_linguist()

    def test_fetch_asvs_raises_before_returning_on_degraded_input(self, monkeypatch):
        module = self._load_module()
        degraded = json.dumps(
            {
                "requirements": [
                    {"req_id": "V1.1.1", "req_description": "t", "chapter_name": "c"}
                    for _ in range(5)
                ]
            }
        ).encode("utf-8")
        monkeypatch.setattr(module, "_fetch", lambda url: degraded)
        with pytest.raises(module.UpstreamFormatError, match="300"):
            module.fetch_asvs()


class TestChecksumsFileIntegrity:
    def test_checksums_match_recorded_sha256(self):
        checksums_text = (VENDORED_DIR / "CHECKSUMS.sha256").read_text(encoding="utf-8")
        for line in checksums_text.splitlines():
            if not line.strip():
                continue
            digest, name = line.split("  ", 1)
            actual = hashlib.sha256((VENDORED_DIR / name).read_bytes()).hexdigest()
            assert actual == digest, f"{name} checksum mismatch"
