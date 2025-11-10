# pysi/io_adapters/csv_adapter.py

# V0R7 の 8 CSV を DataFrame として raw に格納し、build_tree は DF→records 変換して
#  build_tree_from_csv に渡す版。
# set_attribute_from_csv のシグネチャ揺れにも対応、pos_E2E 付与、state の初期器も確保しています。

# 補足（適用済みポイント）
# V0R7 8ファイルを raw に DataFrame として格納（*_path ではなく実体 DF）（load_all）。
# build_tree は DF を to_dict("records") で records に変換し、
# build_tree_from_csv(inb+out) or build_tree_from_csv(inb, out) の両シグネチャに対応。
# コスト属性は set_attribute_from_csv(root, cost_out, cost_in) → 失敗時は cost_out のみ → 失敗時は無視。
# 座標は make_E2E_positions(root, raw["node_geo"]) を best-effort で付与（失敗しても通電）。
# state の器（psi_demand/psi_supply/hist）を dict ラッパ運用時に初期化。
# 既存の 旧API互換 ヘルパ（collect_result, to_series_df など）は温存し、GUI からでも動作できるよう維持。
# この版で、Pipeline.run() → io.load_all(spec) → io.build_tree(raw) の流れが、パス依存を排してDF直渡しに統一されます。V0R7シナリオ（examples/scenarios/<scenario_id>）の 8 CSV を置けば、そのまま読み込み・ツリー構築まで到達します。

# pysi/io_adapters/csv_adapter.py

from __future__ import annotations
from typing import Dict, Any, Optional, List
import pandas as pd
from pathlib import Path
import os

from pysi.core.tree import build_tree_from_csv, set_attribute_from_csv, make_E2E_positions
from pysi.plan.demand_generate import convert_monthly_to_weekly
from pysi.plan.operations import set_df_Slots2psi4demand

class CSVAdapter:
    def __init__(self, root: str, schema_cfg: Optional[Dict[str, Any]] = None, logger=None):
        self.root = Path(root)
        self.schema_cfg = schema_cfg or {}
        self.logger = logger
        self._demand_map = {}

    def load_all(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        raw = {}
        root_dir = self.root / spec.get("scenario_id", "")
        csv_files = [
            "product_tree_inbound.csv", "product_tree_outbound.csv", "sku_cost_table_inbound.csv",
            "sku_cost_table_outbound.csv", "node_geo.csv", "sku_S_month_data.csv", "sku_P_month_data.csv",
            "tariff_table.csv"
        ]
        loaded_count = 0
        for f in csv_files:
            path = root_dir / f
            if path.exists():
                raw[f.rsplit('.', 1)[0]] = pd.read_csv(path)
                loaded_count += 1
            else:
                raw[f.rsplit('.', 1)[0]] = pd.DataFrame()
                if self.logger:
                    self.logger.warn(f"Missing CSV: {path}, using empty DF")
        if self.logger:
            self.logger.info(f"Loaded {loaded_count} CSVs from {root_dir}")

        # NaN処理
        for key in raw:
            if 'year' in raw[key].columns:
                raw[key] = raw[key].dropna(subset=['year'], how='any')

        # 需要生成
        lot_size = 1000
        monthly_S = raw.get("sku_S_month_data", pd.DataFrame())
        if not monthly_S.empty:
            raw["weekly_demand_S"], _, _ = convert_monthly_to_weekly(monthly_S, lot_size)
        monthly_P = raw.get("sku_P_month_data", pd.DataFrame())
        if not monthly_P.empty:
            raw["weekly_demand_P"], _, _ = convert_monthly_to_weekly(monthly_P, lot_size)
        return raw

    def build_tree(self, raw: Dict[str, Any]) -> Any:
        try:
            # --- 修正1: DataFrame → records 変換を明示的に ---
            inb_df = raw.get("product_tree_inbound", pd.DataFrame())
            outb_df = raw.get("product_tree_outbound", pd.DataFrame())

            inb_records = inb_df.to_dict(orient="records") if not inb_df.empty else []
            outb_records = outb_df.to_dict(orient="records") if not outb_df.empty else []

            root_in = build_tree_from_csv(inb_records) if inb_records else None
            root_out = build_tree_from_csv(outb_records) if outb_records else None

            root = root_out or root_in
            if root_in and root_out:
                for child in root_in.children:
                    root.add_child(child)

            # --- コスト設定 ---
            cost_in = raw.get("sku_cost_table_inbound", pd.DataFrame()).to_dict(orient="records")
            cost_out = raw.get("sku_cost_table_outbound", pd.DataFrame()).to_dict(orient="records")
            root = set_attribute_from_csv(root, cost_out, cost_in)

            # --- 位置 ---

            #@251027 STOP
            #geo = raw.get("node_geo", pd.DataFrame())
            #if not geo.empty:
            #    root.pos_E2E = make_E2E_positions(root, geo)

            # 修正: root_out と root_in を渡す
            try:
                root.pos_E2E = make_E2E_positions(root_out, root_in)
            except Exception as e:
                if self.logger:
                    self.logger.warn(f"make_E2E_positions failed (continuing): {e}")


            #@251027 STOP initial 53 weeks setting can NOT get CSV file data
            ## --- PSI初期化 ---
            #weekly_S = raw.get("weekly_demand_S", pd.DataFrame())
            #if not weekly_S.empty:
            #    set_df_Slots2psi4demand(root, weekly_S)
            #weekly_P = raw.get("weekly_demand_P", pd.DataFrame())
            #if not weekly_P.empty:
            #    set_df_Slots2psi4demand(root, weekly_P)
            #    #set_df Гру2psi4demand(root, weekly_P)

            # --- state初期化（pipeline.py用）---
            root.state = {
                "hist": [],
                "psi_demand": {},
                "psi_supply": {},
                "inventory": {}
            }

            return root
        except Exception as e:
            if self.logger:
                self.logger.error(f"build_tree failed: {e}")
            return None

    # --- 修正2: derive_params 追加 ---
    def derive_params_OLD(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """pipeline.py から呼び出されるパラメータ構築"""
        params = {}
        # 例: lot_size, horizon, etc.
        params["lot_size"] = 1000
        params["horizon_weeks"] = 52  # デフォルト
        # 他のパラメータ（tariff_table など）
        tariff = raw.get("tariff_table", pd.DataFrame())
        if not tariff.empty:
            params["tariff_rate"] = tariff.set_index('node_name')['tariff_rate'].to_dict()
        return params


    def derive_params(self, raw: Dict[str, Any]) -> Dict[str, Any]:
            """pipeline.py から呼び出されるパラメータ構築"""
            params = {}
            # 例: lot_size, horizon, etc.
            params["lot_size"] = 1000
            params["horizon_weeks"] = 52  # デフォルト
            
            # 他のパラメータ（tariff_table など）
            tariff = raw.get("tariff_table", pd.DataFrame())
            if not tariff.empty:
                
                # 修正: 'node_name' ではなく 'to_node' カラムをチェックします
                if 'to_node' in tariff.columns:
                    
                    # 'tariff_rate' > 0 の行のみをフィルタリングします
                    # (0 のものは辞書に含める必要がないため)
                    tariff_filtered = tariff[tariff['tariff_rate'] > 0]
                    
                    if not tariff_filtered.empty:
                        # 'to_node' で重複がある場合、最初に見つかった 0 でない関税率を採用します
                        # (もし 'product_name' ごとに変える必要があるなら、より複雑な処理が必要です)
                        tariff_dict = tariff_filtered.drop_duplicates(subset=['to_node']).set_index('to_node')['tariff_rate'].to_dict()
                        params["tariff_rate"] = tariff_dict
                        if self.logger:
                            self.logger.info(f"Loaded {len(tariff_dict)} tariff rates keyed by 'to_node'.")
                    else:
                        params["tariff_rate"] = {} # 関税が 0 のものしかない場合

                elif self.logger:
                    self.logger.warn("tariff_table.csv is missing 'to_node' column, skipping tariff rates.")
            return params








    # 互換ヘルパ
    def collect_result(self, root, params={}):
        return {"kpis": {}, "hist": root.state.get("hist", [])}

    def to_series_df(self, result, horizon=0):
        pass

    def export_csv(self, result, out_dir="out", **kwargs):
        p = Path(out_dir); p.mkdir(parents=True, exist_ok=True)
        (p / "kpi.txt").write_text(str(result.get("kpis", {})))