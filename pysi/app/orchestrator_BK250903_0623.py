# pysi/app/orchestrator.py
"""
Global Weekly PSI Planner - Orchestrator
- Step1 calendar → Step2 schema → Step3 ETL → Step4 I/O → Step5 checks → Step6 report（任意）
- 既存DB/CSV/ネットワークビルダから (node, product) を自動検出して処理
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Optional, Tuple, Set

# --- DB/ETL/IO ----------------------------------------------------
from pysi.db.apply_schema import apply_schema
from pysi.db.calendar_sync import sync_calendar_iso
from pysi.etl.etl_monthly_to_lots import run_etl
from pysi.io.psi_io_adapters import (
    _open,
    get_scenario_id,
    get_scenario_bounds,
    load_leaf_S_and_compute,
    write_both_layers,
)

# --- tree専用の薄い書戻し -----------------------------------------
from pysi.io.tree_writeback import (
    write_both_layers_for_pair,
    pairs_from_weekly_demand,
    node_names_from_plan_root,
    intersect_pairs_with_network,
)


# --- Report（無ければスキップ可能） -------------------------------
try:
    from pysi.report.psi_report import (
        fetch_weekly_counts,
        get_scenario_id as _rep_get_scenario_id,
        get_node_id as _rep_get_node_id,
        get_product_id as _rep_get_product_id,
        plot_weekly,
    )
except Exception:
    fetch_weekly_counts = None


# ========== ヘルパ ==========

def _load_factory(spec: str):
    """
    'pysi.network.factory:factory' のような文字列から関数オブジェクトを取得
    """
    if ":" not in spec:
        raise ValueError("--network は 'pkg.module:factory_func' 形式で指定してください")
    mod_name, func_name = spec.split(":", 1)
    mod = importlib.import_module(mod_name)
    fn = getattr(mod, func_name)
    if not callable(fn):
        raise TypeError(f"{spec} は呼び出し可能ではありません")
    return fn


def _scenario_bounds_from_csv(csv_path: str) -> Tuple[int, int]:
    """
    CSV（S_month_data.csv 的な）から plan_year_st / plan_range を推定。
    etl_monthly_to_lots のロジックと揃えたいが、簡易推定に留める。
    """
    import pandas as pd
    df = pd.read_csv(csv_path)
    years = sorted(set(int(y) for y in df["year"].unique()))
    return years[0], max(1, len(years))


def _ensure_calendar(conn: sqlite3.Connection, args) -> Tuple[int, int, int]:
    """
    calendar_iso を冪等に整備。
    優先度: CLI指定 > CSV推定 > 既存シナリオ値
    """
    plan_year_st = args.plan_year_st
    plan_range   = args.plan_range
    sid: Optional[int] = None

    if plan_year_st is None or plan_range is None:
        if args.csv and not args.skip_etl:
            try:
                plan_year_st, plan_range = _scenario_bounds_from_csv(args.csv)
            except Exception:
                plan_year_st = plan_year_st or 2025
                plan_range   = plan_range or 1
        else:
            # 既存シナリオから読む（存在しない場合は sid=None のまま）
            try:
                sid = get_scenario_id(conn, args.scenario)
                pys, pr = get_scenario_bounds(conn, sid)
                plan_year_st = plan_year_st or pys
                plan_range   = plan_range or pr
            except Exception:
                sid = None

    # スキップ指定がなければ calendar を整える
    n_weeks = 0
    if not args.skip_calendar:
        if sid is not None:
            # シナリオ基準で同期
            n_weeks = sync_calendar_iso(conn, scenario_id=sid)
        else:
            # CLI/CSV で境界が決まっている場合はこちら
            n_weeks = sync_calendar_iso(conn, plan_year_st=int(plan_year_st), plan_range=int(plan_range))
    else:
        cur = conn.execute("SELECT COUNT(*) FROM calendar_iso")
        n_weeks = int(cur.fetchone()[0] or 0)

    return int(plan_year_st), int(plan_range), int(n_weeks)


def _pairs_from_db(conn: sqlite3.Connection, scenario_id: int) -> Set[Tuple[str, str]]:
    """
    DBの weekly_demand から (node_name, product_name) のユニークペアを掘り出す。
    """
    rows = conn.execute(
        """
        SELECT n.name, p.name
        FROM weekly_demand wd
        JOIN node n    ON wd.node_id = n.id
        JOIN product p ON wd.product_id = p.id
        WHERE wd.scenario_id = ?
        GROUP BY n.name, p.name
        """,
        (scenario_id,),
    ).fetchall()
    return {(r[0], r[1]) for r in rows}


def _report_one(conn, scenario: str, node_name: str, product_name: str,
                layer: str, outdir: str, fmt: str = "png") -> Optional[str]:
    """
    週間グラフの 1 枚出力（report モジュールが無い場合は None を返す）
    """
    if fetch_weekly_counts is None:
        return None
    Path(outdir).mkdir(parents=True, exist_ok=True)
    sid = _rep_get_scenario_id(conn, scenario)
    nid = _rep_get_node_id(conn, node_name)
    pid = _rep_get_product_id(conn, product_name)
    df = fetch_weekly_counts(conn, sid, nid, pid, layer)
    out = Path(outdir) / f"{scenario}_{layer}_{node_name}_{product_name}_weekly_chart.{fmt}"
    plot_weekly(df, title=f"{scenario} / {layer} / {node_name} / {product_name}", outpath=str(out))
    return str(out)


# ========== CLI ==========

def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="PySI Orchestrator")
    ap.add_argument("--db", required=True, help="SQLite DB path (e.g. var/psi.sqlite)")
    ap.add_argument("--scenario", required=True, help="Scenario name (e.g. Baseline)")
    ap.add_argument("--schema", help="Apply DDL (schema.sql) before run")
    ap.add_argument("--csv", help="Monthly demand CSV for ETL (S_month_data.csv)")
    ap.add_argument("--default-lot-size", type=int, default=50)

    # カレンダ制御
    ap.add_argument("--plan-year-st", type=int)
    ap.add_argument("--plan-range", type=int)
    ap.add_argument("--skip-calendar", action="store_true")
    ap.add_argument("--skip-etl", action="store_true")

    # モード
    ap.add_argument("--mode", choices=["leaf", "tree"], default="leaf")
    ap.add_argument("--network", help="tree モードで使う factory（pkg.module:factory）")

    # ★ 追加: factory が参照する CSV ディレクトリ
    ap.add_argument("--data-dir", default="data",
                    help="factory が参照するCSV群のディレクトリ（product_tree_*.csv 等）")

    # 出力
    ap.add_argument("--write-all-nodes", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--report-outdir", default="report")
    ap.add_argument("--report-fmt", default="png")

    return ap


def main():
    args = build_argparser().parse_args()

    # DDL
    if args.schema:
        apply_schema(args.db, args.schema)
        print(f"DDL applied: {args.db}")

    with _open(args.db) as conn:
        # ETL（必要なら）
        if args.csv and not args.skip_etl:
            run_etl(args.db, args.csv, args.scenario, args.default_lot_size)

        # カレンダ冪等整備
        pys, pr, n_weeks = _ensure_calendar(conn, args)

        if args.mode == "leaf":
            # 既存：葉ペアごとに S を生成し、両レイヤへ書き戻す
            sid = get_scenario_id(conn, args.scenario)
            pairs = _pairs_from_db(conn, sid)
            written = []
            for node_name, product_name in sorted(pairs):
                d_rows, s_rows = load_leaf_S_and_compute(conn, sid, node_name, product_name)
                if args.write_all_nodes:
                    write_both_layers(conn, sid, node_name, product_name)
                written.append({"node": node_name, "product": product_name,
                                "d_rows": int(d_rows), "s_rows": int(s_rows)})

            # レポート
            reports = []
            if args.report:
                for p in written:
                    out = _report_one(conn, args.scenario, p["node"], p["product"],
                                      "demand", args.report_outdir, args.report_fmt)
                    if out:
                        reports.append(out)

            print(json.dumps({
                "scenario": args.scenario,
                "plan_year_st": pys,
                "plan_range": pr,
                "weeks": n_weeks,
                "mode": "leaf",
                "pairs_total": len(written),
                "written": written,
                "reports": reports,
            }, ensure_ascii=False, indent=2))
            return

        # --- tree モード -------------------------------------------------
        if args.mode == "tree":
            if not args.network:
                raise ValueError("--network に 'pysi.network.factory:factory' のような指定が必要です")

            factory = _load_factory(args.network)

            # ★ data_dir を渡せる実装なら渡す。TypeError なら従来通り引数なしで呼ぶ。
            try:
                root = factory(data_dir=args.data_dir)
            except TypeError:
                root = factory()

            # tree モードの最低限のルーチン（必要に応じて拡張）
            # ここでは単に root が得られたことを確認し、DB への書き戻し等は
            # 既存の write_both_layers 等を使ってアプリ方針に合わせて実装してください。
            print(json.dumps({
                "scenario": args.scenario,
                "plan_year_st": pys,
                "plan_range": pr,
                "weeks": n_weeks,
                "mode": "tree",
                "root_node": getattr(root, "name", "<unknown>"),
                "data_dir": str(Path(args.data_dir).resolve()),
            }, ensure_ascii=False, indent=2))

            # 例：全ペア書戻しやレポートを tree でも行いたい場合は、leaf と同様にここで呼べます。
            if args.write_all_nodes:
                sid = get_scenario_id(conn, args.scenario)
                pairs = _pairs_from_db(conn, sid)
                for node_name, product_name in pairs:
                    write_both_layers(conn, sid, node_name, product_name)

            if args.report:
                if fetch_weekly_counts is not None:
                    sid = get_scenario_id(conn, args.scenario)
                    pairs = _pairs_from_db(conn, sid)
                    outs = []
                    for node_name, product_name in sorted(pairs):
                        out = _report_one(conn, args.scenario, node_name, product_name,
                                          "demand", args.report_outdir, args.report_fmt)
                        if out:
                            outs.append(out)
                    print(json.dumps({"reports": outs}, ensure_ascii=False, indent=2))
            return


if __name__ == "__main__":
    main()
