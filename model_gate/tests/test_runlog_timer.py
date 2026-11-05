import subprocess

import pytest

from experiments.runlog import DirtyRepo, RunLog, read
from experiments.timer import report, stage


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    git = lambda *a: subprocess.run(["git", *a], cwd=r, check=True, capture_output=True)  # noqa: E731
    git("init", "-q")
    (r / "f").write_text("x")
    git("add", "f")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x")
    return r


def test_registro_acrescenta_linhas_com_esquema(repo, tmp_path):
    log = RunLog("r1", model_digest="d" * 64, seed=7, gen={"max_new_tokens": 8}, root=tmp_path, repo=repo)
    log.log("S1", "recusa", 0.5, categoria="Violence")
    log.log("S1", "recusa", 0.25, seed=8)
    rows = read(log.path)
    assert len(rows) == 2 and log.path.name == "r1.jsonl"
    r = rows[0]
    assert set(r) == {
        "run_id", "ts", "model_digest", "git_commit", "dirty", "seed", "gen",
        "instrument", "metric", "value", "extra",
    }
    assert r["dirty"] is False and len(r["git_commit"]) == 40
    assert r["extra"] == {"categoria": "Violence"} and r["seed"] == 7
    assert rows[1]["seed"] == 8


def test_repositorio_sujo(repo, tmp_path):
    (repo / "f").write_text("mudou")
    assert RunLog("r2", root=tmp_path, repo=repo).dirty is True
    with pytest.raises(DirtyRepo):
        RunLog("r3", require_clean=True, root=tmp_path, repo=repo)


def test_timer_grava_no_registro(repo, tmp_path):
    log = RunLog("r4", root=tmp_path, repo=repo)
    with stage("alocar", log) as s:
        buf = bytearray(64 * 2**20)
        buf[-1] = 1
    assert s.result["wall_s"] >= 0 and s.result["peak_rss_gib"] > 0.05
    table = report(read(log.path))
    assert "| alocar |" in table and "total" in table
