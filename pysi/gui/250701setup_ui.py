#250701setup_ui.py
# GEMINI answer


import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Global Weekly PSI Planner")

        # ダミーのconfigオブジェクト（実際のアプリケーションでは適切に初期化されているはずです）
        class Config:
            DEFAULT_LOT_SIZE = 100
            DEFAULT_START_YEAR = 2024
            DEFAULT_PLAN_RANGE = 12
            DEFAULT_PRE_PROC_LT = 5
            DEFAULT_TARGET_SHARE = 0.5
        self.config = Config()

        # ダミーのメソッド（実際のアプリケーションでは実装されているはずです）
        self.load_data_files = lambda: print("load_data_files called")
        self.save_to_directory = lambda: print("save_to_directory called")
        self.load_from_directory = lambda: print("load_from_directory called")
        self.on_exit = lambda: self.root.quit()
        self.Save_Objective_Value = lambda: print("Save_Objective_Value called")
        self.show_cost_stracture_bar_graph = lambda: print("show_cost_stracture_bar_graph called")
        self.show_month_data_csv = lambda: print("show_month_data_csv called")
        self.outbound_psi_to_csv = lambda: print("outbound_psi_to_csv called")
        self.outbound_lot_by_lot_to_csv = lambda: print("outbound_lot_by_lot_to_csv called")
        self.inbound_psi_to_csv = lambda: print("inbound_psi_to_csv called")
        self.inbound_lot_by_lot_to_csv = lambda: print("inbound_lot_by_lot_to_csv called")
        self.lot_cost_structure_to_csv = lambda: print("lot_cost_structure_to_csv called")
        self.supplychain_performance_to_csv = lambda: print("supplychain_performance_to_csv called")
        self.show_revenue_profit = lambda: print("show_revenue_profit called")
        self.psi_price4cf = lambda: print("psi_price4cf called")
        self.cashflow_out_in_net = lambda: print("cashflow_out_in_net called")
        self.show_3d_overview = lambda: print("show_3d_overview called")
        self.supply_planning = lambda: print("supply_planning called")
        self.eval_buffer_stock = lambda: print("eval_buffer_stock called")
        self.optimize_network = lambda: print("optimize_network called")
        self.Inbound_DmBw = lambda: print("Inbound_DmBw called")
        self.Inbound_SpFw = lambda: print("Inbound_SpFw called")
        self.update_total_supply_plan = lambda event=None: self._update_total_supply_plan_dummy()

        # ダミーの初期値
        self.total_supply_plan = 0
        self.total_revenue = 0
        self.total_profit = 0
        self.profit_ratio = 0

        self.setup_ui()
        self.draw_initial_network_graph()
        self.draw_initial_psi_graph()
        self.update_evaluation_results() # 初期表示のための更新

    def _update_total_supply_plan_dummy(self):
        try:
            market_potential = float(self.gmp_entry.get())
            target_share = float(self.ts_entry.get()) / 100
            self.total_supply_plan = market_potential * target_share
            self.tsp_entry.config(state='normal')
            self.tsp_entry.delete(0, tk.END)
            self.tsp_entry.insert(0, f"{self.total_supply_plan:,.0f}")
            self.tsp_entry.config(state='readonly')
        except ValueError:
            self.tsp_entry.config(state='normal')
            self.tsp_entry.delete(0, tk.END)
            self.tsp_entry.insert(0, "Invalid Input")
            self.tsp_entry.config(state='readonly')

    def update_evaluation_results(self):
        # ダミーの計算
        self.total_revenue = 123456789
        self.total_profit = 12345678
        self.profit_ratio = (self.total_profit / self.total_revenue) * 100 if self.total_revenue else 0

        self.total_revenue_entry.config(state='normal')
        self.total_revenue_entry.delete(0, tk.END)
        self.total_revenue_entry.insert(0, f"{self.total_revenue:,.0f}")
        self.total_revenue_entry.config(state='readonly')

        self.total_profit_entry.config(state='normal')
        self.total_profit_entry.delete(0, tk.END)
        self.total_profit_entry.insert(0, f"{self.total_profit:,.0f}")
        self.total_profit_entry.config(state='readonly')

        self.profit_ratio_entry.config(state='normal')
        self.profit_ratio_entry.delete(0, tk.END)
        self.profit_ratio_entry.insert(0, f"{self.profit_ratio:.2f}%")
        self.profit_ratio_entry.config(state='readonly')

    def draw_initial_network_graph(self):
        self.ax_network.clear()
        self.ax_network.text(0.5, 0.5, "Network Graph Area", horizontalalignment='center', verticalalignment='center', transform=self.ax_network.transAxes, fontsize=16, color='gray')
        self.ax_network.set_xticks([])
        self.ax_network.set_yticks([])
        self.ax_network.set_facecolor('lightgray')
        self.fig_network.tight_layout()
        self.canvas_network.draw()

    def draw_initial_psi_graph(self):
        # PSIグラフの初期描画（ダミー）
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        for i in range(5): # 5つのダミーグラフを作成
            fig, ax = plt.subplots(figsize=(6, 2)) # 幅を少し広げ、高さを抑える
            ax.plot([1, 2, 3, 4, 5], [1, 4, 2, 5, 3], label=f'PSI Data {i+1}')
            ax.set_title(f'PSI Graph {i+1}')
            ax.legend()
            ax.set_facecolor('white') # PSIグラフの背景色も白に設定

            canvas = FigureCanvasTkAgg(fig, master=self.scrollable_frame)
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            canvas.draw()

    def setup_ui(self):
        print("setup_ui is processing")

        # ウィンドウを最大化（Windows限定）
        self.root.state("zoomed")

        # フォントの設定
        custom_font = tkfont.Font(family="Helvetica", size=12)

        # メニュー全体のフォントサイズを設定
        self.root.option_add('*TearOffMenu*Font', custom_font)
        self.root.option_add('*Menu*Font', custom_font)

        # メニューバーの作成
        menubar = tk.Menu(self.root)

        # スタイルの設定
        style = ttk.Style()
        style.configure("TMenubutton", font=("Helvetica", 12))
        style.configure("Disabled.TButton", foreground="gray", background="lightgray") # 無効化ボタンのスタイル

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="OPEN: select Directory", command=self.load_data_files)
        file_menu.add_separator()
        file_menu.add_command(label="SAVE: to Directory", command=self.save_to_directory)
        file_menu.add_command(label="LOAD: from Directory", command=self.load_from_directory)
        file_menu.add_separator()
        file_menu.add_command(label="EXIT", command=self.on_exit)
        menubar.add_cascade(label=" FILE ", menu=file_menu)

        # Optimize Parameter menu
        optimize_menu = tk.Menu(menubar, tearoff=0)
        optimize_menu.add_command(label="Save Objective Value", command=self.Save_Objective_Value)
        optimize_menu.add_separator()
        optimize_menu.add_command(label="Weight: Cost Stracture on Common Plan Unit", command=self.show_cost_stracture_bar_graph)
        optimize_menu.add_command(label="Capacity: Market Demand", command=self.show_month_data_csv)
        menubar.add_cascade(label="Optimize Parameter", menu=optimize_menu)

        # Report menu
        report_menu = tk.Menu(menubar, tearoff=0)
        report_menu.add_command(label="Outbound: PSI to csv file", command=self.outbound_psi_to_csv)
        report_menu.add_command(label="Outbound: Lot by Lot data to csv", command=self.outbound_lot_by_lot_to_csv)
        report_menu.add_separator()
        report_menu.add_command(label="Inbound: PSI to csv file", command=self.inbound_psi_to_csv)
        report_menu.add_command(label="Inbound: Lot by Lot data to csv", command=self.inbound_lot_by_lot_to_csv)
        report_menu.add_separator()
        report_menu.add_command(label="Value Chain: Cost Stracture a Lot", command=self.lot_cost_structure_to_csv)
        report_menu.add_command(label="Supply Chain: Revenue Profit", command=self.supplychain_performance_to_csv)
        menubar.add_cascade(label="Report", menu=report_menu)

        # Revenue and Profit menu
        revenue_profit_menu = tk.Menu(menubar, tearoff=0)
        revenue_profit_menu.add_command(label="Revenue and Profit", command=self.show_revenue_profit)
        menubar.add_cascade(label="Revenue and Profit", menu=revenue_profit_menu)

        # Cash Flow analysis menu
        cashflow_menu = tk.Menu(menubar, tearoff=0)
        cashflow_menu.add_command(label="PSI Price for CF", command=self.psi_price4cf)
        cashflow_menu.add_command(label="Cash Out&In&Net", command=self.cashflow_out_in_net)
        menubar.add_cascade(label="Cash Flow", menu=cashflow_menu)

        # 3D overview menu
        overview_menu = tk.Menu(menubar, tearoff=0)
        overview_menu.add_command(label="3D overview on Lots based Plan", command=self.show_3d_overview)
        menubar.add_cascade(label="3D overview", menu=overview_menu)

        self.root.config(menu=menubar)

        # メインフレームの作成 (左側のコントロールパネル)
        self.frame = ttk.Frame(self.root, width=200) # 固定幅を設定
        self.frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10) # 左右にパディングを追加

        # plot_frameの定義: ネットワークグラフとPSIグラフを含む
        self.plot_frame = ttk.Frame(self.root)
        self.plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True) # 残りのスペースを全て使用

        # Lot size entry
        self.lot_size_label = ttk.Label(self.frame, text="Lot Size:")
        self.lot_size_label.pack(side=tk.TOP, pady=(10, 0))
        self.lot_size_entry = ttk.Entry(self.frame, width=10)
        self.lot_size_entry.pack(side=tk.TOP)
        self.lot_size_entry.insert(0, str(self.config.DEFAULT_LOT_SIZE))

        # Plan Year Start entry
        self.plan_year_label = ttk.Label(self.frame, text="Plan Year Start:")
        self.plan_year_label.pack(side=tk.TOP, pady=(10, 0))
        self.plan_year_entry = ttk.Entry(self.frame, width=10)
        self.plan_year_entry.pack(side=tk.TOP)
        self.plan_year_entry.insert(0, str(self.config.DEFAULT_START_YEAR))

        # Plan Range entry
        self.plan_range_label = ttk.Label(self.frame, text="Plan Range:")
        self.plan_range_label.pack(side=tk.TOP, pady=(10, 0))
        self.plan_range_entry = ttk.Entry(self.frame, width=10)
        self.plan_range_entry.pack(side=tk.TOP)
        self.plan_range_entry.insert(0, str(self.config.DEFAULT_PLAN_RANGE))

        # 1行分の空白を追加
        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP, pady=5)

        # Demand Planning ボタン（グレイアウト）
        self.Demand_Pl_button = ttk.Button(
            self.frame,
            text="Demand Planning",
            command=lambda: None,
            state="disabled",
            style="Disabled.TButton"
        )
        self.Demand_Pl_button.pack(side=tk.TOP)

        # Plan Year Start entry
        self.pre_proc_LT_label = ttk.Label(self.frame, text="pre_proc_LT:")
        self.pre_proc_LT_label.pack(side=tk.TOP, pady=(10, 0))
        self.pre_proc_LT_entry = ttk.Entry(self.frame, width=10)
        self.pre_proc_LT_entry.pack(side=tk.TOP)
        self.pre_proc_LT_entry.insert(0, str(self.config.DEFAULT_PRE_PROC_LT))

        # Demand Leveling ボタン（グレイアウト）
        self.Demand_Lv_button = ttk.Button(
            self.frame,
            text="Demand Leveling",
            command=lambda: None,
            state="disabled",
            style="Disabled.TButton"
        )
        self.Demand_Lv_button.pack(side=tk.TOP)

        # add a blank line
        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP, pady=5)

        # Supply Planning button
        self.supply_planning_button = ttk.Button(self.frame, text="Supply Planning ", command=self.supply_planning)
        self.supply_planning_button.pack(side=tk.TOP)

        # add a blank line
        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP, pady=5)

        # Eval_buffer_stock buttons
        self.eval_buffer_stock_button = ttk.Button(self.frame, text="Eval Buffer Stock ", command=self.eval_buffer_stock)
        self.eval_buffer_stock_button.pack(side=tk.TOP)

        # add a blank line
        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP, pady=5)

        # Optimize Network button
        self.optimize_button = ttk.Button(self.frame, text="OPT Supply Alloc", command=self.optimize_network)
        self.optimize_button.pack(side=tk.TOP)

        # add a blank line
        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP, pady=5)

        # Optimize Network button
        self.Inbound_DmBw_button = ttk.Button(self.frame, text="Inbound DmBw P", command=self.Inbound_DmBw)
        self.Inbound_DmBw_button.pack(side=tk.TOP)

        # add a blank line
        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP, pady=5)

        # Optimize Network button
        self.Inbound_SpFw_button = ttk.Button(self.frame, text="Inbound SpFw P", command=self.Inbound_SpFw)
        self.Inbound_SpFw_button.pack(side=tk.TOP)

        # Network Graph frame (plot_frameの左側)
        # ネットワークグラフの幅を固定せず、plot_frame内で利用可能なスペースを適切に配分するように変更
        self.network_frame = ttk.Frame(self.plot_frame)
        self.network_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5) # expand=Trueを追加

        # New Frame for Parameters at the top of the network_frame
        self.param_frame = ttk.Frame(self.network_frame, style="Param.TFrame")
        self.param_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 5)) # 下に少しパディング

        style.configure("Param.TFrame", background='navy')

        # Global Market Potential, Target Share, Total Supply Plan input fields arranged horizontally
        self.gmp_label = tk.Label(self.param_frame, text="Market Potential:", background='navy', foreground='white', font=('Helvetica', 10, 'bold'))
        self.gmp_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.gmp_entry = tk.Entry(self.param_frame, width=10)
        self.gmp_entry.pack(side=tk.LEFT, padx=5, pady=5)

        self.ts_label = tk.Label(self.param_frame, text="TargetShare(%)", background='navy', foreground='white', font=('Helvetica', 10, 'bold'))
        self.ts_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.ts_entry = tk.Entry(self.param_frame, width=5)
        self.ts_entry.pack(side=tk.LEFT, padx=5, pady=5)
        self.ts_entry.insert(0, self.config.DEFAULT_TARGET_SHARE * 100)

        self.tsp_label = tk.Label(self.param_frame, text="Total Supply:", background='navy', foreground='white', font=('Helvetica', 10, 'bold'))
        self.tsp_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.tsp_entry = tk.Entry(self.param_frame, width=10)
        self.tsp_entry.pack(side=tk.LEFT, padx=5, pady=5)
        self.tsp_entry.config(bg='lightgrey')

        # イベントバインディング
        self.gmp_entry.bind("<Return>", self.update_total_supply_plan)
        self.ts_entry.bind("<Return>", self.update_total_supply_plan)

        # ネットワークグラフのFigureとCanvas
        self.fig_network, self.ax_network = plt.subplots(figsize=(6, 8)) # 横幅を調整
        self.canvas_network = FigureCanvasTkAgg(self.fig_network, master=self.network_frame)
        self.canvas_network_widget = self.canvas_network.get_tk_widget()
        self.canvas_network_widget.pack(fill=tk.BOTH, expand=True) # expand=Trueで利用可能なスペースを埋める

        self.fig_network.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

        # Evaluation result area (plot_frameの右側、PSIグラフの上)
        self.eval_frame = ttk.Frame(self.plot_frame, style="Eval.TFrame")
        self.eval_frame.pack(side=tk.TOP, fill=tk.X, padx=(0, 10), pady=(5, 0)) # 横方向に配置、右にパディング
        style.configure("Eval.TFrame", background='darkgreen')

        # Total Revenue
        self.total_revenue_label = ttk.Label(self.eval_frame, text="Total Revenue:", background='darkgreen', foreground='white', font=('Helvetica', 10, 'bold'))
        self.total_revenue_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.total_revenue_entry = ttk.Entry(self.eval_frame, width=10, state='readonly')
        self.total_revenue_entry.pack(side=tk.LEFT, padx=5, pady=5)

        # Total Profit
        self.total_profit_label = ttk.Label(self.eval_frame, text="Total Profit:", background='darkgreen', foreground='white', font=('Helvetica', 10, 'bold'))
        self.total_profit_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.total_profit_entry = ttk.Entry(self.eval_frame, width=10, state='readonly')
        self.total_profit_entry.pack(side=tk.LEFT, padx=5, pady=5)

        # Profit Ratio
        self.profit_ratio_label = ttk.Label(self.eval_frame, text="Profit Ratio:", background='darkgreen', foreground='white', font=('Helvetica', 10, 'bold'))
        self.profit_ratio_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.profit_ratio_entry = ttk.Entry(self.eval_frame, width=10, state='readonly')
        self.profit_ratio_entry.pack(side=tk.LEFT, padx=5, pady=5)

        # PSI Graph scroll frame（plot_frameの右側、評価結果の下）
        self.psi_frame = ttk.Frame(self.plot_frame)
        self.psi_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=(0, 10), pady=(0, 10)) # 残りのスペースを全て使用

        self.canvas_psi = tk.Canvas(self.psi_frame, bg="white") # キャンバスの背景色を設定
        self.scrollbar = ttk.Scrollbar(self.psi_frame, orient="vertical", command=self.canvas_psi.yview)
        self.scrollable_frame = ttk.Frame(self.canvas_psi)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas_psi.configure(scrollregion=self.canvas_psi.bbox("all"))
        )

        self.canvas_psi.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas_psi.configure(yscrollcommand=self.scrollbar.set)

        self.canvas_psi.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()

