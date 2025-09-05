# plan_env_main_test.py

from pysi.utils.config import Config
from pysi.psi_planner_mvp.plan_env_main import PlanEnv

import numpy as np

# COPY方式での整合性検証ユーティリティ（lot_id形式・ノード内重複）
from pysi.plan.validators import (
    validate_lot_format_all,          # 末尾10桁（YYYYWWNNNN）チェック（新旧混在でもOK）
    assert_no_intra_node_duplicates,  # 同一 node × 同一 bucket × 同一週 内の重複検出
)

# P->S集約（子P→親S）＋ S->P を後行順で完走させる
from pysi.plan.operations import propagate_postorder_with_calcP2S

# PSIバケツ
BUCKET = {"S": 0, "CO": 1, "I": 2, "P": 3}


# -------------------------
# ツリー走査・可視ログ
# -------------------------
def _walk(root):
    st = [root]
    while st:
        n = st.pop()
        yield n
        for c in getattr(n, "children", []) or []:
            st.append(c)

def _leaves(root):
    return [n for n in _walk(root) if not getattr(n, "children", [])]

def print_bfs(root):
    """ツリーが正しく多段になっているかを幅優先で確認"""
    from collections import deque
    q = deque([(root, 0)])
    seen = set([root])
    while q:
        n, d = q.popleft()
        children = getattr(n, "children", []) or []
        print(f"[BFS d={d}] {getattr(n,'name',None)} -> {[getattr(c,'name',None) for c in children]}")
        for c in children:
            if c not in seen:
                seen.add(c)
                q.append((c, d + 1))


# -------------------------
# 需要面の“安全な初期化”
# -------------------------
def reset_for_propagation(root, *, preserve_leaf_S=True, clear_leaf_P=True, reset_supply=True):
    """
    伝播前のクリア:
      - demand側: 非葉Sは全消し、CO/I/Pは全ノードで全消し
      - 葉Sは preserve_leaf_S=True なら保持（init_psi で積んだSを守る）
      - 葉Pは clear_leaf_P=True ならクリア（S->Pを安全にやり直す）
      - supply側: reset_supply=True なら全消し（demand->supplyの再同期のため）
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
                    nd.psi4demand[w][BUCKET["S"]] = []
            else:
                nd.psi4demand[w][BUCKET["S"]] = []  # 非葉Sはゼロから
            # CO/I/P をクリア
            nd.psi4demand[w][BUCKET["CO"]] = []
            nd.psi4demand[w][BUCKET["I"]]  = []
            nd.psi4demand[w][BUCKET["P"]]  = [] if (not is_leaf or clear_leaf_P) else nd.psi4demand[w][BUCKET["P"]]
        if reset_supply and hasattr(nd, "psi4supply"):
            nd.psi4supply = [[[], [], [], []] for _ in range(W)]


# -------------------------
# 数量カウント・ログ
# -------------------------
def _psi_week_counts(node, bucket_idx=0, layer="demand"):
    psi = node.psi4supply if layer == "supply" else node.psi4demand
    return np.array([len(psi[w][bucket_idx]) for w in range(len(psi))], dtype=int)

def _print_nonempty_weeks(node, label="node", bucket_idx=0, limit=10):
    arr = _psi_week_counts(node, bucket_idx=bucket_idx, layer="demand")
    hits = [(i, int(c)) for i, c in enumerate(arr) if c > 0][:limit]
    print(f"{label} non-empty weeks (idx:count) -> {hits}")
    return int(arr.sum())

def _sum_root_and_leaf(root):
    # root側
    root_S = int(_psi_week_counts(root, bucket_idx=BUCKET["S"]).sum())
    root_P = int(_psi_week_counts(root, bucket_idx=BUCKET["P"]).sum())
    # leaf側
    leaves = _leaves(root)
    leaf_S = sum(int(_psi_week_counts(lf, bucket_idx=BUCKET["S"]).sum()) for lf in leaves)
    leaf_P = sum(int(_psi_week_counts(lf, bucket_idx=BUCKET["P"]).sum()) for lf in leaves)
    return root_S, root_P, leaf_S, leaf_P


# -------------------------
# 1回限りの安全伝播（COPY方式）
# -------------------------
def propagate_childrenP2parentS_once(
    root,
    *,
    do_leaf_calc=True,        # 葉で S->P を再計算（init_psi でSのみ→ここでPを作る）
    preserve_leaf_S=True,     # 葉Sを保持
    clear_leaf_P=True,        # 葉Pを消してから再計算
    reset_supply=True         # 供給側もクリアしてから同期
):
    """
    (A) クリア（重複追記を防止）
    (B) 葉で S->P（必要なら）
    (C) 子P→親S を後行順で集約し、各親でも S->P → demand->supply 同期
        ※ implementation: pysi.plan.operations.propagate_postorder_with_calcP2S
    """
    # (A) クリア
    reset_for_propagation(
        root,
        preserve_leaf_S=preserve_leaf_S,
        clear_leaf_P=clear_leaf_P,
        reset_supply=reset_supply,
    )

    # (B)(C) 後行順で一括伝播（関数内で「葉S->P → 親P->S → 親S->P → 同期」まで完走）
    # - vacation_policy="shift_to_next_open": 親が休暇週なら開いている週へ前倒しシフト
    # - replace_parent_S=True: 親Sを“再構成”（冪等: 何度実行しても積み増ししない）
    propagate_postorder_with_calcP2S(
        root,
        layer="demand",
        lt_attr="leadtime",
        vacation_policy="shift_to_next_open",
        replace_parent_S=True,
    )


# -------------------------
# メイン
# -------------------------
def main():
    cnf = Config()
    psi = PlanEnv(cnf)
    psi.load_data_files()

    print("Products:", psi.product_name_list)

    # 各製品ごとに OUT/IN の root を取得し、BFSで層を可視化
    for p in psi.product_name_list:
        r_ot, r_in = psi.get_roots(p)
        print(f"[{p}] OUT root: {getattr(r_ot,'name',None)}, IN root: {getattr(r_in,'name',None)}")
        # ネットワークの層を確認
        print_bfs(r_ot)

        # 伝播前の概況（leaf P と root S）
        _print_nonempty_weeks(r_ot, label="root S (pre)", bucket_idx=BUCKET["S"])
        pre_root_S, pre_root_P, pre_leaf_S, pre_leaf_P = _sum_root_and_leaf(r_ot)
        print(f"sum(root S) = {pre_root_S}")
        print(f"sum(leaf P) = {pre_leaf_P} (LT/休暇で先送り→レンジ外に出ると差が出ることがあります)")

    # ツリーの葉数（参考）
    def _count_leaves(n):
        return 1 if not getattr(n, "children", []) else sum(_count_leaves(c) for c in n.children)
    for p, root in psi.prod_tree_dict_OT.items():
        print(f"[{p}] leaves:", _count_leaves(root))

    # =========================
    # 伝播（COPY方式・安全パス）
    # =========================
    for prod, root in psi.prod_tree_dict_OT.items():
        print(f"\n=== Propagate P->S (product={prod}) ===")

        # 1回限りの安全伝播（葉Sを保持し、葉Pを再計算 → 子P→親S → 親S→P）
        propagate_childrenP2parentS_once(
            root,
            do_leaf_calc=True,
            preserve_leaf_S=True,
            clear_leaf_P=True,
            reset_supply=True,
        )

        # 数量ログ（伝播後）
        _print_nonempty_weeks(root, label="root S (post)", bucket_idx=BUCKET["S"])
        post_root_S, post_root_P, post_leaf_S, post_leaf_P = _sum_root_and_leaf(root)
        print(f"sum(root S) = {post_root_S}")
        print(f"sum(leaf P) = {post_leaf_P} (LT/休暇で先送り→レンジ外に出ると差が出ることがあります)")

        # lot_id 形式の検証（新旧両対応）
        validate_lot_format_all(root, use_strict=False)

        # ノード内（S/CO/I/P × 各週）の重複を検出（COPY方式の期待仕様に沿う）
        total_local, dup_local, _samples = assert_no_intra_node_duplicates(root)
        print(f"[{prod}] intra-node uniqueness (per node/bucket/week): total={total_local}, dup={dup_local}")

        # COPY整合のサマリ
        print(f"[COPY check] sum(leaf P)={post_leaf_P}, sum(root S)={post_root_S}  "
              "(※LT/休暇で端に溢れると差が出ます)")
        if post_root_S == 0 and post_leaf_P > 0:
            print(f"[WARN] {prod}: 親Sが0。P->Sの伝播順/初期化/レンジ長(weeks_count)を確認してください。")

    # *****************************************
    # --- SQLite write-through（結果をDBへ） ---
    # *****************************************
    # これで「いまの計画結果（COPY 版）」が psi / price_tag に保存され、GUIや外部レポートから DB を単一参照できます。

    from pysi.io.sql_bridge import persist_all_psi, persist_tariff_table

    DB_PATH = r"C:\Users\ohsug\PySI_V0R8_SQL_010\data\pysi.sqlite3"  # お好みで
    persist_all_psi(psi, DB_PATH)  # PSI & price tags を保存

    # 関税テーブルを使っている場合（持っている dict を渡す）
    try:
        tariff_table = getattr(psi, "tariff_table", None)  # もし PlanEnv が保持していれば
        if tariff_table:
            persist_tariff_table(DB_PATH, tariff_table)
    except Exception:
        pass



    print("\nDONE propagate for all products.")


if __name__ == "__main__":
    main()
