# pysi/io/tree_writeback.py
from __future__ import annotations
from typing import Iterable, Set, Tuple

# いまの実体（keyword-only, node_obj前提）をそのまま使う
from pysi.io import psi_io_adapters as io


class _NodeShim:
    """名前だけ持つ最小ノード。io側は .name を参照する想定。"""
    __slots__ = ("name",)
    def __init__(self, name: str):
        self.name = name


def compute_leaf_S_for_pair(conn, scenario_id: int, node_name: str, product_name: str, layer: str = "demand"):
    """leafのS生成相当。戻り値は None（いまの版準拠）。"""
    node = _NodeShim(node_name)
    try:
        # 現行シグネチャ（keyword-only）
        return io.load_leaf_S_and_compute(
            conn, scenario_id=scenario_id, node_obj=node,
            product_name=product_name, layer=layer
        )
    except TypeError:
        # 旧版互換（位置引数・name渡し）
        return io.load_leaf_S_and_compute(conn, scenario_id, node_name, product_name)


def write_both_layers_for_pair_OLD(conn, scenario_id: int, node_name: str, product_name: str):
    """
    (node, product) ペアの Demand/Supply をDBへ書戻し。
    戻り値: {"d_rows": int, "s_rows": int}
    """
    node = _NodeShim(node_name)
    try:
        d_rows, s_rows = io.write_both_layers(
            conn, scenario_id=scenario_id, node_obj=node, product_name=product_name
        )
    except TypeError:
        # 旧版互換（位置引数・name渡し）
        d_rows, s_rows = io.write_both_layers(conn, scenario_id, node_name, product_name)
    return {"d_rows": int(d_rows), "s_rows": int(s_rows)}


def write_both_layers_for_pair(conn, scenario_id: int, node_name: str, product_name: str):
    node = _NodeShim(node_name)
    try:
        d_rows, s_rows = io.write_both_layers(
            conn, scenario_id=scenario_id, node_obj=node, product_name=product_name
        )
        return {"d_rows": int(d_rows), "s_rows": int(s_rows)}
    except TypeError:
        d_rows, s_rows = io.write_both_layers(conn, scenario_id, node_name, product_name)
        return {"d_rows": int(d_rows), "s_rows": int(s_rows)}
    except Exception as e:
        print(f"[WARN] write_both_layers_for_pair failed: node={node_name}, product={product_name} -> {e}")
        return {}




def pairs_from_weekly_demand(conn, scenario_id: int) -> Set[Tuple[str, str]]:
    rows = conn.execute("""
        SELECT n.name, p.name
        FROM weekly_demand wd
        JOIN node n    ON wd.node_id = n.id
        JOIN product p ON wd.product_id = p.id
        WHERE wd.scenario_id = ?
        GROUP BY n.name, p.name
    """, (scenario_id,)).fetchall()
    return {(r[0], r[1]) for r in rows}


def node_names_from_plan_root(root) -> Set[str]:
    seen, stack = set(), [root]
    while stack:
        cur = stack.pop()
        if cur is None: continue
        nm = getattr(cur, "name", None)
        if nm: seen.add(nm)
        for ch in getattr(cur, "children", []) or []:
            stack.append(ch)
    return seen


def intersect_pairs_with_network(db_pairs: Iterable[Tuple[str, str]], node_names: Set[str]):
    return {(n, p) for (n, p) in db_pairs if n in node_names}
