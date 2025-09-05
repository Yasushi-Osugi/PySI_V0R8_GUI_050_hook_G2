# pysi/io/tree_writeback.py

from __future__ import annotations
import sqlite3
from typing import Dict, Iterable, Set, Tuple, Optional, List

# --- PlanNodeの代わりに使う極薄シム -------------------------------
class _NodeShim:
    """
    PlanNode互換の最小ダミー。
    load_leaf_S_and_compute / write_both_layers が参照する属性/メソッドだけを持つ。
    """
    def __init__(self, name: str):
        self.name = name
        # 一部の実装が存在チェックだけするケースに備えてダミー属性を用意
        self.psi4demand = None
        self._S2psi = None
        self._plan_range = None
        self._plan_year_st = None

    # 署名: set_plan_range_lot_counts(plan_range, plan_year_st)
    def set_plan_range_lot_counts(self, plan_range: int, plan_year_st: int):
        self._plan_range = int(plan_range)
        self._plan_year_st = int(plan_year_st)

    # 署名: set_S2psi(mapping or object)
    
    #@STOP
    #def set_S2psi(self, s2psi):
    #    self._S2psi = s2psi

    def set_S2psi(self, s2psi):
        """PlanNode 互換: 渡された PSI オブジェクトから demand 側を拾って束ねる。"""
        self._S2psi = s2psi
        # いくつかの形に耐えるフェイルセーフ実装
        if hasattr(s2psi, "psi4demand"):
            # PlanNode 由来のオブジェクト: 属性で持っている
            self.psi4demand = s2psi.psi4demand
        elif isinstance(s2psi, dict):
            # dict で渡る系: 'demand' or 'psi4demand' を優先
            if "psi4demand" in s2psi:
                self.psi4demand = s2psi["psi4demand"]
            elif "demand" in s2psi:
                self.psi4demand = s2psi["demand"]
            else:
                # どうにも特定できなければ一旦そのまま
                self.psi4demand = s2psi
        else:
            # 最後のフォールバック
            self.psi4demand = s2psi


    def __repr__(self) -> str:
        return f"<_NodeShim name={self.name!r}>"

# --- DBからペアやネットワーク情報を拾うユーティリティ -----------

def pairs_from_weekly_demand(conn: sqlite3.Connection, scenario_id: int) -> Set[Tuple[str, str]]:
    rows = conn.execute(
        """
        SELECT n.name, p.name
          FROM weekly_demand wd
          JOIN node n    ON wd.node_id=n.id
          JOIN product p ON wd.product_id=p.id
         WHERE wd.scenario_id=?
         GROUP BY n.name, p.name
        """,
        (scenario_id,),
    ).fetchall()
    return {(r[0], r[1]) for r in rows}

def _children_of(node) -> Iterable:
    # PlanNode想定: children / get_children / iter_nodes いずれか
    if hasattr(node, "children"):
        return getattr(node, "children") or []
    if hasattr(node, "get_children"):
        return node.get_children() or []
    return []

def node_names_from_plan_root(root) -> Set[str]:
    seen: Set[str] = set()
    stack: List = [root]
    while stack:
        cur = stack.pop()
        name = getattr(cur, "name", None)
        if name and name not in seen:
            seen.add(name)
            stack.extend(_children_of(cur))
    return seen

def intersect_pairs_with_network(db_pairs: Set[Tuple[str, str]], net_node_names: Set[str]) -> Set[Tuple[str, str]]:
    return {(n, p) for (n, p) in db_pairs if n in net_node_names}

# --- ここが“1関数完結”の書戻し -------------------------------

def write_both_layers_for_pair(
    conn: sqlite3.Connection,
    scenario_id: int,
    node_name: str,
    product_name: str,
) -> Dict[str, int]:
    """
    1ペア（node, product）について、
      1) Sロットの準備（leaf相当の前処理）
      2) demand/supply 両レイヤを DB(lot/lot_bucket) にUPSERT
    までを一括で行い、書き込み件数などを返す。
    """
    from pysi.io.psi_io_adapters import (
        load_leaf_S_and_compute,
        write_both_layers,
        get_scenario_bounds,
    )

    # シナリオの週範囲（calendar_isoと同期済みである前提）
    plan_year_st, plan_range = get_scenario_bounds(conn, scenario_id)

    # PlanNodeの代替として最小限のシムを渡す
    node_obj = _NodeShim(node_name)
    # leaf相当の前処理（キーワード引数が前提の実装に合わせる）
    load_leaf_S_and_compute(
        conn,
        scenario_id=scenario_id,
        node_obj=node_obj,
        product_name=product_name,
        layer="demand",
    )

    # 両レイヤ書戻し（同じくキーワード引数）
    d_rows, s_rows = write_both_layers(
        conn,
        scenario_id=scenario_id,
        node_obj=node_obj,
        product_name=product_name,
        replace_slice=True,
    )

    return {"d_rows": int(d_rows), "s_rows": int(s_rows)}
