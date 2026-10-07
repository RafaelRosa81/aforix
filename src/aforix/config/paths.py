from __future__ import annotations

from pathlib import Path


def config_root_from_path(config_path: Path) -> Path:
    """Resolve the project root used for config-relative paths.

    Repository-local configs anchor at the detected repository root. Configs
    stored directly under <project>/configs or one module directory below it
    (for example configs/examples/main.yaml or configs/sih/sih.yaml) anchor at
    <project> even outside a repository. Other standalone configs anchor at
    the directory containing the config file.
    """
    resolved = Path(config_path).resolve()

    for candidate in [resolved.parent, *resolved.parents]:
        if (
            (candidate / ".git").exists()
            or (candidate / "pyproject.toml").exists()
            or (candidate / "src" / "aforix").exists()
        ):
            return candidate

    if resolved.parent.name == "configs":
        return resolved.parent.parent

    if resolved.parent.parent.name == "configs":
        return resolved.parent.parent.parent

    return resolved.parent
