import glob
import io
import os
import subprocess
import sys
import time
import zipfile
from datetime import timedelta

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yaml

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yaml")

sys.path.append(PROJECT_ROOT)

from utils import bagman_utils, db_utils


def get_git_version():
    try:
        version = subprocess.check_output(
            ["git", "describe", "--tags", "--always"], stderr=subprocess.DEVNULL
        )
        return version.decode("utf-8").strip()
    except subprocess.CalledProcessError:
        return ""


@st.cache_data
def load_data(_database, check_integrity=True):
    data = _database.get_all_records()
    df = pd.DataFrame(data, index=None)
    columns = df.columns.tolist()

    if check_integrity:
        # check database for integrity
        if not set(config["db_columns"]).issubset(set(columns)):
            st.error("database is corrupt")
            missing_columns = set(config["db_columns"]) - set(columns)
            st.markdown("**Following columns are missing in the database:**")
            st.markdown(", ".join(f"`{col}`" for col in missing_columns))

    df = df.drop(columns=config["dash_cols_ignore"], errors="ignore")
    # df = df.iloc[::-1] # data is already sorted, oldest on top
    df = df.sort_values(by="start_time", ascending=False)
    for col in ["start_time", "end_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], unit="s", errors="coerce")
    if "duration" in df.columns:
        df["duration"] = pd.to_timedelta(df["duration"], unit="s", errors="coerce")

    return df


def select_recording(selected_recording, database):
    result = database.get_record("name", str(selected_recording))

    if result and "files" in result:
        tab_map, tab_video, tab_topics, tab_files, tab_download = st.tabs(
            ["Map", "Video", "Topics", "Files", "Download"]
        )

        with tab_map:
            html_file = os.path.join(
                result["path"],
                config["resources_folder"],
                f"{selected_recording}_map.html",
            )
            if os.path.exists(html_file):
                html_content = open(html_file, "r").read()
                components.html(html_content, height=600)
            else:
                st.info("map not available")

        with tab_video:
            video_files = glob.glob(
                os.path.join(result["path"], config["resources_folder"], "*.mp4"),
                recursive=False,
            )
            if video_files:
                for video_file in video_files:
                    st.text(os.path.basename(video_file))
                    st.video(video_file)

        with tab_topics:
            if "topics" in result:
                topics_df = pd.DataFrame(result["topics"])
                st.dataframe(
                    topics_df, hide_index=True, use_container_width=True, height=600
                )

        with tab_files:
            if "files" in result:
                files_df = pd.DataFrame(result["files"])
                st.dataframe(
                    files_df, hide_index=True, use_container_width=True, height=250
                )

        with tab_download:
            if not os.path.exists(result["path"]):
                st.error("recording not found in storage")
                return

            # TODO add option to select by topic/message -> filter and create new .mcap

            files = glob.glob(os.path.join(result["path"], "**", "*"), recursive=True)
            selected_files = []
            for file in files:
                if st.checkbox(
                    os.path.relpath(file, result["path"]), key=file, value=True
                ):
                    selected_files.append(file)

            if selected_files:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zipf:
                    for file in selected_files:
                        zipf.write(file, os.path.relpath(file, result["path"]))

                zip_buffer.seek(0)
                st.download_button(
                    label="Download selected files as ZIP",
                    data=zip_buffer,
                    file_name=f"{result['name']}_selected.zip",
                    mime="application/zip",
                )
            else:
                st.info("No files selected for download")


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
            min_duration = pd.to_datetime(
                data[column].min().total_seconds(), unit="s"
            ).time()
            max_duration = pd.to_datetime(
                data[column].max().total_seconds(), unit="s"
            ).time()

            min_duration_td = pd.to_timedelta(min_duration.strftime("%H:%M:%S"))
            max_duration_td = pd.to_timedelta(max_duration.strftime("%H:%M:%S"))
            duration_span = (max_duration_td - min_duration_td).total_seconds()
            step = timedelta(seconds=15)
            if duration_span > 3600:  # more than 1 hour
                step = timedelta(minutes=1)
            elif duration_span > 21600:  # more than 6 hours
                step = timedelta(minutes=10)
            elif duration_span > 86400:  # more than 1 day
                step = timedelta(hours=1)

            filter_duration = container.slider(
                label=f"Filter {column}",
                min_value=min_duration,
                max_value=max_duration,
                value=(min_duration, max_duration),
                key=f"{column}",
                step=step,
                format="HH:mm:ss",
            )
            if len(filter_duration) == 2:
                data = data[
                    (
                        data[column]
                        >= pd.to_timedelta(filter_duration[0].strftime("%H:%M:%S"))
                    )
                    & (
                        data[column]
                        <= pd.to_timedelta(filter_duration[1].strftime("%H:%M:%S"))
                    )
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

    try:
        database_path = config["database_path"]
        if not os.path.isabs(database_path):
            database_path = os.path.join(PROJECT_ROOT, database_path)
        db = db_utils.BagmanDB(database_path)
        data = load_data(db)
    except FileNotFoundError:
        st.error("Database not found")
        return
    except Exception as e:
        st.error(f"Error reading database: {e}")
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
    # TODO fix path link
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
        recording_name = data.iloc[selected_rows[0]]["name"]
        select_recording(recording_name, db)


def st_page_jobs():
    st.header("Jobs")
    st.write(
        "This section is not yet implemented. In future you can select pipelines and apply them to your recordings."
    )


def st_page_upload():
    st.header("Upload")
    uploaded_recording = st.file_uploader(
        "Upload a recording",
        type=config["dash_upload_files"],
        accept_multiple_files=True,
    )
    if uploaded_recording is None or len(uploaded_recording) == 0:
        return

    # TODO add a cancel button which resets uploaded_recording

    mcap_files = []
    other_files = []
    metadata_file = None

    # filter files for .mcap and metadata files
    for file in uploaded_recording:
        if file.name.lower().endswith(".mcap"):
            mcap_files.append(file)
        elif file.name == config["metadata_file"]:
            metadata_file = file
        else:
            other_files.append(file)
    if len(mcap_files) == 0:
        st.warning("recording must contain .mcap files")
        return

    recording_name = os.path.splitext(mcap_files[0].name)[0].rsplit("_", 1)[0]
    recording_path = os.path.join(config["recordings_storage"], recording_name)
    for file in mcap_files:
        if os.path.splitext(file.name)[0].rsplit("_", 1)[0] != recording_name:
            st.error("all .mcap files must belong to the same recording")
            return

    if metadata_file:
        metadata = yaml.safe_load(metadata_file.getvalue())
    else:
        metadata = {key: "" for key in config["metadata_recorder"]}
        metadata["name"] = recording_name

    # show metadata and make editable
    if "metadata" not in st.session_state:
        st.session_state.metadata = metadata.copy()

    with st.expander("Edit Metadata"):
        for key in config["metadata_recorder"]:
            value = st.session_state.metadata[key]
            if isinstance(value, str):
                st.session_state.metadata[key] = st.text_input(f"{key}:", value)
            elif isinstance(value, (int, float)):
                st.session_state.metadata[key] = st.number_input(f"{key}:", value=value)
            elif isinstance(value, bool):
                st.session_state.metadata[key] = st.checkbox(f"{key}:", value=value)

    # check if recording already exists
    button_label = "Upload"
    if os.path.exists(recording_path):
        st.warning("⚠️ recording already exists in storage")
        button_label = "Overwrite"

    db = db_utils.BagmanDB(config["database_path"])
    db_exists_recording = db.contains_record("name", recording_name)
    del db
    if db_exists_recording:
        st.warning("⚠️ recording already exists in database")
        button_label = "Overwrite"

    if st.button(button_label):
        # TODO disable button and metadata expander
        with st.spinner("uploading ..."):
            os.makedirs(recording_path, exist_ok=True)
            total_files = len(mcap_files) + len(other_files)
            progress_bar = st.progress(0)
            for i, file in enumerate(mcap_files + other_files):
                with open(os.path.join(recording_path, file.name), "wb") as f:
                    f.write(file.getvalue())
                progress_bar.progress((i + 1) / total_files)

            # write updated metadata file (bagman_utils.add_recording will add/update rec info)
            with open(os.path.join(recording_path, config["metadata_file"]), "w") as f:
                yaml.dump(st.session_state.metadata, f)

            # check if all files were uploaded correctly
            for file in mcap_files + other_files:
                uploaded_file_size = len(file.getvalue())
                stored_file_size = os.path.getsize(
                    os.path.join(recording_path, file.name)
                )
                if uploaded_file_size != stored_file_size:
                    st.error(f"File size mismatch for {file.name}")
                    return

            st.toast("upload successful!", icon="✅")
            st.success("✅ upload successful")

        # trigger add to database
        db = db_utils.BagmanDB(config["database_path"])
        bagman_utils.add_recording(db, recording_path, override=True)
        del db


def main():
    global config
    try:
        config = bagman_utils.load_config(CONFIG_PATH)
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
                f"check out bagman on [Git Hub](https://github.com/yannikmotzet/bagman)"
            )
        },
    )
    st.title("🛍️ bagman")
    st.logo("resources/bagman_logo.png", size="large")
    pg.run()


if __name__ == "__main__":
    main()
