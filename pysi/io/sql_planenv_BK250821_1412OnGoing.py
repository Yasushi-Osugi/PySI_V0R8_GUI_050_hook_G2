# pysi/io/sql_planenv.py

from __future__ import annotations

import sqlite3, json
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

from pysi.network.node_base import Node  # 既存Node: .name, .children, .add_child(child) を前提

# ---- 定数 ---------------------------------------------------------------
BUCKET = {"S": 0, "CO": 1, "I": 2, "P": 3}
NULL_LIKES = {None, "", "None", "NULL"}

# ---- 内部ユーティリティ -------------------------------------------------
def _connect(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con

def _load_calendar_meta(con: sqlite3.Connection) -> Tuple[int,int]:
    """
    週レンジ長Wを返す。calendar445 があればその行数、無ければ psi.iso_index の最大+1。
    (Wは psi4demand/psi4supply の週配列長になる)
    """
    try:
        r = con.execute("SELECT COUNT(*) AS c FROM calendar445").fetchone()
        if r and r["c"] > 0:
            return int(r["c"]), 0
    except sqlite3.OperationalError:
        pass
    r = con.execute("SELECT MAX(iso_index) AS mx FROM psi").fetchone()
    W = (int(r["mx"]) + 1) if (r and r["mx"] is not None) else 0
    return W, 0

def _ensure_node(nodes: Dict[str, Node], name: str) -> Node:
    n = nodes.get(name)
    if n is None:
        n = Node(name)
        nodes[name] = n
    return n

def _json_load_or_list(x) -> List[int]:
    try:
        return json.loads(x) if x else []
    except Exception:
        return []

# ---- 中核: 製品ごとの森をSQLから復元 -----------------------------------
def _load_forest_with_meta(con: sqlite3.Connection) -> Tuple[Dict[str, Node], Dict[str, set]]:
    """
    Nodeインスタンス（製品独立ではない“グローバル”）を仮生成し、
    あわせて product->node_name集合 を返す。
    ※最終的に製品ごとにクローンせず、各製品のスコープ内だけで親子リンクを張る。
    """
    nodes: Dict[str, Node] = {}
    node_rows = list(con.execute("SELECT * FROM node"))
    for r in node_rows:
        n = _ensure_node(nodes, r["node_name"])
        n.leadtime = int(r["leadtime"] or 0)
        n.SS_days  = int(r["ss_days"] or 0)
        n.long_vacation_weeks = _json_load_or_list(r["long_vacation_weeks"])

    prod_nodes: Dict[str, set] = defaultdict(set)
    for r in con.execute("SELECT node_name, product_name FROM node_product"):
        prod_nodes[r["product_name"]].add(r["node_name"])

    return nodes, prod_nodes

def _build_product_tree(con: sqlite3.Connection,
                        global_nodes: Dict[str, Node],
                        node_names: set) -> Node:
    """
    1製品のスコープ(node_names)だけで親子リンクを構成し root を決定する。
    最優先: 'supply_point' が居ればそれを root に。
    無ければ 親がNULL/スコープ外 のノードを候補にし、子を持つものを優先。
    """
    # まずスコープ内の Node を shallow コピー（子配列をリセット）
    local: Dict[str, Node] = {}
    for nm in node_names:
        base = global_nodes[nm]
        clone = Node(base.name)
        clone.leadtime = getattr(base, "leadtime", 0)
        clone.SS_days  = getattr(base, "SS_days", 0)
        clone.long_vacation_weeks = list(getattr(base, "long_vacation_weeks", []))
        local[nm] = clone

    # 親子リンク（親がスコープ内にある場合のみ接続）
    for r in con.execute("SELECT node_name, parent_name FROM node WHERE node_name IN ({})".format(
        ",".join(["?"]*len(node_names))
    ), tuple(node_names)):
        child_name = r["node_name"]
        parent_name = r["parent_name"]
        parent_name = None if parent_name in NULL_LIKES else parent_name
        if parent_name and parent_name in local:
            parent = local[parent_name]
            child  = local[child_name]
            parent.add_child(child)

    # root 選定
    if "supply_point" in local:
        return local["supply_point"]

    # 親がスコープ内にいないノード（親がNULL/スコープ外）を候補に
    candidates = []
    for r in con.execute("SELECT node_name, parent_name FROM node WHERE node_name IN ({})".format(
        ",".join(["?"]*len(node_names))
    ), tuple(node_names)):
        nm = r["node_name"]
        pn = r["parent_name"]
        if pn in NULL_LIKES or (pn and pn not in node_names):
            candidates.append(nm)

    if candidates:
        with_children = [nm for nm in candidates if getattr(local[nm], "children", [])]
        root_name = with_children[0] if with_children else candidates[0]
        return local[root_name]

    # フォールバック
    return local[next(iter(local.keys()))]

def _attach_psi(con: sqlite3.Connection, root: Node, product_name: str, weeks_count: int):
    """
    psi テーブルから demand面の psi を復元し、ツリー全ノードにセット。
    形式: 各ノード n に n.psi4demand[w][bucket_idx] = [lot_id,...]
    """
    # まず対象製品に属するノード集合を特定
    node_names = {r["node_name"] for r in con.execute(
        "SELECT node_name FROM node_product WHERE product_name=?", (product_name,))}
    if not node_names:
        return

    # ノード名→Nodeインスタンス解決（rootからDFS）
    def _walk(n: Node):
        st = [n]
        seen = set()
        while st:
            x = st.pop()
            if id(x) in seen: 
                continue
            seen.add(id(x))
            yield x
            for c in getattr(x, "children", []) or []:
                st.append(c)

    name2node = {n.name: n for n in _walk(root)}

    # 初期化（全週×4バケツ）
    for n in name2node.values():
        n.psi4demand = [[[ ] for _ in range(4)] for __ in range(weeks_count)]

    # 取込：psi(node_name, product_name, iso_index, bucket, lot_id)
    # bucketは 'S','CO','I','P'
    for r in con.execute(
        "SELECT node_name, iso_index, bucket, lot_id "
        "FROM psi WHERE product_name=? ORDER BY iso_index",
        (product_name,)
    ):
        nm = r["node_name"]
        if nm not in name2node:
            continue
        w = int(r["iso_index"] or 0)
        if not (0 <= w < weeks_count):
            continue
        b = BUCKET.get((r["bucket"] or "S").upper(), 0)
        lot_id = r["lot_id"]
        name2node[nm].psi4demand[w][b].append(lot_id)

def _attach_price_tags(con: sqlite3.Connection, root: Node, product_name: str):
    """
    price_tag(node_name, product_name, tag in('ASIS','TOBE'), price)
    を Node属性 offering_price_ASIS / offering_price_TOBE として反映
    """
    rows = list(con.execute(
        "SELECT node_name, tag, price FROM price_tag WHERE product_name=?",
        (product_name,)
    ))
    if not rows:
        return

    # name -> Node (DFS)
    def _walk(n: Node):
        st = [n]
        seen = set()
        while st:
            x = st.pop()
            if id(x) in seen:
                continue
            seen.add(id(x))
            yield x
            for c in getattr(x, "children", []) or []:
                st.append(c)
    name2node = {n.name: n for n in _walk(root)}

    for r in rows:
        nm, tag, price = r["node_name"], (r["tag"] or "").upper(), float(r["price"] or 0.0)
        n = name2node.get(nm)
        if not n: 
            continue
        if tag == "ASIS":
            setattr(n, "offering_price_ASIS", price)
        elif tag == "TOBE":
            setattr(n, "offering_price_TOBE", price)



def _attach_unit_costs(con: sqlite3.Connection, root: Node, product_name: str):
    """
    price_money_per_lot(node_name, product_name, direct_materials_costs, tariff_cost)
    を Node 属性 unit_cost_dm / unit_cost_tariff に反映。
    """
    rows = list(con.execute(
        "SELECT node_name, direct_materials_costs, tariff_cost "
        "FROM price_money_per_lot WHERE product_name=?",
        (product_name,)
    ))
    if not rows:
        return

    # name -> Node (DFS)
    def _walk(n: Node):
        st = [n]; seen=set()
        while st:
            x = st.pop()
            if id(x) in seen: continue
            seen.add(id(x)); yield x
            for c in getattr(x, "children", []) or []:
                st.append(c)
    name2node = {n.name: n for n in _walk(root)}

    for r in rows:
        nm = r["node_name"]
        n = name2node.get(nm)
        if not n: 
            continue
        setattr(n, "unit_cost_dm", float(r["direct_materials_costs"] or 0.0))
        setattr(n, "unit_cost_tariff", float(r["tariff_cost"] or 0.0))



class SqlPlanEnv:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.product_name_list: List[str] = []
        self.prod_tree_dict_OT: Dict[str, Node] = {}
        self.prod_tree_dict_IN: Dict[str, Node] = {}   # INも保持（現状はOTと同根）
        self._build()

    def get_roots(self, product_name: str):
        r_ot = self.prod_tree_dict_OT.get(product_name)
        r_in = self.prod_tree_dict_IN.get(product_name, r_ot)
        return (r_ot, r_in)

    def reload(self):
        """DBの最新状態を再読込してツリー/PSI/価格を再構築。"""
        self.product_name_list.clear()
        self.prod_tree_dict_OT.clear()
        self.prod_tree_dict_IN.clear()
        self._build()

    def _build(self):
        with _connect(self.db_path) as con:
            W, _ = _load_calendar_meta(con)
            global_nodes, prod_nodes = _load_forest_with_meta(con)
            self.product_name_list = sorted(prod_nodes.keys())

            for product, node_names in prod_nodes.items():
                if not node_names:
                    continue
                root = _build_product_tree(con, global_nodes, node_names)
                if W > 0:
                    _attach_psi(con, root, product, weeks_count=W)
                _attach_price_tags(con, root, product)   # ASIS/TOBE
                _attach_unit_costs(con, root, product)   # 原価（材料/関税）

                self.prod_tree_dict_OT[product] = root

            # 現段階はCOPY方式なので IN は OT と同根でよい
            self.prod_tree_dict_IN = {p: r for p, r in self.prod_tree_dict_OT.items()}



# ---- 公開クラス: SQL版 PlanEnv 相当 ------------------------------------
class SqlPlanEnv:
    """
    CSV版PlanEnvの最小互換:
      - product_name_list
      - prod_tree_dict_OT: {product: root(Node)}
      - get_roots(product) -> (root_out, root_in)  ※ここでは OUT/IN 同一rootを返す
    """


    def __init__(self, db_path: str):
        self.db_path = db_path
        self.product_name_list: List[str] = []
        self.prod_tree_dict_OT: Dict[str, Node] = {}
        self.prod_tree_dict_IN: Dict[str, Node] = {}   # ★ 追加
        self._build()

    def get_roots(self, product_name: str):
        # ★ OT/IN 両方返す（INが無ければOTで代用）
        r_ot = self.prod_tree_dict_OT.get(product_name)
        r_in = self.prod_tree_dict_IN.get(product_name, r_ot)
        return (r_ot, r_in)

    def _build(self):
        with _connect(self.db_path) as con:
            W, _ = _load_calendar_meta(con)
            global_nodes, prod_nodes = _load_forest_with_meta(con)
            self.product_name_list = sorted(prod_nodes.keys())

            for product, node_names in prod_nodes.items():
                if not node_names:
                    continue
                root = _build_product_tree(con, global_nodes, node_names)
                if W > 0:
                    _attach_psi(con, root, product, weeks_count=W)
                _attach_price_tags(con, root, product)
                self.prod_tree_dict_OT[product] = root

            # ★ INは現段階 COPY方式のためOTをそのまま使う
            self.prod_tree_dict_IN = {p: r for p, r in self.prod_tree_dict_OT.items()}
