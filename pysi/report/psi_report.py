# psi_report.py
# -*- coding: utf-8 -*-
"""
Step 6: 可視化/簡易レポート（Global Weekly PSI Planner）

・lot_bucket を calendar_iso に乗せて週次の S/CO/I/P ロット数を集計
・CSVエクスポートとスタック棒グラフを生成
・親や葉などの区別なく、任意 node×product×layer（demand/supply）で出力
"""

from __future__ import annotations
import argparse
import os
import sqlite3
import json
import math
from typing import List, Dict
import pandas as pd
import matplotlib.pyplot as plt








# ----------------------------
# DB helpers
# ----------------------------
def _open(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

#@250902 STOP
#def get_id(conn: sqlite3.Connection, table: str, name: str) -> int:
#    row = conn.execute(f"SELECT id FROM {table} WHERE name=?", (name,)).fetchone()
#    if not row:
#        raise ValueError(f"{table}.name='{name}' が見つかりません")
#    return int(row["id"])


def get_id(conn: sqlite3.Connection, table: str, name: str) -> int:
    row = conn.execute(f"SELECT id FROM {table} WHERE name=?", (name,)).fetchone()
    if not row:
        raise ValueError(f"{table}.name='{name}' が見つかりません")
    # Row でも tuple でも動くように
    try:
        return int(row["id"])  # sqlite3.Row の場合
    except Exception:
        return int(row[0])     # tuple の場合




def get_scenario_id(conn, scenario_name: str) -> int:
    return get_id(conn, "scenario", scenario_name)

def get_node_id(conn, node_name: str) -> int:
    return get_id(conn, "node", node_name)

def get_product_id(conn, product_name: str) -> int:
    return get_id(conn, "product", product_name)

def get_scenario_bounds(conn, scenario_id: int) -> tuple[int, int]:
    row = conn.execute(
        "SELECT plan_year_st, plan_range FROM scenario WHERE id=?", (scenario_id,)
    ).fetchone()
    if not row:
        raise ValueError("scenario が見つかりません")
    return int(row["plan_year_st"]), int(row["plan_range"])

# ----------------------------
# fetch & pivot
# ----------------------------
def fetch_weekly_counts(
    conn: sqlite3.Connection,
    scenario_id: int,
    node_id: int,
    product_id: int,
    layer: str,
) -> pd.DataFrame:
    """
    週 index をカレンダ正本に合わせてフルレンジで作り、その上に lot_bucket を集約して載せる。
    """
    y0, pr = get_scenario_bounds(conn, scenario_id)
    y1 = y0 + pr - 1

    # 全週（calendar）←左結合で穴埋め
    cal = pd.read_sql_query(
        """
        SELECT week_index, iso_year, iso_week
        FROM calendar_iso
        WHERE iso_year BETWEEN ? AND ?
        ORDER BY week_index
        """,
        conn,
        params=(y0, y1),
    )

    # lot_bucket を集約
    df = pd.read_sql_query(
        """
        SELECT lb.week_index,
               lb.bucket,
               COUNT(DISTINCT lb.lot_id) AS lots
        FROM lot_bucket lb
        WHERE lb.scenario_id = ?
          AND lb.layer = ?
          AND lb.node_id = ?
          AND lb.product_id = ?
        GROUP BY lb.week_index, lb.bucket
        """,
        conn,
        params=(scenario_id, layer, node_id, product_id),
    )

    if df.empty:
        # 空でもカレンダ分の0行を返す
        out = cal.copy()
        for b in ["S", "CO", "I", "P"]:
            out[b] = 0
        return out

    pv = (
        df.pivot_table(index="week_index", columns="bucket", values="lots", aggfunc="sum")
          .reindex(columns=["S", "CO", "I", "P"])
          .fillna(0)
          .astype(int)
          .reset_index()
    )

    out = cal.merge(pv, on="week_index", how="left")
    for b in ["S", "CO", "I", "P"]:
        if b not in out.columns:
            out[b] = 0
    out[["S", "CO", "I", "P"]] = out[["S", "CO", "I", "P"]].fillna(0).astype(int)
    return out

# ----------------------------
# plot
# ----------------------------
def plot_weekly(
    df: pd.DataFrame,
    title: str,
    out_path: str,
    fmt: str = "png",
    show: bool = False,
    annotate_top: bool = True,
):
    """
    スタック棒（S,P）＋折れ線（I,CO）
    """
    x = df["week_index"]
    S = df["S"]
    P = df["P"]
    I = df["I"]
    CO = df["CO"]

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.bar(x, S, label="S (ship)", color="#4C78A8", alpha=0.85)
    ax.bar(x, P, bottom=S, label="P (arrive/produce)", color="#F58518", alpha=0.85)

    ax2 = ax.twinx()
    ax2.plot(x, I, label="I (inventory)", color="#54A24B", linewidth=1.8)
    ax2.plot(x, CO, label="CO (carry-over)", color="#E45756", linewidth=1.8, linestyle="--")

    ax.set_title(title)
    ax.set_xlabel("week_index")
    ax.set_ylabel("lots (S+P)")
    ax2.set_ylabel("lots (I / CO)")

    # 凡例
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax2.legend(h1+h2, l1+l2, loc="upper right", ncol=4, fontsize=9)

    # 目盛り軽量化
    step = max(1, len(x)//26)  # おおよそ隔週〜月次で
    ax.set_xticks(x[::step])
    ax.grid(axis="y", alpha=0.3)

    # 最大週を注記（任意）
    if annotate_top and len(x) > 0:
        k_s = int(S.idxmax()) if S.sum() else None
        k_p = int(P.idxmax()) if P.sum() else None
        if k_s is not None:
            ax.annotate(f"max S={S.loc[k_s]}", (x.loc[k_s], S.loc[k_s]),
                        xytext=(0, 8), textcoords="offset points", ha="center", fontsize=8)
        if k_p is not None:
            sp = S.loc[k_p] + P.loc[k_p]
            ax.annotate(f"max S+P={sp}", (x.loc[k_p], sp),
                        xytext=(0, 8), textcoords="offset points", ha="center", fontsize=8)

    out_img = f"{out_path}.{fmt}"
    os.makedirs(os.path.dirname(out_img) or ".", exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_img, dpi=150)
    if show:
        plt.show()
    plt.close(fig)
    return out_img

# ----------------------------
# main
# ----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="SQLite file path")
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--node", required=True)
    ap.add_argument("--product", required=True)
    ap.add_argument("--layer", choices=["demand", "supply"], default="demand")
    ap.add_argument("--outdir", default="report_out")
    ap.add_argument("--fmt", choices=["png", "svg", "pdf"], default="png")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--csv", action="store_true", help="weekly集計CSVも保存")
    args = ap.parse_args()

    conn = _open(args.db)
    scenario_id = get_scenario_id(conn, args.scenario)
    node_id = get_node_id(conn, args.node)
    product_id = get_product_id(conn, args.product)

    df = fetch_weekly_counts(conn, scenario_id, node_id, product_id, args.layer)

    # CSV保存（任意）
    os.makedirs(args.outdir, exist_ok=True)
    base = os.path.join(
        args.outdir, f"{args.scenario}_{args.layer}_{args.node}_{args.product}"
    )
    if args.csv:
        df.to_csv(f"{base}_weekly_counts.csv", index=False, encoding="utf-8-sig")

    # グラフ
    title = f"{args.scenario} / {args.layer} / {args.node} / {args.product}"
    img = plot_weekly(df, title=title, out_path=f"{base}_weekly_chart", fmt=args.fmt, show=args.show)

    # ざっくりKPIを標準出力
    kpi = {
        "sum_S": int(df["S"].sum()),
        "sum_P": int(df["P"].sum()),
        "sum_I": int(df["I"].sum()),
        "sum_CO": int(df["CO"].sum()),
        "weeks": int(len(df)),
        "first": f"{int(df['iso_year'].iloc[0])}-W{int(df['iso_week'].iloc[0]):02d}" if len(df) else None,
        "last":  f"{int(df['iso_year'].iloc[-1])}-W{int(df['iso_week'].iloc[-1]):02d}" if len(df) else None,
        "image": img,
        "csv": f"{base}_weekly_counts.csv" if args.csv else None,
    }
    print(json.dumps(kpi, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

#使い方
## 需要レイヤ（demand）の TOKYO×RICE をPNGで出力＋CSV保存
#python psi_report.py --db psi.sqlite --scenario Baseline --node TOKYO --product RICE --layer demand --outdir report --fmt png --csv
#
## 供給レイヤ（supply）の JAPAN_DC×RICE をPDFで
#python psi_report.py --db psi.sqlite --scenario Baseline --node JAPAN_DC --product RICE --layer supply --outdir report --fmt pdf
#
#
#出力物：
#
#report/Baseline_demand_TOKYO_RICE_weekly_counts.csv（週ごとの S/CO/I/P ロット数）
#
#report/Baseline_demand_TOKYO_RICE_weekly_chart.png（スタック棒＋折れ線）
#
#補足（拡張のヒント）
#
#休暇週のハイライト：node テーブルに long_vacation_weeks が入っていれば、ax.axvspan() で影を付けられます（必要なら追記します）。
#
#安全在庫しきい値の線：node.SS_days と平均Sロットから threshold = round(SS_days/7) * avg_S を引き、ax2.axhline()。
#
#「子P合計 vs 親S合計」の階層保存則チェックは Step 5 のテストに追加可能。

