# calendar_sync.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import sqlite3
from typing import Optional, Tuple
from calendar_iso import ensure_calendar_iso
from etl_monthly_to_lots import compute_plan_bounds, normalize_monthly_csv
from psi_io_adapters import get_scenario_id, get_scenario_bounds

def _bounds_from_csv(csv_path: str) -> Tuple[int, int]:
    df = normalize_monthly_csv(csv_path)
    b = compute_plan_bounds(df)
    return int(b.plan_year_st), int(b.plan_range)

def sync_calendar_iso(
    conn: sqlite3.Connection,
    *,
    scenario_name: str,
    csv_path: Optional[str] = None,
    plan_year_st: Optional[int] = None,
    plan_range: Optional[int] = None,
    clear_lot_bucket_on_change: bool = True,
) -> int:
    """
    1) 境界を決める（優先度：引数 > CSV > 既存シナリオ）
    2) calendar_iso を ensure（冪等）
    3) 週数を返す。境界が変わったら lot_bucket を消して「再書戻し」を促す
    """
    sid = get_scenario_id(conn, scenario_name)

    # 既存シナリオ境界
    cur_pys, cur_pr = get_scenario_bounds(conn, sid)

    # 入力から境界決定
    if plan_year_st is None or plan_range is None:
        if csv_path:
            pys, pr = _bounds_from_csv(csv_path)
        else:
            pys, pr = cur_pys, cur_pr
    else:
        pys, pr = int(plan_year_st), int(plan_range)

    # 以前のカレンダ週数を取得（比較用）
    prev_weeks = conn.execute("SELECT COUNT(*) FROM calendar_iso").fetchone()[0] or 0
    prev_range = (cur_pys, cur_pr)

    # 正本を冪等更新
    n_weeks = ensure_calendar_iso(conn, pys, pr)

    # シナリオの境界を最新化（保持しておくと可視化や再起動時に便利）
    with conn:
        conn.execute(
            "UPDATE scenario SET plan_year_st=?, plan_range=? WHERE id=?",
            (pys, pr, sid),
        )

    # 境界が変わったら対象シナリオの lot_bucket をクリア（再書戻し前提）
    if clear_lot_bucket_on_change and (prev_range != (pys, pr)):
        with conn:
            conn.execute("DELETE FROM lot_bucket WHERE scenario_id=?", (sid,))

    return int(n_weeks)
