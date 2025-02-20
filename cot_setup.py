import nasdaqdatalink
import streamlit as st
import os
import toml
import streamlit as st
import nasdaqdatalink

st.set_page_config(page_title="CFTC Monitor", layout="wide")

# Initialize session state variables if they don’t exist
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

if "dataset_code" not in st.session_state:
    st.session_state.dataset_code = ""

if "instrument_code" not in st.session_state:
    st.session_state.instrument_code = ""

if "selected_type_category" not in st.session_state:
    st.session_state.selected_type_category = ""

# Streamlit UI
st.title("CFTC - Set Up")

# Try loading from local secrets.toml first
api_key = st.session_state.api_key  # Use session state if already set

if not api_key and os.path.exists("secrets.toml"):
    try:
        local_secrets = toml.load("secrets.toml")
        api_key = local_secrets.get("NASDAQ_API_KEY")
    except Exception as e:
        st.error(f"Error loading local secrets: {e}")

# If not found locally, load from Streamlit Cloud secrets
if not api_key:
    api_key = st.secrets.get("NASDAQ_API_KEY", None)

# Handle missing API key
if not api_key:
    st.error("API Key is missing! Please add it in Streamlit Secrets or `secrets.toml`.")
    st.stop()  # Stop execution if no API key is found

# Store API Key in session state & configure Nasdaq Data Link
st.session_state.api_key = api_key
nasdaqdatalink.ApiConfig.api_key = api_key

st.success(f"Using API Key: {api_key[:5]}******")

# Button to confirm API key
if st.button("Submit API Key"):
    st.success("API Key saved successfully!")

# Dataset selection dropdown
dataset_code = st.selectbox(
    "Select Dataset Code",
    ["QDL/FON", "QDL/LFON", "QDL/FCR", "QDL/CITS"]
)

# Instrument selection dropdown
instrument_mapping = {
    "Crude WTI": "067651",
    "Brent (last day)": "06765T",
    "GC": "088691",
    "Nat Gas": "03565B",
    "10 year e-mini sofr swap": "343603",
    "eMini S&P500": "13874A",
    "YM (not sure it is correct)": "124603",
    "RTY mini": "239742",
    "NASDAQ MINI": "209742",
    "Dollar Index": "098662",
    "6E Euro Index": "6E",
    "Vix": "1170E1"
}
selected_instrument = st.selectbox("Select Instrument", list(instrument_mapping.keys()))
instrument_code = instrument_mapping[selected_instrument]


# Checkbox for Legacy selection
use_legacy = st.checkbox("Use Legacy Format", value=False)

# Dropdown for selecting F or FO
base_type = st.selectbox("Select Base Type", ["F", "FO"])

# Dropdown for selecting _ALL or _CHG
all_or_chg = st.selectbox("Select Data Type", ["ALL", "CHG"])

# Multi-select for optional suffix (_CR, _NT, _OI)
suffix_options = ["_CR", "_NT", "_OI"]
selected_suffixes = st.multiselect("Select Additional Categories", suffix_options)

# Construct the type category dynamically
prefix = f"{base_type}_L" if use_legacy else base_type
type_category_options = [f"{prefix}_{all_or_chg}{suffix}" for suffix in [""] + selected_suffixes]

# Dropdown for selecting the final Type & Category
selected_type_category = st.selectbox("Select Type & Category", type_category_options)

# Store parameters in session state
st.session_state.dataset_code = dataset_code
st.session_state.instrument_code = instrument_code
st.session_state.selected_type_category = selected_type_category

st.write("Go to the **COT Monitor** page to view analysis.")