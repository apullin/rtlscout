"""Every command-line tool is a module of the package (``python -m rtlscout.<module>``); the repository root holds
no scripts."""

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
MODULES = ["run_benchmark", "run_eval", "run_multirun", "run_pipeline", "run_sweep", "batch_eval", "extract_pareto",
           "containers"]
TOOLS = ["run_model", "add_benchmark", "plots.plot_results", "plots.plot_multirun", "plots.plot_pareto_paper",
         "plots.plot_area_delay", "plots.plot_area_delay_with_ref", "plots.visualize_db_run",
         "tools.extract_best_designs", "tools.extract_sweep_pareto", "tools.measure_db_compositions"]


@pytest.mark.parametrize("name", MODULES)
def test_module_has_main_taking_argv(name):
    main = importlib.import_module(f"rtlscout.{name}").main
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])
    assert exit_info.value.code == 0


@pytest.mark.parametrize("name", MODULES + TOOLS)
def test_runs_as_module_from_any_directory(name, tmp_path):
    proc = subprocess.run([sys.executable, "-m", f"rtlscout.{name}", "--help"], cwd=tmp_path, capture_output=True,
                          text=True, env=_env_with_repo_on_path())
    assert proc.returncode == 0 and "usage:" in proc.stdout.lower(), proc.stderr


def test_no_scripts_at_the_repository_root():
    assert sorted(p.name for p in REPO.glob("*.py")) == []


def _env_with_repo_on_path():
    """The package may be importable only through the checkout (tests run without `pip install -e .` too)."""
    import os
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(p for p in (str(REPO), env.get("PYTHONPATH")) if p)
    return env
