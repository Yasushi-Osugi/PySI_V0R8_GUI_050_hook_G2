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
            if "product_tree_outbound.csv" in data_file_list:
                file_path_OT = os.path.join(directory, "product_tree_outbound.csv")
                nodes_outbound, root_node_name_out = create_tree_set_attribute(file_path_OT)
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
                print("error: product_tree_outbound.csv is missed")

            if "product_tree_inbound.csv" in data_file_list:
                file_path_IN = os.path.join(directory, "product_tree_inbound.csv")

                nodes_inbound, root_node_name_in = create_tree_set_attribute(file_path_IN)
                root_node_inbound = nodes_inbound[root_node_name_in]

                self.nodes_inbound = nodes_inbound
                self.root_node_inbound = root_node_inbound
                set_positions(root_node_inbound)
                set_parent_all(root_node_inbound)
                print_parent_all(root_node_inbound)
            else:
                print("error: product_tree_inbound.csv is missed")








            # **************************************
            # join nodes_outbound and nodes_inbound
            # **************************************


            # マージ前に重複チェック（ログ出力あり）
            overlapping_keys = set(nodes_inbound) & set(nodes_outbound)
            if overlapping_keys:
                print(f"[Warn] Overlapping node names: {overlapping_keys}")


            #@STOP python 3.9 upper
            #node_dict = nodes_inbound | nodes_outbound

            node_dict = {**nodes_inbound, **nodes_outbound}
            #  注意：重複キーがあると、後に出てくる辞書の値で上書きされます。
            # "supply_point"がoutboundとinboundで重複しoutboundで上書きされる



            # **************************************
            # make subtree by product_name from "csv files"
            # **************************************
            def build_prod_tree_from_csv(csv_data, product_name):
                node_dict = {}
            
                # 対象 product のみ抽出
                rows = [row for row in csv_data if row["Product_name"] == product_name]
            
                for row in rows:
                    p_name = row["Parent_node"]
                    c_name = row["Child_node"]
            
                    # ノード生成（product依存で一意）
                    if p_name not in node_dict:
                        node_dict[p_name] = Node(name=p_name)
                    if c_name not in node_dict:
                        node_dict[c_name] = Node(name=c_name)
            
                    parent = node_dict[p_name]
                    child = node_dict[c_name]
            
                    child.lot_size = int(row["lot_size"])
                    child.leadtime = int(row["leadtime"])
            
                    # SKUインスタンスを割り当て（planning用）
                    # ← PSI計算後にpsi4demandなどを持たせる
                    child.sku = SKU(product_name, child.name)

                    child.parent = parent
                    parent.add_child(child)
            
                return node_dict  # this is all nodes
                #return node_dict["supply_point"]  # root node




            prod_tree_dict_IN = {} # inbound  {product_name:subtree, ,,,}
            prod_tree_dict_OT = {} # outbound {product_name:subtree, ,,,}

            product_name_list = list(node_dict["supply_point"].sku_dict.keys())
            print("product_name_list", product_name_list)

            prod_nodes = {} # by product tree node"s"

            product_tree_dict = {}


            for prod_nm in product_name_list:

                print("product_nm 4 subtree", prod_nm )

                #@250717 node4psi tree上のnode辞書も見えるようにしておく

                csv_data = read_csv_as_dictlist(file_path_OT)

                node4psi_dict_OT = build_prod_tree_from_csv(csv_data, prod_nm)
                # setting outbound root node
                prod_tree_OT = node4psi_dict_OT["supply_point"]
                prod_tree_dict_OT[prod_nm] = prod_tree_OT # root_node


                csv_data = read_csv_as_dictlist(file_path_IN)

                node4psi_dict_IN = build_prod_tree_from_csv(csv_data, prod_nm)
                # setting inbound root node
                prod_tree_IN = node4psi_dict_IN["supply_point"]
                prod_tree_dict_IN[prod_nm] = prod_tree_IN # root_node


                #@250717 STOP root_nodeのみ
                #prod_tree_dict_OT[prod_nm] = build_prod_tree_from_csv(csv_data, prod_nm)
                #prod_tree_dict_IN[prod_nm] = build_prod_tree_from_csv(csv_data, prod_nm)


            # **************************
            # GUI-計算構造のリンク
            # **************************

            # 設計項目	内容
            # plan_node.name	GUIと計算ノードの一致キーは "Node.name"
            # gui_node_dict[name]	GUI上の全ノードを辞書化しておく
            # sku_dict[product_name]	GUI上のSKU単位で .psi_node_refをセット
            # psi_node_ref	計算結果（PSI/Costなど）の直接参照ポインタ

            def link_planning_nodes_to_gui_sku(product_tree_root, gui_node_dict, product_name):
                """
                product_tree_root: 計算用Node（product別）
                gui_node_dict: GUI上の全ノード（node.name -> Nodeインスタンス）
                product_name: 対象製品名（'JPN_Koshihikari'など）
            
                SKUオブジェクトに計算ノード（Node）のポインタを渡す
                """
                def traverse_and_link(plan_node):
                    gui_node = gui_node_dict.get(plan_node.name)
                    if gui_node is not None:
                        sku = gui_node.sku_dict.get(product_name)
                        if sku:
                            #計算ノードへのリンク
                            sku.psi_node_ref = plan_node  
                    for child in plan_node.children:
                        traverse_and_link(child)
            
                traverse_and_link(product_tree_root)

                for prod_nm in product_name_list:
                    link_planning_nodes_to_gui_sku(prod_tree_dict_OT[prod_nm], nodes_outbound, prod_nm)
                    link_planning_nodes_to_gui_sku(prod_tree_dict_IN[prod_nm], nodes_inbound, prod_nm)




            
            # 検証表示
            for prod_nm in product_name_list:

                print("検証表示product_nm 4 subtree", prod_nm )

                if prod_tree_IN:
                    print("Inbound prod_tree:")
                    prod_tree_dict_IN[prod_nm].print_tree()
            
                if prod_tree_OT:
                    print("Outbound prod_tree:")
                    prod_tree_dict_OT[prod_nm].print_tree()



            # **************************************
            # end of GUI_node, PSI_node and sku data building
            # **************************************



















            # **************************************
            # setting cost parameters
            # **************************************

            #@250719 ADD
            def load_cost_param_csv(filepath):
                import csv

                param_dict = {}

                with open(filepath, newline='', encoding="utf-8-sig") as f:
                #with open(filepath, newline='', encoding="utf-8") as f:

                    reader = csv.DictReader(f)
                    print("CSV columns:", reader.fieldnames)  # デバッグ用

                    #reader = csv.DictReader(f, delimiter="\t") # タブ区切りに
                    #print("CSV columns:", reader.fieldnames)   # 確認用に追加

                    #reader = csv.DictReader(f)



                    for row in reader:
                        product = row["product_name"]
                        node = row["node_name"]

                        if product not in param_dict:
                            param_dict[product] = {}

                        param_dict[product][node] = {
                            "price": float(row.get("price_sales_shipped", 0)),
                            "transport_cost": float(row.get("logistics_costs", 0)),
                            "storage_cost": float(row.get("warehouse_cost", 0)),
                            "purchase_price": float(row.get("direct_materials_costs", 0)),  # or "purchase_total_cost"
                            "fixed_cost": float(row.get("manufacturing_overhead", 0)),
                            "profit_margin": float(row.get("profit", 0)),  # optional
                            # optional: detail for GUI use
                            "sales_admin_cost": float(row.get("sales_admin_cost", 0)),
                            "SGA_total": float(row.get("SGA_total", 0)),
                            "marketing": float(row.get("marketing_promotion", 0)),
                            "direct_labor_costs": float(row.get("direct_labor_costs", 0)),
                            # ... 他の詳細項目も追加可
                        }

                return param_dict


            if "sku_cost_table_outbound.csv" in data_file_list:

                cost_param_OT_dict = load_cost_param_csv(os.path.join(directory, "sku_cost_table_outbound.csv"))

                #@STOP
                #load_sku_cost_master(os.path.join(directory, "sku_cost_table_outbound.csv"), self.nodes_outbound)

                #@STOP
                #read_set_cost(os.path.join(directory, "node_cost_table_outbound.csv"), self.nodes_outbound)

            else:
                print("error: sku_cost_table_outbound.csv is missed")

            if "sku_cost_table_inbound.csv" in data_file_list:

                cost_param_IN_dict = load_cost_param_csv(os.path.join(directory, "sku_cost_table_inbound.csv"))


                #@STOP
                #load_sku_cost_master(os.path.join(directory, "sku_cost_table_inbound.csv"), self.nodes_inbound)

                #@STOP
                #read_set_cost(os.path.join(directory, "node_cost_table_inbound.csv"), self.nodes_inbound)

            else:
                print("error: sku_cost_table_inbound.csv is missed")







            def cost_param_setter(product_tree_root, param_dict, product_name):
                def traverse(node):
                    node_name = node.name
                    if product_name in param_dict and node_name in param_dict[product_name]:
                        param_set = param_dict[product_name][node_name]
                        sku = node.sku

                        sku.price = param_set.get("price", 0)
                        sku.transport_cost = param_set.get("transport_cost", 0)
                        sku.storage_cost = param_set.get("storage_cost", 0)
                        sku.purchase_price = param_set.get("purchase_price", 0)
                        sku.fixed_cost = param_set.get("fixed_cost", 0)
                        sku.other_cost = param_set.get("other_cost", 0)
                        sku.tariff_rate = param_set.get("tariff_rate", 0.0)  # ✅ 追加

                        # 詳細コスト（GUI用など）
                        sku.cost_details = param_set.get("cost_details", {})
                        if sku.cost_details:
                            sku.other_cost = sum(sku.cost_details.values())

                    for child in node.children:
                        traverse(child)

                traverse(product_tree_root)


            # 読み込んだ辞書を全製品ツリーに適用
            for product_name in product_tree_dict:

                cost_param_setter(subtree_OT_dict[product_name], cost_param_OT_dict, product_name)

                cost_param_setter(subtree_IN_dict[product_name], cost_param_IN_dict, product_name)


                #cost_param_setter(product_tree_dict[product_name], param_dict, product_name)

            #@250719 ADD from import
            # *****************************
            # cost propagation
            # *****************************
            gui_run_initial_propagation(product_tree_dict, directory)



#@250720 STOP
#            #@250720 ADD この後のloading processがココで止まる
#            self.view_nx_matlib4opt()
#
#
#    #@250720 ADD loading processの続きを仮設で定義
#    def load_data_files_CONTONUE(self):



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


            # **********************************
            # make&set weekly demand "Slots" on leaf_node, propagate2root
            # initial setting psi4"demand"[w][0] to psi4"supply"[w][0]
            # **********************************
            #set_df_Slots2psi4demand(self.root_node_outbound, df_weekly)
            set_df_Slots2psi4demand(root_node_outbound, df_weekly)


            # convert_monthly_to_weekly() → set_df_Slots2psi4demand() の後
            for node in self.nodes_outbound.values():
                print(f"[{node.name}] demand lots per week:",
                      [len(node.psi4demand[w][0]) for w in range(1, self.plan_range + 1)])

                      #[len(node.psi4demand[w][0]) for w in range(1, min(self.plan_range + 1, 10))])






            # ****************************************************
            # --- Allocation Logic from P_month_data.csv ---
            # ****************************************************


            # ****************************************************
            # Select Allocation Logic
            # ****************************************************
            # e.g. allocation_method = "simple" or "with_links"
            #
            #@250708 STOP
            #if allocation_method == "with_links":
            #    alloc_result, alloc_links, alloc_warn = allocate_lots_with_links(...)
            #else:
            #    alloc_result, alloc_links, alloc_warn = perform_allocation(..)






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





# **********************************
# Another ALLOCATION logic
# **********************************
#
#* 「**紐付け方式**」：S\_lotとP\_lotを1対1対応で明示リンク
#* 「**流し込み方式**」：空いているP\_lotスロットにS\_lotを流し込む（順次・容量制限）
#
#という2つの考え方がある中で、**現状の `allocate_lots_to_harvest()` は後者（流し#込み）です。**
#
#---
#
#### 🧭 一般的なSCMパッケージとの比較：
#
#| 方法         | 特徴                                         | 一般性     |
#|       ------ | ----------------------                       | -----      |
#| 紐付け方式   | トレーサビリティが高い／ロット指定に有効     | B2B向き    |
#| 流し込み方式 | キャパシティに基づき順次割当て／高速処理可能 | 汎用性高い |
#
#---
#
#### 🔧 今後の方向としては：
#
#* 流し込みベースだが **割り当て後に S\_lot と P\_lot の「参照リンク」を持たせる**
#  → ハイブリッド方式（流し込み + トレース）も可能です
#
#---
#
#ご希望であれば、このような **「紐付け情報付き・流し込み方式」** の拡張 allocation ロジックも提示できます。いかがでしょうか？
#
#
## ****************************************************************
# 「紐付け情報付き・流し込み方式」 の拡張 allocation ロジック
# ****************************************************************
#
#S\_lot を空いている週の P\_lot に流し込みながら、\*\*どの S\_lot がどの P\_lot #に対応したかを明示的に記録（紐付け）\*\*します。
#
#---
#
### 🧩 `allocate_lots_with_links()`（紐付け付き・流し込み方式）
#
#```python
#from collections import defaultdict
#
#def allocate_lots_with_links(demand_lots_dict, supply_weeks, lot_capacity=1):
#    """
#    S_lots を P_lot スロットに順次流し込みながら、
#S_lot → P_lot の対応関係を記録。
#
#    Parameters:
#        demand_lots_dict (dict[int, list[str]]): 各週の S_lot ID の辞書（例: {week: [lot1, lot2]})
#        supply_weeks (list[dict]): P_lot の空き情報（例: [{"week": 1, "capacity": 3}, ...]）
#        lot_capacity (int): 各週のキャパ数（通常は1ロット1ユニット）
#
#    Returns:
#        allocation_result (dict[int, list[str]]): P_lot 側から見た割り当て結果（psi4supply[w][3]に相当）
#        allocation_links (dict[str, dict]): 各 S_lot → {"week": w, "linked_to": "P_lot_id"} のリンク情報
#        warnings (list[str]): 割当不能な場合の警告
#    """
#    allocation_result = defaultdict(list)
#    allocation_links = {}
#    week_capacity_map = {w["week"]: w["capacity"] for w in supply_weeks}
#    sorted_weeks = sorted(week_capacity_map.keys())
#    week_index = 0
#    warnings = []
#
#    # flatten all S_lots
#    all_s_lots = []
#    for lots in demand_lots_dict.values():
#        all_s_lots.extend(lots)
#
#    for s_lot in all_s_lots:
#        allocated = False
#        attempts = 0
#        while attempts < len(sorted_weeks):
#            week = sorted_weeks[week_index % len(sorted_weeks)]
#            if len(allocation_result[week]) < week_capacity_map[week]:
#                # 擬似的に P_lot_id を week+通し番号で生成
#                p_lot_id = f"P{week}_{len(allocation_result[week])+1:04d}"
#                allocation_result[week].append(s_lot)
#                allocation_links[s_lot] = {"week": week, "linked_to": p_lot_id}
#                allocated = True
#                break
#            week_index += 1
#            attempts += 1
#        if not allocated:
#            warnings.append(f"Cannot allocate S_lot {s_lot} — all weeks full")
#
#    return dict(allocation_result), allocation_links, warnings
#```
#
#---
#
### ✅ 戻り値の意味
#
#| 変数名              | 内容                                                 |
#| ------------------- | --------------------------------------------         |
#| allocation_result   | psi4supply[w][3]各週にどの S_lot が割当てられたか    |
#| allocation_links    | 各S_lotが"いつ""どの"仮想 P\_lot\_id に割当てられたか|
#| `warnings`          | 割当失敗した S\_lot の記録                           |
#
#
#---
#
### 📌 活用方法
#
#```python
#allocation_result, allocation_links, warnings = allocate_lots_with_links(demand_map, harvest_weeks)
#
## psi4supply 更新
#for w, s_lots in allocation_result.items():
#    node.psi4supply[w][3] = s_lots  # または extend など
#
## S_lot ごとの対応先の追跡が可能
#for s_lot, link_info in allocation_links.items():
#    print(f"{s_lot} was allocated to week {link_info['week']} as {link_info['linked_to']}")
#```
#
#---
#
### 🔧 拡張可能なポイント
#
#* `linked_to` に実際の `Lot` インスタンスを入れると P\_lot と S\_lot の双方向リ#ンクが可能
#* 週別に複数 SKU の同時割当てにも対応可能（SKU名をキーにするだけ）
#
#---
#
#ご希望に応じて：
#
#* `Lot` クラスを用いた双方向リンク化
#* GUI表示やログ出力の統合
#
#などの拡張も可能です。必要であれば続けて提案します。

# *************************************************************************



            # *******************************
            # EXIT allocation process
            # *******************************

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



        # *********************************************
        # setting VALUE 
        # *********************************************

        #@250719 "REMOVED" setting VALUE 
        #@250719 "ALTERNATED" from import xxxx
        # gui_run_initial_propagation(product_tree_dict, directory)





        print("demand_planning execute")

        # *********************************
        # psi2i 4 demand
        # *********************************
        calc_all_psi2i4demand(self.root_node_outbound)



        # ********************************
        # PRE_SET decouple node before "supply" planning 
        # ********************************
        if not self.decouple_node_selected:
                nodes_decouple_all = make_nodes_decouple_all(self.root_node_outbound)
                print("nodes_decouple_all", nodes_decouple_all)
                decouple_node_names = nodes_decouple_all[-2]
        else:
                decouple_node_names = self.decouple_node_selected




        # *********************************
        # #@250626 TEST DATA DUMP4ALLOCATION
        # *********************************


        #@250705 MEMO 
        # 1. "total_supply"のchildren_listとしてDADxxxを抽出する
        # 2. for a_DAD_node in children_list:でDADxxx以降の計画を処理する


        total_supply_node = self.nodes_outbound["supply_point"] 

        DADs_list = total_supply_node.children


        print("DADs_list", DADs_list)

        for dad in DADs_list:

            print("dad.name is ", dad.name )
        
        #@250706 STOP
        #a_DAD_node.dump_PSI_psi4demand() # defined on tree.py
        #a_DAD_node = self.nodes_outbound["DADJPN"] 
        #a_DAD_node.dump_PSI_psi4demand() # defined on tree.py


        # ******************************************
        # confirmedSを出荷先ship2のPとSにshift&set
        # ******************************************
        # 出荷先node psiのPとSに、confirmed_SのlotsをLT shiftで置く
        # main function is this: place_P_in_supply_LT(w, ship2node, lot)
        # ******************************************

        #@2500630 STOP
        ##feedback_psi_lists(self.root_node_outbound, self.nodes_outbound)
        #feedback_psi_lists(a_DAD_node, self.nodes_outbound)
        

        #@250628 GO STOP
        #@250630 GO
        ##self.root_node_outbound.calcPS2I4supply()
        #
        #a_DAD_node.calcPS2I4supply()


            # This is DADs PS2I planning
            dad.calcPS2I4supply()


        #@250706 STOP
        #print("after a_DAD_node.calcPS2I4supply() is this")
        #a_DAD_node.dump_PSI_psi4demand() # defined on tree.py

        ##@250630 probe psi4supply[][]
        #a_DAD_node = self.nodes_outbound["DADJPN"] 
        #print("250630 probe psi4supply[][] after calcPS2I4supply", a_DAD_node.name, a_DAD_node.psi4supply)

     
        #@250630 STOP
        #self.update_evaluation_results()
        #self.decouple_node_selected = []
        #self.view_nx_matlib_stop_draw()




        #@250706 
        # "Demand Leveling"と先行生産は、需給バランス"Lot Allocation"の1つ
        # 今回の米のLot Allocationは初期load_datafilesの中で"P_lots"生成で実施

        #@250706 STOP
        #print("Demand Leveling execute")
        #year_st = self.plan_year_st
        #year_end = year_st + self.plan_range - 1
        #pre_prod_week = self.config.DEFAULT_PRE_PROC_LT
        ##pre_prod_week = self.pre_proc_LT



    # +++++++++++++++++++++++++++++++++++++++++++++++
    # Mother Plant demand leveling 
    # root_node_outbound /supply / [w][0] setting S_allocated&pre_prod&leveled
    # +++++++++++++++++++++++++++++++++++++++++++++++
        #demand_leveling_on_ship(self.root_node_outbound, pre_prod_week, year_st, year_end)



        #@250630 STOP
        #a_DAD_node.calcS2P_4supply()
        ##self.root_node_outbound.calcS2P_4supply()
        #


        #@25062829 STOP GO a_DAD_node
        #@250630 GO
        #self.root_node_outbound.calcPS2I4supply()
        #a_DAD_node.calcPS2I4supply()
        
        
        # ******************************************
        # confirmedSを出荷先ship2のPとSにshift&set
        # ******************************************
        # 出荷先node psiのPとSに、confirmed_SのlotsをLT shiftで置く
        # main function is this: place_P_in_supply_LT(w, ship2node, lot)
        # ******************************************
        #feedback_psi_lists(self.root_node_outbound, self.nodes_outbound)
        
        ##@250628 GO STOP
        #self.root_node_outbound.calcPS2I4supply()


        #@250630 STOP GO
        #self.update_evaluation_results()
        #self.psi_backup_to_file(self.root_node_outbound, 'psi_backup.pkl')
        #self.view_nx_matlib_stop_draw()


        #@250630_0701 STOP 
        #print("Supply planning with Decoupling points")
        #self.root_node_outbound = self.psi_restore_from_file('psi_backup.pkl')


        #@250706 STOP
        ##@250630 probe psi4supply[][]
        #a_DAD_node = self.nodes_outbound["DADJPN"] 
        #print("250630 probe psi4supply[][] 4 show_PSI", a_DAD_node.name, a_DAD_node.psi4supply)


        #@250706 STOP
        ## ********************************
        ## setting decouple node
        ## ********************************
        #if not self.decouple_node_selected:
        #        nodes_decouple_all = make_nodes_decouple_all(self.root_node_outbound)
        #        print("nodes_decouple_all", nodes_decouple_all)
        #        decouple_node_names = nodes_decouple_all[-2]
        #else:
        #        decouple_node_names = self.decouple_node_selected


        #@250706 STOP
        ##@250630_0701 STOP GO
        ##push_pull_all_psi2i_decouple4supply5(self.root_node_outbound, decouple_node_names)
        #push_pull_all_psi2i_decouple4supply5(a_DAD_node, decouple_node_names)


            # This is DADs PUSH&PULL planning
            push_pull_all_psi2i_decouple4supply5(dad, decouple_node_names)

        # *************************
        # End of DADs planning
        # *************************


        # eval area
        self.update_evaluation_results()


        # network area
        self.decouple_node_selected = decouple_node_names
        self.view_nx_matlib4opt()



        # PSI area
        #self.root.after(1000, self.show_psi("outbound", "supply"))

        self.root.after(1000, lambda: self.show_psi("outbound", "supply"))
        # lambda: にすることで、1000ms 後に初めて show_psi() を実行する
        # という本来の動きに


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



