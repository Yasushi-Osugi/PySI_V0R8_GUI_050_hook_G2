# pysi/core/pipeline.py
# pysi/core/pipeline.py

# pysi.plan.psi_dual の 3関数（settle_events_to_P, roll_and_merge_I, consume_S_from_I_ids）
# および init_psi_map を利用し、V0R7の「二層（demand/supply）×週次[S,CO,I,P]（lot-IDのリスト正本）」を
# そのまま正本に保ったまま週次ループを回します。

# 変更点の要約
# V0R7準拠の正本（二層 demand/supply × 週次[S,CO,I,P]（lot-IDのリスト））を維持しつつ、
# psi_dual のユーティリティで 週頭イベント → P(w) → Iロールフォワード → I→Sの消し込み を行う
# 週次ループに更新。

# raw["tree_inbound"] / raw["tree_outbound"] など V0R7のCSVをDataFrameで raw に入れる前提
# （前段で更新した CSVAdapter.load_all() と整合）。

# GUIプレビュー用に root["state"]["hist"] に {"week_idx": w, "inventory": 合計在庫数} を追記
# （後段の to_series_df() がこの履歴を最優先で使える）。

# report:exporters フックでプラグイン側の Exporter 一覧を差し替え可能に（後方互換：空でもOK）。

from __future__ import annotations
from typing import Any, Dict, List
from pysi.core.hooks.core import HookBus
from pysi.plan.psi_dual import (
    PSI_S, PSI_CO, PSI_I, PSI_P,
    init_psi_map,
    settle_events_to_P,
    roll_and_merge_I,
    consume_S_from_I_ids,
)

class Pipeline:
    """段階型パイプライン。全Hookはここを通る。"""
    def __init__(self, hooks: HookBus, io, logger=None):
        self.hooks, self.io, self.logger = hooks, io, logger

    def run(self, db_path: str, scenario_id: str, calendar: Dict[str, Any], out_dir: str = "out"):
        run_id = calendar.get("run_id")

        # ---- Timebase ----
        calendar = self.hooks.apply_filters(
            "timebase:calendar:build", calendar,
            db_path=db_path, scenario_id=scenario_id, logger=self.logger, run_id=run_id
        )

        # ---- Data Load ----
        self.hooks.do_action(
            "before_data_load",
            db_path=db_path, scenario_id=scenario_id, logger=self.logger, run_id=run_id
        )
        spec = {"db_path": db_path, "scenario_id": scenario_id}
        spec = self.hooks.apply_filters(
            "scenario:preload", spec,
            db_path=db_path, scenario_id=scenario_id, logger=self.logger, run_id=run_id
        )
        raw = self.io.load_all(spec)
        self.hooks.do_action(
            "after_data_load",
            db_path=db_path, scenario_id=scenario_id, raw=raw, logger=self.logger, run_id=run_id
        )

        # ---- Tree Build ----
        self.hooks.do_action(
            "before_tree_build",
            db_path=db_path, scenario_id=scenario_id, raw=raw, logger=self.logger
        )
        root = self.io.build_tree(raw)
        root = self.hooks.apply_filters(
            "plan:graph:build", root,
            db_path=db_path, scenario_id=scenario_id, raw=raw, logger=self.logger
        )
        root = self.hooks.apply_filters(
            "opt:network_design", root,
            db_path=db_path, scenario_id=scenario_id, logger=self.logger
        )
        self.hooks.do_action(
            "after_tree_build",
            db_path=db_path, scenario_id=scenario_id, root=root, logger=self.logger
        )


        # ---- 修正: ここから追加 ----
        
        # 1. ツリーに正しい計画期間（週数）を設定
        try:
            # calendar dict から 'weeks' と 'iso_year_start' を取得
            weeks = int(calendar["weeks"] if isinstance(calendar, dict) else getattr(calendar, "weeks", 52))
            year_start = int(calendar["iso_year_start"] if isinstance(calendar, dict) else getattr(calendar, "iso_year_start", 2025))
            
            if hasattr(root, "set_plan_range_by_weeks"):
                # preserve=False で、正しい週数でPSI配列を再初期化する
                root.set_plan_range_by_weeks(weeks, year_start, preserve=False)
                if self.logger:
                    self.logger.info(f"Set tree plan range to {weeks} weeks starting {year_start}.")
            else:
                if self.logger:
                    self.logger.warn("root object has no 'set_plan_range_by_weeks' method. PSI arrays may be incorrect.")

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to set plan range on tree: {e}")

        # 2. PSIデータをツリーにロード (csv_adapter から移管)
        try:
            # operations から set_df_Slots2psi4demand をインポート
            from pysi.plan.operations import set_df_Slots2psi4demand 
            
            weekly_S = raw.get("weekly_demand_S", pd.DataFrame())
            if not weekly_S.empty:
                set_df_Slots2psi4demand(root, weekly_S)
            weekly_P = raw.get("weekly_demand_P", pd.DataFrame())
            if not weekly_P.empty:
                set_df_Slots2psi4demand(root, weekly_P)
        except ImportError:
            if self.logger:
                self.logger.error("Could not import set_df_Slots2psi4demand to load PSI data.")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to load PSI data into tree: {e}")
        
        # ---- 修正: ここまで追加 ----




        # ---- PSI Build ----
        self.hooks.do_action(
            "before_psi_build",
            db_path=db_path, scenario_id=scenario_id, root=root, logger=self.logger
        )
        params = self.io.derive_params(raw)
        params = self.hooks.apply_filters(
            "plan:params", params,
            db_path=db_path, scenario_id=scenario_id, root=root, logger=self.logger
        )
        params = self.hooks.apply_filters(
            "opt:capacity_plan", params,
            db_path=db_path, scenario_id=scenario_id, root=root, logger=self.logger
        )
        self.hooks.do_action(
            "after_psi_build",
            db_path=db_path, scenario_id=scenario_id, params=params, logger=self.logger
        )

        # ---- Plan / Allocate ----
        self.hooks.do_action(
            "plan:pre",
            db_path=db_path, scenario_id=scenario_id, calendar=calendar, logger=self.logger
        )

        weeks = int(calendar["weeks"] if isinstance(calendar, dict) else getattr(calendar, "weeks", 0))

        # 週頭イベントを P に反映（psi_dual ユーティリティ）
        #@2510027 updated
        settle_events_to_P(root, weeks)
        #settle_events_to_P(root, weeks, logger=self.logger)

        # 在庫ロールフォワード（psi_dual ユーティリティ）
        roll_and_merge_I(root, weeks, logger=self.logger)

        # I→S の消し込み（psi_dual ユーティリティ）
        try:
            consume_S_from_I_ids(root, weeks, logger=self.logger, synth_ok=False)
        except Exception as e:
            if self.logger: self.logger.exception(f"consume_S_from_I_ids failed at week={w}: {e}")

        # GUI プレビュー用の hist（在庫合計の例：demand layer の I を合算）
        inv_sum = 0.0
        try:
            for _key, recs in psiD.items():
                inv_sum += float(len(recs[w][PSI_I]))
        except Exception:
            # 週wのIが未初期化でも落とさない
            pass
        root.state["hist"].append({"week_idx": w, "inventory": float(inv_sum)})
        #root["state"]["hist"].append({"week_idx": w, "inventory": float(inv_sum)})

        # 週終わりフック
        self.hooks.do_action("after_week", root=root, week_idx=w, calendar=calendar, logger=self.logger)

        # ---- inventory ビュー（互換）: 最終週の在庫を node 単位で合算（demand layer）
        try:
            inv_view: Dict[str, float] = {}
            last_w = weeks - 1
            for (node, sku), recs in psiD.items():
                inv_view[node] = inv_view.get(node, 0.0) + float(len(recs[last_w][PSI_I]))
            root.state["inventory"] = inv_view
            #root["state"]["inventory"] = inv_view
        except Exception:
            pass

        # ---- 結果収集 / 可視化 / 出力
        result = self.io.collect_result(root, params={})
        # series生成（state["hist"] 優先 + フォールバック内蔵）
        result["psi_df"] = self.io.to_series_df(result, horizon=weeks)

        # 可視化系列の最終加工（必要に応じて）
        result = self.hooks.apply_filters("viz:series", result, calendar=calendar, logger=self.logger)

        # Exporters 実行
        exporters = self.hooks.apply_filters("report:exporters", [])
        for ex in exporters or []:
            try:
                ex(result=result, out_dir=out_dir, logger=self.logger)
            except Exception:
                if self.logger: self.logger.exception("[report] exporter failed")

        return result
    