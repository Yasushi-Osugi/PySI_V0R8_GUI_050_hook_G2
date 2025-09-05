# repair_fk_legacy_refs.py

## 実行手順# 1) 修復
# python repair_fk_legacy_refs.py --db var\psi.sqlite
#
## 2) CREATE文の再確認（node_legacy/product_legacy が消えていること）
# python db_inspect.py --db var\psi.sqlite --sql
## → lot, lot_bucket, monthly_demand_stg, weekly_demand の FOREIGN KEY が
##    node(id), product(id) を指すことを確認
#
## 3) 念のため FK 整合性チェック（問題があれば表示されます）
#python - << 'PY'
#import sqlite3
#con=sqlite3.connect(r"var/psi.sqlite")
#con.execute("PRAGMA foreign_keys=ON;")
#print("fk_check:", con.execute("PRAGMA foreign_key_check").fetchall())
#con.close()
#PY



from __future__ import annotations
import argparse, sqlite3
from pathlib import Path

DDL = {
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
      FOREIGN KEY (node_id)     REFERENCES node(id)      ON DELETE CASCADE,
      FOREIGN KEY (product_id)  REFERENCES product(id)   ON DELETE CASCADE
    );
    """,
    "weekly_demand_idx": """
    CREATE INDEX IF NOT EXISTS idx_weekly_qry
      ON weekly_demand (scenario_id, node_id, product_id, iso_year, iso_week);
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
      FOREIGN KEY (node_id)     REFERENCES node(id)      ON DELETE CASCADE,
      FOREIGN KEY (product_id)  REFERENCES product(id)   ON DELETE CASCADE
    );
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
      FOREIGN KEY (node_id)     REFERENCES node(id)      ON DELETE CASCADE,
      FOREIGN KEY (product_id)  REFERENCES product(id)   ON DELETE CASCADE
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
      FOREIGN KEY (node_id)     REFERENCES node(id)      ON DELETE CASCADE,
      FOREIGN KEY (product_id)  REFERENCES product(id)   ON DELETE CASCADE
    );
    """,
    "lot_bucket_idx": """
    CREATE INDEX IF NOT EXISTS idx_lot_bucket_qry
      ON lot_bucket (scenario_id, layer, node_id, product_id, week_index, bucket);
    """,
}

TARGETS = [
    ("weekly_demand", ["scenario_id","node_id","product_id","iso_year","iso_week","value"], ["weekly_demand_idx"]),
    ("monthly_demand_stg", ["scenario_id","node_id","product_id","year","m1","m2","m3","m4","m5","m6","m7","m8","m9","m10","m11","m12"], []),
    ("lot", ["scenario_id","node_id","product_id","iso_year","iso_week","lot_id"], ["lot_idx"]),
    ("lot_bucket", ["scenario_id","layer","node_id","product_id","week_index","bucket","lot_id"], ["lot_bucket_idx"]),
]

def needs_fix(sql: str) -> bool:
    if not sql: return False
    sql_low = sql.lower()
    return ('"node_legacy"' in sql_low) or ('"product_legacy"' in sql_low) or (" node_legacy" in sql_low) or (" product_legacy" in sql_low)

def pragmatic_copy(conn: sqlite3.Connection, old: str, new: str, cols: list[str]) -> int:
    # 旧→新へ共通列だけコピー（不足列は無視）
    cur_cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{old}")')]
    common = [c for c in cols if c in cur_cols]
    if not common:
        return 0
    cols_csv = ",".join(common)
    sql = f'INSERT OR IGNORE INTO "{new}"({cols_csv}) SELECT {cols_csv} FROM "{old}"'
    return conn.execute(sql).rowcount

def repair(db_path: str):
    dbp = Path(db_path)
    with sqlite3.connect(str(dbp)) as conn:
        conn.execute("PRAGMA foreign_keys=OFF;")  # 再定義中は一旦OFF（SQLite慣習）
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")

        changed = []
        for tbl, cols, idxs in TARGETS:
            row = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tbl,)
            ).fetchone()
            if not row:
                # 無ければ新規作成
                conn.executescript(DDL[tbl])
                for idx in idxs: conn.executescript(DDL[idx])
                print(f"[CREATE] {tbl}")
                continue

            create_sql = row[0] or ""
            if not needs_fix(create_sql):
                # 参照OK → インデックス保証
                for idx in idxs: conn.executescript(DDL[idx])
                continue

            # レガシー参照 → リビルド
            legacy = f"{tbl}_legacy_fk"
            conn.execute(f'ALTER TABLE "{tbl}" RENAME TO "{legacy}"')
            conn.executescript(DDL[tbl])
            for idx in idxs: conn.executescript(DDL[idx])

            copied = pragmatic_copy(conn, legacy, tbl, cols)
            print(f"[REBUILD] {tbl} (from {legacy}) rows_copied={copied}")
            changed.append(tbl)

        conn.execute("PRAGMA foreign_keys=ON;")
        # 実効性チェック
        problems = list(conn.execute("PRAGMA foreign_key_check").fetchall())

    print(f"[OK] repair complete: {dbp.resolve()}")
    if changed:
        print("  fixed tables:", ", ".join(changed))
    if problems:
        print("  [WARN] foreign_key_check returned rows ->", problems)
    else:
        print("  foreign_key_check: clean")

def main():
    ap = argparse.ArgumentParser(description="Repair legacy FKs (node_legacy/product_legacy) to current node/product.")
    ap.add_argument("--db", default="var/psi.sqlite")
    args = ap.parse_args()
    repair(args.db)

if __name__ == "__main__":
    main()

