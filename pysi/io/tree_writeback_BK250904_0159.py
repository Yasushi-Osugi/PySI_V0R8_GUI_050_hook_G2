# pysi/io/tree_writeback.py
from __future__ import annotations
import sqlite3
from typing import Dict, List

from typing import Iterable, Set, Tuple


from pysi.io.psi_io_adapters import (
    get_scenario_bounds,
    load_leaf_S_and_compute,   # keyword-only
    write_both_layers,         # keyword-only
)

def _weeks_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM calendar_iso").fetchone()
    return int(row[0] or 0)

class SafeList(list):
    """範囲外アクセスは空配列を返す安全ラッパ"""
    def __getitem__(self, idx):
        if -len(self) <= idx < len(self):
            return super().__getitem__(idx)
        return []

class _NodeShim:
    """
    PlanNode 最小互換。calendar_iso の週数で配列確保し、
    受け取る配列が短い場合は右パディング、長い場合は切り詰め。
    """
    def __init__(self, name: str, weeks: int):
        self.name = name
        self._weeks = int(weeks)
        self.psi4demand: List[List] = SafeList([[] for _ in range(self._weeks)])
        self.psi4supply: List[List] = SafeList([[] for _ in range(self._weeks)])
        self.lot_size = 1

    def set_plan_range_lot_counts(self, plan_range: int, plan_year_st: int):
        return

    def set_time_flow_label(self, *a, **k):
        return

    def _fit(self, seq):
        seq = list(seq or [])
        if len(seq) < self._weeks:
            seq = seq + [[] for _ in range(self._weeks - len(seq))]
        elif len(seq) > self._weeks:
            seq = seq[:self._weeks]
        return SafeList(seq)

    def set_S2psi(self, pSi):
        """需要側 PSI を受け取り、長さを合わせる。"""
        self.psi4demand = self._fit(pSi)

    def set_PSI(self, layer: str, arr):
        arr = self._fit(arr)
        if layer == "supply":
            self.psi4supply = arr
        elif layer == "demand":
            self.psi4demand = arr

def write_both_layers_for_pair(conn: sqlite3.Connection,
                               scenario_id: int,
                               node_name: str,
                               product_name: str) -> Dict[str, int]:
    """
    1) Nodeシム準備（calendar 週数で配列確保）
    2) 需要S生成（load_leaf_S_and_compute）
    3) demand/supply 両レイヤを lot_bucket へ書戻し
    """
    weeks = _weeks_count(conn)
    if weeks <= 0:
        raise RuntimeError("calendar_iso is empty. Run calendar sync first.")

    plan_year_st, plan_range = get_scenario_bounds(conn, scenario_id)

    node_obj = _NodeShim(node_name, weeks)

    # 需要Sを生成（関数内で set_S2psi が呼ばれる前提）
    load_leaf_S_and_compute(
        conn,
        scenario_id=scenario_id,
        node_obj=node_obj,
        product_name=product_name,
        layer="demand",
    )

    # 念のため SafeList で包み直し（外部が入れ替えた場合でも安全に）
    node_obj.psi4demand = SafeList(node_obj.psi4demand)
    node_obj.psi4supply = SafeList(node_obj.psi4supply)

    d_rows, s_rows = write_both_layers(
        conn,
        scenario_id=scenario_id,
        node_obj=node_obj,
        product_name=product_name,
        replace_slice=True,
    )
    return {"d_rows": int(d_rows), "s_rows": int(s_rows), "weeks": weeks}

# --- helpers for orchestrator tree mode ---------------------------------

def pairs_from_weekly_demand(conn, scenario_id: int) -> Set[Tuple[str, str]]:
    """
    DB中の weekly_demand から (node_name, product_name) のユニーク集合を返す。
    orchestrator の tree 分岐で使う。
    """
    rows = conn.execute(
        """
        SELECT n.name, p.name
        FROM weekly_demand wd
        JOIN node n    ON wd.node_id = n.id
        JOIN product p ON wd.product_id = p.id
        WHERE wd.scenario_id = ?
        GROUP BY n.name, p.name
        """,
        (scenario_id,),
    ).fetchall()
    return {(r[0], r[1]) for r in rows}

def node_names_from_plan_root(root) -> Set[str]:
    """
    PlanNode/Node のルートから子孫をたどって node.name の集合を返す。
    children / childs / get_children のいずれにも対応。
    """
    names: Set[str] = set()
    seen = set()
    stack = [root]
    while stack:
        n = stack.pop()
        if n is None:
            continue
        oid = id(n)
        if oid in seen:
            continue
        seen.add(oid)

        name = getattr(n, "name", None)
        if isinstance(name, str) and name:
            names.add(name)

        # 代表的な子アクセスにゆるく対応
        children = []
        if hasattr(n, "children"):
            children = list(getattr(n, "children") or [])
        elif hasattr(n, "childs"):
            children = list(getattr(n, "childs") or [])
        elif hasattr(n, "get_children"):
            try:
                children = list(n.get_children() or [])
            except Exception:
                children = []
        stack.extend(children)
    return names

def intersect_pairs_with_network(pairs: Iterable[Tuple[str,str]],
                                 node_names: Set[str]) -> Set[Tuple[str,str]]:
    """
    (node, product) の集合をネットワークに存在する node のみに絞る。
    """
    return {(n, p) for (n, p) in pairs if n in node_names}

