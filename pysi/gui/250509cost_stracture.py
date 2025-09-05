#250509cost_stracture.py

def make_stack_bar4cost_stracture(cost_dict):
    attributes_B = [
        'cs_direct_materials_costs',
        'cs_marketing_promotion',
        'cs_sales_admin_cost',
        'cs_tax_portion',
        'cs_logistics_costs',
        'cs_warehouse_cost',
        'cs_prod_indirect_labor',
        'cs_prod_indirect_others',
        'cs_direct_labor_costs',
        'cs_depreciation_others',
        'cs_profit',
    ]

    colors = {
        'cs_direct_materials_costs': 'lightgray',
        'cs_marketing_promotion': 'darkblue',
        'cs_sales_admin_cost': 'blue',
        'cs_tax_portion': 'gray',
        'cs_logistics_costs': 'cyan',
        'cs_warehouse_cost': 'magenta',
        'cs_prod_indirect_labor': 'green',
        'cs_prod_indirect_others': 'lightgreen',
        'cs_direct_labor_costs': 'limegreen',
        'cs_depreciation_others': 'yellowgreen',
        'cs_profit': 'gold',
    }

    nodes = list(cost_dict.keys())
    bar_width = 0.3  

    plt.close('all')  # 🔴【追加】過去のグラフをすべて閉じる

    # 画面サイズを取得 (PCの解像度)
    root = tk.Tk()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.destroy()

    # 縦2つに並べるためのウィンドウサイズ (フルサイズの半分)
    win_width = screen_width
    win_height = screen_height // 2  

    # 🔴【修正】ウィンドウサイズを大きく
    fig, ax = plt.subplots(figsize=(12, 6), dpi=100)  

    # 🔴【修正】bottoms を適切に初期化 (ゼロ配列)
    bottoms = np.zeros(len(nodes))

    for attr in attributes_B:
        values = [cost_dict[node][attr] for node in cost_dict]
        ax.bar(nodes, values, bar_width, label=attr, color=colors[attr], bottom=bottoms)
        bottoms += values  

        # Add text on bars
        for i, value in enumerate(values):
            if value > 0:
                ax.text(i, bottoms[i] - value / 2, f'{value:.1f}', ha='center', va='center', fontsize=6, color='black')

    # Add total values on top of bars
    total_values = [sum(cost_dict[node][attr] for attr in attributes_B) for node in cost_dict]
    for i, total in enumerate(total_values):
        ax.text(i, total + 2, f'{total:.1f}', ha='center', va='bottom', fontsize=6)

    ax.set_title('Supply Chain Cost Structure', fontsize=10)  
    ax.set_xlabel('Node', fontsize=8)  
    ax.set_ylabel('Amount', fontsize=8)

    # 凡例を左上に配置
    ax.legend(title='Attribute', fontsize=6, loc='upper left')

    # X軸ラベルを回転
    ax.set_xticks(range(len(nodes)))
    ax.set_xticklabels(nodes, rotation=30, fontsize=7)  

    # 余白調整
    fig.subplots_adjust(left=0.2, right=0.85, top=0.9, bottom=0.3)

    # 🔴【修正】ウィンドウを画面下半分に移動
    mng = plt.get_current_fig_manager()
    
    #try:
    #    # Windows/macOS (TkAgg)
    #    mng.window.geometry(f"{win_width}x{win_height}+0+{win_height}")  
    #except AttributeError:
    #    # Linux (Qt5Agg)
    #    mng.window.setGeometry(0, win_height, win_width, win_height)




    plt.show()



    # viewing Cost Stracture / an image of Value Chain
    def show_cost_stracture_bar_graph(self):
        try:
            if self.root_node_outbound is None or self.root_node_inbound is None:
                raise ValueError("Data has not been loaded yet")
            
            self.show_nodes_cs_lot_G_Sales_Procure(self.root_node_outbound, self.root_node_inbound)
        
        except ValueError as ve:
            print(f"error: {ve}")
            tk.messagebox.showerror("error", str(ve))
        
        except AttributeError:
            print("Error: Required attributes are missing from the node. Please check if the data is loaded.")
            tk.messagebox.showerror("Error", "Required attributes are missing from the node. Please check if the data is loaded.")
        
        except Exception as e:
            print(f"An unexpected error has occurred: {e}")
            tk.messagebox.showerror("Error", f"An unexpected error has occurred: {e}")




    def show_nodes_cs_lot_G_Sales_Procure(self, root_node_outbound, root_node_inbound):
        attributes = [
            'cs_direct_materials_costs',
            'cs_marketing_promotion',
            'cs_sales_admin_cost',
            'cs_tax_portion',
            'cs_logistics_costs',
            'cs_warehouse_cost',
            'cs_prod_indirect_labor',
            'cs_prod_indirect_others',
            'cs_direct_labor_costs',
            'cs_depreciation_others',
            'cs_profit',
        ]

        def dump_node_amt_all_in(node, node_amt_all):
            for child in node.children:
                dump_node_amt_all_in(child, node_amt_all)
            amt_list = {attr: getattr(node, attr) for attr in attributes}
            if node.name == "JPN":
                node_amt_all["JPN_IN"] = amt_list
            else:
                node_amt_all[node.name] = amt_list
            return node_amt_all

        def dump_node_amt_all_out(node, node_amt_all):
            amt_list = {attr: getattr(node, attr) for attr in attributes}
            if node.name == "JPN":
                node_amt_all["JPN_OUT"] = amt_list
            else:
                node_amt_all[node.name] = amt_list
            for child in node.children:
                dump_node_amt_all_out(child, node_amt_all)
            return node_amt_all

        node_amt_sum_in = dump_node_amt_all_in(root_node_inbound, {})
        node_amt_sum_out = dump_node_amt_all_out(root_node_outbound, {})
        node_amt_sum_in_out = {**node_amt_sum_in, **node_amt_sum_out}

        print("node_amt_sum_out", node_amt_sum_out)

        make_stack_bar4cost_stracture(node_amt_sum_out)

        # CSVファイルへのエクスポートを呼び出す
        self.export_cost_structure_to_csv(root_node_outbound, root_node_inbound, "cost_structure.csv")



    def export_cost_structure_to_csv(self, root_node_outbound, root_node_inbound, file_path):
        attributes = [
            'cs_direct_materials_costs',
            'cs_marketing_promotion',
            'cs_sales_admin_cost',
            'cs_tax_portion',
            'cs_logistics_costs',
            'cs_warehouse_cost',
            'cs_prod_indirect_labor',
            'cs_prod_indirect_others',
            'cs_direct_labor_costs',
            'cs_depreciation_others',
            'cs_profit',
        ]

        def dump_node_amt_all_in(node, node_amt_all):
            for child in node.children:
                dump_node_amt_all_in(child, node_amt_all)
            amt_list = {attr: getattr(node, attr) for attr in attributes}
            if node.name == "JPN":
                node_amt_all["JPN_IN"] = amt_list
            else:
                node_amt_all[node.name] = amt_list
            return node_amt_all

        def dump_node_amt_all_out(node, node_amt_all):
            amt_list = {attr: getattr(node, attr) for attr in attributes}
            if node.name == "JPN":
                node_amt_all["JPN_OUT"] = amt_list
            else:
                node_amt_all[node.name] = amt_list
            for child in node.children:
                dump_node_amt_all_out(child, node_amt_all)
            return node_amt_all

        node_amt_sum_in = dump_node_amt_all_in(root_node_inbound, {})
        node_amt_sum_out = dump_node_amt_all_out(root_node_outbound, {})
        node_amt_sum_in_out = {**node_amt_sum_in, **node_amt_sum_out}

        # 横持ちでデータフレームを作成
        data = []
        for node_name, costs in node_amt_sum_in_out.items():
            row = [node_name] + [costs[attr] for attr in attributes]
            data.append(row)

        df = pd.DataFrame(data, columns=["node_name"] + attributes)

        # CSVファイルにエクスポート
        df.to_csv(file_path, index=False)
        print(f"Cost structure exported to {file_path}")

        # leaf_nodes list is this
        print(self.leaf_nodes_out)


