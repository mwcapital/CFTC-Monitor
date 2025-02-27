import streamlit as st
import nasdaqdatalink
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import os
import toml
import datetime
import json
from functions import generate_highlight_ranges, apply_highlights_to_plot


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

######################highliting the desired period#############################


# Convert date column to datetime format (place this after data is fetched)
data["date"] = pd.to_datetime(data["date"])

# Manage highlights (optional, in-memory only via st.session_state)
if st.checkbox("Define Highlight Periods for Instrument", value=False):
    # Initialize or use highlight periods in session state (no file loading)
    if "highlight_periods" not in st.session_state:
        st.session_state.highlight_periods = {}

    instrument_code = st.session_state.instrument_code

    st.subheader("Define Recurring Highlight Periods for Instrument")
    st.write(f"Current Instrument: {instrument_code}")

    # Add a new recurring highlight period (months and days)
    st.write("### Add a New Recurring Highlight Period")
    months = [f"{m:02d}" for m in range(1, 13)]  # List of months (01 to 12)
    start_month = st.selectbox("Start Month", months, index=1)  # Default to January
    start_day = st.number_input("Start Day", min_value=1, max_value=31, value=1)
    end_month = st.selectbox("End Month", months, index=1)  # Default to January
    end_day = st.number_input("End Day", min_value=1, max_value=31, value=1)

    if st.button("Add Recurring Highlight Period"):
        # Validate the date range using the in-memory function
            if instrument_code not in st.session_state.highlight_periods:
                st.session_state.highlight_periods[instrument_code] = []
            st.session_state.highlight_periods[instrument_code].append({
                "start_month": int(start_month),
                "start_day": int(start_day),
                "end_month": int(end_month),
                "end_day": int(end_day)
            })
            st.success(
                f"Added recurring highlight period from {start_month}/{start_day} to {end_month}/{end_day} for instrument {instrument_code}"
            )

    # Display and manage existing recurring highlight periods
    recurring_periods = st.session_state.highlight_periods.get(instrument_code, [])
    if recurring_periods:
        st.write("### Existing Recurring Highlight Periods")
        for i, period in enumerate(recurring_periods):
            if 'start' in period and 'end' in period:  # Old format (though not saved, for completeness)
                start_date = pd.to_datetime(period['start'])
                end_date = pd.to_datetime(period['end'])
                period_str = f"From {start_date.month:02d}/{start_date.day:02d} to {end_date.month:02d}/{end_date.day:02d} (Migrated)"
            elif all(key in period for key in ['start_month', 'start_day', 'end_month', 'end_day']):  # New format
                period_str = f"From {period['start_month']:02d}/{period['start_day']:02d} to {period['end_month']:02d}/{period['end_day']:02d}"
            else:
                period_str = f"Invalid period: {period}"
                continue

            if st.button(f"Remove Period {i + 1}: {period_str}", key=f"remove_{i}_{instrument_code}"):
                st.session_state.highlight_periods[instrument_code].pop(i)
                st.experimental_rerun()  # Refresh the page to update the list
else:
    recurring_periods = []  # No recurring highlights if the user doesn’t want to define periods

######################PLOTTING THE QDL/FON ONLY HERE#############################
## Plotting for QDL/FON Data (only if dataset_code is QDL/FON)
if st.session_state.dataset_code == "QDL/FON":
    # Check if _CHG is in selected type category for default chart type (unused but kept for consistency)
    default_use_bar_charts = "_CHG" in st.session_state.selected_type_category

    # Chart type selection for Participant Positions and Spreads plots
    st.subheader("Chart Type Selection")
    use_bar_charts = st.checkbox("Use Bar Charts (uncheck for Line Charts)", value=False)

    # Participant Positions (Long, Short) Chart with bar mode option
    st.subheader("Participant Positions (Long & Short) by Participant Type")

    # Define new category mappings and colors
    category_colors = {
        "Commercials": "red",
        "Large Speculators": "blue",
        "Small Specs": "yellow"
    }

    # Map original columns to new categories
    longs_mappings = {
        "producer_merchant_processor_user_longs": "Commercials",
        "swap_dealer_longs": "Commercials",
        "money_manager_longs": "Large Speculators",
        "other_reportable_longs": "Large Speculators",
        "non_reportable_longs": "Small Specs"
    }
    shorts_mappings = {
        "producer_merchant_processor_user_shorts": "Commercials",
        "swap_dealer_shorts": "Commercials",
        "money_manager_shorts": "Large Speculators",
        "other_reportable_shorts": "Large Speculators",
        "non_reportable_shorts": "Small Specs"
    }


    participant_bar_mode = st.radio("Select Bar Mode", ["Grouped", "Stacked"], index=0)  # Default to Grouped

    # User selection for longs and shorts - start blank, with unique keys
    selected_longs = [col for col in longs_mappings.keys() if
                     st.checkbox(f"Show {longs_mappings[col]} Longs", value=False, key=f"long_{col}")]
    selected_shorts = [col for col in shorts_mappings.keys() if
                      st.checkbox(f"Show {shorts_mappings[col]} Shorts", value=False, key=f"short_{col}")]

    # Combine selected series (longs and shorts only)
    combined_series = selected_longs + selected_shorts

    if combined_series:
        if use_bar_charts:
            if participant_bar_mode == "Grouped":
                # Grouped bar chart for longs and shorts
                fig2 = px.bar(
                    data,
                    x="date",
                    y=combined_series,
                    title="Participant Positions (Long & Short) by Participant Type",
                    barmode='group',  # Grouped bars side by side
                    color_discrete_map={col: category_colors[longs_mappings[col] if col in longs_mappings else shorts_mappings[col]] for col in combined_series}
                )
            else:  # Stacked
                # Stacked bar chart for longs and shorts
                fig2 = px.bar(
                    data,
                    x="date",
                    y=combined_series,
                    title="Participant Positions (Long & Short) by Participant Type",
                    barmode='stack',  # Stacked bars
                    color_discrete_map={col: category_colors[longs_mappings[col] if col in longs_mappings else shorts_mappings[col]] for col in combined_series}
                )
            fig2.update_traces(width=8)  # Fixed bar width for thicker bars
            fig2.update_layout(
                barmode='group' if participant_bar_mode == "Grouped" else 'stack',  # Ensure consistent barmode
                xaxis_title="Date",
                yaxis_title="Value",
                legend_title_text="Participant Type",
                legend=dict(orientation="h", y=-0.2),
                bargap=0.05,  # Fixed space between bars
                height=600,  # Increase plot height for better visibility
                width=1200   # Increase plot width for better readability
            )
        else:
            # Line chart for longs and shorts
            fig2 = px.line(
                data,
                x="date",
                y=combined_series,
                title="Participant Positions (Long & Short) by Participant Type",
                color_discrete_map={col: category_colors[longs_mappings[col] if col in longs_mappings else shorts_mappings[col]] for col in combined_series}
            )
            fig2.update_layout(
                xaxis_title="Date",
                yaxis_title="Value",
                legend_title_text="Participant Type",
                legend=dict(orientation="h", y=-0.2),
                height=600,  # Increase plot height for better visibility
                width=1200   # Increase plot width for better readability
            )

        # Dynamically set y-axis range based on data
        y_values = data[combined_series].values.flatten()
        if y_values.size > 0:  # Check if there are any values
            y_min = min(y_values) * 1.1  # Add 10% padding below
            y_max = max(y_values) * 1.1  # Add 10% padding above
            fig2.update_layout(yaxis_range=[y_min, y_max])

        apply_highlights_to_plot(fig2, data, recurring_periods)  # Use the function from functions.py
        st.plotly_chart(fig2, use_container_width=True)

    # Spreads Chart (always grouped bars, using original column names)
    st.subheader("Spreads by Participant Type")

    spread_columns_to_plot = {
        "swap_dealer_spreads": "Swap Dealer Spreads",
        "money_manager_spreads": "Money Manager Spreads",
        "other_reportable_spreads": "Other Reportable Spreads"
    }

    # User selection for spreads - start blank, with unique keys
    selected_spread_series = [col for col in spread_columns_to_plot.keys() if
                            st.checkbox(f"Show {spread_columns_to_plot[col]}", value=False, key=f"spread_{col}")]

    if selected_spread_series:
        if use_bar_charts:
            # Grouped bar chart for spreads (using original names, default colors)
            fig3 = px.bar(
                data,
                x="date",
                y=selected_spread_series,
                title="Spreads by Participant Type",
                barmode='group',  # Fixed as grouped bars
                color_discrete_sequence=px.colors.qualitative.Set3  # Use default Plotly colors
            )
            fig3.update_traces(width=8)  # Fixed bar width for thicker bars
            fig3.update_layout(
                xaxis_title="Date",
                yaxis_title="Value",
                legend_title_text="Spread Type",
                legend=dict(orientation="h", y=-0.2),
                bargap=0.05,  # Fixed space between bars
                height=600,  # Increase plot height for better visibility
                width=1200   # Increase plot width for better readability
            )
        else:
            # Line chart for spreads (using original names, default colors)
            fig3 = px.line(
                data,
                x="date",
                y=selected_spread_series,
                title="Spreads by Participant Type",
                color_discrete_sequence=px.colors.qualitative.Set3  # Use default Plotly colors
            )
            fig3.update_layout(
                xaxis_title="Date",
                yaxis_title="Value",
                legend_title_text="Spread Type",
                legend=dict(orientation="h", y=-0.2),
                height=600,  # Increase plot height for better visibility
                width=1200   # Increase plot width for better readability
            )

        # Dynamically set y-axis range based on data
        y_values = data[selected_spread_series].values.flatten()
        if y_values.size > 0:  # Check if there are any values
            y_min = min(y_values) * 1.1  # Add 10% padding below
            y_max = max(y_values) * 1.1  # Add 10% padding above
            fig3.update_layout(yaxis_range=[y_min, y_max])

        apply_highlights_to_plot(fig3, data, recurring_periods)  # Use the function from functions.py
        st.plotly_chart(fig3, use_container_width=True)

    # Net Positions Chart (always grouped bars)
    st.subheader("Net Positions by Participant Type")

    # Calculate net positions for each category
    data["commercials_net"] = (data["producer_merchant_processor_user_longs"] + data["swap_dealer_longs"]) - \
                              (data["producer_merchant_processor_user_shorts"] + data["swap_dealer_shorts"])
    data["large_speculators_net"] = (data["money_manager_longs"] + data["other_reportable_longs"]) - \
                                    (data["money_manager_shorts"] + data["other_reportable_shorts"])
    data["small_specs_net"] = data["non_reportable_longs"] - data["non_reportable_shorts"]

    net_columns_to_plot = [
        "commercials_net",
        "large_speculators_net",
        "small_specs_net"
    ]

    # Define net category mappings and colors (same as before)
    net_category_mappings = {
        "commercials_net": "Commercials",
        "large_speculators_net": "Large Speculators",
        "small_specs_net": "Small Specs"
    }

    # User selection for nets - start blank, with unique keys
    selected_nets = [col for col in net_columns_to_plot if
                    st.checkbox(f"Show {net_category_mappings[col]} Net", value=False, key=f"net_{col}")]

    if selected_nets:
        # Always use grouped bar chart for net positions
        fig4 = px.bar(
            data,
            x="date",
            y=selected_nets,
            title="Net Positions by Participant Type",
            barmode='group',  # Ensures bars are side by side
            color_discrete_map={col: category_colors[net_category_mappings[col]] for col in selected_nets}
        )
        fig4.update_traces(width=8)  # Fixed bar width for thicker bars
        fig4.update_layout(
            xaxis_title="Date",
            yaxis_title="Value",
            legend_title_text="Net Type",
            legend=dict(orientation="h", y=-0.2),
            bargap=0.05,  # Fixed space between bars
            height=600,  # Increase plot height for better visibility
            width=1200   # Increase plot width for better readability
        )

        # Dynamically set y-axis range based on data
        y_values = data[selected_nets].values.flatten()
        if y_values.size > 0:  # Check if there are any values
            y_min = min(y_values) * 1.1  # Add 10% padding below
            y_max = max(y_values) * 1.1  # Add 10% padding above
            fig4.update_layout(yaxis_range=[y_min, y_max])

        apply_highlights_to_plot(fig4, data, recurring_periods)  # Use the function from functions.py
        st.plotly_chart(fig4, use_container_width=True)
######################PLOTTING THE QDL/LFON ONLY HERE#############################
# Plotting for QDL/LFON Data (only if dataset_code is QDL/LFON)
if st.session_state.dataset_code == "QDL/LFON":
    # Chart type selection for Long & Short, Spreads, and Net plots
    st.subheader("Chart Type Selection")
    use_bar_charts = st.checkbox("Use Bar Charts (uncheck for Line Charts)", value=False)

    # Long & Short Positions Chart with bar mode option
    st.subheader("Long & Short Positions by Participant Type")

    longs_columns_to_plot = [
        "non_commercial_longs",
        "commercial_longs",
        "total_reportable_longs",
        "non_reportable_longs"
    ]
    shorts_columns_to_plot = [
        "non_commercial_shorts",
        "commercial_shorts",
        "total_reportable_shorts",
        "non_reportable_shorts"
    ]

    # Add option to switch between grouped and stacked bars for Long & Short plot
    st.write("### Long & Short Bar Mode")
    long_short_bar_mode = st.radio("Select Bar Mode", ["Grouped", "Stacked"], index=0)  # Default to Grouped

    # User selection for longs and shorts - start blank
    selected_longs = [col for col in longs_columns_to_plot if
                     st.checkbox(f"Show {col.replace('_', ' ').title()}", value=False)]
    selected_shorts = [col for col in shorts_columns_to_plot if
                      st.checkbox(f"Show {col.replace('_', ' ').title()}", value=False)]

    # Combine selected series (longs and shorts only)
    combined_series = selected_longs + selected_shorts

    if combined_series:
        if use_bar_charts:
            if long_short_bar_mode == "Grouped":
                # Grouped bar chart for longs and shorts
                fig2 = px.bar(
                    data,
                    x="date",
                    y=combined_series,
                    title="Long & Short Positions by Participant Type",
                    barmode='group'  # Grouped bars side by side
                )
            else:  # Stacked
                # Stacked bar chart for longs and shorts
                fig2 = px.bar(
                    data,
                    x="date",
                    y=combined_series,
                    title="Long & Short Positions by Participant Type",
                    barmode='stack'  # Stacked bars
                )
            fig2.update_traces(width=8)  # Fixed bar width for thicker bars
            fig2.update_layout(bargap=0.05)  # Fixed space between bars
        else:
            # Line chart for longs and shorts
            fig2 = px.line(
                data,
                x="date",
                y=combined_series,
                title="Long & Short Positions by Participant Type"
            )
        fig2.update_layout(
            xaxis_title="Date",
            yaxis_title="Value",
            legend=dict(orientation="h", y=-0.2),
            height=600,  # Increase plot height for better visibility
            width=1200   # Increase plot width for better readability
        )

        # Dynamically set y-axis range based on data
        y_values = data[combined_series].values.flatten()
        if y_values.size > 0:  # Check if there are any values
            y_min = min(y_values) * 1.1  # Add 10% padding below
            y_max = max(y_values) * 1.1  # Add 10% padding above
            fig2.update_layout(yaxis_range=[y_min, y_max])

        apply_highlights_to_plot(fig2, data, recurring_periods)  # Use the function from functions.py
        st.plotly_chart(fig2, use_container_width=True)  # Use full container width in Streamlit

    # Spreads Chart (without Market Participation, always grouped bars)
    st.subheader("Spread Positions by Participant Type")
    spreads_columns_to_plot = ["non_commercial_spreads"]

    # User selection for spreads - start blank
    selected_spreads = [col for col in spreads_columns_to_plot if
                       st.checkbox(f"Show {col.replace('_', ' ').title()}", value=False)]

    if selected_spreads:
        if use_bar_charts:
            # Grouped bar chart for spreads
            fig3 = px.bar(
                data,
                x="date",
                y=selected_spreads,
                title="Spread Positions by Participant Type",
                barmode='group'  # Fixed as grouped bars
            )
            fig3.update_traces(width=8)  # Fixed bar width for thicker bars
            fig3.update_layout(bargap=0.05)  # Fixed space between bars
        else:
            # Line chart for spreads
            fig3 = px.line(
                data,
                x="date",
                y=selected_spreads,
                title="Spread Positions by Participant Type"
            )
        fig3.update_layout(
            xaxis_title="Date",
            yaxis_title="Value",
            legend=dict(orientation="h", y=-0.2),
            height=600,  # Increase plot height for better visibility
            width=1200   # Increase plot width for better readability
        )

        # Dynamically set y-axis range for Spreads chart
        y_values = data[selected_spreads].values.flatten()
        if y_values.size > 0:  # Check if there are any values
            y_min = min(y_values) * 1.1  # Add 10% padding below
            y_max = max(y_values) * 1.1  # Add 10% padding above
            fig3.update_layout(yaxis_range=[y_min, y_max])

        apply_highlights_to_plot(fig3, data, recurring_periods)  # Use the function from functions.py
        st.plotly_chart(fig3, use_container_width=True)  # Use full container width in Streamlit

    # Net Positions Chart (always grouped bars)
    st.subheader("Net Positions by Participant Type")

    # Calculate net positions
    data["commercial_net"] = data["commercial_longs"] - data["commercial_shorts"]
    data["non_commercial_net"] = data["non_commercial_longs"] - data["non_commercial_shorts"]
    data["non_reportables_net"] = data["non_reportable_longs"] - data["non_reportable_shorts"]
    data["total_net"] = data["total_reportable_longs"] - data["total_reportable_shorts"]

    net_columns_to_plot = [
        "commercial_net",
        "non_commercial_net",
        "non_reportables_net",
        "total_net"
    ]

    # Define net category mappings and colors
    net_category_mappings = {
        "commercial_net": "Commercials",
        "non_commercial_net": "Non Commercials Net",
        "non_reportables_net": "Non Reportables",
        "total_net": "Total Net"
    }
    net_category_colors = {
        "Commercials": "red",
        "Non Commercials Net": "blue",
        "Non Reportables": " yellow",
        "Total Net": "green"
    }

    # User selection for nets - start blank
    selected_nets = [col for col in net_columns_to_plot if
                    st.checkbox(f"Show {net_category_mappings[col]}", value=False)]

    if selected_nets:
        # Always use grouped bar chart for net positions
        fig4 = px.bar(
            data,
            x="date",
            y=selected_nets,
            title="Net Positions by Participant Type",
            barmode='group',  # Ensures bars are side by side
            color_discrete_map={col: net_category_colors[net_category_mappings[col]] for col in selected_nets}
        )
        fig4.update_traces(width=8)  # Fixed bar width for thicker bars
        fig4.update_layout(bargap=0.05)  # Fixed space between bars

        fig4.update_layout(
            xaxis_title="Date",
            yaxis_title="Value",
            legend=dict(orientation="h", y=-0.2),
            height=600,  # Increase plot height for better visibility
            width=1200   # Increase plot width for better readability
        )

        # Dynamically set y-axis range based on data
        y_values = data[selected_nets].values.flatten()
        if y_values.size > 0:  # Check if there are any values
            y_min = min(y_values) * 1.1  # Add 10% padding below
            y_max = max(y_values) * 1.1  # Add 10% padding above
            fig4.update_layout(yaxis_range=[y_min, y_max])

        apply_highlights_to_plot(fig4, data, recurring_periods)  # Use the function from functions.py
        st.plotly_chart(fig4, use_container_width=True)  # Use full container width in Streamlit

    # Market Participation Chart (separate, always line)
    st.subheader("Market Participation Over Time")

    # User selection for market participation - start blank
    show_market_participation = st.checkbox("Show Market Participation", value=False)

    if show_market_participation:
        fig5 = px.line(
            data,
            x="date",
            y="market_participation",
            title="Market Participation Over Time"
        )
        fig5.update_layout(
            xaxis_title="Date",
            yaxis_title="Value",
            legend=dict(orientation="h", y=-0.2),
            height=600,  # Increase plot height for better visibility
            width=1200   # Increase plot width for better readability
        )

        # Dynamically set y-axis range for Market Participation chart
        y_values = data["market_participation"].values.flatten()
        if y_values.size > 0:  # Check if there are any values
            y_min = min(y_values) * 1.1  # Add 10% padding below
            y_max = max(y_values) * 1.1  # Add 10% padding above
            fig5.update_layout(yaxis_range=[y_min, y_max])

        apply_highlights_to_plot(fig5, data, recurring_periods)  # Use the function from functions.py
        st.plotly_chart(fig5, use_container_width=True)  # Use full container width in Streamlitiner width in Streamlitull container width in Streamlit
######################PLOTTING THE QDL/FCR ONLY HERE#############################

if st.session_state.dataset_code == "QDL/FCR":
    st.subheader("Concentration Ratios: Largest Traders")

    concentration_columns = {
        "largest_4_longs_gross": "Top 4 Largest Traders (Gross Long Positions)",
        "largest_4_shorts_gross": "Top 4 Largest Traders (Gross Short Positions)",
        "largest_8_longs_gross": "Top 8 Largest Traders (Gross Long Positions)",
        "largest_8_shorts_gross": "Top 8 Largest Traders (Gross Short Positions)",
        "largest_4_longs_net": "Top 4 Largest Traders (Net Long Positions)",
        "largest_4_shorts_net": "Top 4 Largest Traders (Net Short Positions)",
        "largest_8_longs_net": "Top 8 Largest Traders (Net Long Positions)",
        "largest_8_shorts_net": "Top 8 Largest Traders (Net Short Positions)"
    }

    selected_series = [col for col in concentration_columns if st.checkbox(
        f"Show {concentration_columns[col]}", value=True,
        help="Displays data for the selected group of large traders."
    )]

    if selected_series:
        fig = px.line(data, x="date", y=selected_series, title="Concentration Ratios: Largest Traders")
        fig.update_layout(legend=dict(orientation="h", y=-0.2))

        st.plotly_chart(fig, use_container_width=True)
