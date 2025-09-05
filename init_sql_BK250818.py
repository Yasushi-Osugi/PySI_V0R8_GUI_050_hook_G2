#init_sql.py


from __future__ import annotations

import pandas as pd

from pysi.db.sqlite import (
    connect, init_schema,
    upsert_node, upsert_product, upsert_node_product,
    upsert_tariff, seed_calendar445,
    upsert_weekly_demand, load_lots_for_node,
    persist_node_psi, set_price_tag,
)
from pysi.network.node_base import Node
# 週インデックス生成のヘルパ（5/6で貼っていただいたやつ）
from pysi.plan.operations import _build_iso_week_index_map



# 最上部に追加
from pysi.utils.config import Config

# グローバル設定値として取得
PLAN_YEAR_ST = Config.DEFAULT_START_YEAR
PLAN_RANGE   = Config.DEFAULT_PLAN_RANGE



DB_PATH = "psi.sqlite3"
SCHEMA_PATH = "pysi/db/schema.sql"

PRODUCT = "prod-A"
ROOT    = "DAD01"   # 上流
LEAF    = "MOM01"   # 下流

PLAN_YEAR_ST = 2025
PLAN_RANGE   = 3    # 年数（= 53週×PLAN_RANGE）

def seed_schema_and_master():
    # スキーマ初期化
    with connect(DB_PATH) as con:
        init_schema(con, schema_path=SCHEMA_PATH)

    # マスタ投入（ノード、製品、コスト比率、関税率）
    with connect(DB_PATH) as con:
        upsert_node(con, ROOT, None, leadtime=1, ss_days=7, long_vacation_weeks=[1, 52])
        upsert_node(con, LEAF, ROOT, leadtime=2, ss_days=7, long_vacation_weeks=[])
        upsert_product(con, PRODUCT)

        # 共通計画単位：完成品 lot_size=1 を想定
        upsert_node_product(
            con, ROOT, PRODUCT, lot_size=1,
            cs_logistics_costs=0.05, cs_warehouse_cost=0.03,
            cs_fixed_cost=0.02, cs_profit=0.15,
            cs_direct_materials_costs=0.70, cs_tax_portion=0.05
        )
        upsert_node_product(
            con, LEAF, PRODUCT, lot_size=1,
            cs_logistics_costs=0.08, cs_warehouse_cost=0.04,
            cs_fixed_cost=0.02, cs_profit=0.12,
            cs_direct_materials_costs=0.69, cs_tax_portion=0.05
        )

        # 関税率（from=親、to=子）
        upsert_tariff(con, PRODUCT, ROOT, LEAF, 0.08)  # 8%

def seed_calendar():
    """
    ISOカレンダの index→(year, week) を作って DB に投入。
    ラベルは簡易に "Wxx" を付けています。
    """
    week_index_map, weeks_count = _build_iso_week_index_map(PLAN_YEAR_ST, PLAN_RANGE)

    # mapping は {(year,'WW'): idx}。idx順に並べ替えた行を作る
    rows = [None] * weeks_count
    for (y, ww), idx in week_index_map.items():
        w = int(ww)
        rows[idx] = (idx, y, w, f"W{w:02d}")

    with connect(DB_PATH) as con:
        seed_calendar445(con, rows)

    return week_index_map, weeks_count

def monthly_to_weekly_dummy_df():
    """
    “月次→週次変換後”の df_weekly をダミーで作る版。
    実務では convert_monthly_to_weekly_sku(...) の結果を使ってください。
    """
    # 例：2025年の数週だけ S を入れて lot_id_list を生成
    # 本来は pysi.plan.demand_generate.convert_monthly_to_weekly_sku の出力を upsert します。
    data = []
    def mk_lots(node, prod, y, w, cnt):
        return [f"{node}-{prod}-{y}{w:02d}{i+1:04d}" for i in range(cnt)]

    for (y, w, s) in [(2025, 1, 2), (2025, 2, 1), (2025, 3, 3)]:
        data.append({
            "product_name": PRODUCT,
            "node_name": LEAF,
            "iso_year": y,
            "iso_week": w,
            "value": s,               # 任意（残してもいいし未使用でもOK）
            "S_lot": s,               # ロット数
            "lot_id_list": mk_lots(LEAF, PRODUCT, y, w, s)
        })

    df_weekly = pd.DataFrame(data)
    return df_weekly

def seed_weekly_demand(df_weekly: pd.DataFrame):
    with connect(DB_PATH) as con:
        upsert_weekly_demand(con, df_weekly)



def build_tiny_tree(weeks_count: int, plan_year_st: int):
    dad = Node(ROOT)
    mom = Node(LEAF)
    dad.add_child(mom)

    # PSIレンジをweeks_countベースで設定
    dad.set_plan_range_by_weeks(weeks_count, plan_year_st)
    mom.set_plan_range_by_weeks(weeks_count, plan_year_st)

    # 🔧 安全策：psi4demandも含めて初期化する（将来的にはset_plan_range_by_weeksに統合してもOK）
    dad.psi4demand = [[[], [], [], []] for _ in range(weeks_count)]
    mom.psi4demand = [[[], [], [], []] for _ in range(weeks_count)]

    dad.psi4supply = [[[], [], [], []] for _ in range(weeks_count)]
    mom.psi4supply = [[[], [], [], []] for _ in range(weeks_count)]

    print(f"[DEBUG] weeks_count={weeks_count}, PLAN_YEAR_ST={plan_year_st}")

    return dad, mom




def build_tiny_tree_OLD2(weeks_count: int, plan_year_st: int):
    dad = Node(ROOT)
    mom = Node(LEAF)
    dad.add_child(mom)

    dad.set_plan_range_by_weeks(weeks_count, plan_year_st)
    mom.set_plan_range_by_weeks(weeks_count, plan_year_st)

    print(f"[DEBUG] weeks_count={weeks_count}, PLAN_YEAR_ST={plan_year_st}")


    return dad, mom


def build_tiny_tree4CONFIG():
    dad = Node(ROOT)
    mom = Node(LEAF)
    dad.add_child(mom)

    # PSI バッファ長さを設定
    dad.set_plan_range_lot_counts(Config.DEFAULT_PLAN_RANGE, Config.DEFAULT_START_YEAR)
    mom.set_plan_range_lot_counts(Config.DEFAULT_PLAN_RANGE, Config.DEFAULT_START_YEAR)

    # debug用: lenチェック
    print(f"len(mom.psi4demand) = {len(mom.psi4demand)}")
    return dad, mom


def build_tiny_tree_OLD(weeks_count: int):
    """
    Node ツリーを最小構成で構築（DBに保存するために psi を持つ実体が必要）
    """
    dad = Node(ROOT)
    mom = Node(LEAF)
    dad.add_child(mom)

    # PSI バッファ長さを計画レンジに合わせる
    dad.set_plan_range_lot_counts(PLAN_RANGE, PLAN_YEAR_ST)
    mom.set_plan_range_lot_counts(PLAN_RANGE, PLAN_YEAR_ST)

    # 念のため：長さが weeks_count と一致している前提（node_base の設計は 53*plan_range 固定）
    return dad, mom




def push_S_lots_to_leaf(mom: Node, week_index_map: dict, weeks_count: int):
    with connect(DB_PATH) as con:
        pSi = load_lots_for_node(con, LEAF, PRODUCT, week_index_map, weeks_count)

    # 🔧 pSi の長さを Node 側に合わせる
    if len(pSi) < weeks_count:
        pSi += [[] for _ in range(weeks_count - len(pSi))]
    elif len(pSi) > weeks_count:
        pSi = pSi[:weeks_count]

    # --- ここから “ノイズ少なめ” デバッグ出力 ---
    total_lots = sum(len(lst) for lst in pSi)
    print(f"weeks_count={weeks_count}, len(pSi)={len(pSi)}, total_lots={total_lots}")

    # 非空週だけ（index, 件数）を抽出して先頭10件だけ表示
    non_empty = [(i, len(lst)) for i, lst in enumerate(pSi) if lst]
    if non_empty:
        print("non-empty weeks (index:count) - first 10:", non_empty[:10])
        # おまけ：最初の3週だけ lot_id サンプルも表示（各週3件まで）
        samples = {i: pSi[i][:3] for i, _ in non_empty[:3]}
        print("samples (first 3 non-empty weeks):", samples)
    else:
        print("no S lots found for this selection.")
    # --- ここまで ---

    mom.set_S2psi(pSi)
    mom.calcS2P()
    mom.copy_demand_to_supply()




def push_S_lots_to_leaf_OLD(mom: Node, week_index_map: dict, weeks_count: int):
    """
    DB(weekly_demand) → mom.psi4demand[w][0] に S ロットを割り付け
    """
    with connect(DB_PATH) as con:
        pSi = load_lots_for_node(con, LEAF, PRODUCT, week_index_map, weeks_count)
    mom.set_S2psi(pSi)     # S をセット
    mom.calcS2P()          # S→P（安全在庫/休暇週を考慮して後ろ倒し）
    mom.copy_demand_to_supply()

def gather_to_parent_and_calc(dad: Node):
    """
    子P→親S を集約し、親側でも S→P を実施
    """
    dad.get_set_childrenP2S2psi()  # 子P→親S (LTぶん前倒し)
    #dad.get_set_childrenP2S2psi(PLAN_RANGE)  # 子P→親S (LTぶん前倒し)
    dad.calcS2P()
    dad.copy_demand_to_supply()

def persist_psi_all(dad: Node, mom: Node):
    with connect(DB_PATH) as con:
        persist_node_psi(con, mom, PRODUCT, source="demand")
        persist_node_psi(con, mom, PRODUCT, source="supply")
        persist_node_psi(con, dad, PRODUCT, source="demand")
        persist_node_psi(con, dad, PRODUCT, source="supply")

def seed_price_tags():
    with connect(DB_PATH) as con:
        set_price_tag(con, ROOT, PRODUCT, "ASIS", 120.0)   # ルート出荷(親)のASIS
        set_price_tag(con, LEAF, PRODUCT, "TOBE", 300.0)   # 末端(子)の市場TOBE

def main():
    print("== Phase 0: schema & master seed")
    seed_schema_and_master()

    print("== Phase 0b: calendar seed")
    week_index_map, weeks_count = seed_calendar()

    print("== Phase 1a: weekly demand seed (dummy)")
    df_weekly = monthly_to_weekly_dummy_df()
    seed_weekly_demand(df_weekly)

    print("== Phase 1b: build tiny Node tree")
    #dad, mom = build_tiny_tree(weeks_count)

    dad, mom = build_tiny_tree(weeks_count, PLAN_YEAR_ST)



    print("== Phase 1c: push S-lots to leaf and calc S->P")

    print(f"len(mom.psi4demand) = {len(mom.psi4demand)}")

    #@250818 ADD
    push_S_lots_to_leaf(mom, week_index_map, weeks_count)

    print("== Phase 1d: gather to parent and calc S->P on parent")
    gather_to_parent_and_calc(dad)

    print("== Phase 1e: persist PSI (demand/supply)")
    persist_psi_all(dad, mom)

    print("== Phase 1f: set price tags (optional)")
    seed_price_tags()

    print("DONE. You can now inspect 'psi' / 'weekly_demand' tables in", DB_PATH)


# **************************
# verify_db_counts
# **************************
from pysi.db.sqlite import connect
import json

def verify_db_counts(db_path: str = "psi.sqlite3", node: str = "MOM01", prod: str = "prod-A"):
    with connect(db_path) as con:
        # weekly_demand のロット数合計
        rows = con.execute("""
            SELECT lot_id_list FROM weekly_demand
            WHERE node_name=? AND product_name=?""", (node, prod)).fetchall()
        wd_lots = sum(len(json.loads(r["lot_id_list"])) for r in rows)

        # psi(S) のロット数
        psi_s = con.execute("""
            SELECT COUNT(*) AS c FROM psi
            WHERE node_name=? AND product_name=? AND bucket='S'""",
            (node, prod)).fetchone()["c"]

    print("weekly_demand total lots =", wd_lots)
    print("psi(S) rows              =", psi_s)
    assert wd_lots == psi_s, "Mismatch between weekly_demand and psi(S)!"


def sample_non_empty_weeks(db_path: str,
                           node_name: str,
                           product_name: str,
                           bucket: str = "P",
                           limit: int = 10) -> list[tuple[int, int]]:
    """psi テーブルで bucket が非空の週インデックスと件数を先頭 limit 件だけ返す。"""
    from pysi.db.sqlite import connect
    with connect(db_path) as con:
        rows = con.execute("""
            SELECT iso_index, COUNT(*) AS c
            FROM psi
            WHERE node_name=? AND product_name=? AND bucket=?
            GROUP BY iso_index
            HAVING c > 0
            ORDER BY iso_index
            LIMIT ?
        """, (node_name, product_name, bucket, int(limit))).fetchall()
    return [(int(r["iso_index"]), int(r["c"])) for r in rows]



def sample_non_empty_weeks_human(db_path: str,
                                 node_name: str,
                                 product_name: str,
                                 bucket: str = "P",
                                 limit: int = 10) -> list[tuple[int, int, int]]:
    """(iso_year, iso_week, 件数) を返す。"""
    from pysi.db.sqlite import connect
    with connect(db_path) as con:
        rows = con.execute("""
            SELECT c.iso_year, c.iso_week, COUNT(*) AS c
            FROM psi p
            JOIN calendar445 c ON p.iso_index = c.iso_index
            WHERE p.node_name=? AND p.product_name=? AND p.bucket=?
            GROUP BY c.iso_year, c.iso_week
            HAVING c > 0
            ORDER BY c.iso_year, c.iso_week
            LIMIT ?
        """, (node_name, product_name, bucket, int(limit))).fetchall()
    return [(int(r["iso_year"]), int(r["iso_week"]), int(r["c"])) for r in rows]




if __name__ == "__main__":
    main()                # ← まずDB生成～保存まで実行
    verify_db_counts()    # ← 直後に検証（必要に応じて引数で node/prod を変更）


    ## psi(P) のサンプル 既存: DB_PATH / NODE / PROD が定義済みの想定
    #pairs = sample_non_empty_weeks(DB_PATH, NODE, PROD)  # bucket='P'、limit=10 が既定
    #if pairs:
    #    print("psi(P) sample (week_index:count):", pairs)
    #else:
    #    print("psi(P) has no rows yet (小さなSやSS/LTで先送り中なら正常).")


    # 年・週で見たい場合（calendar445 と結合する版）
    #human = sample_non_empty_weeks_human(DB_PATH, NODE, PROD)
    #print("psi(P) sample (YYYY,WW,count):", human)


