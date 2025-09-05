# app.py

import streamlit as st
import pandas as pd
import altair as alt
import json, os
from sqlalchemy.orm import Session
from models import Session as DBSession, Scenario, Parameter, Run
from psi_runner import run_simulation
from psi_adapter import run_real_engine, EngineNotAvailable

st.set_page_config(page_title="Global Weekly PSI Planner", layout="wide")
st.title("PSI Planner – シナリオ/パラメータ設定・実行")

def get_or_create_scenario(s: Session, name: str) -> Scenario:
    sc = s.query(Scenario).filter_by(name=name).first()
    if not sc:
        sc = Scenario(name=name, description="Rice SC baseline")
        s.add(sc); s.commit()
    return sc

def _parse_multi(s: str):
    return [x.strip() for x in s.split(",") if x.strip()]

PARAM_DEFS = [
    ("lead_time_days","float","days",0.0,180.0,"補充LT（日）"),  # ← 0 → 0.0 / 180 → 180.0
    ("price_markup","float","ratio",0.8,1.5,"原価→販売価格倍率"),
    ("service_level","float","ratio",0.8,0.999,"在庫サービス水準")
]


with DBSession() as db:
    st.sidebar.header("Scenario")
    names = [x.name for x in db.query(Scenario).all()]
    sel = st.sidebar.selectbox("シナリオを選択", names + ["(新規)"])
    if sel == "(新規)":
        new = st.sidebar.text_input("新規シナリオ名", "rice_baseline")
        if st.sidebar.button("作成"):
            get_or_create_scenario(db, new); st.rerun()
        st.stop()

    sc = db.query(Scenario).filter_by(name=sel).first()
    USE_REAL = st.sidebar.toggle("Use real PSI engine", value=bool(os.getenv("USE_REAL_ENGINE")))

    st.sidebar.header("Scope Filters (optional)")
    with st.sidebar.expander("Filters", expanded=False):
        sku_in = st.text_input("SKU（カンマ区切り）", "RICE-A")
        region_in = st.text_input("Region（カンマ区切り）", "Kanto")
        origin_in = st.text_input("Origin", "VN")
        dest_in = st.text_input("Dest", "JP")
        channel_in = st.text_input("Channel（カンマ区切り）", "EC, Retail")

    filters = {}
    if sku_in:
        L = _parse_multi(sku_in); filters["sku"] = L if len(L)>1 else L[0]
    if region_in:
        L = _parse_multi(region_in); filters["region"] = L if len(L)>1 else L[0]
    if origin_in:
        L = _parse_multi(origin_in); filters["origin"] = L if len(L)>1 else L[0]
    if dest_in:
        L = _parse_multi(dest_in); filters["dest"] = L if len(L)>1 else L[0]
    if channel_in:
        L = _parse_multi(channel_in); filters["channel"] = L if len(L)>1 else L[0]
    if filters:
        st.sidebar.caption("適用フィルタ"); st.sidebar.code(json.dumps(filters, ensure_ascii=False, indent=2))

    st.subheader(f"Parameters: {sc.name}")
    cols = st.columns(3)
    updates = {}
    for i,(k,dt,unit,vmin,vmax,help_) in enumerate(PARAM_DEFS):
        p = next((x for x in sc.parameters if x.key==k), None)
        cur = float(p.value) if p else (vmin+vmax)/2
        with cols[i]:
            val = st.number_input(f"{k} ({unit})", min_value=vmin, max_value=vmax,
                                   value=cur, step=0.01, help=help_)
            updates[k]=val

    errors = []
    for (k,dt,unit,vmin,vmax,help_) in PARAM_DEFS:
        val = updates[k]
        if dt == "float" and not (vmin <= float(val) <= vmax):
            errors.append(f"{k} は {vmin}〜{vmax} の範囲で入力してください")
    if errors:
        st.warning("\n".join(errors))

    if st.button("保存", type="primary"):
        if errors:
            st.error("入力エラーを修正してください")
        else:
            for k,val in updates.items():
                p = next((x for x in sc.parameters if x.key==k), None)
                if not p:
                    p = Parameter(scenario_id=sc.id, key=k, dtype="float",
                                  unit=next(x[2] for x in PARAM_DEFS if x[0]==k))
                    db.add(p)
                p.value = str(val)
            db.commit(); st.success("保存しました。")

    st.caption("パラメータ辞書（型/単位/範囲/説明）")
    st.table(pd.DataFrame([
        {"key": k, "type": dt, "unit": unit, "range": f"{vmin}–{vmax}", "help": help_}
        for (k,dt,unit,vmin,vmax,help_) in PARAM_DEFS
    ]))

    st.divider()
    st.subheader("価格感度の例：price_markup ±% をスイープ")
    sweep = st.slider("変動幅(%)", -20, 20, 5, 1)

    if st.button("PSIを実行"):
        if errors:
            st.error("入力エラーを修正してください"); st.stop()

        base = {p.key: p.value for p in sc.parameters}
        variants = [("baseline", 0), ("price_minus", -sweep), ("price_plus", sweep)]
        rows = []
        for label, pct in variants:
            params = base.copy()
            params["price_markup"] = str(float(base.get("price_markup", 1.2)) * (1+pct/100))
            r = Run(scenario_id=sc.id, label=label, sweep={"price_markup_pct": pct})
            db.add(r); db.commit()
            try:
                if USE_REAL:
                    kpi = run_real_engine(sc.name, params, filters=filters if filters else None)
                else:
                    kpi = run_simulation(sc.name, params)  # ダミーはfilters未対応
            except EngineNotAvailable:
                st.info("実エンジンが未接続のためスタブで実行します")
                kpi = run_simulation(sc.name, params)
            r.status = "done"; r.summary = kpi; db.commit()
            rows.append({"variant": label, **kpi})

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

        c1 = alt.Chart(df).mark_bar().encode(x=alt.X('variant:N', title=''),
                                             y=alt.Y('gross_profit:Q', title='Gross Profit'),
                                             color='variant')
        c2 = alt.Chart(df).mark_bar().encode(x=alt.X('variant:N', title=''),
                                             y=alt.Y('inventory_turns:Q', title='Inventory Turns'),
                                             color='variant')
        c3 = alt.Chart(df).mark_bar().encode(x=alt.X('variant:N', title=''),
                                             y=alt.Y('stockout_rate:Q', title='Stockout Rate'),
                                             color='variant')
        st.altair_chart((c1 | c2 | c3).resolve_scale(y='independent'), use_container_width=True)
