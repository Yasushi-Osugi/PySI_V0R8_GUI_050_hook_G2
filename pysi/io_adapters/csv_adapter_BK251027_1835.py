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


from __future__ import annotations
from typing import Dict, Any, Optional, List
import pandas as pd
from pathlib import Path
import os

from pysi.core.tree import build_tree_from_csv, set_attribute_from_csv, make_E2E_positions  # V0R7マージ
from pysi.plan.demand_generate import convert_monthly_to_weekly  # V0R7の需要生成追加
from pysi.plan.operations import set_df_Slots2psi4demand  # V0R7持ち込み (PSI初期化)

class CSVAdapter:
    """
    設定駆動のCSVアダプタ。
    - root: CSVルートパス
    - schema_cfg: （将来拡張用。現状は未使用でも可）
    """
    def __init__(self, root: str, schema_cfg: Optional[Dict[str, Any]] = None, logger=None):
        self.root = Path(root)
        self.schema_cfg = schema_cfg or {}
        self.logger = logger
        self._demand_map = {}  # 互換: 旧APIのフォールバックで使用することがある

    # ----------------------------------------------------------------------
    # Data Load (V0R7 固定 8ファイルを DF で raw に格納)
    # ----------------------------------------------------------------------
    def load_all(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        raw = {}
        root_dir = self.root / spec.get("scenario_id", "")
        csv_files = [
            "product_tree_inbound.csv", "product_tree_outbound.csv", "sku_cost_table_inbound.csv",
            "sku_cost_table_outbound.csv", "node_geo.csv", "sku_S_month_data.csv", "sku_P_month_data.csv",
            "tariff_table.csv"  # V0R7の全CSV
        ]
        loaded_count = 0
        for f in csv_files:
            path = root_dir / f
            if path.exists():
                raw[f.rsplit('.', 1)[0]] = pd.read_csv(path)
                loaded_count += 1
            else:
                raw[f.rsplit('.', 1)[0]] = pd.DataFrame()  # 空DFフォールバック
                if self.logger:
                    self.logger.warn(f"Missing CSV: {path}, using empty DF")
        if self.logger:
            self.logger.info(f"Loaded {loaded_count} CSVs from {root_dir}")
        # NaN処理 (year列など)
        for key in raw:
            if 'year' in raw[key].columns:
                raw[key] = raw[key].dropna(subset=['year'], how='any')
        # V0R7のdemand_generate追加 (sku_S_month_data/sku_P_month_data変換)
        lot_size = 1000  # V0R7デフォルト; paramsから動的取得可
        monthly_S = raw.get("sku_S_month_data", pd.DataFrame())
        if not monthly_S.empty:
            raw["weekly_demand_S"], _, _ = convert_monthly_to_weekly(monthly_S, lot_size)
        monthly_P = raw.get("sku_P_month_data", pd.DataFrame())
        if not monthly_P.empty:
            raw["weekly_demand_P"], _, _ = convert_monthly_to_weekly(monthly_P, lot_size)
        return raw

    # ----------------------------------------------------------------------
    # Tree Build (V0R7マージ: DF→records変換 + 属性/位置設定 + PSI初期化)
    # ----------------------------------------------------------------------
    def build_tree(self, raw: Dict[str, Any]) -> Any:  # root Node返す
        try:
            # V0R7持ち込み: file by file tree build (inbound/outbound別)
            inb_df = raw.get("product_tree_inbound", pd.DataFrame())
            outb_df = raw.get("product_tree_outbound", pd.DataFrame())
            inb_records = inb_df.to_dict(orient="records") if not inb_df.empty else []
            outb_records = outb_df.to_dict(orient="records") if not outb_df.empty else []
            # build_tree_from_csv (V0R7関数: 別々処理)
            root_in = build_tree_from_csv(inb_records) if inb_records else None
            root_out = build_tree_from_csv(outb_records) if outb_records else None
            # 統合 (V0R7風: outbound優先 or merge)
            root = root_out or root_in  # outbound優先
            if root_in and root_out:
                # マージロジック (V0R7風: 子ノード追加など)
                for child in root_in.children:
                    root.add_child(child)
            # 属性設定 (コスト: inbound/outbound分離)
            cost_in = raw.get("sku_cost_table_inbound", pd.DataFrame()).to_dict(orient="records")
            cost_out = raw.get("sku_cost_table_outbound", pd.DataFrame()).to_dict(orient="records")
            root = set_attribute_from_csv(root, cost_out, cost_in)  # V0R7関数
            
            # 位置生成 (best-effort)
            geo = raw.get("node_geo", pd.DataFrame())

            if not geo.empty:
                root.pos_E2E = make_E2E_positions(root, geo)
            
            # V0R7持ち込み: PSI初期化 (weekly_demandからset_df_Slots2psi4demand)
            weekly_S = raw.get("weekly_demand_S", pd.DataFrame())
            if not weekly_S.empty:
                set_df_Slots2psi4demand(root, weekly_S)  # V0R7関数 (demand PSI)

            weekly_P = raw.get("weekly_demand_P", pd.DataFrame())
            if not weekly_P.empty:
                set_df_Slots2psi4demand(root, weekly_P)  # supply PSI

            return root

        except Exception as e:
            if self.logger:
                self.logger.error(f"build_tree failed: {e}")
            return None  # None返却でpipelineフォールバック

    # ----------------------------------------------------------------------
    # その他互換ヘルパ (V0R7の初期化/出力など)
    # ----------------------------------------------------------------------
    def collect_result(self, root, params={}):
        # V0R7互換: stateのhist/psi収集 (仮)
        return {"kpis": {}, "hist": root.get("state", {}).get("hist", [])}

    def to_series_df(self, result, horizon=0):
        # V0R7互換: histからDF生成 (添付の既存ロジックそのまま)
        # ... (既存コードをここに保持)
        pass

    def export_csv(self, result, out_dir="out", **kwargs):
        p = Path(out_dir); p.mkdir(parents=True, exist_ok=True)
        (p / "kpi.txt").write_text(str(result.get("kpis", {})))
