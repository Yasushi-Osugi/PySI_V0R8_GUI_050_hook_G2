# pysi/core/psi_state.py
# PSI = 週配列 × [S, CO, I, P]、各要素は「lot_ID のリスト」だけ（数量は len(list) で算出）

PSI_S, PSI_CO, PSI_I, PSI_P = 0, 1, 2, 3

def make_psi(n_weeks: int):
    # 週ごとに [S, CO, I, P] を用意。各バケツは list[str]（lot_ID の配列）
    return [[[], [], [], []] for _ in range(n_weeks)]

def init_state(n_weeks: int, nodes_skus: list[tuple[str, str]]):
    """
    state:
      - psi_demand[(node, sku)] = week->[S,CO,I,P] （各バケツ list[str]）
      - psi_supply[(node, sku)] = 同上
      - scheduled: 将来イベント（Iへの移管）を格納
    """
    state = {
        "psi_demand": {},
        "psi_supply": {},
        "scheduled": []
    }
    for node, sku in nodes_skus:
        state["psi_demand"][(node, sku)] = make_psi(n_weeks)
        state["psi_supply"][(node, sku)] = make_psi(n_weeks)
    return state

