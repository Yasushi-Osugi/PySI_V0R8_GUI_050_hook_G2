# main.py
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
import tkinter as tk

# ---- プロジェクト内モジュール（依存注入のためのimport） ----
from pysi.utils.config import Config


def _repo_root() -> Path:
    """この main.py から見たリポジトリのルートを推定（相対パス安定化）。"""
    return Path(__file__).resolve().parent


def _default_paths() -> dict[str, Path]:
    root = _repo_root()
    return {
        "db": root / "var" / "psi.sqlite",
        "schema": root / "pysi" / "db" / "schema.sql",
        "csv": root / "data" / "S_month_data.csv",  # 無ければ自動でスキップ
    }


def _ensure_parent_dir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def orchestrate_once(
    db_path: Path,
    *,
    scenario: str,
    schema_sql: Path | None,
    monthly_csv: Path | None,
    default_lot_size: int | None,
) -> None:
    """
    GUI起動前に一度だけ、スキーマ→ETL→calendar同期→S注入→書戻し を冪等実行。
    """
    # 選択的に monthly_csv を使う（存在しない場合はETLをスキップ）
    csv_for_run = str(monthly_csv) if (monthly_csv and monthly_csv.exists()) else None
    schema_for_run = str(schema_sql) if (schema_sql and schema_sql.exists()) else None

    from pysi.app.orchestrator import orchestrate

    _ensure_parent_dir(db_path)
    rows = orchestrate(
        str(db_path),
        scenario=scenario,
        schema_sql=schema_for_run,
        monthly_csv=csv_for_run,
        default_lot_size=default_lot_size,
        product_filter=None,
    )
    print(f"[orchestrate] wrote {rows} rows into lot_bucket.")


def build_env(db_path: Path, *, use_sql_backend: bool) -> object:
    """
    GUIから使う実行環境を返す。SQLバックエンドを優先。
    """
    if use_sql_backend:
        from pysi.io.sql_planenv import SqlPlanEnv

        env = SqlPlanEnv(str(db_path))
        return env
    else:
        # 旧MVP（CSV直読み）の後方互換ルート
        from pysi.psi_planner_mvp.plan_env_main import PlanEnv

        env = PlanEnv(Config())
        env.load_data_files()
        return env


def launch_gui(config: Config, psi_env: object) -> None:
    """
    Tkinter GUI を起動。env.reload() を先に呼び、DBの内容で初期化。
    """
    # DB→メモリエンジンへのリロード（SqlPlanEnv 側のメソッド）
    if hasattr(psi_env, "reload"):
        psi_env.reload()

    from pysi.gui.app import PSIPlannerApp  # GUIは core の利用者

    root = tk.Tk()
    app = PSIPlannerApp(root, config, psi_env=psi_env)  # 依存注入
    root.mainloop()


def parse_args() -> argparse.Namespace:
    d = _default_paths()
    ap = argparse.ArgumentParser(
        description="PySI GUI launcher with pre-GUI orchestration (schema/ETL/compute/writeback)."
    )
    ap.add_argument("--scenario", default=os.getenv("PYSI_SCENARIO", "Baseline"))
    ap.add_argument("--db", default=str(d["db"]), help="Path to SQLite DB (default: var/psi.sqlite)")
    ap.add_argument("--schema", default=str(d["schema"]), help="Path to schema.sql")
    ap.add_argument(
        "--csv",
        default=str(d["csv"]),
        help="Monthly demand CSV (product_name,node_name,year,m1..m12). If missing, ETL is skipped.",
    )
    ap.add_argument("--default-lot-size", type=int, default=50, help="Fallback lot size for ETL (optional)")
    ap.add_argument(
        "--backend",
        choices=["sql", "mvp"],
        default=os.getenv("PYSI_BACKEND", "sql"),
        help="sql: SqlPlanEnv (DB主導) / mvp: legacy CSV MVP",
    )
    ap.add_argument(
        "--skip-orchestrate",
        action="store_true",
        help="Skip pre-GUI orchestration (use existing DB as-is).",
    )
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    config = Config()

    db_path = Path(args.db).resolve()
    schema_sql = Path(args.schema).resolve() if args.schema else None
    csv_path = Path(args.csv).resolve() if args.csv else None
    use_sql_backend = args.backend == "sql"

    # 1) GUIの前に一度だけ orchestrate（冪等）。--skip-orchestrate で省略可能
    if use_sql_backend and not args.skip_orchestrate:
        try:
            orchestrate_once(
                db_path,
                scenario=args.scenario,
                schema_sql=schema_sql,
                monthly_csv=csv_path,
                default_lot_size=args.default_lot_size,
            )
        except Exception as e:
            # 失敗してもGUI起動自体は継続：既存DBをそのまま表示
            print(f"[WARN] Orchestration failed: {e}\n       Launching GUI with existing DB...")

    # 2) GUI用の実行環境を構築
    psi_env = build_env(db_path, use_sql_backend=use_sql_backend)

    # 3) GUI起動（env.reload → Tk mainloop）
    launch_gui(config, psi_env)


if __name__ == "__main__":
    # 実行カレントがリポジトリ直下でない場合でも相対が動くように PYTHONPATH を補助（任意）
    repo = _repo_root()
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    main()

