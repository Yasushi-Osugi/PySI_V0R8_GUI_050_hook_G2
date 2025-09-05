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


from functools import lru_cache
from pysi.plan.demand_generate import _normalize_monthly_demand_df_sku, convert_monthly_to_weekly_sku

#from pysi.db.sqlite import connect
import json

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


# init_sql.py に追加（seed_schema_and_master の下あたり）
def ensure_master_for_df(df_weekly: pd.DataFrame):
    """df_weekly に登場する node/product を node / product / node_product に upsert."""
    nodes = sorted(set(df_weekly["node_name"].astype(str)))
    prods = sorted(set(df_weekly["product_name"].astype(str)))

    with connect(DB_PATH) as con:
        # 1) product
        for prod in prods:
            upsert_product(con, prod)

        # 2) node（親は暫定で ROOT にぶら下げる／必要なら分岐）
        for node in nodes:
            # 既にある DAD01/MOM01 以外も許容。leadtime/ss は暫定既定値。
            upsert_node(con, node, ROOT, leadtime=2, ss_days=7, long_vacation_weeks=[])

        # 3) node_product（未登録なら既定Lot/コストで作成）
        for node in nodes:
            for prod in prods:
                # 既存なら UPDATE されるが値も更新したくない場合は存在チェックしてもOK
                upsert_node_product(
                    con, node, prod,
                    lot_size=getattr(Config, "DEFAULT_LOT_SIZE", 1),
                    cs_logistics_costs=0.05, cs_warehouse_cost=0.03,
                    cs_fixed_cost=0.02, cs_profit=0.15,
                    cs_direct_materials_costs=0.70, cs_tax_portion=0.05
                )



# --- 実データ→週次DFを作る ------------------------------------
def build_weekly_from_csv() -> tuple[pd.DataFrame, int, int]:
    # 1) 月次CSVを読む（列名ゆらぎは_normalizeで吸収）
    #   ※ Windows で文字化けする場合は encoding="cp932" に変更
    df_month = pd.read_csv(Config.MONTHLY_DEMAND_FILE, encoding="utf-8")
    df_month = _normalize_monthly_demand_df_sku(df_month)

    # 2) lot_size を DB から引くルックアップ
    @lru_cache(maxsize=None)
    def _lot_size_lookup(prod: str, node: str) -> int:
        with connect(DB_PATH) as con:
            row = con.execute("""
                SELECT lot_size FROM node_product
                WHERE product_name=? AND node_name=?
            """, (prod, node)).fetchone()
        return int(row["lot_size"]) if row else int(Config.DEFAULT_LOT_SIZE)

    # 3) 週次へ変換（lot_id_list付き）
    df_weekly, plan_range, plan_year_st = convert_monthly_to_weekly_sku(
        df_month, _lot_size_lookup
    )

    return df_weekly, plan_range, plan_year_st






def seed_calendar(plan_year_st: int, plan_range: int):
    """
    ISOカレンダの index→(year, week) を作って DB に投入。
    ラベルは簡易に "Wxx" を付けています。
    返り値: (week_index_map, weeks_count)
    """
    week_index_map, weeks_count = _build_iso_week_index_map(plan_year_st, plan_range)

    rows = [None] * weeks_count
    for (y, ww), idx in week_index_map.items():
        w = int(ww)
        rows[idx] = (idx, y, w, f"W{w:02d}")

    with connect(DB_PATH) as con:
        seed_calendar445(con, rows)  # INSERT OR REPLACE なので再実行も安全

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



# --- Verification 1: weekly_demand のロット合計 == psi(S) 件数 を検証 ---


def verify_weekly_vs_psiS(db_path: str, node_name: str, product_name: str, *, verbose: bool = True) -> tuple[int, int]:
    """
    DB上の weekly_demand に保存された lot_id_list の総数と、
    psi テーブルの S バケツ件数が一致するかを確認するユーティリティ。
    戻り値: (weekly_demandの総lot数, psi(S)の件数)
    """
    # weekly_demand 側の lot 数合計
    with connect(db_path) as con:
        rows = con.execute("""
            SELECT lot_id_list
            FROM weekly_demand
            WHERE node_name=? AND product_name=?
        """, (node_name, product_name)).fetchall()

    wd_lots = 0
    for r in rows:
        try:
            lots = json.loads(r["lot_id_list"]) if r["lot_id_list"] else []
            if not isinstance(lots, list):
                lots = []
        except Exception:
            lots = []
        wd_lots += len(lots)

    # psi(S) 側の件数
    with connect(db_path) as con:
        psi_s = con.execute("""
            SELECT COUNT(*) AS c
            FROM psi
            WHERE node_name=? AND product_name=? AND bucket='S'
        """, (node_name, product_name)).fetchone()["c"]

    psi_s = int(psi_s)

    if verbose:
        print(f"weekly_demand total lots = {wd_lots}")
        print(f"psi(S) rows              = {psi_s}")
        print("[OK] weekly_demand と psi(S) は一致しています。" if wd_lots == psi_s
              else "[WARN] Mismatch: weekly_demand と psi(S) が一致していません。")

    return wd_lots, psi_s


def verify_psiP_sample(db_path: str, node_name: str, product_name: str, limit: int = 10):
    with connect(db_path) as con:
        rows = con.execute("""
            SELECT iso_index, COUNT(*) AS c
            FROM psi
            WHERE node_name=? AND product_name=? AND bucket='P'
            GROUP BY iso_index
            HAVING c > 0
            ORDER BY iso_index
            LIMIT ?
        """, (node_name, product_name, limit)).fetchall()
    if rows:
        print("psi(P) sample (week_index:count):", [(r["iso_index"], r["c"]) for r in rows])
    else:
        print("psi(P) has no rows yet (SS/LT で先送り or まだ小さいSなら正常).")



# --- tiny GUI (Tkinter + matplotlib) for quick check -----------------
def run_gui(db_path: str, node_name: str, product_name: str):
    import tkinter as tk
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from pysi.db.sqlite import connect

    # 週数はDBから動的取得
    with connect(db_path) as con:
        weeks_row = con.execute(
            "SELECT COALESCE(MAX(iso_index)+1,0) AS wc FROM calendar445"
        ).fetchone()
        weeks_count = int(weeks_row["wc"])

        # 例：Sのロット数を時系列で
        rows = con.execute("""
            SELECT iso_index, COUNT(*) AS s
            FROM psi
            WHERE node_name=? AND product_name=? AND bucket='S'
            GROUP BY iso_index
            ORDER BY iso_index
        """, (node_name, product_name)).fetchall()

    xs = [r["iso_index"] for r in rows]
    ys = [r["s"] for r in rows]

    root = tk.Tk()
    root.title(f"PSI S-series  ({node_name}/{product_name})")

    fig = Figure(figsize=(10, 4), dpi=100)
    ax = fig.add_subplot(111)
    ax.plot(xs, ys, marker="o")
    ax.set_xlim(left=0, right=max(weeks_count-1, 0))
    ax.set_xlabel("week index (0..)")
    ax.set_ylabel("S lots")
    ax.grid(True)

    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    root.mainloop()



def seed_calendar_by(plan_year_st: int, plan_range: int):
    """
    実データ由来の plan_year_st/plan_range から ISO週カレンダをシード。
    戻り: (week_index_map, weeks_count)
    """
    week_index_map, weeks_count = _build_iso_week_index_map(plan_year_st, plan_range)

    rows = [None] * weeks_count
    for (y, ww), idx in week_index_map.items():
        w = int(ww)
        rows[idx] = (idx, y, w, f"W{w:02d}")

    with connect(DB_PATH) as con:
        seed_calendar445(con, rows)

    return week_index_map, weeks_count


# ==== ここから可視化ユーティリティ（init_sql.py の末尾あたりに追加）====
import numpy as np
import math
import matplotlib.pyplot as plt

def _collect_nodes_preorder(root):
    """preorderで Node 一覧を返す"""
    out = []
    def _walk(n):
        out.append(n)
        for c in getattr(n, "children", []):
            _walk(c)
    _walk(root)
    return out

def psi_counts_from_node(node, layer: str = "supply"):
    """
    Node の psi4demand / psi4supply から S/CO/I/P の週次ロット件数を配列化
    layer: "demand" or "supply"
    """
    psi = node.psi4supply if layer == "supply" else node.psi4demand
    W = len(psi)
    S  = np.array([len(psi[w][0]) for w in range(W)], dtype=int)
    CO = np.array([len(psi[w][1]) for w in range(W)], dtype=int)
    I  = np.array([len(psi[w][2]) for w in range(W)], dtype=int)
    P  = np.array([len(psi[w][3]) for w in range(W)], dtype=int)
    return {"S": S, "CO": CO, "I": I, "P": P, "weeks": W}

def _plot_psi_stacked_on_ax(ax, series, title="", xtick_step=None):
    """
    積み上げ棒（上側= I+P、下側= -(S+CO)）を1サブプロットに描画
    """
    W = series["weeks"]
    x = np.arange(W)

    # 配色（Tableau系）
    colors = {"S":"#4e79a7", "CO":"#f28e2b", "I":"#59a14f", "P":"#e15759"}

    # 上側（在庫・入荷）
    bar_I = ax.bar(x, series["I"], color=colors["I"], label="I")
    bar_P = ax.bar(x, series["P"], bottom=series["I"], color=colors["P"], label="P")

    # 下側（出荷・繰越）
    bar_S  = ax.bar(x, -series["S"], color=colors["S"], label="S")
    bar_CO = ax.bar(x, -series["CO"], bottom=-series["S"], color=colors["CO"], label="CO")

    ax.axhline(0, color="#444", lw=0.8)
    ax.set_title(title, fontsize=10)
    ax.set_ylabel("lots")
    ax.grid(True, axis="y", alpha=0.3)

    # x軸のスッキリ化
    if xtick_step is None:
        xtick_step = max(1, W // 20)  # 20目盛り程度に間引き
    ticks = np.arange(0, W, xtick_step)
    ax.set_xticks(ticks)
    ax.set_xlim(-0.5, W - 0.5)

def show_psi_tree(root_node, product_name: str, layer: str = "supply",
                  per_page: int = 6):
    """
    ツリーを手繰って全ノードの PSI を積み上げ棒で表示（ページング）
    layer: "demand" or "supply"
    per_page: 1ページに並べるサブプロット数（6=2x3）
    """
    nodes = _collect_nodes_preorder(root_node)
    if not nodes:
        print("[WARN] no nodes to plot.")
        return

    # レイアウト（2x3, 3x3など）
    rows = int(math.sqrt(per_page))
    cols = math.ceil(per_page / rows)

    # ページごとに描く
    for page_start in range(0, len(nodes), per_page):
        page_nodes = nodes[page_start:page_start+per_page]
        fig, axes = plt.subplots(rows, cols, figsize=(cols*6, rows*3.5), squeeze=False)
        fig.suptitle(f"PSI stacked ({layer})  product={product_name}", fontsize=12)

        # 凡例は最初のサブプロットにつける
        legend_added = False

        for i, node in enumerate(page_nodes):
            r, c = divmod(i, cols)
            ax = axes[r][c]
            series = psi_counts_from_node(node, layer=layer)
            _plot_psi_stacked_on_ax(ax, series, title=node.name)

            if not legend_added:
                handles, labels = ax.get_legend_handles_labels()
                fig.legend(handles, labels, loc="upper right", ncol=4, frameon=False)
                legend_added = True

        # 余白の空サブプロットは非表示
        for j in range(len(page_nodes), rows*cols):
            r, c = divmod(j, cols)
            axes[r][c].axis("off")

        fig.tight_layout(rect=[0, 0, 0.98, 0.95])
        plt.show()
# ==== ここまで ====





def main():
    print("== Phase 0: schema & master seed")
    seed_schema_and_master()

    print("== Phase 1a: monthly->weekly (CSV)")
    df_weekly, plan_range, plan_year_st = build_weekly_from_csv()

    print("== Phase 1b: seed calendar (by returned plan)")
    week_index_map, weeks_count = seed_calendar_by(plan_year_st, plan_range)

    print("== Phase 1c: upsert weekly_demand")
    # ★ DFに登場する node / product をマスタ登録（FK対策）
    ensure_master_for_df(df_weekly)
    seed_weekly_demand(df_weekly)

    print("== Phase 1d: build tiny Node tree")
    dad, mom = build_tiny_tree(weeks_count, plan_year_st)

    print("== Phase 1e: push S-lots to leaf and calc S->P")
    # （ノイズ少なめのログに調整）
    with connect(DB_PATH) as con:
        pSi = load_lots_for_node(con, LEAF, PRODUCT, week_index_map, weeks_count)
    non_empty = [(i, len(lst)) for i, lst in enumerate(pSi) if lst]
    total_lots = sum(c for _, c in non_empty)
    print(f"weeks_count={weeks_count}, total_lots={total_lots}, "
          f"first_non_empty={non_empty[:10]}")
    mom.set_S2psi(pSi)
    mom.calcS2P()
    mom.copy_demand_to_supply()

    print("== Phase 1f: gather to parent and calc S->P on parent")
    #dad.get_set_childrenP2S2psi(plan_range)  # 既存仕様：ここは plan_range を使う設計
    dad.get_set_childrenP2S2psi()  # 既存仕様：ここは plan_range を使う設計
    dad.calcS2P()
    dad.copy_demand_to_supply()

    print("== Phase 1g: persist PSI (demand/supply)")
    persist_psi_all(dad, mom)


    # 検証や価格タグなどのあと
    # 末端～親まで全部を stacked bar で可視化（supply層）
    #show_psi_tree(dad, PRODUCT, layer="supply", per_page=6)

    # demand層で見たい場合
    show_psi_tree(dad, PRODUCT, layer="demand", per_page=6)


    print("== Phase 1h: set price tags (optional)")
    seed_price_tags()

    # 簡易検証：weekly_demand の合計ロット数 = psi(S)
    verify_weekly_vs_psiS(DB_PATH, LEAF, PRODUCT)

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




#if __name__ == "__main__":
#    main()                # ← まずDB生成～保存まで実行
#    verify_db_counts()    # ← 直後に検証（必要に応じて引数で node/prod を変更）


    ## psi(P) のサンプル 既存: DB_PATH / NODE / PROD が定義済みの想定
    #pairs = sample_non_empty_weeks(DB_PATH, NODE, PROD)  # bucket='P'、limit=10 が既定
    #pairs = sample_non_empty_weeks(DB_PATH, LEAF, PRODUCT)

    #if pairs:
    #    print("psi(P) sample (week_index:count):", pairs)
    #else:
    #    print("psi(P) has no rows yet (小さなSやSS/LTで先送り中なら正常).")


    # 年・週で見たい場合（calendar445 と結合する版）
    #human = sample_non_empty_weeks_human(DB_PATH, NODE, PROD)
    #print("psi(P) sample (YYYY,WW,count):", human)



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true", help="finish seeding then open quick GUI")
    args = parser.parse_args()

    main()  # ← DB seed & 計算 & 保存

    # 任意の検証
    verify_weekly_vs_psiS(DB_PATH, LEAF, PRODUCT)

    pairs = sample_non_empty_weeks(DB_PATH, LEAF, PRODUCT)
    if pairs:
        print("psi(P) sample (week_index:count):", pairs)
    else:
        print("psi(P) has no rows yet (小さなSやSS/LTで先送り中なら正常).")


    if args.gui:
        # Tkinter mainloop はブロッキング。最後に呼べばOK
        run_gui(DB_PATH, LEAF, PRODUCT)

