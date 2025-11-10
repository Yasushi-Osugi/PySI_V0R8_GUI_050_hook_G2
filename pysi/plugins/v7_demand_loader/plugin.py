#plugins/v7_demand_loader/plugin.py

def register(bus):
    import os, pandas as pd
    from pysi.plan.demand_generate import trans_month2week2lot_id_list
    from pysi.core.tree import get_nodes

    def load_monthly_to_Slots(root, **ctx):
        scenario_root = ctx.get("db_path") or "."
        csv_path = os.path.join(scenario_root, "sku_S_month_data.csv")
        # lot_size は暫定（CSVや設定から与える設計も可）
        df_weekly, plan_range, plan_year_st = trans_month2week2lot_id_list(csv_path, lot_size=100)

        # ISO→内部週indexへ積む（各Nodeの S=0 に割付）
        from pysi.plan.operations import _build_iso_week_index_map, _make_lot_id_list_slots_iso, set_S2psi_stop
        week_map, W = _build_iso_week_index_map(plan_year_st, plan_range)

        for n in get_nodes(root):
            pSi = _make_lot_id_list_slots_iso(df_weekly, n.name, week_map, W)  # 各週の lot_id_list
            set_S2psi_stop(n, pSi)  # n.psi4demand[w][0] へ投入

        return root

    # ✅ Hook名を pipeline 準拠に変更
    #bus.add_action("plan:post_build", load_monthly_to_Slots, priority=60)
    bus.add_action("after_tree_build", load_monthly_to_Slots, priority=60)
