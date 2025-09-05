# evaluate_cost_models.py

#呼び出し
#from evaluate_cost_models import gui_run_initial_propagation
#
## データディレクトリと product_tree_dict をもとに初期伝播を実施
#gui_run_initial_propagation(product_tree_dict, directory)


#import csv
#import json
#import os
#import tkinter as tk
#from tkinter import filedialog, messagebox

# ✅ 関税率取得関数（from_node → to_node の関係に基づく）
def get_tariff_rate(product_name, from_node_name, to_node_name, tariff_table):
    return tariff_table.get((product_name, from_node_name, to_node_name), 0.0)


# ✅ Outbound価格逆算用：下流ノードから上流へ価格を逆伝播（関税対応あり）
def evaluate_outbound_price(leaf_node, product_name, tariff_table):
    def back_propagate(node):
        sku = node.sku

        if not node.children:
            if not sku.price or sku.price <= 0:
                raise ValueError(f"{node.name}: 最終ノードに価格が設定されていません")
            return sku.price

        child_prices = []
        for child in node.children:
            downstream_price = back_propagate(child)
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
        print("sku.price = sum(child_prices) / len(child_prices)", sku.price, child_prices, len(child_prices))
        return sku.price

    back_propagate(leaf_node)


def evaluate_outbound_price_all(leaf_nodes, product_name, tariff_table):
    for leaf in leaf_nodes:
        evaluate_outbound_price(leaf, product_name, tariff_table)


# ✅ Inboundコスト構成展開用：上流ノードから下流へコスト伝播（関税対応あり）
def evaluate_inbound_cost(root_node, product_name, tariff_table):
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


# ✅ Tariff Table CSV 読み込み

def load_tariff_table_from_csv(filepath):
    tariff_table = {}
    with open(filepath, newline='', encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["product_name"].strip(), row["from_node"].strip(), row["to_node"].strip())
            tariff_table[key] = float(row["tariff_rate"])
    return tariff_table


# ✅ 全商品一括実行関数（outbound + inbound）
def run_price_and_cost_propagation(product_tree_dict, tariff_table):
    for product_name, tree in product_tree_dict.items():
        leaf_nodes = find_leaf_nodes(tree.root_node_outbound)
        evaluate_outbound_price_all(leaf_nodes, product_name, tariff_table)
        evaluate_inbound_cost(tree.root_node_inbound, product_name, tariff_table)


# ✅ 結果出力（GUIボタン連携を想定、CSV出力）
def export_node_prices_and_costs(product_tree_dict, output_dir):
    output_path = os.path.join(output_dir, "price_cost_output.csv")
    with open(output_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "product_name", "node_name", "price", "total_cost", "purchase_price",
            "tariff_cost", "transport_cost", "storage_cost", "fixed_cost", "other_cost"
        ])
        for product_name, tree in product_tree_dict.items():
            def traverse(node):
                sku = node.sku
                writer.writerow([
                    product_name, node.name, sku.price, sku.total_cost, sku.purchase_price,
                    getattr(sku, "tariff_cost", 0), sku.transport_cost, sku.storage_cost,
                    sku.fixed_cost, getattr(sku, "other_cost", 0)
                ])
                for child in node.children:
                    traverse(child)
            traverse(tree)
            #@STOP
            #traverse(tree.root_node_inbound)
            #traverse(tree.root_node_outbound)


# ✅ GUIボタン用の実行関数

def gui_run_tariff_simulation(product_tree_dict):
    root = tk.Tk()
    root.withdraw()

    tariff_path = filedialog.askopenfilename(title="Select Tariff Table CSV")
    if not tariff_path:
        messagebox.showerror("Error", "Tariff CSV not selected.")
        return

    output_dir = filedialog.askdirectory(title="Select Output Directory")
    if not output_dir:
        messagebox.showerror("Error", "Output directory not selected.")
        return

    try:
        tariff_table = load_tariff_table_from_csv(tariff_path)
        run_price_and_cost_propagation(product_tree_dict, tariff_table)
        export_node_prices_and_costs(product_tree_dict, output_dir)
        messagebox.showinfo("Success", f"Price and cost propagation completed.\nOutput saved to: {output_dir}")
    except Exception as e:
        messagebox.showerror("Execution Failed", str(e))


# ✅ GUIファイルロード処理から初期コスト伝播を統合的に呼び出す（importして使用）
def gui_run_initial_propagation(product_tree_dict, data_dir):
    try:
        tariff_csv = os.path.join(data_dir, "tariff_table.csv")
        if os.path.exists(tariff_csv):
            tariff_table = load_tariff_table_from_csv(tariff_csv)
            print("tariff_table applied...", tariff_table)
        else:
            print("[Info] tariff_table.csv not found → 関税0%で処理")
            tariff_table = {}

        run_price_and_cost_propagation(product_tree_dict, tariff_table)
        print("[Info] 初期コスト伝播が完了しました")
    except Exception as e:
        print("[Error] 初期コスト伝播に失敗:", str(e))



def propagate_cost_to_plan_nodes(product_tree_dict):
    for product_name, tree in product_tree_dict.items():
        def traverse(node):
            sku = node.sku
            node.eval_cs_price_sales_shipped = getattr(sku, "price", 0)
            node.eval_cs_profit = getattr(sku, "profit", 0)
            node.eval_cs_SGA_total = getattr(sku, "SGA_total", 0)
            node.eval_cs_tax_portion = getattr(sku, "tariff_cost", 0)
            node.eval_cs_logistics_costs = getattr(sku, "transport_cost", 0)
            node.eval_cs_warehouse_cost = getattr(sku, "storage_cost", 0)
            node.eval_cs_direct_materials_costs = getattr(sku, "purchase_price", 0)
            for child in node.children:
                traverse(child)
        traverse(tree)

