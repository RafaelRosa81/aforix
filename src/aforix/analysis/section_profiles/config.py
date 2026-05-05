from pathlib import Path
from aforix.config.loader import load_config

def load_section_profiles_config(config_path: Path) -> dict:
    cfg = load_config(config_path)
    return cfg.get('analysis', {}).get('section_profiles', {})
