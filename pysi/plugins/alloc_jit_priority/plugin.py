#plugins/alloc_jit_priority/plugin.py

def register(bus):
    from pysi.core.tree import get_nodes

    def jit_assign(root, **ctx):
        weeks = ctx.get("calendar", {}).get("weeks", 52)

        for n in get_nodes(root):
            # 需要週ごとに、最短誤差（|ws - wd|）の生産週へ lot をコピー
            for wd in range(weeks):
                for lot_id in n.psi4demand[wd][0]:
                    best_ws, best_cost = None, 10**9
                    for ws in range(weeks):
                        cost = abs(ws - wd)  # 早納/遅納の対称コスト
                        if cost < best_cost:
                            best_ws, best_cost = ws, cost
                    if best_ws is not None:
                        n.psi4supply[best_ws][3].append(lot_id)
        return root

    # ✅ Hook名を pipeline 準拠に変更
    #bus.add_action("plan:post_build", jit_assign, priority=70)
    ## “after_tree_build” で実行するのが手軽（専用フックにしてもOK）
    bus.add_action("after_tree_build", jit_assign, priority=70)

