from pathlib import Path
import numpy as np, pandas as pd, plotly.express as px, streamlit as st

st.set_page_config(page_title="NYC Home Price Index", layout="wide")
DATA = Path(__file__).parent / "data"


@st.cache_data
def load(name, **kw):
    return pd.read_csv(DATA / name, **kw)


st.title("NYC Home Price Index and Valuation Engine")
st.caption("Repeat-sales index (Bailey-Muth-Nourse) and valuation model built on NYC Dept. of Finance sales, 2003-2025.")
t1, t2, t3, t4 = st.tabs(["Index explorer", "Validation", "Valuation model", "Method and limits"])

with t1:
    hpi = load("hpi_quarterly.csv", parse_dates=["quarter_start"])
    quarters = sorted(hpi["quarter"].unique())
    sel = st.multiselect("Geography", sorted(hpi["geography"].unique()), default=["City", "HOUSE", "CONDO_COOP"])
    c1, c2 = st.columns(2)
    start = c1.selectbox("From", quarters, index=quarters.index("2004Q1"))
    base = c2.selectbox("Index = 100 at", quarters, index=quarters.index("2004Q1"))
    base_vals = hpi[hpi["quarter"] == base].set_index("geography")["value"]
    d = hpi[hpi["geography"].isin(sel) & (hpi["quarter"] >= start)].copy()
    d["Index"] = d["value"] / d["geography"].map(base_vals) * 100
    st.plotly_chart(px.line(d, x="quarter_start", y="Index", color="geography",
                            labels={"quarter_start": ""}), use_container_width=True)
    wide = hpi.pivot(index="quarter", columns="geography", values="value").sort_index()
    latest = pd.DataFrame({"Latest": wide.iloc[-1],
                           "YoY %": (wide.iloc[-1] / wide.iloc[-5] - 1) * 100,
                           "Growth since 2004Q1 %": (wide.iloc[-1] / wide.loc["2004Q1"] - 1) * 100,
                           "Peak-to-trough 2003-2012 %": [
                               ((wide[c].loc[:"2012Q4"] / wide[c].loc[:"2012Q4"].cummax()) - 1).min() * 100
                               for c in wide.columns]})
    st.dataframe(latest.round(1), use_container_width=True)
    st.caption(f"Latest quarter: {wide.index[-1]}")

with t2:
    st.subheader("Against Case-Shiller New York (metro area, mainly single-family)")
    v = load("validation_case_shiller.csv", parse_dates=["quarter_start"])
    lv = np.log(v.set_index("quarter_start").drop(columns="quarter"))
    yoy = lv.diff(4).dropna()
    m1, m2 = st.columns(2)
    m1.metric("Our HOUSE index: YoY correlation", f"{yoy['Ours HOUSE'].corr(yoy['Case-Shiller NY']):.2f}")
    m2.metric("Our citywide index: YoY correlation", f"{yoy['Ours City'].corr(yoy['Case-Shiller NY']):.2f}")
    st.plotly_chart(px.line(v.melt(id_vars=["quarter", "quarter_start"], var_name="Series", value_name="Index (2004Q1=100)"),
                            x="quarter_start", y="Index (2004Q1=100)", color="Series", labels={"quarter_start": ""}),
                    use_container_width=True)
    st.caption("Case-Shiller covers the wider metro area, including suburbs, so levels differ. "
               "Correlation is of year-over-year changes, which rewards getting the big cycle right.")
    st.subheader("Against FHFA county indexes (annual)")
    f = load("validation_fhfa.csv")
    rows = []
    for b, g in f.groupby("borough"):
        g = g.sort_values("year")
        rows.append({"Borough": b, "YoY correlation": np.log(g["ours"]).diff().corr(np.log(g["fhfa"]).diff())})
    st.dataframe(pd.DataFrame(rows).round(2), use_container_width=True, hide_index=True)
    b = st.selectbox("Borough", sorted(f["borough"].unique()))
    g = f[f["borough"] == b].melt(id_vars=["borough", "year"], var_name="Series", value_name="Index")
    st.plotly_chart(px.line(g, x="year", y="Index", color="Series"), use_container_width=True)
    st.caption("Manhattan is not shown: FHFA does not publish a Manhattan county series.")

with t3:
    res = load("model_results.csv")
    st.subheader("Held-out accuracy")
    st.markdown("Metrics: **MdAPE** (median absolute percent error), **PE10 / PE20** (share of predictions within 10% / 20% of the sale price).")
    seg = res[(res["split"] == "valid") & res["group"].isin(["HOUSE", "CONDO_COOP", "MULTIFAMILY"]) &
              res["model"].isin(["Baseline + HPI", "XGBoost v2"])]
    st.plotly_chart(px.bar(seg, x="group", y="mdape", color="model", barmode="group",
                           labels={"mdape": "Median abs. % error (validation)", "group": ""}),
                    use_container_width=True)
    st.markdown("**Test split (touched once, after the model was fixed)**")
    st.dataframe(res[res["split"] == "test"].drop(columns="split"), use_container_width=True, hide_index=True)
    st.markdown("**All validation rows**")
    st.dataframe(res[res["split"] == "valid"].drop(columns="split"), use_container_width=True, hide_index=True)
    sh = load("shap.csv").sort_values("mean_abs_shap")
    st.plotly_chart(px.bar(sh, x="mean_abs_shap", y="feature", orientation="h",
                           labels={"mean_abs_shap": "Mean |SHAP| (log-price units)", "feature": ""}),
                    use_container_width=True)

with t4:
    st.markdown("""
**Data.** NYC Dept. of Finance rolling sales, 2003-2025: 2,070,484 records combined from two source schemas; 1,264,635 arm's-length sales in three segments (house, condo/co-op, multifamily) used for modeling.

**Entity resolution.** Addresses are normalized, split into house number / street / unit, and fuzzy-matched within blocks (borough, ZIP, house number, unit) with numeric parts required to match exactly. Unit comes from the address or, when absent, the `APARTMENT NUMBER` column (the two agree 98.1% of the time). Against parcel IDs (BBL): pairwise precision 99.5%, recall 99.1%. Adding the unit fix cut sale pairs within 30 days from 139,632 to 9,915 by separating different apartments in the same building.

**Repeat-sales pairs.** 364,338 consecutive sale pairs at least 90 days apart, after filtering non-market prices (below $10k or below 0.25x the borough-segment-year median) and condo/co-op sales without a valid unit.

**Index.** Quarterly Bailey-Muth-Nourse regression with weights set per holding-period bucket (noise is U-shaped, not rising with time) and robust trimming of standardized residuals (5.8% of pairs). Changing the minimum holding period from 90 to 365 days moves 2025Q4 by about 1 point; removing 0.2% of suspect pairs moves no quarter by more than 0.06%.

**Valuation model.** XGBoost on a time-adjusted target (log price minus log index), with a property-grouped train/validation/test split so no property appears in two splits. Adding the property's own previous sale improves error on repeat sellers (12.8% vs 17.5% without a prior sale).

**Known limits.**
- About 48% of 2021 condo/co-op sales have no unit in the source data and are excluded from pairs.
- 2011-2019 growth is higher than FHFA county indexes in every borough; the cause is unresolved (different sample: FHFA is mortgage-based).
- Multifamily has few pairs (about 16k) and is indicative only. Manhattan has no FHFA benchmark.
- Condo/co-op sales have no unit size or floor, so they are predicted less accurately than houses.
- A small share of test rows (1.6%) have a prior sale only at the building level.
""")