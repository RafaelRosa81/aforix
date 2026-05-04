import pandas as pd


def select_best_models(metrics_df: pd.DataFrame, criterion: str = "r2") -> pd.DataFrame:
    if metrics_df.empty:
        return metrics_df

    ascending = criterion in ["rmse", "mae", "nrmse"]

    idx = (
        metrics_df.sort_values(criterion, ascending=ascending)
        .groupby([
            "station_id",
            "analysis_group",
            "instrument",
            "stage_origin",
            "stage_type",
        ])[criterion]
        .idxmax()
        if not ascending
        else metrics_df.sort_values(criterion, ascending=True)
        .groupby([
            "station_id",
            "analysis_group",
            "instrument",
            "stage_origin",
            "stage_type",
        ])[criterion]
        .idxmin()
    )

    return metrics_df.loc[idx].reset_index(drop=True)
