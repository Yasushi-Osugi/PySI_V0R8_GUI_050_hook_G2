#load_data_files.py



    def load_data_files(self):
        directory = filedialog.askdirectory(title="Select Data Directory")

        if directory:
            try:
                self.lot_size = int(self.lot_size_entry.get())
                self.plan_year_st = int(self.plan_year_entry.get())
                self.plan_range = int(self.plan_range_entry.get())
            except ValueError:
                print("Invalid input for lot size, plan year start, or plan range. Using default values.")

            self.outbound_data = []
            self.inbound_data = []

            data_file_list = os.listdir(directory)

            print("data_file_list", data_file_list)

            self.directory = directory
            self.load_directory = directory

            # --- Load Tree Structures ---
            if "profile_tree_outbound.csv" in data_file_list:
                file_path = os.path.join(directory, "profile_tree_outbound.csv")
                nodes_outbound, root_node_name_out = create_tree_set_attribute(file_path)
                root_node_outbound = nodes_outbound[root_node_name_out]

                def make_leaf_nodes(node, leaf_list):
                    if not node.children:
                        leaf_list.append(node.name)
                    for child in node.children:
                        make_leaf_nodes(child, leaf_list)
                    return leaf_list

                leaf_nodes_out = make_leaf_nodes(root_node_outbound, [])
                self.nodes_outbound = nodes_outbound
                self.root_node_outbound = root_node_outbound
                self.leaf_nodes_out = leaf_nodes_out
                set_positions(root_node_outbound)
                set_parent_all(root_node_outbound)
                print_parent_all(root_node_outbound)
            else:
                print("error: profile_tree_outbound.csv is missed")

            if "profile_tree_inbound.csv" in data_file_list:
                file_path = os.path.join(directory, "profile_tree_inbound.csv")
                nodes_inbound, root_node_name_in = create_tree_set_attribute(file_path)
                root_node_inbound = nodes_inbound[root_node_name_in]
                self.nodes_inbound = nodes_inbound
                self.root_node_inbound = root_node_inbound
                set_positions(root_node_inbound)
                set_parent_all(root_node_inbound)
                print_parent_all(root_node_inbound)
            else:
                print("error: profile_tree_inbound.csv is missed")

            if "node_cost_table_outbound.csv" in data_file_list:
                read_set_cost(os.path.join(directory, "node_cost_table_outbound.csv"), self.nodes_outbound)
            else:
                print("error: node_cost_table_outbound.csv is missed")

            if "node_cost_table_inbound.csv" in data_file_list:
                read_set_cost(os.path.join(directory, "node_cost_table_inbound.csv"), self.nodes_inbound)
            else:
                print("error: node_cost_table_inbound.csv is missed")

            if "S_month_data.csv" in data_file_list:
                in_file_path = os.path.join(directory, "S_month_data.csv")
                df_weekly, plan_range, plan_year_st = process_monthly_demand(in_file_path, self.lot_size)
                self.plan_year_st = plan_year_st
                self.plan_range = plan_range
                self.plan_year_entry.delete(0, tk.END)
                self.plan_year_entry.insert(0, str(self.plan_year_st))
                self.plan_range_entry.delete(0, tk.END)
                self.plan_range_entry.insert(0, str(self.plan_range))
                df_weekly.to_csv(os.path.join(directory, "S_iso_week_data.csv"), index=False)
            else:
                print("error: S_month_data.csv is missed")

            root_node_outbound.set_plan_range_lot_counts(plan_range, plan_year_st)
            root_node_inbound.set_plan_range_lot_counts(plan_range, plan_year_st)

            node_psi_dict_Ot4Dm = make_psi_space_dict(root_node_outbound, {}, plan_range)
            node_psi_dict_Ot4Sp = make_psi_space_dict(root_node_outbound, {}, plan_range)
            self.node_psi_dict_In4Dm = make_psi_space_dict(root_node_inbound, {}, plan_range)
            self.node_psi_dict_In4Sp = make_psi_space_dict(root_node_inbound, {}, plan_range)
            set_dict2tree_psi(root_node_outbound, "psi4demand", node_psi_dict_Ot4Dm)
            set_dict2tree_psi(root_node_outbound, "psi4supply", node_psi_dict_Ot4Sp)
            set_dict2tree_psi(root_node_inbound, "psi4demand", self.node_psi_dict_In4Dm)
            set_dict2tree_psi(root_node_inbound, "psi4supply", self.node_psi_dict_In4Sp)

            set_df_Slots2psi4demand(root_node_outbound, df_weekly)

            # --- Allocation Logic from P_month_data.csv ---



            # ****************************************************
            # Allocation with using Production Template
            # ****************************************************

            # 1. Monthly template reader
            def read_p_month_data_csv(filepath, target_node, target_product, target_year):

                print("ead_p_month_data_csv(filepath, target_node, target_product, target_year):", filepath, target_node, target_product, target_year)

                month_abbr = list(calendar.month_abbr)[1:]
                month2cap = {}
                with open(filepath, newline='', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if (row['node_name'] == target_node and
                            row['product_name'] == target_product and
                            int(row['year']) == target_year):
                            for i, m in enumerate(month_abbr, start=1):
                                cap = float(row[f"m{i}"])

                                if cap >= 0:
                                #if cap > 0:

                                    month2cap[m] = cap

                                    print("month2cap", month2cap)


                            break



                if not month2cap:
                    raise ValueError(f"No data for {target_node}/{target_product}/{target_year}")

                print("month2cap", month2cap)

                return month2cap


            # 2. Generate ISO-week mapping using calendar matching PSI Planner
            def generate_iso_calendar(plan_year, plan_weeks=3*52+5):
                iso_map = {}
                # start at ISO week 1 of plan_year
                d = date(plan_year,1,4)  # ISO week 1 guaranteed within Jan 4
                iso_year, iso_week, _ = d.isocalendar()
                d = d - timedelta(days=d.isocalendar()[2]-1)
                week_no = 1
                while week_no <= plan_weeks:
                    iso_year, iso_week, _ = d.isocalendar()
                    iso_map.setdefault((iso_year, iso_week), []).append(d)
                    d += timedelta(days=7)
                    week_no += 1
                # build month→list of (iso_year, iso_week)
                month_week_map = defaultdict(set)
                for (iy, iw), days in iso_map.items():
                    for day in days:
                        month = calendar.month_abbr[day.month]
                        if iy == plan_year:
                            month_week_map[month].add((iy, iw))
                # compute start and counts
                start = {m: min(iw for iy, iw in weeks) for m, weeks in month_week_map.items()}
                count = {m: len(weeks) for m, weeks in month_week_map.items()}
                return start, count

            # 3. Month to weekly buckets
            def month_to_week_buckets(month2cap, start, count):
                arr = []
                for m, cap in month2cap.items():
                    wcnt = count.get(m,0)
                    if wcnt==0: continue
                    per = cap / wcnt
                    base = start[m]
                    for i in range(wcnt):
                        w = base + i
                        arr.append({'week': w, 'prod': per})
                return arr

            # 4. floor-lot
            def week_data_to_capacities(pweek, lot_size):
                hw=[]
                for r in pweek:
                    c = floor(r['prod']/lot_size)
                    if c>0:
                        hw.append({'week':r['week'],'capacity':c})
                return hw



            # **************************************************


            # 5. Allocation logic with rollover
            def allocate_lots_to_harvest(demand_lots_dict, harvest_weeks, lead_time_weeks=5):
                allocation = defaultdict(list)
                week_capacity = {hw['week']: hw['capacity'] for hw in harvest_weeks}
                sorted_hw = sorted(harvest_weeks, key=lambda x: x['week'])
                hw_idx = 0
                warnings = []

                all_lots = []
                for w in sorted(demand_lots_dict):
                    all_lots.extend(demand_lots_dict[w])

                for lot_id in all_lots:
                    attempts = 0
                    while True:
                        current_hw = sorted_hw[hw_idx % len(sorted_hw)]
                        w = current_hw['week']
                        if len(allocation[w]) < week_capacity[w]:
                            allocation[w].append(lot_id)
                            break
                        else:
                            hw_idx += 1
                            attempts += 1
                            if attempts > len(sorted_hw):
                                warnings.append(f"Cannot allocate lot {lot_id}: all weeks full")
                                break
                    hw_idx += 1

                return dict(allocation), warnings



            def allocation_result_to_psi4supply(allocation_result):
                max_week = max(allocation_result.keys(), default=0)
                # 0週目（ダミー）+ max_week 週分を list で初期化
                psi4supply = [[[], [], [], []] for _ in range(max_week + 1)]

                for w, lots in allocation_result.items():
                    psi4supply[w][3] = lots  # wはlist indexとして機能する（1〜max_week）

                return psi4supply

            # ****************************************************


            if "P_month_data.csv" in data_file_list:
                p_template_path = os.path.join(directory, "P_month_data.csv")
                df_p_month = pd.read_csv(p_template_path, encoding='utf-8-sig')
                unique_nodes = df_p_month["node_name"].unique()

                for node_name in unique_nodes:
                    try:
                        month2cap = read_p_month_data_csv(p_template_path, node_name, "prod-A", self.plan_year_st)
                        start, count = generate_iso_calendar(self.plan_year_st, plan_weeks=self.plan_range)
                        pweek = month_to_week_buckets(month2cap, start, count)
                        harvest_weeks = week_data_to_capacities(pweek, lot_size=self.lot_size)

                        dad_node = self.nodes_outbound.get(node_name)
                        #dad_node = self.nodes_inbound.get(node_name)

                        if dad_node is None:
                            print(f"Warning: Node '{node_name}' not found in inbound tree.")
                            continue

                        psi4demand = dad_node.psi4demand
                        demand_map = {w: psi4demand[w][0] for w in range(1, self.plan_range + 1)}

                        allocation_result, warnings = allocate_lots_to_harvest(demand_map, harvest_weeks)
                        if warnings:
                            print("\n".join(warnings))

                        psi4supply = allocation_result_to_psi4supply(allocation_result)
                        for w in range(1, self.plan_range + 1):
                            dad_node.psi4supply[w][3] = psi4supply[w][3] if w in psi4supply else []

                        print(f"Allocation completed for {node_name}")

                        print( "psi4supply", psi4supply )

                    except Exception as e:
                        print(f"Error processing allocation for {node_name}: {e}")
            else:
                print("error: P_month_data.csv is missed")

            print("Data files loaded successfully.")



# **** A PART of ORIGINAL load_data_files *****

        def count_lots_on_S_psi4demand(node, S_list):
                if not node.children:
                        for w_psi in node.psi4demand:
                                S_list.append(w_psi[0])
                for child in node.children:
                        count_lots_on_S_psi4demand(child, S_list)
                return S_list

        S_list = []
        year_lots_list4S = []
        S_list = count_lots_on_S_psi4demand(root_node_outbound, S_list)

        #@250117 STOP
        #plan_year_st = year_st

        #for yyyy in range(plan_year_st, plan_year_st + plan_range + 1):
        for yyyy in range(int(plan_year_st), int(plan_year_st + plan_range + 1)):

                year_lots4S = count_lots_yyyy(S_list, str(yyyy))
                year_lots_list4S.append(year_lots4S)

        self.market_potential = year_lots_list4S[1]
        print("self.market_potential", self.market_potential)

        self.total_supply_plan = round(self.market_potential * self.target_share)
        print("self.total_supply_plan", self.total_supply_plan)

        for filename in os.listdir(directory):
                if filename.endswith(".csv"):
                        filepath = os.path.join(directory, filename)
                        print(f"Loading file: {filename}")
                        if "outbound" in filename.lower():
                                self.outbound_data.append(pd.read_csv(filepath))
                        elif "inbound" in filename.lower():
                                self.inbound_data.append(pd.read_csv(filepath))
        print("Outbound files loaded.")
        print("Inbound files loaded.")

        def find_node_with_cost_standard_flag(nodes, flag_value):
                for node_name, node in nodes.items():
                        if node.cost_standard_flag == flag_value:
                                return node_name, node
                return None, None

        node_name, base_leaf = find_node_with_cost_standard_flag(nodes_outbound, 100)
        self.base_leaf_name = node_name

        if node_name is None:
                print("NO cost_standard = 100 in profile")
        else:
                print(f"Node name: {node_name}, Base leaf: {base_leaf}")

        root_price = set_price_leaf2root(base_leaf, self.root_node_outbound, 100)
        print("root_price", root_price)
        set_value_chain_outbound(root_price, self.root_node_outbound)



        print("demand_planning execute")




        # *********************************
        # psi2i 4 demand
        # *********************************
        calc_all_psi2i4demand(self.root_node_outbound)


        # *********************************
        # #@250626 TEST DATA DUMP4ALLOCATION
        # *********************************

        a_DAD_node = self.nodes_outbound["DADJPN"] 

        a_DAD_node.dump_S_psi4demand() # defined on tree.py



        # ******************************************
        # confirmedSを出荷先ship2のPとSにshift&set
        # ******************************************
        # 出荷先node psiのPとSに、confirmed_SのlotsをLT shiftで置く
        # main function is this: place_P_in_supply_LT(w, ship2node, lot)
        # ******************************************

        #feedback_psi_lists(self.root_node_outbound, self.nodes_outbound)
        feedback_psi_lists(a_DAD_node, self.nodes_outbound)
        
        #@250628 GO STOP
        #self.root_node_outbound.calcPS2I4supply()
        a_DAD_node.calcPS2I4supply()




        self.update_evaluation_results()
        self.decouple_node_selected = []
        self.view_nx_matlib_stop_draw()





        print("Demand Leveling execute")
        year_st = self.plan_year_st
        year_end = year_st + self.plan_range - 1
        pre_prod_week = self.config.DEFAULT_PRE_PROC_LT
        #pre_prod_week = self.pre_proc_LT



    # +++++++++++++++++++++++++++++++++++++++++++++++
    # Mother Plant demand leveling 
    # root_node_outbound /supply / [w][0] setting S_allocated&pre_prod&leveled
    # +++++++++++++++++++++++++++++++++++++++++++++++
        #demand_leveling_on_ship(self.root_node_outbound, pre_prod_week, year_st, year_end)

        a_DAD_node.calcS2P_4supply()
        #self.root_node_outbound.calcS2P_4supply()

        #@25062829 STOP GO a_DAD_node
        #self.root_node_outbound.calcPS2I4supply()
        a_DAD_node.calcPS2I4supply()
        
        
        # ******************************************
        # confirmedSを出荷先ship2のPとSにshift&set
        # ******************************************
        # 出荷先node psiのPとSに、confirmed_SのlotsをLT shiftで置く
        # main function is this: place_P_in_supply_LT(w, ship2node, lot)
        # ******************************************
        #feedback_psi_lists(self.root_node_outbound, self.nodes_outbound)
        
        ##@250628 GO STOP
        #self.root_node_outbound.calcPS2I4supply()


        self.update_evaluation_results()
        self.psi_backup_to_file(self.root_node_outbound, 'psi_backup.pkl')
        self.view_nx_matlib_stop_draw()



        print("Supply planning with Decoupling points")
        self.root_node_outbound = self.psi_restore_from_file('psi_backup.pkl')

        if not self.decouple_node_selected:
                nodes_decouple_all = make_nodes_decouple_all(self.root_node_outbound)
                print("nodes_decouple_all", nodes_decouple_all)
                decouple_node_names = nodes_decouple_all[-2]
        else:
                decouple_node_names = self.decouple_node_selected




        #push_pull_all_psi2i_decouple4supply5(self.root_node_outbound, decouple_node_names)
        push_pull_all_psi2i_decouple4supply5(a_DAD_node, decouple_node_names)


        # eval area
        self.update_evaluation_results()


        # network area
        self.decouple_node_selected = decouple_node_names
        self.view_nx_matlib4opt()



        # PSI area
        self.root.after(1000, self.show_psi("outbound", "supply"))



        # ****************************
        # market potential Graph viewing
        # ****************************
        self.initialize_parameters()




        # Enable buttons after loading is complete
        self.supply_planning_button.config(state="normal")
        self.eval_buffer_stock_button.config(state="normal")
        print("Data files loaded and buttons enabled.")




        #try:
        #    # Perform data-loading steps
        #    self.root.update_idletasks()  # Ensure the GUI is updated during the process
        #
        #    # Assume data is successfully loaded
        #    print("Data loaded successfully!")
        #
        #    # Re-enable buttons
        #    self.supply_planning_button.config(state="normal")
        #    self.eval_buffer_stock_button.config(state="normal")
        #
        #except Exception as e:
        #    print(f"Error during data loading: {e}")
        #    tk.messagebox.showerror("Error", "Failed to load data files.")


        # Return focus to the main window
        self.root.focus_force()






# **** A PART of ORIGINAL load_data_files END *****

