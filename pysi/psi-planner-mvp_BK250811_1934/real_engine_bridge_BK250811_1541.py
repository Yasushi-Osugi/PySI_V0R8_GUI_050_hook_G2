# real_engine_bridge.py
from typing import Any, Dict, Optional
import os, csv, io, sys, re
from engine_api import PlanNode as EPNode

DATA_DIR = os.environ.get(
    "PSI_DATA_DIR",
    r"C:\Users\ohsug\PySI_V0R8\_data_parameters\data_PySI_V0R8_bridge"
)

# ---- 公開API ---------------------------------------------------------------
def build_plan_graph(scenario_name: str,
                     product: Optional[str] = None,
                     filters: Optional[Dict[str, Any]] = None) -> EPNode:
    """product_tree_outbound.csv を読み、SKU（=Product_name）ごとの木を構築。
       product 未指定時は全SKUを super-root 配下にぶら下げて返す。"""
    ot_path = os.path.join(DATA_DIR, "product_tree_outbound.csv")
    rows = _read_rows(ot_path)

    sku_all = sorted({r.get("Product_name") or r.get("Product_n") for r in rows})
    sku_sel = [product] if (product and product in sku_all) else sku_all

    super_root = EPNode("ROOT", f"{scenario_name}-ROOT", "root")
    for sku in sku_sel:
        root = _build_tree_for_product(rows, sku)
        super_root.add_child(root)
    return super_root

# ---- 公開API ---------------------------------------------------------------




def run_core(root: EPNode, horizon_weeks: int, seed: int | None,
             overrides: Dict[str, Any] | None) -> None:
    """接続確認用（あとで実エンジンに差し替え）。各ノードにダミーKPIソースを置く。"""
    def walk(n: EPNode):
        n.attrs.setdefault("shipped_qty", 100.0)
        n.attrs.setdefault("price", 250.0)
        n.attrs.setdefault("cogs", 200.0)
        for c in n.children: walk(c)
    walk(root)

# ---- ヘルパ ---------------------------------------------------------------

# CSVのエンコーディングを自動判別（utf-8-sig優先→cp932）
def _read_rows(path: str):
    for enc in ("utf-8-sig", "cp932", "utf-8"):
        try:
            with io.open(path, "r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeError:
            continue
    # 最後に失敗したら例外
    with open(path, newline="") as f:
        return list(csv.DictReader(f))

# 列名のマッピング（ヘッダ揺れに強く）
COL = {
    "product": ("Product_name", "Product_n"),
    "parent":  ("Parent_node",  "Parent_no"),
    "child":   ("Child_node",   "Child_nod"),
    "label":   ("child_node_name", "child_node"),
    "lot":     ("lot_size",),
    "lt":      ("leadtime",),
    "flag":    ("PSI_graph_flag",),
    "tariff":  ("customs_tariff_rate",),
    "elas":    ("price_elasticity",),
}

def _g(row, key, default=None):
    for k in COL[key]:
        if k in row and row[k] != "":
            return row[k]
    return default

def _guess_type(node_id: str) -> str:
    if node_id.startswith("DAD"): return "DAD"
    if node_id.startswith("WS1"): return "WS1"
    if node_id.startswith("WS2"): return "WS2"
    if node_id.startswith("RT"):  return "RT"
    if node_id.startswith("CS"):  return "CS"
    if node_id == "supply_point": return "root"
    return "node"

REGION_PAT = re.compile(r".*[_-]([A-Z]{2,3})$")  # 末尾の _JPN / -JPN 等を抽出

def _guess_region(node_id: str) -> Optional[str]:
    m = REGION_PAT.match(node_id)
    return m.group(1) if m else None

def _build_tree_for_product(rows, product_name: str) -> EPNode:
    # Product_name で絞り、PSI_graph_flag==ON の行だけ採用（無ければ全採用）
    pr = [r for r in rows
          if (_g(r,"product")==product_name)
          and ((_g(r,"flag") or "ON") in ("ON","On","on"))]

    nodes: dict[str, EPNode] = {}

    def ensure(nid: str, label: Optional[str]=None) -> EPNode:
        if nid not in nodes:
            nodes[nid] = EPNode(
                id=nid,
                name=label or nid,
                node_type=_guess_type(nid),
                sku=product_name,
                region=_guess_region(nid),
                channel=("Retail" if nid.startswith("RT") else ("Consumer" if nid.startswith("CS") else None)),
                attrs={}
            )
        return nodes[nid]

    for r in pr:
        p = _g(r,"parent"); c = _g(r,"child"); lbl = _g(r,"label") or c
        if not p or not c:  # 欠損防御
            continue
        parent = ensure(p, p); child = ensure(c, lbl)
        # 属性（子側＝エッジの受け側にぶら下げる）
        try:
            if _g(r,"lot") not in (None,""):
                child.attrs["lot_size"] = int(float(_g(r,"lot")))
            if _g(r,"lt") not in (None,""):
                child.attrs["lead_time_days"] = int(float(_g(r,"lt")))
        except Exception:
            pass
        if _g(r,"tariff") not in (None,""):
            child.attrs["tariff_rate"] = float(_g(r,"tariff"))
        if _g(r,"elas") not in (None,""):
            child.attrs["price_elasticity"] = float(_g(r,"elas"))
        parent.add_child(child)

    # ルート推定（親だが子に現れないノード）
    children = { _g(r,"child") for r in pr }
    parents  = { _g(r,"parent") for r in pr }
    roots = [nid for nid in parents if nid and nid not in children]
    root_id = roots[0] if roots else ( "supply_point" if "supply_point" in nodes else next(iter(nodes)) )
    root = nodes[root_id]
    root.node_type = "root"
    return root


#@250811 ADD
# 1) 既存ノード→EPNode写像時に“元ノード”を保持
def _map_to_plan_node(n) -> EPNode:
    pn = EPNode(
        id=getattr(n,"id",getattr(n,"name","unknown")),
        name=getattr(n,"name",getattr(n,"id","node")),
        node_type=getattr(n,"node_type","node"),
        sku=getattr(n,"sku",None),
        region=getattr(n,"region",None),
        channel=getattr(n,"channel",None),
        attrs={}
    )
    pn.attrs["_legacy"] = n  # ← これだけ追加
    for c in getattr(n, "children", []):
        pn.add_child(_map_to_plan_node(c))
    return pn

# 2) 実行（まずは実エンジン呼び出し→なければ簡易サマリ）
def run_core(root: EPNode, horizon_weeks: int, seed: int | None,
             overrides: Dict[str, Any] | None) -> None:
    try:
        # 例：あなたの実関数に合わせて import/引数名を調整
        from psi_core.engine import run_weekly
        legacy_root = root.attrs.get("_legacy") or _find_legacy(root)
        if legacy_root is not None:
            run_weekly(legacy_root, horizon=horizon_weeks, seed=seed, overrides=overrides or {})
            _pull_back_kpis(legacy_root, root)  # psi4*→attrs へ転記
            return
    except Exception as e:
        print("[bridge] real engine call failed, fallback:", e)

    _smoke(root)  # ← 既存のダミーにフォールバック

def _find_legacy(n: EPNode):
    if "_legacy" in n.attrs: return n.attrs["_legacy"]
    for c in n.children:
        r = _find_legacy(c)
        if r is not None: return r
    return None

def _pull_back_kpis(legacy_node, ep_node: EPNode):
    """最小版：psi4demand/psi4supply の lot 数で shipped_qty を作る（精緻化は後段）"""
    lots_out = getattr(legacy_node, "psi4demand", None)
    lots_in  = getattr(legacy_node, "psi4supply", None)
    def _count(L):
        try:    return sum(len(L[w][0]) for w in range(1, len(L)))  # 週×レーン0 仮
        except: return 0
    ep_node.attrs["shipped_qty"] = float((_count(lots_out) + _count(lots_in)) / 2.0)
    # 価格/原価は当面デフォルト（後で resolve(price/cogs) に置換）
    ep_node.attrs.setdefault("price", 250.0)
    ep_node.attrs.setdefault("cogs", 200.0)
    # 子へ
    for lc, ec in zip(getattr(legacy_node, "children", []), ep_node.children):
        _pull_back_kpis(lc, ec)

