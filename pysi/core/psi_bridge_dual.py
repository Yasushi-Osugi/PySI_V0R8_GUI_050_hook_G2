# pysi/core/psi_bridge_dual.py
# Allocation ⇄ PSI のブリッジ（demand/supply 二層）
# 仕様: PSIは「lot_ID のリスト」を保持し、数量は len(list) で算出する

from __future__ import annotations
from typing import Dict, List, Tuple, Callable, Any
from .psi_state import PSI_S, PSI_CO, PSI_I, PSI_P

# ===== demand_generate.py と同じ規約を流用 =====
LOT_SEP = "-"  # node/product に使わない安全な区切り
def _sanitize_token(s: str) -> str:
    """区切り記号や空白を除去してロットIDのプレフィクスに安全なトークンにする"""
    return str(s).replace(LOT_SEP, "").replace(" ", "").strip()

# ---- ISO年週の解決 -----------------------------------------------------------
def _resolve_year_week(week_idx: int, *, ctx: Dict[str, Any], params: Dict[str, Any]) -> Tuple[int, int]:
    """
    週インデックス -> (ISO年, ISO週) を解決。
    優先順位:
      1) ctx["resolve_year_week"](week_idx) があればそれを使用（推奨）
      2) ctx["calendar"]["resolve_year_week"](week_idx) があれば使用
      3) フォールバック: params["iso_year_start"] から 52週ロール（簡易）
    """
    # 1) 明示リゾルバ
    fn = ctx.get("resolve_year_week")
    if callable(fn):
        return fn(week_idx)

    # 2) calendar 側のリゾルバ
    cal = ctx.get("calendar") or {}
    fn2 = cal.get("resolve_year_week")
    if callable(fn2):
        return fn2(week_idx)

    # 3) 簡易ロールオーバー（53週は考慮しない簡易版）
    base_year = int(params.get("iso_year_start", 2025))
    y = base_year + (week_idx // 52)
    w = (week_idx % 52) + 1
    return (y, w)

# ---- lot サイズの解決 ---------------------------------------------------------
def _lot_size_lookup(node: str, sku: str, *, params: Dict[str, Any]) -> int:
    """
    lotサイズ（=1ロットあたり何個か）を返す。PSIは“lot_ID の数”を積む前提なので、
    Ship qty(整数) を lot_size で天井割りして S_lot を決める。
    優先順位:
      1) params["lot_size_lookup"](node, sku)
      2) params["lot_size_map"][(node, sku)] / params["lot_size_map"][sku]
      3) デフォルト 1
    """
    fn = params.get("lot_size_lookup")
    if callable(fn):
        try:
            v = int(fn(node, sku))
            return max(1, v)
        except Exception:
            pass

    mp = params.get("lot_size_map", {})
    if isinstance(mp, dict):
        if (node, sku) in mp:
            try:
                return max(1, int(mp[(node, sku)]))
            except Exception:
                pass
        if sku in mp:
            try:
                return max(1, int(mp[sku]))
            except Exception:
                pass
    return 1

# ---- lot_ID 生成（demand_generate.py の規約互換） -----------------------------
def _mk_lot_ids(node: str, sku: str, year: int, week: int, count: int) -> List[str]:
    """
    形式: NODE-PRODUCT-YYYYWWNNNN
    - NODE/PRODUCT はサニタイズして LOT_SEP で連結
    - NNNN は 1 始まりのゼロ詰め 4桁
    """
    nn = _sanitize_token(node)
    pn = _sanitize_token(sku)
    if count <= 0:
        return []
    return [f"{nn}{LOT_SEP}{pn}{LOT_SEP}{year}{week:02d}{i+1:04d}" for i in range(count)]

def _normalize_lot_ids(lots: List[Any]) -> List[str]:
    """
    入力 lots が:
      - 文字列IDの配列: そのまま返す
      - dictの配列: {"id": "..."} からID抽出
      - それ以外/None: 空配列
    """
    if not lots:
        return []
    out: List[str] = []
    for x in lots:
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, dict) and "id" in x:
            out.append(str(x["id"]))
        else:
            # 想定外は無視（安定運用のため）
            continue
    return out

# ---- PSI 操作（リストの移動: list-of-IDs前提）---------------------------------
def _move_ids(src_list: List[str], dst_list: List[str], ids: List[str]) -> None:
    """
    src_list から ids を個数分だけ“1個ずつ”削除し、dst_list に同数追加する。
    （multiset のように扱う）
    """
    if not ids:
        return
    # CO や P は「週 from」に積まれているはずなので、そこから剥がすイメージ
    for lid in ids:
        try:
            src_list.remove(lid)  # 初回一致のみ除去（1個だけ）
        except ValueError:
            # 見つからなければスキップ（冪等性を優先）
            pass
        dst_list.append(lid)

# ---- demand 層: shipments → S と CO(→Iは settle で) --------------------------
def commit_shipments_to_demand_psi(alloc: dict, state: dict, params: dict, **ctx):
    """
    shipments を demand PSI に反映。
      - src 側: S[w] に lot_ID を積む（I 消費ロジックは別途/将来拡張）
      - dst 側: CO[w_ship] に lot_ID を積む（到着は settle で I[w_arr] に移す）
      - lot_ID が未指定なら、leaf（=dst）で ISO年週に基づき生成
    """
    psiD: Dict[Tuple[str, str], List[List[List[str]]]] = state["psi_demand"]
    lt_edge = params.get("leadtime_weeks", {})  # {(src,dst,sku): L}
    for s in alloc.get("shipments", []):
        src, dst, sku = s["src"], s["dst"], s["sku"]
        w_ship = int(s["week"])
        qty = int(round(float(s.get("qty", 0))))
        if qty <= 0:
            continue

        # 1) lot_ID 決定
        ids = _normalize_lot_ids(s.get("lots", []))
        if not ids:
            y, w = _resolve_year_week(w_ship, ctx=ctx, params=params)
            # leaf（dst）で lot を起こす（需要起点）
            lot_size = _lot_size_lookup(dst, sku, params=params)
            s_lot = max(1, (qty + lot_size - 1) // lot_size)  # 天井割り
            ids = _mk_lot_ids(dst, sku, y, w, s_lot)

        # 2) src 側 S に積む
        psi_src = psiD.get((src, sku))
        if psi_src is not None:
            psi_src[w_ship][PSI_S].extend(ids)

        # 3) dst 側 CO に積む（到着は event で）
        psi_dst = psiD.get((dst, sku))
        if psi_dst is not None:
            psi_dst[w_ship][PSI_CO].extend(ids)

        # 4) 到着イベントを積む
        arr_w = w_ship + int(lt_edge.get((src, dst, sku), 0))
        state["scheduled"].append({
            "type": "receive_demand",
            "dst": dst,
            "sku": sku,
            "from_week": w_ship,
            "to_week": arr_w,
            "lots": list(ids),  # list[str]
        })

# ---- supply 層: 補充（P/CO→I は settle で）-----------------------------------
def commit_replenishment_to_supply_psi(alloc: dict, state: dict, params: dict, **ctx):
    """
    shipments に合わせて、src ノードで補充を起票（P と CO）。
      - order_policy:
          "at_ship_week"     : w_order = w_ship
          "advance_by_{k}"   : w_order = max(0, w_ship - k)
      - lot_ID が未指定なら、src（補充元）で ISO年週に基づき生成
    """
    psiS: Dict[Tuple[str, str], List[List[List[str]]]] = state["psi_supply"]
    prod_lead = params.get("prod_lead_weeks", {})       # {(node,sku): Lp}
    order_policy = str(params.get("order_policy", "at_ship_week"))

    for s in alloc.get("shipments", []):
        node, sku = s["src"], s["sku"]
        w_ship = int(s["week"])
        qty = int(round(float(s.get("qty", 0))))
        if qty <= 0:
            continue

        # 発注週の決定
        if order_policy.startswith("advance_by_"):
            try:
                k = int(order_policy.split("_")[-1])
            except Exception:
                k = 0
            w_order = max(0, w_ship - k)
        else:
            w_order = w_ship

        # lot_ID 決定
        ids = _normalize_lot_ids(s.get("lots", []))
        if not ids:
            y, w = _resolve_year_week(w_order, ctx=ctx, params=params)
            lot_size = _lot_size_lookup(node, sku, params=params)
            s_lot = max(1, (qty + lot_size - 1) // lot_size)
            ids = _mk_lot_ids(node, sku, y, w, s_lot)

        # P と CO に積む
        psi_node = psiS.get((node, sku))
        if psi_node is not None:
            psi_node[w_order][PSI_P].extend(ids)
            psi_node[w_order][PSI_CO].extend(ids)

        # 生産完了イベント
        done_w = w_order + int(prod_lead.get((node, sku), 0))
        state["scheduled"].append({
            "type": "produce_supply",
            "node": node,
            "sku": sku,
            "from_week": w_order,
            "to_week": done_w,
            "lots": list(ids),  # list[str]
        })

# ---- 週頭のイベント決済（CO/P → I）-------------------------------------------
def settle_scheduled_events_dual(state: dict, week_idx: int):
    """
    週頭に scheduled を走査し、to_week == week_idx のイベントを決済。
      - demand: CO[from] → I[to]
      - supply: (P[from],CO[from]) → I[to]
    """
    psiD = state["psi_demand"]
    psiS = state["psi_supply"]
    rest = []
    for ev in state.get("scheduled", []):
        if int(ev.get("to_week", -1)) != int(week_idx):
            rest.append(ev)
            continue

        lots: List[str] = list(ev.get("lots", []))
        if not lots:
            continue

        if ev["type"] == "receive_demand":
            dst = ev["dst"]; sku = ev["sku"]
            w_from = int(ev["from_week"]); w_to = int(ev["to_week"])
            psi = psiD.get((dst, sku))
            if psi is not None:
                # CO[w_from] から I[w_to] へIDを移動
                _move_ids(psi[w_from][PSI_CO], psi[w_to][PSI_I], lots)

        elif ev["type"] == "produce_supply":
            node = ev["node"]; sku = ev["sku"]
            w_from = int(ev["from_week"]); w_to = int(ev["to_week"])
            psi = psiS.get((node, sku))
            if psi is not None:
                # P[w_from] / CO[w_from] から I[w_to] へIDを移動
                _move_ids(psi[w_from][PSI_P],  psi[w_to][PSI_I], lots)
                _move_ids(psi[w_from][PSI_CO], psi[w_to][PSI_I], lots)

    state["scheduled"] = rest
