# pysi/core/pipeline.py
# V0R8 Hook 版 Pipeline（Node/dict 両対応の state 取得＋イベント決済を修正）
from __future__ import annotations

from typing import Any, Dict, List
import pandas as pd

from pysi.core.hooks.core import HookBus
# PSI（デュアル層）ユーティリティ
from pysi.plan.psi_dual import (
    PSI_S, PSI_CO, PSI_I, PSI_P,
    init_psi_map,
    settle_events_to_P,      # 既存の単関数（必要なら併用）
    roll_and_merge_I,
    consume_S_from_I_ids,
)

# Node/dict 両対応のイベント決済（lot-IDを demand/supply 双方へ）
from pysi.core.psi_bridge_dual import settle_scheduled_events_dual


def _as_state(obj) -> Dict[str, Any]:
    """
    Node / dict の両対応で obj.state（dict）を返す。
    無ければ空dictを作って紐づける。
    """
    if isinstance(obj, dict):
        st = obj.get("state")
        if isinstance(st, dict):
            return st
        st = {}
        obj["state"] = st
        return st

    # Node オブジェクト
    st = getattr(obj, "state", None)
    if isinstance(st, dict):
        return st
    st = {}
    setattr(obj, "state", st)
    return st


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

        # ---- 計画期間（weeks）をツリーへ反映 ----
        try:
            weeks = int(calendar["weeks"] if isinstance(calendar, dict) else getattr(calendar, "weeks", 52))
            year_start = int(calendar["iso_year_start"] if isinstance(calendar, dict) else getattr(calendar, "iso_year_start", 2025))
            if hasattr(root, "set_plan_range_by_weeks"):
                root.set_plan_range_by_weeks(weeks, year_start, preserve=False)
                if self.logger:
                    self.logger.info(f"Set tree plan range to {weeks} weeks starting {year_start}.")
            else:
                if self.logger:
                    self.logger.warning("root has no set_plan_range_by_weeks().")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to set plan range: {e}")

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

        # ---- Plan / Allocate (週次ループ前の初期化) ----
        self.hooks.do_action(
            "plan:pre",
            db_path=db_path, scenario_id=scenario_id, calendar=calendar, logger=self.logger
        )

        weeks = int(calendar["weeks"] if isinstance(calendar, dict) else getattr(calendar, "weeks", 0))

        # ---- ここが今回の修正ポイント：イベント決済は state を明示し、週次で処理 ----
        state = _as_state(root)
        state.setdefault("scheduled", [])  # plugins が積む受け皿（配列）

        # 例）plugins.psi_commit_dual 等が state["scheduled"] に
        # {"type": "...", "node":/ "src": "...", "dst": "...", "sku": "...", "from_week": w, "to_week": w2, "lots": [...]} を積む

        # 週頭イベントの決済（CO/P→I 等）
        for w in range(weeks):
            try:
                settle_scheduled_events_dual(state, w)
            except Exception as e:
                if self.logger:
                    self.logger.exception(f"settle_scheduled_events_dual failed at week={w}: {e}")

        # 以降、必要に応じて psi_dual の補助関数を利用
        try:

            pass
        
            #@251108 STOP
            # [V7-compat] skip inventory roll for CSV/JIT MVP
            #
            ## P/CO→I のロールフォワード等（内部は list[str] の move を行う）
            #roll_and_merge_I(root, weeks, logger=self.logger)
            #
            ## I→S の消し込み（不足時は synth_ok=False で合成禁止）
            #consume_S_from_I_ids(root, weeks, logger=self.logger, synth_ok=False)

        except Exception as e:
            if self.logger:
                self.logger.exception(f"PSI post-processing failed: {e}")

        # ---- 結果収集 / 可視化 / 出力 ----
        result = self.io.collect_result(root, params={})
        # GUIプレビュー用：hist が無い場合でも to_series_df がフォールバック
        result["psi_df"] = self.io.to_series_df(result, horizon=weeks)

        result = self.hooks.apply_filters("viz:series", result, calendar=calendar, logger=self.logger)

        exporters = self.hooks.apply_filters("report:exporters", [])
        for ex in exporters or []:
            try:
                ex(result=result, out_dir=out_dir, logger=self.logger)
            except Exception:
                if self.logger:
                    self.logger.exception("[report] exporter failed")

        return result
