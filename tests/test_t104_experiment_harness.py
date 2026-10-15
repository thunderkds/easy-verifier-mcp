"""T104 — experiment harness: Laya vs LLM on detect-gate pick questions.

Covers AC1 (determinism, label always in candidates, cap 20), AC2 (over-budget
handling counted), AC3 (accuracy/ECE on a hand-computed toy file) and AC10
(the model is a parameter: unknown model and missing key exit non-zero naming
it, ``jev`` refuses a non-allow-listed repo, ``random``/``heuristic`` write the
shared answer format). Runs without torch or laya installed.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HARNESS = REPO_ROOT / "experiments" / "t104_laya"
sys.path.insert(0, str(HARNESS))

import build_dataset  # noqa: E402
import evaluate  # noqa: E402
import run  # noqa: E402


def _write(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _words(text: str) -> int:
    return len(text.split())


def _repo(tmp_path: Path, extra: int = 30) -> Path:
    files = {
        "README.md": "# Demo project\n",
        "docs/architecture.md": "# Architecture\n",
        "docs/spec-task.md": "# Spec and tasks\n",  # spec-doc AND task-breakdown
        "ruff-lint.toml": "[lint]\n",  # lint-config, config shape
        ".editorconfig": "root = true\n",  # format-config, no config extension
        ".env.local.yaml": "TOKEN: FAKEfake\n",  # secret-bearing, yaml-shaped
        "secrets.yaml": "token: FAKEfake\n",  # secret-bearing, owned by no role
        "settings.yaml": "a: 1\n",
        "main.py": "print('hi')\n",
    }
    for index in range(extra):
        files[f"notes/n{index:02d}.md"] = f"# Note {index}\n"
    return _write(tmp_path / "repo", files)


def _build(repo: Path, **kwargs):
    kwargs.setdefault("count_tokens", _words)
    return build_dataset.build_questions(repo, "demo", **kwargs)


# ---------------------------------------------------------------------------
# AC1 — dataset builder
# ---------------------------------------------------------------------------


def test_builder_is_deterministic_byte_for_byte(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    first, _ = _build(repo)
    second, _ = _build(repo)
    out_a, out_b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    build_dataset.write_jsonl(out_a, first)
    build_dataset.write_jsonl(out_b, second)
    assert out_a.read_bytes() == out_b.read_bytes()
    assert out_a.read_bytes()  # not vacuously equal


def test_label_always_in_candidates_and_cap_20(tmp_path: Path) -> None:
    questions, stats = _build(_repo(tmp_path))
    by_role = {q["role"]: q for q in questions}
    assert by_role["readme"]["label"] == "README.md"
    assert by_role["architecture-doc"]["label"] == "docs/architecture.md"
    assert by_role["lint-config"]["label"] == "ruff-lint.toml"
    for question in questions:
        paths = [c["path"] for c in question["candidates"]]
        assert question["label"] in paths
        assert 2 <= len(paths) <= build_dataset.MAX_CANDIDATES == 20
        assert len(set(paths)) == len(paths)
    # 30 notes + other docs exceed the cap: the doc questions hit exactly 20.
    assert len(by_role["readme"]["candidates"]) == 20
    assert stats["questions"] == len(questions)


def test_candidate_order_is_shuffled_not_sorted(tmp_path: Path) -> None:
    questions, _ = _build(_repo(tmp_path))
    readme = next(q for q in questions if q["role"] == "readme")
    paths = [c["path"] for c in readme["candidates"]]
    assert paths != sorted(paths)
    # A different seed gives a different order over the same set.
    other, _ = _build(_repo(tmp_path / "x"), seed=7)
    other_paths = [c["path"] for c in next(q for q in other if q["role"] == "readme")[
        "candidates"
    ]]
    assert sorted(other_paths) == sorted(paths) and other_paths != paths


def test_same_file_labels_two_roles_both_kept(tmp_path: Path) -> None:
    questions, _ = _build(_repo(tmp_path))
    labels = {q["role"]: q["label"] for q in questions}
    assert labels["spec-doc"] == "docs/spec-task.md"
    assert labels["task-breakdown"] == "docs/spec-task.md"


def test_label_outside_shape_is_counted_and_excluded(tmp_path: Path) -> None:
    questions, stats = _build(_repo(tmp_path))
    assert "format-config" not in {q["role"] for q in questions}
    assert stats["label_outside_shape"] >= 1
    assert "format-config" in stats["label_outside_shape_roles"]


def test_secret_bearing_files_are_never_candidates(tmp_path: Path) -> None:
    questions, _ = _build(_repo(tmp_path))
    every = {c["path"] for q in questions for c in q["candidates"]}
    assert ".env.local.yaml" not in every
    assert "secrets.yaml" not in every  # excluded by eligibility, not ownership
    assert "settings.yaml" in every  # the same shape is otherwise offered


def test_trivial_role_with_one_candidate_is_counted(tmp_path: Path) -> None:
    repo = _write(tmp_path / "r", {"README.md": "# Only\n", "main.py": "x = 1\n"})
    questions, stats = _build(repo)
    assert questions == []
    assert stats["trivial"] == 1
    assert stats["filled_roles"] >= 1


def test_repo_with_zero_filled_roles_is_not_an_error(tmp_path: Path) -> None:
    repo = _write(tmp_path / "r", {"main.py": "x = 1\n"})
    questions, stats = _build(repo)
    assert questions == [] and stats["questions"] == 0


def test_non_latin_paths_are_counted(tmp_path: Path) -> None:
    repo = _write(
        tmp_path / "r",
        {"README.md": "# R\n", "ドキュメント/説明.md": "# 説明\n"},
    )
    questions, stats = _build(repo)
    assert len(questions) == 1
    assert questions[0]["non_latin"] is True
    assert stats["non_latin"] == 1


# ---------------------------------------------------------------------------
# AC2 — token budget
# ---------------------------------------------------------------------------


def test_over_budget_drops_furthest_candidates_and_counts_them(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    full, _ = _build(repo)
    full_readme = next(q for q in full if q["role"] == "readme")
    full_size = _words(build_dataset.render_question(full_readme))
    questions, stats = _build(repo, budget=full_size - 10)
    readme = next(q for q in questions if q["role"] == "readme")
    assert _words(build_dataset.render_question(readme)) <= full_size - 10
    assert readme["label"] in [c["path"] for c in readme["candidates"]]
    assert readme["dropped_for_budget"] > 0
    assert stats["truncated_questions"] >= 1
    assert stats["dropped_candidates"] >= readme["dropped_for_budget"]
    # The dropped ones are the furthest from the label in sorted-path order.
    ordered = sorted(c["path"] for c in full_readme["candidates"])
    kept = {c["path"] for c in readme["candidates"]}
    gone = [p for p in ordered if p not in kept]
    kept_far = max(abs(ordered.index(p) - ordered.index("README.md")) for p in kept)
    assert all(
        abs(ordered.index(p) - ordered.index("README.md")) >= kept_far for p in gone
    )


def test_question_that_cannot_fit_is_skipped_and_counted(tmp_path: Path) -> None:
    questions, stats = _build(_repo(tmp_path), budget=3)
    assert questions == []
    assert stats["skipped_over_budget"] == stats["candidate_questions"] > 0


def test_split_loro_holds_out_one_repo_and_dedupes_identical_questions() -> None:
    def q(repo: str, role: str, label: str) -> dict:
        return {
            "id": f"{repo}:{role}",
            "repo": repo,
            "role": role,
            "label": label,
            "candidates": [
                {"path": label, "heading": ""},
                {"path": "x.md", "heading": ""},
            ],
        }

    questions = [q("a", "readme", "README.md"), q("b", "readme", "README.md"),
                 q("b", "spec-doc", "SPEC.md"), q("c", "readme", "docs/R.md")]
    train, test, deduped = build_dataset.split_loro(questions, "a")
    assert [x["repo"] for x in test] == ["a"]
    assert {x["id"] for x in train} == {"b:spec-doc", "c:readme"}
    assert deduped == 1


def test_questions_only_strips_labels() -> None:
    record = {"id": "a:readme", "repo": "a", "role": "readme", "label": "README.md",
              "candidates": [{"path": "README.md", "heading": ""}]}
    (stripped,) = build_dataset.questions_only([record])
    assert "label" not in stripped and stripped["id"] == "a:readme"
    assert "label" in record  # input untouched


# ---------------------------------------------------------------------------
# AC3 — evaluator on a hand-computed toy file
# ---------------------------------------------------------------------------


def _toy() -> tuple[list[dict], list[dict]]:
    cands = [{"path": p, "heading": ""} for p in ("A", "B", "C")]
    questions = [
        {"id": "q1", "repo": "a", "label": "A", "candidates": cands},
        {"id": "q2", "repo": "a", "label": "A", "candidates": cands},
        {"id": "q3", "repo": "b", "label": "B", "candidates": cands},
        {"id": "q4", "repo": "b", "label": "C", "candidates": cands},
    ]
    answers = [
        {"id": "q1", "choice": "A", "confidence": 0.9, "latency_ms": 10},
        {"id": "q2", "choice": "B", "confidence": 0.9, "latency_ms": 20},
        {"id": "q3", "choice": "B", "confidence": 0.6, "latency_ms": 30},
        {"id": "q4", "choice": "A", "confidence": 0.3, "latency_ms": 40},
    ]
    return questions, answers


def test_evaluator_accuracy_ece_latency_coverage_by_hand() -> None:
    questions, answers = _toy()
    report = evaluate.score(questions, answers)
    overall = report["overall"]
    assert overall["n"] == 4
    assert overall["accuracy"] == pytest.approx(0.5)
    # bins: 0.9 -> |0.5-0.9|*2/4 = 0.2; 0.6 -> |1-0.6|/4 = 0.1; 0.3 -> 0.3/4
    assert overall["ece"] == pytest.approx(0.375)
    assert overall["p50_ms"] == 20 and overall["p95_ms"] == 40
    assert overall["coverage_at_0_8"] == pytest.approx(0.5)
    assert overall["accuracy_at_0_8"] == pytest.approx(0.5)
    per_repo = report["per_repo"]
    assert per_repo["a"]["ece"] == pytest.approx(0.4)
    assert per_repo["b"]["ece"] == pytest.approx(0.35)
    assert per_repo["b"]["accuracy"] == pytest.approx(0.5)


def test_evaluator_counts_missing_and_invalid_answers_as_wrong() -> None:
    questions, answers = _toy()
    answers = [a for a in answers if a["id"] != "q1"]  # q1 missing
    answers[0] = dict(answers[0], choice="not-a-candidate")  # q2 invalid
    overall = evaluate.score(questions, answers)["overall"]
    assert overall["missing"] == 1 and overall["invalid"] == 1
    assert overall["accuracy"] == pytest.approx(0.25)


def test_evaluator_latency_absent_is_reported_not_invented() -> None:
    questions, answers = _toy()
    answers = [dict(a, latency_ms=None) for a in answers]
    overall = evaluate.score(questions, answers)["overall"]
    assert overall["p50_ms"] is None and overall["p95_ms"] is None


def test_evaluator_imports_no_torch() -> None:
    probe = (
        f"import sys; sys.path.insert(0, {str(HARNESS)!r}); import evaluate, run, "
        "backends; assert 'torch' not in sys.modules and 'laya' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


# ---------------------------------------------------------------------------
# AC10 — the model is a parameter
# ---------------------------------------------------------------------------


def _questions_file(tmp_path: Path, repo_alias: str = "demo") -> Path:
    questions, _ = build_dataset.build_questions(
        _repo(tmp_path), repo_alias, count_tokens=_words
    )
    path = tmp_path / "questions.jsonl"
    build_dataset.write_jsonl(path, questions)
    return path


def test_unknown_model_exits_non_zero_naming_it(tmp_path: Path, capsys) -> None:
    questions = _questions_file(tmp_path)
    code = run.main(
        ["--model", "gpt-wizard", "--questions", str(questions),
         "--out", str(tmp_path / "out.jsonl")]
    )
    assert code != 0
    assert "gpt-wizard" in capsys.readouterr().err
    assert not (tmp_path / "out.jsonl").exists()


def test_jev_missing_key_exits_non_zero_naming_it(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    questions = _questions_file(tmp_path, "easy-verifier-mcp")
    code = run.main(
        ["--model", "jev", "--questions", str(questions),
         "--out", str(tmp_path / "out.jsonl")]
    )
    assert code != 0
    assert "TYPESAFE_API_KEY" in capsys.readouterr().err


def test_jev_refuses_a_repo_not_on_the_public_allow_list(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "FAKEfake")
    monkeypatch.setenv("TYPESAFE_BASE_URL", "https://example.invalid")

    def no_network(*_args, **_kwargs):
        raise AssertionError("network call attempted for a private repo")

    monkeypatch.setattr("urllib.request.urlopen", no_network)
    questions = _questions_file(tmp_path, "private-alias")
    code = run.main(
        ["--model", "jev", "--questions", str(questions),
         "--out", str(tmp_path / "out.jsonl")]
    )
    assert code != 0
    err = capsys.readouterr().err
    assert "private-alias" in err and "allow-list" in err
    assert not (tmp_path / "out.jsonl").exists()


def test_jev_allow_list_is_the_public_fixture_only() -> None:
    from backends import jev_backend

    assert frozenset({"easy-verifier-mcp"}) == jev_backend.JevBackend.ALLOWED_REPOS


@pytest.mark.parametrize("model", ["random", "heuristic"])
def test_simple_backends_write_the_shared_answer_format(
    tmp_path: Path, model: str
) -> None:
    questions_path = _questions_file(tmp_path)
    out = tmp_path / f"{model}.jsonl"
    code = run.main(["--model", model, "--questions", str(questions_path),
                     "--out", str(out)])
    assert code == 0
    questions = evaluate.load_jsonl(questions_path)
    answers = evaluate.load_jsonl(out)
    assert [a["id"] for a in answers] == [q["id"] for q in questions]
    for question, answer in zip(questions, answers, strict=True):
        assert set(answer) == {"id", "model", "choice", "confidence", "latency_ms"}
        assert answer["model"] == model
        assert answer["choice"] in {c["path"] for c in question["candidates"]}
        assert 0.0 <= answer["confidence"] <= 1.0
        assert answer["latency_ms"] >= 0
    # The evaluator scores any backend's file unchanged.
    assert evaluate.score(questions, answers)["overall"]["n"] == len(questions)


def test_random_backend_is_seeded_and_reports_one_over_k(tmp_path: Path) -> None:
    questions_path = _questions_file(tmp_path)
    outs = []
    for name in ("a", "b"):
        out = tmp_path / f"{name}.jsonl"
        assert run.main(["--model", "random", "--questions", str(questions_path),
                         "--out", str(out)]) == 0
        outs.append([a["choice"] for a in evaluate.load_jsonl(out)])
    assert outs[0] == outs[1]
    questions = evaluate.load_jsonl(questions_path)
    answers = evaluate.load_jsonl(tmp_path / "a.jsonl")
    for question, answer in zip(questions, answers, strict=True):
        assert answer["confidence"] == pytest.approx(1 / len(question["candidates"]))


def test_heuristic_prefers_the_role_named_file(tmp_path: Path) -> None:
    questions_path = _questions_file(tmp_path)
    out = tmp_path / "h.jsonl"
    assert run.main(["--model", "heuristic", "--questions", str(questions_path),
                     "--out", str(out)]) == 0
    answers = {a["id"]: a["choice"] for a in evaluate.load_jsonl(out)}
    assert answers["demo:readme"] == "README.md"
    assert answers["demo:architecture-doc"] == "docs/architecture.md"


def test_every_registered_model_is_lazily_importable_by_name() -> None:
    from backends import REGISTRY

    assert set(REGISTRY) == {"random", "heuristic", "laya", "laya-ft", "jev"}
    assert all(":" in target for target in REGISTRY.values())


def test_runner_cli_runs_end_to_end_without_ml_dependencies(tmp_path: Path) -> None:
    questions_path = _questions_file(tmp_path)
    out = tmp_path / "cli.jsonl"
    completed = subprocess.run(
        [sys.executable, str(HARNESS / "run.py"), "--model", "random",
         "--questions", str(questions_path), "--out", str(out)],
        capture_output=True, text=True, check=False, stdin=subprocess.DEVNULL,
    )
    assert completed.returncode == 0, completed.stderr
    assert out.read_text(encoding="utf-8").count("\n") == len(
        evaluate.load_jsonl(questions_path)
    )
    unknown = subprocess.run(
        [sys.executable, str(HARNESS / "run.py"), "--model", "nope",
         "--questions", str(questions_path), "--out", str(tmp_path / "x.jsonl")],
        capture_output=True, text=True, check=False, stdin=subprocess.DEVNULL,
    )
    assert unknown.returncode != 0 and "nope" in unknown.stderr
