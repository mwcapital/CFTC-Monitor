import streamlit as st
import nasdaqdatalink
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import os
import toml

st.title("CFTC Monitor - Data Analysis")

# Try loading API Key from local file
api_key = st.session_state.get("api_key", None)  # Use session state if already set

if not api_key and os.path.exists("secrets.toml"):
    try:
        local_secrets = toml.load("secrets.toml")
        api_key = local_secrets.get("NASDAQ_API_KEY")
    except Exception as e:
        st.error(f"Error loading local secrets: {e}")

# If not found locally, try getting from Streamlit Cloud
if not api_key:
    api_key = st.secrets.get("NASDAQ_API_KEY", None)

# Handle missing API key
if not api_key:
    st.error("API Key is missing! Please add it in Streamlit Secrets or `secrets.toml`.")
    st.stop()

# Set API Key for Nasdaq Data Link & store in session state
st.session_state.api_key = api_key
nasdaqdatalink.ApiConfig.api_key = api_key

st.success(f"Using API Key: {api_key[:5]}******")

# Retrieve parameters from session state
if not all(key in st.session_state for key in ["dataset_code", "instrument_code", "selected_type_category"]):
    st.error("Missing dataset parameters! Please go back to the setup page.")
    st.stop()

dataset_code = st.session_state.dataset_code
instrument_code = st.session_state.instrument_code
type_category = st.session_state.selected_type_category

st.write(f"**Dataset Code:** {dataset_code}")
st.write(f"**Instrument Code:** {instrument_code}")
st.write(f"**Type & Category:** {type_category}")

# Fetch full data initially
data = nasdaqdatalink.get_table(
    dataset_code,  # Example: 'QDL/FON'
    contract_code=instrument_code,  # Example: '067651'
    type=type_category  # Example: 'F_ALL', 'FO_CHG'
)

# Display raw data first
st.subheader("Raw Data")
st.dataframe(data)  # Show full table

# Date selection AFTER fetching the data
st.subheader("Filter by Date")
start_date = st.date_input("Select Start Date")
end_date = st.date_input("Select End Date")

# Apply date filtering only if a date range is selected
if start_date and end_date:
    filtered_data = data[(data["date"] >= str(start_date)) & (data["date"] <= str(end_date))]
    st.subheader("Filtered Data")
    st.dataframe(filtered_data)
else:
    st.info("Select a date range to filter the data.")

######################PLOTTING THE QDL/FON ONLY HERE#############################

# Convert date column to datetime format
data["date"] = pd.to_datetime(data["date"])

# Function to get working day ranges for highlighting
def get_highlight_ranges(df, month, num_days):
    filtered = df[(df["date"].dt.month == month) & (df["date"].dt.weekday < 5)].head(num_days)
    if len(filtered) > 0:
        return [(filtered["date"].min(), filtered["date"].max())]
    return []

# Get highlighted date ranges (batch processing)
highlight_ranges = []
for year in data["date"].dt.year.unique():
    yearly_data = data[data["date"].dt.year == year]
    highlight_ranges.extend(get_highlight_ranges(yearly_data, 2, 10))  # Feb (First 2 weeks)
    highlight_ranges.extend(get_highlight_ranges(yearly_data, 9, 11))  # Sep (First 11 working days)
    highlight_ranges.extend(get_highlight_ranges(yearly_data, 12, 12))  # Dec (First 12 working days)

# Function to add highlight regions efficiently
def add_highlight_regions(fig):
    for start_date, end_date in highlight_ranges:
        fig.add_vrect(
            x0=start_date, x1=end_date,
            fillcolor="rgba(255, 50, 50, 0.5)",  # Dark red, visible but not overpowering
            opacity=0.9, layer="below",
            line_width=2, line_color="black"
        )

# Market Participation Chart
if st.session_state.dataset_code == "QDL/FON":
    st.subheader("Market Participation Over Time")

    fig1 = px.line(data, x="date", y="market_participation", title="Market Participation Over Time")
    fig1.update_layout(legend=dict(orientation="h", y=-0.2))
    add_highlight_regions(fig1)
    st.plotly_chart(fig1, use_container_width=True)

    # Long Positions Chart
    st.subheader("Long Positions by Participant Type")

    long_columns_to_plot = [
        "producer_merchant_processor_user_longs",
        "swap_dealer_longs",
        "money_manager_longs",
        "other_reportable_longs",
        "non_reportable_longs"
    ]

    selected_long_series = [col for col in long_columns_to_plot if st.checkbox(f"Show {col.replace('_', ' ').title()}", value=True)]

    if selected_long_series:
        fig2 = px.line(data, x="date", y=selected_long_series, title="Long Positions by Participant Type")
        fig2.update_layout(legend=dict(orientation="h", y=-0.2))
        add_highlight_regions(fig2)
        st.plotly_chart(fig2, use_container_width=True)

    # Short Positions Chart
    st.subheader("Short Positions by Participant Type")

    short_columns_to_plot = [
        "producer_merchant_processor_user_shorts",
        "swap_dealer_shorts",
        "money_manager_shorts",
        "other_reportable_shorts",
        "non_reportable_shorts"
    ]

    selected_short_series = [col for col in short_columns_to_plot if st.checkbox(f"Show {col.replace('_', ' ').title()}", value=True)]

    if selected_short_series:
        fig3 = px.line(data, x="date", y=selected_short_series, title="Short Positions by Participant Type")
        fig3.update_layout(legend=dict(orientation="h", y=-0.2))
        add_highlight_regions(fig3)
        st.plotly_chart(fig3, use_container_width=True)
