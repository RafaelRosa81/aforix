import pandas as pd


def apply_ranking(df: pd.DataFrame, ranking: list[str]) -> pd.DataFrame:
    if df.empty:
        return df

    rank_map = {inst: i for i, inst in enumerate(ranking)}
    df["rank"] = df["instrument"].map(rank_map).fillna(999)

    df_best = (
        df.sort_values("rank")
        .groupby(["station_id", "measurement_date"], as_index=False)
        .first()
    )

    df_best["analysis_group"] = "BEST"
    df["analysis_group"] = df["instrument"]

    return pd.concat([df, df_best], ignore_index=True)
