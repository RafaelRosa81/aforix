import pandas as pd


def apply_transforms(df, transforms, columns_spec):
    for transform in transforms:
        name = transform["name"]

        if name == "strip_strings":
            df = strip_strings(df)

        elif name == "numeric_commas_to_dots":
            df = numeric_commas_to_dots(df, columns_spec)

        elif name == "enforce_dtypes":
            df = enforce_dtypes(df, columns_spec)

        else:
            raise ValueError(f"Unknown transform: {name}")

    return df


def strip_strings(df):
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
    return df


def numeric_commas_to_dots(df, columns_spec):
    for col, spec in columns_spec.items():
        if spec.get("dtype") == "float" and col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", ".", regex=False)
            )
    return df


def enforce_dtypes(df, columns_spec):
    for col, spec in columns_spec.items():
        if col not in df.columns:
            continue

        dtype = spec.get("dtype")

        if dtype == "float":
            df[col] = pd.to_numeric(df[col], errors="coerce")

        elif dtype == "int":
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

        elif dtype == "string":
            df[col] = df[col].astype("string")

        elif dtype == "date":
            s = df[col].astype("string").str.strip()

            # Si viene como 20251215, interpretarlo como YYYYMMDD
            mask_yyyymmdd = s.str.fullmatch(r"\d{8}", na=False)

            parsed = pd.to_datetime(s, errors="coerce")

            parsed.loc[mask_yyyymmdd] = pd.to_datetime(
                s.loc[mask_yyyymmdd],
                format="%Y%m%d",
                errors="coerce",
            )

            df[col] = parsed.dt.date

        elif dtype == "datetime":
            df[col] = pd.to_datetime(df[col], errors="coerce")

        elif dtype == "time_hhmmss":
            s = df[col].astype("string").str.strip().str.zfill(6)
            df[col] = (
                s.str.slice(0, 2)
                + ":"
                + s.str.slice(2, 4)
                + ":"
                + s.str.slice(4, 6)
            )

    return df