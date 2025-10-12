import glob
import io
import os
import zipfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


@st.cache_data
def load_recordings(_database, config, check_integrity=True):
    data = _database.get_all_records()
    df = pd.DataFrame(data, index=None)
    columns = df.columns.tolist()

    if check_integrity:
        # check database for integrity
        if not set(config["database_columns"]).issubset(set(columns)):
            missing_columns = set(config["database_columns"]) - set(columns)
            missing_columns_str = ", ".join(f"`{col}`" for col in missing_columns)
            with st.expander("⚠️ database is corrupt"):
                st.write(
                    f"Following columns are missing in the database: {missing_columns_str}"
                )

    df = df.drop(columns=config["dash_cols_ignore"], errors="ignore")
    # df = df.iloc[::-1] # data is already sorted, oldest on top
    df = df.sort_values(by="start_time", ascending=False)

    # convert datetime and datetime columns
    timezone = datetime.now().astimezone().tzinfo
    if "dash_timezone" in config:
        try:
            timezone = ZoneInfo(config["dash_timezone"])
        except Exception:
            st.warning(
                f"Invalid timezone in config: {config['dash_timezone']}. "
                f"Using system timezone instead: {timezone}."
            )

    for col in config["dash_cols_datetime"]:
        if col in df.columns:
            df[col] = (
                pd.to_datetime(df[col], unit="s", errors="coerce")
                .dt.tz_localize("UTC")
                .dt.tz_convert(timezone)
                .dt.tz_localize(None)
            )
    for col in config["dash_cols_timedelta"]:
        if col in df.columns:
            df[col] = pd.to_timedelta(df[col], unit="s", errors="coerce")

    return df


def select_recording(selected_recording, database, config):
    recording_data = database.get_record("name", str(selected_recording))
    if not recording_data:
        st.error("recording not found in database")
        return

    # TODO check if "files", "path", "topics" in result

    # TODO add button to open recording

    tab_map, tab_video, tab_topics, tab_files, tab_download = st.tabs(
        ["Map", "Video", "Topics", "Files", "Download"]
    )

    with tab_map:
        html_file = os.path.join(
            recording_data["path"],
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
            os.path.join(recording_data["path"], config["resources_folder"], "*.mp4"),
            recursive=False,
        )
        if video_files:
            for video_file in video_files:
                st.text(os.path.basename(video_file))
                st.video(video_file)
        else:
            st.info("video not available")

    with tab_topics:
        if "topics" in recording_data:
            topics_df = pd.DataFrame(recording_data["topics"])
            st.dataframe(
                topics_df, hide_index=True, use_container_width=True, height=600
            )

    with tab_files:
        if "files" in recording_data:
            files_df = pd.DataFrame(recording_data["files"])
            st.dataframe(
                files_df, hide_index=True, use_container_width=True, height=250
            )

    with tab_download:
        if not os.path.exists(recording_data["path"]):
            st.error("recording not found in storage")
            return

        # TODO add option to select by topic/message -> filter and create new .mcap

        files = glob.glob(
            os.path.join(recording_data["path"], "**", "*"), recursive=True
        )
        selected_files = []
        for file in files:
            if os.path.isdir(file):
                continue
            file_path = os.path.relpath(file, recording_data["path"])
            file_size = os.path.getsize(file) / (1024 * 1024)  # convert to MB
            if st.checkbox(f"{file_path} ({file_size:.2f} MB)", key=file, value=False):
                selected_files.append(file)

        if selected_files:
            with st.spinner("Creating .zip file ..."):
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zipf:
                    for file in selected_files:
                        zipf.write(file, os.path.relpath(file, recording_data["path"]))

                zip_buffer.seek(0)
                st.download_button(
                    label="Download selected files as .zip",
                    data=zip_buffer,
                    file_name=f"{recording_data['name']}.zip",
                    mime="application/zip",
                )
        else:
            st.info("please select files to download")


def filter_recording(data, container, config):
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
                np.ceil(data[column].max().total_seconds()), unit="s"
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
