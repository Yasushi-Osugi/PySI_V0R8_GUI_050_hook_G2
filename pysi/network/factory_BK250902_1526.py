# network_factory.py
# -*- coding: utf-8 -*-
import csv, os
from typing import Dict, Tuple, List, Iterable
try:
    from pysi.network.node_base import PlanNode
except Exception as e:
    raise RuntimeError("PlanNode を import できません。PYTHONPATH を確認してください。") from e

def _read_rows(path: str) -> List[dict]:
    with open(path, newline='', encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def _build_tree_for_product(rows: List[dict], product_name: str) -> PlanNode:
    nodes: Dict[str, PlanNode] = {}
    for r in rows:
        if r.get("Product_name") != product_name:
            continue
        p = r["Parent_node"].strip()
        c = r["Child_node"].strip()
        lot_size = int(float(r.get("lot_size", 1) or 1))
        leadtime = int(float(r.get("leadtime", 0) or 0))

        if p not in nodes:
            nodes[p] = PlanNode(p)
        if c not in nodes:
            nodes[c] = PlanNode(c)

        parent, child = nodes[p], nodes[c]
        child.lot_size = lot_size
        child.leadtime = leadtime
        child.parent = parent
        parent.add_child(child)

    if "supply_point" in nodes:
        return nodes["supply_point"]
    # fallback: 入力の最上位（親を持たないノード）をrootに
    candidates = {n for n in nodes.values() if not getattr(n, "parent", None)}
    if not candidates:
        raise ValueError(f"product '{product_name}' のrootが見つかりません")
    return sorted(candidates, key=lambda n: n.name)[0]

def available_products(data_dir: str, direction: str = "outbound") -> List[str]:
    fname = "product_tree_outbound.csv" if direction == "outbound" else "product_tree_inbound.csv"
    rows = _read_rows(os.path.join(data_dir, fname))
    return sorted({r["Product_name"] for r in rows if r.get("Product_name")})

def factory(data_dir: str = ".", product_name: str = None, direction: str = "outbound") -> PlanNode:
    """
    orchestrator の --network から使う場合は、環境変数や固定引数で product を決める運用に。
    例: factory(data_dir="/path/to/csv", product_name="JPN_RICE_1", direction="outbound")
    """
    fname = "product_tree_outbound.csv" if direction == "outbound" else "product_tree_inbound.csv"
    path = os.path.join(data_dir, fname)
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    rows = _read_rows(path)
    if not product_name:
        # CSVに出現する最初の製品を既定に
        prods = [r["Product_name"] for r in rows if r.get("Product_name")]
        if not prods:
            raise ValueError("CSVに Product_name がありません")
        product_name = prods[0]

    root = _build_tree_for_product(rows, product_name)
    return root
