#plugins/v7_tree_builder/plugin.py

def register(bus):
    from pysi.core.node_base import Node  # V0R7準拠のNode
    import csv, os

    def build_v7(root, **ctx):
        # v0r7_rice ディレクトリ直下の product_tree_* を読み、最小の木を作る
        scenario_root = ctx.get("db_path") or "."
        outbound = os.path.join(scenario_root, "product_tree_outbound.csv")

        # ここでは「単一ルート＋子」を仮置き（実装ではCSVを舐めて接続）
        R = Node("ROOT")
        # R.children.append(Node("WS1CAL")) ... CSVから構築
        return R


    bus.add_filter("plan:graph:build", build_v7, priority=50)
