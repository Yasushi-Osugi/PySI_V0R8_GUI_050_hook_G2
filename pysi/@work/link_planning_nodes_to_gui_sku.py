link_planning_nodes_to_gui_sku.py


#設計項目       	内容
#plan_node.name 	GUIと計算ノードの一致キーは "Node.name"
#gui_node_dict[name]	GUI上の全ノードを辞書化しておく必要あり
#sku_dict[product_name]	GUI上のSKU単位で .psi_node_ref をセット
#psi_node_ref   	計算結果(PSI/Costなど)を直接参照するポインタとして使う


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
                sku.psi_node_ref = plan_node  # ← 計算ノードへのリンク
        for child in plan_node.children:
            traverse_and_link(child)

    traverse_and_link(product_tree_root)




for product_name in product_tree_dict:
    link_planning_nodes_to_gui_sku(
        product_tree_dict[product_name],
        gui_node_dict,
        product_name
    )



def on_node_click(gui_node, product_name):
    sku = gui_node.sku_dict.get(product_name)
    if sku and sku.psi_node_ref:
        plan_node = sku.psi_node_ref
        print("PSI Demand:", plan_node.sku.psi4demand)
        print("PSI Supply:", plan_node.sku.psi4supply)
        print("Cost:", plan_node.sku.cost)



