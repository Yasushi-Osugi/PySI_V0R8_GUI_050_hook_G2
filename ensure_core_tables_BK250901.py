# ensure_core_tables.py
from __future__ import annotations
import sqlite3
from pathlib import Path

CORE_DDL = {
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
"scenario": """
CREATE TABLE IF NOT EXISTS scenario (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  name          TEXT NOT NULL UNIQUE,
  plan_year_st  INTEGER NOT NULL,
  plan_range    INTEGER NOT NULL,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
""",
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
"weekly_demand_idx": """
CREATE INDEX IF NOT EXISTS idx_weekly_qry
  ON weekly_demand (scenario_id, node_id, product_id, iso_year, iso_week);
""",
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

def ensure_core(db_path: str) -> None:
    dbp = Path(db_path)
    dbp.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(dbp)) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")

        # 既存テーブルを取得
        existing = {
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

        created = []
        # 1) テーブル本体（存在しなければ作成）
        for key in ("calendar_iso","scenario","node","product","node_product",
                    "monthly_demand_stg","lot","lot_bucket"):
            sql = CORE_DDL[key]
            try:
                conn.executescript(sql)
                if key not in existing:
                    created.append(key)
            except sqlite3.Error as e:
                print(f"[ERR] create {key}: {e}")

        # 2) 週次需要のインデックス（weekly_demandがある場合のみ）
        if "weekly_demand" in existing:
            conn.executescript(CORE_DDL["weekly_demand_idx"])

        # 3) 補助インデックス
        conn.executescript(CORE_DDL["lot_idx"])
        conn.executescript(CORE_DDL["lot_bucket_idx"])

        # レポート
        print(f"[OK] ensure_core done for {dbp.resolve()}")
        if created:
            print("  created tables:", ", ".join(created))
        else:
            print("  no new tables were created (already present).")

if __name__ == "__main__":
    ensure_core("var/psi.sqlite")
