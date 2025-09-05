#250710SKU_version



# 1 SKUクラス定義
from collections import defaultdict

class SKU:
    def __init__(self, product_name, node_name):
        self.product_name = product_name
        self.node_name = node_name
        self.psi_table = defaultdict(lambda: {"I": 0, "P": 0, "S": 0, "CO": 0})  # week単位



# 2 Nodeクラスの拡張
class Node:
    def __init__(self, node_name):
        self.node_name = node_name
        self.sku_dict = {}  # product_name → SKU

    def get_sku(self, product_name):
        return self.sku_dict[product_name]



# 3 load_data_files()（CSVファイル一式対応）
import csv

def load_data_files(file_path):
    """
    file_path: 1つの統合CSV (node,product,week,status,qty) を読み込む
    node_dict: グローバルに保持しておく Nodeインスタンスのdict
    """
    node_dict = {}

    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            node_name = row['node']
            product = row['product']
            week = row['week']
            status = row['status']  # 'I', 'P', 'S', 'CO'
            qty = int(row['qty'])

            if node_name not in node_dict:
                node_dict[node_name] = Node(node_name)
            node = node_dict[node_name]

            if product not in node.sku_dict:
                node.sku_dict[product] = SKU(product, node_name)
            sku = node.sku_dict[product]

            sku.psi_table[week][status] += qty

    return node_dict




# 4 GUI部品（Tkinter） - Node / Product選択とshow_psi
import tkinter as tk

def update_product_menu(*args):
    node = node_dict[selected_node.get()]
    product_menu['menu'].delete(0, 'end')
    for p in node.sku_dict:
        product_menu['menu'].add_command(label=p, command=tk._setit(selected_product, p))

def show_psi():
    node = node_dict[selected_node.get()]
    sku = node.get_sku(selected_product.get())
    for week in sorted(sku.psi_table):
        row = sku.psi_table[week]
        print(f"{week}: I={row['I']}, P={row['P']}, S={row['S']}, CO={row['CO']}")

# GUI要素
root = tk.Tk()

selected_node = tk.StringVar()
selected_product = tk.StringVar()

node_menu = tk.OptionMenu(root, selected_node, *node_dict.keys())
node_menu.pack()

product_menu = tk.OptionMenu(root, selected_product, "")
product_menu.pack()

selected_node.trace('w', update_product_menu)

btn = tk.Button(root, text="Show PSI", command=show_psi)
btn.pack()

root.mainloop()


