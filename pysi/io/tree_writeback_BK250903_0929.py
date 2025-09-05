# pysi/io/tree_writeback.py
from __future__ import annotations
import sqlite3
from typing import Dict, Iterable, List, Optional, Set, Tuple

# 既存の I/O（キーワード専用引数）をインポート
from pysi.io.psi_io_adapters import (
    load_leaf_S_and_compute,
    write_both_layers,
)

class _NodeShim:
    """
    計算用 PlanNode の代替（最小限）
    load_leaf_S_and_compute が node_obj に属性を書き込む前提に合わせて
    受け皿だけ用意する。
    """
    __slots__ = ("name", "parent", "children", "psi4demand", "psi4supply")
    def __init__(self, name: str):
        self.name = name
        self.parent = None
        self.children: List["_NodeShim"] = []
        self.psi4demand = None
        self.psi4supply = None
    def add_child(self, child: "_NodeShim"):
        child.parent = self
        self.children.append(child)

def compute_leaf_S_for_pair(conn: sqlite3.Connection,
                            scenario_id: int,
                            node_name: str,
                            product_name: str) -> Tuple[int, int]:
    """
    “S生成のみ”を行い、おおまかな行数(0,0)を返すダミー。
    実際の書き込みは write_both_layers_for_pair で行うのを推奨。
    """
    node_obj = _NodeShim(node_name)
    # キーワード専用引数で委譲
    load_leaf_S_and_compute(conn,
                            scenario_id=scenario_id,
                            node_obj=node_obj,
                            product_name=product_name,
                            layer="demand")
    # 件数は書戻し後でないと確定しないため仮で 0 を返す
    return 0, 0

def write_both_layers_for_pair(conn: sqlite3.Connection,
                               scenario_id: int,
                               node_name: str,
                               product_name: str) -> Dict[str, int]:
    """
    1ペア（node, product）について、
      1) Sロット生成（DBの node_product.lot_size を参照）
      2) demand/supply 両レイヤを書戻し
    をまとめて実施。戻り値は {'d_rows': x, 's_rows': y}
    """
    node_obj = _NodeShim(node_name)

    # 先に S を生成（lot_size はアダプタ内部で解決される想定）
    load_leaf_S_and_compute(conn,
                            scenario_id=scenario_id,
                            node_obj=node_obj,
                            product_name=product_name,
                            layer="demand")

    # 両レイヤ書戻し（Tuple[int,int] = (d_rows, s_rows) を返す想定）
    d_rows, s_rows = write_both_layers(conn,
                                       scenario_id=scenario_id,
                                       node_obj=node_obj,
                                       product_name=product_name,
                                       replace_slice=True)
    return {"d_rows": int(d_rows), "s_rows": int(s_rows)}

# --- 既存ユーティリティ（orchestrator で使用） --------------------

def pairs_from_weekly_demand(conn: sqlite3.Connection, scenario_id: int) -> Set[Tuple[str, str]]:
    rows = conn.execute("""
        SELECT n.name, p.name
        FROM weekly_demand wd
        JOIN node n    ON wd.node_id = n.id
        JOIN product p ON wd.product_id = p.id
        WHERE wd.scenario_id=?
        GROUP BY n.name, p.name
    """, (scenario_id,)).fetchall()
    return {(r[0], r[1]) for r in rows}

def node_names_from_plan_root(root) -> Set[str]:
    names: Set[str] = set()
    stack = [root]
    while stack:
        n = stack.pop()
        nm = getattr(n, "name", None)
        if nm and nm not in names:
            names.add(nm)
            stack.extend(getattr(n, "children", []) or [])
    return names

def intersect_pairs_with_network(db_pairs: Set[Tuple[str,str]],
                                 net_nodes: Set[str]) -> Set[Tuple[str,str]]:
    return {(n,p) for (n,p) in db_pairs if n in net_nodes}
