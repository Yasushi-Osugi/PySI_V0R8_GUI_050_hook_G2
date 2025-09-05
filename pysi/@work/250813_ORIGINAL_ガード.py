#250813_ORIGINAL_ガード.py

# *****************************************************
#@250813 ORIGINAL
# *****************************************************

        # ========== 0) ガード ==========
        if not self.prod_tree_dict_OT:
            print("[WARN] No outbound product trees. Run load_data_files() first.")
            return

        # 基本パラメータ
        plan_range   = int(getattr(self, "plan_range", 3) or 3)
        plan_year_st = int(getattr(self, "plan_year_st", 2024) or 2024)

        # ========== 1) PSIスペース割当 ==========
        for prod_nm, root_ot in self.prod_tree_dict_OT.items():
            _alloc_psi_for_tree(root_ot, plan_range, plan_year_st)
        print("[INFO] PSI spaces allocated to all outbound nodes.")

        # ********************************************************
        # ********************************************************
        # @250813 UPDATE for "sku_S_month_data.csv"
        # ********************************************************
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

        # lot_size 参照関数を用意（製品ごとの Plan 木から node の lot_size を取得）
        def _lot_size_lookup(prod_name: str, node_name: str) -> int:
            root = prod_tree_dict_OT.get(prod_name)
            if root is None:
                return 1
            nd = root.find_node(lambda n: n.name == node_name)
            return int(getattr(nd, "lot_size", 1) or 1)

        # 週次へ変換（lot_size は行ごとに lookup）
        df_weekly, plan_range, plan_year_st = convert_monthly_to_weekly_sku(df_month, _lot_size_lookup)

        # PlanNode 側へ計画長をセット（全製品の Plan 木に一括適用）
        for root in prod_tree_dict_OT.values():
            root.set_plan_range_lot_counts(plan_range, plan_year_st)

        # 製品ごとに S ロットを Plan ツリーへ流し込み（leaf→root の既存ロジックを利用）
        for prod_name, root in prod_tree_dict_OT.items():
            df_w_prod = df_weekly[df_weekly["product_name"] == prod_name]
            if df_w_prod.empty:
                print(f"[INFO] no weekly demand rows for {prod_name}; skip.")
                continue
            set_df_Slots2psi4demand(root, df_w_prod)

        # ********************************************************



        # ========== 3) 週次スロット割当 ==========
        if df_weekly is not None:
            try:
                if "set_df_Slots2psi4demand" in globals():
                    for prod_nm, root_ot in self.prod_tree_dict_OT.items():
                        set_df_Slots2psi4demand(root_ot, df_weekly)
                    print("[INFO] demand slots set & propagated.")
                else:
                    print("[WARN] set_df_Slots2psi4demand not available; weekly demand computed but not assigned.")
            except Exception as e:
                print(f"[WARN] set_df_Slots2psi4demand failed: {e}")
        else:
            print("[WARN] df_weekly is None; skip setting demand slots.")

        # ========== 4) デバッグ出力 ==========
        try:
            sample_prod = next(iter(self.prod_tree_dict_OT.keys()))
            sample_root = self.prod_tree_dict_OT[sample_prod]
            any_node = next(_traverse(sample_root))
            weeks = min(5, self.plan_range)
            print(f"[DEBUG] PSI slot lengths for node '{any_node.name}' (first {weeks} weeks):",
                [len(any_node.psi4demand[w][0]) for w in range(1, weeks + 1)])
        except Exception:
            pass

# *****************************************************

