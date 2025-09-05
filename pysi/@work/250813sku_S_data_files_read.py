#250813sku_S_data_files_read.py


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
        # ORIGINAL
        # ********************************************************
        # ========== 2) S_month_data.csv の正規化→週次化 ==========
        directory  = self.directory
        month_csv  = os.path.join(directory, "S_month_data.csv")
        if not os.path.exists(month_csv):
            print("[INFO] S_month_data.csv not found; PSI slots not set.")
            return

        # 読み込み
        try:
            df_month_raw = pd.read_csv(month_csv, encoding="utf-8-sig")
        except Exception as e:
            print(f"[WARN] Failed to read S_month_data.csv: {e}")
            return

        # 正規化（製品/年/月/数量）
        df_month = _normalize_monthly_demand_df(df_month_raw)
        print("[DEBUG] monthly normalized head:\n", df_month.head(6))




        # 期間・開始年の推定（convert が返せばそれを採用）
        min_y, max_y = int(df_month["Year"].min()), int(df_month["Year"].max())
        inferred_range = max_y - min_y + 1
        inferred_start = min_y

        df_weekly = None
        # まず process_monthly_demand(file, lot_size) があればそれを優先
        try:
            if "process_monthly_demand" in globals():
                df_weekly, pr, pys = process_monthly_demand(month_csv, getattr(self, "lot_size", 1000))
                if pr:  self.plan_range = int(pr)
                else:   self.plan_range = inferred_range
                if pys: self.plan_year_st = int(pys)
                else:   self.plan_year_st = inferred_start

                # 器の再割当
                for _, root_ot in self.prod_tree_dict_OT.items():
                    _alloc_psi_for_tree(root_ot, self.plan_range, self.plan_year_st)
            else:
                raise NameError("process_monthly_demand not found")
        except Exception:
            # convert_monthly_to_weekly(df, lot_size) を試す
            try:
                res = convert_monthly_to_weekly(df_month, getattr(self, "lot_size", 1000))
                if isinstance(res, tuple) and len(res) >= 1:
                    df_weekly = res[0]
                    self.plan_range   = int(res[1]) if len(res) >= 2 and res[1] else inferred_range
                    self.plan_year_st = int(res[2]) if len(res) >= 3 and res[2] else inferred_start
                else:
                    df_weekly = res  # 単一戻り値パターン
                    self.plan_range   = inferred_range
                    self.plan_year_st = inferred_start

                # 器の再割当
                for _, root_ot in self.prod_tree_dict_OT.items():
                    _alloc_psi_for_tree(root_ot, self.plan_range, self.plan_year_st)
            except Exception as e2:
                print(f"[WARN] Demand weekly conversion failed: {e2}")
                df_weekly = None
        # ********************************************************

