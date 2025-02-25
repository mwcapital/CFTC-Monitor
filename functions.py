import streamlit as st
import pandas as pd
import json
import os
import datetime
from typing import List, Dict, Optional


def generate_highlight_ranges(data: pd.DataFrame, recurring_periods: List[Dict]) -> List[tuple]:
    """
    Generate highlight ranges for all years in the data based on recurring periods.

    Args:
        data (pd.DataFrame): DataFrame containing the 'date' column.
        recurring_periods (List[Dict]): List of period dictionaries with recurring month/day data.

    Returns:
        List[tuple]: List of (start_date, end_date) tuples for highlighting.
    """
    highlight_ranges = []
    if not recurring_periods:
        return highlight_ranges

    min_date = data["date"].min()
    max_date = data["date"].max()

    for period in recurring_periods:
        if 'start' in period and 'end' in period:  # Old format: specific dates
            start_date = pd.to_datetime(period['start'])
            end_date = pd.to_datetime(period['end'])
            start_month = start_date.month
            start_day = start_date.day
            end_month = end_date.month
            end_day = end_date.day
        elif all(
                key in period for key in ['start_month', 'start_day', 'end_month', 'end_day']):  # New format: recurring
            start_month = period['start_month']
            start_day = period['start_day']
            end_month = period['end_month']
            end_day = period['end_day']
        else:
            continue

        for year in data["date"].dt.year.unique():
            try:
                start_date = pd.to_datetime(f"{year}-{start_month:02d}-{start_day:02d}")
                end_date = pd.to_datetime(f"{year}-{end_month:02d}-{end_day:02d}")

                if min_date <= start_date <= max_date and min_date <= end_date <= max_date:
                    if start_date <= end_date:
                        start_date = max(start_date, min_date)
                        end_date = min(end_date, max_date)
                        highlight_ranges.append((start_date, end_date))
                    else:
                        continue
            except ValueError:
                continue

    return highlight_ranges


def apply_highlights_to_plot(fig, data: pd.DataFrame, recurring_periods: List[Dict]) -> None:
    """
    Apply highlight regions to a Plotly figure based on recurring periods and data.

    Args:
        fig: Plotly figure to apply highlights to.
        data (pd.DataFrame): DataFrame containing the 'date' column.
        recurring_periods (List[Dict]): List of period dictionaries with recurring month/day data.
    """
    highlight_ranges = generate_highlight_ranges(data, recurring_periods)
    if highlight_ranges:
        for start_date, end_date in highlight_ranges:
            fig.add_vrect(
                x0=start_date, x1=end_date,
                fillcolor="rgba(255, 50, 50, 0.5)",  # Dark red, visible but not overpowering
                opacity=0.9, layer="below",
                line_width=2, line_color="black"
            )
    else:
        st.info("No recurring highlight periods defined.")
