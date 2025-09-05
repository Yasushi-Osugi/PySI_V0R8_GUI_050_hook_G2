#evaluate_price_TOBE.py

def evaluate_price_TOBE(leaf_node, product_name, tariff_table):
    node = leaf_node
    print(f"[TOBE Init] Leaf {node.name} offering_price = {node.cs_offering_price:.2f}")

    while node.parent:
        child = node
        node = node.parent

        child_price = child.cs_offering_price

        # 関税率を取得
        tariff_rate = get_tariff_rate(product_name, node.name, child.name, tariff_table)
        node.cs_tariff_rate = tariff_rate

        # その他のコスト合計
        other_costs = (
            node.cs_logistics_costs +
            node.cs_warehouse_cost +
            node.cs_fixed_cost +
            node.cs_profit
        )

        # offering_priceを関税込みで割り戻す
        node.cs_offering_price = (child_price - other_costs) / (1 + tariff_rate)

        # 関税コストを改めて算出
        node.cs_tariff_cost = tariff_rate * node.cs_offering_price

        print(f"[TOBE] {node.name} -> {child.name} : offering_price = {node.cs_offering_price:.2f}")

