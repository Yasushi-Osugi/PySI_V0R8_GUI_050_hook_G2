#evaluate_cost_models.py

# ✅ Outbound価格逆算用：下流ノードから上流へ価格を逆伝播

def evaluate_outbound_price(leaf_node):
    """
    outboundノード（最終需要側）から上流に向かって価格を逆算し、出荷価格を算出する。
    例: consumer → retailer → wholesaler → DADxxx
    """
    def back_propagate(node):
        sku = node.sku

        # 最終ノードの価格が直接指定されていることを前提とする
        if not node.children:
            if not sku.price or sku.price <= 0:
                raise ValueError(f"{node.name}: 最終ノードに価格が設定されていません")
            return sku.price

        child_prices = []
        for child in node.children:
            downstream_price = back_propagate(child)
            price_here = downstream_price - (
                sku.transport_cost +
                sku.storage_cost +
                sku.tariff_rate * downstream_price +
                sku.fixed_cost
            )
            child_prices.append(price_here)

        sku.price = sum(child_prices) / len(child_prices)
        return sku.price

    back_propagate(leaf_node)


# ✅ Inboundコスト構成展開用：上流ノードから下流へコスト伝播

def evaluate_inbound_cost(root_node):
    """
    inboundノード（root_node_outbound）から下流（部材・素材）へコスト構成を伝播する。
    """
    def forward_propagate(node):
        sku = node.sku

        if node.parent:
            sku.purchase_price = node.parent.sku.price
        else:
            sku.purchase_price = 0

        sku.total_cost = (
            sku.purchase_price +
            sku.transport_cost +
            sku.storage_cost +
            sku.tariff_rate * sku.purchase_price +
            sku.fixed_cost
        )

        if not sku.price or sku.price <= 0:
            margin_rate = getattr(sku, "profit_margin", 0.05)
            sku.price = sku.total_cost * (1 + margin_rate)

        for child in node.children:
            forward_propagate(child)

    forward_propagate(root_node)

