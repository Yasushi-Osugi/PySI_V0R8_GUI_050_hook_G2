# ensure_core_tables.py

#実行方法
## 1) コア表を安全に追加（旧 weekly_demand は自動退避）
# python ensure_core_tables.py --db var/psi.sqlite
#
## 2) 確認
# python db_inspect.py --db var/psi.sqlite --counts
#これで scenario / calendar_iso / lot / lot_bucket / monthly_demand_stg / weekly_demand（新スキーマ）が揃います。
#旧 weekly_demand は weekly_demand_legacy（または weekly_demand_legacy2 …）に残します。


from __future__ import annotations
import argparse
import sqlite3
from pathlib import Path
from typing import List, Set

REQ_WEEKLY_COLS: Set[str] = {"scenario_id", "node_id", "product_id", "iso_year", "iso_week", "value"}

DDL = {
    # 正本カレンダ
    "calendar_iso": """
    CREATE TABLE IF NOT EXISTS calendar_iso (
      week_index INTEGER PRIMARY KEY,
      iso_year   INTEGER NOT NULL,
      iso_week   INTEGER NOT NULL,
      week_start TEXT    NOT NULL,
      week_end   TEXT    NOT NULL,
      UNIQUE (iso_year, iso_week)
    );
    """,
    # シナリオ
    "scenario": """
    CREATE TABLE IF NOT EXISTS scenario (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      name          TEXT NOT NULL UNIQUE,
      plan_year_st  INTEGER NOT NULL,
      plan_range    INTEGER NOT NULL,
      created_at    TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    # ノード/製品
    "node": """
    CREATE TABLE IF NOT EXISTS node (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      longitude REAL, latitude REAL
    );
    """,
    "product": """
    CREATE TABLE IF NOT EXISTS product (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE
    );
    """,
    # ノード×製品パラメータ
    "node_product": """
    CREATE TABLE IF NOT EXISTS node_product (
      node_id INTEGER NOT NULL,
      product_id INTEGER NOT NULL,
      lot_size INTEGER NOT NULL DEFAULT 1,
      leadtime INTEGER NOT NULL DEFAULT 0,
      ss_days INTEGER NOT NULL DEFAULT 0,
      long_vacation_weeks TEXT,
      PRIMARY KEY (node_id, product_id),
      FOREIGN KEY (node_id) REFERENCES node(id) ON DELETE CASCADE,
      FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE
    );
    """,
    # 月次ステージング
    "monthly_demand_stg": """
    CREATE TABLE IF NOT EXISTS monthly_demand_stg (
      scenario_id INTEGER NOT NULL,
      node_id     INTEGER NOT NULL,
      product_id  INTEGER NOT NULL,
      year        INTEGER NOT NULL,
      m1 REAL DEFAULT 0,  m2 REAL DEFAULT 0,  m3 REAL DEFAULT 0,
      m4 REAL DEFAULT 0,  m5 REAL DEFAULT 0,  m6 REAL DEFAULT 0,
      m7 REAL DEFAULT 0,  m8 REAL DEFAULT 0,  m9 REAL DEFAULT 0,
      m10 REAL DEFAULT 0, m11 REAL DEFAULT 0, m12 REAL DEFAULT 0,
      UNIQUE (scenario_id, node_id, product_id, year),
      FOREIGN KEY (scenario_id) REFERENCES scenario(id) ON DELETE CASCADE,
      FOREIGN KEY (node_id) REFERENCES node(id) ON DELETE CASCADE,
      FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE
    );
    """,
    # 週次需要（新スキーマ）
    "weekly_demand": """
    CREATE TABLE IF NOT EXISTS weekly_demand (
      scenario_id INTEGER NOT NULL,
      node_id     INTEGER NOT NULL,
      product_id  INTEGER NOT NULL,
      iso_year    INTEGER NOT NULL,
      iso_week    INTEGER NOT NULL,
      value       REAL    NOT NULL DEFAULT 0,
      UNIQUE (scenario_id, node_id, product_id, iso_year, iso_week),
      FOREIGN KEY (scenario_id) REFERENCES scenario(id) ON DELETE CASCADE,
      FOREIGN KEY (node_id) REFERENCES node(id) ON DELETE CASCADE,
      FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE
    );
    """,
    "weekly_demand_idx": """
    CREATE INDEX IF NOT EXISTS idx_weekly_qry
      ON weekly_demand (scenario_id, node_id, product_id, iso_year, iso_week);
    """,
    # 生成 lot
    "lot": """
    CREATE TABLE IF NOT EXISTS lot (
      scenario_id INTEGER NOT NULL,
      node_id     INTEGER NOT NULL,
      product_id  INTEGER NOT NULL,
      iso_year    INTEGER NOT NULL,
      iso_week    INTEGER NOT NULL,
      lot_id      TEXT    NOT NULL,
      UNIQUE (lot_id),
      FOREIGN KEY (scenario_id) REFERENCES scenario(id) ON DELETE CASCADE,
      FOREIGN KEY (node_id) REFERENCES node(id) ON DELETE CASCADE,
      FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE
    );
    """,
    "lot_idx": """
    CREATE INDEX IF NOT EXISTS idx_lot_lookup
      ON lot (scenario_id, node_id, product_id, iso_year, iso_week);
    """,
    # エンジン出力
    "lot_bucket": """
    CREATE TABLE IF NOT EXISTS lot_bucket (
      scenario_id INTEGER NOT NULL,
      layer  TEXT NOT NULL CHECK(layer IN ('demand','supply')),
      node_id     INTEGER NOT NULL,
      product_id  INTEGER NOT NULL,
      week_index  INTEGER NOT NULL,
      bucket TEXT NOT NULL CHECK(bucket IN ('S','CO','I','P')),
      lot_id  TEXT  NOT NULL,
      UNIQUE (scenario_id, layer, node_id, product_id, week_index, bucket, lot_id),
      FOREIGN KEY (scenario_id) REFERENCES scenario(id) ON DELETE CASCADE,
      FOREIGN KEY (node_id) REFERENCES node(id) ON DELETE CASCADE,
      FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE
    );
    """,
    "lot_bucket_idx": """
    CREATE INDEX IF NOT EXISTS idx_lot_bucket_qry
      ON lot_bucket (scenario_id, layer, node_id, product_id, week_index, bucket);
    """
}

def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None

def get_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    try:
        rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    except sqlite3.Error:
        return []
    return [r[1].lower() for r in rows]  # name column

def find_free_name(conn: sqlite3.Connection, base: str) -> str:
    """weekly_demand_legacy, weekly_demand_legacy2, ... のように衝突回避"""
    name = f"{base}_legacy"
    i = 2
    while table_exists(conn, name):
        name = f"{base}_legacy{i}"
        i += 1
    return name

def ensure_weekly_demand(conn: sqlite3.Connection) -> str:
    """
    weekly_demand が無い → 新規作成。
    あるが列不足 → 旧表をリネームして退避し、新スキーマで作り直し（移行は行わない）。
    戻り値：実体として使用する weekly_demand のテーブル名（通常 'weekly_demand'）
    """
    if not table_exists(conn, "weekly_demand"):
        conn.executescript(DDL["weekly_demand"])
        conn.executescript(DDL["weekly_demand_idx"])
        return "weekly_demand"

    cols = set(get_columns(conn, "weekly_demand"))
    if REQ_WEEKLY_COLS.issubset(cols):
        # 既に要件を満たしている → インデックスだけ保証
        conn.executescript(DDL["weekly_demand_idx"])
        return "weekly_demand"

    # 列不足 → 退避リネームして新設
    legacy_name = find_free_name(conn, "weekly_demand")
    conn.execute(f'ALTER TABLE "weekly_demand" RENAME TO "{legacy_name}"')
    conn.executescript(DDL["weekly_demand"])
    conn.executescript(DDL["weekly_demand_idx"])
    print(f"[INFO] Renamed legacy weekly_demand -> {legacy_name} (kept for reference)")
    return "weekly_demand"

def ensure_core(db_path: str) -> None:
    dbp = Path(db_path)
    dbp.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(dbp)) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")

        # テーブル本体（存在しなければ作成）
        for key in ("calendar_iso","scenario","node","product","node_product","monthly_demand_stg","lot","lot_bucket"):
            conn.executescript(DDL[key])

        # 週次需要（検査→必要なら退避→新設）
        wd_name = ensure_weekly_demand(conn)

        # 補助インデックス
        conn.executescript(DDL["lot_idx"])
        conn.executescript(DDL["lot_bucket_idx"])

        print(f"[OK] ensure_core done for {dbp.resolve()}")
        print(f"     weekly_demand in use: {wd_name}")

def main():
    ap = argparse.ArgumentParser(description="Ensure PSI core tables exist (non-destructive).")
    ap.add_argument("--db", default="var/psi.sqlite", help="SQLite DB path (default: var/psi.sqlite)")
    args = ap.parse_args()
    ensure_core(args.db)

if __name__ == "__main__":
    main()
