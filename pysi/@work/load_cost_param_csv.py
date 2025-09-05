#load_cost_param_csv.py

## ✅ 2. `.cost_details` 構造の導入例（SKUクラス）

class SKU:
    def __init__(self):
        self.price = 0
        self.transport_cost = 0
        self.storage_cost = 0

        sku.tariff_cost = 0

        self.purchase_price = 0
        self.fixed_cost = 0
        self.other_cost = 0
        self.cost_details = {}  # ← ここが詳細構造！

        self.total_cost = 0
        self.revenue = 0
        self.profit = 0
        self.demand = 0



def load_cost_param_csv(filepath):
    import csv

    param_dict = {}

    with open(filepath, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
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
    cost_param_setter(product_tree_dict[product_name], param_dict, product_name)


```

### ✅ コスト詳細の設定例（cost\_param\_setter内などで）

```python
sku.cost_details = {
    "sales_admin": float(row.get("sales_admin_cost", 0)),
    "marketing": float(row.get("marketing_promotion", 0)),
    "direct_labor": float(row.get("direct_labor_costs", 0)),
    "depreciation": float(row.get("depreciation_others", 0)),
    "manufacturing_overhead": float(row.get("manufacturing_overhead", 0))
}

# other_cost に集約
sku.other_cost = sum(sku.cost_details.values())

