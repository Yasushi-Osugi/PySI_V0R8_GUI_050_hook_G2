#plan_env_main.py

#EPNode = "Engine Proxy Node"

class PlanEnv:

    def __init__(self, config):


        self.config = config

        #self.root.title(self.config.APP_NAME)
        #
        #self.info_window = None

        self.tree_structure = None

        # setup_uiの前にproduct selectを初期化
        self.product_name_list = []
        self.product_selected = None

        ## 必ず setup_ui を先に呼び出す
        #self.setup_ui()
        
        # 必要な初期化処理を後から呼び出す
        self.initialize_parameters()



        # ********************************
        # PSI planner
        # ********************************
        self.outbound_data = None
        self.inbound_data = None

        # PySI tree
        self.root_node_outbound = None
        self.nodes_outbound     = None
        self.leaf_nodes_out     = []

        self.root_node_inbound  = None
        self.nodes_inbound      = None
        self.leaf_nodes_in      = []

        self.root_node_out_opt  = None
        self.nodes_out_opt      = None
        self.leaf_nodes_opt     = []


        self.optimized_root     = None
        self.optimized_nodes    = None



        self.node_psi_dict_In4Dm = {}  # 需要側 PSI 辞書
        self.node_psi_dict_In4Sp = {}  # 供給側 PSI 辞書

        # market
        self.market_potential = 0

        # Evaluation on PSI
        self.total_revenue = 0
        self.total_profit  = 0
        self.profit_ratio  = 0

        # by product select view
        self.prod_tree_dict_IN = {}
        self.prod_tree_dict_OT = {}


        # view
        self.select_node = None
        self.G = None

        # Optimise
        self.Gdm_structure = None

        self.Gdm = None
        self.Gsp = None

        self.pos_E2E = None

        self.flowDict_opt = {} #None
        self.flowCost_opt = {} #None

        self.total_supply_plan = 0

        # loading files
        self.directory = None
        self.load_directory = None

        self.base_leaf_name = {} # { product_name: leaf_node_name, ,,,}

        # supply_plan / decoupling / buffer stock
        self.decouple_node_dic = {}

        self.decouple_node_selected = []

# ******************************
# PlanEnv method def(self, xxx) start
# ******************************


# ******************************
#@250811 chatGPT defined 
# ******************************
#
# plan_env.py などに配置
from __future__ import annotations
from typing import Dict, List, Tuple, Optional, Type
import csv, os

# 既存の PlanNode を注入できるようにしておく（未指定なら内蔵の極小版を使う）
class _MiniPlanNode:
    def __init__(self, name: str, node_type: str = "node"):
        self.id = name              # 既存系が id と name を持つ想定に合わせる
        self.name = name
        self.node_type = node_type
        self.children: List["_MiniPlanNode"] = []
        self.parent: Optional["_MiniPlanNode"] = None

        # 任意属性（必要に応じてエンジン橋渡し時に使う）
        self.lot_size: Optional[int] = None
        self.leadtime: Optional[int] = None
        self.sku_name: Optional[str] = None     # 「SKUクラス不使用」前提で文字列だけ持つ

    def add_child(self, c: "_MiniPlanNode"):
        c.parent = self
        self.children.append(c)

class PlanEnv:
    """GUIを剥がした最小の計画モデルホルダ
       - prod_tree_dict_OT/IN に {product_name: PlanNode(root)} を持つ
    """
    def __init__(self):
        self.base_dir: str = ""

        self.product_name_list: List[str] = []
        self.product_selected: Optional[str] = None

        self.prod_tree_dict_OT: Dict[str, object] = {}
        self.prod_tree_dict_IN: Dict[str, object] = {}

    # ---- public helpers -------------------------------------------------
    def get_roots(self, product: Optional[str] = None) -> Tuple[object, object]:
        """選択製品の (OUT_root, IN_root) を返す（無い側は None）"""
        p = product or self.product_selected
        return self.prod_tree_dict_OT.get(p), self.prod_tree_dict_IN.get(p)

    def iter_products(self):
        for p in self.product_name_list:
            yield p

    # ---- factory --------------------------------------------------------
    @classmethod
    def from_dir(cls, dir_path: str, PlanNodeClass: Type = _MiniPlanNode) -> "PlanEnv":
        """CSVディレクトリから PlanEnv を構築する最小版。
           期待列: Product_name, Parent_node, Child_node, lot_size, leadtime
        """
        def _read_csv(path: str) -> List[dict]:
            with open(path, newline="", encoding="utf-8-sig") as f:
                return list(csv.DictReader(f))

        def _build_prod_tree(rows: List[dict], product: str) -> Optional[object]:
            rows_p = [r for r in rows if r.get("Product_name") == product]
            if not rows_p:
                return None
            nodes: Dict[str, object] = {}
            has_parent = set()
            for r in rows_p:
                pn = r["Parent_node"].strip()
                cn = r["Child_node"].strip()
                # ノード生成
                if pn not in nodes: nodes[pn] = PlanNodeClass(pn)
                if cn not in nodes: nodes[cn] = PlanNodeClass(cn)
                parent = nodes[pn]; child = nodes[cn]
                # 属性（あれば）
                try: child.lot_size = int(r.get("lot_size", "") or 0) or None
                except: pass
                try: child.leadtime = int(r.get("leadtime", "") or 0) or None
                except: pass
                child.sku_name = product
                # 接続
                parent.add_child(child)
                has_parent.add(cn)
            # ルート推定：親を持たないノード、なければ 'supply_point' 優先
            candidates = [n for n in nodes if n not in has_parent]
            root_name = "supply_point" if "supply_point" in nodes else (candidates[0] if candidates else None)
            return nodes[root_name] if root_name else None

        # --- 準備
        env = cls()
        env.base_dir = dir_path

        # ファイル存在確認
        ot_path = os.path.join(dir_path, "product_tree_outbound.csv")
        in_path = os.path.join(dir_path, "product_tree_inbound.csv")
        rows_ot = _read_csv(ot_path) if os.path.exists(ot_path) else []
        rows_in = _read_csv(in_path) if os.path.exists(in_path) else []

        # 製品一覧（OUT/IN の和集合）
        prods = {r["Product_name"] for r in rows_ot} | {r["Product_name"] for r in rows_in}
        env.product_name_list = sorted(prods)
        env.product_selected = env.product_name_list[0] if env.product_name_list else None

        # 製品別ツリーを構築
        for p in env.product_name_list:
            root_ot = _build_prod_tree(rows_ot, p)
            root_in = _build_prod_tree(rows_in, p)
            if root_ot: env.prod_tree_dict_OT[p] = root_ot
            if root_in: env.prod_tree_dict_IN[p] = root_in

        return env


# *****************************

    def initialize_parameters(self):

        print("Initializing parameters")
        self.lot_size     = self.config.DEFAULT_LOT_SIZE
        self.plan_year_st = self.config.DEFAULT_START_YEAR
        self.plan_range   = self.config.DEFAULT_PLAN_RANGE

        self.pre_proc_LT  = self.config.DEFAULT_PRE_PROC_LT
    
        # self.market_potential = 0 # initial setting from "demand_generate"
        self.target_share = self.config.DEFAULT_TARGET_SHARE
        self.total_supply = 0




        #if not hasattr(self, 'gmp_entry') or not hasattr(self, 'ts_entry') or not hasattr(self, 'tsp_entry'):
        #    raise AttributeError("Required UI components (gmp_entry, ts_entry, tsp_entry) have not been initialized.")


        print("Setting market potential and share")
        # Calculation and setting of Global Market Potential
        #market_potential = getattr(self, 'market_potential', self.config.DEFAULT_MARKET_POTENTIAL)  # Including initial settings

        self.market_potential = self.config.DEFAULT_MARKET_POTENTIAL)  # Including initial settings

        #self.gmp_entry.delete(0, tk.END)
        #self.gmp_entry.insert(0, "{:,}".format(market_potential))  # Display with comma separated thousands

        # Initial setting of Target Share (already set in setup_ui)

        # Calculation and setting of Total Supply Plan
        #target_share = float(self.ts_entry.get().replace('%', ''))/100  # Convert string to float and remove %

        total_supply_plan = round(market_potential * target_share)
        #self.tsp_entry.delete(0, tk.END)
        #self.tsp_entry.insert(0, "{:,}".format(total_supply_plan))  # Display with comma separated thousands

        #self.global_market_potential  = global_market_potential

        self.market_potential         = market_potential
        self.target_share             = target_share           
        self.total_supply_plan        = total_supply_plan
        print(f"At initialization - market_potential: {self.market_potential}, target_share: {self.target_share}")  # Add log




#@250630 STOP GO
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


            # **************************************
            # this is Nodes_all for GUI handling
            # **************************************
            node_dict = {**nodes_inbound, **nodes_outbound}
            #  注意：重複キーがあると、後に出てくる辞書の値で上書きされます。
            # "supply_point"がoutboundとinboundで重複しoutboundで上書きされる



            #@250726 ココでby productのPlanNodeを生成
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
                        node_dict[p_name] = PlanNode(name=p_name) #@250726MARK
                        #node_dict[p_name] = Node(name=p_name) #@250726MARK

                    if c_name not in node_dict:
                        node_dict[c_name] = PlanNode(name=c_name)
                        #node_dict[c_name] = Node(name=c_name)

            
                    parent = node_dict[p_name]
                    child = node_dict[c_name]
            
                    child.lot_size = int(row["lot_size"])
                    child.leadtime = int(row["leadtime"])
            
                    # SKUインスタンスを割り当て（planning用）
                    # ← PSI計算後にpsi4demandなどを持たせる
                    child.sku = SKU(product_name, child.name)

                    #@250728 STOP see "link_planning_nodes_to_gui_sku" in end_of_loading
                    ##@250728 MEMO linkage plan_node2gui_node
                    #gui_node = nodes_all[child.name]         # picking up gui_node
                    #gui_node.sku_dict[product_name] = child　# linking plan_node 2 gui_node
                    ##@250728 MEMO "plan_node = sku"となるので、planning engineはplan_nodeで良いsku無し

                    #@250726 STOP by productのPlanNodeの世界なので、node直下にskuがあり、sku_dictはxxx
                    #@250728 sku_dict[product_name] = plan_nodeとして、GUINodeとPlanNodeをlinkする
                    #        このlinkingは、plan_nodeのbuilding processで行う
                    ##@250725 MEMO setting for Multi-Product
                    #child.sku_dict[product_name] = SKU(product_name, child.name)

                    child.parent = parent
                    parent.add_child(child)
            
                return node_dict  # this is all nodes
                #return node_dict["supply_point"]  # root node




            prod_tree_dict_IN = {} # inbound  {product_name:subtree, ,,,}
            prod_tree_dict_OT = {} # outbound {product_name:subtree, ,,,}

            product_name_list = list(node_dict["supply_point"].sku_dict.keys())
            print("product_name_list", product_name_list)

            # initial setting product_name 
            self.product_name_list = product_name_list
            self.product_selected = product_name_list[0]
            
            # initial setting for "Select Product" BOX UI  
            self.cb_product['values'] = self.product_name_list
            if self.product_name_list:
                self.cb_product.current(0)


            prod_nodes = {} # by product tree node"s"

            product_tree_dict = {}


            for prod_nm in product_name_list:

                print("product_nm 4 subtree", prod_nm )

                #@250717 node4psi tree上のnode辞書も見えるようにしておく

                csv_data = read_csv_as_dictlist(file_path_OT)

                node4psi_dict_OT = build_prod_tree_from_csv(csv_data, prod_nm)
                # setting outbound root node
                prod_tree_root_OT = node4psi_dict_OT["supply_point"]
                prod_tree_dict_OT[prod_nm] = prod_tree_root_OT # by product root_node


                csv_data = read_csv_as_dictlist(file_path_IN)

                node4psi_dict_IN = build_prod_tree_from_csv(csv_data, prod_nm)
                # setting inbound root node
                prod_tree_root_IN = node4psi_dict_IN["supply_point"]
                prod_tree_dict_IN[prod_nm] = prod_tree_root_IN # by Product root_node


                #@250717 STOP root_nodeのみ
                #prod_tree_dict_OT[prod_nm] = build_prod_tree_from_csv(csv_data, prod_nm)
                #prod_tree_dict_IN[prod_nm] = build_prod_tree_from_csv(csv_data, prod_nm)


                #@250726 MEMO by Productでroot_nodeとnodesを生成後、
                # PlanNodeのroot_nodeからselfたどって? self.xxxとしてセットする
                def make_leaf_nodes(node, list):
                    if node.children == []: # leaf_nodeの場合
                        list.append(node.name)
                    else:
                        pass

                    for child in node.children:
                        make_leaf_nodes(child, list)

                    return list

                leaf_nodes = []
                
                leaf_nodes = make_leaf_nodes(prod_tree_root_OT, leaf_nodes)
                #leaf_nodes = make_leaf_nodes(root_node_out, leaf_nodes)


                #@250726 STOP このself.はGUI
                ## PlanNodeのinstanceも、self.xxx/plan_node.xxxの属性名は共通
                #leaf_nodes_out = make_leaf_nodes(prod_tree_root_OT, [])
                #
                #self.nodes_outbound = node4psi_dict_OT
                #self.root_node_outbound = prod_tree_root_OT
                #
                #self.leaf_nodes_out = leaf_nodes_out
                #
                ## このby ProductのpositionsはPlanNodeでは未使用GUINodeを使う
                ##set_positions(prod_tree_root_OT) 

                #@250726 STOP 各nodeがtree全体の情報nodesを持つのは冗長
                #for node_name in list( node4psi_dict_OT.keys() ):
                #    plan_node = node4psi_dict_OT[node_name]
                #
                #    plan_node.nodes_outbound = node4psi_dict_OT
                #    plan_node.root_node_outbound = prod_tree_root_OT
                #
                #    leaf_nodes_out = make_leaf_nodes(prod_tree_root_OT, [])
                #    plan_node.leaf_nodes_out = leaf_nodes_out

                #@250726 GO
                set_parent_all(prod_tree_root_OT)
                print_parent_all(prod_tree_root_OT)



                #leaf_nodes_out = make_leaf_nodes(root_node_outbound, [])
                #self.nodes_outbound = nodes_outbound
                #self.root_node_outbound = root_node_outbound
                #self.leaf_nodes_out = leaf_nodes_out
                #set_positions(root_node_outbound)
                #set_parent_all(root_node_outbound)
                #print_parent_all(root_node_outbound)





                #@250726 STOP このself.はGUI
                ## nodes_inbound, root_node_name_in = create_tree_set_attribute(file_path_IN)
                ## root_node_inbound = nodes_inbound[root_node_name_in]
                #
                #self.nodes_inbound = node4psi_dict_IN
                #self.root_node_inbound = prod_tree_root_IN
                #
                ## このby ProductのpositionsはPlanNodeでは未使用GUINodeを使う
                ##set_positions(prod_tree_root_IN)
                #

                #@250726 STOP 各nodeがtree全体の情報nodesを持つのは冗長
                #for node_name in list( node4psi_dict_IN.keys() ):
                #    plan_node = node4psi_dict_IN[node_name]
                #
                #    plan_node.nodes_inbound = node4psi_dict_IN
                #    plan_node.root_node_inbound = prod_tree_root_IN
                #
                #    leaf_nodes_in = make_leaf_nodes(prod_tree_root_IN, [])
                #    plan_node.leaf_nodes_in = leaf_nodes_in

                #@250726 GO
                set_parent_all(prod_tree_root_IN)
                print_parent_all(prod_tree_root_IN)


                #nodes_inbound, root_node_name_in = create_tree_set_attribute(file_path_IN)
                #root_node_inbound = nodes_inbound[root_node_name_in]
                #
                #self.nodes_inbound = nodes_inbound
                #self.root_node_inbound = root_node_inbound
                #set_positions(root_node_inbound)
                #set_parent_all(root_node_inbound)
                #print_parent_all(root_node_inbound)






            # **************************
            # GUI-計算構造のリンク
            # **************************

            # 設計項目	内容
            # plan_node.name	GUIと計算ノードの一致キーは "Node.name"
            # gui_node_dict[name]	GUI上の全ノードを辞書化しておく

            #@250728 STOP
            ## sku_dict[product_name]	GUI上のSKU単位で .psi_node_refをセット
            ## psi_node_ref	計算結果（PSI/Costなど）の直接参照ポインタ

            #@250728 GO
            # sku_dict[product_name]	gui_nodeのby product(SKU単位)で、ここにplan_nodeを直接セット
            # "plan_node=sku"という意味合い



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

                        #@250728 STOP
                        #sku = gui_node.sku_dict.get(product_name)
                        #if sku:
                        #    #計算ノードへのリンク
                        #    sku.psi_node_ref = plan_node

                        #@250728 GO
                        gui_node.sku_dict[product_name] = plan_node # Plan2GUI direct setting



                    for child in plan_node.children:
                        traverse_and_link(child)
            
                traverse_and_link(product_tree_root)

            for prod_nm in product_name_list:
                link_planning_nodes_to_gui_sku(prod_tree_dict_OT[prod_nm], nodes_outbound, prod_nm)
                link_planning_nodes_to_gui_sku(prod_tree_dict_IN[prod_nm], nodes_inbound, prod_nm)


            # save to self.xxx
            self.prod_tree_dict_OT = prod_tree_dict_OT
            self.prod_tree_dict_IN = prod_tree_dict_IN

            
            # 検証表示
            for prod_nm in product_name_list:

                print("検証表示product_nm 4 subtree", prod_nm )

                if prod_tree_root_IN:
                    print("Inbound prod_tree:")
                    prod_tree_dict_IN[prod_nm].print_tree()
            
                if prod_tree_root_OT:
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
                            "cost_total": float(row.get("cost_total", 0)),
                            "profit_margin": float(row.get("profit", 0)),  # optional

                            "marketing": float(row.get("marketing_promotion", 0)),
                            "sales_admin_cost": float(row.get("sales_admin_cost", 0)),
                            "SGA_total": float(row.get("SGA_total", 0)),
                            
                            "transport_cost": float(row.get("logistics_costs", 0)),
                            "storage_cost": float(row.get("warehouse_cost", 0)),
                            "purchase_price": float(row.get("direct_materials_costs", 0)),  
                            "tariff_cost": float(row.get("tariff_cost", 0)),  
                            "purchase_total_cost": float(row.get("purchase_total_cost", 0)), 

                            "direct_labor_cost": float(row.get("direct_labor_costs", 0)),
                            "fixed_cost": float(row.get("manufacturing_overhead", 0)),


                            # optional: detail for GUI use
                            "prod_indirect_labor": float(row.get("prod_indirect_labor", 0)),
                            "prod_indirect_cost": float(row.get("prod_indirect_others", 0)),
                            "depreciation_cost": float(row.get("depreciation_others", 0)),
                            # ... 他の詳細項目も追加可
                        }

                return param_dict


            if "sku_cost_table_outbound.csv" in data_file_list:

                cost_param_OT_dict = load_cost_param_csv(os.path.join(directory, "sku_cost_table_outbound.csv"))
                print("cost_param_OT_dict", cost_param_OT_dict)
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



            ## Cost structure demand
            #self.price_sales_shipped = 0
            #self.cost_total = 0
            #self.profit = 0
            #self.marketing_promotion = 0
            #self.sales_admin_cost = 0
            #self.SGA_total = 0
            #self.custom_tax = 0
            #self.tax_portion = 0
            #self.logistics_costs = 0
            #self.warehouse_cost = 0
            #self.direct_materials_costs = 0
            #self.purchase_total_cost = 0
            #self.prod_indirect_labor = 0
            #self.prod_indirect_others = 0
            #self.direct_labor_costs = 0
            #self.depreciation_others = 0
            #self.manufacturing_overhead = 0


            # this is "product_tree" operation / that is "PlanNode"
            def cost_param_setter(product_tree_root, param_dict, product_name):
                def traverse(node):
                    node_name = node.name
                    if product_name in param_dict and node_name in param_dict[product_name]:
                        param_set = param_dict[product_name][node_name]

                        #@250801 memo node is an instance of "PlanNode"
                        sku = node.sku


                        sku.price               = param_set.get("price", 0)              
                        sku.cost_total          = param_set.get("cost_total", 0)         
                        sku.profit_margin       = param_set.get("profit_margin", 0)      
                                                                
                        sku.marketing           = param_set.get("marketing", 0)          
                        sku.sales_admin_cost    = param_set.get("sales_admin_cost", 0)   
                        sku.SGA_total           = param_set.get("SGA_total", 0)          
                                                                
                        sku.transport_cost      = param_set.get("transport_cost", 0)     
                        sku.storage_cost        = param_set.get("storage_cost", 0)       
                        sku.purchase_price      = param_set.get("purchase_price", 0)     
                        sku.tariff_cost         = param_set.get("tariff_cost", 0)
                        sku.purchase_total_cost = param_set.get("purchase_total_cost", 0)
                                                                
                        sku.direct_labor_costs  = param_set.get("direct_labor_costs", 0) 
                        sku.fixed_cost          = param_set.get("fixed_cost", 0)         
                                                                
                        sku.prod_indirect_labor = param_set.get("prod_indirect_labor", 0)
                        sku.prod_indirect_cost  = param_set.get("prod_indirect_cost", 0) 
                        sku.depreciation_cost   = param_set.get("depreciation_cost", 0)  



                        #sku.price               = param_set.get("sku.price", 0)              
                        #sku.cost_total          = param_set.get("sku.cost_total", 0)         
                        #sku.profit_margin       = param_set.get("sku.profit_margin", 0)      
                                                                
                        #sku.marketing           = param_set.get("sku.marketing", 0)          
                        #sku.sales_admin_cost    = param_set.get("sku.sales_admin_cost", 0)   
                        #sku.SGA_total           = param_set.get("sku.SGA_total", 0)          
                                                                
                        #sku.transport_cost      = param_set.get("sku.transport_cost", 0)     
                        #sku.storage_cost        = param_set.get("sku.storage_cost", 0)       
                        #sku.purchase_price      = param_set.get("sku.purchase_price", 0)     
                        #sku.tariff_cost         = param_set.get("tariff_cost", 0)
                        #sku.purchase_total_cost = param_set.get("sku.purchase_total_cost", 0)
                                                                
                        #sku.direct_labor_costs  = param_set.get("sku.direct_labor_costs", 0) 
                        #sku.fixed_cost          = param_set.get("sku.fixed_cost", 0)         
                                                                
                        #sku.prod_indirect_labor = param_set.get("sku.prod_indirect_labor", 0)
                        #sku.prod_indirect_cost  = param_set.get("sku.prod_indirect_cost", 0) 
                        #sku.depreciation_cost   = param_set.get("sku.depreciation_cost", 0)  



                        #sku.price = param_set.get("price", 0)
                        #sku.transport_cost = param_set.get("transport_cost", 0)
                        #sku.storage_cost = param_set.get("storage_cost", 0)
                        #sku.purchase_price = param_set.get("purchase_price", 0)
                        #sku.fixed_cost = param_set.get("fixed_cost", 0)
                        #sku.other_cost = param_set.get("other_cost", 0)

                        #sku.total_cost = (
                        #    sku.purchase_price + sku.transport_cost + sku.storage_cost +
                        #    sku.tariff_cost + sku.fixed_cost + sku.other_cost
                        #)

                        # ✅ PlanNode 側へコピー

                        node.cs_price_sales_shipped    = sku.price               
                        node.cs_cost_total             = sku.cost_total          
                        node.cs_profit                 = sku.profit_margin       
                                                                                
                        node.cs_marketing_promotion    = sku.marketing           
                        node.cs_sales_admin_cost       = sku.sales_admin_cost    
                        node.cs_SGA_total              = sku.SGA_total           
                                                                                
                        node.cs_logistics_costs        = sku.transport_cost      
                        node.cs_warehouse_cost         = sku.storage_cost        
                        node.cs_direct_materials_costs = sku.purchase_price      
                        node.cs_tax_portion            = sku.tariff_cost         
                        node.cs_purchase_total_cost    = sku.purchase_total_cost 
                                                                                
                        node.cs_direct_labor_costs     = sku.direct_labor_costs  
                        node.cs_manufacturing_overhead = sku.fixed_cost          
                                                                                
                        node.cs_prod_indirect_labor    = sku.prod_indirect_labor 
                        node.cs_prod_indirect_others   = sku.prod_indirect_cost  
                        node.cs_depreciation_others    = sku.depreciation_cost   
  

                        #node.eval_cs_price_sales_shipped = sku.price
                        #node.eval_cs_profit = sku.price - sku.total_cost
                        #node.eval_cs_SGA_total = param_set.get("SGA_total", 0)
                        #node.eval_cs_tax_portion = sku.tariff_cost
                        #node.eval_cs_logistics_costs = sku.transport_cost
                        #node.eval_cs_warehouse_cost = sku.storage_cost
                        #node.eval_cs_direct_materials_costs = sku.purchase_price

                    for child in node.children:
                        traverse(child)

                traverse(product_tree_root)



            # 読み込んだ辞書を全製品ツリーに適用
            for product_name in list(prod_tree_dict_OT.keys()):
                #@250729 ADD
                print("cost_param_OT_dict", cost_param_OT_dict)

                cost_param_setter(prod_tree_dict_OT[product_name], cost_param_OT_dict, product_name)
                #cost_param_setter(subtree_OT_dict[product_name], cost_param_OT_dict, product_name)


            for product_name in list(prod_tree_dict_IN.keys()):

                cost_param_setter(prod_tree_dict_IN[product_name], cost_param_IN_dict, product_name)
                #cost_param_setter(subtree_IN_dict[product_name], cost_param_IN_dict, product_name)



                #cost_param_setter(product_tree_dict[product_name], param_dict, product_name)

            #@250719 ADD from import
            # *****************************
            # cost propagation
            # *****************************

            # 0.setting price table
            selling_price_table_csv = os.path.join(directory, "selling_price_table.csv")
            tobe_price_dict = load_tobe_prices(selling_price_table_csv)
            assign_tobe_prices_to_leaf_nodes(prod_tree_dict_OT, tobe_price_dict)

            shipping_price_table_csv = os.path.join(directory, "shipping_price_table.csv")
            asis_price_dict = load_asis_prices(shipping_price_table_csv)
            assign_asis_prices_to_root_nodes(prod_tree_dict_OT, asis_price_dict)

            print("offering_price check: self.nodes_outbound[ CS_JPN ].sku_dict[ JPN_Koshihikari ].offering_price_TOBE", self.nodes_outbound["CS_JPN"].sku_dict["JPN_Koshihikari"].offering_price_TOBE)
            print("offering_price check: self.nodes_outbound[ DADJPN ].sku_dict[ JPN_RICE_1 ].offering_price_TOBE", self.nodes_outbound["DADJPN"].sku_dict["JPN_RICE_1"].offering_price_TOBE)

            # 1.initial propagation 実行
            print("cost propagation processing")
            gui_run_initial_propagation(prod_tree_dict_OT, directory)
            #@250807 STOP
            #gui_run_initial_propagation(prod_tree_dict_IN, directory)

            print("offering_price check: self.nodes_outbound[ CS_JPN ].sku_dict[ JPN_Koshihikari ].offering_price_TOBE", self.nodes_outbound["CS_JPN"].sku_dict["JPN_Koshihikari"].offering_price_TOBE)
            print("offering_price check: self.nodes_outbound[ DADJPN ].sku_dict[ JPN_RICE_1 ].offering_price_TOBE", self.nodes_outbound["DADJPN"].sku_dict["JPN_RICE_1"].offering_price_TOBE)

            # 2.PlanNodeへの評価値のコピー
            print("propagate_cost_to_plan_nodes start...")
            #self.print_cost_sku()
            #self.print_cost_node_cs()
            #self.print_cost_node_eval_cs()

            propagate_cost_to_plan_nodes(prod_tree_dict_OT)
            propagate_cost_to_plan_nodes(prod_tree_dict_IN)

            print("propagate_cost_to_plan_nodes end...")
            #self.print_cost_sku()
            #self.print_cost_node_cs()
            #self.print_cost_node_eval_cs()


#@250720 STOP
#            #@250720 ADD この後のloading processがココで止まる
#            self.view_nx_matlib4opt()
#
#
#    #@250720 ADD loading processの続きを仮設で定義
#    def load_data_files_CONTONUE(self):



            # **************************************
            # setting S_month 2 psi4demand 
            # **************************************

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


            # ****************************************
            # Original Node base demand setting
            # ****************************************
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



            # ****************************************
            # by Product tree with PlanNode  demand setting
            # ****************************************
            for prod_nm in product_name_list:
                
                prod_tree_root_OT = prod_tree_dict_OT[prod_nm] 
                prod_tree_root_IN = prod_tree_dict_IN[prod_nm] 
                
                prod_tree_root_OT.set_plan_range_lot_counts(plan_range, plan_year_st)
                prod_tree_root_IN.set_plan_range_lot_counts(plan_range, plan_year_st)

                #root_node_outbound.set_plan_range_lot_counts(plan_range, plan_year_st)
                #root_node_inbound.set_plan_range_lot_counts(plan_range, plan_year_st)

                node_psi_dict_Ot4Dm = make_psi_space_dict(prod_tree_root_OT, {}, plan_range)
                node_psi_dict_Ot4Sp = make_psi_space_dict(prod_tree_root_OT, {}, plan_range)
                self.node_psi_dict_In4Dm = make_psi_space_dict(prod_tree_root_IN, {}, plan_range)
                self.node_psi_dict_In4Sp = make_psi_space_dict(prod_tree_root_IN, {}, plan_range)

                #node_psi_dict_Ot4Dm = make_psi_space_dict(root_node_outbound, {}, plan_range)
                #node_psi_dict_Ot4Sp = make_psi_space_dict(root_node_outbound, {}, plan_range)
                #self.node_psi_dict_In4Dm = make_psi_space_dict(root_node_inbound, {}, plan_range)
                #self.node_psi_dict_In4Sp = make_psi_space_dict(root_node_inbound, {}, plan_range)


                set_dict2tree_psi(prod_tree_root_OT, "psi4demand", node_psi_dict_Ot4Dm)
                set_dict2tree_psi(prod_tree_root_OT, "psi4supply", node_psi_dict_Ot4Sp)
                set_dict2tree_psi(prod_tree_root_IN, "psi4demand", self.node_psi_dict_In4Dm)
                set_dict2tree_psi(prod_tree_root_IN, "psi4supply", self.node_psi_dict_In4Sp)

                # **********************************
                # make&set weekly demand "Slots" on leaf_node, propagate2root
                # initial setting psi4"demand"[w][0] to psi4"supply"[w][0]
                # **********************************
                #set_df_Slots2psi4demand(self.root_node_outbound, df_weekly)
                set_df_Slots2psi4demand(prod_tree_root_OT, df_weekly)

                # convert_monthly_to_weekly() → set_df_Slots2psi4demand() の後
                #for node in self.prod_tree_dict_OT[prod_nm].values():
                for node in self.nodes_outbound.values():

                    print(f"[{node.name}] by Product demand lots per week:",
                          [len(node.psi4demand[w][0]) for w in range(1, self.plan_range + 1)])

                          #[len(node.psi4demand[w][0]) for w in range(1, min(self.plan_range + 1, 10))])


                #prod_tree_root_OT = prod_tree_dict_OT[prod_nm] 
           






        # *****************************
        # export offring_price ASIS/TOBE to csv
        # *****************************
        filename = "offering_price_ASIS_TOBE.csv"
        output_csv_path = os.path.join(self.directory, filename)

        self.export_offering_prices(output_csv_path)





        #@STOP can NOT eval before "psi" loading
        ## eval area
        #self.update_evaluation_results()


        # network area
        self.decouple_node_selected = []
        #self.decouple_node_selected = decouple_node_names

        self.view_nx_matlib4opt()
        #self.view_nx_matlib4opt_WO_capa()


        # _init_ self.product_selected = self.product_name_list[0]
        #product_name = self.product_selected 
        product_name = self.product_name_list[1]

        # PSI area
        self.root.after(1000, self.show_psi_by_product("outbound", "demand", product_name))

        #@STOP
        ## PSI area
        ##self.root.after(1000, self.show_psi("outbound", "supply"))
        #
        #self.root.after(1000, lambda: self.show_psi("outbound", "supply"))
        ## lambda: にすることで、1000ms 後に初めて show_psi() を実行する


        # ****************************
        # market potential Graph viewing
        # ****************************
        self.initialize_parameters()


        # Enable buttons after loading is complete
        self.supply_planning_button.config(state="normal")
        self.eval_buffer_stock_button.config(state="normal")
        print("Data files loaded and buttons enabled.")


        # Return focus to the main window
        self.root.focus_force()



        # ****************************
        # passing following process
        # ****************************
        pass

# **** A PART of ORIGINAL load_data_files END *****

    # ******************************
    # define planning ENGINE
    # ******************************
    def demand_planning(self):
        # Implement forward planning logic here
        print("Forward planning executed.")

        #@240903@241106
        calc_all_psi2i4demand(self.root_node_outbound)


        self.update_evaluation_results()

        #@241212 add
        self.decouple_node_selected = []
        self.view_nx_matlib()

        self.root.after(1000, self.show_psi("outbound", "demand"))
        #self.root.after(1000, self.show_psi_graph)
        #self.show_psi_graph() # this event do not live 



    def demand_planning4multi_product(self):
        # Implement forward planning logic here
        print("demand_planning4multi_product planning executed.")

        #@250730 ADD multi_product Focus on Selected Product # root is "supply_point"
        self.root_node_outbound_byprod = self.prod_tree_dict_OT[self.product_selected]
        self.root_node_inbound_byprod  = self.prod_tree_dict_IN[self.product_selected]

        #@240903@241106
        calc_all_psi2i4demand(self.root_node_outbound_byprod)





        #self.update_evaluation_results()
        self.update_evaluation_results4multi_product()

        #@241212 add
        self.decouple_node_selected = []

        #self.view_nx_matlib()
        self.view_nx_matlib4opt()

        self.root.after(1000, self.show_psi_by_product("outbound", "demand", self.product_selected))
        #show_psi_by_product(self, bound, layer, product_name)

        #self.root.after(1000, self.show_psi_graph)
        #self.show_psi_graph() # this event do not live 






    #def demand_leveling(self):
    #    pass

    #@250120 STOP with "name chaged"
    def demand_leveling(self):
        # Demand Leveling logic here
        print("Demand Leveling executed.")


        # *********************************
        # Demand LEVELing on shipping yard / with pre_production week
        # *********************************

        year_st  = 2020
        year_end = 2021

        year_st  = self.plan_year_st
        year_end = year_st + self.plan_range - 1

        pre_prod_week = self.pre_proc_LT

        # STOP
        #year_st = df_capa_year["year"].min()
        #year_end = df_capa_year["year"].max()

        # root_node_outboundのsupplyの"S"のみを平準化して生成している
        demand_leveling_on_ship(self.root_node_outbound, pre_prod_week, year_st, year_end)


        # root_node_outboundのsupplyの"PSI"を生成している
        ##@241114 KEY CODE
        self.root_node_outbound.calcS2P_4supply()  #mother plantのconfirm S=> P
        self.root_node_outbound.calcPS2I4supply()  #mother plantのPS=>I


        #@241114 KEY CODE
        # ***************************************
        # その3　都度のparent searchを実行 setPS_on_ship2node
        # ***************************************
        feedback_psi_lists(self.root_node_outbound, self.nodes_outbound)


        #feedback_psi_lists(self.root_node_outbound, node_psi_dict_Ot4Sp, self.nodes_outbound)


        # STOP
        #decouple_node_names = [] # initial PUSH with NO decouple node
        ##push_pull_on_decouple
        #push_pull_all_psi2i_decouple4supply5(
        #    self.root_node_outbound,
        #    decouple_node_names )



        #@241114 KEY CODE
        #@240903

        #calc_all_psi2i4demand(self.root_node_outbound)
        #calc_all_psi2i4supply(self.root_node_outbound)


        self.update_evaluation_results()

        # PSI計画の初期状態をバックアップ
        self.psi_backup_to_file(self.root_node_outbound, 'psi_backup.pkl')

        self.view_nx_matlib()

        self.root.after(1000, self.show_psi("outbound", "supply"))
        #self.root.after(1000, self.show_psi_graph)


    def demand_leveling4multi_prod(self):
        # Demand Leveling logic here
        print("Demand Leveling4multi_prod executed.")

        #@250730 ADD multi_product Focus on Selected Product # root is "supply_point"
        self.root_node_outbound_byprod = self.prod_tree_dict_OT[self.product_selected]
        self.root_node_inbound_byprod  = self.prod_tree_dict_IN[self.product_selected]


        # *********************************
        # Demand LEVELing on shipping yard / with pre_production week
        # *********************************

        year_st  = 2020
        year_end = 2021

        year_st  = self.plan_year_st
        year_end = year_st + self.plan_range - 1

        pre_prod_week = self.pre_proc_LT

        # STOP
        #year_st = df_capa_year["year"].min()
        #year_end = df_capa_year["year"].max()

        # root_node_outboundのsupplyの"S"のみを平準化して生成している
        demand_leveling_on_ship(self.root_node_outbound_byprod, pre_prod_week, year_st, year_end)


        # root_node_outboundのsupplyの"PSI"を生成している
        ##@241114 KEY CODE
        # node.calcXXXはPlanNodeのmethod

        self.root_node_outbound_byprod.calcS2P_4supply()  #mother plantのconfirm S=> P
        self.root_node_outbound_byprod.calcPS2I4supply()  #mother plantのPS=>I


        #@241114 KEY CODE
        # ***************************************
        # その3　都度のparent searchを実行 setPS_on_ship2node
        # ***************************************

        def make_nodes(node):
            nodes = {}

            def traverse(n):
                if n is None:
                    return
                # ノード名をキーにノード自身を格納
                nodes[n.name] = n
                # 子ノードがある場合は再帰的に探索
                for child in getattr(n, 'children', []):
                    traverse(child)

            traverse(node)
            return nodes


        nodes_outbound_byprod = make_nodes(self.root_node_outbound_byprod)


        feedback_psi_lists(self.root_node_outbound_byprod, nodes_outbound_byprod)
        #feedback_psi_lists(self.root_node_outbound_byprod, self.nodes_outbound)


        #feedback_psi_lists(self.root_node_outbound, node_psi_dict_Ot4Sp, self.nodes_outbound)


        # STOP
        #decouple_node_names = [] # initial PUSH with NO decouple node
        ##push_pull_on_decouple
        #push_pull_all_psi2i_decouple4supply5(
        #    self.root_node_outbound,
        #    decouple_node_names )



        #@241114 KEY CODE
        #@240903

        #calc_all_psi2i4demand(self.root_node_outbound)
        #calc_all_psi2i4supply(self.root_node_outbound)


        self.update_evaluation_results4multi_product()

        #@250730 STOP
        ## PSI計画の初期状態をバックアップ
        #self.psi_backup_to_file(self.root_node_outbound, 'psi_backup.pkl')

        self.view_nx_matlib4opt()

        self.root.after(1000, self.show_psi_by_product("outbound", "supply", self.product_selected))
        #self.root.after(1000, self.show_psi_graph)




    def psi_backup(self, node, status_name):
        return copy.deepcopy(node)

    def psi_restore(self, node_backup, status_name):
        return copy.deepcopy(node_backup)

    def psi_backup_to_file(self, node, filename):
        with open(filename, 'wb') as file:
            pickle.dump(node, file)

    def psi_restore_from_file(self, filename):
        with open(filename, 'rb') as file:
            node_backup = pickle.load(file)
        return node_backup


    def supply_planning4multi_product(self):

        #@250730 ADD multi_product Focus on Selected Product # root is "supply_point"
        self.root_node_outbound_byprod = self.prod_tree_dict_OT[self.product_selected]
        self.root_node_inbound_byprod  = self.prod_tree_dict_IN[self.product_selected]

        # Check if the necessary data is loaded
        #if self.root_node_outbound is None or self.nodes_outbound is None:
        if self.root_node_outbound_byprod is None:
            print("Error: PSI Plan data4multi-product is not loaded.")
            tk.messagebox.showerror("Error", "PSI Plan data4multi-product is not loaded.")
            return
    
        # Implement forward planning logic here
        print("Supply planning with Decoupling points")
    
        #@250730 STOP
        ## Restore PSI data from a backup file
        #self.root_node_outbound = self.psi_restore_from_file('psi_backup.pkl')
    
        #@250730 Temporary ADD
        self.decouple_node_selected = []

        if self.decouple_node_selected == []:
            # Search nodes_decouple_all[-2], that is "DAD" nodes
            nodes_decouple_all = make_nodes_decouple_all(self.root_node_outbound_byprod)
            print("nodes_decouple_all by_product", self.product_selected, nodes_decouple_all)
    
            # [-3] will be "DAD" node, the point of Delivery and Distribution
            decouple_node_names = nodes_decouple_all[-3] # this is "DADxxx"
            print("decouple_node_names = nodes_decouple_all[-3] ", self.product_selected, decouple_node_names)
            # sampl image of nodes_decouple_all
            # nodes_decouple_all by_product JPN_Koshihikari [['CS_JPN'], ['RT_JPN'], ['WS2JPN'], ['WS1Kosihikari'], ['DADKosihikari'], ['supply_point'], ['root']]

        else:
            decouple_node_names = self.decouple_node_selected
    


        print("push_pull_all_psi2i_decouple4supply5")
        print("self.root_node_outbound_byprod.name", self.root_node_outbound_byprod.name)
        print("decouple_node_names", decouple_node_names)

        # Perform supply planning logic
        push_pull_all_psi2i_decouple4supply5(
            self.root_node_outbound_byprod, decouple_node_names
        )
    
        # Evaluate the results
        #self.update_evaluation_results()
        self.update_evaluation_results4multi_product()
        
    
        #@250218 STOP
        ## Cash OUT/IN
        #self.cash_flow_print()
    
    
    
        # Update the network visualization
        self.decouple_node_selected = decouple_node_names
        self.view_nx_matlib4opt()
    
        # Update the PSI area
        self.root.after(1000, self.show_psi_by_product("outbound", "supply", self.product_selected))
        #self.root.after(1000, self.show_psi("outbound", "supply"))
    
    



    def supply_planning(self):
        # Check if the necessary data is loaded
        if self.root_node_outbound is None or self.nodes_outbound is None:
            print("Error: PSI Plan data is not loaded. Please load the data first.")
            tk.messagebox.showerror("Error", "PSI Plan data is NOT loaded. please File Open parameter directory first.")
            return
    
        # Implement forward planning logic here
        print("Supply planning with Decoupling points")
    
        # Restore PSI data from a backup file
        self.root_node_outbound = self.psi_restore_from_file('psi_backup.pkl')
    
        if self.decouple_node_selected == []:
            # Search nodes_decouple_all[-2], that is "DAD" nodes
            nodes_decouple_all = make_nodes_decouple_all(self.root_node_outbound    )
            print("nodes_decouple_all", nodes_decouple_all)
    
            # [-2] will be "DAD" node, the point of Delivery and Distribution
            decouple_node_names = nodes_decouple_all[-2]
        else:
            decouple_node_names = self.decouple_node_selected
    
        # Perform supply planning logic
        push_pull_all_psi2i_decouple4supply5(
            self.root_node_outbound, decouple_node_names
        )
    
        # Evaluate the results
        self.update_evaluation_results()
    
    
        #@250218 STOP
        ## Cash OUT/IN
        #self.cash_flow_print()
    
    
    
        # Update the network visualization
        self.decouple_node_selected = decouple_node_names
        self.view_nx_matlib4opt()
    
        # Update the PSI area
        self.root.after(1000, self.show_psi("outbound", "supply"))
    
    
    
    
    #def eval_buffer_stock(self):
    #    pass

    def eval_buffer_stock(self):

        # Check if the necessary data is loaded
        if self.root_node_outbound is None or self.nodes_outbound is None:
            print("Error: PSI Plan data is not loaded. Please load the data first.")
            tk.messagebox.showerror("Error", "PSI Plan data is NOT loaded. please File Open parameter directory first.")
            return

        print("eval_buffer_stock with Decoupling points")

        # This backup is in "demand leveling"
        ## PSI計画の初期状態をバックアップ
        #self.psi_backup_to_file(self.root_node_outbound, 'psi_backup.pkl')

        nodes_decouple_all = make_nodes_decouple_all(self.root_node_outbound)
        print("nodes_decouple_all", nodes_decouple_all)

        for i, decouple_node_names in enumerate(nodes_decouple_all):
            print("nodes_decouple_all", nodes_decouple_all)


            # PSI計画の状態をリストア
            self.root_node_outbound = self.psi_restore_from_file('psi_backup.pkl')

            push_pull_all_psi2i_decouple4supply5(self.root_node_outbound, decouple_node_names)
            self.update_evaluation_results()

            print("decouple_node_names", decouple_node_names)
            print("self.total_revenue", self.total_revenue)
            print("self.total_profit", self.total_profit)

            self.decouple_node_dic[i] = [self.total_revenue, self.total_profit, decouple_node_names]

            ## network area
            #self.view_nx_matlib()

            ##@241207 TEST
            #self.root.after(1000, self.show_psi("outbound", "supply"))


        self.display_decoupling_patterns()
        # PSI area => move to selected_node in window




    def update_evaluation_results4multi_product(self):

        #@250730 ADD Focus on Product Selected 
        # root_node is "supply_point"
        self.root_node_outbound_byprod = self.prod_tree_dict_OT[self.product_selected]
        self.root_node_inbound_byprod  = self.prod_tree_dict_IN[self.product_selected]

        # Evaluation on PSI
        self.total_revenue = 0
        self.total_profit  = 0
        self.profit_ratio  = 0


        # ***********************
        # This is a simple Evaluation process with "cost table"
        # ***********************


#@241120 STOP
#        self.eval_plan()
#
#    def eval_plan(self):



        # 在庫係数の計算
        # I_cost_coeff = I_total_qty_init / I_total_qty_planned
        #
        # 計画された在庫コストの算定
        # I_cost_planned = I_cost_init * I_cost_coeff
    
    
        # by node evaluation Revenue / Cost / Profit
        # "eval_xxx" = "lot_counts" X "cs_xxx" that is from cost_table
        # Inventory cost has 係数 = I_total on Demand/ I_total on Supply
    
    
        #self.total_revenue = 0
        #self.total_profit  = 0
    
        #eval_supply_chain_cost(self.root_node_outbound)
        #self.eval_supply_chain_cost(self.root_node_outbound)
    
        #eval_supply_chain_cost(self.root_node_inbound)
        #self.eval_supply_chain_cost(self.root_node_inbound)

        #@ CONTEXT グローバル変数 STOP
        ## サプライチェーン全体のコストを評価
        #eval_supply_chain_cost(self.root_node_outbound, self)
        #eval_supply_chain_cost(self.root_node_inbound, self)




        # サプライチェーンの評価を開始

        # tree.py に配置して、node に対して：
        # set_lot_counts() を呼び出し、ロット数を設定
        # EvalPlanSIP_cost() で revenue と profit を計算
        # 子ノード (children) に対して再帰的に eval_supply_chain_cost() をcall

        self.total_revenue, self.total_profit = eval_supply_chain_cost(self.root_node_outbound_byprod)



        ttl_revenue = self.total_revenue
        ttl_profit  = self.total_profit

        if ttl_revenue == 0:
            ttl_profit_ratio = 0
        else:
            ttl_profit_ratio = ttl_profit / ttl_revenue

        # 四捨五入して表示 
        total_revenue = round(ttl_revenue) 
        total_profit = round(ttl_profit) 
        profit_ratio = round(ttl_profit_ratio*100, 1) # パーセント表示

        print("total_revenue", total_revenue)
        print("total_profit", total_profit)
        print("profit_ratio", profit_ratio)


#total_revenue 343587
#total_profit 32205
#profit_ratio 9.4


        self.total_revenue_entry.config(state='normal')
        self.total_revenue_entry.delete(0, tk.END)
        self.total_revenue_entry.insert(0, f"{total_revenue:,}")
        #self.total_revenue_entry.insert(0, str(kpi_results["total_revenue"]))
        self.total_revenue_entry.config(state='readonly')


        self.total_profit_entry.config(state='normal')
        self.total_profit_entry.delete(0, tk.END)
        self.total_profit_entry.insert(0, f"{total_profit:,}")
        #self.total_profit_entry.insert(0, str(kpi_results["total_profit"]))
        self.total_profit_entry.config(state='readonly')


        self.profit_ratio_entry.config(state='normal')
        self.profit_ratio_entry.delete(0, tk.END)
        self.profit_ratio_entry.insert(0, f"{profit_ratio}%")
        self.profit_ratio_entry.config(state='readonly')

        # 画面を再描画
        self.total_revenue_entry.update_idletasks()
        self.total_profit_entry.update_idletasks()
        self.profit_ratio_entry.update_idletasks()





    def update_evaluation_results4optimize(self):


        # Evaluation on PSI
        self.total_revenue = 0
        self.total_profit  = 0
        self.profit_ratio  = 0


        # ***********************
        # This is a simple Evaluation process with "cost table"
        # ***********************


        # 在庫係数の計算
        # I_cost_coeff = I_total_qty_init / I_total_qty_planned
        #
        # 計画された在庫コストの算定
        # I_cost_planned = I_cost_init * I_cost_coeff
    
    
        # by node evaluation Revenue / Cost / Profit
        # "eval_xxx" = "lot_counts" X "cs_xxx" that is from cost_table
        # Inventory cost has 係数 = I_total on Demand/ I_total on Supply
    
    
        #self.total_revenue = 0
        #self.total_profit  = 0
    


        #@241225 memo "root_node_out_opt"のtreeにはcs_xxxxがセットされていない
        # cs_xxxxのあるnode = self.nodes_outbound[node_opt.name]に変換して参照
        #@241225 be checkek
        # ***************************
        # change ROOT HANDLE
        # ***************************
        self.eval_supply_chain_cost4opt(self.root_node_out_opt)

        print("self.root_node_out_opt.name", self.root_node_out_opt.name)

        #self.eval_supply_chain_cost(self.root_node_outbound)
        #self.eval_supply_chain_cost(self.root_node_inbound)

        ttl_revenue = self.total_revenue
        ttl_profit  = self.total_profit

        print("def update_evaluation_results4optimize")
        print("self.total_revenue", self.total_revenue)
        print("self.total_profit" , self.total_profit)


        if ttl_revenue == 0:
            ttl_profit_ratio = 0
        else:
            ttl_profit_ratio = ttl_profit / ttl_revenue

        # 四捨五入して表示 
        total_revenue = round(ttl_revenue) 
        total_profit = round(ttl_profit) 
        profit_ratio = round(ttl_profit_ratio*100, 1) # パーセント表示

        print("total_revenue", total_revenue)
        print("total_profit", total_profit)
        print("profit_ratio", profit_ratio)


#total_revenue 343587
#total_profit 32205
#profit_ratio 9.4

        print( f"total_revenue = {total_revenue:,}")
        print( f"total_profit  = {total_profit:,}")
        print( f"profit_ratio  = {profit_ratio}%")


























# ******************************
# actions
# ******************************

    def derive_weekly_capacity_from_plots(self):
        """
        node.psi4supply[w][3] に入っている P_lots の数をその週のキャパシティとみなして weekly_cap_dict を作成。
        """
        self.weekly_cap_dict = {}
    
        for node_name, node in self.nodes_outbound.items():
            self.weekly_cap_dict[node_name] = []
    
            for week_index, week_data in enumerate(node.psi4supply):
                lot_ids = week_data[3]
                if lot_ids:
                    self.weekly_cap_dict[node_name].append({
                        "week": week_index,
                        "capacity": len(lot_ids)
                    })

        print(f"[INFO] Weekly capacity derived from psi4supply for {len(self.weekly_cap_dict)} nodes")



#@250720 TODO memo
# 0a. SKU based S_month 2 week 2 psi4xxx
# 0b. SKU based evaluation
# 1. SKU based demand_planning
# 2. SKU based P_month allocation
# 3. SKU based suppy planning and PUSH/PULL planning

# *****************************
# 1.Done: load_data_files building GUI_node and PSI_node 
# 2.Done: linking GUI_node 2 sku_dict[product_name] 2 sku=PSI_node
# 3.Done: setting cost paramete
# 4.TODO: setting S_month 2 psi4demand
# 5.TODO: showing network
# *****************************


    #@250808 ADD ******************
    # export offring_price ASIS/TOBE to csv
    # *****************************
    def export_offering_prices(self, output_csv_path):
        header = ["product_name", "node_name", "offering_price_ASIS", "offering_price_TOBE"]
        rows = []

        for node_name, node in self.nodes_outbound.items():  # inboundも必要なら追加ループ
            for product_name, plan_node in node.sku_dict.items():
                rows.append([
                    product_name,
                    node_name,
                    plan_node.offering_price_ASIS,
                    plan_node.offering_price_TOBE
                ])

        with open(output_csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)

        print(f"[INFO] offering price CSV exported: {output_csv_path}")






    def regenerate_nodes(self, root_node):
        nodes = {}

        def traverse(node):
            nodes[node.name] = node
            for child in node.children:
                traverse(child)

        traverse(root_node)
        return nodes





    def Save_Objective_Value(self):

        # 供給配分の最適化 DADxxx2leaf_nodes profit_ratio CSVファイル
        self.calculate_net_profit_rates(self.root_node_outbound)


    def calculate_net_profit_rates(self, root_node_outbound, output_file="net_profit_ratio.csv"):
        # **** 対象コスト項目
        target_cost_attributes = [

            'cs_cost_total'

            #'cs_logistics_costs',
            #'cs_warehouse_cost',
            #'cs_sales_admin_cost',
            #'cs_marketing_promotion'

        ]

        results = []



        ## Cost Structure
        #self.cs_price_sales_shipped = 0
        #self.cs_cost_total = 0
        #self.cs_profit = 0
        #self.cs_marketing_promotion = 0 #<=
        #self.cs_sales_admin_cost = 0    #<=
        #self.cs_SGA_total = 0

        ##self.cs_custom_tax = 0 # stop tariff_rate

        #self.cs_tax_portion = 0             #
        #self.cs_logistics_costs = 0         #
        #self.cs_warehouse_cost = 0          #
        #self.cs_direct_materials_costs = 0  #
        #self.cs_purchase_total_cost = 0
        #self.cs_prod_indirect_labor = 0     #
        #self.cs_prod_indirect_others = 0    #
        #self.cs_direct_labor_costs = 0      #
        #self.cs_depreciation_others = 0     #
        #self.cs_manufacturing_overhead = 0


        for leaf_name in self.leaf_nodes_out:

            node = self.nodes_outbound[leaf_name]
            #node = nodes_outbound.get(leaf_name)

            print(f"Checking init node: {node.name}")

            total_cost = 0.0
            total_profit = 0.0

            # **** ルート探索：Leaf Nodeからrootまで遡る

            while node is not None:
            #while node.name != "supply_point":
                print(f"Checking node: {node.name}")
                #for attr in target_cost_attributes:
                #    if not hasattr(node, attr):
                #        print(f"⚠️ 属性 {attr} がノード {node.name} に存在しません")
                #    total_cost += getattr(node, attr, 0.0)

                total_cost   += getattr(node, 'cs_cost_total', 0.0)
                total_profit += getattr(node, 'cs_profit', 0.0)


                # 親が"supply_point"なら、これ以上遡らずに終了
                print("node.parent.name", node.parent.name)
                if node.parent and node.parent.name == "supply_point":
                    #node = None
                    break
                else:
                    node = node.parent


                ## DADxxxのノードで停止する
                #if node.parent is None or "DAD" in node.parent.name:
                #    node = None
                #else:
                #    node = node.parent

                #node = node.parent
                        
            

            #while node is not None:
            #    for attr in target_cost_attributes:
            #        total_cost += getattr(node, attr, 0.0)
            #    total_profit += getattr(node, 'cs_profit', 0.0)
            #    node = node.parent

            # **** 純利益率計算
            total_amount = total_cost + total_profit
            net_profit_rate = total_profit / total_amount if total_amount > 0 else 0.0

            results.append({

                "Source": node.name,
                #"Source": root_node_outbound.name,

                "Target": leaf_name,
                "Total_Cost": round(total_cost, 4),
                "Total_Profit": round(total_profit, 4),
                "Net_Profit_Rate": round(net_profit_rate, 4)
            })

        # **** DataFrame化とCSV出力
        df_result = pd.DataFrame(results)

        # ファイル保存ダイアログを表示して保存先ファイルパスを取得
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not save_path:
            return  # ユーザーがキャンセルした場合


        df_result.to_csv(save_path, index=False)
        #df_result.to_csv(output_file, index=False)

        print(f"✔ 純利益率データを出力しました：{save_path}")







    def show_month_data_csv(self):
        pass
    

    def outbound_psi_to_csv(self):
        # ファイル保存ダイアログを表示して保存先ファイルパスを取得
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not save_path:
            return  # ユーザーがキャンセルした場合

        # planの出力期間をcalculation
        output_period_outbound = 53 * self.root_node_outbound.plan_range

        # dataの収集
        data = []

        def collect_data(node, output_period):
            for attr in range(4):  # 0:"Sales", 1:"CarryOver", 2:"Inventory", 3:"Purchase"
                row = [node.name, attr]
                for week_no in range(output_period):
                    count = len(node.psi4supply[week_no][attr])
                    row.append(count)
                data.append(row)
            for child in node.children:
                collect_data(child, output_period)

        # root_node_outboundのtree構造を走査してdataを収集
        headers_outbound = ["node_name", "PSI_attribute"] + [f"w{i+1}" for i in range(output_period_outbound)]
        collect_data(self.root_node_outbound, output_period_outbound)

        # dataフレームを作成してCSVファイルに保存
        df_outbound = pd.DataFrame(data[:len(data)], columns=headers_outbound)  
        # STOP
        # # 複数のdataフレームを1つにaggregateする場合
        # df_combined = pd.concat([df_outbound, df_inbound])

        df_outbound.to_csv(save_path, index=False)

        # 完了メッセージを表示
        messagebox.showinfo("CSV Export", f"PSI data has been exported to {save_path}")




    def outbound_lot_by_lot_to_csv(self):
        # ファイル保存ダイアログを表示して保存先ファイルパスを取得
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not save_path:
            return  # ユーザーがキャンセルした場合

        # 計画の出力期間を計算
        #output_period_outbound = 53 * self.plan_range
        output_period_outbound = 53 * self.root_node_outbound.plan_range

        start_year = self.plan_year_st

        # ヘッダーの作成
        headers = ["tier", "node_name", "parent", "PSI_attribute", "year", "week_no", "lot_id"]

        # データの収集
        data = []

        def collect_data(node, output_period, tier_no, parent_name):
            for attr in range(4):  # 0:"Sales", 1:"CarryOver", 2:"Inventory", 3:"Purchase"
                for week_no in range(output_period):
                    year = start_year + week_no // 53
                    week = week_no % 53 + 1
                    lot_ids = node.psi4supply[week_no][attr]
                    if not lot_ids:  # 空リストの場合、空文字を追加
                        lot_ids = [""]
                    for lot_id in lot_ids:
                        data.append([tier_no, node.name, parent_name, attr, year, week, lot_id])
            for child in node.children:
                collect_data(child, output_period, tier_no + 1, node.name)

        # root_node_outboundのツリー構造を走査してデータを収集
        collect_data(self.root_node_outbound, output_period_outbound, 0, "root")

        # データフレームを作成してCSVファイルに保存
        df = pd.DataFrame(data, columns=headers)
        df.to_csv(save_path, index=False)

        # 完了メッセージを表示
        messagebox.showinfo("CSV Export", f"Lot by Lot data has been exported to {save_path}")
    
   


    def inbound_psi_to_csv(self):
        # ファイル保存ダイアログを表示して保存先ファイルパスを取得
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not save_path:
            return  # ユーザーがキャンセルした場合

        # planの出力期間をcalculation
        output_period_inbound = 53 * self.root_node_inbound.plan_range

        # dataの収集
        data = []

        def collect_data(node, output_period):
            for attr in range(4):  # 0:"Sales", 1:"CarryOver", 2:"Inventory", 3:"Purchase"
                row = [node.name, attr]
                for week_no in range(output_period):
                    count = len(node.psi4supply[week_no][attr])
                    row.append(count)
                data.append(row)
            for child in node.children:
                collect_data(child, output_period)

        # root_node_inboundのtree構造を走査してdataを収集
        headers_inbound = ["node_name", "PSI_attribute"] + [f"w{i+1}" for i in range(output_period_inbound)]
        collect_data(self.root_node_inbound, output_period_inbound)


        # dataフレームを作成してCSVファイルに保存
        df_inbound = pd.DataFrame(data[:len(data)], columns=headers_inbound) 

        df_inbound.to_csv(save_path, index=False)

        # 完了メッセージを表示
        messagebox.showinfo("CSV Export", f"PSI data has been exported to {save_path}")





    def inbound_lot_by_lot_to_csv(self):
        # ファイル保存ダイアログを表示して保存先ファイルパスを取得
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not save_path:
            return  # ユーザーがキャンセルした場合

        # planの出力期間をcalculation
        output_period_inbound = 53 * self.root_node_inbound.plan_range
        start_year = self.plan_year_st

        # ヘッダーの作成
        headers = ["tier", "node_name", "parent", "PSI_attribute", "year", "week_no", "lot_id"]

        # dataの収集
        data = []

        def collect_data(node, output_period, tier_no, parent_name):
            for attr in range(4):  # 0:"Sales", 1:"CarryOver", 2:"Inventory", 3:"Purchase"
                for week_no in range(output_period):
                    year = start_year + week_no // 53
                    week = week_no % 53 + 1
                    lot_ids = node.psi4supply[week_no][attr]
                    if not lot_ids:  # 空リストの場合、空文字を追加
                        lot_ids = [""]
                    for lot_id in lot_ids:
                        data.append([tier_no, node.name, parent_name, attr, year, week, lot_id])
            for child in node.children:
                collect_data(child, output_period, tier_no + 1, node.name)

        # root_node_outboundのtree構造を走査してdataを収集
        collect_data(self.root_node_inbound, output_period_inbound, 0, "root")

        # dataフレームを作成してCSVファイルに保存
        df = pd.DataFrame(data, columns=headers)
        df.to_csv(save_path, index=False)

        # 完了メッセージを表示
        messagebox.showinfo("CSV Export", f"Lot by Lot data has been exported to {save_path}")








    def lot_cost_structure_to_csv(self):
        # "PSI for Excel"のprocess内容を定義

        # ファイル保存ダイアログを表示して保存先ファイルパスを取得
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not save_path:
            return  # ユーザーがキャンセルした場合

        self.export_cost_structure_to_csv(self.root_node_outbound, self.root_node_inbound, save_path)


        # 完了メッセージを表示
        messagebox.showinfo("CSV Export", f"export_cost_structure_to_csv data has been exported to {save_path}")






    def outbound_rev_prof_csv(self):
        # "PSI for Excel"のprocess内容を定義
        pass



    def supplychain_performance_to_csv(self):
        # ファイル保存ダイアログを表示して保存先ファイルパスを取得
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not save_path:
            return  # ユーザーがキャンセルした場合

        self.export_performance_to_csv(self.root_node_outbound, self.root_node_inbound, save_path)

        # 完了メッセージを表示
        messagebox.showinfo("CSV Export", f"Business performance data has been exported to {save_path}")


    def export_performance_to_csv(self, root_node_outbound, root_node_inbound, file_path):
        attributes = [


# evaluated cost = Cost Structure X lot_counts


            #@250322 STOP
            #"cs_custom_tax",             # political TAX parameter
            # "cs_WH_cost_coefficiet",    # operational cost parameter


            # "purchase_total_cost" is followings
            "cs_direct_materials_costs", # material
            "cs_tax_portion",            # portion calculated by TAX xx%
            "cs_logistics_costs",        # inbound logistic cost

            # plant operations are followings
            "cs_warehouse_cost",

            # eval_cs_manufacturing_overhead
            "cs_prod_indirect_labor",    # man indirect
            "cs_prod_indirect_others",   # expense
            "cs_direct_labor_costs",     # man direct
            "cs_depreciation_others",    # machine

            # Sales side operations
            "cs_marketing_promotion",
            "cs_sales_admin_cost",

            # cash generated
            "cs_profit",

            # sub total cost item
            "cs_purchase_total_cost",    # material + TAX + logi cost
            "cs_manufacturing_overhead",
            "cs_SGA_total",  # marketing_promotion + sales_admin_cost

            "cs_cost_total",
            "cs_price_sales_shipped", # revenue
        ]


        def dump_node_amt_all_in(node, node_amt_all):
            for child in node.children:
                dump_node_amt_all_in(child, node_amt_all)
            amt_list = {attr: getattr(node, attr) for attr in attributes}
            if node.name == "JPN":
                node_amt_all["JPN_IN"] = amt_list
            else:
                node_amt_all[node.name] = amt_list
            return node_amt_all

        def dump_node_amt_all_out(node, node_amt_all):
            amt_list = {attr: getattr(node, attr) for attr in attributes}
            if node.name == "JPN":
                node_amt_all["JPN_OUT"] = amt_list
            else:
                node_amt_all[node.name] = amt_list
            for child in node.children:
                dump_node_amt_all_out(child, node_amt_all)
            return node_amt_all

        node_amt_sum_in = dump_node_amt_all_in(root_node_inbound, {})
        node_amt_sum_out = dump_node_amt_all_out(root_node_outbound, {})
        node_amt_sum_in_out = {**node_amt_sum_in, **node_amt_sum_out}

        # 横持ちでdataフレームを作成
        data = []
        for node_name, performance in node_amt_sum_in_out.items():
            row = [node_name] + [performance[attr] for attr in attributes]
            data.append(row)

        df = pd.DataFrame(data, columns=["node_name"] + attributes)

        # CSVファイルにエクスポート
        df.to_csv(file_path, index=False)
        print(f"Business performance data exported to {file_path}")


#@250218
# ******************



    def print_cost_sku(self):
        sku = self.select_node.sku_dict[self.product_selected]
        print("select_node plan_node =", self.select_node.name, sku.name)

        print("sku.cs_profit                ", sku.cs_profit                )
        print("sku.cs_SGA_total             ", sku.cs_SGA_total             )
        print("sku.cs_tax_portion           ", sku.cs_tax_portion           )
        print("sku.cs_logistics_costs       ", sku.cs_logistics_costs       )
        print("sku.cs_warehouse_cost        ", sku.cs_warehouse_cost        )
        print("sku.cs_direct_materials_costs", sku.cs_direct_materials_costs)


    def print_cost_node_cs(self):
        plan_node = self.select_node.sku_dict[self.product_selected]
        print("select_node plan_node =", self.select_node.name, plan_node.name)

        print("plan_node.cs_profit                ", plan_node.cs_profit                )
        print("plan_node.cs_SGA_total             ", plan_node.cs_SGA_total             )
        print("plan_node.cs_tax_portion           ", plan_node.cs_tax_portion           )
        print("plan_node.cs_logistics_costs       ", plan_node.cs_logistics_costs       )
        print("plan_node.cs_warehouse_cost        ", plan_node.cs_warehouse_cost        )
        print("plan_node.cs_direct_materials_costs", plan_node.cs_direct_materials_costs)

            
    def print_cost_node_eval_cs(self): 
        plan_node = self.select_node.sku_dict[self.product_selected]
        print("select_node plan_node =", self.select_node.name, plan_node.name)

        print("plan_node.eval_cs_profit                ", plan_node.eval_cs_profit                )
        print("plan_node.eval_cs_SGA_total             ", plan_node.eval_cs_SGA_total             )
        print("plan_node.eval_cs_tax_portion           ", plan_node.eval_cs_tax_portion           )
        print("plan_node.eval_cs_logistics_costs       ", plan_node.eval_cs_logistics_costs       )
        print("plan_node.eval_cs_warehouse_cost        ", plan_node.eval_cs_warehouse_cost        )
        print("plan_node.eval_cs_direct_materials_costs", plan_node.eval_cs_direct_materials_costs)

 






    def Inbound_DmBw(self):


        connect_outbound2inbound(self.root_node_outbound, self.root_node_inbound)
    
    
        calc_all_psiS2P2childS_preorder(self.root_node_inbound)


        #@250120 eval and view
        self.update_evaluation_results()

        #@241212 add
        self.decouple_node_selected = []
        self.view_nx_matlib()

        self.root.after(1000, self.show_psi("inbound", "demand"))
        #self.root.after(1000, self.show_psi("outbound", "demand"))




        pass



    def Inbound_SpFw(self):


        #@240907 demand2supply
        # copy demand layer to supply layer # メモリーを消費するので要修正
    
        self.node_psi_dict_In4Sp = psi_dict_copy(
                                 self.node_psi_dict_In4Dm, # in demand  .copy()
                                 self.node_psi_dict_In4Sp   # in supply
                              )
    
        # In4Dmの辞書をself.psi4supply = node_psi_dict_In4Dm[self.name]でre_connect
    
        def re_connect_suppy_dict2psi(node, node_psi_dict):
    
            node.psi4supply = node_psi_dict[node.name]
    
            for child in node.children:
    
                re_connect_suppy_dict2psi(child, node_psi_dict)
    
    
        re_connect_suppy_dict2psi(self.root_node_inbound, self.node_psi_dict_In4Sp)
    
        calc_all_psi2i4supply_post(self.root_node_inbound)
    
    
    
        #@250120 eval and view
        self.update_evaluation_results()

        #@241212 add
        self.decouple_node_selected = []
        self.view_nx_matlib()

        self.root.after(1000, self.show_psi("inbound", "supply"))
        #self.root.after(1000, self.show_psi("outbound", "demand"))





    
        pass



# **** 19 call_backs END*****



# **** Start of SUB_MODULE for Optimization ****

    def _load_tree_structure(self, load_directory):

        with open(f"{load_directory}/root_node_outbound.pkl", 'rb') as f:
            self.root_node_outbound = pickle.load(f)
            print(f"root_node_outbound loaded: {self.root_node_outbound}")

        with open(f"{load_directory}/root_node_inbound.pkl", 'rb') as f:
            self.root_node_inbound = pickle.load(f)
            print(f"root_node_inbound loaded: {self.root_node_inbound}")


        if os.path.exists(f"{load_directory}/root_node_out_opt.pkl"):
            with open(f"{load_directory}/root_node_out_opt.pkl", 'rb') as f:
                self.root_node_out_opt = pickle.load(f)
                print(f"root_node_out_opt loaded: {self.root_node_out_opt}")
        else:
            self.flowDict_opt = {}  # NO optimize
            pass





    # オリジナルノードからコピーする処理
    def copy_node(self, node_name):
        original_node = self.nodes_outbound[node_name]  #オリジナルノードを取得
        copied_node = copy.deepcopy(original_node)  # deepcopyを使ってコピー
        return copied_node





    def plan_through_engines4opt(self):

    #@RENAME
    # nodes_out_opt     : nodes_out_opt    
    # root_node_out_opt : root_node_out_opt


        print("planning with OPTIMIZED S")


        # Demand planning
        calc_all_psi2i4demand(self.root_node_out_opt)


        # Demand LEVELing on shipping yard / with pre_production week
        year_st = self.plan_year_st
        year_end = year_st + self.plan_range - 1
        pre_prod_week = self.pre_proc_LT
        demand_leveling_on_ship(self.root_node_out_opt, pre_prod_week, year_st, year_end)
        # root_node_out_optのsupplyの"PSI"を生成している
        self.root_node_out_opt.calcS2P_4supply()  #mother plantのconfirm S=> P
        self.root_node_out_opt.calcPS2I4supply()  #mother plantのPS=>I

        # ***************************************
        # その3　都度のparent searchを実行 setPS_on_ship2node
        # ***************************************
        feedback_psi_lists(self.root_node_out_opt, self.nodes_out_opt)



        #@241208 STOP
        ## Supply planning
        #print("Supply planning with Decoupling points")
        #nodes_decouple_all = make_nodes_decouple_all(self.root_node_out_opt)
        #print("nodes_decouple_all", nodes_decouple_all)
        #
        #for i, decouple_node_names in enumerate(nodes_decouple_all):
        #    decouple_flag = "OFF"
        #    if i == 0:

        decouple_node_names = self.decouple_node_selected

        push_pull_all_psi2i_decouple4supply5(self.root_node_out_opt, decouple_node_names)






# **** End of Optimization ****





    def load_tree_structure(self):
        try:
            file_path = filedialog.askopenfilename(title="Select Tree Structure File")
            if not file_path:
                return
            # Placeholder for loading tree structure
            self.tree_structure = nx.DiGraph()
            self.tree_structure.add_edge("Root", "Child1")
            self.tree_structure.add_edge("Root", "Child2")
            messagebox.showinfo("Success", "Tree structure loaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load tree structure: {e}")








# ******************************************
# clear_s_values
# ******************************************
#
#複数年のデータに対応するために、node_name と year をキーにして各ノードのデータを処理。
#
#説明
#leaf_nodeの特定方法の修正：
#
#flow_dict 内で各ノードに sales_office が含まれているかどうかで leaf_nodes を特定します。
#
#rule-1, rule-2, rule-3 の適用：
#
#rule-1: flow_dict に存在しないノードの月次Sの値を0に設定。
#
#rule-2: flow_dict に存在し、sales_office に繋がるノードの値が0である場合、月次S#の値を0に設定。
#
#rule-3: flow_dict に存在し、sales_office に繋がるノードの値が0以外である場合、月次Sの値をプロポーションに応じて分配。
#
#proportionsの計算と値の丸め：
#
#各月のproportionを計算し、それを使って丸めた値を求めます。
#
#rounded_values に丸めた値を格納し、合計が期待する供給量と一致しない場合は、
#最大の値を持つ月で調整します。
#
#年間total_supplyが0の場合の処理：
#年間total_supplyが0の場合は、月次Sの値をすべて0に設定します。


    def clear_s_values(self, flow_dict, input_csv, output_csv):
        # 1. 入力ファイルS_month_data.csvをデータフレームに読み込み
        df = pd.read_csv(input_csv)

        # leaf_nodeを特定
        leaf_nodes = [node for node, connections in flow_dict.items() if 'sales_office' in connections]

        # 2. rule-1, rule-2, rule-3を適用してデータを修正する
        for index, row in df.iterrows():
            node_name = row['node_name']
            year = row['year']
            
            if node_name in flow_dict:
                # ノードがflow_dictに存在する場合
                if node_name in leaf_nodes:
                    # rule-2: ノードの値が0の場合、月次Sの値をすべて0に設定
                    if flow_dict[node_name]['sales_office'] == 0:
                        df.loc[(df['node_name'] == node_name) & (df['year'] == year),
                               ['m1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7', 'm8', 'm9', 'm10', 'm11', 'm12']] = 0
                    else:
                        # rule-3: ノードの値が0以外の場合、月次Sのproportionに応じて分配
                        total_supply = sum(df.loc[(df['node_name'] == node_name) & (df['year'] == year), 
                                                  ['m1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7', 'm8', 'm9', 'm10', 'm11', 'm12']].values.flatten())
                        if total_supply != 0:
                            proportions = df.loc[(df['node_name'] == node_name) & (df['year'] == year), 
                                                 ['m1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7', 'm8', 'm9', 'm10', 'm11', 'm12']].values.flatten() / total_supply
                            rounded_values = [round(proportion * flow_dict[node_name]['sales_office']) for proportion in proportions]
                            difference = flow_dict[node_name]['sales_office'] - sum(rounded_values)
                            if difference != 0:
                                max_index = rounded_values.index(max(rounded_values))
                                rounded_values[max_index] += difference
                            df.loc[(df['node_name'] == node_name) & (df['year'] == year),
                                   ['m1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7', 'm8', 'm9', 'm10', 'm11', 'm12']] = rounded_values
                        else:
                            # 供給量がゼロの場合、元データを保持（エラーチェック）
                            df.loc[(df['node_name'] == node_name) & (df['year'] == year), 
                                   ['m1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7', 'm8', 'm9', 'm10', 'm11', 'm12']] = [0] * 12
            else:
                # rule-1: ノードがflow_dictに存在しない場合、月次Sの値をすべて0に設定
                df.loc[index, ['m1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7', 'm8', 'm9', 'm10', 'm11', 'm12']] = 0

        # 3. 結果を"S_month_data_optimized.csv"として保存する
        df.to_csv(output_csv, index=False)
        print(f"Optimized data saved to {output_csv}")







    def eval_supply_chain_cost4opt(self, node_opt):
    
        # change from "out_opt" to "outbound"
        node = self.nodes_outbound[node_opt.name]

        # *********************
        # counting Purchase Order
        # *********************
        # psi_listのPOは、psi_list[w][3]の中のlot_idのロット数=リスト長

        # lot_counts is "out_opt"side
        node_opt.set_lot_counts()

        #@ STOP
        #node.set_lot_counts()
    
        # output:
        #    self.lot_counts_all = sum(self.lot_counts)

        # change lot_counts from "out_opt"side to "outbound"side
        node.lot_counts_all = node_opt.lot_counts_all
    
        # *********************
        # EvalPlanSIP()の中でnode instanceに以下をセットする
        # self.profit, self.revenue, self.profit_ratio
        # *********************
    
        # by weekの計画状態xxx[w]の変化を評価して、self.eval_xxxにセット
        total_revenue, total_profit = node.EvalPlanSIP_cost()

    
        #@241225 ADD
        node.total_revenue     = total_revenue    
        node.total_profit      = total_profit     
                                 
        node_opt.total_revenue = total_revenue
        node_opt.total_profit  = total_profit 
                                 
        self.total_revenue += total_revenue
        self.total_profit  += total_profit
    
    
        #@241118 "eval_" is 1st def /  "eval_cs_" is 2nd def
        # print(
        #    "Eval node profit revenue profit_ratio",
        #    node.name,
        #    node.eval_profit,
        #    node.eval_revenue,
        #    node.eval_profit_ratio,
        # )
    
        for child in node.children:
    
            self.eval_supply_chain_cost4opt(child)





#@250218 STOP
#    def cash_flow_print(self):
#
#        #self.total_revenue, self.total_profit = eval_supply_chain_cost(self.root_node_outbound)
#
#        self.total_revenue, self.total_profit = eval_supply_chain_cash(self.root_node_outbound)




    def update_evaluation_results(self):

        # Evaluation on PSI
        self.total_revenue = 0
        self.total_profit  = 0
        self.profit_ratio  = 0


        # ***********************
        # This is a simple Evaluation process with "cost table"
        # ***********************


#@241120 STOP
#        self.eval_plan()
#
#    def eval_plan(self):



        # 在庫係数の計算
        # I_cost_coeff = I_total_qty_init / I_total_qty_planned
        #
        # 計画された在庫コストの算定
        # I_cost_planned = I_cost_init * I_cost_coeff
    
    
        # by node evaluation Revenue / Cost / Profit
        # "eval_xxx" = "lot_counts" X "cs_xxx" that is from cost_table
        # Inventory cost has 係数 = I_total on Demand/ I_total on Supply
    
    
        #self.total_revenue = 0
        #self.total_profit  = 0
    
        #eval_supply_chain_cost(self.root_node_outbound)
        #self.eval_supply_chain_cost(self.root_node_outbound)
    
        #eval_supply_chain_cost(self.root_node_inbound)
        #self.eval_supply_chain_cost(self.root_node_inbound)

        #@ CONTEXT グローバル変数 STOP
        ## サプライチェーン全体のコストを評価
        #eval_supply_chain_cost(self.root_node_outbound, self)
        #eval_supply_chain_cost(self.root_node_inbound, self)




        # サプライチェーンの評価を開始

        # tree.py に配置して、node に対して：
        # set_lot_counts() を呼び出し、ロット数を設定
        # EvalPlanSIP_cost() で revenue と profit を計算
        # 子ノード (children) に対して再帰的に eval_supply_chain_cost() をcall

        self.total_revenue, self.total_profit = eval_supply_chain_cost(self.root_node_outbound)



        ttl_revenue = self.total_revenue
        ttl_profit  = self.total_profit

        if ttl_revenue == 0:
            ttl_profit_ratio = 0
        else:
            ttl_profit_ratio = ttl_profit / ttl_revenue

        # 四捨五入して表示 
        total_revenue = round(ttl_revenue) 
        total_profit = round(ttl_profit) 
        profit_ratio = round(ttl_profit_ratio*100, 1) # パーセント表示

        print("total_revenue", total_revenue)
        print("total_profit", total_profit)
        print("profit_ratio", profit_ratio)


#total_revenue 343587
#total_profit 32205
#profit_ratio 9.4

