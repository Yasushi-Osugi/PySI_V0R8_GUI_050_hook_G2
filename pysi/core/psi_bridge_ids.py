# pysi/core/psi_bridge_ids.py
# 「idリストだけ」で PSI を回すブリッジ。数量は len(list) で計算。

from .psi_state import PSI_S, PSI_CO, PSI_I, PSI_P

def _mk_syn_id(seed: str) -> str:
    # 実行ごとに安定させたいなら別生成器に差し替え可
    return f"SYN-{abs(hash(seed))%100000:05d}"

def _ids_or_synth(lots, qty: float, node: str, sku: str, week: int, lot_size: float) -> list[str]:
    """
    lot_ID配列を返す。lots が空で qty>0 の場合、qty/lot_size を四捨五入して合成IDを生成。
    - lots: None/[]/list[str]/list[dict{id,qty}]/list[tuple(id,qty)] を許容（idだけ抽出）
    - qty: 参考値（lots未指定時の合成個数の元）
    - lot_size: 1ロットあたりの数量（既定=1.0）
    """
    out: list[str] = []
    if lots:
        for x in lots:
            if isinstance(x, str):
                out.append(x)
            elif isinstance(x, dict) and "id" in x:
                out.append(str(x["id"]))
            elif isinstance(x, tuple) and len(x) >= 1:
                out.append(str(x[0]))
            # その他は無視（安全側）
        if out:
            return out
    # lotsが無い → qty を lot_size で割って個数化
    if qty and lot_size > 0:
        n = int(round(float(qty) / float(lot_size)))
    else:
        n = 0
    if n <= 0:
        n = 1  # 非ゼロの動作にしたいときのフォールバック（要件に応じて0でも可）
    base = f"{node}:{sku}:{week}:{qty}:{lot_size}"
    return [_mk_syn_id(f"{base}:{i}") for i in range(n)]

def _remove_ids(bucket: list[str], ids: list[str]):
    """bucket から ids を削除（最初の一致を順次取り除く）"""
    if not bucket or not ids:
        return
    # O(n*m)だが、V0R7流の高速実装は別途（set/map）最適化で
    for lid in ids:
        try:
            idx = bucket.index(lid)
            bucket.pop(idx)
        except ValueError:
            pass

def _append_ids(bucket: list[str], ids: list[str]):
    if ids:
        bucket.extend(ids)

def commit_shipments_to_demand_psi_ids(alloc: dict, state: dict, params: dict):
    """
    shipments を demand PSI に反映（idリスト版）:
      - src: S[w] にlot_IDを積む（I消し込みはここでは行わず、I(w)=I(w-1)+P(w)-S(w)の計算系に委ね）
      - dst: CO[w] にlot_IDを起票
      - receive_demand イベントを予定（CO[from]→I[to] に移管）
    """
    psiD = state["psi_demand"]
    lt_edge = params.get("leadtime_weeks", {})
    lot_size_map = params.get("lot_size", {})  # {sku: lot_size} or { (node,sku): lot_size }

    for s in alloc.get("shipments", []):
        src, dst, sku = s["src"], s["dst"], s["sku"]
        w_ship = int(s["week"]); qty = float(s.get("qty", 0.0)); lots = s.get("lots", [])
        lot_size = lot_size_map.get((src, sku), lot_size_map.get(sku, 1.0))

        ids = _ids_or_synth(lots, qty, src, sku, w_ship, lot_size)

        psi_src = psiD.get((src, sku))
        if psi_src is not None:
            _append_ids(psi_src[w_ship][PSI_S], ids)

        psi_dst = psiD.get((dst, sku))
        if psi_dst is not None:
            _append_ids(psi_dst[w_ship][PSI_CO], ids)

        arr_w = w_ship + int(lt_edge.get((src, dst, sku), 0))
        state["scheduled"].append({
            "type": "receive_demand",
            "dst": dst, "sku": sku,
            "from_week": w_ship, "to_week": arr_w,
            "lots": ids  # ← list[str]
        })

def commit_replenishment_to_supply_psi_ids(alloc: dict, state: dict, params: dict):
    """
    shipments に応じて supply PSI へ補充（idリスト版）:
      - w_order に P[w]/CO[w] を即時起票
      - produce_supply イベントを予定（P/CO[from]→I[to] に移管）
    """
    psiS = state["psi_supply"]
    prod_lead = params.get("prod_lead_weeks", {})
    order_policy = params.get("order_policy", "at_ship_week")
    lot_size_map = params.get("lot_size", {})  # 同上

    for s in alloc.get("shipments", []):
        node, sku = s["src"], s["sku"]
        w_ship = int(s["week"]); qty = float(s.get("qty", 0.0)); lots = s.get("lots", [])
        lot_size = lot_size_map.get((node, sku), lot_size_map.get(sku, 1.0))

        psi_node = psiS.get((node, sku))
        if psi_node is None:
            continue

        w_order = w_ship
        if order_policy.startswith("advance_by_"):
            try:
                k = int(order_policy.split("_")[-1])
                w_order = max(0, w_ship - k)
            except Exception:
                w_order = w_ship

        ids = _ids_or_synth(lots, qty, node, sku, w_order, lot_size)

        _append_ids(psi_node[w_order][PSI_P],  ids)
        _append_ids(psi_node[w_order][PSI_CO], ids)

        done_w = w_order + int(prod_lead.get((node, sku), 0))
        state["scheduled"].append({
            "type": "produce_supply",
            "node": node, "sku": sku,
            "from_week": w_order, "to_week": done_w,
            "lots": ids  # ← list[str]
        })

def settle_scheduled_events_ids(state: dict, week_idx: int):
    """
    週頭のイベント決済（idリストを CO/P → I へ移す）
    """
    psiD, psiS = state["psi_demand"], state["psi_supply"]
    rest = []
    for ev in state.get("scheduled", []):
        if ev["to_week"] != week_idx:
            rest.append(ev)
            continue
        lots = ev.get("lots", [])
        if ev["type"] == "receive_demand":
            key = (ev["dst"], ev["sku"])
            psi = psiD.get(key)
            if psi:
                _remove_ids(psi[ev["from_week"]][PSI_CO], lots)
                _append_ids(psi[ev["to_week"]][PSI_I], lots)
        elif ev["type"] == "produce_supply":
            key = (ev["node"], ev["sku"])
            psi = psiS.get(key)
            if psi:
                _remove_ids(psi[ev["from_week"]][PSI_P],  lots)
                _remove_ids(psi[ev["from_week"]][PSI_CO], lots)
                _append_ids(psi[ev["to_week"]][PSI_I], lots)
    state["scheduled"] = rest
