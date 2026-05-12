import streamlit as st
import pandas as pd
import numpy as np
import base64

# --- Remove Streamlit header/menu for full-screen background ---
st.set_page_config(page_title="Best Branch Scoring Calculator", layout="wide")

hide_streamlit_style = """
    <style>
    /* Hide Streamlit header and footer */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    /* Make app full height */
    .stApp {
        height: 100vh;
    }
    /* Remove default padding/margins */
    .css-18e3th9 {padding:0rem !important; margin:0rem !important;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- Function to set full-screen background ---
def set_background(image_file):
    with open(image_file, "rb") as f:
        encoded_string = base64.b64encode(f.read()).decode()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpg;base64,{encoded_string}");
            background-size: cover;
            background-repeat: no-repeat;
            background-position: center;
            background-attachment: fixed;
            height: 100vh;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# --- Add background image ---
set_background("background.jpg")

# --- Logo ---
import base64

# --- Load logo as base64 ---
def load_logo(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

logo_base64 = load_logo("singer_finance_logo.png")

# --- Add small top-right logo ---
st.markdown(f"""
<style>
.top-right-logo {{
    position: fixed;
    top: 20px;
    right: 20px;
    width: 120px;   /* change size */
    z-index: 9999;
}}
</style>

<img src="data:image/png;base64,{logo_base64}" class="top-right-logo">
""", unsafe_allow_html=True)


# --- Title CSS ---
st.markdown("""
<style>
.main-title {
    font-size: 50px !important;
    font-weight: 800 !important;
    color: black !important;
    text-align: center;
    margin-bottom: -10px;
}
.subtitle {
    text-align: center;
    font-size: 22px;
    font-weight: 800 !important;
    color: #455a64;
    margin-bottom: 25px;
}
</style>
""", unsafe_allow_html=True)

# --- Title ---
st.markdown('<div class="main-title">🏆 Best Branch Scoring Calculator</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Automatically detects score columns or calculates using memo thresholds</div>', unsafe_allow_html=True)


# ------------------------------------------------------------
# NEW CSS — Resize & Center File Uploader Box
# ------------------------------------------------------------
st.markdown("""
<style>
[data-testid="stFileUploader"] {
    width: 450px !important;      /* Change width */
    margin-left: auto !important; /* Center horizontally */
    margin-right: auto !important;
}

[data-testid="stFileUploader"] section {
    padding: 30px !important;     /* Change height */
    border: 2px dashed #444 !important;
    border-radius: 15px !important;
}

[data-testid="stFileUploader"] div {
    text-align: center !important;
}
</style>
""", unsafe_allow_html=True)




# -------------------------
# Utilities
# -------------------------
def parse_numeric_series(s, percent_detect=True):
    s = s.astype(str).fillna("").str.strip()
    s = s.str.replace(r'^\((.*)\)$', r'-\1', regex=True)   # (1,234) -> -1234
    has_pct = s.str.contains("%")
    s_clean = s.str.replace("%", "", regex=False).str.replace(",", "", regex=False).str.strip()
    numeric = pd.to_numeric(s_clean.replace({"": np.nan, "nan": np.nan}), errors="coerce")
    if percent_detect:
        if not has_pct.any():
            non_null = numeric.dropna()
            if len(non_null) > 0 and (non_null.abs() <= 1.0).sum() / len(non_null) > 0.6:
                numeric = numeric * 100.0
    return numeric

def apply_scale(series, scale):
    if scale == "raw":
        return series
    if scale == "thousands":
        return series * 1_000.0
    if scale == "millions":
        return series * 1_000_000.0
    return series

# Heuristic: detect if a numeric series looks like component scores already
def looks_like_score(series):
    ser = pd.to_numeric(series, errors="coerce").dropna()
    if len(ser) == 0:
        return False
    within_range = ser.between(-15, 20).mean()
    unique_frac = ser.nunique() / len(ser)
    med_abs = ser.abs().median()
    if within_range > 0.9 and (ser.nunique() <= 12 or unique_frac < 0.25) and med_abs <= 20:
        return True
    return False


# -------------------------
# Tier functions (exact PPT thresholds)
# -------------------------
def tier_receivable_abs_growth(val):
    if pd.isna(val): 
        return 0.0

    # De-growth
    if val < 0:
        return -10.0

    # Annualize the value (8 months → annual factor = 12/8 = 1.5)
    annualized = val * 1.5

    # Main scoring
    if annualized > 850_000_000:
        score = 10.0
    elif 500_000_000 <= annualized <= 850_000_000:
        score = 7.5
    elif 250_000_000 <= annualized < 500_000_000:
        score = 5.0
    else:
        score = 0.0

    # Bonus for exceptional performance
    if annualized > 1_000_000_000:
        score += 2.0

    return score


def tier_avg_receivable_month(val):
    if pd.isna(val): return 0.0
    if val > 75_000_000: return 10.0
    if 60_000_000 <= val <= 75_000_000: return 7.5
    if 40_000_000 <= val < 60_000_000: return 5.0
    if 15_000_000 <= val < 40_000_000: return 0.0
    return 0.0

def tier_receivable_growth_pct(val):
    if pd.isna(val): return 0.0
    if val < 0: return -5.0
    if val > 80: return 5.0
    if 40 <= val <= 80: return 2.5
    return 0.0

def tier_profitability_contribution(val):
    if pd.isna(val): return 0.0
    if val >= 3.0: return 15.0
    if 2.0 <= val < 3.0: return 10.0
    if 1.0 <= val < 2.0: return 5.0
    return 0.0

def tier_npl(val):
    if pd.isna(val): return 0.0
    if val <= 3.0: return 10.0
    if 3.0 < val <= 6.0: return 5.0
    return -5.0

def tier_fd_abs_growth(val):
    if pd.isna(val): return 0.0
    if val < 0: return -5.0
    if val < 50_000_000: return -5.0
    if 50_000_000 <= val < 250_000_000: return 0.0
    if 250_000_000 <= val <= 400_000_000: return 5.0
    if val > 400_000_000: return 10.0
    return 0.0


def tier_fd_growth_pct(val):
    if pd.isna(val): return 0.0
    if val > 30: return 5.0
    if 15 <= val <= 30: return 2.5
    if 0 <= val < 15: return 0.0
    return 0.0


def tier_savings_abs_growth(val):
    if pd.isna(val): return 0.0
    if val < 1_000_000: return -5.0
    if 20_000_000 <= val: return 5.0
    if 10_000_000 <= val < 20_000_000: return 2.5
    if 1_000_000 <= val < 10_000_000: return 0.0
    return 0.0


def tier_savings_growth_pct(val):
    if pd.isna(val): return 0.0
    if val < 0: return -5.0
    if val >= 25: return 5.0
    if 10 <= val < 25: return 2.5
    if 0 <= val < 10: return 0.0
    return 0.0


def tier_nim(val):
    if pd.isna(val): return 0.0
    if val > 10: return 10.0       # Over 10%
    if 7.5 <= val <= 10: return 5.0  # 7.5% – 10%
    if val < 7.5: return 0.0       # Below 7.5%
    return 0.0


def tier_facilities(val):
    if pd.isna(val): return 0.0
    if val > 600: return 5.0          # Over 600
    if 300 <= val <= 600: return 2.5 # 300 to 600
    if val < 300: return 0.0         # Less than 300
    return 0.0


def tier_solar(val):
    if pd.isna(val): return 0.0
    if val > 12: return 5.0        # Over 12
    if 5 <= val <= 12: return 2.5 # 5 to 12
    if val < 5: return 0.0        # Less than 5
    return 0.0

# List of brands included under Home Brands Champion
HOME_BRANDS_LIST = [
    "Lima",
    "Piaggio",
    "Kubota",
    "John Deere",
    "Omoda",
    "Jaecoo",
    "TailG"
]

def tier_home_brands(val):
    if pd.isna(val): return 0.0
    if val > 75: return 10.0
    if 35 <= val <= 75: return 5.0
    if val < 35: return 0.0
    return 0.0


# -------------------------
# Upload and read
# -------------------------

uploaded = st.file_uploader(
    "Upload your Excel/CSV file",
    type=["xlsx", "xls", "csv"]
)

if uploaded is None:
    st.stop()

file_name = uploaded.name.lower()

# If Excel file
if file_name.endswith(".xlsx") or file_name.endswith(".xls"):
    df = pd.read_excel(uploaded)

# If CSV file
elif file_name.endswith(".csv"):
    try:
        df = pd.read_csv(uploaded, encoding="utf-8")
    except:
        uploaded.seek(0)
        df = pd.read_csv(uploaded, encoding="latin1")

# If wrong file
else:
    st.error("Please upload Excel or CSV file")
    st.stop()

st.subheader("Preview uploaded table (top rows)")
st.dataframe(df.head())

scale_choice = st.selectbox("Unit scaling for amount columns (what Excel numbers represent):",
                            options=["raw", "thousands", "millions"], index=0)

df.columns = [str(c).strip() for c in df.columns]

expected_inputs = [
    "BRANCH","Maturity","Receivable Absolute Growth","Receivable Average Receivable Per Month",
    "Receivable Growth %","No.of files generated","Profitabilty","NPL%","FD Absolute Growth",
    "FD Growth %","Savings Absolute Growth","Savings Growth %","NIM",
    "No.of solar facilities generated","Home Brand facilities"
]

def find_column(df_cols, candidates):
    for cand in candidates:
        for c in df_cols:
            if cand.lower().replace(" ", "") in str(c).lower().replace(" ", ""):
                return c
    return None

candidates = {
    "BRANCH": ["BRANCH","Branch","Branches"],
    "Maturity": ["Maturity","maturity"],
    "Receivable Absolute Growth": ["Receivable Absolute Growth","Receivable Abs Growth","Receivable_Abs_Growth","ReceivableAbsolute"],
    "Receivable Average Receivable Per Month": ["Receivable Average Receivable Per Month","Average Receivable Per Month","Avg_Receivable_Month","AvgReceivableMonth"],
    "Receivable Growth %": ["Receivable Growth %","Receivable Growth","Receivable Growth Percent"],
    "No.of files generated": ["No.of files generated","Files generated","No. of files generated","No.of files Generated","Facilities","No of facilities"],
    "Profitabilty": ["Profitabilty","Profitability","Profit"],
    "NPL%": ["NPL%","NPL"],
    "FD Absolute Growth": ["FD Absolute Growth","FD Abs Growth","FDAbsolute"],
    "FD Growth %": ["FD Growth %","FD Growth","FD Growth Percent"],
    "Savings Absolute Growth": ["Savings Absolute Growth","Savings Abs Growth","SavingsAbsolute"],
    "Savings Growth %": ["Savings Growth %","Savings Growth","Savings Growth Percent"],
    "NIM": ["NIM","NIM Score","Net Interest Margin"],
    "No.of solar facilities generated": ["No.of solar facilities generated","Solar Facilities","No of Solar Facilities"],
    "Home Brand facilities": ["Home Brand facilities","Home Brand Champion","Home Brand"]
}

mapped = {}
for key, cands in candidates.items():
    mapped[key] = find_column(df.columns, cands)

st.write("Detected columns (mapping):")
st.json(mapped)

def safe_series(colname, percent_detect=True):
    c = mapped.get(colname)
    if c is None:
        return pd.Series([np.nan]*len(df))
    if colname in ["Receivable Absolute Growth","Receivable Average Receivable Per Month","FD Absolute Growth","Savings Absolute Growth"]:
        s = parse_numeric_series(df[c].astype(str), percent_detect=False)
        return apply_scale(s, scale_choice)
    else:
        return parse_numeric_series(df[c].astype(str), percent_detect=percent_detect)

res = pd.DataFrame()
res["BRANCH"] = df[mapped["BRANCH"]] if mapped.get("BRANCH") else df.iloc[:,0].astype(str)
res["Maturity"] = df[mapped["Maturity"]] if mapped.get("Maturity") else np.nan

components = [
    ("Receivable Absolute Growth","Receivable Scores Absolute Growth", tier_receivable_abs_growth, False),
    ("Receivable Average Receivable Per Month","Receivable Scores Average Receivable Per Month", tier_avg_receivable_month, False),
    ("Receivable Growth %","Receivable Scores Growth %", tier_receivable_growth_pct, True),
    ("No.of files generated","No.of files Generated Score", tier_facilities, False),
    ("Profitabilty","Profitability Score", tier_profitability_contribution, True),
    ("NPL%","NPL Score", tier_npl, True),
    ("FD Absolute Growth","FD Absolute Growth Score", tier_fd_abs_growth, False),
    ("FD Growth %","FD Growth % Score", tier_fd_growth_pct, True),
    ("Savings Absolute Growth","Savings Absolute Growth Score", tier_savings_abs_growth, False),
    ("Savings Growth %","Savings Growth % Score", tier_savings_growth_pct, True),
    ("NIM","NIM Score", tier_nim, True),
    ("No.of solar facilities generated","No.of solar facilities Generated Score", tier_solar, False),
    ("Home Brand facilities","Home Brand facilities Score", tier_home_brands, False)
]

for raw_name, out_name, tier_fn, pct_detect in components:
    series_raw = safe_series(raw_name, percent_detect=pct_detect)
    if raw_name in ["NPL%"]:
        res[f"{raw_name} (raw)"] = series_raw
        res[out_name] = series_raw.apply(tier_fn)
        res[f"{raw_name}::used_as"] = "computed_from_raw"
        continue
    if raw_name in ["Profitabilty"]:
        res[f"{raw_name} (raw)"] = series_raw
        res[out_name] = series_raw.apply(tier_profitability_contribution)
        res[f"{raw_name}::used_as"] = "computed_from_raw"
        continue
    if looks_like_score(series_raw):
        res[out_name] = series_raw.astype(float)
        res[f"{raw_name} (raw)"] = series_raw
        res[f"{raw_name}::used_as"] = "sheet_score"
    else:
        res[f"{raw_name} (raw)"] = series_raw
        res[out_name] = series_raw.apply(tier_fn)
        res[f"{raw_name}::used_as"] = "computed_from_raw"

score_col_names = [
    "Receivable Scores Absolute Growth",
    "Receivable Scores Average Receivable Per Month",
    "Receivable Scores Growth %",
    "No.of files Generated Score",
    "Profitability Score",
    "NPL Score",
    "FD Absolute Growth Score",
    "FD Growth % Score",
    "Savings Absolute Growth Score",
    "Savings Growth % Score",
    "NIM Score",
    "No.of solar facilities Generated Score",
    "Home Brand facilities Score"
]

for sc in score_col_names:
    if sc not in res.columns:
        res[sc] = 0.0

res["Final Score"] = res[score_col_names].sum(axis=1)
res["Rank"] = res["Final Score"].rank(method="dense", ascending=False).astype(int)

output_cols = [
    "BRANCH","Maturity",
    "Receivable Scores Absolute Growth","Receivable Scores Average Receivable Per Month","Receivable Scores Growth %",
    "No.of files Generated Score","Profitability Score","NPL Score","FD Absolute Growth Score","FD Growth % Score",
    "Savings Absolute Growth Score","Savings Growth % Score","NIM Score",
    "No.of solar facilities Generated Score","Home Brand facilities Score",
    "Final Score","Rank"
]

final_out = res.reindex(columns=[c for c in output_cols if c in res.columns])

st.subheader("Final output (scores + rank)")
st.dataframe(final_out.head(200))

diag_cols = [c for c in res.columns if "::used_as" in c]
if diag_cols:
    st.subheader("Diagnostics (how each column was handled for first 50 rows)")
    st.dataframe(res[["BRANCH"] + diag_cols].head(200))

# Download
csv = final_out.to_csv(index=False).encode("utf-8")
st.download_button("📥 Download Final CSV", data=csv, file_name="Branch_Scoring_Auto_Output.csv", mime="text/csv")

st.success("Done — the app auto-detects per-column whether to use sheet scores or compute from raw. If results still look wrong, tell me 2-3 branch names with incorrect Final Score and I will debug those rows exactly.")

