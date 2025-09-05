250708Tryexcept_indent.py


if "P_month_data.csv" in data_file_list:
    try:
        p_path = os.path.join(self.directory, "P_month_data.csv")
        df_p_month = pd.read_csv(p_path, encoding='utf-8-sig')

        unique_nodes = df_p_month["node_name"].unique()

        # 月次→週次変換＆Lot ID生成（複数年対応）
        df_weekly_p, plan_range_p, plan_year_st_p = convert_monthly_to_weekly_p(df_p_month, self.lot_size)

        # PSI Planner全体の計画開始年との整合性を確認
        assert plan_year_st_p == self.plan_year_st, (
            f"P data year start {plan_year_st_p} mismatches PSI plan start {self.plan_year_st}"
        )

        # ノード単位で週次 P_lot を登録
        set_df_Plots2psi4supply(self.nodes_outbound, df_weekly_p, self.plan_year_st)

        # Step 1.5: キャパシティ算出
        self.derive_weekly_capacity_from_plots()

        print(f"[INFO] Loaded P_month_data.csv → psi4supply populated for {len(df_weekly_p)} entries")

        # Step 2: S_lot → P_lot 割当処理
        for node_name in unique_nodes:  # node_name is DADxxx
            try:
                dad_node = self.nodes_outbound[node_name]

                # psi4demand から需要ロットを収集
                demand_map = {
                    w: dad_node.psi4demand[w][0]
                    for w in range(len(dad_node.psi4demand))
                    if dad_node.psi4demand[w][0]
                }

                # キャパシティ情報の存在確認
                if node_name not in self.weekly_cap_dict:
                    print(f"[WARNING] No weekly capacity data for node {node_name}")
                    continue

                supply_weeks = self.weekly_cap_dict[node_name]

                # perform_allocation 実行
                alloc_result, alloc_links, alloc_warn = perform_allocation(
                    node=dad_node,
                    demand_map=demand_map,
                    supply_weeks=supply_weeks
                )

                print(f"[INFO] Allocation completed for {node_name}: {len(alloc_links)} links")
                if alloc_warn:
                    print(f"[WARNING] Allocation issues for {node_name}:\n" + "\n".join(alloc_warn))

                def allocation_result_to_psi4supply(allocation_result):
                    max_week = max(allocation_result.keys(), default=0)
                    psi4supply = [[[], [], [], []] for _ in range(max_week + 1)]
                    for w, lots in allocation_result.items():
                        psi4supply[w][3] = lots
                    return psi4supply

                psi4supply = allocation_result_to_psi4supply(alloc_result)

                for w in range(1, self.plan_range * 53):
                    if w < len(psi4supply) and len(psi4supply[w][3]) > 0:
                        dad_node.psi4supply[w][3] = copy.deepcopy(psi4supply[w][3])

            except Exception as e:
                print(f"[ERROR] Allocation error for {node_name}: {e}")

    except Exception as e:
        print(f"[FATAL ERROR] Failed to process P_month_data.csv: {e}")
else:
    print("warning: P_month_data.csv is missing")


