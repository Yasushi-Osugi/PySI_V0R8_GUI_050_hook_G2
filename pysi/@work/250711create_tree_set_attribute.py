#250711create_tree_set_attribute.py


# 2パス構成（Node構築 → SKU登録）
# 3フェーズ
# 1. ノードの重複作成を防ぐ
# 2. ツリー構造を先に正しくつなぐ
# 3. SKUは行ごとに追加可能にする（同じNode名が複数回出てきても問題ない

def create_tree_set_attribute(file_name):
    """
    Create a supply chain tree and set attributes, supporting multiple SKU per node.

    Parameters:
        file_name (str): Path to the tree file.

    Returns:
        tuple[dict, str]: Dictionary of Node instances and the root node name.
    """
    from collections import defaultdict

    width_tracker = defaultdict(int)
    root_node_name = ""

    rows = read_tree_file(file_name)
    nodes = {}

    # Phase 1: Create all nodes
    for row in rows:
        child_name = row["Child_node"]
        parent_name = row["Parent_node"]

        if child_name not in nodes:
            nodes[child_name] = Node(child_name)

        if parent_name != "root" and parent_name not in nodes:
            nodes[parent_name] = Node(parent_name)

    # Phase 2: Link tree structure
    for row in rows:
        parent_name = row["Parent_node"]
        child_name = row["Child_node"]
        if parent_name == "root":
            root_node_name = child_name
            nodes[root_node_name].width += 4
        else:
            parent = nodes[parent_name]
            child = nodes[child_name]
            parent.add_child(child)
            child.set_attributes(row)

    # Phase 3: Register SKUs (multiple SKUs per Node)
    for row in rows:
        child_name = row["Child_node"]
        if "product_name" in row and row["product_name"]:
            nodes[child_name].add_sku(row["product_name"])

    return nodes, root_node_name







class Node:
    def __init__(self, name: str):
        self.name = name
        self.children: List['Node'] = []
        self.parent: Optional['Node'] = None

        self.depth = 0
        self.width = 0
        self.longitude = None
        self.latitude = None

        # SKU linkage
        self.sku_dict = {}  # product_name → SKU instance

    def add_sku(self, product_name: str):
        sku = SKU(product_name, self.name)
        self.sku_dict[product_name] = sku
        return sku


class SKU: 
    def __init__(self, product_name, node_name):
        self.product_name = product_name
        self.node_name = node_name


# ********************************************************************

以下のpython codeは、添付のcsv fileを読み込んでnode treeをcreateする定義です。今回、ckass Node(self, node_naame): と別にclass SKU(self,  node_name, product_name)を追加する機能拡張を行っていきたいのですが、a_new_node = Node(node_name)をinstanceした後、sku=SKU(node_name, product_name)は、どのようにinstancateを定義すれば良いですか? ここで、SKU()のclass定義は''' class SKU: 
    def __init__(self, product_name, node_name):
        self.product_name = product_name
        self.node_name = node_name
 '''とするとともに、Node()ではskuとのlinkadge定義を辞書"self.sku_dict = {}  # product_name 2 SKU"でclass Node()に定義しています。''' class Node: 
    def __init__(self, name: str):
        self.name = name
        self.children: List['Node'] = []
        self.parent: Optional['Node'] = None

        # node position on network
        self.depth = 0
        self.width = 0


        # Geographic Position
        self.longitude = None
        self.latitude  = None  



        # *******************
        # SKU linkage
        # *******************
        self.sku_dict = {}  # product_name 2 SKU
 '''のとおり、各nodeにおいてproduct_nameをkeyに辞書でskuを指すpointorを定義します。 # ****        def load_data_files(self): 
        directory = filedialog.askdirectory(title="Select Data Directory")

        if directory:
            try:
                self.lot_size = int(self.lot_size_entry.get())
                self.plan_year_st = int(self.plan_year_entry.get())
                self.plan_range = int(self.plan_range_entry.get())
            except ValueError:
                print("Invalid input for lot size, plan year start, or plan range. Using default values.")

            self.outbound_data = []
            self.inbound_data = []

            data_file_list = os.listdir(directory)

            print("data_file_list", data_file_list)

            self.directory = directory
            self.load_directory = directory


            # --- Loading Tree Structures ---
            if "product_tree_outbound.csv" in data_file_list:
                file_path = os.path.join(directory, "product_tree_outbound.csv")
                nodes_outbound, root_node_name_out = create_tree_set_attribute(file_path)
                root_node_outbound = nodes_outbound[root_node_name_out]

                def make_leaf_nodes(node, leaf_list):
                    if not node.children:
                        leaf_list.append(node.name)
                    for child in node.children:
                        make_leaf_nodes(child, leaf_list)
                    return leaf_list

                leaf_nodes_out = make_leaf_nodes(root_node_outbound, [])
                self.nodes_outbound = nodes_outbound
                self.root_node_outbound = root_node_outbound
                self.leaf_nodes_out = leaf_nodes_out
                set_positions(root_node_outbound)
                set_parent_all(root_node_outbound)
                print_parent_all(root_node_outbound)




def create_tree_set_attribute(file_name):
    """
    Create a supply chain tree and set attributes.

    Parameters:
        file_name (str): Path to the tree file.

    Returns:
        tuple[dict, str]: Dictionary of Node instances and the root node name.
    """
    width_tracker = defaultdict(int)
    root_node_name = ""

    # Read the tree file
    rows = read_tree_file(file_name)
    nodes = {row["child_node_name"]: Node(row["child_node_name"]) for row in rows}

    for row in rows:
        if row["Parent_node"] == "root":
            root_node_name = row["Child_node"]
            root = nodes[root_node_name]
            root.width += 4
        else:
            parent = nodes[row["Parent_node"]]
            child = nodes[row["Child_node"]]
            parent.add_child(child)
            child.set_attributes(row)

    return nodes, root_node_name







# ********************************************************************


    def load_data_files(self):
        directory = filedialog.askdirectory(title="Select Data Directory")

        if directory:
            try:
                self.lot_size = int(self.lot_size_entry.get())
                self.plan_year_st = int(self.plan_year_entry.get())
                self.plan_range = int(self.plan_range_entry.get())
            except ValueError:
                print("Invalid input for lot size, plan year start, or plan range. Using default values.")

            self.outbound_data = []
            self.inbound_data = []

            data_file_list = os.listdir(directory)

            print("data_file_list", data_file_list)

            self.directory = directory
            self.load_directory = directory


            # --- Loading Tree Structures ---
            if "product_tree_outbound.csv" in data_file_list:
                file_path = os.path.join(directory, "product_tree_outbound.csv")
                nodes_outbound, root_node_name_out = create_tree_set_attribute(file_path)
                root_node_outbound = nodes_outbound[root_node_name_out]

                def make_leaf_nodes(node, leaf_list):
                    if not node.children:
                        leaf_list.append(node.name)
                    for child in node.children:
                        make_leaf_nodes(child, leaf_list)
                    return leaf_list

                leaf_nodes_out = make_leaf_nodes(root_node_outbound, [])
                self.nodes_outbound = nodes_outbound
                self.root_node_outbound = root_node_outbound
                self.leaf_nodes_out = leaf_nodes_out
                set_positions(root_node_outbound)
                set_parent_all(root_node_outbound)
                print_parent_all(root_node_outbound)




def create_tree_set_attribute(file_name):
    """
    Create a supply chain tree and set attributes.

    Parameters:
        file_name (str): Path to the tree file.

    Returns:
        tuple[dict, str]: Dictionary of Node instances and the root node name.
    """
    width_tracker = defaultdict(int)
    root_node_name = ""

    # Read the tree file
    rows = read_tree_file(file_name)
    nodes = {row["child_node_name"]: Node(row["child_node_name"]) for row in rows}

    for row in rows:
        if row["Parent_node"] == "root":
            root_node_name = row["Child_node"]
            root = nodes[root_node_name]
            root.width += 4
        else:
            parent = nodes[row["Parent_node"]]
            child = nodes[row["Child_node"]]
            parent.add_child(child)
            child.set_attributes(row)

    return nodes, root_node_name




