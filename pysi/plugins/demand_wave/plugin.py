# pysi/plugins/demand_wave/plugin.py

from pysi.core.hooks.core import action

@action("after_tree_build", priority=60)
def demand_to_S_buckets(root=None, raw=None, calendar=None, logger=None, **_):
    """
    S_month → 週次化の最小ダミー実装。
    ここでは「m1（1月分）」を week=0 に、個数ぶん lot_ID を積むだけ。
    実務では 4-4-5 等の週割りや季節性・祝日補正を入れて、
    psi_demand[(node, sku)][week][S] に lot_ID を積む実装へ置き換えてください。

    期待される state 形：
      root["state"]["psi_demand"][(node, sku)][w][0]  # 0 = S バケツ
    期待される raw：
      raw["S_month"] : DataFrame（列: product_name, node_name, m1..m12 等）
    """
    try:

        #@251030 STOP
        #weeks = int((calendar or {}).get("weeks", 3))
        #state = (root or {}).get("state", {})
        #psiD  = state.get("psi_demand", {})

        weeks = int((calendar or {}).get("weeks", 3))
        # root は Node または dict の両対応にする
        if isinstance(root, dict):
            state = root.get("state", {})
        else:
            state = getattr(root, "state", {})
        psiD = state.get("psi_demand", {})




        s_month = (raw or {}).get("S_month")

        if s_month is None or getattr(s_month, "empty", True):
            return

        # ここでは m1 を week 0 にだけ起票する最小ダミー
        for _, r in s_month.iterrows():
            node = str(r.get("node_name"))
            sku  = str(r.get("product_name"))
            key = (node, sku)
            if key not in psiD:
                # ツリー初期化で登録されていない (node,sku) はスキップ
                continue

            # m1 を整数ロット数に丸めて week=0 の S バケツへ
            try:
                n = int(round(float(r.get("m1", 0.0))))
            except Exception:
                n = 0
            if n <= 0:
                continue

            week0 = 0 if weeks > 0 else 0
            # psiD[key][week][S] ; S=0
            S_bucket = psiD[key][week0][0]
            # ダミー lot_ID を個数ぶん積む（ID設計は各自の規約に合わせて変更可）
            S_bucket.extend([f"DM_{node}_{sku}_W{week0}_{i}" for i in range(n)])

    except Exception:
        if logger:
            logger.exception("[demand_wave] failed")
