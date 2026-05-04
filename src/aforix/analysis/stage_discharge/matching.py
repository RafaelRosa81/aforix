import pandas as pd


def match_manual_and_instrument(df_summary: pd.DataFrame, df_manual: pd.DataFrame) -> pd.DataFrame:
    if df_summary.empty:
        return pd.DataFrame()

    if df_manual.empty:
        df_summary["manual_stage_m"] = None
        return df_summary

    df = pd.merge(
        df_summary,
        df_manual,
        how="left",
        left_on=["station_id", "measurement_date"],
        right_on=["station_id", "measurement_date"],
    )

    return df
