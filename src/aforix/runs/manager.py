from datetime import datetime
from pathlib import Path
import json
import shutil


def create_run(pipeline_name: str, config_path: Path) -> Path:
    """Create a reproducible run directory."""

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path("runs") / pipeline_name / run_id

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