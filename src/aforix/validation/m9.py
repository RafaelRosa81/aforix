"""Validation of normalized M9 transects without inventing discrete verticals."""
from pathlib import Path
import numpy as np
import pandas as pd

KEYS = ["instrument", "station_id", "measurement_date", "measurement_time", "source_file"]
SUMMARY_NUMERIC = ["q_total_m3s", "area_total_m2", "width_total_m", "sample_count",
                   "wetted_perimeter_m", "hydraulic_radius_m"]
POINT_NUMERIC = ["sample_number", "distance_m", "width_m", "depth_m",
                 "velocity_mean_m_s", "q_cumulative_m3s", "q_increment_m3s"]


# Each diagnostic states the limitation and a concrete next action.
GUIDANCE = {
    "missing_table": ("Falta una tabla necesaria para comprobar el aforo", "Revisar el manifiesto de ingesta y regenerar agrupacion y normalizacion del MAT afectado"),
    "missing_columns": ("El esquema no contiene todos los campos necesarios", "Revisar la configuracion de normalizacion M9 y regenerar la tabla; no crear valores de relleno"),
    "identity": ("No se puede vincular el registro de forma inequivoca con su aforo", "Revisar estacion, fecha, hora y source_file en el origen y regenerar los datos"),
    "finite": ("El campo no contiene un numero utilizable; los calculos que dependen de el no pueden validarse", "Comparar el campo con el MAT y su exportacion en RiverSurveyor; corregir el origen o el mapeo si procede y reingerir. Si el dato no existe, mantenerlo vacio y pendiente de revision"),
    "duplicate": ("Varias filas tienen la misma identidad de aforo o muestra", "Comparar source_file y sample_number y revisar los manifiestos; regenerar en una carpeta aislada para descartar salidas antiguas. No eliminar ni promediar filas automaticamente"),
    "range": ("El valor incumple el rango requerido por este campo", "Revisar unidades y valores en el MAT y la normalizacion; corregir la causa y regenerar, sin sustituir el dato por cero"),
    "integer": ("El contador o numero de muestra debe ser entero", "Comparar la numeracion con el origen y regenerar los registros afectados"),
    "missing_pair": ("Summary y Points no identifican el mismo conjunto de aforos", "Regenerar ambas tablas desde la misma ingesta y comprobar source_file"),
    "sample_count": ("La cantidad de Points no coincide con la declarada en Summary", "Comparar las muestras con el MAT y regenerar ambas tablas desde la misma version"),
    "sample_sequence": ("La numeracion contiene huecos, repeticiones o un inicio distinto de 1", "Revisar el MAT y el manifiesto de ingesta; regenerar sin renumerar ni eliminar muestras manualmente"),
    "width": ("El ancho de Points y Summary no coincide o no es utilizable", "Revisar trayectoria, distancias a margenes y campos faltantes; regenerar ambas tablas desde el mismo MAT"),
    "position": ("Una distancia queda fuera del ancho declarado de la seccion", "Revisar origen, orientacion, unidades y margenes de la trayectoria; corregir la causa sin recortar posiciones"),
    "ive_positions": ("El motor IVE requiere una posicion distinta por vertical; varias muestras comparten distancia y pueden tener distinta profundidad o velocidad", "Revisar esas muestras en Points y la trayectoria original. Si hay un error de origen, corregirlo y reingerir; si las repeticiones son reales, conservarlas e informar IVE no disponible. Agrupar o seleccionar muestras requiere un criterio validado; no se promedia automaticamente"),
    "discharge": ("El caudal acumulado final no coincide con el caudal de Summary o falta un valor", "Comparar ambos campos con el mismo MAT y revisar que no se mezclaron versiones; regenerar sin ajustar artificialmente el caudal"),
    "increments": ("Los incrementos no reproducen las diferencias del caudal acumulado", "Revisar orden, muestras faltantes y version de origen; regenerar Points desde el MAT"),
    "radius": ("El radio no coincide con area/perimetro mojado o falta alguno de los datos", "Revisar primero area y perimetro en Summary y el MAT; corregir la causa y regenerar. Si falta el area, conservar el radio vacio"),
}


def validate_m9(summary: pd.DataFrame | None, points: pd.DataFrame | None) -> pd.DataFrame:
    """Return issues only; an empty report means all implemented checks passed.

    Missing IVE inputs are reported for review, not filled or silently discarded.
    Q_mid is deliberately not equated with the manufacturer's Summary discharge.
    """
    rows = []

    def issue(table, rule, message, source=""):
        reason, action = GUIDANCE[rule]
        message = f"Que sucede: {message}. Razon: {reason}. Accion: {action}."
        rows.append(dict(table=table, instrument="m9", source_file=source,
                         rule=rule, status="inconsistent", message=message))

    tables = {}
    for name, frame, numeric in (("Summary", summary, SUMMARY_NUMERIC),
                                  ("Points", points, POINT_NUMERIC)):
        if frame is None or frame.empty:
            issue(name, "missing_table", "No hay registros M9 disponibles")
            continue
        missing = set(KEYS + numeric) - set(frame.columns)
        if missing:
            issue(name, "missing_columns", ", ".join(sorted(missing)))
            continue
        df = frame.copy()
        blank_keys = df[KEYS].isna() | df[KEYS].astype(str).apply(lambda col: col.str.strip().eq(""))
        if blank_keys.any().any():
            issue(name, "identity", "Faltan datos de identificacion del aforo")
        for col in numeric:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            if not np.isfinite(df[col].to_numpy(dtype=float)).all():
                issue(name, "finite", f"{col} contiene valores ausentes, no numericos o no finitos")
        duplicates = KEYS + (["sample_number"] if name == "Points" else [])
        if df.duplicated(duplicates, keep=False).any():
            issue(name, "duplicate", "Identidad de aforo o muestra repetida")
        nonnegative = ["area_total_m2", "hydraulic_radius_m"] if name == "Summary" else ["depth_m", "distance_m"]
        positive = ["width_total_m", "sample_count", "wetted_perimeter_m"] if name == "Summary" else ["width_m", "sample_number"]
        for col in nonnegative:
            if df[col].lt(0).any():
                issue(name, "range", f"{col} debe ser mayor o igual a cero")
        for col in positive:
            if df[col].le(0).any():
                issue(name, "range", f"{col} debe ser mayor que cero")
        integer = "sample_count" if name == "Summary" else "sample_number"
        if df[integer].dropna().mod(1).ne(0).any():
            issue(name, "integer", f"{integer} debe ser entero")
        tables[name] = df

    if len(tables) == 2:
        s, p = tables["Summary"], tables["Points"]
        sg = {key: group for key, group in s.groupby(KEYS, dropna=False)}
        pg = {key: group for key, group in p.groupby(KEYS, dropna=False)}
        for key in sg.keys() | pg.keys():
            source = str(key[-1])
            if key not in sg or key not in pg:
                issue("Summary/Points", "missing_pair", "Transecto sin su tabla complementaria", source)
                continue
            if len(sg[key]) != 1:
                continue
            row = sg[key].iloc[0]
            samples = pg[key].sort_values("sample_number")
            if len(samples) != row["sample_count"]:
                issue("Points", "sample_count", "La cantidad de muestras difiere de Summary", source)
            if not np.array_equal(samples["sample_number"].to_numpy(), np.arange(1, len(samples) + 1)):
                issue("Points", "sample_sequence", "Se esperaba numeracion 1..N sin huecos", source)
            if not np.allclose(samples["width_m"], row["width_total_m"], rtol=1e-8, atol=1e-8):
                issue("Points", "width", "El ancho de Points no coincide con Summary", source)
            if samples["distance_m"].gt(row["width_total_m"] + 1e-8).any():
                issue("Points", "position", "Posicion fuera del ancho de la seccion", source)
            if samples.loc[np.isfinite(samples["distance_m"]), "distance_m"].duplicated().any():
                issue("Points", "ive_positions", "Hay posiciones repetidas que impiden calcular IVE con el metodo actual", source)
            q = samples["q_cumulative_m3s"]
            if not np.isclose(q.iloc[-1], row["q_total_m3s"], rtol=1e-8, atol=1e-8):
                issue("Summary/Points", "discharge", "El caudal acumulado final no coincide con Summary", source)
            expected = q.diff()
            expected.iloc[0] = q.iloc[0]
            if not np.allclose(samples["q_increment_m3s"], expected, rtol=1e-8, atol=1e-8):
                issue("Points", "increments", "Los incrementos de caudal no coinciden con el acumulado", source)
            perimeter = row["wetted_perimeter_m"]
            if perimeter > 0 and not np.isclose(row["hydraulic_radius_m"], row["area_total_m2"] / perimeter,
                                               rtol=1e-8, atol=1e-8):
                issue("Summary", "radius", "El radio no coincide con area/perimetro mojado o hay valores ausentes", source)
    return pd.DataFrame(rows, columns=["table", "instrument", "source_file", "rule", "status", "message"])


def split_instruments(input_dir: Path, temporary_dir: Path):
    """Provide generic checks with non-M9 rows and M9 with its own schema.

    Preserve the old execution path exactly when M9 is absent. Consolidated
    normalized tables remain the input contract of the validation command.
    """
    tables = {}
    has_m9 = False
    for name in ("Summary", "Points"):
        path = input_dir / f"{name}.csv"
        df = pd.read_csv(path, dtype=str) if path.exists() else None
        if df is not None and "instrument" in df:
            mask = df["instrument"].fillna("").str.strip().str.casefold().eq("m9")
        else:
            mask = pd.Series(False, index=df.index) if df is not None else None
        tables[name] = (df, mask)
        has_m9 |= mask is not None and bool(mask.any())
    if not has_m9:
        return input_dir, True, None
    has_other = False
    m9 = {}
    # Other configured tables are copied unchanged for legacy checks.
    import shutil
    for path in input_dir.glob("*.csv"):
        shutil.copy2(path, temporary_dir / path.name)
    for name, (df, mask) in tables.items():
        m9[name] = df.loc[mask].copy() if df is not None else None
        if df is not None:
            others = df.loc[~mask]
            has_other |= not others.empty
            others.to_csv(temporary_dir / f"{name}.csv", index=False)
    return temporary_dir, has_other, validate_m9(m9["Summary"], m9["Points"])
