#evaluate_cost_models_tariff.py


# *************************************************************

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



# ************************************************************
# 最新 tariff対応
# leaf_nodes対応


# evaluate_cost_models.py

# ✅ Outbound価格逆算用：下流ノードから上流へ価格を逆伝播（関税対応あり）

def evaluate_outbound_price(leaf_node):
    """
    outboundノード（最終需要側）から上流に向かって価格を逆算し、出荷価格を算出する。
    関税（仕向け国が課す場合）を含めて価格逆算。
    例: consumer → retailer → wholesaler → DADxxx
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

            # outbound関税の計算
            sku.tariff_cost = sku.tariff_rate * downstream_price

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


def evaluate_outbound_price_all(leaf_nodes):
    """
    与えられたすべての leaf_node に対して価格逆算処理を実施。
    """
    for leaf in leaf_nodes:
        evaluate_outbound_price(leaf)


# ✅ Inboundコスト構成展開用：上流ノードから下流へコスト伝播（関税対応あり）

def evaluate_inbound_cost(root_node):
    """
    inboundノード（root_node_inbound）から下流（部材・素材）へコスト構成を伝播する。
    関税（仕入価格に対する）をtotal_costに加算。
    """
    def forward_propagate(node):
        sku = node.sku

        if node.parent:
            sku.purchase_price = node.parent.sku.price
        else:
            sku.purchase_price = 0

        sku.tariff_cost = sku.tariff_rate * sku.purchase_price

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



# ************************************************************


# evaluate_cost_models.py

# ✅ Outbound価格逆算用：下流ノードから上流へ価格を逆伝播（関税対応あり）

def evaluate_outbound_price(leaf_node):
    """
    outboundノード（最終需要側）から上流に向かって価格を逆算し、出荷価格を算出する。
    関税（仕向け国が課す場合）を含めて価格逆算。
    例: consumer → retailer → wholesaler → DADxxx
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

            # outbound関税の計算
            sku.tariff_cost = sku.tariff_rate * downstream_price

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


def evaluate_outbound_price_all_leaves(root_node):
    """
    outboundツリーの全leafノードから価格逆算を実施。
    複数チャネルがある場合でも全てのleafから遡る。
    """
    def get_leaves(node):
        leaves = []
        def traverse(n):
            if not n.children:
                leaves.append(n)
            for c in n.children:
                traverse(c)
        traverse(node)
        return leaves

    leaves = get_leaves(root_node)
    for leaf in leaves:
        evaluate_outbound_price(leaf)


# ✅ Inboundコスト構成展開用：上流ノードから下流へコスト伝播（関税対応あり）

def evaluate_inbound_cost(root_node):
    """
    inboundノード（root_node_inbound）から下流（部材・素材）へコスト構成を伝播する。
    関税（仕入価格に対する）をtotal_costに加算。
    """
    def forward_propagate(node):
        sku = node.sku

        if node.parent:
            sku.purchase_price = node.parent.sku.price
        else:
            sku.purchase_price = 0

        sku.tariff_cost = sku.tariff_rate * sku.purchase_price

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


# ************************************************************


# Pythonコード側の属性
#--------------------
#price              
#transport_cost     
#storage_cost      
#purchase_price     

#tariff_cost

#fixed_cost         
#other_cost


# evaluate_cost_models.py

# ✅ Outbound価格逆算用：下流ノードから上流へ価格を逆伝播（関税対応あり）

def evaluate_outbound_price(leaf_node):
    """
    outboundノード（最終需要側）から上流に向かって価格を逆算し、出荷価格を算出する。
    関税（仕向け国が課す場合）を含めて価格逆算。
    例: consumer → retailer → wholesaler → DADxxx
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

            # outbound関税の計算
            sku.tariff_cost = sku.tariff_rate * downstream_price

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


# ✅ Inboundコスト構成展開用：上流ノードから下流へコスト伝播（関税対応あり）

def evaluate_inbound_cost(root_node):
    """
    inboundノード（root_node_inbound）から下流（部材・素材）へコスト構成を伝播する。
    関税（仕入価格に対する）をtotal_costに加算。
    """
    def forward_propagate(node):
        sku = node.sku

        if node.parent:
            sku.purchase_price = node.parent.sku.price
        else:
            sku.purchase_price = 0

        sku.tariff_cost = sku.tariff_rate * sku.purchase_price

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



