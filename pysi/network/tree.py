#network_tree250114.py

#@250713 for def load_sku_cost_master(...)
import pandas as pd


# network/tree.py
from typing import List, Dict, Optional

from collections import defaultdict

from pysi.utils.file_io import read_tree_file
#from some_module import Node  # Nodeクラスを適切な場所からインポート

#from pysi.plan.demand_processing import *
#from plan.demand_processing import shiftS2P_LV

from pysi.plan.operations import *
#from pysi.plan.operations import calcS2P, set_S2psi, get_set_childrenP2S2psi

from pysi.network.node_base import Node, SKU

from pysi.network.tree import *





    
    
    
# ****************************
# after demand leveling / planning outbound supply
# ****************************
def shiftS2P_LV_replace(psiS, shift_week, lv_week):  # LV:long vacations

    # ss = safety_stock_week
    sw = shift_week

    plan_len = len(psiS) - 1  # -1 for week list position

    for w in range(plan_len):  # foreward planningでsupplyのp [w][3]を初期化

        # psiS[w][0] = [] # S active

        psiS[w][1] = []  # CO
        psiS[w][2] = []  # I
        psiS[w][3] = []  # P

    for w in range(plan_len, sw, -1):  # backward planningでsupplyを降順でシフト

        # my_list = [1, 2, 3, 4, 5]
        # for i in range(2, len(my_list)):
        #    my_list[i] = my_list[i-1] + my_list[i-2]

        # 0:S
        # 1:CO
        # 2:I
        # 3:P

        eta_plan = w - sw  # sw:shift week ( including safty stock )

        eta_shift = check_lv_week_bw(lv_week, eta_plan)  # ETA:Eatimate Time Arrival

        # リスト追加 extend
        # 安全在庫とカレンダ制約を考慮した着荷予定週Pに、w週Sからoffsetする
        psiS[eta_shift][3].extend(psiS[w][0])  # P made by shifting S with

    return psiS






# ****************************
# extract_subtree_by_product
# ****************************
def extract_subtree_by_product(root_node: Node, product_name: str) -> Optional[Node]:
#def extract_subtree_by_product(root_node: Node, product_name: str, new_nodes: dictc) -> Optional[Node]:

    """
    与えられたroot_nodeから、product_nameに関連するノードのみを含む部分ツリーを再構成して返す。
    対象ノードが存在しない場合はNoneを返す。
    """

    # ベース条件：このノードまたは子孫にproduct_nameが存在しなければ除外
    def contains_product(node: Node) -> bool:
        if product_name in node.sku_dict:
            return True
        return any(contains_product(child) for child in node.children)

    if not contains_product(root_node):
        return None

    # 新しいノードを作成（Node(name)のみコピー、他の情報は再利用せず）
    print("root_node.name", root_node.name)

    new_node = Node(root_node.name)    #### new_node
    #new_nodes[root_node.name] = new_node

    print("new_node.name", new_node.name)

    # sku_dictの該当SKUだけコピー（deep copyも可能）
    if product_name in root_node.sku_dict:
        new_node.sku_dict[product_name] = root_node.sku_dict[product_name]

    # 子ノード再帰
    for child in root_node.children:
        filtered_child = extract_subtree_by_product(child, product_name )
        #filtered_child = extract_subtree_by_product(child, product_name, new_nodes )
        
        #@250714ADD 250715STOP 250716GO
        # 子から見た親nodeをセット

        if filtered_child is not None:
            filtered_child.parent = new_node  # 修正点1
            new_node.add_child(filtered_child)

        #filtered_child.parent = root_node
        #
        #print("filtered_child.name", filtered_child.name)
        #
        #if filtered_child is not None:
        #    new_node.add_child(filtered_child)
        #    #new_nodes[filtered_child.name] = filtered_child


    return new_node
    #return new_node, new_nodes

















# ****************************
# PSI planning demand
# ****************************
def calc_all_psi2i4demand(node):

    node.calcPS2I4demand()

    for child in node.children:

        calc_all_psi2i4demand(child)




# ****************************
# connect_out2in
# ****************************




def connect_out2in_dict_copy(node_psi_dict_Ot4Dm, node_psi_dict_In4Dm):

    node_psi_dict_In4Dm = node_psi_dict_Ot4Dm.copy()
    
    return node_psi_dict_In4Dm




def psi_dict_copy(from_psi_dict, to_psi_dict):

    to_psi_dict = from_psi_dict.copy()
    
    return to_psi_dict






def connect_out2in_psi_copy(root_node_outbound, root_node_inbound):

    # ***************************************
    # setting root node OUTBOUND to INBOUND
    # ***************************************

    plan_range = root_node_outbound.plan_range

    root_node_inbound.psi4demand = root_node_outbound.psi4supply.copy()




def connect_outbound2inbound(root_node_outbound, root_node_inbound):

    # ***************************************
    # setting root node OUTBOUND to INBOUND
    # ***************************************

    plan_range = root_node_outbound.plan_range

    for w in range(53 * plan_range):

        root_node_inbound.psi4demand[w][0] = root_node_outbound.psi4supply[w][0].copy()
        root_node_inbound.psi4demand[w][1] = root_node_outbound.psi4supply[w][1].copy()
        root_node_inbound.psi4demand[w][2] = root_node_outbound.psi4supply[w][2].copy()
        root_node_inbound.psi4demand[w][3] = root_node_outbound.psi4supply[w][3].copy()

        root_node_inbound.psi4supply[w][0] = root_node_outbound.psi4supply[w][0].copy()
        root_node_inbound.psi4supply[w][1] = root_node_outbound.psi4supply[w][1].copy()
        root_node_inbound.psi4supply[w][2] = root_node_outbound.psi4supply[w][2].copy()
        root_node_inbound.psi4supply[w][3] = root_node_outbound.psi4supply[w][3].copy()





# ************************************
# checking constraint to inactive week , that is "Long Vacation"
# ************************************
def check_lv_week_bw(const_lst, check_week):

    num = check_week

    if const_lst == []:

        pass

    else:

        while num in const_lst:

            num -= 1

    return num




def shift_P2childS_LV(node, child, safety_stock_week, lv_week):

    # psiP = node.psi4demand

    ss = safety_stock_week

    plan_len = len(node.psi4demand) - 1  # -1 for week list position
    #plan_len = len(psiP) - 1  # -1 for week list position

    for w in range( (plan_len - 1), 0, -1):  # forward planningで確定Pを確定Sにシフト

        # my_list = [1, 2, 3, 4, 5]
        # for i in range(2, len(my_list)):
        #    my_list[i] = my_list[i-1] + my_list[i-2]

        # 0:S
        # 1:CO
        # 2:I
        # 3:P

        etd_plan = w - ss  # ss:safty stock

        etd_shift = check_lv_week_bw(lv_week,etd_plan) #BW ETD:Eatimate TimeDep
        # リスト追加 extend
        # 安全在庫とカレンダ制約を考慮した着荷予定週Pに、w週Sからoffsetする

        # "child S" position made by shifting P with

        #child.psi4supply[etd_shift][0] = node.psi4supply[w][3]

        print("[etd_shift][0] [w][3]  ",child.name,etd_shift, "  ",node.name,w)

        if etd_shift > 0:

            child.psi4demand[etd_shift][0] = node.psi4demand[w][3]

        else:

            pass

        #psi[etd_shift][0] = psiP[w][3]  # S made by shifting P with

    #return psiP
    #
    #return psi



def check_lv_week_fw(const_lst, check_week):

    num = check_week

    if const_lst == []:

        pass

    else:

        while num in const_lst:

            num += 1

    return num




# backward P2S ETD_shifting 
def shiftP2S_LV(psiP, safety_stock_week, lv_week):  # LV:long vacations

    ss = safety_stock_week

    plan_len = len(psiP) - 1  # -1 for week list position

    for w in range(plan_len - 1):  # forward planningで確定Pを確定Sにシフト

        # my_list = [1, 2, 3, 4, 5]
        # for i in range(2, len(my_list)):
        #    my_list[i] = my_list[i-1] + my_list[i-2]

        # 0:S
        # 1:CO
        # 2:I
        # 3:P

        etd_plan = w + ss  # ss:safty stock

        etd_shift = check_lv_week_fw(lv_week, etd_plan)  # ETD:Eatimate TimeDep
        # リスト追加 extend
        # 安全在庫とカレンダ制約を考慮した着荷予定週Pに、w週Sからoffsetする

        psiP[etd_shift][0] = psiP[w][3]  # S made by shifting P with

    return psiP


# P2S
def calc_all_psiS2P2childS_preorder(node):

    # inbound supply backward plan with pre_ordering
    #node.calcS2P_4supply()    # "self.psi4supply"

    # nodeの中で、S2P
    node.calcS2P()    # "self.psi4demand" # backward planning

    if node.children == []:

        pass

    else:

        for child in node.children:

    #def calc_all_P2S(node)
            # **************************
            # Safety Stock as LT shift
            # **************************
            safety_stock_week = child.leadtime

            # **************************
            # long vacation weeks
            # **************************
            lv_week = child.long_vacation_weeks

            # P to S の計算処理
            # backward P2S ETD_shifting 
            #self.psi4supply = shiftP2S_LV(node.psi4supply, safety_stock_week, lv_week)

            # node, childのpsi4supplyを直接update
            shift_P2childS_LV(node, child, safety_stock_week, lv_week)

            #child.psi4supply = shift_P2childS_LV(node, child, safety_stock_week, lv_week)


    for child in node.children:

        calc_all_psiS2P2childS_preorder(child)





def calc_all_psi2i4supply_post(node):



    for child in node.children:

        calc_all_psi2i4supply_post(child)

    node.calcPS2I4supply()




# ****************************
# Inbound Demand Backward Plan
# ****************************



#  class NodeのメソッドcalcS2Pと同じだが、node_psiの辞書を更新してreturn
def calc_bwd_inbound_si2p(node, node_psi_dict_In4Dm):

    # **************************
    # Safety Stock as LT shift
    # **************************
    # leadtimeとsafety_stock_weekは、ここでは同じ

    #@240906 SS+LTでoffset

    safety_stock_week = int(round(node.SS_days / 7))

    #safety_stock_week += node.leadtime

    # **************************
    # long vacation weeks
    # **************************
    lv_week = node.long_vacation_weeks

    # S to P の計算処理  # dictに入れればself.psi4supplyから接続して見える
    node_psi_dict_In4Dm[node.name] = shiftS2P_LV(
        node.psi4demand, safety_stock_week, lv_week
    )

    return node_psi_dict_In4Dm


def calc_bwd_inbound_all_si2p(node, node_psi_dict_In4Dm):

    plan_range = node.plan_range

    # ********************************
    # inboundは、親nodeのSをそのままPに、shift S2Pして、node_spi_dictを更新
    # ********************************
    #    S2P # dictにlistセット
    node_psi_dict_In4Dm = calc_bwd_inbound_si2p(node, node_psi_dict_In4Dm)

    # *********************************
    # 子nodeがあればP2_child.S
    # *********************************

    if node.children == []:

        pass

    else:

        # inboundの場合には、dict=[]でセット済　代入する[]になる
        # 辞書のgetメソッドでキーnameから値listを取得。
        # キーが存在しない場合はNone
        # self.psi4demand = node_psi_dict_In4Dm.get(self.name)

        for child in node.children:

            for w in range(53 * plan_range):

                # move_lot P2S
                child.psi4demand[w][0] = node.psi4demand[w][3].copy()

    for child in node.children:

        calc_bwd_inbound_all_si2p(child, node_psi_dict_In4Dm)

    # stop 返さなくても、self.psi4demand[w][3]でPを参照できる。
    return node_psi_dict_In4Dm















# ****************************
# tree positioing
# ****************************
def set_positions_recursive(node, width_tracker):
    for child in node.children:
        child.depth = node.depth + 1
        child.width = width_tracker[child.depth]
        width_tracker[child.depth] += 1
        set_positions_recursive(child, width_tracker)

def adjust_positions(node):
    if not node.children:
        return node.width

    children_y_min = min(adjust_positions(child) for child in node.children)
    children_y_max = max(adjust_positions(child) for child in node.children)
    node.width = (children_y_min + children_y_max) / 2

    for i, child in enumerate(node.children):
        child.width += i * 0.1

    return node.width

def set_positions(root):
    width_tracker = [0] * 100
    set_positions_recursive(root, width_tracker)
    adjust_positions(root)


#@250712 ADD
def load_sku_cost_master(file_path: str, node_dict: dict[str, Node]):
    df = pd.read_csv(file_path)

    for _, row in df.iterrows():
        node_name = row["node_name"]
        product_name = row["product_name"]

        if node_name not in node_dict:
            print(f"[Warn] Node {node_name} not found in node_dict")
            continue

        node = node_dict[node_name]

        sku = node.sku_dict.get(product_name)

        if sku is None:
            sku = node.add_sku(product_name)

        # 一括コストセット
        sku.set_cost_attr(
            price_sales_shipped=float(row["price_sales_shipped"]),
            cost_total=float(row["cost_total"]),
            profit=float(row["profit"]),
            marketing_promotion=float(row.get("marketing_promotion", 0)),
            sales_admin_cost=float(row.get("sales_admin_cost", 0)),
            logistics_costs=float(row.get("logistics_costs", 0)),
            warehouse_cost=float(row.get("warehouse_cost", 0)),
            direct_materials_costs=float(row["direct_materials_costs"]),
            prod_indirect_labor=float(row.get("prod_indirect_labor", 0)),
            prod_indirect_others=float(row.get("prod_indirect_others", 0)),
            direct_labor_costs=float(row.get("direct_labor_costs", 0)),
            depreciation_others=float(row.get("depreciation_others", 0)),
        )

        sku.normalize_cost()



#@250712 STOP
#def set_node_costs(cost_table, nodes):
#    """
#    Set cost attributes for nodes based on the given cost table.
#
#    Parameters:
#        cost_table (pd.DataFrame): DataFrame containing cost data.
#        nodes (dict): Dictionary of node instances.
#
#    Returns:
#        None
#    """
#    df_transposed = cost_table.transpose()
#
#    rows = df_transposed.iterrows()
#    next(rows)  # Skip the header row
#
#    for index, row in rows:
#        node_name = index
#        try:
#            node = nodes[node_name]
#            node.set_cost_attr(*row)
#
#            node.normalize_cost() # add Custom_Tax and normalize
#
#            node.print_cost_attr()
#        except KeyError:
#            print(f"Warning: {node_name} not found in nodes. Continuing with next item.")






def set_parent_all(node):
    # preordering

    if node.children == []:
        pass
    else:
        node.set_parent()  # この中で子nodeを見て親を教える。
        # def set_parent(self)

    for child in node.children:

        set_parent_all(child)




def print_parent_all(node):
    # preordering

    if node.children == []:
        pass
    else:
        print("node.parent and children", node.name, node.children)

    for child in node.children:

        print("child and parent", child.name, node.name)

        print_parent_all(child)





def build_tree_from_dict(tree_dict: Dict[str, List[str]]) -> Node:
    """
    Build a tree structure from a dictionary.

    Parameters:
        tree_dict (Dict[str, List[str]]): A dictionary where keys are parent node names
                                         and values are lists of child node names.

    Returns:
        Node: The root node of the constructed tree.
    """
    nodes: Dict[str, Node] = {}

    # Create all nodes
    for parent, children in tree_dict.items():
        if parent not in nodes:
            nodes[parent] = Node(parent)
        for child in children:
            if child not in nodes:
                nodes[child] = Node(child)

    # Link nodes
    for parent, children in tree_dict.items():
        for child in children:
            nodes[parent].add_child(nodes[child])

    # Assume the root is the one without a parent
    root_candidates = set(nodes.keys()) - {child for children in tree_dict.values() for child in children}
    if len(root_candidates) != 1:
        raise ValueError("Tree must have exactly one root")

    root_name = root_candidates.pop()
    root = nodes[root_name]
    root.set_depth(0)
    return root



def create_tree_set_attribute(file_name):
    """
    Create a supply chain tree and set attributes, supporting multiple SKU per node.

    Parameters:
        file_name (str): Path to the tree file.

    Returns:
        tuple[dict, str]: Dictionary of Node instances and the root node name.
    """
    from collections import defaultdict

    width_tracker = defaultdict(int)
    root_node_name = ""

    rows = read_tree_file(file_name)
    nodes = {}

    # Phase 1: Create all nodes
    for row in rows:
        child_name = row["Child_node"]
        parent_name = row["Parent_node"]

        if child_name not in nodes:
            nodes[child_name] = Node(child_name)

        if parent_name != "root" and parent_name not in nodes:
            nodes[parent_name] = Node(parent_name)


    # Phase 2: Link tree structure
    for row in rows:
        parent_name = row["Parent_node"]
        child_name = row["Child_node"]
        product_name = row.get("Product_name", "")

        if parent_name == "root":
            root_node_name = child_name
            nodes[root_node_name].width += 4
        else:
            parent = nodes[parent_name]
            child = nodes[child_name]

            parent.add_child(child) 
            # 異なる親:供給元が同じ子:販売店を持つ場合
            # node.sku_dict[product_name]のproduct_nameで判定?

            # ここからSKU単位でset_attributesに切り替え
            if product_name:
                sku = child.add_sku(product_name)
                sku.set_attributes(row)
            else:
                print(f"[Warning] SKU attribute skipped: missing product_name in row {row}")




    #@250712 STOP
    ## Phase 2: Link tree structure
    #for row in rows:
    #    parent_name = row["Parent_node"]
    #    child_name = row["Child_node"]
    #    if parent_name == "root":
    #        root_node_name = child_name
    #        nodes[root_node_name].width += 4
    #    else:
    #        parent = nodes[parent_name]
    #        child = nodes[child_name]
    #        parent.add_child(child)
    #        child.set_attributes(row)



    # Phase 3: 確認のみ（オプション）
    for row in rows:
        child_name = row["Child_node"]
        pname = row.get("Product_name", "")
        if pname and pname not in nodes[child_name].sku_dict:
            nodes[child_name].add_sku(pname)

    return nodes, root_node_name


    #@250712 STOP
    # Phase 3: Register SKUs (multiple SKUs per Node)
    #for row in rows:
    #    child_name = row["Child_node"]
    #    if "product_name" in row and row["product_name"]:
    #        nodes[child_name].add_sku(row["product_name"])
    #
    #return nodes, root_node_name




def create_tree_set_attribute_OLD(file_name):
    """
    Create a supply chain tree and set attributes.

    Parameters:
        file_name (str): Path to the tree file.

    Returns:
        tuple[dict, str]: Dictionary of Node instances and the root node name.
    """
    width_tracker = defaultdict(int)
    root_node_name = ""

    # Read the tree file
    rows = read_tree_file(file_name)
    nodes = {row["child_node_name"]: Node(row["child_node_name"]) for row in rows}

    for row in rows:
        if row["Parent_node"] == "root":
            root_node_name = row["Child_node"]
            root = nodes[root_node_name]
            root.width += 4
        else:
            parent = nodes[row["Parent_node"]]
            child = nodes[row["Child_node"]]
            parent.add_child(child)
            child.set_attributes(row)

    return nodes, root_node_name






# ******************************
# Evaluation process
# ******************************

#[STEP 1] 下流価格 → 上流SKU まで逆伝播（Leaf → Root）
#[STEP 2] Root SKU の価格 → 全体へ正伝播（Root → Leaf）

def run_price_propagation_scenario(
    product_price_map: dict[str, float],
    leaf_node: Node,
    root_node: Node,
    node_dict: dict[str, Node]
):
    """
    製品ごとの末端価格（FOBなど）を元に、SKUコスト構造を双方向に評価展開するシナリオ処理。

    Parameters:
    - product_price_map: dict[product_name, leaf_sku_price]
    - leaf_node: Leaf Node（最終消費地点ノード）
    - root_node: Root Node（出発点）
    - node_dict: node_name → Node の辞書（親探索に使用）

    Returns:
    - root_val_dict: ルートSKUごとの評価済み辞書
    """

    root_val_dict = {}

    for product_name, leaf_price in product_price_map.items():

        leaf_sku = leaf_node.get_sku(product_name)
        root_sku = root_node.get_sku(product_name)

        if leaf_sku is None or root_sku is None:
            print(f"[Skip] SKU not found for product: {product_name}")
            continue

        # STEP 1: 価格逆伝播（Leaf → Root）
        print(f"\n🔁 Backward: {product_name} → 価格逆伝播開始")
        root_price = set_price_leaf2root_sku(
            sku=leaf_sku,
            root_sku=root_sku,
            val=leaf_price,
            node_dict=node_dict
        )

        print(f"✅ Root Price for {product_name}: {root_price:.2f}")

        # STEP 2: 価格正伝播（Root → Leaf）
        root_sku.cs_price_sales_shipped = root_price
        root_val_dict[product_name] = root_sku

    print("\n▶️ Forward: 全体へ価格評価伝播")
    set_value_chain_outbound_sku(root_val_dict, root_node)

    return root_val_dict


#@250712 ADD
def set_price_leaf2root_sku(sku, root_sku, val, node_dict):
    """
    SKUベースでLeaf→Rootにコスト逆伝播（.node_nameを使って親ノード探索）
    
    Parameters:
        sku (SKU): 現在のSKU
        root_sku (SKU): ルートSKU（比較対象）
        val (float): 価格（下流SKUから伝播される）
        node_dict (dict[str, Node]): node_name → Node の辞書（全ノード保持）
    Returns:
        float: 最終的な上流SKUでの出発価格（root）
    """
    pb = sku.price_sales_shipped

    if pb == 0:
        print(f"[Error] SKU {sku.product_name}@{sku.node_name}: price_sales_shipped is 0")
        return 0

    # 評価値をSKUにセット
    sku.cs_price_sales_shipped = val
    sku.cs_cost_total = val * sku.cost_total / pb
    sku.cs_profit = val * sku.profit / pb
    sku.cs_marketing_promotion = val * sku.marketing_promotion / pb
    sku.cs_sales_admin_cost = val * sku.sales_admin_cost / pb
    sku.cs_SGA_total = sku.cs_marketing_promotion + sku.cs_sales_admin_cost

    sku.cs_logistics_costs = val * sku.logistics_costs / pb
    sku.cs_warehouse_cost = val * sku.warehouse_cost / pb
    sku.cs_direct_materials_costs = val * sku.direct_materials_costs / pb
    sku.cs_purchase_total_cost = val * sku.purchase_total_cost / pb

    sku.cs_prod_indirect_labor = val * sku.prod_indirect_labor / pb
    sku.cs_prod_indirect_others = val * sku.prod_indirect_others / pb
    sku.cs_direct_labor_costs = val * sku.direct_labor_costs / pb
    sku.cs_depreciation_others = val * sku.depreciation_others / pb
    sku.cs_manufacturing_overhead = val * sku.manufacturing_overhead / pb

    print(f"[Trace] {sku.node_name}:{sku.product_name} ← cs_price = {sku.cs_price_sales_shipped:.2f}")

    if sku == root_sku:
        sku.cs_profit_accume = sku.cs_profit
        return sku.cs_price_sales_shipped
    else:
        current_node = node_dict[sku.node_name]

        #@250716ココの親nodeの製品名を判定する・・・しかし、一つしかない???
        parent_node = current_node.parent

        if parent_node is None:
            raise ValueError(f"[Error] Parent not found for node {sku.node_name}")
        else:
            print(f"[Status] current_node {sku.node_name} and parent_node {parent_node.name} are matching {sku.product_name}")

        #@250716 STOP 親node(供給元)が複数あるので、すべてcheck
        #parent_sku = parent_node.get_sku(sku.product_name)

        for prod_regist in list( parent_node.sku_dict.keys() ):
            if prod_regist == sku.product_name:  # 登録prodと整合check
                parent_sku = parent_node.get_sku(prod_regist)
                pass
            else:
                print("product_name unmatching in node_profile")

        return set_price_leaf2root_sku(parent_sku, root_sku, sku.cs_direct_materials_costs, node_dict)




def set_price_leaf2root_sku_OLD(sku, root_sku, val):
    """
    SKUベースでLeaf→Rootにコスト逆伝播する再帰関数。
    
    Parameters:
    - sku: 現在のSKU（Node.sku_dict[product_name]）
    - root_sku: ルートSKU
    - val: 末端側で評価された価格（最終製品のFOBなど）
    
    Returns:
    - root_price: 根本SKUでの価格（最終的な上流価格）
    """
    pb = sku.price_sales_shipped

    if pb == 0:
        print(f"[Error] SKU {sku.product_name}@{sku.node_name}: price_sales_shipped is 0")
        return 0

    # 評価価格設定
    sku.cs_price_sales_shipped = val
    sku.cs_cost_total = val * sku.cost_total / pb
    sku.cs_profit = val * sku.profit / pb
    sku.cs_marketing_promotion = val * sku.marketing_promotion / pb
    sku.cs_sales_admin_cost = val * sku.sales_admin_cost / pb
    sku.cs_SGA_total = sku.cs_marketing_promotion + sku.cs_sales_admin_cost

    sku.cs_logistics_costs = val * sku.logistics_costs / pb
    sku.cs_warehouse_cost = val * sku.warehouse_cost / pb
    sku.cs_direct_materials_costs = val * sku.direct_materials_costs / pb
    sku.cs_purchase_total_cost = val * sku.purchase_total_cost / pb

    sku.cs_prod_indirect_labor = val * sku.prod_indirect_labor / pb
    sku.cs_prod_indirect_others = val * sku.prod_indirect_others / pb
    sku.cs_direct_labor_costs = val * sku.direct_labor_costs / pb
    sku.cs_depreciation_others = val * sku.depreciation_others / pb
    sku.cs_manufacturing_overhead = val * sku.manufacturing_overhead / pb

    # デバッグ出力（必要に応じて）
    print(f"[Trace] set_price_leaf2root_sku {sku.node_name}:{sku.product_name} cs_price={sku.cs_price_sales_shipped:.2f}")

    if sku == root_sku:
        sku.cs_profit_accume = sku.cs_profit
        return sku.cs_price_sales_shipped
    else:
        parent_node = sku_node_map[sku.node_name].parent  # ※または sku.parent_node
        if parent_node is None:
            raise ValueError(f"[Error] Parent not found for SKU: {sku.product_name}@{sku.node_name}")
        parent_sku = parent_node.get_sku(sku.product_name)
        return set_price_leaf2root_sku(parent_sku, root_sku, sku.cs_direct_materials_costs)




def set_price_leaf2root(node, root_node_outbound, val):

    #print("node.name ", node.name)
    root_price = 0

    pb = 0
    pb = node.price_sales_shipped  # pb : Price_Base

    # set value on shipping price
    node.cs_price_sales_shipped = val

    print("def set_price_leaf2root", node.name, node.cs_price_sales_shipped )

    node.show_sum_cs()



    # cs : Cost_Stracrure
    node.cs_cost_total = val * node.cost_total / pb
    node.cs_profit = val * node.profit / pb
    node.cs_marketing_promotion = val * node.marketing_promotion / pb
    node.cs_sales_admin_cost = val * node.sales_admin_cost / pb
    node.cs_SGA_total = val * node.SGA_total / pb

    #node.cs_custom_tax = val * node.custom_tax / pb
    #node.cs_tax_portion = val * node.tax_portion / pb

    node.cs_logistics_costs = val * node.logistics_costs / pb
    node.cs_warehouse_cost = val * node.warehouse_cost / pb

    # direct shipping price that is,  like a FOB at port
    node.cs_direct_materials_costs = val * node.direct_materials_costs / pb

    node.cs_purchase_total_cost = val * node.purchase_total_cost / pb
    node.cs_prod_indirect_labor = val * node.prod_indirect_labor / pb
    node.cs_prod_indirect_others = val * node.prod_indirect_others / pb
    node.cs_direct_labor_costs = val * node.direct_labor_costs / pb
    node.cs_depreciation_others = val * node.depreciation_others / pb
    node.cs_manufacturing_overhead = val * node.manufacturing_overhead / pb

    print("probe")
    node.show_sum_cs()

    #print("node.cs_direct_materials_costs", node.name, node.cs_direct_materials_costs)
    #print("root_node_outbound.name", root_node_outbound.name)


    if node.name == root_node_outbound.name:
    #if node == root_node_outbound:

        node.cs_profit_accume = node.cs_profit # profit_accumeの初期セット

        root_price = node.cs_price_sales_shipped
        # root_price = node.cs_direct_materials_costs

        pass

    else:

        root_price = set_price_leaf2root(
            node.parent, root_node_outbound, node.cs_direct_materials_costs
        )

    return root_price


#@250712 ADD
def set_value_chain_outbound_sku(val_dict: dict[str, SKU], node: Node):
    for child in node.children:
        for product_name, sku in child.sku_dict.items():
            parent_sku = val_dict.get(product_name)

            if parent_sku is None:
                print(f"[Warn] No root SKU value for {product_name}")
                continue

            pb = sku.direct_materials_costs
            if pb == 0:
                print(f"[Warn] {child.name}:{product_name} pb=0")
                continue

            # 伝播計算
            sku.cs_direct_materials_costs = parent_sku.cs_price_sales_shipped
            sku.cs_tax_portion = sku.cs_direct_materials_costs * sku.customs_tariff_rate

            sku.cs_price_sales_shipped = sku.cs_direct_materials_costs * sku.price_sales_shipped / pb
            sku.cs_profit = sku.cs_direct_materials_costs * sku.profit / pb
            sku.cs_marketing_promotion = sku.cs_direct_materials_costs * sku.marketing_promotion / pb
            sku.cs_sales_admin_cost = sku.cs_direct_materials_costs * sku.sales_admin_cost / pb
            sku.cs_SGA_total = sku.cs_marketing_promotion + sku.cs_sales_admin_cost
            # 他項目も同様に...

            sku.cs_profit_accume += sku.cs_profit

            # 次ノードに伝播（SKUを更新したval_dictを渡す）
            val_dict[product_name] = sku

        set_value_chain_outbound_sku(val_dict, child)


# 1st val is "root_price"
# 元の売値=valが、先の仕入れ値=pb Price_Base portionになる。
def set_value_chain_outbound(val, node):


    # root_nodeをpassして、子供からstart


    # はじめは、root_nodeなのでnode.childrenは存在する
    for child in node.children:

        #print("set_value_chain_outbound child.name ", child.name)
        # root_price = 0

        pb = 0
        pb = child.direct_materials_costs  # pb : Price_Base portion

        print("child.name", child.name)
        print("pb = child.direct_materials_costs",child.direct_materials_costs)

        # pb = child.price_sales_shipped # pb : Price_Base portion

        # direct shipping price that is,  like a FOB at port

        child.cs_direct_materials_costs = val

        ## direct shipping price that is,  like a FOB at port
        #node.cs_direct_materials_costs = val * node.direct_materials_costs /pb

        #@250322 updated
        #child.cs_custom_tax = val * child.custom_tax / pb   # STOP tariff_rate
        #child.cs_tax_portion = val * child.tax_portion / pb # custom_tax
        # ****************************
        # custom_tax = materials_cost imported X custom_tariff 
        # ****************************
        child.cs_tax_portion            = child.cs_direct_materials_costs * child.customs_tariff_rate



        # set value on shipping price
        child.cs_price_sales_shipped = val * child.price_sales_shipped / pb
        #print("def set_value_chain_outbound", child.name, child.cs_price_sales_shipped )
        child.show_sum_cs()



        val_child = child.cs_price_sales_shipped

        # cs : Cost_Stracrure
        child.cs_cost_total = val * child.cost_total / pb

        child.cs_profit = val * child.profit / pb

        # root2leafまでprofit_accume
        child.cs_profit_accume += node.cs_profit

        child.cs_marketing_promotion = val * child.marketing_promotion / pb
        child.cs_sales_admin_cost = val * child.sales_admin_cost / pb
        child.cs_SGA_total = val * child.SGA_total / pb

        child.cs_logistics_costs = val * child.logistics_costs / pb
        child.cs_warehouse_cost = val * child.warehouse_cost / pb


        child.cs_purchase_total_cost = val * child.purchase_total_cost / pb
        child.cs_prod_indirect_labor = val * child.prod_indirect_labor / pb
        child.cs_prod_indirect_others = val * child.prod_indirect_others / pb
        child.cs_direct_labor_costs = val * child.direct_labor_costs / pb
        child.cs_depreciation_others = val * child.depreciation_others / pb
        child.cs_manufacturing_overhead = val * child.manufacturing_overhead / pb

        #print("probe")
        #child.show_sum_cs()


        print(
            "node.cs_direct_materials_costs",
            child.name,
            child.cs_direct_materials_costs,
        )
        # print("root_node_outbound.name", root_node_outbound.name )

        # to be rewritten@240803

        if child.children == []:  # leaf_nodeなら終了

            pass

        else:  # 孫を処理する

            set_value_chain_outbound(val_child, child)

    # return


# **************************************
# call from gui.app
# **************************************




#@ STOP
#def eval_supply_chain_cost(node, context):
#    """
#    Recursively evaluates the cost of the entire supply chain.
#    
#    Parameters:
#        node (Node): The node currently being evaluated.
#        context (object): An object holding the total cost values (e.g., an instance of the GUI class).
#    """
#    # Count the number of lots for each node
#    node.set_lot_counts()
#
#    # Perform cost evaluation
#    total_revenue, total_profit = node.EvalPlanSIP_cost()
#
#    # Add the evaluation results to the context
#    context.total_revenue += total_revenue
#    context.total_profit += total_profit
#
#    # Recursively evaluate for child nodes
#    for child in node.children:
#        eval_supply_chain_cost(child, context)


# ******************************
# PSI evaluation on tree
# ******************************
# ******************************
# PSI evaluation on tree
# ******************************

#@250216 cash_out_in

def eval_supply_chain_cash(node):


    # by node
    # cash_out = psiのPで、P*price weekly list AP_LT offset
    # cash_in  = psiのSで、P*price weekly list AR_LT offset


    # Count the number of lots for the node
    node.set_lot_counts()

    # Evaluate the current node's costs
    node.revenue, node.profit = node.EvalPlanSIP_cost()



    # Accumulate the revenue and profit
    total_revenue += node.revenue
    total_profit  += node.profit

    # Recursively evaluate child nodes
    for child in node.children:
        total_revenue, total_profit = eval_supply_chain_cost(
            child, total_revenue, total_profit
        )


    return cash_out, cash_in


# = eval_supply_chain_cash(self.root_node_outbound)





def eval_supply_chain_cost(node, total_revenue=0, total_profit=0):
    """
    Recursively evaluates the cost of the supply chain for a given node.
    
    Parameters:
        node (Node): The root node to start the evaluation.
        total_revenue (float): Accumulated total revenue (default 0).
        total_profit (float): Accumulated total profit (default 0).

    Returns:
        Tuple[float, float]: Accumulated total revenue and total profit.
    """
    # Count the number of lots for the node
    node.set_lot_counts()

    # Evaluate the current node's costs
    node.revenue, node.profit = node.EvalPlanSIP_cost()



    # Accumulate the revenue and profit
    total_revenue += node.revenue
    total_profit  += node.profit

    # Recursively evaluate child nodes
    for child in node.children:
        total_revenue, total_profit = eval_supply_chain_cost(
            child, total_revenue, total_profit
        )

    return total_revenue, total_profit









# *****************
# network graph "node" "edge" process
# *****************




def make_edge_weight_capacity(node, child):
    # Calculate stock cost and customs tariff
    child.EvalPlanSIP_cost()

    #@ STOP
    #stock_cost = sum(child.WH_cost[1:])

    customs_tariff = child.customs_tariff_rate * child.cs_direct_materials_costs

    # Determine weight (logistics cost + tax + storage cost)
    cost_portion = 0.5
    weight4nx = max(0, child.cs_cost_total + (customs_tariff * cost_portion))

    # Calculate capacity (3 times the average weekly demand)
    demand_lots = sum(len(node.psi4demand[w][0]) for w in range(53 * node.plan_range))
    ave_demand_lots = demand_lots / (53 * node.plan_range)
    capacity4nx = 3 * ave_demand_lots

    # Add tariff to leaf nodes
    def add_tariff_on_leaf(node, customs_tariff):
        if not node.children:
            node.tariff_on_price += customs_tariff * cost_portion
        else:
            for child in node.children:
                add_tariff_on_leaf(child, customs_tariff)

    add_tariff_on_leaf(node, customs_tariff)

    # Logging for debugging (optional)
    print(f"child.name: {child.name}")
    print(f"weight4nx: {weight4nx}, capacity4nx: {capacity4nx}")

    return weight4nx, capacity4nx




def make_edge_weight_capacity_OLD(node, child):
    # Weight (重み)
    #    - `weight`は、edgeで定義された2つのノード間の移動コストを表す。
    #       物流費、関税、保管コストなどの合計金額に対応する。
    #    - 例えば、物流費用が高い場合、対応するエッジの`weight`は高くなる。
    #     最短経路アルゴリズム(ダイクストラ法)を適用すると適切な経路を選択する。
    #
    #    self.demandにセット?
    #

    # *********************
    # add_edge_parameter_set_weight_capacity()
    # add_edge()の前処理
    # *********************
    # capacity
    # - `capacity`は、エッジで定義された2つのノード間における期間当たりの移動量
    #   の制約を表します。
    # - サプライチェーンの場合、以下のアプリケーション制約条件を考慮して
    #   ネック条件となる最小値を設定する。
    #     - 期間内のノード間物流の容量の上限値
    #     - 通関の期間内処理量の上限値
    #     - 保管倉庫の上限値
    #     - 出庫・出荷作業の期間内処理量の上限値


    # *****************************************************
    # 在庫保管コストの算定のためにevalを流す
    # 子ノード child.
    # *****************************************************
    stock_cost = 0

    #@ 要確認
    #@241231 ココは新しいcost_tableで評価する
    child.EvalPlanSIP_cost()

    stock_cost = child.eval_WH_cost = sum(child.WH_cost[1:])

    customs_tariff = 0

    #@241231 関税率 X 仕入れ単価とする
    customs_tariff = child.customs_tariff_rate * child.cs_direct_materials_costs

    print("child.name", child.name)
    print("child.customs_tariff_rate", child.customs_tariff_rate)
    print("child.cs_direct_materials_costs", child.cs_direct_materials_costs)
    print("customs_tariff", customs_tariff)

    print("self.cs_price_sales_shipped", node.cs_price_sales_shipped)
    print("self.cs_cost_total", node.cs_cost_total)
    print("self.cs_profit", node.cs_profit)


    #関税コストの吸収方法 1
    # 1. 利益を維持し、コストと価格に上乗せする。
    # 2. 価格を維持し、コストに上乗せし、利益を削る。

    #    self.cs_price_sales_shipped # revenue
    #    self.cs_cost_total          # cost
    #    self.cs_profit              # profit


    #@ OLD STOP
    # 関税率 X 単価
    #customs_tariff = child.customs_tariff_rate * child.REVENUE_RATIO



    weight4nx = 0


    # 物流コスト
    # + TAX customs_tariff
    # + 在庫保管コスト
    # weight4nx = child.Distriburion_Cost + customs_tariff + stock_cost


    #@241231 仮定:関税の増分50%を利益削減する
    cost_portion = 0.5  # price_portion = 0.5 is following

    #@ RUN 
    weight4nx = child.cs_cost_total + (customs_tariff * cost_portion)



    #@ STOP
    #weight4nx = child.cs_profit_accume - (customs_tariff * cost_portion)
    #weight4nx =100*2 - child.cs_profit_accume + (customs_tariff *cost_portion)

    #print("child.cs_profit_accume", child.cs_profit_accume)

    print("child.cs_cost_total", child.cs_cost_total)

    print("customs_tariff", customs_tariff)
    print("cost_portion", cost_portion)
    print("weight4nx", weight4nx)



    if weight4nx < 0:
        weight4nx = 0


    # 出荷コストはPO_costに含まれている
    ## 出荷コスト
    # + xxxx

    #print("child.Distriburion_Cost", child.Distriburion_Cost)
    #print("+ TAX customs_tariff", customs_tariff)
    #print("+ stock_cost", stock_cost)
    #print("weight4nx", weight4nx)

    # ******************************
    # capacity4nx = 3 * average demand lots # ave weekly demand の3倍のcapa
    # ******************************
    capacity4nx = 0

    # ******************************
    # average demand lots
    # ******************************
    demand_lots = 0
    ave_demand_lots = 0

    for w in range(53 * node.plan_range):
        demand_lots += len(node.psi4demand[w][0])

    ave_demand_lots = demand_lots / (53 * node.plan_range)

    #@241231 仮定:関税の増分50%を価格増加による需要曲線上の価格弾力性=1とする
    # on the demand curve,
    # assume a price elasticity of demand of 1 due to price increase.

    #    self.cs_price_sales_shipped # revenue

    # demand_on_curve 需要曲線上の需要
    # customs_tariff*0.5 関税の50%
    # self.cs_price_sales_shipped 売上

    # 価格弾力性による需要変化
    # customs_tariff*0.5 / self.cs_price_sales_shipped 価格増加率
    # self.price_elasticity
    # 0.0: demand "stay" like a medecine
    # 1.0: demand_decrease = price_increse * 1
    # 2.0: demand_decrease = price_increse * 2

    #@241231 MEMO demand_curve
    # 本来、demandは価格上昇時に末端市場leaf_nodeで絞られるが、
    # ここでは、通関時の中間nodeのcapacityでdemandを絞ることで同様の効果とする

    # 末端価格ではないので、関税による価格増減率が異なる?
    # customs_tariff:関税増分のcostを退避しておく、self.customs_tariff
    # leaf_nodeの末端価格のdemand_on_curve = 価格増加率 * node.price_elasticity


    # (customs_tariff * 0.5) をlead_nodeのnode.tariff_on_priceにadd

    def add_tariff_on_leaf(node, customs_tariff):

        price_portion = 0.5 # cost_portion = 0.5 is previously defined

        if node.children == []:  # leaf_node
            node.tariff_on_price += customs_tariff * price_portion # 0.5
        else:
            for child in node.children:
                add_tariff_on_leaf(child, customs_tariff)

    add_tariff_on_leaf(node, customs_tariff)

    #@ STOP
    #demand_on_curve = 3 * ave_demand_lots * (1-(customs_tariff*0.5 / node.cs_price_sales_shipped) * node.price_elasticity )
    #
    #capacity4nx = demand_on_curve       # 


    #@ STOP RUN
    capacity4nx = 3 * ave_demand_lots  # N * ave weekly demand

    print("weight4nx", weight4nx)
    print("capacity4nx", capacity4nx)

    return weight4nx, capacity4nx  # ココはfloatのまま戻す








def G_add_edge_from_tree(node, G):

    if node.children == []:  # leaf_nodeを判定

        # ******************************
        # capacity4nx = average demand lots # ave weekly demand をそのままset
        # ******************************
        capacity4nx = 0
        demand_lots = 0
        ave_demand_lots = 0

        for w in range(53 * node.plan_range):
            demand_lots += len(node.psi4demand[w][0])

        ave_demand_lots = demand_lots / (53 * node.plan_range)

        capacity4nx = ave_demand_lots  # N * ave weekly demand


        # ******************************
        # edge connecting leaf_node and "sales_office" 接続
        # ******************************

        #@ RUN X1
        capacity4nx_int = round(capacity4nx) + 1

        #@ STOP
        # float2int X100
        #capacity4nx_int = float2int(capacity4nx)

        G.add_edge(node.name, "sales_office",
                 weight=0,
                 #capacity=capacity4nx_int
                 capacity=2000
        )

        print(
            "G.add_edge(node.name, office",
            node.name,
            "sales_office",
            "weight = 0, capacity =",
            capacity4nx,
        )

        # pass

    else:

        for child in node.children:

            # *****************************
            # make_edge_weight_capacity
            # *****************************
            weight4nx, capacity4nx = make_edge_weight_capacity(node, child)

            # float2int
            weight4nx_int = float2int(weight4nx)

            #@ RUN X1
            capacity4nx_int = round(capacity4nx) + 1

            #@ STOP
            # float2int X100
            #capacity4nx_int = float2int(capacity4nx)

            child.nx_weight = weight4nx_int
            child.nx_capacity = capacity4nx_int

            # ******************************
            # edge connecting self.node & child.node
            # ******************************

            G.add_edge(
                node.name, child.name, 
                weight=weight4nx_int,

                #capacity=capacity4nx_int
                capacity=2000

            )

            print(
                "G.add_edge(node.name, child.name",
                node.name,
                child.name,
                "weight =",
                weight4nx_int,
                "capacity =",
                capacity4nx_int,
            )

            G_add_edge_from_tree(child, G)





def Gsp_add_edge_sc2nx_inbound(node, Gsp):

    if node.children == []:  # leaf_nodeを判定

        # ******************************
        # capacity4nx = average demand lots # ave weekly demand をそのままset
        # ******************************
        capacity4nx = 0
        demand_lots = 0
        ave_demand_lots = 0

        for w in range(53 * node.plan_range):
            demand_lots += len(node.psi4demand[w][0])

        ave_demand_lots = demand_lots / (53 * node.plan_range)

        capacity4nx = ave_demand_lots  # N * ave weekly demand

        # ******************************
        # edge connecting leaf_node and "sales_office" 接続
        # ******************************

        # float2int
        capacity4nx_int = float2int(capacity4nx)

        Gsp.add_edge( "procurement_office", node.name,
                 weight=0,
                 capacity = 2000 # 240906 TEST # capacity4nx_int * 1 # N倍
                 #capacity=capacity4nx_int * 1 # N倍
        )

        # pass

    else:

        for child in node.children:

            # *****************************
            # make_edge_weight_capacity
            # *****************************
            weight4nx, capacity4nx = make_edge_weight_capacity(node, child)

            # float2int
            weight4nx_int = float2int(weight4nx)
            capacity4nx_int = float2int(capacity4nx)

            #@240906 TEST 
            capacity4nx_int = 2000

            child.nx_weight = weight4nx_int
            child.nx_capacity = capacity4nx_int

            # ******************************
            # edge connecting self.node & child.node
            # ******************************

            Gsp.add_edge(
                child.name, node.name, 
                weight=weight4nx_int,

                capacity=capacity4nx_int
            )

            Gsp_add_edge_sc2nx_inbound(child, Gsp)





def Gdm_add_edge_sc2nx_outbound(node, Gdm):

    if node.children == []:  # leaf_nodeを判定

        # ******************************
        # capacity4nx = average demand lots # ave weekly demand をそのままset
        # ******************************
        capacity4nx = 0
        demand_lots = 0
        ave_demand_lots = 0

        for w in range(53 * node.plan_range):
            demand_lots += len(node.psi4demand[w][0])



        ave_demand_lots = demand_lots / (53 * node.plan_range)

        #@ STOP
        #capacity4nx = ave_demand_lots  # N * ave weekly demand


        if node.cs_price_sales_shipped == 0:
            tariff_portion = 0
        else:
            tariff_portion = node.tariff_on_price / node.cs_price_sales_shipped

        demand_on_curve = 3 * ave_demand_lots * (1- tariff_portion) * node.price_elasticity 


        print("node.name", node.name)

        print("node.tariff_on_price", node.tariff_on_price)
        print("node.cs_price_sales_shipped", node.cs_price_sales_shipped)
        print("tariff_portion", tariff_portion)

        print("ave_demand_lots", ave_demand_lots)
        print("node.price_elasticity", node.price_elasticity)
        print("demand_on_curve", demand_on_curve)



        #demand_on_curve = 3 * ave_demand_lots * (1-(customs_tariff*0.5 / node.cs_price_sales_shipped) * node.price_elasticity )

        capacity4nx = demand_on_curve       # 


        print("capacity4nx", capacity4nx)



        # ******************************
        # edge connecting leaf_node and "sales_office" 接続
        # ******************************

        # float2int
        capacity4nx_int = float2int(capacity4nx)

        # set PROFIT 2 WEIGHT

        Gdm.add_edge(node.name, "sales_office",
                 weight=0,
                 capacity=capacity4nx_int * 1 # N倍
        )

        print(
            "Gdm.add_edge(node.name, office",
            node.name,
            "sales_office",
            "weight = 0, capacity =",
            capacity4nx,
        )

        # pass

    else:

        for child in node.children:

            # *****************************
            # make_edge_weight_capacity
            # *****************************
            weight4nx, capacity4nx = make_edge_weight_capacity(node, child)

            # float2int
            weight4nx_int = float2int(weight4nx)
            capacity4nx_int = float2int(capacity4nx)

            child.nx_weight = weight4nx_int
            child.nx_capacity = capacity4nx_int

            # ******************************
            # edge connecting self.node & child.node
            # ******************************

            Gdm.add_edge(
                node.name, child.name, 
                weight=weight4nx_int,

                capacity=capacity4nx_int
            )

            print(
                "Gdm.add_edge(node.name, child.name",
                node.name, child.name,
                "weight =", weight4nx_int,
                "capacity =", capacity4nx_int
            )

            Gdm_add_edge_sc2nx_outbound(child, Gdm)






def make_edge_weight(node, child):


#NetworkXでは、エッジの重み（weight）が大きい場合、そのエッジの利用優先度は、アルゴリズムや目的によって異なる

    # Weight (重み)
    #    - `weight`はedgeで定義された2ノード間で発生するprofit(rev-cost)で表す
    #       cost=物流費、関税、保管コストなどの合計金額に対応する。
    #    - 例えば、物流費用が高い場合、対応するエッジの`weight`は低くなる。
    #     最短経路アルゴリズム(ダイクストラ法)を適用すると適切な経路を選択する。

#最短経路アルゴリズム（例：Dijkstra’s algorithm）では、エッジの重みが大きいほど、そのエッジを通る経路のコストが高くなるため、優先度は下がる

#最大フロー問題などの他のアルゴリズムでは、エッジの重みが大きいほど、そのエッジを通るフローが多くなるため、優先度が上がることがある
#具体的な状況や使用するアルゴリズムによって異なるため、
#目的に応じて適切なアルゴリズムを選択することが重要

# 最大フロー問題（Maximum Flow Problem）
# フォード・ファルカーソン法 (Ford-Fulkerson Algorithm)
#フォード・ファルカーソン法は、ネットワーク内のソース（始点）からシンク（終点）までの最大フローを見つけるアルゴリズム
#このアルゴリズムでは、エッジの重み（容量）が大きいほど、そのエッジを通るフローが多くなるため、優先度が上がります。


#@240831 
#    # *****************************************************
#    # 在庫保管コストの算定のためにevalを流す
#    # 子ノード child.
#    # *****************************************************
#
#    stock_cost = 0
#
#    child.EvalPlanSIP()
#
#    stock_cost = child.eval_WH_cost = sum(child.WH_cost[1:])
#
#    customs_tariff = 0
#    customs_tariff = child.customs_tariff_rate * child.REVENUE_RATIO  # 関税率 X 単価
#
#    # 物流コスト
#    # + TAX customs_tariff
#    # + 在庫保管コスト
#    # weight4nx = child.Distriburion_Cost + customs_tariff + stock_cost


    # priority is "profit"

    weight4nx = 0

    weight4nx = child.cs_profit_accume

    return weight4nx






#@240830 コこを修正
# 1.capacityの計算は、supply sideで製品ロット単位の統一したroot_capa * N倍
# 2.自node=>親nodeの関係定義 G.add_edge(self.node, parent.node)

def G_add_edge_from_inbound_tree(node, supplyers_capacity, G):

    if node.children == []:  # leaf_nodeを判定

        # ******************************
        # capacity4nx = average demand lots # ave weekly demand *N倍をset
        # ******************************
        capacity4nx = 0

        # 
        # ******************************
        #demand_lots = 0
        #ave_demand_lots = 0
        #
        #for w in range(53 * node.plan_range):
        #    demand_lots += len(node.psi4demand[w][0])
        #
        #ave_demand_lots = demand_lots / (53 * node.plan_range)
        #
        #capacity4nx = ave_demand_lots * 5  # N * ave weekly demand
        #
        # ******************************

        # supplyers_capacityは、root_node=mother plantのcapacity
        # 末端suppliersは、平均の5倍のcapa
        capacity4nx = supplyers_capacity * 5  # N * ave weekly demand


        # float2int
        capacity4nx_int = float2int(capacity4nx)

        # ******************************
        # edge connecting leaf_node and "procurement_office" 接続
        # ******************************

        G.add_edge("procurement_office", node.name, weight=0, capacity=2000)

        #G.add_edge("procurement_office", node.name, weight=0, capacity=capacity4nx_int)

        print(
            "G.add_edge(node.name, office",
            node.name,
            "sales_office",
            "weight = 0, capacity =",
            capacity4nx,
        )

        # pass

    else:

        for child in node.children:


            # supplyers_capacityは、root_node=mother plantのcapacity
            # 中間suppliersは、平均の3倍のcapa
            capacity4nx = supplyers_capacity * 3  # N * ave weekly demand


            # *****************************
            # set_edge_weight
            # *****************************
            weight4nx = make_edge_weight(node, child)

            ## *****************************
            ## make_edge_weight_capacity
            ## *****************************
            #weight4nx, capacity4nx = make_edge_weight_capacity(node, child)



            # float2int
            weight4nx_int = float2int(weight4nx)
            capacity4nx_int = float2int(capacity4nx)

            child.nx_weight = weight4nx_int
            child.nx_capacity = capacity4nx_int

            # ******************************
            # edge connecting from child.node to self.node as INBOUND
            # ******************************
            #G.add_edge(
            #    child.name, node.name, 
            #    weight=weight4nx_int, capacity=capacity4nx_int
            #)

            G.add_edge(
                child.name, node.name, 
                weight=weight4nx_int, capacity=2000
            )

            #print(
            #    "G.add_edge(child.name, node.name ",
            #    child.name,
            #    node.name,
            #    "weight =",
            #    weight4nx_int,
            #    "capacity =", 
            #    capacity4nx_int,
            #)

            G_add_edge_from_inbound_tree(child, supplyers_capacity, G)






    # *********************
    # OUT treeを探索してG.add_nodeを処理する
    # node_nameをGにセット (X,Y)はfreeな状態、(X,Y)のsettingは後処理
    # *********************
def G_add_nodes_from_tree(node, G):


    G.add_node(node.name, demand=0)
    #G.add_node(node.name, demand=node.nx_demand) #demandは強い制約でNOT set!!

    print("G.add_node", node.name, "demand =", node.nx_demand)

    if node.children == []:  # leaf_nodeの場合、total_demandに加算

        pass

    else:

        for child in node.children:

            G_add_nodes_from_tree(child, G)



    # *********************
    # IN treeを探索してG.add_nodeを処理する。ただし、root_node_inboundをskip
    # node_nameをGにセット (X,Y)はfreeな状態、(X,Y)のsettingは後処理
    # *********************
def G_add_nodes_from_tree_skip_root(node, root_node_name_in, G):

    #@240901STOP
    #if node.name == root_node_name_in:
    #
    #    pass
    #
    #else:
    #
    #    G.add_node(node.name, demand=0)
    #    print("G.add_node", node.name, "demand = 0")

    G.add_node(node.name, demand=0)
    print("G.add_node", node.name, "demand = 0")

    if node.children == []:  # leaf_nodeの場合

        pass

    else:

        for child in node.children:

            G_add_nodes_from_tree_skip_root(child, root_node_name_in, G)
        





# *****************
# demand, weight and scaling FLOAT to INT
# *****************
def float2int(value):

    scale_factor = 100
    scaled_demand = value * scale_factor

    # 四捨五入
    rounded_demand = round(scaled_demand)
    # print(f"四捨五入: {rounded_demand}")

    ## 切り捨て
    # floored_demand = math.floor(scaled_demand)
    # print(f"切り捨て: {floored_demand}")

    ## 切り上げ
    # ceiled_demand = math.ceil(scaled_demand)
    # print(f"切り上げ: {ceiled_demand}")

    return rounded_demand



# *********************
# 末端市場、最終消費の販売チャネルのdemand = leaf_node_demand
# treeのleaf nodesを探索して"weekly average base"のtotal_demandを集計
# *********************
def set_leaf_demand(node, total_demand):

    if node.children == []:  # leaf_nodeの場合、total_demandに加算

        # ******************************
        # average demand lots
        # ******************************
        demand_lots = 0
        ave_demand_lots = 0
        ave_demand_lots_int = 0

        for w in range(53 * node.plan_range):
            demand_lots += len(node.psi4demand[w][0])

        ave_demand_lots = demand_lots / (53 * node.plan_range)

        # float2int
        ave_demand_lots_int = float2int(ave_demand_lots)


        # **** networkX demand *********
        # set demand on leaf_node    
        # weekly average demand by lot
        # ******************************
        node.nx_demand = ave_demand_lots_int


        total_demand += ave_demand_lots_int

    else:

        for child in node.children:

            # "行き" GOing on the way

            total_demand = set_leaf_demand(child, total_demand)


            # "帰り" RETURNing on the way BACK
            node.nx_demand = child.nx_demand  # set "middle_node" demand


    return total_demand





# ***************************
# make network with NetworkX
# show network with plotly
# ***************************



def calc_put_office_position(pos_office, office_name):
    x_values = [pos_office[key][0] for key in pos_office]
    max_x = max(x_values)
    y_values = [pos_office[key][1] for key in pos_office]
    max_y = max(y_values)
    pos_office[office_name] = (max_x + 1, max_y + 1)
    return pos_office

def generate_positions(node, pos, depth=0, y_offset=0, leaf_y_positions=None):
    if not node.children:
        pos[node.name] = (depth, leaf_y_positions.pop(0))
    else:
        child_y_positions = []
        for child in node.children:
            generate_positions(child, pos, depth + 1, y_offset, leaf_y_positions)
            child_y_positions.append(pos[child.name][1])
        pos[node.name] = (depth, sum(child_y_positions) / len(child_y_positions))  # 子ノードのY軸平均値を親ノードに設定
    return pos

def count_leaf_nodes(node):
    if not node.children:
        return 1
    return sum(count_leaf_nodes(child) for child in node.children)

def get_leaf_y_positions(node, y_positions=None):
    if y_positions is None:
        y_positions = []
    if not node.children:
        y_positions.append(len(y_positions))
    else:
        for child in node.children:
            get_leaf_y_positions(child, y_positions)
    return y_positions

def tune_hammock(pos_E2E, nodes_outbound, nodes_inbound):
    # Compare 'procurement_office' and 'sales_office' Y values and choose the larger one
    procurement_office_y = pos_E2E['procurement_office'][1]
    office_y = pos_E2E['sales_office'][1]

    max_y = max(procurement_office_y, office_y)
    
    pos_E2E['procurement_office'] = (pos_E2E['procurement_office'][0], max_y)
    pos_E2E['sales_office'] = (pos_E2E['sales_office'][0], max_y)

    # Align 'FA_xxxx' and 'PL_xxxx' pairs and their children
    for key, value in pos_E2E.items():
        if key.startswith('MOM'):
            corresponding_key = 'DAD' + key[3:]
            if corresponding_key in pos_E2E:
                fa_y = value[1]
                pl_y = pos_E2E[corresponding_key][1]
                aligned_y = max(fa_y, pl_y)
                pos_E2E[key] = (value[0], aligned_y)
                pos_E2E[corresponding_key] = (pos_E2E[corresponding_key][0], aligned_y)


                offset_y = max( aligned_y - fa_y, aligned_y - pl_y )

                if aligned_y - fa_y == 0: # inboundの高さが同じ outboundを調整
                    
                    pool_node = nodes_outbound[corresponding_key]
                    adjust_child_positions(pool_node, pos_E2E, offset_y)

                else:

                    fassy_node = nodes_inbound[key]
                    adjust_child_positions(fassy_node, pos_E2E, offset_y)



                ## Adjust children nodes
                #adjust_child_positions(pos_E2E, key, aligned_y)
                #adjust_child_positions(pos_E2E, corresponding_key, aligned_y)

    return pos_E2E

#def adjust_child_positions(pos, parent_key, parent_y):
#    for key, value in pos.items():
#        if key != parent_key and pos[key][0] > pos[parent_key][0]:
#            pos[key] = (value[0], value[1] + (parent_y - pos[parent_key][1]))


def adjust_child_positions(node, pos, offset_y):
    if node.children == []:  # leaf_nodeを判定
        pass
    else:
        for child in node.children:
            # yの高さを調整 
            pos[child.name] = (pos[child.name][0], pos[child.name][1]+offset_y)
            adjust_child_positions(child, pos, offset_y)


def make_E2E_positions(root_node_outbound, root_node_inbound):
    out_leaf_count = count_leaf_nodes(root_node_outbound)
    in_leaf_count = count_leaf_nodes(root_node_inbound)

    print("out_leaf_count", out_leaf_count)
    print("in_leaf_count", in_leaf_count)

    out_leaf_y_positions = get_leaf_y_positions(root_node_outbound)
    in_leaf_y_positions = get_leaf_y_positions(root_node_inbound)

    pos_out = generate_positions(root_node_outbound, {}, leaf_y_positions=out_leaf_y_positions)
    pos_out = calc_put_office_position(pos_out, "sales_office")

    pos_in = generate_positions(root_node_inbound, {}, leaf_y_positions=in_leaf_y_positions)
    pos_in = calc_put_office_position(pos_in, "procurement_office")

    max_x = max(x for x, y in pos_in.values())
    pos_in_reverse = {node: (max_x - x, y) for node, (x, y) in pos_in.items()}
    pos_out_shifting = {node: (x + max_x, y) for node, (x, y) in pos_out.items()}

    merged_dict = pos_in_reverse.copy()
    for key, value in pos_out_shifting.items():
        if key in merged_dict:
            if key == root_node_outbound.name:
                merged_dict[key] = value if value[1] > merged_dict[key][1] else merged_dict[key]
            else:
                merged_dict[key] = value
        else:
            merged_dict[key] = value

    pos_E2E = merged_dict

    return pos_E2E











if __name__ == "__main__":

    # Example usage
    example_tree = {
        "root": ["child1", "child2"],
        "child1": ["child1_1", "child1_2"],
        "child2": ["child2_1"]
    }

    root_node = build_tree_from_dict(example_tree)
    root_node.print_tree()


