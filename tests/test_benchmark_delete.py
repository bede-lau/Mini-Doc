"""delete_run: directory removal + traversal guard."""
import pytest

from packages.core.evaluation.benchmark import delete_run


class _Settings:
    def __init__(self, results_dir):
        self.results_dir = results_dir


def test_delete_run_removes_directory_and_reports_files(tmp_path):
    results = tmp_path / "results"
    run_dir = results / "run_001"
    run_dir.mkdir(parents=True)
    (run_dir / "scores.csv").write_text("question_id,hit_at_1\nq1,1\n", encoding="utf-8")
    (run_dir / "summary.md").write_text("# run_001", encoding="utf-8")

    res = delete_run("run_001", settings=_Settings(results))

    assert res["deleted"] is True
    assert res["run_id"] == "run_001"
    assert any(p.endswith("scores.csv") for p in res["removed_files"])
    assert not run_dir.exists()


def test_delete_run_rejects_invalid_and_traversal_ids(tmp_path):
    results = tmp_path / "results"
    (results / "run_001").mkdir(parents=True)
    s = _Settings(results)

    with pytest.raises(ValueError):
        delete_run("../escape", settings=s)        # path traversal
    with pytest.raises(ValueError):
        delete_run("bad/id", settings=s)           # path separator
    with pytest.raises(ValueError):
        delete_run("run 002", settings=s)          # whitespace


def test_delete_run_missing_is_404(tmp_path):
    with pytest.raises(FileNotFoundError):
        delete_run("run_999", settings=_Settings(tmp_path / "results"))
