# pysi/io/tree_writeback.py

from __future__ import annotations
import sqlite3
from typing import Iterable, List, Optional, Sequence, Set, Tuple
from pathlib import Path

# ---- DBユーティリティ -------------------------------------------------

def _get_id(conn: sqlite3.Connection, table: str, name: str) -> int:
    row = conn.execute(f"SELECT id FROM {table} WHERE name=?", (name,)).fetchone()
    if row:
        return int(row[0])
    conn.execute(f"INSERT INTO {table}(name) VALUES (?)", (name,))
    return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])

def _week_index(conn: sqlite3.Connection, iso_year: int, iso_week: int) -> int:
    row = conn.execute(
        "SELECT week_index FROM calendar_iso WHERE iso_year=? AND iso_week=?",
        (iso_year, iso_week)
    ).fetchone()
    if not row:
        raise ValueError(f"calendar_iso に {iso_year}-W{iso_week:02d} がありません")
    return int(row[0])

# ---- ペア抽出（DB / PlanNode） -----------------------------------------

def pairs_from_weekly_demand(conn: sqlite3.Connection, scenario_id: int) -> Set[Tuple[str, str]]:
    rows = conn.execute("""
        SELECT n.name, p.name
        FROM weekly_demand wd
        JOIN node n    ON wd.node_id = n.id
        JOIN product p ON wd.product_id = p.id
        WHERE wd.scenario_id=?
        GROUP BY n.name, p.name
    """, (scenario_id,)).fetchall()
    return {(r[0], r[1]) for r in rows}

def node_names_from_plan_root(root) -> Set[str]:
    names: Set[str] = set()
    def dfs(n):
        names.add(getattr(n, "name", None))
        for c in getattr(n, "children", []) or []:
            dfs(c)
    dfs(root)
    names.discard(None)
    return names

def intersect_pairs_with_network(db_pairs: Set[Tuple[str, str]],
                                 net_nodes: Set[str]) -> Set[Tuple[str, str]]:
    return {(n, prod) for (n, prod) in db_pairs if n in net_nodes}

# ---- 計算＆書戻し（DBネイティブ版） -----------------------------------

def compute_leaf_S_for_pair(conn: sqlite3.Connection, *,
                            scenario_id: int,
                            node_name: str,
                            product_name: str) -> dict:
    """
    互換API：GUIを使わず“DBだけ”で完結する方針なので、ここでは前処理は不要。
    将来、事前検算が必要ならここで行う。今は no-op。
    """
    return {"d_rows": 0, "s_rows": 0}

def write_both_layers_for_pair(conn: sqlite3.Connection, *,
                               scenario_id: int,
                               node_name: str,
                               product_name: str) -> dict:
    """
    weekly_demand を正として、lot / lot_bucket を“決定的なIDで”再生成（冪等）する。
    - 既存 pair の lot/lot_bucket はシンプルに削除 → 再投入（同一生成式なら何度でも同結果）
    - demand/supply 両レイヤに 'S' をミラー（初期状態）
    """
    nid = _get_id(conn, "node", node_name)
    pid = _get_id(conn, "product", product_name)

    # 入力（正本）
    rows = conn.execute("""
        SELECT iso_year, iso_week, value
        FROM weekly_demand
        WHERE scenario_id=? AND node_id=? AND product_id=?
        ORDER BY iso_year, iso_week
    """, (scenario_id, nid, pid)).fetchall()

    # 既存を削除（この pair のみ）
    conn.execute("DELETE FROM lot_bucket WHERE scenario_id=? AND node_id=? AND product_id=?",
                 (scenario_id, nid, pid))
    conn.execute("DELETE FROM lot WHERE scenario_id=? AND node_id=? AND product_id=?",
                 (scenario_id, nid, pid))

    d_rows = 0
    s_rows = 0

    for iso_year, iso_week, val in rows:
        count = int(val or 0)
        if count <= 0:
            continue
        widx = _week_index(conn, int(iso_year), int(iso_week))
        for j in range(1, count + 1):
            lot_id = f"{scenario_id}-{nid}-{pid}-{int(iso_year):04d}W{int(iso_week):02d}-{j:03d}"

            # lot（存在保証）
            conn.execute("""
                INSERT OR REPLACE INTO lot
                    (scenario_id, node_id, product_id, iso_year, iso_week, lot_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (scenario_id, nid, pid, int(iso_year), int(iso_week), lot_id))

            # demandレイヤ：S
            conn.execute("""
                INSERT OR REPLACE INTO lot_bucket
                    (scenario_id, layer, node_id, product_id, week_index, bucket, lot_id)
                VALUES (?, 'demand', ?, ?, ?, 'S', ?)
            """, (scenario_id, nid, pid, widx, lot_id))
            d_rows += 1

            # supplyレイヤ：初期は demand をミラー（必要に応じて別ロジックに差し替え可）
            conn.execute("""
                INSERT OR REPLACE INTO lot_bucket
                    (scenario_id, layer, node_id, product_id, week_index, bucket, lot_id)
                VALUES (?, 'supply', ?, ?, ?, 'S', ?)
            """, (scenario_id, nid, pid, widx, lot_id))
            s_rows += 1

    conn.commit()
    return {"d_rows": d_rows, "s_rows": s_rows}
