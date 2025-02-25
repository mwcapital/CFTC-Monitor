
import streamlit as st
import nasdaqdatalink
import os
import toml
import json
import pandas as pd
from functions import generate_highlight_ranges, apply_highlights_to_plot  # Ensure this import exists

# Page configuration
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

# Strictly load instrument mapping from instruments.json
instrument_mapping_file = "instruments.json"
if not os.path.exists(instrument_mapping_file):
    st.error("instruments.json file not found. Please ensure the file exists in the app directory with the instrument mappings.")
    st.stop()  # Stop execution if the file doesn’t exist

try:
    with open(instrument_mapping_file, "r") as f:
        st.session_state.instrument_mapping = json.load(f)
except json.JSONDecodeError as e:
    st.error(f"Error decoding instruments.json: {e}")
    st.stop()  # Stop execution if the JSON is invalid
except Exception as e:
    st.error(f"Error loading instruments.json: {e}")
    st.stop()  # Stop execution for other file-related errors

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




# Instrument selection, addition, and removal
st.subheader("Instrument Selection")

# Allow user to select from predefined instruments (using session state mapping)
selected_instrument = st.selectbox("Select an Instrument", list(st.session_state.instrument_mapping.keys()))
instrument_code = st.session_state.instrument_mapping[selected_instrument]


# Checkbox for Legacy selection
use_legacy = st.checkbox("Use Legacy Format", value=False)

# Dropdown for selecting F or FO
base_type = st.selectbox("Select Base Type", ["F", "FO", "CITS"])

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








# Section for managing instruments (add and remove)
st.write("### Manage Instruments")

# Add a new instrument
st.write("#### Add a New Instrument")
new_instrument_name = st.text_input("Enter Product Name", placeholder="e.g., Copper Futures")
new_instrument_code = st.text_input("Enter Instrument Code", placeholder="e.g., 123456")

if st.button("Add Instrument"):
    if new_instrument_name and new_instrument_code:
        st.session_state.instrument_mapping[new_instrument_name] = new_instrument_code
        # Save updated mapping to file
        try:
            with open(instrument_mapping_file, "w") as f:
                json.dump(st.session_state.instrument_mapping, f, indent=4)
            st.success(f"Added: {new_instrument_name} ({new_instrument_code})")
            st.experimental_rerun()  # Refresh the app to update the selectbox and removal options
        except Exception as e:
            st.error(f"Error saving instruments.json: {e}")
    else:
        st.warning("Please enter both a product name and a code.")

# Remove an instrument
st.write("#### Remove an Instrument")
instrument_to_remove = st.selectbox("Select Instrument to Remove", list(st.session_state.instrument_mapping.keys()), index=None)
if st.button("Remove Instrument"):
    if instrument_to_remove:
        if instrument_to_remove == selected_instrument:
            st.warning("Cannot remove the currently selected instrument. Please select a different instrument first.")
        else:
            del st.session_state.instrument_mapping[instrument_to_remove]
            # Save updated mapping to file
            try:
                with open(instrument_mapping_file, "w") as f:
                    json.dump(st.session_state.instrument_mapping, f, indent=4)
                st.success(f"Removed: {instrument_to_remove}")
                st.experimental_rerun()  # Refresh the app to update the selectbox and removal options
            except Exception as e:
                st.error(f"Error saving instruments.json: {e}")
    else:
        st.warning("Please select an instrument to remove.")

# Update session state with the selected instrument
st.session_state.instrument_code = instrument_code
st.session_state.selected_instrument = selected_instrument

st.write(f"**Selected Instrument Code:** {instrument_code}")

# Store parameters in session state
st.session_state.dataset_code = dataset_code
st.session_state.instrument_code = instrument_code
st.session_state.selected_type_category = selected_type_category



st.write("Go to the **COT Monitor** page to view analysis.")

st.markdown("""
## 📌 Understanding the Report Structure

The dataset is structured into three main parts: **Type, Category, and Sub-category**.



### **1 Choose Core Dataset **
This defines the **scope** of the report.
- **FO** – Futures and Options Combined 
- **F** – Futures Only 
 

### **2 if you want legacy tick the legacy too**

### **3 Choose  Category (Position Type)**
This specifies how positions are categorized.
- **ALL** – All positions included  
- **CHG** – Changes in positions   
 

### **4 Choose Sub category **
These sub-categories provide additional analysis:
- **_CR** – Concentration Ratios: Largest traders’ positions   
(this is needed if you want to see top 4 longs and shorts)
- **_NT** – Number of Traders in the market 
- **_OI** – Open Interest: Total outstanding contracts   

You can select different combinations of these to customize your analysis.

""")





st.markdown("""
## Understanding Legacy vs. Non-Legacy CFTC Reports  

### Legacy Reports  
The **Legacy COT Report** has been published since 1968 and provides a simplified breakdown of market positions:  
- **Commercial Traders**: Entities hedging against price risk (e.g., producers, manufacturers).  
- **Non-Commercial Traders**: Speculative traders such as hedge funds and large investors.  
- **Non-Reportable Traders**: Small traders whose positions are too small to be categorized.  

These reports aggregate **futures-only** and **futures + options combined** data with minimal granularity.  

### Non-Legacy (Disaggregated) Reports  
Introduced in **2009**, the **Disaggregated COT Report** offers more detailed trader classifications:  
- **Producer/Merchant/Processor/User**: Entities using futures to hedge physical market risk.  
- **Swap Dealers**: Financial institutions using swaps and futures for risk management.  
- **Money Managers**: Hedge funds and institutional investors.  
- **Other Reportables**: Large traders that do not fit other categories.  

This version provides better transparency on speculative vs. hedging activity.  

### Key Differences  
| Feature               | Legacy Report          | Non-Legacy (Disaggregated) |
|----------------------|----------------------|---------------------------|
| **First Available**  | 1968                 | 2009                      |
| **Trader Breakdown** | 3 Categories         | 4 Categories               |
| **Hedge Funds**      | Not Separate         | Categorized as Money Managers |
| **Swap Dealers**     | Not Identified       | Categorized Separately |
| **Transparency**     | Lower                | Higher                     |

**When to Use Each:**  
- Use **Legacy Reports** for long-term historical analysis .  
- Use **Non-Legacy Reports** for more precise trader classification.  
""")
