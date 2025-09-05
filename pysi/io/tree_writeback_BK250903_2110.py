# pysi/io/tree_writeback.py

from __future__ import annotations
import sqlite3
from typing import Dict, Iterable, List, Set, Tuple, Any

# 既存 I/O（leaf で使っている実体）を利用
from pysi.io.psi_io_adapters import (
    load_leaf_S_and_compute,  # (conn, *, scenario_id, node_obj, product_name, layer)
    write_both_layers,        # (conn, *, scenario_id, node_obj, product_name, replace_slice)
)

# ────────────────────────────────────────────────────────────────────
# 極小 PlanNode シム
# ────────────────────────────────────────────────────────────────────
class _NodeShim:
    """
    psi_io_adapters が期待する PlanNode の最小サブセット。
    - name: ノード名（DBの node.name と一致）
    - psi4demand: S注入で使われるワーク領域（リストでOK）
    - set_plan_range_lot_counts(): 期間パラメタを受け取るだけ（ここでは no-op）
    必要になったら最小限を足していく方針。
    """
    __slots__ = ("name", "psi4demand", "sku_dict", "lot_size")

    def __init__(self, name: str, lot_size: int = 1):
        self.name = name
        self.psi4demand: List[Any] = []  # アダプタ側が詰め替えるワーク
        self.sku_dict: Dict[str, Any] = {}  # 将来のGUIリンク用（未使用）
        self.lot_size = lot_size

    def set_plan_range_lot_counts(self, plan_range: int, plan_year_st: int) -> None:
        # アダプタ側で呼ばれる想定のため、存在だけ合わせる（処理は不要）
        return

# ────────────────────────────────────────────────────────────────────
# DBユーティリティ（ネットワーク×DBの突合せ）
# ────────────────────────────────────────────────────────────────────
def pairs_from_weekly_demand(conn: sqlite3.Connection, scenario_id: int) -> Set[Tuple[str, str]]:
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
    names: Set[str] = set()
    stack: List[Any] = [root]
    while stack:
        node = stack.pop()
        nm = getattr(node, "name", None)
        if nm:
            names.add(nm)
        # 子リストの取り出し（あなたの PlanNode 実装に合わせ複数候補を見る）
        children = (
            getattr(node, "children", None)
            or getattr(node, "_children", None)
            or []
        )
        try:
            stack.extend(children)
        except TypeError:
            pass
    return names

def intersect_pairs_with_network(pairs: Iterable[Tuple[str, str]], node_names: Set[str]) -> Set[Tuple[str, str]]:
    return {(n, sku) for (n, sku) in pairs if n in node_names}

# ────────────────────────────────────────────────────────────────────
# 1ペア書戻し（S生成→両レイヤ書戻し）
# ────────────────────────────────────────────────────────────────────
def write_both_layers_for_pair(conn: sqlite3.Connection,
                               scenario_id: int,
                               node_name: str,
                               product_name: str) -> Dict[str, int]:
    """
    - leafモードで行っている処理を（node, product）単位に縮退して実行。
    - PlanNode を持たなくても _NodeShim で代用できるようにする。
    戻り値: {"d_rows": .., "s_rows": .., "w_d": .., "w_s": ..}
    """
    node_obj = _NodeShim(node_name)

    # 1) まず S を注入して内部計算（demand レイヤ想定）
    d_rows, s_rows = load_leaf_S_and_compute(
        conn,
        scenario_id=scenario_id,
        node_obj=node_obj,
        product_name=product_name,
        layer="demand",
    )

    # 2) 計算結果を lot / lot_bucket に書戻し（demand/supply 両方）
    w_d, w_s = write_both_layers(
        conn,
        scenario_id=scenario_id,
        node_obj=node_obj,
        product_name=product_name,
        replace_slice=True,
    )

    return {"d_rows": int(d_rows), "s_rows": int(s_rows),
            "w_d": int(w_d), "w_s": int(w_s)}
