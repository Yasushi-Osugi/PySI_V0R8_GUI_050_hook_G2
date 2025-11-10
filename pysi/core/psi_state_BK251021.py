# pysi/core/psi_state.py
# PSIリスト構造の定義（V0R7継承: 週×[S, CO, I, P] with lot）

PSI_S, PSI_CO, PSI_I, PSI_P = 0, 1, 2, 3  # S: Sales/Shipment, CO: Carry Over/On Order, I: Inventory, P: Purchase

def make_psi(n_weeks: int):
    """
    週ごとに [S, CO, I, P] のリストを作成。各バケツの要素はlot辞書（{"id": str, "qty": float, ...}）
    """
    return [[[],[],[],[]] for _ in range(n_weeks)]

def init_state(n_weeks: int, nodes_skus: list):
    """
    state初期化。psi_demand/psi_supplyを{(node, sku): psi_list}で保持。
    """
    state = {
        "psi_demand": {},
        "psi_supply": {},
        "scheduled": []  # 未来イベント（到着/生産完了）
    }
    for node, sku in nodes_skus:
        state["psi_demand"][(node, sku)] = make_psi(n_weeks)
        state["psi_supply"][(node, sku)] = make_psi(n_weeks)
    return state
