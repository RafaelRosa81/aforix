from datetime import datetime
from pathlib import Path
import json
import shutil

from aforix.config.loader import load_config


def _project_root_from_config(config_path: Path) -> Path:
    resolved = Path(config_path).resolve()

    for candidate in [resolved.parent, *resolved.parents]:
        if (
            (candidate / ".git").exists()
            or (candidate / "pyproject.toml").exists()
            or (candidate / "src" / "aforix").exists()
        ):
            return candidate

    # Standard Aforix layout:
    # <project>/configs/examples/<config>.yaml
    if (
        resolved.parent.name == "examples"
        and resolved.parent.parent.name == "configs"
    ):
        return resolved.parents[2]

    # Standalone configs outside a detectable repository resolve relative
    # paths from the config location, not from an arbitrary ancestor or cwd.
    return resolved.parent


def _runs_root_from_config(config_path: Path) -> Path:
    config_path = Path(config_path).resolve()
    cfg = load_config(config_path)

    runs_root = Path(cfg.get("paths", {}).get("runs_root", "runs"))
    if runs_root.is_absolute():
        return runs_root.resolve()

    return (_project_root_from_config(config_path) / runs_root).resolve()


def create_run(pipeline_name: str, config_path: Path) -> Path:
    """Create a reproducible run directory under the configured runs root."""

    config_path = Path(config_path).resolve()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = _runs_root_from_config(config_path) / pipeline_name / run_id

    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "logs").mkdir()
    (run_dir / "outputs").mkdir()

    shutil.copy2(config_path, run_dir / "config_used.yaml")

    manifest = {
        "pipeline": pipeline_name,
        "run_id": run_id,
        "config_used": str(run_dir / "config_used.yaml"),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    with open(run_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return run_dir
