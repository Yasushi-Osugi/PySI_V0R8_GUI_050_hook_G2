#load_data_files_NEW3.py


def load_data_files(self):
    directory = filedialog.askdirectory(title="Select Data Directory")
    if not directory:
        return

    try:
        self.lot_size = int(self.lot_size_entry.get())
        self.plan_year_st = int(self.plan_year_entry.get())
        self.plan_range = int(self.plan_range_entry.get())
    except ValueError:
        print("Invalid input. Using default values.")

    self.directory = directory
    self.load_directory = directory
    self.outbound_data = []
    self.inbound_data = []

    self.load_tree_structures(directory)
    self.load_cost_tables(directory)
    df_weekly = self.convert_monthly_to_weekly(directory)
    self.initialize_psi_spaces(df_weekly)
    self.perform_allocation_from_template(directory)
    self.finalize_allocation_and_render()
    self.update_evaluation_results()
    self.view_nx_matlib4opt()
    self.root.after(1000, self.show_psi("outbound", "supply"))
    self.initialize_parameters()
    self.supply_planning_button.config(state="normal")
    self.eval_buffer_stock_button.config(state="normal")
    print("Data files loaded and buttons enabled.")

def load_tree_structures(self, directory):
    data_file_list = os.listdir(directory)
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

def load_cost_tables(self, directory):
    data_file_list = os.listdir(directory)
    if "node_cost_table_outbound.csv" in data_file_list:
        read_set_cost(os.path.join(directory, "node_cost_table_outbound.csv"), self.nodes_outbound)
    else:
        print("error: node_cost_table_outbound.csv is missed")

    if "node_cost_table_inbound.csv" in data_file_list:
        read_set_cost(os.path.join(directory, "node_cost_table_inbound.csv"), self.nodes_inbound)
    else:
        print("error: node_cost_table_inbound.csv is missed")

def convert_monthly_to_weekly(self, directory):
    if "S_month_data.csv" in os.listdir(directory):
        in_file_path = os.path.join(directory, "S_month_data.csv")
        df_weekly, plan_range, plan_year_st = process_monthly_demand(in_file_path, self.lot_size)
        self.plan_year_st = plan_year_st
        self.plan_range = plan_range
        self.plan_year_entry.delete(0, tk.END)
        self.plan_year_entry.insert(0, str(self.plan_year_st))
        self.plan_range_entry.delete(0, tk.END)
        self.plan_range_entry.insert(0, str(self.plan_range))
        df_weekly.to_csv(os.path.join(directory, "S_iso_week_data.csv"), index=False)
        return df_weekly
    else:
        print("error: S_month_data.csv is missed")
        return pd.DataFrame()

def initialize_psi_spaces(self, df_weekly):
    plan_range = self.plan_range
    plan_year_st = self.plan_year_st
    root_node_outbound = self.root_node_outbound
    root_node_inbound = self.root_node_inbound

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

def perform_allocation_from_template(self, directory):
    if "P_month_data.csv" not in os.listdir(directory):
        print("error: P_month_data.csv is missed")
        return

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
            if dad_node is None:
                print(f"Warning: Node '{node_name}' not found in outbound tree.")
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
        except Exception as e:
            print(f"Error processing allocation for {node_name}: {e}")

def finalize_allocation_and_render(self):
    # [ステップ1] demand側のpsi4demand[w][0]（TOBE shipped lots）をsupply側のpsi4supply[w][0]（Sスロット）にコピー
    for node in self.nodes_outbound.values():
        for w in range(1, self.plan_range + 1):
            lots = node.psi4demand[w][0]
            node.psi4supply[w][0] = lots.copy() if lots else []

    a_DAD_node = self.nodes_outbound.get("DADJPN")
    if a_DAD_node is None:
        print("DADJPN node not found.")
        return

    a_DAD_node.dump_S_psi4demand()
    feedback_psi_lists(a_DAD_node, self.nodes_outbound)
    a_DAD_node.calcPS2I4supply()
    a_DAD_node.calcS2P_4supply()
    a_DAD_node.calcPS2I4supply()
    self.update_evaluation_results()
    self.psi_backup_to_file(self.root_node_outbound, 'psi_backup.pkl')
    self.view_nx_matlib_stop_draw()

    self.root_node_outbound = self.psi_restore_from_file('psi_backup.pkl')
    if not self.decouple_node_selected:
        nodes_decouple_all = make_nodes_decouple_all(self.root_node_outbound)
        decouple_node_names = nodes_decouple_all[-2]
    else:
        decouple_node_names = self.decouple_node_selected

    push_pull_all_psi2i_decouple4supply5(a_DAD_node, decouple_node_names)
    self.decouple_node_selected = decouple_node_names
