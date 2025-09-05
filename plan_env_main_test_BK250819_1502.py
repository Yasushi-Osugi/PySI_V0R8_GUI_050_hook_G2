#plan_env_main_test.py






from pysi.utils.config import Config

#from pysi.gui.app import *
from pysi.psi_planner_mvp.plan_env_main import *



def main():
    # Create a global configuration instance
    cnf = Config()

    # Initialize GUI with the configuration


    psi = PlanEnv(cnf)
    
    psi.load_data_files()

    psi.init_psi_spaces_and_demand()  # ココで週次 PSI スロットまでセット


    print("Products:", psi.product_name_list)
    for p in psi.product_name_list:
        rot, rin = psi.get_roots(p)
        print(f"[{p}] OUT root: {getattr(rot, 'name', None)}, IN root: {getattr(rin, 'name', None)}")

    # 任意：各製品の leaf ノード数
    def count_leaves(n):
        if not getattr(n, "children", []):
            return 1
        return sum(count_leaves(c) for c in n.children)

    for p, root in psi.prod_tree_dict_OT.items():
        print(f"[{p}] leaves:", count_leaves(root))


    # **************************
    # planning process
    # **************************
    from pysi.plan.validators import assert_unique_lot_ids  # ついでに重複検査

    prod = next(iter(psi.prod_tree_dict_OT))
    root = psi.prod_tree_dict_OT[prod]

    # 1) まず leaf 側に S→P が入っていること（init_psi… 済み）
    # 2) 子P→親S の再帰集約を実施（Node/PlanNode 実装により n.get_set_childrenP2S2psi() か util関数）
    root.get_set_childrenP2S2psi()         # ← PlanNodeのメソッド版
    root.calcS2P()                         # 親側でも S->P
    root.copy_demand_to_supply()           # demand面→supply面 へ同期（実装がある場合）

    # （任意）ロットID重複の再検査
    total, dup_cnt, _ = assert_unique_lot_ids({prod: root})
    print(f"[{prod}] after P->S propagate: total lots={total}, dup={dup_cnt}")

    # （確認）親の S 件数が0週だけでも >0 になっているか簡易チェック
    import numpy as np
    S_parent = np.array([len(root.psi4demand[w][0]) for w in range(len(root.psi4demand))])
    print("non-empty weeks on parent S (index:count) ->",
        [(i,int(c)) for i,c in enumerate(S_parent) if c>0][:10])



if __name__ == "__main__":
    main()




