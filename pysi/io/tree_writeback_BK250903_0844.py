# pysi/io/tree_writeback.py
from __future__ import annotations
import sqlite3
from typing import Iterable, Set, Tuple

# 既存 I/O を再利用（leafモードで使っている関数群）
from pysi.io.psi_io_adapters import (
    write_both_layers,  # (conn, scenario_id, node_name, product_name)
)

# （任意）node/product の存在を最低限保証したい場合は ensure_* を使う
try:
    from pysi.etl.etl_monthly_to_lots import ensure_node, ensure_product
except Exception:
    ensure_node = ensure_product = None

def write_both_layers_for_pair(conn: sqlite3.Connection, scenario_id: int,
                               node_name: str, product_name: str):
    """
    treeモードの（node, product）ペアを、leafモードと同じ書戻しロジックに通す薄いアダプタ。
    """
    if ensure_node:
        ensure_node(conn, node_name)
    if ensure_product:
        ensure_product(conn, product_name)
    return write_both_layers(conn, scenario_id, node_name, product_name)

def pairs_from_weekly_demand(conn: sqlite3.Connection, scenario_id: int) -> Set[Tuple[str, str]]:
    """
    シナリオに実在する（node, product）ペアを DB から列挙。
    treeネットワーク上のノードと突き合わせる前の全体集合。
    """
    sql = """
    SELECT n.name, p.name
    FROM weekly_demand w
    JOIN node n    ON n.id = w.node_id
    JOIN product p ON p.id = w.product_id
    WHERE w.scenario_id = ?
    GROUP BY n.name, p.name
    """
    return {(r[0], r[1]) for r in conn.execute(sql, (scenario_id,)).fetchall()}

def node_names_from_plan_root(root) -> Set[str]:
    """PlanNode ルートからネットワーク内の node.name を列挙。"""
    seen = set()
    stack = [root]
    while stack:
        n = stack.pop()
        if n.name not in seen:
            seen.add(n.name)
            stack.extend(getattr(n, "children", []) or [])
    return seen

def intersect_pairs_with_network(pairs: Iterable[Tuple[str, str]], node_names: Set[str]) -> Set[Tuple[str, str]]:
    """DBのペア集合を、ネットワーク内のノード名に制限。"""
    return {(node, prod) for (node, prod) in pairs if node in node_names}
