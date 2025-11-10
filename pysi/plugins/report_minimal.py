# pysi/plugins/report_minimal.py

import csv
import os
from pysi.core.hooks.core import filter as hook_filter

def _export_series(result, out_dir, logger=None):
    """
    result["psi_df"]（pandas.DataFrame）を CSV 出力します。
    出力先: <out_dir>/series.csv
    """
    series = result.get("psi_df")
    if series is None:
        return
    p = os.path.join(out_dir, "series.csv")
    os.makedirs(out_dir, exist_ok=True)
    try:
        series.to_csv(p, index=False, encoding="utf-8-sig")
        if logger:
            logger.info(f"[report] write {p}")
    except Exception:
        if logger:
            logger.exception("[report] series export failed")

def _export_kpi(result, out_dir, logger=None):
    """
    result["kpis"]（dict想定）を CSV 出力します。
    出力先: <out_dir>/kpi.csv
    """
    kpi = result.get("kpis") or {}
    p = os.path.join(out_dir, "kpi.csv")
    os.makedirs(out_dir, exist_ok=True)
    try:
        with open(p, "w", newline="", encoding="utf-8-sig") as f:
            wr = csv.writer(f)
            wr.writerow(["key", "value"])
            for k, v in kpi.items():
                wr.writerow([k, v])
        if logger:
            logger.info(f"[report] write {p}")
    except Exception:
        if logger:
            logger.exception("[report] kpi export failed")

@hook_filter("report:exporters", priority=50)
def add_basic_exporters(ex_list, **ctx):
    """
    Pipeline 側の report:exporters フィルタに、
    最小の CSV 出力エクスポータ（series/kpi）を追加します。
    """
    ex_list = list(ex_list or [])
    ex_list.extend([_export_series, _export_kpi])
    return ex_list
