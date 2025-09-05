
    def setup_ui(self):

        print("setup_ui is processing")

        # フォントの設定
        custom_font = tkfont.Font(family="Helvetica", size=12)

        # メニュー全体のフォントサイズを設定
        self.root.option_add('*TearOffMenu*Font', custom_font)
        self.root.option_add('*Menu*Font', custom_font)

        # フォントスタイルの統一設定
        style = ttk.Style()
        style.configure("TLabel", font=('Helvetica', 10))
        style.configure("TButton", font=('Helvetica', 10))
        style.configure("Disabled.TButton", font=('Helvetica', 10))

        # メニューバーの作成
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="OPEN: select Directory", command=self.load_data_files)
        file_menu.add_separator()
        file_menu.add_command(label="SAVE: to Directory", command=self.save_to_directory)
        file_menu.add_command(label="LOAD: from Directory", command=self.load_from_directory)
        file_menu.add_separator()
        file_menu.add_command(label="EXIT", command=self.on_exit)
        menubar.add_cascade(label=" FILE  ", menu=file_menu)

        optimize_menu = tk.Menu(menubar, tearoff=0)
        optimize_menu.add_command(label="Save Objective Value", command=self.Save_Objective_Value)
        optimize_menu.add_separator()
        optimize_menu.add_command(label="Weight: Cost Stracture on Common Plan Unit", command=self.show_cost_stracture_bar_graph)
        optimize_menu.add_command(label="Capacity: Market Demand", command=self.show_month_data_csv)
        menubar.add_cascade(label="Optimize Parameter", menu=optimize_menu)

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

        revenue_profit_menu = tk.Menu(menubar, tearoff=0)
        revenue_profit_menu.add_command(label="Revenue and Profit", command=self.show_revenue_profit)
        menubar.add_cascade(label="Revenue and Profit", menu=revenue_profit_menu)

        cashflow_menu = tk.Menu(menubar, tearoff=0)
        cashflow_menu.add_command(label="PSI Price for CF", command=self.psi_price4cf)
        cashflow_menu.add_command(label="Cash Out&In&Net", command=self.cashflow_out_in_net)
        menubar.add_cascade(label="Cash Flow", menu=cashflow_menu)

        overview_menu = tk.Menu(menubar, tearoff=0)
        overview_menu.add_command(label="3D overview on Lots based Plan", command=self.show_3d_overview)
        menubar.add_cascade(label="3D overview", menu=overview_menu)

        self.root.config(menu=menubar)

        # plot_frame の定義
        self.plot_frame = ttk.Frame(self.root)
        self.plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # フレームの作成
        self.frame = ttk.Frame(self.root)
        self.frame.pack(side=tk.LEFT, fill=tk.Y)

        self.lot_size_label = ttk.Label(self.frame, text="Lot Size:")
        self.lot_size_label.pack(side=tk.TOP)
        self.lot_size_entry = tk.Entry(self.frame, width=10, font=('Helvetica', 10))
        self.lot_size_entry.pack(side=tk.TOP)
        self.lot_size_entry.insert(0, str(self.config.DEFAULT_LOT_SIZE))

        self.plan_year_label = ttk.Label(self.frame, text="Plan Year Start:")
        self.plan_year_label.pack(side=tk.TOP)
        self.plan_year_entry = tk.Entry(self.frame, width=10, font=('Helvetica', 10))
        self.plan_year_entry.pack(side=tk.TOP)
        self.plan_year_entry.insert(0, str(self.config.DEFAULT_START_YEAR))

        self.plan_range_label = ttk.Label(self.frame, text="Plan Range:")
        self.plan_range_label.pack(side=tk.TOP)
        self.plan_range_entry = tk.Entry(self.frame, width=10, font=('Helvetica', 10))
        self.plan_range_entry.pack(side=tk.TOP)
        self.plan_range_entry.insert(0, str(self.config.DEFAULT_PLAN_RANGE))

        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        self.Demand_Pl_button = ttk.Button(
            self.frame,
            text="Demand Planning",
            command=lambda: None,
            state="disabled",
            style="Disabled.TButton"
        )
        self.Demand_Pl_button.pack(side=tk.TOP)

        self.pre_proc_LT_label = ttk.Label(self.frame, text="pre_proc_LT:")
        self.pre_proc_LT_label.pack(side=tk.TOP)
        self.pre_proc_LT_entry = tk.Entry(self.frame, width=10, font=('Helvetica', 10))
        self.pre_proc_LT_entry.pack(side=tk.TOP)
        self.pre_proc_LT_entry.insert(0, str(self.config.DEFAULT_PRE_PROC_LT))

        self.Demand_Lv_button = ttk.Button(
            self.frame,
            text="Demand Leveling",
            command=lambda: None,
            state="disabled",
            style="Disabled.TButton"
        )
        self.Demand_Lv_button.pack(side=tk.TOP)

        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        self.supply_planning_button = ttk.Button(self.frame, text="Supply Planning ", command=self.supply_planning)
        self.supply_planning_button.pack(side=tk.TOP)

        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        self.eval_buffer_stock_button = ttk.Button(self.frame, text="Eval Buffer Stock ", command=self.eval_buffer_stock)
        self.eval_buffer_stock_button.pack(side=tk.TOP)

        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        self.optimize_button = ttk.Button(self.frame, text="OPT Supply Alloc", command=self.optimize_network)
        self.optimize_button.pack(side=tk.TOP)

        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        self.Inbound_DmBw_button = ttk.Button(self.frame, text="Inbound DmBw P", command=self.Inbound_DmBw)
        self.Inbound_DmBw_button.pack(side=tk.TOP)

        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        self.Inbound_SpFw_button = ttk.Button(self.frame, text="Inbound SpFw P", command=self.Inbound_SpFw)
        self.Inbound_SpFw_button.pack(side=tk.TOP)

        # Global Parameters input fields (gmp, ts, tsp)
        self.param_frame = ttk.Frame(self.plot_frame)
        self.param_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.gmp_label = ttk.Label(self.param_frame, text="Market Potential:", font=('Helvetica', 10))
        self.gmp_label.pack(side=tk.LEFT, padx=5)
        self.gmp_entry = tk.Entry(self.param_frame, width=10, font=('Helvetica', 10))
        self.gmp_entry.pack(side=tk.LEFT, padx=5)

        self.ts_label = ttk.Label(self.param_frame, text="TargetShare(%)", font=('Helvetica', 10))
        self.ts_label.pack(side=tk.LEFT, padx=5)
        self.ts_entry = tk.Entry(self.param_frame, width=5, font=('Helvetica', 10))
        self.ts_entry.pack(side=tk.LEFT, padx=5)

        self.ts_entry.insert(0, self.config.DEFAULT_TARGET_SHARE * 100)

        self.tsp_label = ttk.Label(self.param_frame, text="Total Supply:", font=('Helvetica', 10))
        self.tsp_label.pack(side=tk.LEFT, padx=5)
        self.tsp_entry = tk.Entry(self.param_frame, width=10, font=('Helvetica', 10))
        self.tsp_entry.pack(side=tk.LEFT, padx=5)
        self.tsp_entry.config(bg='lightgrey')

        self.gmp_entry.bind("<Return>", self.update_total_supply_plan)
        self.ts_entry.bind("<Return>", self.update_total_supply_plan)



# *******************************************

    def setup_ui(self):

        print("setup_ui is processing")

        #@250703 STOP
        ## フォントの設定
        #custom_font = tkfont.Font(family="Helvetica", size=12)

        ## メニュー全体のフォントサイズを設定
        #self.root.option_add('*TearOffMenu*Font', custom_font)
        #self.root.option_add('*Menu*Font', custom_font)




        # フォントの設定
        custom_font = tkfont.Font(family="Helvetica", size=12)

        # メニュー全体のフォントサイズを設定
        self.root.option_add('*TearOffMenu*Font', custom_font)
        self.root.option_add('*Menu*Font', custom_font)

        # フォントスタイルの統一設定
        style = ttk.Style()
        style.configure("TLabel", font=('Helvetica', 10))
        style.configure("TButton", font=('Helvetica', 10))
        style.configure("Disabled.TButton", font=('Helvetica', 10))





        # メニューバーの作成
        menubar = tk.Menu(self.root)

        # スタイルの設定
        style = ttk.Style()
        style.configure("TMenubutton", font=("Helvetica", 12))

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="OPEN: select Directory", command=self.load_data_files)
        file_menu.add_separator()
        file_menu.add_command(label="SAVE: to Directory", command=self.save_to_directory)

        file_menu.add_command(label="LOAD: from Directory", command=self.load_from_directory)

        file_menu.add_separator()
        file_menu.add_command(label="EXIT", command=self.on_exit)

        menubar.add_cascade(label=" FILE  ", menu=file_menu)


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

        report_menu.add_separator()

        report_menu.add_command(label="Value Chain: Cost Stracture a Lot", command=self.lot_cost_structure_to_csv)

        report_menu.add_command(label="Supply Chain: Revenue Profit", command=self.supplychain_performance_to_csv)



        #report_menu.add_separator()
        #
        #report_menu.add_command(label="PSI for Excel", command=self.psi_for_excel)

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


        #@250701 ADD
        # <<< ここに plot_frame の定義を追加 >>>
        self.plot_frame = ttk.Frame(self.root)
        self.plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)





        # カレンダー設定とフィルタ処理（週番号ではなく yymm に基づいて正確に制限）
        cal = Calendar445(
            start_year=self.plan_year_st,
            plan_range=self.plan_range,
            use_13_months=True,
            holiday_country="JP"
        )
        week_start = 1
        week_end = self.plan_range * 53
        max_year = self.plan_year_st + self.plan_range - 1
        week_to_yymm_all = cal.get_week_labels()
        week_to_yymm = {w: y for w, y in week_to_yymm_all.items() if int(str(y)[:2]) <= max_year % 100}
        month_end_weeks = [w for w in cal.get_month_end_weeks() if w in week_to_yymm]
        holiday_weeks = [w for w in cal.get_holiday_weeks() if w in week_to_yymm]







        # フレームの作成
        self.frame = ttk.Frame(self.root)
        self.frame.pack(side=tk.LEFT, fill=tk.Y)

        # Lot size entry
        self.lot_size_label = ttk.Label(self.frame, text="Lot Size:")
        self.lot_size_label.pack(side=tk.TOP)
        self.lot_size_entry = ttk.Entry(self.frame, width=10)
        self.lot_size_entry.pack(side=tk.TOP)

        #@250117 UPDATE
        self.lot_size_entry.insert(0, str(self.config.DEFAULT_LOT_SIZE))  # 初期値を設定
        #self.lot_size_entry.insert(0, str(self.lot_size))  # 初期値を設定

        # Plan Year Start entry
        self.plan_year_label = ttk.Label(self.frame, text="Plan Year Start:")
        self.plan_year_label.pack(side=tk.TOP)
        self.plan_year_entry = ttk.Entry(self.frame, width=10)
        self.plan_year_entry.pack(side=tk.TOP)


        self.plan_year_entry.insert(0, str(self.config.DEFAULT_START_YEAR))  # 初期値を設定
        #self.plan_year_entry.insert(0, str(self.plan_year_st))  # 初期値を設定

        # Plan Range entry
        self.plan_range_label = ttk.Label(self.frame, text="Plan Range:")
        self.plan_range_label.pack(side=tk.TOP)
        self.plan_range_entry = ttk.Entry(self.frame, width=10)
        self.plan_range_entry.pack(side=tk.TOP)


        self.plan_range_entry.insert(0, str(self.config.DEFAULT_PLAN_RANGE))  # 初期値を設定
        #self.plan_range_entry.insert(0, str(self.plan_range))  # 初期値を設定

        # 1行分の空白を追加
        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)



        #@250120 RUN
        # Demand Planning ボタン（グレイアウト）
        self.Demand_Pl_button = ttk.Button(
            self.frame,
            text="Demand Planning",
            command=lambda: None,  # 無効化
            state="disabled",  # ボタンを無効化
            style="Disabled.TButton"  # スタイルを適用
        )
        self.Demand_Pl_button.pack(side=tk.TOP)


        #@250120 STOP
        ## Demand Planning buttons
        #self.Demand_Pl_button = ttk.Button(self.frame, text="Demand Planning", command=self.demand_planning)
        #self.Demand_Pl_button.pack(side=tk.TOP)




        # Plan Year Start entry
        self.pre_proc_LT_label = ttk.Label(self.frame, text="pre_proc_LT:")
        self.pre_proc_LT_label.pack(side=tk.TOP)
        self.pre_proc_LT_entry = ttk.Entry(self.frame, width=10)
        self.pre_proc_LT_entry.pack(side=tk.TOP)


        self.pre_proc_LT_entry.insert(0, str(self.config.DEFAULT_PRE_PROC_LT))  # 初期値を設定
        #self.pre_proc_LT_entry.insert(0, str(self.pre_proc_LT))  # 初期値を設定


        #@250120 RUN
        # Demand Leveling ボタン（グレイアウト）
        self.Demand_Lv_button = ttk.Button(
            self.frame,
            text="Demand Leveling",
            command=lambda: None,  # 無効化
            state="disabled",  # ボタンを無効化
            style="Disabled.TButton"  # スタイルを適用
        )
        self.Demand_Lv_button.pack(side=tk.TOP)


        #@250120 STOP
        ## Demand Leveling button
        #self.Demand_Lv_button = ttk.Button(self.frame, text="Demand Leveling", command=self.demand_leveling)
        #self.Demand_Lv_button.pack(side=tk.TOP)





        # add a blank line
        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        # Supply Planning button
        self.supply_planning_button = ttk.Button(self.frame, text="Supply Planning ", command=self.supply_planning)
        self.supply_planning_button.pack(side=tk.TOP)

        # add a blank line
        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        # Eval_buffer_stock buttons
        self.eval_buffer_stock_button = ttk.Button(self.frame, text="Eval Buffer Stock ", command=self.eval_buffer_stock)
        self.eval_buffer_stock_button.pack(side=tk.TOP)

        # add a blank line
        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        # Optimize Network button
        self.optimize_button = ttk.Button(self.frame, text="OPT Supply Alloc", command=self.optimize_network)
        self.optimize_button.pack(side=tk.TOP)



        # add a blank line
        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        # Optimize Network button
        self.Inbound_DmBw_button = ttk.Button(self.frame, text="Inbound DmBw P", command=self.Inbound_DmBw)
        self.Inbound_DmBw_button.pack(side=tk.TOP)



        # add a blank line
        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        # Optimize Network button
        self.Inbound_SpFw_button = ttk.Button(self.frame, text="Inbound SpFw P", command=self.Inbound_SpFw)
        self.Inbound_SpFw_button.pack(side=tk.TOP)








        # Network Graph frame
        self.network_frame = ttk.Frame(self.plot_frame)
        self.network_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # expand 追加、fill=BOTH

        #@250701 STOP
        ## Plot area divided into two frames
        #self.plot_frame = ttk.Frame(self.root)
        #self.plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        #@250701 STOP
        # Network Graph frame
        #self.network_frame = ttk.Frame(self.plot_frame)
        #self.network_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ## Network Graph frame
        #self.network_frame = ttk.Frame(self.plot_frame, width=500)  # 横幅指定を追加
        #self.network_frame.pack(side=tk.LEFT, fill=tk.Y)  # fill=tk.Y に変更して固定幅化


        # New Frame for Parameters at the top of the network_frame
        self.param_frame = ttk.Frame(self.network_frame)
        self.param_frame.pack(side=tk.TOP, fill=tk.X)


        # Global Market Potential, Target Share, Total Supply Plan input fields arranged horizontally
        self.gmp_label = tk.Label(self.param_frame, text="Market Potential:", background='navy', foreground='white', font=('Helvetica', 10, 'bold'))
        self.gmp_label.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=10)
        self.gmp_entry = tk.Entry(self.param_frame, width=10)
        self.gmp_entry.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=10)

        self.ts_label = tk.Label(self.param_frame, text="TargetShare(%)", background='navy', foreground='white', font=('Helvetica', 10, 'bold'))
        self.ts_label.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=10)
        self.ts_entry = tk.Entry(self.param_frame, width=5)
        self.ts_entry.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=10)



        self.ts_entry.insert(0, self.config.DEFAULT_TARGET_SHARE * 100) # 初期値
        #self.ts_entry.insert(0, self.target_share * 100) # 初期値

        self.tsp_label = tk.Label(self.param_frame, text="Total Supply:", background='navy', foreground='white', font=('Helvetica', 10, 'bold'))
        self.tsp_label.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=10)
        self.tsp_entry = tk.Entry(self.param_frame, width=10)
        self.tsp_entry.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=10)
        self.tsp_entry.config(bg='lightgrey')  # 背景色をlightgreyに設定




        # イベントバインディング
        self.gmp_entry.bind("<Return>", self.update_total_supply_plan)
        self.ts_entry.bind("<Return>", self.update_total_supply_plan)

        self.fig_network, self.ax_network = plt.subplots(figsize=(4, 8))  # 横幅を縮小
        self.canvas_network = FigureCanvasTkAgg(self.fig_network, master=self.network_frame)

        ##@250228 ADD STOP
        #self.canvas_network.get_tk_widget().config(width=500, height=300)  # 画面サイズを制限
        #self.canvas_network.get_tk_widget().pack(fill=tk.BOTH, expand=False)  # ウィンドウのリサイズを防ぐ

        #@250228 STOP RUN
        self.canvas_network.get_tk_widget().pack(fill=tk.BOTH, expand=True)




        self.fig_network.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

        # Evaluation result area
        self.eval_frame = ttk.Frame(self.plot_frame)
        self.eval_frame.pack(side=tk.TOP, fill=tk.X, padx=(20, 0))  # 横方向に配置

        # Total Revenue
        self.total_revenue_label = ttk.Label(self.eval_frame, text="Total Revenue:", background='darkgreen', foreground='white', font=('Helvetica', 10, 'bold'))
        self.total_revenue_label.pack(side=tk.LEFT, padx=5, pady=10)
        self.total_revenue_entry = ttk.Entry(self.eval_frame, width=10, state='readonly')
        self.total_revenue_entry.pack(side=tk.LEFT, padx=5, pady=10)

        # Total Profit
        self.total_profit_label = ttk.Label(self.eval_frame, text="Total Profit:", background='darkgreen', foreground='white', font=('Helvetica', 10, 'bold'))
        self.total_profit_label.pack(side=tk.LEFT, padx=5, pady=10)
        self.total_profit_entry = ttk.Entry(self.eval_frame, width=10, state='readonly')
        self.total_profit_entry.pack(side=tk.LEFT, padx=5, pady=10)




        # Profit Ratio
        self.profit_ratio_label = ttk.Label(self.eval_frame, text="Profit Ratio:", background='darkgreen', foreground='white', font=('Helvetica', 10, 'bold'))
        self.profit_ratio_label.pack(side=tk.LEFT, padx=5, pady=10)
        self.profit_ratio_entry = ttk.Entry(self.eval_frame, width=10, state='readonly')
        self.profit_ratio_entry.pack(side=tk.LEFT, padx=5, pady=10)


        # PSI Graph scroll frame
        self.psi_frame = ttk.Frame(self.plot_frame)
        self.psi_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # これもそのままでOK

        #@250701 STOP
        ## PSI Graph scroll frame
        #self.psi_frame = ttk.Frame(self.plot_frame)
        #self.psi_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # side=tk.LEFT に変更

        #@250701 STOP
        # PSI Graph scroll frame (moved to below evaluation area)
        #self.psi_frame = ttk.Frame(self.plot_frame)
        #self.psi_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)



        self.canvas_psi = tk.Canvas(self.psi_frame)
        self.scrollbar = ttk.Scrollbar(self.psi_frame, orient="vertical", command=self.canvas_psi.yview)
        self.scrollable_frame = ttk.Frame(self.canvas_psi)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas_psi.configure(
                scrollregion=self.canvas_psi.bbox("all")
            )
        )

        self.canvas_psi.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas_psi.configure(yscrollcommand=self.scrollbar.set)

        self.canvas_psi.pack(side="left", fill="both", expand=True)

        #@250702 UPDATE
        #self.scrollbar.pack(side="right", fill="y")
        self.scrollbar.pack(side="right", fill="y", expand=True)

        #@250120 STOP
        ## 初期化関数を呼び出してパラメータ設定
        #self.initialize_parameters()



