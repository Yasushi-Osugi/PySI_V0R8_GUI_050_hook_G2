build_product_tree_from_csv.py

class Node:
    def __init__(self, name):
        self.name = name
        self.parent = None
        self.children = []
        self.lot_size = None
        self.leadtime = None
        self.sku = None  # ← planning用SKU（このNodeが属するproductのみに使う）

    def add_child(self, child):
        self.children.append(child)


def build_product_tree_from_csv(csv_data, product_name):
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
        child.sku = SKU()  # ← PSI計算後にpsi4demandなどを持たせる
        child.parent = parent
        parent.add_child(child)

    return node_dict["supply_point"]  # root node


product_tree_dict = {}
for product in product_list:
    product_tree_dict[product] = build_product_tree_from_csv(csv_data, product)


