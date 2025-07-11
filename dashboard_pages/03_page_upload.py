import os

import streamlit as st
import yaml

from bagman.utils import bagman_utils
from bagman.utils.db import BagmanDB

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "..", "config.yaml")


def main():
    st.header("Upload")

    try:
        config = bagman_utils.load_config(CONFIG_PATH)
    except Exception as e:
        st.error(f"Error loading config: {e}")
        return

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

    metadata = {key: "" for key in config["metadata_recorder"]}
    if metadata_file:
        metadata_file = yaml.safe_load(metadata_file.getvalue())
        metadata.update(metadata_file)
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
            else:
                st.session_state.metadata[key] = st.text_input(f"{key}:", value=value)

    # check if recording already exists
    button_label = "Upload"

    storage_exists = os.path.exists(recording_path)
    db = BagmanDB(config["database_type"], config["database_uri"])
    db_exists = db.contains_record("name", recording_name)
    del db

    if storage_exists and db_exists:
        st.warning("⚠️ recording already exists in storage and database")
        button_label = "Overwrite"
    elif storage_exists:
        st.warning("⚠️ recording already exists in storage")
        button_label = "Overwrite"
    elif db_exists:
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

            # check if all files were uploaded correctly (TODO use checksum instead of file size)
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
        db = BagmanDB(config["database_type"], config["database_uri"])
        bagman_utils.add_recording(
            db,
            recording_path,
            metadata_file_name=config["metadata_file"],
            sort_by=config["database_sort_by"],
        )
        del db


if __name__ == "__main__":
    main()
