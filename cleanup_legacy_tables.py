# cleanup_legacy_tables.py

# 実行方法
# python cleanup_legacy_tables.py --db var\psi.sqlite
# python db_inspect.py --db var\psi.sqlite --sql

## ① スキーマ適用（冪等）※既にOKなら省略可
# python -c "from pysi.db.apply_schema import apply_schema; apply_schema('var/psi.sqlite','pysi/db/schema.sql')"

## ② ETL（CSV→週→lot）
# python -m pysi.app.orchestrator --db var\psi.sqlite --scenario Baseline --schema pysi\db\schema.sql --csv data\S_month_data.csv


from __future__ import annotations
import sqlite3, argparse, os, csv, time, pathlib

PATTERNS = ["%_legacy_fk", "%_legacy"]  # 旧世代の退避テーブルを全捕捉

def export_table_to_csv(conn: sqlite3.Connection, table: str, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    rows = conn.execute(f'SELECT * FROM "{table}"').fetchall()
    if not rows:
        return ""
    cols = [c[1] for c in conn.execute(f'PRAGMA table_info("{table}")')]
    out = os.path.join(out_dir, f"{table}.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow(r)
    return out

def main():
    ap = argparse.ArgumentParser(description="Drop legacy *_legacy / *_legacy_fk tables with CSV backup.")
    ap.add_argument("--db", default="var/psi.sqlite")
    args = ap.parse_args()

    dbp = pathlib.Path(args.db).resolve()
    conn = sqlite3.connect(str(dbp))
    conn.execute("PRAGMA foreign_keys=OFF;")

    # 検出
    targets = []
    for pat in PATTERNS:
        q = "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?"
        targets += [r[0] for r in conn.execute(q, (pat,)).fetchall()]
    # ただし“正規テーブル”は除外（念のため）
    keep = {"node","product","node_product","scenario","weekly_demand","monthly_demand_stg","lot","lot_bucket","calendar_iso"}
    targets = [t for t in sorted(set(targets)) if t not in keep]

    if not targets:
        print("[OK] no legacy tables found")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.close()
        return

    # バックアップ
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join("var", "backups", f"legacy_dump_{stamp}")
    total_backed = 0
    for t in targets:
        cnt = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        if cnt:
            path = export_table_to_csv(conn, t, backup_dir)
            total_backed += cnt
            print(f"[BACKUP] {t}: {cnt} rows -> {path}")
        else:
            print(f"[BACKUP] {t}: empty (skip CSV)")

    # DROP
    for t in targets:
        conn.execute(f'DROP TABLE IF EXISTS "{t}"')
        print(f"[DROP] {t}")

    conn.commit()
    conn.execute("PRAGMA foreign_keys=ON;")

    # 新テーブルのみFKチェック
    problems = {}
    for t in ("weekly_demand","monthly_demand_stg","lot","lot_bucket"):
        rows = conn.execute(f"PRAGMA foreign_key_check('{t}')").fetchall()
        if rows:
            problems[t] = rows
    conn.close()

    print(f"[DONE] Legacy cleanup completed for {dbp}")
    if total_backed:
        print(f"       Backed up {total_backed} rows into {backup_dir}")
    print("       FK check:", "clean" if not problems else problems)

if __name__ == "__main__":
    main()
