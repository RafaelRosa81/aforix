from pathlib import Path
import pandas as pd

from aforix.normalize.registry import NormalizationRegistry
from aforix.normalize.normalizer import normalize_table


# --- Cargar registry ---
registry = NormalizationRegistry(Path("configs/normalization"))

# --- Ruta a UN archivo real de Points ---
input_csv = Path(
    r"D:\Dropbox\MADI\DINAGUA_SL\03-Proces_Info_DIN\04-Codigo\aforix\runs\ingest_flowtracker\20260429_214706\outputs\raw_canonical\flowtracker\Summary/P8_Summary_20251215_115907.csv"
)

# --- Leer datos ---
df_raw = pd.read_csv(input_csv)

print("\n--- RAW COLUMNS ---")
print(df_raw.columns)

# --- Obtener spec ---
spec = registry.get("flowtracker", "Summary")

# --- Normalizar ---
df_norm = normalize_table(df_raw, spec)

print("\n--- NORMALIZED HEAD ---")
print(df_norm.head())

print("\n--- DTYPES ---")
print(df_norm.dtypes)