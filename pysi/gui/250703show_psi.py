


week_start = 1
week_end = self.plan_range * 53 - 1  # 2025〜2027年分までに限定

psi_data = []
...

# カレンダー処理
cal = Calendar445(start_year=self.plan_year_st, plan_range=self.plan_range)
week_to_yymm = {w: y for w, y in cal.get_week_labels().items() if week_start <= w <= week_end}
month_end_weeks = [w for w in cal.get_month_end_weeks() if w <= week_end]




# **************************
# collect_psi_data
# **************************


def collect_psi_data(node, D_S_flag, week_start, week_end, psi_data):
    if D_S_flag == "demand":
        psi_lots = []
        df_demand_plan = map_psi_lots2df(node, D_S_flag, psi_lots)
        df_init = df_demand_plan
    elif D_S_flag == "supply":
        psi_lots = []
        df_supply_plan = map_psi_lots2df(node, D_S_flag, psi_lots)
        df_init = df_supply_plan
    else:
        print("error: D_S_flag should be demand or supply")
        return

    # 修正：week_end の範囲超え防止
    if not df_init.empty:
        max_week = df_init["week"].max()
        week_end = min(week_end, max_week)

    condition1 = df_init["node_name"] == node.name
    condition2 = (df_init["week"] >= week_start) & (df_init["week"] <= week_end)
    df = df_init[condition1 & condition2]

    # デバッグ用 print（必要なら）
    print(f"[{node.name}] PSI df shape: {df.shape}")
    print(df[df["s-co-i-p"] == 3].head())  # P
    print(df[df["s-co-i-p"] == 2].head())  # I
    print(df[df["s-co-i-p"] == 0].head())  # S

    line_data_2I = df[df["s-co-i-p"].isin([2])]
    bar_data_0S = df[df["s-co-i-p"] == 0]
    bar_data_3P = df[df["s-co-i-p"] == 3]

    line_plot_data_2I = line_data_2I.groupby("week")["lot_id"].count()
    bar_plot_data_3P = bar_data_3P.groupby("week")["lot_id"].count()
    bar_plot_data_0S = bar_data_0S.groupby("week")["lot_id"].count()

    revenue = round(node.eval_cs_price_sales_shipped)
    profit = round(node.eval_cs_profit)
    profit_ratio = round((profit / revenue) * 100, 1) if revenue != 0 else 0

    psi_data.append((node.name, revenue, profit, profit_ratio, line_plot_data_2I, bar_plot_data_3P, bar_plot_data_0S))





    def show_psi(self, bound, layer): # Calendar445
        print("making PSI graph data...")

        week_start = 1

        week_end = self.plan_range * 53
        #week_end = ( self.plan_range - 1 ) * 53

        psi_data = []

        if bound not in ["outbound", "inbound"]:
            print("error: outbound or inbound must be defined for PSI layer")
            return

        if layer not in ["demand", "supply"]:
            print("error: demand or supply must be defined for PSI layer")
            return

        def traverse_nodes(node):
            for child in node.children:
                traverse_nodes(child)
            collect_psi_data(node, layer, week_start, week_end, psi_data)

        if bound == "outbound":
            traverse_nodes(self.root_node_outbound)
        else:
            traverse_nodes(self.root_node_inbound)

        # 4-4-5カレンダーの横軸ラベルと月末週を取得
        cal = Calendar445(start_year=self.plan_year_st, plan_range=self.plan_range)
        week_to_yymm = cal.get_week_labels()
        month_end_weeks = cal.get_month_end_weeks()

        fig, axs = plt.subplots(len(psi_data), 1, figsize=(6, len(psi_data) * 1.5))  

        #fig, axs = plt.subplots(len(psi_data), 1, figsize=(5, len(psi_data) * 1))  # 高さ控えめ

        # グラフ全体の横幅を 8インチ、各サブプロットの高さを 1.5インチ 
        # にしたい場合、次のように変更します。
        # fig, axs = plt.subplots(len(psi_data), 1, figsize=(8, len(psi_data) * 1.5))



        if len(psi_data) == 1:
            axs = [axs]

        for ax, (node_name, revenue, profit, profit_ratio, line_plot_data_2I, bar_plot_data_3P, bar_plot_data_0S) in zip(axs, psi_data):
            ax2 = ax.twinx()

            ax.bar(line_plot_data_2I.index, line_plot_data_2I.values, color='r', alpha=0.6)
            ax.bar(bar_plot_data_3P.index, bar_plot_data_3P.values, color='g', alpha=0.6)
            ax2.plot(bar_plot_data_0S.index, bar_plot_data_0S.values, color='b')

            ax.set_ylabel('I&P Lots', fontsize=10) #@250702 fantsize 8=>10
            ax2.set_ylabel('S Lots', fontsize=10)
            ax.set_title(f'Node: {node_name} | REVENUE: {revenue:,} | PROFIT: {profit:,} | PROFIT_RATIO: {profit_ratio}%', fontsize=10)

            # 共通時間軸設定
            ax.set_xlim(week_start, week_end)
            ax.set_xticks(list(week_to_yymm.keys()))
            ax.set_xticklabels(list(week_to_yymm.values()), rotation=45, fontsize=8)

            # 月末週のグレーアウト
            for week in month_end_weeks:
                ax.axvspan(week - 0.5, week + 0.5, color='gray', alpha=0.1)

        fig.tight_layout(pad=0.5)

        print("making PSI figure and widget...")

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        canvas_psi = FigureCanvasTkAgg(fig, master=self.scrollable_frame)
        canvas_psi.draw()
        canvas_psi.get_tk_widget().pack(fill=tk.BOTH, expand=True)





