# pysi/app/run_once.py

#ポイント
#run_once(cfg, bus=None, io=None, logger=None)：GUI側で生成した HookBus / CSVAdapter / logger をそのまま渡して使えます。
#plugins_dir を sys.path に追加後、autoload_plugins("pysi.plugins") で自動ロード。
#calendar は cfg["calendar"] があれば優先、なければ weeks/iso_year_start/iso_week_start を拾って正規化。
#scenario_id は scenario_id → scenario → "" の順でフォールバック。
#out_dir は out_dir → out → "out" の順でフォールバック。


from __future__ import annotations

import sys, uuid
from typing import Any, Dict, Optional

from pysi.core.hooks.core import HookBus, set_global, autoload_plugins
from pysi.core.pipeline import Pipeline
from pysi.io_adapters.csv_adapter import CSVAdapter
# SQL を使う場合は適宜インポート
# from pysi.io_adapters.sql_adapter import SQLAdapter

def _make_calendar_from_cfg(cfg: Dict[str, Any]) -> Dict[str, int]:
    """GUI/CLI どちらの形式でも受け取れるよう、calendar を合成"""
    cal = cfg.get("calendar") or {}
    iso_year = int(cal.get("iso_year_start", cfg.get("iso_year_start", 2025)))
    iso_week = int(cal.get("iso_week_start", cfg.get("iso_week_start", 1)))
    weeks    = int(cal.get("weeks",          cfg.get("weeks", 3)))
    return {
        "iso_year_start": iso_year,
        "iso_week_start": iso_week,
        "weeks": weeks,
    }

def run_once(cfg: Dict[str, Any],
             bus: Optional[HookBus] = None,
             io: Optional[CSVAdapter] = None,
             logger=None):
    """
    cfg 例（GUIから）:
      {
        "root": ".../examples/scenarios/v0r7_rice",
        "scenario": "v0r7_rice",          # or "scenario_id"
        "plugins_dir": "./plugins",       # GUIでは var_plugins
        "weeks": 3, "iso_year_start": 2025, "iso_week_start": 1,
        "out": ".../_out"                 # or "out_dir"
      }
    """

    run_id = str(uuid.uuid4())[:8]
    if logger:
        logger.info(f"run_id={run_id} start")

    # ---- HookBus を用意 & グローバルへ設定
    bus = bus or HookBus(logger=logger)
    set_global(bus)

    # ---- プラグインを読み込み（GUI側でも読むなら二重ロードに注意）
    plugins_dir = cfg.get("plugins_dir") or cfg.get("plugins")
    if plugins_dir:
        if plugins_dir not in sys.path:
            sys.path.insert(0, plugins_dir)
    autoload_plugins("pysi.plugins")

    # ---- IO アダプタ（ここでは CSV 前提。SQL 使う場合は適宜分岐）
    io = io or CSVAdapter(root=cfg.get("root"), schema_cfg=cfg.get("schema_cfg"), logger=logger)

    # ---- 呼び出し引数を正規化
    scenario_id = cfg.get("scenario_id") or cfg.get("scenario") or ""
    calendar    = _make_calendar_from_cfg(cfg)
    db_path     = cfg.get("root") or cfg.get("db_path") or "."
    out_dir     = cfg.get("out_dir") or cfg.get("out") or "out"

    # ---- 実行
    pipe = Pipeline(hooks=bus, io=io, logger=logger)
    result = pipe.run(db_path=db_path,
                      scenario_id=scenario_id,
                      calendar=calendar,
                      out_dir=out_dir)

    if logger:
        logger.info(f"run_id={run_id} done")
    return result
