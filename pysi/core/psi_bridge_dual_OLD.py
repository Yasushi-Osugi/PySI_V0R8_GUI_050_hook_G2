# pysi/core/psi_bridge_dual.py
# Allocation ⇄ PSIのブリッジ（demand/supply二層）


# pysi/core/psi_bridge_dual.py から抜粋・確定版

from .psi_state import PSI_S, PSI_CO, PSI_I, PSI_P

def _lots_or_synth(lots, qty):
    if lots:
        out = []
        for x in lots:
            if isinstance(x, str):
                out.append(x)
            elif isinstance(x, dict) and "id" in x:
                out.append(x["id"])
        return out
    # 決定論な合成ID（簡略版）
    return [f"SYN-{abs(hash(('syn', qty)))%10000:04d}"]

def commit_replenishment_to_supply_psi(alloc: dict, state: dict, params: dict):
    """
    shipments に合わせて供給層へ補充を起票：
      - w_order に P/CO を即時記録
      - 完了イベント（to_week）も scheduled に積む
    """
    psiS = state["psi_supply"]
    prod_lead = params.get("prod_lead_weeks", {})
    order_policy = params.get("order_policy", "at_ship_week")

    for s in alloc.get("shipments", []):
        node, sku = s["src"], s["sku"]
        w_ship = int(s["week"])
        qty    = float(s.get("qty", 0.0))
        lots   = s.get("lots", [])
        lot_ids = _lots_or_synth(lots, qty)

        psi_node = psiS.get((node, sku))
        if psi_node is None:
            # 初期化漏れ防止（nodes_skus 未登録時の安全ネット）
            continue

        # 発注週の決定
        w_order = w_ship
        if order_policy.startswith("advance_by_"):
            try:
                k = int(order_policy.split("_")[-1])
                w_order = max(0, w_ship - k)
            except Exception:
                w_order = w_ship

        # ★ 即時に P/CO を積む（ここが Supply PSI[0] を空にしない肝）
        psi_node[w_order][PSI_P].extend(lot_ids)
        psi_node[w_order][PSI_CO].extend(lot_ids)

        # 完了タイミングをスケジュール（I へ入るのは settle 側で）
        done_w = w_order + int(prod_lead.get((node, sku), 0))
        state["scheduled"].append({
            "type": "produce_supply",
            "node": node, "sku": sku,
            "from_week": w_order, "to_week": done_w,
            "lots": lot_ids
        })







#from .psi_state import PSI_S, PSI_CO, PSI_I, PSI_P

def _lots_or_synth_OLD(lots, qty):
    """
    明示lotがなければ合成（V0R7風: SYN-****）
    """
    if lots:
        out = []
        for x in lots:
            if isinstance(x, str):
                out.append((x, qty))
            else:
                out.append((x.get("id", "SYN"), float(x.get("qty", qty))))
        return out
    return [(f"SYN-{abs(hash(('syn', qty)))%10000:04d}", qty)]

def _consume_I_and_append(psi, w, lots, qty, bucket_idx):
    """
    Iから消費し、指定バケツに追加（FIFO簡易、V0R7のpop_lots相当）
    """
    need = qty
    stock = psi[w][PSI_I]
    taken = []
    while need > 1e-9 and stock:
        lot = stock[0]
        take = min(lot["qty"], need)
        lot["qty"] -= take
        taken.append({"id": lot["id"], "qty": take})
        if lot["qty"] <= 1e-9:
            stock.pop(0)
        need -= take
    if need > 1e-9:
        taken.append({"id": f"SYN-{abs(hash(('synI', need)))%10000:04d}", "qty": need})
    for x in taken:
        psi[w][bucket_idx].append(x)

def _co_to_I(psi, w_from, w_to, lots):
    """
    COからIへ移管（lot消し込み）
    """
    co = psi[w_from][PSI_CO]
    for lid, q in lots:
        rem = q
        i = 0
        while rem > 1e-9 and i < len(co):
            if co[i]["id"] == lid:
                take = min(co[i]["qty"], rem)
                co[i]["qty"] -= take
                rem -= take
                if co[i]["qty"] <= 1e-9:
                    co.pop(i)
                    i -= 1
            i += 1
        psi[w_to][PSI_I].append({"id": lid, "qty": q})

def _p_co_to_I(psi, w_from, w_to, lots):
    """
    P/COからIへ（supply層用）
    """
    for idx in (PSI_P, PSI_CO):
        arr = psi[w_from][idx]
        for lid, q in lots:
            rem = q
            i = 0
            while rem > 1e-9 and i < len(arr):
                if arr[i]["id"] == lid:
                    take = min(arr[i]["qty"], rem)
                    arr[i]["qty"] -= take
                    rem -= take
                    if arr[i]["qty"] <= 1e-9:
                        arr.pop(i)
                        i -= 1
                i += 1
    for lid, q in lots:
        psi[w_to][PSI_I].append({"id": lid, "qty": q})

def commit_shipments_to_demand_psi(alloc: dict, state: dict, params: dict):
    """
    shipmentsをdemand PSIに反映（src: I→S, dst: CO→Iイベント）
    """
    psiD = state["psi_demand"]
    lt_edge = params.get("leadtime_weeks", {})
    for s in alloc.get("shipments", []):
        src, dst, sku = s["src"], s["dst"], s["sku"]
        w_ship, qty, lots = int(s["week"]), float(s["qty"]), s.get("lots", [])
        psi_src = psiD.get((src, sku))
        if psi_src:
            _consume_I_and_append(psi_src, w_ship, lots, qty, PSI_S)
        psi_dst = psiD.get((dst, sku))
        if psi_dst:
            for lid, q in _lots_or_synth(lots, qty):
                psi_dst[w_ship][PSI_CO].append({"id": lid, "qty": q})
        arr_w = w_ship + int(lt_edge.get((src, dst, sku), 0))
        state["scheduled"].append({
            "type": "receive_demand", "dst": dst, "sku": sku,
            "from_week": w_ship, "to_week": arr_w,
            "lots": _lots_or_synth(lots, qty)
        })

def commit_replenishment_to_supply_psi_OLD(alloc: dict, state: dict, params: dict):
    """
    shipmentsに応じてsupply PSIに補充（P→CO→Iイベント）
    """
    psiS = state["psi_supply"]
    prod_lead = params.get("prod_lead_weeks", {})
    order_policy = params.get("order_policy", "at_ship_week")
    for s in alloc.get("shipments", []):
        node, sku = s["src"], s["sku"]
        w_ship, qty, lots = int(s["week"]), float(s["qty"]), s.get("lots", [])
        psi_node = psiS.get((node, sku))
        if not psi_node:
            continue
        w_order = w_ship
        if order_policy.startswith("advance_by_"):
            k = int(order_policy.split("_")[-1])
            w_order = max(0, w_ship - k)
        for lid, q in _lots_or_synth(lots, qty):
            psi_node[w_order][PSI_P].append({"id": lid, "qty": q})
            psi_node[w_order][PSI_CO].append({"id": lid, "qty": q})
        done_w = w_order + int(prod_lead.get((node, sku), 0))
        state["scheduled"].append({
            "type": "produce_supply", "node": node, "sku": sku,
            "from_week": w_order, "to_week": done_w,
            "lots": _lots_or_synth(lots, qty)
        })

def settle_scheduled_events_dual(state: dict, week_idx: int):
    """
    週頭のイベント決済（CO/P→I）
    """
    psiD, psiS = state["psi_demand"], state["psi_supply"]
    rest = []
    for ev in state.get("scheduled", []):
        if ev["to_week"] != week_idx:
            rest.append(ev)
            continue
        if ev["type"] == "receive_demand":
            psi = psiD.get((ev["dst"], ev["sku"]))
            if psi:
                _co_to_I(psi, ev["from_week"], ev["to_week"], ev["lots"])
        elif ev["type"] == "produce_supply":
            psi = psiS.get((ev["node"], ev["sku"]))
            if psi:
                _p_co_to_I(psi, ev["from_week"], ev["to_week"], ev["lots"])
    state["scheduled"] = rest