# pysi/plugins/scenario_preload_json.py

# 現在の配置（提案）
# pysi/plugins/scenario_preload_json.py（単一ファイル）
# autoload_plugins("pysi.plugins") は pkgutil.iter_modules(pkg.__path__) で pysi/plugins/ 配下の .py モジュールも検出・import します。
# 従って、この形は そのままでOK です。追加の __init__.py 調整は不要です。

# 以前の配置（これまでの方式）
# pysi/plugins/scenario_preload_json/plugin.py（サブパッケージ + plugin.py）
# この場合、autoload_plugins は pysi.plugins.scenario_preload_json パッケージを import しますが、
# その __init__.py 内で from .plugin import * などを実行して、@filter デコレータ登録が走るようにしておく必要があります。

# つまり、ディレクトリ方式を使う場合は __init__.py の中継が必須です。

# 結論：どちらの方式でも動作します。
# 単一モジュール方式（今回の scenario_preload_json.py）は、追加の仕込みなしで自動ロードされやすいのでシンプル。
# ディレクトリ方式を続ける場合は、__init__.py に from .plugin import * を記述してください。

import json
from pathlib import Path
from pysi.core.hooks.core import filter as hook_filter



@hook_filter("scenario:preload", priority=50)
def load_scenario_json(spec, **ctx):
    """
    examples/scenarios/<scenario_id>/scenario.json を読み込み、
    その内容を spec["scenario"] に注入します。

    目的：
      - シナリオごとに plugins ON/OFF・個別パラメータ（config）・目的関数等を、JSONで管理
      - Pipeline.run 内の `spec = hooks.apply_filters("scenario:preload", spec, ...)` で適用される

    期待するディレクトリ構成例：
      examples/
        scenarios/
          v0r7_rice/
            scenario.json               <-- 本プラグインが読むファイル
            product_tree_inbound.csv
            product_tree_outbound.csv
            sku_cost_table_inbound.csv
            sku_cost_table_outbound.csv
            node_geo.csv
            sku_P_month_data.csv
            sku_S_month_data.csv
            tariff_table.csv

    JSON例（サンプル）：
      {
        "id": "RICE_V0R7_DEMO",
        "timebase": { "weeks": 5, "iso_year_start": 2025, "iso_week_start": 1 },
        "plugins": {
          "enable": [
            "pysi.plugins.urgency_tickets",
            "pysi.plugins.capacity_clip"
          ],
          "config": {
            "pysi.plugins.capacity_clip": { "clip_mode": "hard" }
          }
        },
        "objective": {
          "weights": { "fill_rate": 1.0, "inventory": 0.2 }
        }
      }

    備考：
      - ファイルが無い・パース失敗の場合は spec を変更せず、そのまま返す
    """
    # spec or ctx からパス情報を取得
    db_path     = spec.get("db_path") or ctx.get("db_path") or "."
    scenario_id = spec.get("scenario_id") or ""

    p = Path(db_path) / scenario_id / "scenario.json"
    if p.exists():
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            spec["scenario"] = obj
        except Exception:
            # ロギングは上位の logger（ctx["logger"]）があればそちらに任せる
            # ここでは安全側に倒して握りつぶす（specは変更しない）
            pass
    return spec
