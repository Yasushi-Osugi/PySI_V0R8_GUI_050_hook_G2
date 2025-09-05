# orchestrator.py
# -*- coding: utf-8 -*-
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
from typing import Callable, Iterable, List, Optional, Sequence, Set, Tuple



# ---- 既存モジュール（前段ステップで提示済み） ----
# calendar
#from calendar_iso import ensure_calendar_iso

from pysi.db.apply_schema import apply_schema
from pysi.db.calendar_sync import sync_calendar_iso
from pysi.etl.etl_monthly_to_lots import run_etl


from pysi.io.psi_io_adapters import (
    _open, get_scenario_id, get_scenario_bounds,  # ★ 追加
    load_leaf_S_and_compute, write_both_layers
)



# 冪等パス（Step7）
try:
    from pysi.plan.run_pass import run_idempotent_demand_pass
except Exception:
    run_idempotent_demand_pass = None

# レポート（Step6）
try:
    from pysi.report.psi_report import fetch_weekly_counts, get_scenario_id as _rep_get_scenario_id, get_node_id as _rep_get_node_id, get_product_id as _rep_get_product_id, plot_weekly

except Exception:
    fetch_weekly_counts = None

# PlannerのPlanNode
try:
    from pysi.network.node_base import PlanNode
except Exception as e:
    PlanNode = None


# --------------------------
# Helpers
# --------------------------
def _parse_list(arg: Optional[str]) -> Optional[List[str]]:
    if not arg:
        return None
    return [s.strip() for s in arg.split(",") if s.strip()]

def _import_factory(spec: str) -> Callable[[], object]:
    """
    'pkg.module:factory' を import してコール可能な関数を返す
    """
    if ":" not in spec:
        raise ValueError("--network は 'pkg.module:factory' 形式で指定してください")
    mod, fn = spec.split(":", 1)
    m = importlib.import_module(mod)
    f = getattr(m, fn)
    if not callable(f):
        raise TypeError(f"{spec} は関数ではありません")
    return f

def _scenario_bounds_from_csv(csv_path: str) -> Tuple[int, int]:
    # compute_plan_bounds は (start, range) を返す
    import pandas as pd
    df = pd.read_csv(csv_path)
    from etl_monthly_to_lots import normalize_monthly_csv
    df = normalize_monthly_csv(csv_path)
    b = compute_plan_bounds(df)
    return int(b.plan_year_st), int(b.plan_range)




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
    if not args.skip_calendar:
        if sid is not None:
            n_weeks = sync_calendar_iso(conn, scenario_id=sid)  # ← calendar_sync.py のAPIに合わせる
        else:
            # CSVやCLIで境界が決まっている場合はこちらで同期
            n_weeks = sync_calendar_iso(conn, plan_year_st=int(plan_year_st), plan_range=int(plan_range))
    else:
        cur = conn.execute("SELECT COUNT(*) FROM calendar_iso")
        n_weeks = int(cur.fetchone()[0] or 0)

    return int(plan_year_st), int(plan_range), int(n_weeks)



def _pairs_from_lot(conn: sqlite3.Connection, scenario_id: int) -> Set[Tuple[str,str]]:
    sql = """
    SELECT n.name, p.name
    FROM lot l
    JOIN node n ON n.id=l.node_id
    JOIN product p ON p.id=l.product_id
    WHERE l.scenario_id=?
    GROUP BY n.name, p.name
    ORDER BY n.name, p.name
    """
    return {(r[0], r[1]) for r in conn.execute(sql, (scenario_id,)).fetchall()}

def _filter_pairs(pairs: Set[Tuple[str,str]], nodes: Optional[Sequence[str]], products: Optional[Sequence[str]]) -> List[Tuple[str,str]]:
    out = []
    for n, p in sorted(pairs):
        if nodes and n not in nodes:
            continue
        if products and p not in products:
            continue
        out.append((n, p))
    return out

def _iter_tree(root) -> Iterable[object]:
    stack = [root]
    while stack:
        n = stack.pop()
        yield n
        for c in getattr(n, "children", []) or []:
            stack.append(c)

def _leaves_of(root) -> List[object]:
    return [n for n in _iter_tree(root) if not getattr(n, "children", [])]

def _report_one(conn: sqlite3.Connection, scenario: str, node: str, product: str, layer: str, outdir: str, fmt: str) -> Optional[str]:
    if fetch_weekly_counts is None:
        return None
    sid = _rep_get_scenario_id(conn, scenario)
    nid = _rep_get_node_id(conn, node)
    pid = _rep_get_product_id(conn, product)
    import os
    df = fetch_weekly_counts(conn, sid, nid, pid, layer)
    os.makedirs(outdir, exist_ok=True)
    base = os.path.join(outdir, f"{scenario}_{layer}_{node}_{product}")
    title = f"{scenario} / {layer} / {node} / {product}"
    img = plot_weekly(df, title, f"{base}_weekly_chart", fmt=fmt, show=False)
    df.to_csv(f"{base}_weekly_counts.csv", index=False, encoding="utf-8-sig")
    return img


# --------------------------
# Main flow
# --------------------------
def main():
    ap = argparse.ArgumentParser(description="Global Weekly PSI Planner Orchestrator")
    ap.add_argument("--db", required=True)
    ap.add_argument("--scenario", required=True)

    ap.add_argument("--schema", help="schema.sql path")
    ap.add_argument("--skip-schema", action="store_true")

    ap.add_argument("--csv", help="monthly demand CSV (optional)")
    ap.add_argument("--skip-etl", action="store_true")

    ap.add_argument("--plan-year-st", type=int)
    ap.add_argument("--plan-range", type=int)
    ap.add_argument("--skip-calendar", action="store_true")

    ap.add_argument("--default-lot-size", type=int)

    ap.add_argument("--mode", choices=["leaf","tree"], default="leaf")
    ap.add_argument("--network", help="pkg.module:factory (tree mode)")
    ap.add_argument("--write-all-nodes", action="store_true")

    ap.add_argument("--nodes", help="comma separated node names")
    ap.add_argument("--products", help="comma separated product names")

    ap.add_argument("--report", action="store_true")
    ap.add_argument("--report-outdir", default="report")
    ap.add_argument("--report-fmt", choices=["png","svg","pdf"], default="png")

    ap.add_argument("--data-dir", default="data",
                help="factory が参照するCSV群のディレクトリ（product_tree_*.csv 等）")


    args = ap.parse_args()

    # 1) Schema
    if args.schema and not args.skip_schema:
        if apply_schema is None:
            raise RuntimeError("apply_schema が見つかりません。schema適用は --skip-schema でスキップできます。")
        apply_schema(args.db, args.schema)

    # 2) ETL
    if args.csv and not args.skip_etl:
        run_etl(args.db, args.csv, args.scenario, args.default_lot_size)

    # 3) Calendar
    conn = _open(args.db)
    pys, pr, n_weeks = _ensure_calendar(conn, args)
    scenario_id = get_scenario_id(conn, args.scenario)

    # 4) 対象 (node, product) の決定
    pairs = _pairs_from_lot(conn, scenario_id)
    nodes = _parse_list(args.nodes)
    products = _parse_list(args.products)
    targets = _filter_pairs(pairs, nodes, products)

    if not targets and args.mode == "leaf":
        print("[WARN] lot が空か、指定に一致する (node,product) が見つかりません。ETLの実行/条件を確認してください。")

    summary = {
        "scenario": args.scenario,
        "plan_year_st": pys,
        "plan_range": pr,
        "weeks": n_weeks,
        "mode": args.mode,
        "pairs_total": len(targets),
        "written": [],
        "reports": []
    }

    # 5) Engine
    if args.mode == "leaf":
        if PlanNode is None:
            raise RuntimeError("PlanNode が import できません。PYTHONPATH を確認してください。")
        for node_name, product_name in targets:
            node_obj = PlanNode(node_name)
            load_leaf_S_and_compute(conn, scenario_id=scenario_id, node_obj=node_obj, product_name=product_name, layer="demand")
            d_rows, s_rows = write_both_layers(conn, scenario_id=scenario_id, node_obj=node_obj, product_name=product_name, replace_slice=True)
            summary["written"].append({"node": node_name, "product": product_name, "d_rows": d_rows, "s_rows": s_rows})
            if args.report:
                img = _report_one(conn, args.scenario, node_name, product_name, "demand", args.report_outdir, args.report_fmt)
                if img: summary["reports"].append(img)

    else:  # tree
        if not args.network:
            raise ValueError("tree モードでは --network を指定してください（例: pkg.module:build_network）")
        factory = _import_factory(args.network)
        root = factory()  # 既存コードのネットワークビルダ：root PlanNode を返す想定
        if PlanNode is None:
            raise RuntimeError("PlanNode が import できません。PYTHONPATH を確認してください。")

        # leaf 推定：ツリーの葉に対して DB の lot から該当する product を注入
        leaf_nodes = _leaves_of(root)
        leaf_names = {ln.name for ln in leaf_nodes}
        leaf_pairs = [(n, p) for (n, p) in targets if n in leaf_names]

        for node_name, product_name in leaf_pairs:
            # ツリー上の該当ノードを見つける
            leaf_node = next((ln for ln in leaf_nodes if ln.name == node_name), None)
            if leaf_node is None:
                print(f"[WARN] leaf '{node_name}' がツリーに存在しません。スキップします。")
                continue
            load_leaf_S_and_compute(conn, scenario_id=scenario_id, node_obj=leaf_node, product_name=product_name, layer="demand")

        # 冪等パスで全体計算
        if run_idempotent_demand_pass is None:
            raise RuntimeError("run_idempotent_demand_pass が見つかりません。Step7 のパッチを適用してください。")
        run_idempotent_demand_pass(root)

        # 書き戻し：rootのみ or 全ノード
        nodes_to_write = list(_iter_tree(root)) if args.write_all_nodes else [root]
        for n in nodes_to_write:
            # プロダクトは DB で leafにあったものを使うか、明示指定があればそれを優先
            prods_for_node = {p for (nn, p) in targets if nn == n.name} or (set(products) if products else set())
            if not prods_for_node:
                # ツリー全ノードに対して同一の product 群を処理したい場合は --products を指定してください
                continue
            for product_name in sorted(prods_for_node):
                d_rows, s_rows = write_both_layers(conn, scenario_id=scenario_id, node_obj=n, product_name=product_name, replace_slice=True)
                summary["written"].append({"node": n.name, "product": product_name, "d_rows": d_rows, "s_rows": s_rows})
                if args.report:
                    img = _report_one(conn, args.scenario, n.name, product_name, "demand", args.report_outdir, args.report_fmt)
                    if img: summary["reports"].append(img)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
