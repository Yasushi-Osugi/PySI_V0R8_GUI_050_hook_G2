# pysi/db/calendar_sync.py

from __future__ import annotations

import sqlite3
from typing import Optional, Tuple

# ★ すべて pysi. から始まる絶対インポートにする
from pysi.db.calendar_iso import ensure_calendar_iso

try:
    import pandas as pd
except Exception:
    pd = None  # csv から境界推定しないなら未導入でもOK


def _compute_bounds_from_csv(csv_path: str) -> Tuple[int, int]:
    """
    月次CSV(product_name,node_name,year,m1..m12)から計画境界を推定。
    仕様：plan_year_st = min(year), plan_range = (max-min+1)+1
          （+1は後ろはみ出し保険）
    """
    if pd is None:
        raise RuntimeError("pandas が必要です（pip install pandas）。")
    df = pd.read_csv(csv_path)
    if "year" not in df.columns:
        raise ValueError("CSV に 'year' 列がありません。")
    years = pd.to_numeric(df["year"], errors="coerce").dropna().astype(int)
    y0 = int(years.min())
    y1 = int(years.max())
    plan_year_st = y0
    plan_range = (y1 - y0 + 1) + 1
    return plan_year_st, plan_range


def _get_scenario(conn: sqlite3.Connection, scenario_name: str) -> Tuple[int, int, int]:
    row = conn.execute(
        "SELECT id, plan_year_st, plan_range FROM scenario WHERE name=?",
        (scenario_name,),
    ).fetchone()
    if not row:
        raise ValueError(f"scenario not found: {scenario_name}")
    sid, pys, pr = int(row[0]), int(row[1]), int(row[2])
    return sid, pys, pr


def _update_scenario_bounds(conn: sqlite3.Connection, scenario_id: int, plan_year_st: int, plan_range: int) -> None:
    conn.execute(
        "UPDATE scenario SET plan_year_st=?, plan_range=? WHERE id=?",
        (int(plan_year_st), int(plan_range), int(scenario_id)),
    )


def sync_calendar_iso(
    conn: sqlite3.Connection,
    *,
    scenario_name: str,
    csv_path: Optional[str] = None,
    clear_lot_bucket_on_change: bool = True,
) -> dict:
    """
    シナリオの計画境界に calendar_iso を同期。
    - csv_path を与えると CSV から境界を推定し、scenario を更新。
    - ensure_calendar_iso() で calendar_iso を再構築（冪等）。
    - 週数の変化があれば lot_bucket をクリア（オプション）。
    戻り: 変更サマリ dict
    """
    with conn:
        sid, old_pys, old_pr = _get_scenario(conn, scenario_name)

        if csv_path:
            new_pys, new_pr = _compute_bounds_from_csv(csv_path)
        else:
            new_pys, new_pr = old_pys, old_pr

        # 変化があれば scenario を更新
        scenario_changed = (new_pys != old_pys) or (new_pr != old_pr)
        if scenario_changed:
            _update_scenario_bounds(conn, sid, new_pys, new_pr)

        # カレンダ同期
        before_cnt = conn.execute("SELECT COUNT(*) FROM calendar_iso;").fetchone()[0] or 0
        weeks = ensure_calendar_iso(conn, new_pys, new_pr)
        after_cnt = conn.execute("SELECT COUNT(*) FROM calendar_iso;").fetchone()[0] or 0
        calendar_changed = (before_cnt != after_cnt) or scenario_changed

        # 週レンジが変わったら、このシナリオの lot_bucket をクリアして整合性を守る
        cleared = 0
        if calendar_changed and clear_lot_bucket_on_change:
            cleared = conn.execute(
                "DELETE FROM lot_bucket WHERE scenario_id=?",
                (sid,),
            ).rowcount

    return {
        "scenario_id": sid,
        "scenario_changed": scenario_changed,
        "old_bounds": (old_pys, old_pr),
        "new_bounds": (new_pys, new_pr),
        "calendar_weeks": weeks,
        "calendar_changed": calendar_changed,
        "lot_bucket_cleared": int(cleared),
    }
