from pathlib import Path
import yaml


class NormalizationRegistry:
    def __init__(self, registry_dir: Path):
        self.registry_dir = Path(registry_dir)
        self._specs = {}
        self.load()

    def load(self):
        for path in self.registry_dir.glob("*.yaml"):
            with open(path, "r", encoding="utf-8") as f:
                spec = yaml.safe_load(f)

            instrument = spec["instrument"]

            for table_name, table_spec in spec["tables"].items():
                key = (instrument, table_name)
                self._specs[key] = table_spec

    def get(self, instrument: str, table_name: str) -> dict:
        key = (instrument, table_name)

        if key not in self._specs:
            raise KeyError(
                f"No normalization spec found for instrument={instrument}, table={table_name}"
            )

        return self._specs[key]