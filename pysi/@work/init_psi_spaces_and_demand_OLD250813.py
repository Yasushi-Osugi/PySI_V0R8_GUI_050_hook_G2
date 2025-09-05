#init_psi_spaces_and_demand_OLD250813.py



    def init_psi_spaces_and_demand_OLD250813(self):
        """
        1) 各製品の outbound ツリー全ノードに PSI スペース(psi4demand/psi4supply)を自前で確保
        - 週キーは 1..plan_range
        - 値は [[], [], []] として index=0 を「スロット配列」に使える形にする
        2) S_month_data.csv があれば:
        - DataFrame をカラム正規化（製品/年/月/数量）
        - convert_monthly_to_weekly で週次化（process_monthly_demand があれば優先）
        - set_df_Slots2psi4demand があれば、週次スロットを leaf に設定・伝播
        """
        import os
        import re
        import pandas as pd
        import calendar

        # ========== helpers ==========
        #def _traverse(root):
        #    stack = [root]
        #    while stack:
        #        n = stack.pop()
        #        yield n
        #        stack.extend(getattr(n, "children", []) or [])

        #def _alloc_psi_for_tree(root, plan_range, plan_year_st):
        #    # 既存APIがあれば使う（無くてもOK）
        #    if hasattr(root, "set_plan_range_lot_counts"):
        #        try:
        #            root.set_plan_range_lot_counts(plan_range, plan_year_st)
        #        except Exception:
        #            pass
        #    # 全ノードに psi4demand / psi4supply を辞書で用意
        #    for node in _traverse(root):
        #        if not hasattr(node, "psi4demand") or not isinstance(getattr(node, "psi4demand"), dict):
        #            node.psi4demand = {}
        #        if not hasattr(node, "psi4supply") or not isinstance(getattr(node, "psi4supply"), dict):
        #            node.psi4supply = {}
        #        for w in range(1, plan_range + 1):
        #            node.psi4demand.setdefault(w, [[], [], []])
        #            node.psi4supply.setdefault(w, [[], [], []])

        def _traverse(root):
            stack = [root]
            while stack:
                n = stack.pop()
                yield n
                stack.extend(getattr(n, "children", []) or [])

        def _alloc_psi_for_tree(root, plan_range, plan_year_st):
            # 既存APIがあれば使う
            if hasattr(root, "set_plan_range_lot_counts"):
                try:
                    root.set_plan_range_lot_counts(plan_range, plan_year_st)
                except Exception:
                    pass


        def _month_label_to_num(x):
            """Jan, January, 1, 01, M01, 2024-01, 01/2024, 2024/01 など多様な月表記を 1..12 に変換"""
            if pd.isna(x):
                return None
            s = str(x).strip()

            # 直接数値
            if re.fullmatch(r"\d{1,2}", s):
                m = int(s)
                return m if 1 <= m <= 12 else None

            # M01 / m01 / M1
            m = re.fullmatch(r"[Mm](\d{1,2})", s)
            if m:
                mv = int(m.group(1))
                return mv if 1 <= mv <= 12 else None

            # YYYY-MM / YYYY/MM / MM-YYYY / MM/YYYY
            m = re.search(r"(\d{4})[-/](\d{1,2})", s) or re.search(r"(\d{1,2})[-/](\d{4})", s)
            if m:
                a, b = int(m.group(1)), int(m.group(2))
                # どちらが月かを判定
                if 1 <= b <= 12:
                    return b
                if 1 <= a <= 12:
                    return a

            # Jan, January
            abbr_map = {name.lower(): i for i, name in enumerate(calendar.month_abbr) if name}
            full_map = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
            s_low = s.lower()
            if s_low in abbr_map:
                return abbr_map[s_low]
            if s_low in full_map:
                return full_map[s_low]

            return None

        def _find_first_existing(cols, candidates):
            for c in candidates:
                if c in cols:
                    return c
            return None

        def _normalize_monthly_demand_df(df_raw: pd.DataFrame) -> pd.DataFrame:
            """
            期待する最終スキーマ: ['Product_name','Year','Month','Demand']
            - ワイド（12か月が列）/ ロング（Year, Month 列持ち）両対応
            - 列名の表記ゆれも吸収（日本語/英語・大小・SKU 等）
            """
            df = df_raw.copy()

            # 1) 列名のトリム
            df.columns = [str(c).strip() for c in df.columns]

            # 2) 候補名
            product_candidates = [
                "Product_name", "product_name", "Product", "product",
                "SKU", "sku", "sku_name", "Item", "item", "品目", "製品名"
            ]
            year_candidates = ["Year", "year", "年度", "FY", "fy"]
            month_candidates = ["Month", "month", "月", "Mon", "mon"]
            qty_candidates = ["Demand", "demand", "Quantity", "quantity", "Qty", "qty", "需要", "数量", "出荷", "販売数量"]

            cols = set(df.columns)
            prod_col = _find_first_existing(cols, product_candidates)
            year_col = _find_first_existing(cols, year_candidates)
            mon_col  = _find_first_existing(cols, month_candidates)
            val_col  = _find_first_existing(cols, qty_candidates)

            # 3) ロング形式（Year, Month, Demand っぽい列がすでにある）
            if (prod_col is not None) and (mon_col is not None) and (val_col is not None):
                df = df[[prod_col] + ([year_col] if year_col else []) + [mon_col, val_col]].copy()
                # 列名統一
                rename_map = {prod_col: "Product_name", mon_col: "Month", val_col: "Demand"}
                if year_col:
                    rename_map[year_col] = "Year"
                df = df.rename(columns=rename_map)
                # Year 補完
                if "Year" not in df.columns or df["Year"].isna().all():
                    df["Year"] = getattr(self, "plan_year_st", 2024)
                # Month を 1..12 に
                df["Month"] = df["Month"].apply(_month_label_to_num)
                df = df[df["Month"].between(1, 12, inclusive="both")]
                # 型
                df["Year"] = df["Year"].astype(int)
                df["Month"] = df["Month"].astype(int)
                df["Demand"] = pd.to_numeric(df["Demand"], errors="coerce").fillna(0.0)
                return df[["Product_name", "Year", "Month", "Demand"]].reset_index(drop=True)

            # 4) ワイド形式（12か月が列として並んでいるケース）
            #    「月と判定できる列」を集める
            month_like_cols = []
            for c in df.columns:
                mnum = _month_label_to_num(c)
                if mnum is not None:
                    month_like_cols.append((c, mnum))

            if prod_col is None:
                # 製品名列が無ければ、単一SKUとして仮置き（全体に同じ Product_name を割当）
                prod_col = "__PRODUCT__"
                df[prod_col] = getattr(self, "product_selected", "UNKNOWN_PRODUCT")

            if month_like_cols:
                # 年列が無ければ self.plan_year_st を補う
                if year_col is None:
                    df["Year"] = getattr(self, "plan_year_st", 2024)
                    year_col = "Year"

                # melt
                month_like_cols_sorted = [c for c, _ in sorted(month_like_cols, key=lambda x: x[1])]
                id_vars = [prod_col, year_col] if year_col else [prod_col]
                df_long = df.melt(id_vars=id_vars, value_vars=month_like_cols_sorted,
                                var_name="MonthLabel", value_name="Demand")
                # ラベル→番号
                df_long["Month"] = df_long["MonthLabel"].apply(_month_label_to_num)
                df_long = df_long.drop(columns=["MonthLabel"])
                # 列名統一
                rename_map = {prod_col: "Product_name"}
                if year_col:
                    rename_map[year_col] = "Year"
                df_long = df_long.rename(columns=rename_map)

                # 型・フィルタ
                if "Year" not in df_long.columns or df_long["Year"].isna().all():
                    df_long["Year"] = getattr(self, "plan_year_st", 2024)
                df_long = df_long[df_long["Month"].between(1, 12, inclusive="both")]
                df_long["Year"] = df_long["Year"].astype(int)
                df_long["Month"] = df_long["Month"].astype(int)
                df_long["Demand"] = pd.to_numeric(df_long["Demand"], errors="coerce").fillna(0.0)

                return df_long[["Product_name", "Year", "Month", "Demand"]].reset_index(drop=True)

            # 5) どちらでもない場合は諦めず、最もそれっぽい列を作る
            #    - Product_name: 固定値
            #    - Year: plan_year_st
            #    - Month: 1..12 を複製
            #    - Demand: 0
            pn = getattr(self, "product_selected", "UNKNOWN_PRODUCT")
            yr = getattr(self, "plan_year_st", 2024)
            df_fallback = pd.DataFrame({
                "Product_name": [pn] * 12,
                "Year": [yr] * 12,
                "Month": list(range(1, 13)),
                "Demand": [0.0] * 12
            })
            print("[WARN] Could not normalize monthly demand columns; using zero-demand placeholder.")
            return df_fallback

# *****************************************************
#@250813 UPDATE
# *****************************************************

        # ========== 0) ガード ==========
        if not self.prod_tree_dict_OT:
            print("[WARN] No outbound product trees. Run load_data_files() first.")
            return

        # 基本パラメータ
        plan_range   = int(getattr(self, "plan_range", 3) or 3)
        plan_year_st = int(getattr(self, "plan_year_st", 2024) or 2024)

        # ========== 1) PSIスペース割当 ==========
        for _, root_ot in self.prod_tree_dict_OT.items():   # ← self. を付ける
            _alloc_psi_for_tree(root_ot, plan_range, plan_year_st)
        print("[INFO] PSI spaces allocated to all outbound nodes.")

        # ========== 2) sku_S_month_data.csv の正規化→週次化 ==========
        directory  = self.directory
        new_csv    = os.path.join(directory, "sku_S_month_data.csv")
        old_csv    = os.path.join(directory, "S_month_data.csv")
        month_csv  = new_csv if os.path.exists(new_csv) else old_csv
        if not os.path.exists(month_csv):
            print("[INFO] sku_S_month_data.csv (or S_month_data.csv) not found; PSI slots not set.")
            return

        try:
            df_month_raw = pd.read_csv(month_csv, encoding="utf-8-sig")
        except Exception as e:
            print(f"[WARN] Failed to read {os.path.basename(month_csv)}: {e}")
            return

        # 正規化（列名のゆらぎを吸収）
        df_month = _normalize_monthly_demand_df_sku(df_month_raw)
        print("[DEBUG] monthly normalized head:\n", df_month.head(6))

        # lot_size 参照関数：self.prod_tree_dict_OT を使う & find_node が無い場合も安全に
        def _lot_size_lookup(prod_name: str, node_name: str) -> int:
            root = self.prod_tree_dict_OT.get(prod_name)   # ← self. を付ける
            if root is None:
                return 1
            # find_node があるなら使う
            fn = getattr(root, "find_node", None)
            if callable(fn):
                nd = fn(lambda n: getattr(n, "name", None) == node_name)
                return int(getattr(nd, "lot_size", 1) or 1) if nd else 1
            # フォールバック：手で走査
            stack = [root]
            while stack:
                n = stack.pop()
                if getattr(n, "name", None) == node_name:
                    return int(getattr(n, "lot_size", 1) or 1)
                stack.extend(getattr(n, "children", []))
            return 1

        # 週次へ変換（lot_size は行ごとに lookup）
        df_weekly, plan_range, plan_year_st = convert_monthly_to_weekly_sku(df_month, _lot_size_lookup)

        # PlanNode 側へ計画長をセット（全製品に一括適用）
        for root in self.prod_tree_dict_OT.values():        # ← self. を付ける
            if hasattr(root, "set_plan_range_lot_counts"):
                root.set_plan_range_lot_counts(plan_range, plan_year_st)

        # 製品ごとに S ロットを流し込み
        for prod_name, root in self.prod_tree_dict_OT.items():  # ← self. を付ける
            df_w_prod = df_weekly[df_weekly["product_name"] == prod_name]
            if df_w_prod.empty:
                print(f"[INFO] no weekly demand rows for {prod_name}; skip.")
                continue
            set_df_Slots2psi4demand(root, df_w_prod)

        # ========== 3) まとめ出力 ==========
        try:
            sample_prod = next(iter(self.prod_tree_dict_OT.keys()))
            sample_root = self.prod_tree_dict_OT[sample_prod]
            any_node = next(_traverse(sample_root))
            weeks = min(5, self.plan_range)
            print(f"[DEBUG] PSI slot lengths for node '{any_node.name}' (first {weeks} weeks):",
                  [len(any_node.psi4demand[w][0]) for w in range(weeks)])
        except Exception:
            pass


    # *************************************************
    def init_psi_spaces_and_demand_OLD(self):
        """
        1) PSIスペース(psi4demand/psi4supply)の割当
        2) 月次需要(S_month_data.csv)→週次に変換
        3) 週次スロットを leaf にセットし、rootへ伝播
        """
        import os
        import csv

        directory = self.directory
        # 1) by-product root を対象に PSI の器を作る
        if not self.prod_tree_dict_OT:
            print("[WARN] No product trees to init PSI.")
            return

        # plan_range/year は config ベースでOK（CSVから決めたい場合は後述）
        plan_range = self.plan_range
        plan_year_st = self.plan_year_st

        # PSIの器を作る
        for prod_nm, root_ot in self.prod_tree_dict_OT.items():
            root_ot.set_plan_range_lot_counts(plan_range, plan_year_st)
            node_psi_dict_dm = make_psi_space_dict(root_ot, {}, plan_range)
            node_psi_dict_sp = make_psi_space_dict(root_ot, {}, plan_range)
            set_dict2tree_psi(root_ot, "psi4demand", node_psi_dict_dm)
            set_dict2tree_psi(root_ot, "psi4supply", node_psi_dict_sp)

        # 2) 月次需要→週次に変換（変換器が無い場合はスキップ）
        month_csv = os.path.join(directory, "S_month_data.csv")
        if not os.path.exists(month_csv):
            print("[INFO] S_month_data.csv not found; PSI slots not set.")
            return

        # なるべく既存の convert_monthly_to_weekly を使う
        # CSVはプロジェクト依存なので例外吸収で安全に
        try:
            import pandas as pd
            df_month = pd.read_csv(month_csv, encoding="utf-8-sig")
        except Exception as e:
            print(f"[WARN] Failed to read S_month_data.csv: {e}")
            return

        try:
            # 既存APIをラップ（戻り値の仕様はプロジェクトに依存）
            # ここでは以下の返り値を想定: df_weekly, plan_range, plan_year_st
            df_weekly, pr, pys = convert_monthly_to_weekly(df_month, self.lot_size)
            if pr and isinstance(pr, int):
                self.plan_range = pr
            if pys and isinstance(pys, int):
                self.plan_year_st = pys
            # 器も更新
            for prod_nm, root_ot in self.prod_tree_dict_OT.items():
                root_ot.set_plan_range_lot_counts(self.plan_range, self.plan_year_st)
        except Exception as e:
            print(f"[WARN] convert_monthly_to_weekly failed; skipping demand slots. err={e}")
            return

        # 3) 週次スロットを leaf にセットし、rootへ伝播
        # set_df_Slots2psi4demand は operations 側の実装に依存
        try:
            for prod_nm, root_ot in self.prod_tree_dict_OT.items():
                set_df_Slots2psi4demand(root_ot, df_weekly)
            print("[INFO] demand slots set & propagated.")
        except Exception as e:
            print(f"[WARN] set_df_Slots2psi4demand failed: {e}")



