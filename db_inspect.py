# db_inspect.py
from __future__ import annotations
import argparse
import sqlite3
from pathlib import Path

def list_tables(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    return [r[0] for r in cur.fetchall()]

def print_tables(conn: sqlite3.Connection, *, show_counts: bool, show_sql: bool) -> None:
    tables = list_tables(conn)
    db_path = conn.execute("PRAGMA database_list").fetchone()[2]
    print("tables in", Path(db_path).resolve())
    if not tables:
        print(" (no tables)")
        return

    for t in tables:
        line = f" - {t}"
        if show_counts:
            try:
                cnt = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                line += f" (rows={cnt})"
            except sqlite3.Error:
                line += " (rows=? )"
        print(line)

        if show_sql:
            row = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (t,),
            ).fetchone()
            if row and row[0]:
                print("    ", row[0])

def main() -> None:
    ap = argparse.ArgumentParser(description="List tables in a SQLite database.")
    ap.add_argument("--db", default="var/psi.sqlite", help="Path to SQLite file")
    ap.add_argument("--counts", action="store_true", help="Show row counts")
    ap.add_argument("--sql", action="store_true", help="Show CREATE TABLE SQL")
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"[ERR] DB not found: {db_path.resolve()}")
        return

    with sqlite3.connect(str(db_path)) as conn:
        print_tables(conn, show_counts=args.counts, show_sql=args.sql)

if __name__ == "__main__":
    main()
