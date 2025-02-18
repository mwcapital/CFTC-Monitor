import nasdaqdatalink
import streamlit as st

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
st.title("CFTC-Set Up")

# API Key input
api_key = st.secrets["NASDAQ_API_KEY"]


if st.button("Submit API Key"):
    if not api_key:
        st.error("API Key is required!")
    else:
        st.session_state.api_key = api_key  # Store API key in session state
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

# Single dropdown for Type + Category combination
type_category_options = ["F_ALL", "F_CHG", "FO_ALL", "FO_CHG"]
selected_type_category = st.selectbox("Select Type & Category", type_category_options)

# Store parameters in session state
st.session_state.dataset_code = dataset_code
st.session_state.instrument_code = instrument_code
st.session_state.selected_type_category = selected_type_category

st.write("Go to the **COT Monitor** page to view analysis.")