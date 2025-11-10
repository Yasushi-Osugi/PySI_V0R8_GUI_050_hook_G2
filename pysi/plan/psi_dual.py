# pysi/plan/psi_dual.py
# ---------------------------------------------------------------------
# V0R7正本（dual: demand/supply × weekly [S,CO,I,P]）の最小テンプレ
# - 量は len(list) で決まる（lot は不可分）
# - PSIバケツは lot-ID のリストのみ（属性は lot_pool 等の外部辞書で参照）
# - 週次フロー：
#    ① 到着/完成イベントを P(w) に反映（settle_events_to_P）
#    ② I(w) = I(w-1) のコピー → P(w) を取り込み（roll_and_merge_I）
#    ③ 当週の出荷：I(w) から n_lots を S(w) へ（consume_S_from_I_ids）
# ---------------------------------------------------------------------

# V0R7の正本（二層：demand/supply × 週次 [S,CO,I,P]、各バケツは lot-ID のリスト／数量は len(list) で算出）
# に準拠し、pipeline.py からインポートされる関数・定数をすべて提供します。

 
# 拡張ポイント（任意）
# FEFO高度化：I(w) へ P(w) を取り込むタイミングで bisect を用いて exp_week 昇順維持にすれば、毎週の sort は不要になります。
# Iの遡り消費：現状は「当週 I(w)」だけから出荷しています。V0R7流の「直近在庫プール（過週を遡って消費）」をやるなら、consume_S_from_I_ids 内で week, week-1, ... と遡るループを追加してください。
# 週外ガード：ホライズン外の to_week が来る可能性があるなら、_bound_week() を導入し事前にクリップしてから settle_events_to_P で反映するのが堅実です。
# このテンプレを pysi/plan/psi_dual.py として追加すれば、前出の pipeline.py（V0R8/GUI）と素直に連携します。必要に応じて、receive_demand / produce_supply のイベント仕様はリポジトリ内の実データに合わせて拡張してください。


from __future__ import annotations
from typing import Dict, List, Any, Tuple, Optional

# PSI バケツの添字（固定）
PSI_S, PSI_CO, PSI_I, PSI_P = 0, 1, 2, 3

def init_psi_map(nodes: List[str], skus: List[str], weeks: int) -> Dict[Tuple[str, str], List[List[List[str]]]]:
    """
    (node, sku) → week配列 → [S,CO,I,P] という 3段構造の空器を作る。
    各バケツは lot_id(list[str]) のリスト。数量は len(bucket) で算出する。
    """
    psi: Dict[Tuple[str, str], List[List[List[str]]]] = {}
    if weeks < 1:
        weeks = 1
    for n in nodes or []:
        for s in skus or []:
            # week 配列：各週に 4バケツ（S,CO,I,P）を持つ
            psi[(n, s)] = [ [[], [], [], []] for _ in range(weeks) ]
    return psi


# ---- イベント → P(w) 反映 ----------------------------------------------------

def settle_events_to_P(state: Dict[str, Any], week: int) -> None:
    """
    state["scheduled"] に溜めた「到着/完成イベント」を当週の P(w) に反映する。
    - demand 層（psi_demand）/ supply 層（psi_supply）両方を対象にできる
    - 最小仕様（例）:
        - type == "receive_demand":
            keys: dst, sku, from_week, to_week, lots (list[str])
            動作: psi_demand[(dst,sku)][from_week][CO] から lots を取り除き、
                  psi_demand[(dst,sku)][week][P] に lots を追加
        - type == "produce_supply":
            keys: node, sku, to_week, lots (list[str])
            動作: psi_supply[(node,sku)][week][P] に lots を追加
    ※ キー不足やマップ欠損は無視（落とさずスキップ）
    """
    scheduled: List[Dict[str, Any]] = list(state.get("scheduled", []))
    if not scheduled:
        return

    psiD = state.get("psi_demand") or {}
    psiS = state.get("psi_supply") or {}

    rest: List[Dict[str, Any]] = []
    for ev in scheduled:
        try:
            to_w = int(ev.get("to_week", -1))
        except Exception:
            to_w = -1
        if to_w != week:
            rest.append(ev)
            continue

        etype = (ev.get("type") or "").strip().lower()
        try:
            if etype == "receive_demand":
                dst  = str(ev.get("dst"))
                sku  = str(ev.get("sku"))
                f_w  = int(ev.get("from_week", -1))
                lots = list(ev.get("lots") or [])
                psi = psiD.get((dst, sku))
                if psi is None:
                    continue
                # CO(from_week) から lots を取り除き、P(week)へ追加
                if 0 <= f_w < len(psi):
                    _remove_ids(psi[f_w][PSI_CO], lots)
                if 0 <= week < len(psi):
                    psi[week][PSI_P].extend(lots)

            elif etype == "produce_supply":
                node = str(ev.get("node"))
                sku  = str(ev.get("sku"))
                lots = list(ev.get("lots") or [])
                psi = psiS.get((node, sku))
                if psi is None:
                    continue
                if 0 <= week < len(psi):
                    psi[week][PSI_P].extend(lots)

            else:
                # 未知タイプは保持（将来別フックで処理）
                rest.append(ev)

        except Exception:
            # 例外は握りつぶす（監査は上位logger側で）
            continue

    state["scheduled"] = rest


def _remove_ids(bucket: List[str], ids: List[str]) -> None:
    """
    bucket から ids の中の lot_id を出現回数分だけ取り除く。
    多重度を尊重（同じIDが複数あれば複数回消す）。
    """
    if not bucket or not ids:
        return
    want: Dict[str, int] = {}
    for lid in ids:
        want[lid] = want.get(lid, 0) + 1

    i = 0
    while i < len(bucket):
        lid = bucket[i]
        cnt = want.get(lid, 0)
        if cnt > 0:
            want[lid] = cnt - 1
            bucket.pop(i)
        else:
            i += 1


# ---- 週頭：I ロールフォワード & P 取込 ---------------------------------------

def roll_and_merge_I(psi_map: Dict[Tuple[str, str], List[List[List[str]]]], week: int) -> None:
    """
    I(w) = I(w-1) のコピー → P(w) を I(w) に extend する。
    - 週0は P(0) を I(0) へ取り込むだけ。
    """
    if week < 0:
        return

    for _key, weeks in psi_map.items():
        if not weeks:
            continue
        if week == 0:
            # 初週：P(0) を I(0) へ
            if len(weeks) >= 1:
                I0 = weeks[0][PSI_I]
                P0 = weeks[0][PSI_P]
                if P0:
                    I0.extend(P0)
            continue

        if week >= len(weeks):
            # 計画地平を超える週は無視（上位でクリップしている想定）
            continue

        prev_I = weeks[week - 1][PSI_I]
        # list[str] の浅いコピーで十分（要素は不変の文字列）
        weeks[week][PSI_I] = list(prev_I)

        Pw = weeks[week][PSI_P]
        if Pw:
            weeks[week][PSI_I].extend(Pw)


# ---- 当週の出荷：I(w) → S(w) -------------------------------------------------

def consume_S_from_I_ids(
    psi_map: Dict[Tuple[str, str], List[List[List[str]]]],
    shipments: List[Dict[str, Any]],
    week: int,
    lot_pool: Optional[Dict[str, Any]] = None,
    fefo: bool = False
) -> None:
    """
    shipments の各要素について、(node, sku, week) の I(w) から "n_lots" ぶん S(w) に移す。
    - 要素例:
        {"src": "WS1", "sku": "RICE_A", "week": w, "n_lots": 5, "wanted": ["L1","L2",...]}
      "src" が無ければ "node" を代わりに見る。
    - fefo=True のときは、lot_pool[lid].exp_week で I(w) を昇順ソートしてから取り出す。
    - 不足分は SYN ロットを決定論的IDで補填（S側のみに積む。Iには積まない）
    """
    if not shipments:
        return

    for s in shipments:
        try:
            w = int(s.get("week", -1))
            if w != week:
                continue
            node = s.get("src", None)
            if node is None:
                node = s.get("node", None)
            if node is None:
                continue
            node = str(node)
            sku  = str(s.get("sku"))
            n    = int(s.get("n_lots", 0))
            if n <= 0:
                continue
        except Exception:
            continue

        psi = psi_map.get((node, sku))
        if psi is None:
            continue
        if not (0 <= week < len(psi)):
            continue

        Iw = psi[week][PSI_I]
        Sw = psi[week][PSI_S]

        # FEFO：lot_pool から exp_week を参照（なければ末尾に）
        if fefo and lot_pool:
            Iw.sort(key=lambda lid: getattr(lot_pool.get(lid, None), "exp_week", float("inf")))

        # 1) wanted優先（Iから該当IDを見つけ次第 pop → Sへ）
        wanted_ids = s.get("wanted")
        if wanted_ids:
            wanted = set(str(x) for x in wanted_ids)
            i = 0
            while i < len(Iw) and n > 0:
                if Iw[i] in wanted:
                    Sw.append(Iw.pop(i))
                    n -= 1
                else:
                    i += 1

        # 2) 残りは順番どおり先頭から取り出す
        take = min(n, len(Iw))
        if take > 0:
            Sw.extend(Iw[:take])
            del Iw[:take]
            n -= take

        # 3) 不足は合成 lot を補填（決定論的ID）
        if n > 0:
            syn_ids = _make_synthetic_ids(node, sku, week, n)
            Sw.extend(syn_ids)


# ---- helpers -----------------------------------------------------------------

def _make_synthetic_ids(node: str, sku: str, week: int, count: int) -> List[str]:
    """
    再現性のため決定論的に合成IDを生成する（監査や比較に強い）。
    """
    base = f"SYN:{node}:{sku}:{week}:"
    # 連番で十分（必要なら sha1 などに変更）
    return [f"{base}{i:04d}" for i in range(count)]
