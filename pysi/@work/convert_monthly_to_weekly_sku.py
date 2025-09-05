#convert_monthly_to_weekly_sku.py

def convert_monthly_to_weekly_sku(df: pd.DataFrame, lot_size_lookup) -> tuple[pd.DataFrame, int, int]:
    """
    月次を週次に変換。行ごとの lot_size は lot_size_lookup(product_name, node_name) で解決。
    戻り値: (df_weekly, plan_range, plan_year_st)
    """
    # 計画レンジ
    plan_range, plan_year_st = check_plan_range(df.rename(columns={"year":"year"}))

    # 縦持ち化
    df_melt = df.melt(
        id_vars=["product_name", "node_name", "year"],
        var_name="month", value_name="value"
    )
    # 'm1'→1
    df_melt["month"] = df_melt["month"].str[1:].astype(int)

    # 日次にばらし → 週番号で集計
    frames = []
    for _, r in df_melt.iterrows():
        y = int(r["year"]); m = int(r["month"]); v = float(r["value"])
        if v == 0:
            continue
        try:
            days = pd.Timestamp(y, m, 1).days_in_month
        except Exception:
            continue
        dates = pd.date_range(f"{y}-{m:02d}-01", periods=days, freq="D")
        frames.append(pd.DataFrame({
            "product_name": r["product_name"],
            "node_name":    r["node_name"],
            "date":         dates,
            "value":        v
        }))
    if frames:
        df_daily = pd.concat(frames, ignore_index=True)
    else:
        df_daily = pd.DataFrame(columns=["product_name","node_name","date","value"])

    if df_daily.empty:
        # 空でも落ちないように最低限の列を返す
        return (pd.DataFrame(columns=["product_name","node_name","iso_year","iso_week","value","S_lot","lot_id_list"]),
                plan_range, plan_year_st)

    iso = df_daily["date"].dt.isocalendar()
    df_daily["iso_year"] = iso.year.astype(int)
    df_daily["iso_week"] = iso.week.astype(int)

    df_weekly = (
        df_daily.groupby(["product_name","node_name","iso_year","iso_week"], as_index=False)["value"]
        .sum()
    )

    # lot_size を行ごとに解決して S_lot と lot_id を作成
    def _row_lot_size(row):
        try:
            return max(1, int(lot_size_lookup(row["product_name"], row["node_name"])))
        except Exception:
            return 1

    df_weekly["lot_size"] = df_weekly.apply(_row_lot_size, axis=1)
    df_weekly["S_lot"]    = (df_weekly["value"] / df_weekly["lot_size"]).apply(np.ceil).astype(int)

    # LotID 生成（既存仕様に合わせる：NODE + YYYY + WW(2桁) + NNNN）
    def _mk_lots(row):
        y = int(row["iso_year"])
        w = int(row["iso_week"])
        nn = row["node_name"]
        cnt = int(row["S_lot"])
        if cnt <= 0:
            return []
        ww = f"{w:02d}"
        return [f"{nn}{y}{ww}{i+1:04d}" for i in range(cnt)]

    df_weekly["lot_id_list"] = df_weekly.apply(_mk_lots, axis=1)

    # 週番号は文字列2桁に整形（既存の make_lot_id_list_list と互換）
    df_weekly["iso_week"] = df_weekly["iso_week"].astype(str).str.zfill(2)

    return df_weekly, plan_range, plan_year_st

