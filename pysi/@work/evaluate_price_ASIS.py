evaluate_price_ASIS.py


# --------------------------------------------
# outbound supplychain 上流 -> 下流へ価格積上げ（RootからLearへ）
# --------------------------------------------
def evaluate_price_ASIS(root_node, product_name, tariff_table):

    node = leaf_node

    print(f"[TOBE Init] Leaf {node.name} offering_price = {node.offering_price_TOBE:.2f}")

    while node.parent:

        #child = node
        #node = node.parent
        parent = node.parent

        #child_price = child.offering_price_TOBE
        node_price = node.offering_price_TOBE

        # 関税率を取得
        #tariff_rate = get_tariff_rate(product_name, node.name, child.name, tariff_table)
        tariff_rate = get_tariff_rate(product_name, parent.name, node.name, tariff_table)
        node.cs_tariff_rate = tariff_rate

        # その他のコスト合計
        other_costs = (
            node.cs_logistics_costs +
            node.cs_warehouse_cost +
            node.cs_fixed_cost +
            node.cs_profit
        )

        # offering_priceを関税込みで割り戻す
        #node.offering_price_TOBE = (child_price - other_costs) / (1 + tariff_rate)
        parent.offering_price_TOBE = (node_price - other_costs) / (1 + tariff_rate)

        # 関税コストを改めて算出
        node.cs_tariff_cost = tariff_rate * node.offering_price_TOBE

        print(f"[TOBE] {parent.name} -> {node.name} : offering_price = {node.offering_price_TOBE:.2f}")

        node = parent





# --------------------------------------------
# 下流 -> 上流へ価格逆算（LeafからRootへ）
# --------------------------------------------
def evaluate_price_TOBE(leaf_node, product_name, tariff_table):
    node = leaf_node
    print(f"[TOBE Init] Leaf {node.name} offering_price = {node.offering_price_TOBE:.2f}")

    while node.parent:

        #child = node
        #node = node.parent
        parent = node.parent

        #child_price = child.offering_price_TOBE
        node_price = node.offering_price_TOBE

        # 関税率を取得
        #tariff_rate = get_tariff_rate(product_name, node.name, child.name, tariff_table)
        tariff_rate = get_tariff_rate(product_name, parent.name, node.name, tariff_table)
        node.cs_tariff_rate = tariff_rate

        # その他のコスト合計
        other_costs = (
            node.cs_logistics_costs +
            node.cs_warehouse_cost +
            node.cs_fixed_cost +
            node.cs_profit
        )

        # offering_priceを関税込みで割り戻す
        #node.offering_price_TOBE = (child_price - other_costs) / (1 + tariff_rate)
        parent.offering_price_TOBE = (node_price - other_costs) / (1 + tariff_rate)

        # 関税コストを改めて算出
        node.cs_tariff_cost = tariff_rate * node.offering_price_TOBE

        print(f"[TOBE] {parent.name} -> {node.name} : offering_price = {node.offering_price_TOBE:.2f}")

        node = parent
