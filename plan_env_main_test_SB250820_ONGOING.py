#plan_env_main_test.py






from pysi.utils.config import Config

#from pysi.gui.app import *
from pysi.psi_planner_mvp.plan_env_main import *

# 追加
from pysi.plan.operations import propagate_postorder_with_calcP2S


# --- PSIバケツ定義（既に定義済ならスキップ可） ---
BUCKET = {"S":0, "CO":1, "I":2, "P":3}


# checking all tree
from collections import deque

def print_bfs(root):
    q = deque([(root, 0)])
    seen = set()
    while q:
        n, d = q.popleft()
        if n in seen:
            continue
        seen.add(n)
        print(f"[BFS d={d}] {getattr(n,'name',None)} -> {[getattr(c,'name',None) for c in getattr(n,'children',[]) or []]}")
        for c in getattr(n, "children", []) or []:
            q.append((c, d+1))


# --- フォールバック用：親ノードのSを合計 ---
def _sum_parent_S(parent, layer="demand"):
    psi = parent.psi4supply if layer == "supply" else parent.psi4demand
    return sum(len(psi[w][BUCKET["S"]]) for w in range(len(psi)))


# --- フォールバック用：子Pから親Sを自動で集約（±LT自動判定） ---
def _aggregate_children_P_into_parent_S_auto(parent, *, layer="demand", lt_attr="leadtime",
                                             dedup=True, verbose=True):
    psi_p = parent.psi4supply if layer == "supply" else parent.psi4demand
    W = len(psi_p)
    children = getattr(parent, "children", []) or []

    def _try(sign):
        newS = [[] for _ in range(W)]
        assigned = 0
        overflow = 0
        for ch in children:
            psi_c = ch.psi4supply if layer == "supply" else ch.psi4demand
            if len(psi_c) != W:
                continue
            LT = int(getattr(ch, lt_attr, 0) or 0)
            for wc in range(W):
                clots = psi_c[wc][BUCKET["P"]]
                if not clots:
                    continue
                wp = wc - LT if sign == "minus" else wc + LT
                if 0 <= wp < W:
                    newS[wp].extend(clots)
                    assigned += len(clots)
                else:
                    overflow += len(clots)
        for w in range(W):
            psi_p[w][BUCKET["S"]] = list(dict.fromkeys(newS[w])) if (dedup and newS[w]) else newS[w]
        return assigned, overflow

    assigned_minus, _ = _try("minus")
    assigned_plus, _ = _try("plus")

    if assigned_plus > assigned_minus:
        assigned, overflow = _try("plus")
        mode = "plus"
    else:
        assigned, overflow = _try("minus")
        mode = "minus"

    if verbose:
        print(f"[fallback-P2S] node={getattr(parent,'name',None)} mode={mode} "
              f"assigned={assigned} overflow={overflow}")
    return mode, assigned, overflow


# --- 修正版 _childrenP2parentS ---
def _childrenP2parentS(root, *, layer="demand", lt_attr="leadtime"):
    used_builtin = False
    if hasattr(root, "get_set_childrenP2S2psi"):
        root.get_set_childrenP2S2psi()
        used_builtin = True
    else:
        try:
            from pysi.plan.operations import get_set_childrenP2S2psi as util_p2s
            util_p2s(root)
            used_builtin = True
        except Exception as e:
            print(f"[WARN] get_set_childrenP2S2psi を呼べません: {e}")

    if _sum_parent_S(root, layer=layer) > 0:
        if used_builtin:
            print("[P2S] builtin propagation OK.")
        return

    print("[P2S] builtin yielded zero S → fallback(local auto).")
    _aggregate_children_P_into_parent_S_auto(root, layer=layer, lt_attr=lt_attr, verbose=True)




def main():


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
    


    # 1) 準備
    cnf = Config()
    psi = PlanEnv(cnf)
    psi.load_data_files()
    #@ STOP
    #psi.init_psi_spaces_and_demand()  # ここで leaf に S は入っている


    print("Products:", psi.product_name_list)


    # =========================
    # get root IN/OUT
    # =========================
    for p in psi.product_name_list:
        r_ot, r_in = psi.get_roots(p)
        print(f"[{p}] OUT root: {getattr(r_ot, 'name', None)}, IN root: {getattr(r_in, 'name', None)}")


        # (D) 目視しやすい検証ログ

        #@ ADD
        leaves = _leaves(r_ot)

        S_parent = _psi_counts(r_ot, bucket_idx=0, layer="demand")   # 親S（demand面）
        P_leaves_total = sum(_psi_counts(lf, bucket_idx=3, layer="demand") for lf in leaves)  # 葉P合計

        print("root S non-empty weeks (idx:count) ->",
                [(i,int(c)) for i,c in enumerate(S_parent) if c>0][:10])
        print("sum(root S) =", int(S_parent.sum()))
        print("sum(leaf P) =", int(P_leaves_total.sum()),
                "(LT/休暇で先送り→レンジ外に出ると差が出ることがあります)")






    # =========================
    # Tree status checking
    # =========================


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



    # ========== helpers: PSIクリア & 1回限りの安全伝播 ==========
    # ========== common helpers ==========
    def _walk(n):
        st=[n]
        while st:
            x=st.pop()
            yield x
            for c in getattr(x, "children", []) or []:
                st.append(c)

    def _leaves(root):
        return [n for n in _walk(root) if not getattr(n, "children", [])]

    def reset_for_propagation(root, *, preserve_leaf_S=True, clear_leaf_P=True, reset_supply=True):
        """
        伝播前のクリア:
        - demand側: 非葉Sを空、CO/I/Pは全ノード空
        - 葉Sは preserve_leaf_S=True なら維持（init_psi...で積んだSを守る）
        - 葉Pは clear_leaf_P=True なら空に（calcS2Pを安全にやり直すため）
        - 供給側: reset_supply=True なら全て空
        """
        for nd in _walk(root):
            psi = getattr(nd, "psi4demand", None)
            if not isinstance(psi, list):
                continue
            W = len(psi)
            is_leaf = not getattr(nd, "children", [])
            for w in range(W):
                # S
                if is_leaf:
                    if not preserve_leaf_S:
                        nd.psi4demand[w][0] = []
                else:
                    nd.psi4demand[w][0] = []  # 非葉Sは毎回ゼロから
                # CO/I/P
                nd.psi4demand[w][1] = []
                nd.psi4demand[w][2] = []
                nd.psi4demand[w][3] = [] if (not is_leaf or clear_leaf_P) else nd.psi4demand[w][3]
            if reset_supply and hasattr(nd, "psi4supply"):
                nd.psi4supply = [[[],[],[],[]] for _ in range(W)]

    def _calc_S2P(node):
        """ノード1個に対し、実装に合わせて S->P を呼ぶ（あれば同期も）"""
        if hasattr(node, "calcS2P"):
            node.calcS2P()
        elif hasattr(node, "calcS2P_4supply"):
            node.calcS2P_4supply()
        if hasattr(node, "copy_demand_to_supply"):
            node.copy_demand_to_supply()

    def _childrenP2parentS_OLD(root):
        """子P→親S を呼ぶ（メソッド or pysi.plan.operations のフォールバック）"""
        if hasattr(root, "get_set_childrenP2S2psi"):
            root.get_set_childrenP2S2psi()
            return
        try:
            from pysi.plan.operations import get_set_childrenP2S2psi as util_p2s
            util_p2s(root)
        except Exception as e:
            print(f"[WARN] get_set_childrenP2S2psi を呼べません: {e}")

    # ========== これを呼べばOK ==========
    def propagate_childrenP2parentS_once(root,
                                        *,
                                        do_leaf_calc=True,
                                        preserve_leaf_S=True,
                                        clear_leaf_P=True,
                                        reset_supply=True):
        """
        (A) 葉でS->Pを作成（必要なら）
        (B) 子P->親S の再帰伝播
        (C) 親でも S->P を実施 & demand->supply 同期
        すべてクリア後に“1回だけ”実行する安全版
        """
        # クリア（重複追記を防止）
        reset_for_propagation(root,
                            preserve_leaf_S=preserve_leaf_S,
                            clear_leaf_P=clear_leaf_P,
                            reset_supply=reset_supply)

        # (A) 葉の S->P（init_psi... でSだけ入っている前提が多いので既定で計算する）
        if do_leaf_calc:
            for lf in _leaves(root):
                _calc_S2P(lf)

        # (B) 子P→親S
        
        #_childrenP2parentS(root)
        
        _childrenP2parentS(root, layer="demand", lt_attr="leadtime")



        # (C) 親 S->P ＋ 同期
        _calc_S2P(root)










    # 製品ごとに実行（まずは1製品でOK）
    for prod, root in psi.prod_tree_dict_OT.items():
        print(f"\n=== Propagate P->S (product={prod}) ===")

        # 旧: A/B/C の条件分岐ブロック（calcS2P / get_set_childrenP2S2psi / copy_demand_to_supply）
        # 新: 1回限りの安全伝播
        propagate_childrenP2parentS_once(
            root,
            do_leaf_calc=True,        # 葉Pを作りたい（init_psiでSのみ→Pをここで生成）
            preserve_leaf_S=True,     # init_psiでセットされた葉Sは維持
            clear_leaf_P=True,        # 葉Pは再計算のため事前クリア
            reset_supply=True         # 供給面もクリアしてから同期し直す
        )




    # 製品ごとに実行
    for prod, root in psi.prod_tree_dict_OT.items():
        print(f"\n=== Propagate P->S (product={prod}) ===")

        # 伝播前のクリア（あなたの既存ヘルパでOK）
        reset_for_propagation(
            root,
            preserve_leaf_S=True,   # leafのSは保持
            clear_leaf_P=True,      # leafのPはいったん空に
            reset_supply=True
        )

        # ← ここで post-order 版を呼ぶ（子P→親Sの集約＆親S→Pまで含まれる）
        propagate_postorder_with_calcP2S(
            root,
            layer="demand",
            lt_attr="leadtime",
            vacation_policy="shift_to_next_open",
            replace_parent_S=True
        )



        # *************************************
        # OLD Definition
        # *************************************
        ## (A) まず葉で S->P を作る（必要十分条件）
        #leaves = _leaves(root)
        #for lf in leaves:
        #    # SからPを計算（実装により calcS2P or calcS2P_4supply が存在）
        #    if hasattr(lf, "calcS2P"):
        #        lf.calcS2P()
        #    elif hasattr(lf, "calcS2P_4supply"):
        #        lf.calcS2P_4supply()
        #    # demand面→supply面 同期がある場合のみ呼ぶ（無ければ無視してOK）
        #    if hasattr(lf, "copy_demand_to_supply"):
        #        lf.copy_demand_to_supply()

        ## (B) 子P→親S の再帰伝播（メソッド or ユーティリティ両対応）
        #if hasattr(root, "get_set_childrenP2S2psi"):
        #    root.get_set_childrenP2S2psi()
        #else:
        #    # フォールバック（ユーティリティ関数の実装がある場合）
        #    try:
        #        from pysi.plan.operations import get_set_childrenP2S2psi
        #        get_set_childrenP2S2psi(root)
        #    except Exception as e:
        #        print(f"[WARN] get_set_childrenP2S2psi が呼べません: {e}")

        ## (C) 親でも S->P を実施（必要に応じて）
        #if hasattr(root, "calcS2P"):
        #    root.calcS2P()
        #elif hasattr(root, "calcS2P_4supply"):
        #    root.calcS2P_4supply()
        #if hasattr(root, "copy_demand_to_supply"):
        #    root.copy_demand_to_supply()




        # (D) 目視しやすい検証ログ

        #@ ADD
        leaves = _leaves(root)

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