# pysi/io/tree_writeback.py
from __future__ import annotations
import sqlite3
from typing import Dict, List

# 既存 I/O ユーティリティを利用
from pysi.io.psi_io_adapters import (
    get_scenario_bounds,
    load_leaf_S_and_compute,   # (conn, *, scenario_id, node_obj, product_name, layer='demand')
    write_both_layers,         # (conn, *, scenario_id, node_obj, product_name, replace_slice=True)
)

def _weeks_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM calendar_iso").fetchone()
    return int(row[0] or 0)

class _NodeShim:
    """
    PlanNodeの最小互換シム。
    - psi4demand / psi4supply を calendar_iso の週数に合わせて確保
    - load_leaf_S_and_compute() が呼ぶメソッドをダミー実装
    """
    def __init__(self, name: str, weeks: int):
        self.name = name
        self._weeks = int(weeks)
        # 週ごとにロット配列（例: 週tのSロットID群）を入れる2次元リストを想定
        self.psi4demand: List[List] = [[] for _ in range(self._weeks)]
        self.psi4supply: List[List] = [[] for _ in range(self._weeks)]
        # 必要なら後で上書きされる
        self.lot_size = 1

    # --- load_leaf_S_and_compute() から呼ばれうるAPIをダミーで用意 ---
    def set_plan_range_lot_counts(self, plan_range: int, plan_year_st: int):
        """GUI版PlanNode互換のダミー。配列確保は __init__ 済みなので何もしない。"""
        return

    def set_time_flow_label(self, *a, **k):
        """ダミー（GUI用ラベル）。"""
        return

    def set_S2psi(self, pSi):
        """需要側PSIの受け取り。長さが足りなければ右側を空リストで埋める。"""
        if pSi is None:
            return
        # list-like を想定（週 × ロット配列）
        pSi = list(pSi)
        if len(pSi) < self._weeks:
            pSi = pSi + [[] for _ in range(self._weeks - len(pSi))]
        elif len(pSi) > self._weeks:
            pSi = pSi[:self._weeks]
        self.psi4demand = pSi

    def set_PSI(self, layer: str, arr):
        """必要に応じて供給側も受け取れるように。"""
        if arr is None:
            return
        arr = list(arr)
        if len(arr) < self._weeks:
            arr = arr + [[] for _ in range(self._weeks - len(arr))]
        elif len(arr) > self._weeks:
            arr = arr[:self._weeks]
        if layer == "supply":
            self.psi4supply = arr
        elif layer == "demand":
            self.psi4demand = arr

def write_both_layers_for_pair(conn: sqlite3.Connection,
                               scenario_id: int,
                               node_name: str,
                               product_name: str) -> Dict[str, int]:
    """
    （node, product）ペアのために：
      1) calendar_iso 週数に合わせて Nodeシムを準備
      2) 需要Sを生成（load_leaf_S_and_compute）
      3) demand/supply 両レイヤを lot_bucket へ書戻し
    """
    # 週数を正に（ゼロならスキップ）
    weeks = _weeks_count(conn)
    if weeks <= 0:
        raise RuntimeError("calendar_iso is empty. Run calendar sync first.")

    # シナリオ境界を一応読んでおく（互換のため）
    plan_year_st, plan_range = get_scenario_bounds(conn, scenario_id)

    # Nodeシムを calendar週数で確保
    node_obj = _NodeShim(node_name, weeks)

    # 1) 需要Sを生成してシムに流し込む（関数内で node_obj.set_S2psi が呼ばれる想定）
    load_leaf_S_and_compute(
        conn,
        scenario_id=scenario_id,
        node_obj=node_obj,
        product_name=product_name,
        layer="demand",
    )

    # 2) 両レイヤ書戻し（閾値・置換ポリシーは既定のまま）
    d_rows, s_rows = write_both_layers(
        conn,
        scenario_id=scenario_id,
        node_obj=node_obj,
        product_name=product_name,
        replace_slice=True,
    )

    return {"d_rows": int(d_rows), "s_rows": int(s_rows), "weeks": weeks}
