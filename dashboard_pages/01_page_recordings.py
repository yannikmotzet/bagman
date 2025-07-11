import os

import pandas as pd
import streamlit as st

from bagman.utils import bagman_utils
from bagman.utils.db import BagmanDB
from dashboard_pages import dashboard_utils

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "..", "config.yaml")


def main():
    st.header("Recordings")

    try:
        config = bagman_utils.load_config(CONFIG_PATH)
    except Exception as e:
        st.error(f"Error loading config: {e}")
        return

    try:
        with st.spinner("Connecting to database..."):
            # the abspath check is required to use the recordings_example.json which has a relative path
            if config["database_type"] == "json":
                database_path = config["database_uri"]
                if not os.path.isabs(database_path):
                    database_path = os.path.join(PROJECT_ROOT, database_path)
                db = BagmanDB(
                    config["database_type"], database_path, config["database_name"]
                )
            else:
                db = BagmanDB(
                    config["database_type"],
                    config["database_uri"],
                    config["database_name"],
                )
            data = dashboard_utils.load_recordings(db, config)
    except Exception:
        st.error("⚠️ no connection to database")
        return

    num_total_data = len(data)
    columns = data.columns.tolist()

    st_sidebar = st.sidebar
    col1, col2 = st_sidebar.columns(2)
    with col1:
        st.metric("number all results", num_total_data, border=False)
    with col2:
        st_metric_number_results = st.empty()

    # filter data based on search query
    search_query = st_sidebar.text_input("Search", "")
    if search_query:
        data = data[
            data.apply(
                lambda row: row.astype(str)
                .str.contains(search_query, case=False)
                .any(),
                axis=1,
            )
        ]

    # option to add/remove columns (alternative: st.pills, st.segmented_control with selection_mode="multi")
    selectable_columns = [
        col for col in columns if col not in config["dash_cols_mandatory"]
    ]
    # default_columns = [c for c in selectable_columns if c not in HIDDEN_COLUMNS]
    selected_columns = st_sidebar.multiselect(
        "Show columns", options=selectable_columns, default=config["dash_cols_default"]
    )

    # apply selected columns to the data
    data = data[config["dash_cols_mandatory"] + selected_columns]

    # reorder default columns
    valid_default_columns = [
        col for col in config["dash_cols_default"] if col in data.columns
    ]
    ordered_columns = valid_default_columns + [
        col for col in data.columns if col not in valid_default_columns
    ]
    data = data[ordered_columns]

    # add a checkbox to turn on/off the filters
    enable_filters = st_sidebar.toggle("Enable Filters", value=False)
    if enable_filters:
        data = dashboard_utils.filter_recording(data, st_sidebar, config)

    if num_total_data != len(data):
        st_metric_number_results.metric("number filtered results", len(data))

    # fix the issue of timedelta64[ns] not being displayed correctly (https://discuss.streamlit.io/t/streamlit-treats-timedelta-column-as-strings/84487)
    for column in config["dash_cols_timedelta"]:
        if column in data.columns:
            data[column] = data[column].apply(
                lambda x: (
                    str(x)
                    if pd.isnull(x)
                    else f"{int(x.total_seconds() // 3600):02}:{int((x.total_seconds() % 3600) // 60):02}:{int(x.total_seconds() % 60):02}"
                )
            )

    # display the dataframe

    column_config = {}
    if config["dash_allow_path_link"]:
        column_config = {
            "path": st.column_config.LinkColumn(
                "path",
                help="open link to recording in new tab",
                max_chars=100,
                display_text=None,
            ),
        }

    event = st.dataframe(
        data,
        column_config=column_config,
        use_container_width=True,
        height=500,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # handle selection of a row
    selected_rows = event.selection.rows
    if len(selected_rows) > 0:
        recording_name = data.iloc[selected_rows[0]]["name"]
        dashboard_utils.select_recording(recording_name, db, config)


if __name__ == "__main__":
    main()
