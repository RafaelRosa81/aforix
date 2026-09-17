from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from openpyxl import Workbook

from aforix.metadata import canonical_station_id
from aforix.analysis.correlation.excel import add_pair_sheet, safe_save_workbook, write_summary_sheet, write_run_config_sheet
from aforix.analysis.correlation.io.gauges import load_gauges_daily
from aforix.analysis.correlation.io.stations import load_station_series
from aforix.analysis.correlation.metrics import mae, mape, nse, pbias, pearson, r2, rmse
from aforix.analysis.correlation.plotting import save_scatter_with_regression, save_time_series
from aforix.analysis.correlation.types import MeasuringInstrument


def _require_roles(variable_roles, workflow_name):
    if not variable_roles: raise ValueError(f"variable_roles must be provided from config for {workflow_name}")
    missing = {"x", "y"} - set(variable_roles)
    if missing: raise ValueError(f"Missing variable_roles key(s) for {workflow_name}: {', '.join(sorted(missing))}")
    return {"x": str(variable_roles["x"]).lower(), "y": str(variable_roles["y"]).lower()}


def _role_columns(roles):
    role_to_col = {"station": "q_station_l/s", "gauge": "q_gauge_l/s"}
    if roles["x"] not in role_to_col or roles["y"] not in role_to_col: raise ValueError(f"Invalid variable_roles for gauges_vs_stations: {roles}")
    return role_to_col[roles["x"]], role_to_col[roles["y"]], f"q_{roles['y']}_pred_l/s", f"{roles['x'].capitalize()} q [l/s]", f"{roles['y'].capitalize()} q [l/s]"


def _linear_fit(x, y):
    if len(x) < 2 or np.nanstd(x) == 0:
        intercept = float(np.nanmean(y)) if len(y) else float("nan"); return 0.0, intercept, np.full_like(y, intercept, dtype=float)
    slope, intercept = np.polyfit(x, y, 1); return float(slope), float(intercept), slope * x + intercept


def _apply_window_merge(df_g, df_s, days_window):
    rows = []
    for _, row in df_g.iterrows():
        d = row["date"]; subset = df_s.loc[(df_s["date"] >= d-pd.Timedelta(days=days_window)) & (df_s["date"] <= d+pd.Timedelta(days=days_window))]
        if subset.empty: continue
        closest = subset.iloc[(subset["date"]-d).abs().argsort()].iloc[0]; rows.append({"date": d, "q_gauge_l/s": row["q_gauge_l/s"], "q_station_l/s": closest["q_station_l/s"], "source": row.get("source", "")})
    return pd.DataFrame(rows)


def _available_station_ids(stations_dir, timestep): return sorted({p.name.split("_")[0] for p in stations_dir.glob(f"*_{timestep}_station_data.csv")})


def _normalize_pairs(pairs: Iterable[tuple[str, str]] | None) -> list[tuple[str, str]]:
    out = []
    for station_id, point_id in pairs or []:
        station = str(station_id).removeprefix("S").strip(); point = canonical_station_id(point_id)
        if station and point: out.append((station, point))
    return out


def run_gauges_vs_stations(*, normalized_root: Path, stations_dir: Path, output_dir: Path, instruments: list[MeasuringInstrument], ranking_codes: list[str], timestep: str="daily", match_mode: str="exact", window_days: int=0, pairs=None, variable_roles=None) -> Path:
    roles = _require_roles(variable_roles, "gauges_vs_stations"); x_col,y_col,pred_col,x_label,y_label = _role_columns(roles); gauges = load_gauges_daily(normalized_root,instruments,ranking_codes); ranking_label="_".join(ranking_codes); selected_pairs=_normalize_pairs(pairs); pairs_label="all_pairs" if not selected_pairs else "pairs_"+"_".join(f"S{s}_{p}" for s,p in selected_pairs); out_dir=output_dir/"gauges_vs_stations"/timestep/f"instruments_{ranking_label}"/f"match_{match_mode}_window_{window_days}"/pairs_label; plots_dir=out_dir/"plots"; out_dir.mkdir(parents=True,exist_ok=True)
    wb=Workbook(); wb.remove(wb.active); write_run_config_sheet(wb,{"analysis_type":"gauges_vs_stations","x_role":roles["x"],"y_role":roles["y"],"x_column":x_col,"y_column":y_col,"ranking":ranking_codes,"timestep":timestep,"match_mode":match_mode,"window_days":window_days,"pairs":selected_pairs if selected_pairs else "ALL","normalized_root":str(normalized_root),"stations_dir":str(stations_dir),"output_dir":str(out_dir)})
    summary_rows=[]; station_ids=sorted({s for s,_ in selected_pairs}) if selected_pairs else _available_station_ids(stations_dir,timestep)
    for station_id in station_ids:
        df_station=load_station_series(stations_dir,station_id,timestep)
        if timestep!="daily": continue
        point_ids=[p for s,p in selected_pairs if s==station_id] if selected_pairs else sorted(gauges.keys(),key=int)
        for point in point_ids:
            if point not in gauges: continue
            df_gauge=gauges[point].copy(); merged=pd.merge(df_gauge,df_station,on="date",how="inner") if match_mode=="exact" else _apply_window_merge(df_gauge,df_station,window_days)
            if merged.empty: continue
            merged=merged.sort_values("date").reset_index(drop=True); x_values=merged[x_col].to_numpy(dtype=float); y_values=merged[y_col].to_numpy(dtype=float); slope,intercept,y_pred=_linear_fit(x_values,y_values); merged[pred_col]=y_pred; merged["residual_l/s"]=y_values-y_pred; merged["time"]=merged["date"].dt.strftime("%Y-%m-%d"); dmin=merged["date"].min().strftime("%Y%m%d"); dmax=merged["date"].max().strftime("%Y%m%d"); export=merged[["time","q_station_l/s","q_gauge_l/s",pred_col,"residual_l/s"]].copy(); export.to_csv(out_dir/f"S{station_id}_{point}_gauges_vs_stations_{timestep}_{match_mode}_{dmin}_{dmax}.csv",index=False)
            rmse_direct=rmse(y_values,x_values); rmse_reg=rmse(y_values,y_pred); q_mean_y=float(y_values.mean()) if len(y_values) else float("nan"); row={"Station":f"S{station_id}","Point":point,"X role":roles["x"],"Y role":roles["y"],"X variable":f"{roles['x']} [l/s]","Y variable":f"{roles['y']} [l/s]","X column":x_col,"Y column":y_col,"Linear equation":f"{roles['y']} = {slope:.6f} * {roles['x']} + {intercept:.6f}","slope":slope,"intercept":intercept,"n":int(len(merged)),"R2":r2(y_values,y_pred),"Pearson r":pearson(x_values,y_values),"RMSE Y vs. X [l/s]":rmse_direct,"RMSE regression vs. Y [l/s]":rmse_reg,"q mean Y [l/s]":q_mean_y,"NRMSE Y vs. X [-]":rmse_direct/q_mean_y if q_mean_y else float("nan"),"MAE regression vs. Y [l/s]":mae(y_values,y_pred),"MAPE regression vs. Y [%]":mape(y_values,y_pred),"PBIAS regression vs. Y [%]":pbias(y_values,y_pred),"NSE regression vs. Y":nse(y_values,y_pred),"match_mode":match_mode,"window_days":window_days,"start":dmin,"end":dmax}; summary_rows.append(row); sheet=f"S{station_id}_{point}"; add_pair_sheet(wb,sheet,export,row,x_col=x_col,y_col=y_col,pred_col=pred_col,time_col="time",x_label=x_label,y_label=y_label); save_scatter_with_regression(export,x_col=x_col,y_col=y_col,pred_col=pred_col,x_label=x_label,y_label=y_label,out_path=plots_dir/f"S{station_id}_{point}_scatter_gauges_vs_stations.png"); save_time_series(export,time_col="time",series=[(x_col,roles["x"].capitalize()),(y_col,roles["y"].capitalize())],out_path=plots_dir/f"S{station_id}_{point}_timeseries_gauges_vs_stations.png")
    if summary_rows:
        pd.DataFrame(summary_rows).to_csv(out_dir/f"summary_gauges_vs_stations_{timestep}_{match_mode}_window_{window_days}.csv",index=False); write_summary_sheet(wb,"SummaryMetrics",summary_rows); safe_save_workbook(wb,out_dir/f"correlation_gauges_vs_stations_{timestep}_{ranking_label}_{match_mode}_window_{window_days}.xlsx")
    return out_dir
