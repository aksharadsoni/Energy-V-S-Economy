import streamlit as st
import os
import pandas as pd
import numpy as np
from datetime import timedelta

st.set_page_config(page_title="Energy–Economy Disconnect", layout="wide")

conn = st.connection("snowflake", ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL"))

# ── Constants ──
FOCUS_CODES = ["CHN", "IND", "USA"]
G7_CODES = ["CAN", "FRA", "DEU", "ITA", "JPN", "GBR", "USA"]
COUNTRY_NAMES = {
    "USA": "United States", "CHN": "China", "IND": "India", "DEU": "Germany",
    "GBR": "United Kingdom", "FRA": "France", "JPN": "Japan", "BRA": "Brazil",
    "CAN": "Canada", "AUS": "Australia", "KOR": "South Korea", "RUS": "Russia",
    "MEX": "Mexico", "IDN": "Indonesia", "TUR": "Turkey", "SAU": "Saudi Arabia",
    "ZAF": "South Africa", "NGA": "Nigeria", "ARG": "Argentina", "ITA": "Italy",
    "ESP": "Spain", "THA": "Thailand", "POL": "Poland", "NLD": "Netherlands",
    "SWE": "Sweden", "NOR": "Norway", "CHE": "Switzerland", "AUT": "Austria",
    "BEL": "Belgium", "CHL": "Chile", "COL": "Colombia", "EGY": "Egypt",
    "IRN": "Iran", "IRQ": "Iraq", "MYS": "Malaysia", "PHL": "Philippines",
    "PAK": "Pakistan", "PER": "Peru", "BGD": "Bangladesh", "VNM": "Vietnam",
    "NZL": "New Zealand", "FIN": "Finland", "DNK": "Denmark", "PRT": "Portugal",
    "GRC": "Greece", "CZE": "Czech Republic", "ROU": "Romania", "HUN": "Hungary",
    "ISR": "Israel", "ARE": "United Arab Emirates", "QAT": "Qatar", "KWT": "Kuwait",
}
COUNTRY_FLAGS = {"CHN": "\U0001f1e8\U0001f1f3", "IND": "\U0001f1ee\U0001f1f3", "USA": "\U0001f1fa\U0001f1f8"}

ECON_INDICATORS = {
    "GDP (constant 2015 USD)": "WDI_NY.GDP.MKTP.KD",
    "GDP Growth (annual %)": "WDI_NY.GDP.MKTP.KD.ZG",
    "GDP per Capita (current USD)": "WDI_NY.GDP.PCAP.CD",
}
ENERGY_INDICATORS = {
    "Energy Use (kg oil eq. per capita)": "ESG_EG.USE.PCAP.KG.OE",
    "Electric Power Consumption (kWh per capita)": "WDI_EG.USE.ELEC.KH.PC",
    "Energy Intensity (MJ/$2021 PPP GDP)": "ESG_EG.EGY.PRIM.PP.KD",
}


# ── Data loading (preserved) ──
@st.cache_data(ttl=timedelta(hours=1))
def load_wb_data(variable_ids, geo_ids):
    var_list = "'" + "','".join(variable_ids) + "'"
    geo_list = "'" + "','".join(geo_ids) + "'"
    sql = f"""
        SELECT GEO_ID, VARIABLE, VARIABLE_NAME,
               YEAR(DATE) AS YEAR, VALUE, UNIT
        FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.WORLD_BANK_TIMESERIES
        WHERE VARIABLE IN ({var_list})
          AND GEO_ID IN ({geo_list})
          AND VALUE IS NOT NULL
        ORDER BY GEO_ID, VARIABLE, YEAR
    """
    return conn.query(sql, ttl=timedelta(hours=1))


@st.cache_data(ttl=timedelta(hours=1))
def get_available_countries():
    sql = """
        SELECT DISTINCT SUBSTRING(GEO_ID, 9) AS CODE
        FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.WORLD_BANK_TIMESERIES
        WHERE GEO_ID LIKE 'country/%'
          AND VARIABLE = 'WDI_NY.GDP.MKTP.CD'
          AND VALUE IS NOT NULL
        ORDER BY CODE
    """
    df = conn.query(sql, ttl=timedelta(hours=1))
    codes = df["CODE"].tolist()
    return [c for c in codes if c in COUNTRY_NAMES]


def pct_change_col(series):
    return series.pct_change() * 100


def classify_signal(econ_chg, energy_chg):
    if pd.isna(econ_chg) or pd.isna(energy_chg):
        return "Insufficient Data"
    disconnect = econ_chg - energy_chg
    if abs(disconnect) < 1.0:
        return "Aligned"
    if econ_chg > 0 and energy_chg >= 0 and econ_chg > energy_chg:
        return "Economy outpaced energy"
    if energy_chg > 0 and econ_chg >= 0 and energy_chg > econ_chg:
        return "Energy outpaced economy"
    if econ_chg < 0 and energy_chg > 0:
        return "Stress signal"
    if econ_chg > 0 and energy_chg < 0:
        return "Strong divergence"
    if econ_chg < 0 and energy_chg < 0:
        return "Joint decline"
    return "Mixed signal"


def fmt_big(val):
    if abs(val) >= 1e12:
        return f"{val/1e12:.2f}T"
    if abs(val) >= 1e9:
        return f"{val/1e9:.1f}B"
    if abs(val) >= 1e6:
        return f"{val/1e6:.1f}M"
    if abs(val) >= 1e3:
        return f"{val/1e3:.1f}K"
    return f"{val:.1f}"


# ── CSS ──
st.markdown("""
<style>
    .big-number { font-size: 2rem; font-weight: 700; margin: 0; }
    .label-text { font-size: 0.85rem; color: #999; margin: 0; }
    .signal-text { font-size: 0.9rem; color: #00D4AA; margin-top: 0.5rem; font-style: italic; }
    .section-title { font-size: 1.6rem; font-weight: 700; letter-spacing: 2px; margin-top: 2rem; }
    .insight-box { background: #1A1F2E; border-radius: 8px; padding: 0.8rem 1rem; margin: 0.4rem 0; border-left: 3px solid #00D4AA; }
    .pressure-header { color: #FF6B6B; font-weight: 700; font-size: 0.95rem; margin-bottom: 0.2rem; }
    .pressure-body { font-size: 0.9rem; color: #ccc; }
</style>
""", unsafe_allow_html=True)


# ── SIDEBAR ──
st.sidebar.markdown("## Filters")
year_range = st.sidebar.slider("Time Period", 1970, 2023, (1990, 2022))
econ_label = st.sidebar.selectbox("Economic Indicator", list(ECON_INDICATORS.keys()), index=0)
energy_label = st.sidebar.selectbox("Energy Indicator", list(ENERGY_INDICATORS.keys()), index=0)
econ_var = ECON_INDICATORS[econ_label]
energy_var = ENERGY_INDICATORS[energy_label]

avail_countries = get_available_countries()
explore_countries = [c for c in avail_countries if c not in FOCUS_CODES]
with st.sidebar.expander("Advanced Options"):
    extra_country_code = st.selectbox(
        "Compare another country",
        options=["None"] + explore_countries,
        index=0,
        format_func=lambda c: "None" if c == "None" else COUNTRY_NAMES.get(c, c),
    )

# ── Load data: focus + G7 + optional extra ──
all_needed_codes = list(set(FOCUS_CODES + G7_CODES + (["IND"] if "IND" not in G7_CODES else []) + ([extra_country_code] if extra_country_code != "None" else [])))
geo_ids = [f"country/{c}" for c in all_needed_codes]
all_vars = list(set([econ_var, energy_var] + list(ECON_INDICATORS.values()) + list(ENERGY_INDICATORS.values())))

with st.spinner("Loading data..."):
    raw = load_wb_data(all_vars, geo_ids)

if raw.empty:
    st.error("No data found for the selected filters.")
    st.stop()

raw["COUNTRY"] = raw["GEO_ID"].str.slice(8).map(COUNTRY_NAMES).fillna(raw["GEO_ID"].str.slice(8))
raw["CODE"] = raw["GEO_ID"].str.slice(8)


def get_indicator_ts(df, variable, year_min, year_max):
    sub = df[(df["VARIABLE"] == variable) & (df["YEAR"] >= year_min) & (df["YEAR"] <= year_max)]
    return sub[["COUNTRY", "CODE", "YEAR", "VALUE", "UNIT"]].copy()


econ_ts = get_indicator_ts(raw, econ_var, year_range[0], year_range[1])
energy_ts = get_indicator_ts(raw, energy_var, year_range[0], year_range[1])

# Get unit labels from data
econ_unit = econ_ts["UNIT"].dropna().iloc[0] if not econ_ts["UNIT"].dropna().empty else econ_label
energy_unit = energy_ts["UNIT"].dropna().iloc[0] if not energy_ts["UNIT"].dropna().empty else energy_label


# ── Disconnect engine (preserved) ──
def build_disconnect(codes_list, econ_data, energy_data):
    frames = []
    for code in codes_list:
        name = COUNTRY_NAMES.get(code, code)
        c_econ = econ_data[econ_data["CODE"] == code].sort_values("YEAR")
        c_energy = energy_data[energy_data["CODE"] == code].sort_values("YEAR")
        if c_econ.empty or c_energy.empty:
            continue
        merged = c_econ[["YEAR", "VALUE"]].merge(
            c_energy[["YEAR", "VALUE"]], on="YEAR", suffixes=("_ECON", "_ENERGY")
        ).sort_values("YEAR").reset_index(drop=True)
        if len(merged) < 2:
            continue
        if econ_var == "WDI_NY.GDP.MKTP.KD.ZG":
            merged["ECON_CHG"] = merged["VALUE_ECON"]
        else:
            merged["ECON_CHG"] = pct_change_col(merged["VALUE_ECON"])
        merged["ENERGY_CHG"] = pct_change_col(merged["VALUE_ENERGY"])
        merged["DISCONNECT"] = merged["ECON_CHG"] - merged["ENERGY_CHG"]
        merged["ENERGY_PRODUCTIVITY"] = np.where(
            merged["VALUE_ENERGY"] != 0,
            merged["VALUE_ECON"] / merged["VALUE_ENERGY"], np.nan,
        )
        merged["SIGNAL"] = merged.apply(lambda r: classify_signal(r["ECON_CHG"], r["ENERGY_CHG"]), axis=1)
        merged["COUNTRY"] = name
        merged["CODE"] = code
        frames.append(merged)
    if frames:
        return pd.concat(frames, ignore_index=True).dropna(subset=["DISCONNECT"])
    return pd.DataFrame()


disc_all = build_disconnect(all_needed_codes, econ_ts, energy_ts)
disc_focus = disc_all[disc_all["CODE"].isin(FOCUS_CODES)] if not disc_all.empty else pd.DataFrame()

if disc_focus.empty:
    st.error("Insufficient overlapping data for the selected indicators and period.")
    st.stop()


# ════════════════════════════════════════════════════════
# 1. TITLE
# ════════════════════════════════════════════════════════
st.markdown("""
<h1 style='text-align:center; font-size:2.6rem; letter-spacing:3px; margin-bottom:0;'>
ENERGY &mdash; ECONOMY DISCONNECT
</h1>
<p style='text-align:center; color:#888; font-size:1.1rem; margin-top:0.3rem; margin-bottom:1.5rem;'>
Where economic growth and energy demand stop telling the same story.
</p>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
# 2. ENERGY TRENDS — Absolute Values (3 lines)
# ════════════════════════════════════════════════════════
st.markdown("---")
st.markdown(f"""
<p style='text-align:center; font-size:1.3rem; font-weight:700; color:#FAFAFA;'>
Energy Trends: China vs India vs United States
</p>
<p style='text-align:center; color:#888; font-size:0.85rem;'>
{energy_label} &nbsp;&bull;&nbsp; Absolute values &nbsp;&bull;&nbsp; {year_range[0]}–{year_range[1]}
</p>
""", unsafe_allow_html=True)

energy_chart_data = {}
energy_start = {}
energy_end = {}
for code in FOCUS_CODES:
    name = COUNTRY_NAMES[code]
    ts = energy_ts[energy_ts["CODE"] == code].sort_values("YEAR")
    if not ts.empty:
        energy_chart_data[name] = ts.set_index("YEAR")["VALUE"]
        energy_start[name] = ts.iloc[0]["VALUE"]
        energy_end[name] = ts.iloc[-1]["VALUE"]

if energy_chart_data:
    energy_df = pd.DataFrame(energy_chart_data)
    st.line_chart(energy_df, use_container_width=True, height=380)

    # Auto-generated insights for energy chart
    insights_e = []
    if energy_end:
        highest = max(energy_end, key=energy_end.get)
        lowest = min(energy_end, key=energy_end.get)
        insights_e.append(f"{highest} has the highest absolute {energy_label.split('(')[0].strip()} at the end of the period ({fmt_big(energy_end[highest])}).")
        if len(energy_start) == 3 and len(energy_end) == 3:
            changes = {n: energy_end[n] - energy_start[n] for n in energy_start}
            biggest_increase = max(changes, key=changes.get)
            insights_e.append(f"{biggest_increase} experienced the largest absolute increase in energy use over the period.")
            pct_changes = {n: ((energy_end[n] / energy_start[n]) - 1) * 100 for n in energy_start if energy_start[n] != 0}
            if pct_changes:
                fastest = max(pct_changes, key=pct_changes.get)
                slowest = min(pct_changes, key=pct_changes.get)
                insights_e.append(f"{fastest} grew fastest in percentage terms ({pct_changes[fastest]:+.0f}%), while {slowest} grew slowest ({pct_changes[slowest]:+.0f}%).")
    for ins in insights_e[:3]:
        st.markdown(f"""<div class='insight-box'>{ins}</div>""", unsafe_allow_html=True)
else:
    st.warning("Insufficient energy data for the three focus countries.")


# ════════════════════════════════════════════════════════
# 3. ECONOMY TRENDS — Absolute Values (3 lines)
# ════════════════════════════════════════════════════════
st.markdown("---")
st.markdown(f"""
<p style='text-align:center; font-size:1.3rem; font-weight:700; color:#FAFAFA;'>
Economic Trends: China vs India vs United States
</p>
<p style='text-align:center; color:#888; font-size:0.85rem;'>
{econ_label} &nbsp;&bull;&nbsp; Absolute values &nbsp;&bull;&nbsp; {year_range[0]}–{year_range[1]}
</p>
""", unsafe_allow_html=True)

econ_chart_data = {}
econ_start = {}
econ_end = {}
for code in FOCUS_CODES:
    name = COUNTRY_NAMES[code]
    ts = econ_ts[econ_ts["CODE"] == code].sort_values("YEAR")
    if not ts.empty:
        econ_chart_data[name] = ts.set_index("YEAR")["VALUE"]
        econ_start[name] = ts.iloc[0]["VALUE"]
        econ_end[name] = ts.iloc[-1]["VALUE"]

if econ_chart_data:
    econ_df = pd.DataFrame(econ_chart_data)
    max_econ_val = econ_df.max().max()
    if max_econ_val >= 1e12:
        econ_df_display = econ_df / 1e12
        econ_scale_label = "Trillions"
    elif max_econ_val >= 1e9:
        econ_df_display = econ_df / 1e9
        econ_scale_label = "Billions"
    else:
        econ_df_display = econ_df
        econ_scale_label = ""
    if econ_scale_label:
        st.caption(f"Y-axis in {econ_scale_label}")
    st.line_chart(econ_df_display, use_container_width=True, height=380)

    insights_ec = []
    if econ_end:
        highest = max(econ_end, key=econ_end.get)
        insights_ec.append(f"{highest} has the largest economy by {econ_label.split('(')[0].strip()} at the end of the period ({fmt_big(econ_end[highest])}).")
        if len(econ_start) == 3 and len(econ_end) == 3:
            pct_changes = {n: ((econ_end[n] / econ_start[n]) - 1) * 100 for n in econ_start if econ_start[n] != 0}
            if pct_changes:
                fastest = max(pct_changes, key=pct_changes.get)
                insights_ec.append(f"{fastest} saw the fastest economic growth over the period ({pct_changes[fastest]:+.0f}%).")
            gap_start = abs(econ_start.get("China", 0) - econ_start.get("India", 0))
            gap_end = abs(econ_end.get("China", 0) - econ_end.get("India", 0))
            if gap_start > 0 and gap_end > gap_start:
                insights_ec.append("The economic gap between China and India has widened over this period.")
            elif gap_start > 0 and gap_end < gap_start:
                insights_ec.append("The economic gap between China and India has narrowed over this period.")
    for ins in insights_ec[:3]:
        st.markdown(f"""<div class='insight-box'>{ins}</div>""", unsafe_allow_html=True)
else:
    st.warning("Insufficient economic data for the three focus countries.")


# ════════════════════════════════════════════════════════
# 4. COUNTRY SNAPSHOT CARDS
# ════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("<p class='section-title'>COUNTRY SNAPSHOTS</p>", unsafe_allow_html=True)

cols = st.columns(3)
for i, code in enumerate(FOCUS_CODES):
    name = COUNTRY_NAMES.get(code, code)
    flag = COUNTRY_FLAGS.get(code, "")
    cdata = disc_focus[disc_focus["CODE"] == code].sort_values("YEAR")
    if len(cdata) < 3:
        with cols[i]:
            st.warning(f"Insufficient data for {name}")
        continue

    avg_econ = cdata["ECON_CHG"].mean()
    avg_energy = cdata["ENERGY_CHG"].mean()
    avg_disc = cdata["DISCONNECT"].mean()
    latest_prod = cdata["ENERGY_PRODUCTIVITY"].dropna()
    prod_val = latest_prod.iloc[-1] if not latest_prod.empty else None
    first_prod = latest_prod.iloc[0] if not latest_prod.empty and len(latest_prod) > 1 else None
    prod_chg = ((prod_val / first_prod) - 1) * 100 if prod_val and first_prod and first_prod != 0 else None

    with cols[i]:
        with st.container(border=True):
            st.markdown(f"### {flag} {name}")
            st.markdown(f"<p class='label-text'>Avg. Economic Growth</p><p class='big-number'>{avg_econ:+.1f}%</p>", unsafe_allow_html=True)
            st.markdown(f"<p class='label-text'>Avg. Energy Change</p><p class='big-number'>{avg_energy:+.1f}%</p>", unsafe_allow_html=True)
            st.markdown(f"<p class='label-text'>Avg. Disconnect</p><p class='big-number'>{avg_disc:+.1f}pp</p>", unsafe_allow_html=True)
            if prod_chg is not None:
                st.markdown(f"<p class='label-text'>Energy Productivity Change</p><p class='big-number'>{prod_chg:+.1f}%</p>", unsafe_allow_html=True)



# ════════════════════════════════════════════════════════
# 5. WHAT DOESN'T ADD UP? — Single clean table
# ════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("""
<p class='section-title' style='text-align:center; color:#FF6B6B;'>
WHAT DOESN'T ADD UP?
</p>
<p style='text-align:center; color:#888; font-size:0.9rem;'>
Moments where the relationship between energy and economic performance became unusual
</p>
""", unsafe_allow_html=True)

anomaly_rows = []
for code in FOCUS_CODES:
    name = COUNTRY_NAMES.get(code, code)
    cdata = disc_focus[disc_focus["CODE"] == code].sort_values("YEAR")
    if len(cdata) < 3:
        continue
    mean_disc = cdata["DISCONNECT"].mean()
    std_disc = cdata["DISCONNECT"].std()
    if std_disc == 0:
        continue
    for _, row in cdata.iterrows():
        z_score = abs(row["DISCONNECT"] - mean_disc) / std_disc
        if z_score >= 1.3:
            anomaly_rows.append({
                "Country": name,
                "Year": int(row["YEAR"]),
                "Economic Change": f"{row['ECON_CHG']:+.1f}%",
                "Energy Change": f"{row['ENERGY_CHG']:+.1f}%",
                "Disconnect": f"{row['DISCONNECT']:+.1f}pp",
                "Signal": row["SIGNAL"],
                "_abs_disc": abs(row["DISCONNECT"]),
                "_z": z_score,
            })

if anomaly_rows:
    anomaly_df = pd.DataFrame(anomaly_rows).sort_values("_z", ascending=False).head(10)
    display_df = anomaly_df[["Country", "Year", "Economic Change", "Energy Change", "Disconnect", "Signal"]].reset_index(drop=True)
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("No strong anomalies detected for the current selection.")


# ════════════════════════════════════════════════════════
# 6. DISCONNECT OVER TIME — One visualization
# ════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("""
<p class='section-title' style='text-align:center;'>
WHERE IS THE DISCONNECT LARGEST?
</p>
<p style='text-align:center; color:#888; font-size:0.9rem;'>
Economic growth % minus Energy growth % — positive means economy outpacing energy
</p>
""", unsafe_allow_html=True)

disc_pivot = disc_focus.pivot_table(index="YEAR", columns="COUNTRY", values="DISCONNECT")
if not disc_pivot.empty:
    st.line_chart(disc_pivot, use_container_width=True, height=320)

    # Inferences from disconnect chart
    disc_inferences = []
    for code in FOCUS_CODES:
        name = COUNTRY_NAMES[code]
        cdata = disc_focus[disc_focus["CODE"] == code].sort_values("YEAR")
        if len(cdata) < 5:
            continue
        avg_disc = cdata["DISCONNECT"].mean()
        recent_disc = cdata.tail(5)["DISCONNECT"].mean()
        max_row = cdata.loc[cdata["DISCONNECT"].abs().idxmax()]
        if avg_disc > 1.5:
            disc_inferences.append(f"{name}: Economy consistently outpaced energy growth (avg disconnect: {avg_disc:+.1f}pp), indicating decoupling.")
        elif avg_disc < -1.5:
            disc_inferences.append(f"{name}: Energy growth consistently outpaced economic growth (avg disconnect: {avg_disc:+.1f}pp), indicating rising energy intensity.")
        else:
            disc_inferences.append(f"{name}: Energy and economic growth were broadly aligned (avg disconnect: {avg_disc:+.1f}pp).")
        if abs(recent_disc - avg_disc) > 2:
            direction = "widening" if abs(recent_disc) > abs(avg_disc) else "narrowing"
            disc_inferences.append(f"{name}: The disconnect has been {direction} in recent years (recent avg: {recent_disc:+.1f}pp vs overall avg: {avg_disc:+.1f}pp).")
        disc_inferences.append(f"{name}: Peak divergence occurred in {int(max_row['YEAR'])} ({max_row['DISCONNECT']:+.1f}pp).")
    for inf in disc_inferences:
        st.markdown(f"""<div class='insight-box'>{inf}</div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
# 7. CURRENT PRESSURES & POSSIBLE RESPONSES
# ════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("<p class='section-title'>CURRENT PRESSURES & POSSIBLE RESPONSES</p>", unsafe_allow_html=True)
st.markdown("""
<p style='color:#888; font-size:0.8rem;'>
<b>Important:</b> The historical data above comes from Snowflake (World Bank datasets).
The current pressures described below are based on widely reported structural conditions as of mid-2025.
They are <u>not</u> sourced from the Snowflake dataset and should be verified against current reporting.
</p>
""", unsafe_allow_html=True)

# Derive recent-period data signals to ground the section
recent_signals = {}
for code in FOCUS_CODES:
    name = COUNTRY_NAMES[code]
    cdata = disc_focus[disc_focus["CODE"] == code].sort_values("YEAR")
    if len(cdata) >= 5:
        recent = cdata.tail(5)
        recent_signals[code] = {
            "avg_econ": recent["ECON_CHG"].mean(),
            "avg_energy": recent["ENERGY_CHG"].mean(),
            "avg_disc": recent["DISCONNECT"].mean(),
            "trend": "accelerating" if recent["ENERGY_CHG"].iloc[-1] > recent["ENERGY_CHG"].mean() else "decelerating",
        }

pressure_cols = st.columns(3)

# CHINA
with pressure_cols[0]:
    with st.container(border=True):
        st.markdown("### \U0001f1e8\U0001f1f3 China")
        sig = recent_signals.get("CHN", {})
        if sig:
            st.markdown(f"*Recent data signal: avg economic growth {sig['avg_econ']:.1f}%, avg energy change {sig['avg_energy']:.1f}%, energy trend {sig['trend']}.*")
        st.markdown("<p class='pressure-header'>CURRENT PRESSURE</p>", unsafe_allow_html=True)
        st.markdown("""
China is undergoing large-scale electrification and industrial electricity demand continues to grow.
Renewable generation capacity has expanded rapidly, but grid integration, curtailment, and inter-regional
transmission remain structural challenges. A key question is whether rising electricity demand is
translating proportionally into domestic economic output, or whether energy-intensive export manufacturing
is absorbing a disproportionate share.
""")
        st.markdown("<p class='pressure-header'>WHY IT MATTERS</p>", unsafe_allow_html=True)
        st.markdown("If industrial electricity demand grows faster than the economic value it produces, China's energy intensity could rise even as total GDP grows — a pattern visible in the historical disconnect data.")
        st.markdown("<p class='pressure-header'>POSSIBLE RESPONSES</p>", unsafe_allow_html=True)
        st.markdown("""
- Investigate whether electricity growth is concentrated in specific industrial sectors
- Assess grid flexibility and energy storage deployment
- Examine the productivity of energy-intensive industrial activity
- Evaluate the relationship between domestic consumption and industrial production
""")

# INDIA
with pressure_cols[1]:
    with st.container(border=True):
        st.markdown("### \U0001f1ee\U0001f1f3 India")
        sig = recent_signals.get("IND", {})
        if sig:
            st.markdown(f"*Recent data signal: avg economic growth {sig['avg_econ']:.1f}%, avg energy change {sig['avg_energy']:.1f}%, energy trend {sig['trend']}.*")
        st.markdown("<p class='pressure-header'>CURRENT PRESSURE</p>", unsafe_allow_html=True)
        st.markdown("""
India faces rapidly increasing electricity demand driven by economic growth, urbanization, and extreme heat
(increasing cooling demand). Coal remains the dominant generation source during peak demand, creating pressure
on fuel inventories and supply chains. Renewable capacity is growing but grid-scale storage and distribution
infrastructure have not kept pace.
""")
        st.markdown("<p class='pressure-header'>WHY IT MATTERS</p>", unsafe_allow_html=True)
        st.markdown("India's economic growth requires substantially more energy growth to sustain it compared to mature economies. If energy supply constraints emerge, they could directly limit economic expansion.")
        st.markdown("<p class='pressure-header'>POSSIBLE RESPONSES</p>", unsafe_allow_html=True)
        st.markdown("""
- Accelerate battery and grid-scale storage deployment
- Expand demand-response programs during peak periods
- Reduce transmission and distribution bottlenecks
- Diversify reliable generation beyond coal dependence
- Invest in cooling-efficiency standards and infrastructure
""")

# USA
with pressure_cols[2]:
    with st.container(border=True):
        st.markdown("### \U0001f1fa\U0001f1f8 United States")
        sig = recent_signals.get("USA", {})
        if sig:
            st.markdown(f"*Recent data signal: avg economic growth {sig['avg_econ']:.1f}%, avg energy change {sig['avg_energy']:.1f}%, energy trend {sig['trend']}.*")
        st.markdown("<p class='pressure-header'>CURRENT PRESSURE</p>", unsafe_allow_html=True)
        st.markdown("""
After years of relatively flat electricity demand, the United States is experiencing a rapid increase driven
by AI data centers, electrification of transport, and manufacturing reshoring. Grid interconnection queues
have grown substantially, and new large loads are connecting faster than new generation and transmission
capacity can be built. Electricity affordability is also becoming a concern in some regions.
""")
        st.markdown("<p class='pressure-header'>WHY IT MATTERS</p>", unsafe_allow_html=True)
        st.markdown("The historical US pattern of economic growth decoupling from energy growth may reverse if large new electricity loads outpace efficiency gains — potentially ending a decades-long trend visible in the disconnect data.")
        st.markdown("<p class='pressure-header'>POSSIBLE RESPONSES</p>", unsafe_allow_html=True)
        st.markdown("""
- Accelerate grid interconnection and permitting processes
- Expand transmission capacity between regions
- Develop demand flexibility programs for large electricity consumers
- Deploy firm generation and long-duration storage
- Improve energy efficiency standards for data centers and industrial facilities
""")


# ════════════════════════════════════════════════════════
# 8. INDIA vs G7
# ════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("""
<p class='section-title' style='text-align:center;'>
INDIA vs G7: ENERGY & ECONOMIC TRAJECTORY
</p>
<p style='text-align:center; color:#888; font-size:0.9rem;'>
India is not a G7 member — this section compares its trajectory against the world's largest advanced economies.
</p>
""", unsafe_allow_html=True)

g7_with_india = list(set(G7_CODES + ["IND"]))
g7_available = [c for c in g7_with_india if not energy_ts[energy_ts["CODE"] == c].empty]
g7_missing = [COUNTRY_NAMES.get(c, c) for c in g7_with_india if c not in g7_available]
if g7_missing:
    st.caption(f"Data unavailable for: {', '.join(g7_missing)}")

# G7 ENERGY CHART
st.markdown(f"""
<p style='text-align:center; font-size:1.1rem; font-weight:600;'>
India vs G7 — {energy_label}
</p>
""", unsafe_allow_html=True)

g7_energy_data = {}
for code in g7_available:
    name = COUNTRY_NAMES.get(code, code)
    ts = energy_ts[energy_ts["CODE"] == code].sort_values("YEAR")
    if not ts.empty:
        g7_energy_data[name] = ts.set_index("YEAR")["VALUE"]

if g7_energy_data:
    g7_energy_df = pd.DataFrame(g7_energy_data)
    st.line_chart(g7_energy_df, use_container_width=True, height=350)

# G7 ECONOMY CHART
st.markdown(f"""
<p style='text-align:center; font-size:1.1rem; font-weight:600;'>
India vs G7 — {econ_label}
</p>
""", unsafe_allow_html=True)

g7_econ_data = {}
for code in g7_available:
    name = COUNTRY_NAMES.get(code, code)
    ts = econ_ts[econ_ts["CODE"] == code].sort_values("YEAR")
    if not ts.empty:
        g7_econ_data[name] = ts.set_index("YEAR")["VALUE"]

if g7_econ_data:
    g7_econ_df = pd.DataFrame(g7_econ_data)
    max_g7_econ = g7_econ_df.max().max()
    if max_g7_econ >= 1e12:
        g7_econ_display = g7_econ_df / 1e12
        g7_econ_scale = "Trillions"
    elif max_g7_econ >= 1e9:
        g7_econ_display = g7_econ_df / 1e9
        g7_econ_scale = "Billions"
    else:
        g7_econ_display = g7_econ_df
        g7_econ_scale = ""
    if g7_econ_scale:
        st.caption(f"Y-axis in {g7_econ_scale}")
    st.line_chart(g7_econ_display, use_container_width=True, height=350)

# WHAT MAKES INDIA DIFFERENT?
st.markdown("#### What Makes India Different?")

disc_g7 = disc_all[disc_all["CODE"].isin(g7_available)]
india_disc = disc_all[disc_all["CODE"] == "IND"]
g7_no_india = disc_g7[disc_g7["CODE"] != "IND"]

india_insights = []
if not india_disc.empty and not g7_no_india.empty:
    india_avg_energy = india_disc["ENERGY_CHG"].mean()
    g7_avg_energy = g7_no_india.groupby("CODE")["ENERGY_CHG"].mean()
    if not g7_avg_energy.empty:
        g7_median_energy = g7_avg_energy.median()
        if india_avg_energy > g7_median_energy:
            india_insights.append(f"India's average annual energy growth ({india_avg_energy:.1f}%) exceeds the G7 median ({g7_median_energy:.1f}%) — energy demand is growing substantially faster than in mature economies.")

    india_avg_econ = india_disc["ECON_CHG"].mean()
    g7_avg_econ = g7_no_india.groupby("CODE")["ECON_CHG"].mean()
    if not g7_avg_econ.empty:
        g7_median_econ = g7_avg_econ.median()
        if india_avg_econ > g7_median_econ:
            margin_word = "wider" if (india_avg_econ - g7_median_econ) > (india_avg_energy - g7_median_energy) else "narrower"
            india_insights.append(f"India's average annual economic growth ({india_avg_econ:.1f}%) also exceeds the G7 median ({g7_median_econ:.1f}%), but the margin is {margin_word} than for energy growth.")

    india_avg_disc = india_disc["DISCONNECT"].mean()
    g7_avg_disc = g7_no_india.groupby("CODE")["DISCONNECT"].mean()
    if not g7_avg_disc.empty:
        g7_median_disc = g7_avg_disc.median()
        if india_avg_disc < g7_median_disc - 1:
            india_insights.append(f"India's disconnect ({india_avg_disc:+.1f}pp) is lower than the G7 median ({g7_median_disc:+.1f}pp), suggesting India requires proportionally more energy growth to support each unit of economic growth.")
        elif india_avg_disc > g7_median_disc + 1:
            india_insights.append(f"India's disconnect ({india_avg_disc:+.1f}pp) is higher than the G7 median ({g7_median_disc:+.1f}pp), suggesting India is achieving relatively more economic output per unit of energy growth.")

    # Convergence check: is India's absolute energy use approaching any G7 country?
    if energy_end.get("India") is not None:
        india_energy_latest = energy_end["India"]
        for g7code in G7_CODES:
            g7name = COUNTRY_NAMES.get(g7code, g7code)
            g7_ts = energy_ts[energy_ts["CODE"] == g7code].sort_values("YEAR")
            if not g7_ts.empty:
                g7_latest = g7_ts.iloc[-1]["VALUE"]
                if g7_latest != 0:
                    ratio = india_energy_latest / g7_latest
                    if 0.7 <= ratio <= 1.3 and g7code != "IND":
                        india_insights.append(f"India's absolute energy use per capita has converged near {g7name}'s level (ratio: {ratio:.2f}).")
                        break

if india_insights:
    for ins in india_insights[:4]:
        st.markdown(f"""<div class='insight-box'>{ins}</div>""", unsafe_allow_html=True)
else:
    st.info("Insufficient comparable data to generate India vs G7 insights.")


# ════════════════════════════════════════════════════════
# 9. EXPLORE ANOTHER COUNTRY
# ════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("<p class='section-title'>EXPLORE ANOTHER COUNTRY</p>", unsafe_allow_html=True)
st.markdown("<p style='color:#888; font-size:0.85rem;'>Select a country from the sidebar (Advanced Options) to compare against the three focus economies.</p>", unsafe_allow_html=True)

if extra_country_code != "None":
    extra_name = COUNTRY_NAMES.get(extra_country_code, extra_country_code)
    extra_data = disc_all[disc_all["CODE"] == extra_country_code]

    if not extra_data.empty and len(extra_data) >= 3:
        st.markdown(f"### Comparing: {extra_name} vs China, India & United States")

        comparison_rows = []
        for code in FOCUS_CODES + [extra_country_code]:
            cname = COUNTRY_NAMES.get(code, code)
            cdata = disc_all[disc_all["CODE"] == code]
            if cdata.empty:
                continue
            comparison_rows.append({
                "Country": cname,
                "Avg Economic Growth (%)": round(cdata["ECON_CHG"].mean(), 2),
                "Avg Energy Change (%)": round(cdata["ENERGY_CHG"].mean(), 2),
                "Avg Disconnect (pp)": round(cdata["DISCONNECT"].mean(), 2),
            })
        if comparison_rows:
            st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)

        compare_data = disc_all[disc_all["CODE"].isin(FOCUS_CODES + [extra_country_code])]
        if not compare_data.empty:
            disc_cmp_pivot = compare_data.pivot_table(index="YEAR", columns="COUNTRY", values="DISCONNECT")
            if not disc_cmp_pivot.empty:
                st.markdown(f"**Disconnect Over Time — {extra_name} vs Focus Countries**")
                st.line_chart(disc_cmp_pivot, use_container_width=True, height=280)
    else:
        st.warning(f"Insufficient data for {extra_name} with the current indicators and time period.")
else:
    st.info("No additional country selected. Use the **Advanced Options** in the sidebar to add a comparison country.")


# ── Footer ──
st.markdown("---")
st.caption(
    f"Data: World Bank Open Data via Snowflake Marketplace \u00b7 "
    f"Indicators: {econ_label} vs {energy_label} \u00b7 "
    f"Period: {year_range[0]}\u2013{year_range[1]} \u00b7 "
    f"Correlation indicates association, not causation."
)
