#plan_env_main_test.py






from pysi.utils.config import Config

#from pysi.gui.app import *
from pysi.psi_planner_mvp.plan_env_main import *


def main():
    # 1) 準備
    cnf = Config()
    psi = PlanEnv(cnf)
    psi.load_data_files()
    psi.init_psi_spaces_and_demand()  # ここで leaf に S は入っている

    print("Products:", psi.product_name_list)
    for p in psi.product_name_list:
        rot, rin = psi.get_roots(p)
        print(f"[{p}] OUT root: {getattr(rot, 'name', None)}, IN root: {getattr(rin, 'name', None)}")

    # 任意：leaf数の確認
    def count_leaves(n):
        if not getattr(n, "children", []):
            return 1
        return sum(count_leaves(c) for c in n.children)
    for p, root in psi.prod_tree_dict_OT.items():
        print(f"[{p}] leaves:", count_leaves(root))

    # =========================
    # planning process（堅牢化）
    # =========================
    import numpy as np
    from pysi.plan.validators import assert_unique_lot_ids, assert_no_intra_node_duplicates

    # 汎用ヘルパ
    def _traverse(n):
        st=[n]
        while st:
            x=st.pop()
            yield x
            for c in getattr(x, "children", []) or []:
                st.append(c)

    def _leaves(n):
        return [x for x in _traverse(n) if not getattr(x, "children", [])]

    def _psi_counts(node, bucket_idx=0, layer="demand"):
        psi = node.psi4supply if layer=="supply" else node.psi4demand
        return np.array([len(psi[w][bucket_idx]) for w in range(len(psi))], dtype=int)


    # ========== helpers: PSIクリア & 1回限りの安全伝播 ==========
    def _walk(n):
        st=[n]
        while st:
            x=st.pop()
            yield x
            for c in getattr(x, "children", []) or []:
                st.append(c)

    def reset_for_propagation(root, *, preserve_leaf_S=True, reset_supply=True):
        """
        - 非葉ノードSを空に
        - 全ノードの CO/I/P を空に
        - 供給面は望むなら全クリア
        """
        for nd in _walk(root):
            W = len(getattr(nd, "psi4demand", []) or [])
            is_leaf = not getattr(nd, "children", [])
            for w in range(W):
                # demand side
                if not (preserve_leaf_S and is_leaf):
                    nd.psi4demand[w][0] = []  # S
                nd.psi4demand[w][1] = []      # CO
                nd.psi4demand[w][2] = []      # I
                nd.psi4demand[w][3] = []      # P
            if reset_supply and hasattr(nd, "psi4supply"):
                nd.psi4supply = [[[],[],[],[]] for _ in range(W)]

    def propagate_childrenP2parentS_once(root):
        """
        クリア -> 子P→親S -> 親S→親P -> demand→supply 同期 を1回だけ実行
        """
        reset_for_propagation(root, preserve_leaf_S=True, reset_supply=True)
        # 子P→親S
        root.get_set_childrenP2S2psi()
        # 親S→親P
        root.calcS2P()
        # demand→supply 同期
        if hasattr(root, "copy_demand_to_supply"):
            root.copy_demand_to_supply()












    # 製品ごとに実行（まずは1製品でOK）
    for prod, root in psi.prod_tree_dict_OT.items():
        print(f"\n=== Propagate P->S (product={prod}) ===")


        # (A) まず葉で S->P を作る（必要十分条件）
        leaves = _leaves(root)
        for lf in leaves:
            # SからPを計算（実装により calcS2P or calcS2P_4supply が存在）
            if hasattr(lf, "calcS2P"):
                lf.calcS2P()
            elif hasattr(lf, "calcS2P_4supply"):
                lf.calcS2P_4supply()
            # demand面→supply面 同期がある場合のみ呼ぶ（無ければ無視してOK）
            if hasattr(lf, "copy_demand_to_supply"):
                lf.copy_demand_to_supply()

        # (B) 子P→親S の再帰伝播（メソッド or ユーティリティ両対応）
        if hasattr(root, "get_set_childrenP2S2psi"):
            root.get_set_childrenP2S2psi()
        else:
            # フォールバック（ユーティリティ関数の実装がある場合）
            try:
                from pysi.plan.operations import get_set_childrenP2S2psi
                get_set_childrenP2S2psi(root)
            except Exception as e:
                print(f"[WARN] get_set_childrenP2S2psi が呼べません: {e}")

        # (C) 親でも S->P を実施（必要に応じて）
        if hasattr(root, "calcS2P"):
            root.calcS2P()
        elif hasattr(root, "calcS2P_4supply"):
            root.calcS2P_4supply()
        if hasattr(root, "copy_demand_to_supply"):
            root.copy_demand_to_supply()



        # (D) 目視しやすい検証ログ
        S_parent = _psi_counts(root, bucket_idx=0, layer="demand")   # 親S（demand面）
        P_leaves_total = sum(_psi_counts(lf, bucket_idx=3, layer="demand") for lf in leaves)  # 葉P合計

        print("root S non-empty weeks (idx:count) ->",
              [(i,int(c)) for i,c in enumerate(S_parent) if c>0][:10])
        print("sum(root S) =", int(S_parent.sum()))
        print("sum(leaf P) =", int(P_leaves_total.sum()),
              "(LT/休暇で先送り→レンジ外に出ると差が出ることがあります)")

        # （任意）ロットID重複チェック
        total, dup_cnt, _ = assert_unique_lot_ids({prod: root})
        print(f"[{prod}] lot_id unique check: total={total}, dup={dup_cnt}")

        total, dup_cnt, _ = assert_no_intra_node_duplicates(root)
        print(f"[{prod}] intra-node uniqueness: total={total}, dup={dup_cnt}")

        #total, dup_cnt, _ = assert_unique_lot_ids({prod: root})
        #print(f"[{prod}] lot_id unique check: total={total}, dup={dup_cnt}")




        # シンプルな健全性アサート（必要に応じて緩めてください）
        if S_parent.sum() == 0:
            print(f"[WARN] {prod}: 親Sが全週0です。葉でのS->Pや伝播順序を再確認してください。")

    print("\nDONE propagate for all products.")
    # =========================

if __name__ == "__main__":
    main()

#これで改善されるポイント
#
#葉→親の順序保証：葉で S->P を先に作るため、get_set_childrenP2S2psi() が前提とする「子Pが出来ている」状態を確実化。
#
#メソッド名差異の吸収：calcS2P / calcS2P_4supply のどちらでも動作。
#
#同期の有無に対応：copy_demand_to_supply() が未実装でもエラーにしない。
#
#検証ログ：親Sと葉Pの合計、非空週のサンプルを即確認できる。
#
#重複ID検査：伝播後も lot_id の重複がないかをチェック。
#
#補足：sum(root S) と sum(leaf P) の合計は、子→親でのLT前倒し/休暇週シフトやレンジ外へのはみ出しでズレることがあります。
#ズレが大きい場合は、PlanNode の leadtime、ss_days、長期休暇週設定を一度見直してください。
#
#この形で一度回してみてください。
#ログに「親Sの非空週」が出て、合計件数が妥当なら伝播は正しく効いています。
#必要なら、このロジックを PlanEnv.demand_planning4multi_product() 側に移植して GUI 側のボタン操作と揃えることもできます。