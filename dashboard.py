import os
import sqlite3

import numpy as np
import pandas as pd
import streamlit as st
import tinydb

from utils import bagman_utils
import subprocess

def get_git_version():
    try:
        version = subprocess.check_output(["git", "describe", "--tags", "--always"], stderr=subprocess.DEVNULL)
        return version.decode("utf-8").strip()
    except subprocess.CalledProcessError:
        return ""


@st.cache_data
def load_df_sqlite3(database, table):
    conn = sqlite3.connect(database)
    cursor = conn.execute(f"PRAGMA table_info('{table}')")
    columns = [info[1] for info in cursor.fetchall()]
    query = f"SELECT * FROM '{table}'"
    data = pd.read_sql_query(query, conn)
    if "timestamp" in columns:
        data["timestamp"] = pd.to_datetime(data["timestamp"], unit="s", errors="coerce")
    conn.close()
    return data


@st.cache_data
def load_df_tinydb(database):
    db = tinydb.TinyDB(database)
    records = db.all()
    df = pd.DataFrame(records)
    df = df.drop(columns=config["dash_cols_ignore"], errors="ignore")
    for col in ["start_time", "end_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], unit="s", errors="coerce")
    if "duration" in df.columns:
        df["duration"] = pd.to_timedelta(df["duration"], unit="s", errors="coerce")

    return df


def select_recording(selected_recording):
    db = tinydb.TinyDB(config["database_path"])
    query = tinydb.Query()
    result = db.search(query.name == selected_recording)

    if result and "files" in result[0]:
        tab_map, tab_video, tab_topics, tab_files, tab_download = st.tabs(
            ["Map", "Video", "Topics", "Files", "Download"]
        )

        with tab_map:
            if "coordinates" in result[0]:
                df = pd.DataFrame(result[0]["coordinates"], columns=["lat", "lon"])
                st.map(df)
            else:
                st.info("No coordinates available")

        with tab_video:
            st.write("Video not implemented yet")

        with tab_topics:
            if "topics" in result[0]:
                topics_df = pd.DataFrame(result[0]["topics"])
                st.dataframe(
                    topics_df, hide_index=True, use_container_width=True, height=600
                )

        with tab_files:
            if "files" in result[0]:
                files_df = pd.DataFrame(result[0]["files"])
                st.dataframe(
                    files_df, hide_index=True, use_container_width=True, height=250
                )

        with tab_download:
            st.download_button(
                "Download",
                f"/home/yamo/recordings/{result[0]['path']}",
                f"{result[0]['name']}.mcap",
                key="download",
            )


def filter_recording(data, container):
    # for each column create a filter for the specific data type
    for column in data.columns.tolist():
        if column in config["dash_cols_no_filter"]:
            continue
        if data.empty:
            continue

        # datetime column
        if np.issubdtype(data[column].dtype, np.datetime64):
            min_date = data[column].min().date()
            max_date = data[column].max().date()

            filter_date = container.date_input(
                f"Filter {column}",
                (min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                format="YYYY-MM-DD",
                key=f"{column}",
            )
            if len(filter_date) == 2:
                data = data[
                    (data[column].dt.date >= filter_date[0])
                    & (data[column].dt.date <= filter_date[1])
                ]
            continue

        # timedelta
        if np.issubdtype(data[column].dtype, np.timedelta64):
            min_duration = int(np.floor(data[column].min() / np.timedelta64(1, "m")))
            max_duration = int(np.ceil(data[column].max() / np.timedelta64(1, "m")))

            filter_duration = container.slider(
                f"Filter {column} [min]",
                min_duration,
                max_duration,
                (min_duration, max_duration),
                key=f"{column}",
            )
            if len(filter_duration) == 2:
                data = data[
                    (data[column] >= np.timedelta64(filter_duration[0], "m"))
                    & (data[column] <= np.timedelta64(filter_duration[1], "m"))
                ]
            continue

        # categorial data
        unique_values = data[column].unique().tolist()
        if len(unique_values) <= config["dash_max_categories"]:
            # TODO sort values
            filter_categories = container.segmented_control(
                f"Filter {column}",
                options=unique_values,
                default=unique_values,
                selection_mode="multi",
                key=f"{column}",
            )
            if filter_categories:
                data = data[data[column].isin(filter_categories)]
            else:
                data = data.iloc[0:0]  # return empty DataFrame
            continue

        # numerical data
        if np.issubdtype(data[column].dtype, np.number):
            min_val = data[column].min()
            max_val = data[column].max()
            filter_data = container.slider(
                f"Filter {column}",
                min_val,
                max_val,
                (min_val, max_val),
                key=f"{column}",
            )
            data = data[
                (data[column] >= filter_data[0]) & (data[column] <= filter_data[1])
            ]
            continue

    return data


def st_page_recordings():
    st.header("Recordings")
    if not os.path.exists(config["database_path"]):
        st.error("Database not found")
        return
    try:
        data = load_df_tinydb(config["database_path"])
    except Exception as e:
        st.error(f"Error loading database: {e}")
        return
    num_total_data = len(data)
    columns = data.columns.tolist()

    st_sidebar = st.sidebar

    col1, col2 = st_sidebar.columns(2)
    with col1:
        st_metric_all_results = st.metric(
            "number all results", num_total_data, border=False
        )
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

    # Add a checkbox to turn on/off the filters
    enable_filters = st_sidebar.toggle("Enable Filters", value=False)
    if enable_filters:
        data = filter_recording(data, st_sidebar)

    if num_total_data != len(data):
        st_metric_number_results.metric("number filtered results", len(data))

    # fix the issue of timedelta64[ns] not being displayed correctly (https://discuss.streamlit.io/t/streamlit-treats-timedelta-column-as-strings/84487)
    for column in config["dash_cols_timedelta"]:
        if column in data.columns:
            data[column] = data[column].apply(
                lambda x: str(x)
                if pd.isnull(x)
                else f"{int(x.total_seconds() // 3600):02}:{int((x.total_seconds() % 3600) // 60):02}:{int(x.total_seconds() % 60):02}"
            )

    # display the dataframe
    event = st.dataframe(
        data,
        column_config={
            "path": st.column_config.LinkColumn(
                "path",
                help="open recording in file manager",
                max_chars=100,
                display_text=None,
            ),
        },
        use_container_width=True,
        height=600,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    selected_rows = event.selection.rows
    if len(selected_rows) > 0:
        select_recording(data.iloc[selected_rows[0]]["name"])


def st_page_jobs():
    st.header("Jobs")
    st.write("Jobs are not implemented yet")


def st_page_upload():
    st.header("Uploads")
    # TODO change max file size
    st.file_uploader(
        "Upload recording", type=["mcap", "json", "yaml"], accept_multiple_files=True
    )


def main():
    global config
    try:
        config = bagman_utils.load_config()
    except Exception as e:
        st.error(f"Error loading config: {e}")
        return

    pg = st.navigation(
        [
            st.Page(st_page_recordings, title="Recordings", url_path="recordings"),
            st.Page(st_page_jobs, title="Jobs", url_path="jobs"),
            st.Page(st_page_upload, title="Upload", url_path="upload"),
        ]
    )

    st.set_page_config(
        page_title="bagman",
        page_icon="🛍️",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "About": (
                f"### bagman\n"
                f"version: {get_git_version()}  \n"
                f"check out bagman on [Git Hub](https://github.com/yannikmotzet/bagman)")
        }
    )
    st.title("🛍️ bagman")
    pg.run()


if __name__ == "__main__":
    main()
