run_price_and_cost_propagation.py


# evaluate_cost_models.py

# ✅ 関税率取得関数（from_node → to_node の関係に基づく）
def get_tariff_rate(product_name, from_node_name, to_node_name, tariff_table):
    return tariff_table.get((product_name, from_node_name, to_node_name), 0.0)


# ✅ Outbound価格逆算用：下流ノードから上流へ価格を逆伝播（関税対応あり）
def evaluate_outbound_price(leaf_node, product_name, tariff_table):
    """
    outboundノード（最終需要側）から上流に向かって価格を逆算し、出荷価格を算出する。
    関税（仕向け国が課す場合）を含めて価格逆算。
    """
    def back_propagate(node):
        sku = node.sku

        if not node.children:
            if not sku.price or sku.price <= 0:
                raise ValueError(f"{node.name}: 最終ノードに価格が設定されていません")
            return sku.price

        child_prices = []
        for child in node.children:
            downstream_price = back_propagate(child)

            # outbound関税の計算（リンクベース）
            tariff_rate = get_tariff_rate(product_name, node.name, child.name, tariff_table)
            sku.tariff_cost = tariff_rate * downstream_price

            price_here = downstream_price - (
                sku.transport_cost +
                sku.storage_cost +
                sku.tariff_cost +
                sku.fixed_cost +
                sku.other_cost
            )
            child_prices.append(price_here)

        sku.price = sum(child_prices) / len(child_prices)
        return sku.price

    back_propagate(leaf_node)


def evaluate_outbound_price_all(leaf_nodes, product_name, tariff_table):
    """
    与えられたすべての leaf_node に対して価格逆算処理を実施。
    """
    for leaf in leaf_nodes:
        evaluate_outbound_price(leaf, product_name, tariff_table)


# ✅ Inboundコスト構成展開用：上流ノードから下流へコスト伝播（関税対応あり）
def evaluate_inbound_cost(root_node, product_name, tariff_table):
    """
    inboundノード（root_node_inbound）から下流（部材・素材）へコスト構成を伝播する。
    関税（仕入価格に対する）をtotal_costに加算。
    """
    def forward_propagate(node):
        sku = node.sku

        if node.parent:
            sku.purchase_price = node.parent.sku.price
            tariff_rate = get_tariff_rate(product_name, node.parent.name, node.name, tariff_table)
            sku.tariff_cost = tariff_rate * sku.purchase_price
        else:
            sku.purchase_price = 0
            sku.tariff_cost = 0

        sku.total_cost = (
            sku.purchase_price +
            sku.transport_cost +
            sku.storage_cost +
            sku.tariff_cost +
            sku.fixed_cost +
            sku.other_cost
        )

        if not sku.price or sku.price <= 0:
            margin_rate = getattr(sku, "profit_margin", 0.05)
            sku.price = sku.total_cost * (1 + margin_rate)

        for child in node.children:
            forward_propagate(child)

    forward_propagate(root_node)


# ✅ Leaf Node探索関数（汎用）
def find_leaf_nodes(root_node):
    leaf_nodes = []
    def traverse(node):
        if not node.children:
            leaf_nodes.append(node)
        else:
            for child in node.children:
                traverse(child)
    traverse(root_node)
    return leaf_nodes


tariff_table = load_tariff_table_from_csv(os.path.join(directory, "tariff_table.csv"))


tariff_table = {
    ("CAL_RICE_1", "DADCAL", "WS1CAL"): 0.03,
    ("CAL_RICE_1", "WS1CAL", "RT_CAL"): 0.00,
    ("CAL_RICE_1", "RT_CAL", "CS_CAL"): 0.00,
    ("JPN_RICE_1", "DADJPN", "WS1JPN"): 0.05,
    ("JPN_RICE_1", "WS1JPN", "RT_JPN"): 0.00,
    ("JPN_RICE_1", "RT_JPN", "CS_JPN"): 0.00,
    ("Reserv_Rice", "DADGSJP", "GR_CS_JPN"): 0.10,
}


# ✅ 全商品一括実行関数（outbound + inbound）
def run_price_and_cost_propagation(product_tree_dict, tariff_table):
    for product_name, tree in product_tree_dict.items():
        leaf_nodes = find_leaf_nodes(tree.root_node_outbound)
        evaluate_outbound_price_all(leaf_nodes, product_name, tariff_table)
        evaluate_inbound_cost(tree.root_node_inbound, product_name, tariff_table)




# 呼び出し例
evaluate_outbound_price_all(
    leaf_nodes=product_tree_dict["CAL_RICE_1"].leaf_nodes,
    product_name="CAL_RICE_1",
    tariff_table=tariff_table
)


# a sample of "tariff_tabble.csv"
product_name,from_node,to_node,tariff_rate
CAL_RICE_1,DADCAL,WS1CAL,0.03
CAL_RICE_1,WS1CAL,RT_CAL,0.00
CAL_RICE_1,RT_CAL,CS_CAL,0.00
JPN_RICE_1,DADJPN,WS1JPN,0.05
JPN_RICE_1,WS1JPN,RT_JPN,0.00
JPN_RICE_1,RT_JPN,CS_JPN,0.00
Reserv_Rice,DADGSJP,GR_CS_JPN,0.10


def load_tariff_table_from_csv(filepath):
    import csv
    tariff_table = {}
    with open(filepath, newline='', encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (
                row["product_name"].strip(),
                row["from_node"].strip(),
                row["to_node"].strip()
            )
            tariff_table[key] = float(row["tariff_rate"])
    return tariff_table


tariff_table = load_tariff_table_from_csv(os.path.join(directory, "tariff_table.csv"))

run_price_and_cost_propagation(product_tree_dict, tariff_table)


