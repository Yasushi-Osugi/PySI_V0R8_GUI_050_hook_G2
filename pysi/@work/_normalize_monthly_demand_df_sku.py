#_normalize_monthly_demand_df_sku.py

def _normalize_monthly_demand_df_sku(df: pd.DataFrame) -> pd.DataFrame:
    """
    入力DFを `product_name,node_name,year,m1..m12` に正規化。
    大文字小文字や別名 (Product_name, Node, Year, M1..M12) も吸収。
    """
    # トリム＋小文字化した暫定名で揃える
    rename = {c: c.strip() for c in df.columns}
    df = df.rename(columns=rename)

    # 代表名へ寄せる
    aliases = {
        "Product_name": "product_name",
        "PRODUCT_NAME": "product_name",
        "Node": "node_name",
        "Node_name": "node_name",
        "NODE_NAME": "node_name",
        "Year": "year",
        "YEAR": "year",
    }
    # 月列も一括で吸収
    for m in range(1, 13):
        aliases[f"M{m}"] = f"m{m}"
        aliases[f"m{m}"] = f"m{m}"

    df = df.rename(columns=aliases)

    # 必須列チェック
    required = ["product_name", "node_name", "year"] + [f"m{i}" for i in range(1, 12+1)]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"[ERR] monthly csv missing columns: {missing}")

    # 型と欠損処理
    df["product_name"] = df["product_name"].astype(str).str.strip()
    df["node_name"]    = df["node_name"].astype(str).str.strip()
    df["year"]         = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    for m in range(1, 13):
        col = f"m{m}"
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # year 欠損は除外
    df = df.dropna(subset=["year"]).copy()
    df["year"] = df["year"].astype(int)

    return df[required]

