#price_setting.py

# TOBE価格（市場価格）をLeafノードにセット
def load_tobe_prices(filepath):
    tobe_price_dict = {}
    with open(filepath, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['leaf_node_name'].strip(), row['product_name'].strip())
            tobe_price_dict[key] = float(row['offering_price_TOBE'])
    return tobe_price_dict

def assign_tobe_prices_to_leaf_nodes(product_tree_dict, tobe_price_dict):
    for product_name, tree in product_tree_dict.items():
        leaf_nodes = find_leaf_nodes(tree)
        for leaf in leaf_nodes:
            key = (leaf.name.strip(), product_name.strip())
            if key in tobe_price_dict:

                leaf.offering_price_TOBE = tobe_price_dict[key]
                #leaf.cs_offering_price = tobe_price_dict[key]

                print(f"[Assign TOBE] {leaf.name} - {product_name} = {leaf.cs_offering_price}")
            else:
                print(f"[Warning] No TOBE price found for {key}")





#ASIS価格（出荷価格）をRootノードにセット
def load_asis_prices(filepath):
    asis_price_dict = {}
    with open(filepath, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['product_name'].strip(), row['DAD_node_name'].strip())
            asis_price_dict[key] = float(row['offering_price_ASIS'])
    return asis_price_dict

def assign_asis_prices_to_root_nodes(product_tree_dict, asis_price_dict):

    for product_name, tree in product_tree_dict.items():

        root = tree  # または tree.root_node_inbound

        for dad_node in asis_price_dict:

            if dad_node[0] == product_name:

                root.offering_price_ASIS = asis_price_dict[dad_node]
                #root.sku.price = asis_price_dict[dad_node]

                print(f"[Assign ASIS] {root.name} - {product_name} = {root.cs_offering_price_ASIS}")
                #print(f"[Assign ASIS] {root.name} - {product_name} = {root.sku.price}")



tobe_price_dict = load_tobe_prices(filepath)

assign_tobe_prices_to_leaf_nodes(product_tree_dict, tobe_price_dict)


asis_price_dict = load_asis_prices(filepath)

assign_asis_prices_to_root_nodes(product_tree_dict, asis_price_dict)
