import argparse
import os
import sys

from prefect import flow, get_run_logger, task

from bagman.utils import bagman_utils
from bagman.utils.db import BagmanDB


@task
def add_recording(recording_name, config):
    logger = get_run_logger()
    recording_path = os.path.join(
        config["recordings_storage"],
        recording_name,
    )
    if not os.path.exists(recording_path):
        logger.error(
            "Recording does not exist in recordings storage. "
            "First upload recording before adding to database."
        )
        sys.exit(1)

    try:
        db = BagmanDB(
            config["database_type"], config["database_uri"], config["database_name"]
        )
    except Exception as e:
        logger.error(f"Failed to connect to the database: {e}")
        sys.exit(1)

    exists_recording = db.contains_record("name", os.path.basename(recording_path))

    if exists_recording:
        logger.warning("Recording already exists in database. It will be overwritten.")

    logger.info("Adding recording to database...")
    try:
        bagman_utils.add_recording(
            db,
            recording_path,
            metadata_file_name=config["metadata_file"],
            use_existing_metadata=False,
            override_db=True,
            sort_by=config["database_sort_by"],
            store_metadata_file=True,
        )
    except Exception as e:
        logger.error(f"Failed to add recording: {e}")
        sys.exit(1)

    logger.info("Recording added successfully.")


@task
def generate_map_plot(recording_name, config_file):
    logger = get_run_logger()
    logger.info(f"Generating map for {recording_name}...")
    config = bagman_utils.load_config(config_file)
    bagman_utils.generate_map(
        os.path.join(config["recordings_storage"], recording_name), config
    )
    logger.info("Map generation complete.")


@task
def generate_video_files(recording_name, config_file):
    logger = get_run_logger()
    logger.info(f"Generating video for {recording_name}...")
    config = bagman_utils.load_config(config_file)
    bagman_utils.generate_video(
        os.path.join(config["recordings_storage"], recording_name), config
    )
    logger.info("Video generation complete.")


@flow
def flow_default(recording_name: str, config_file: str):
    logger = get_run_logger()

    if not os.path.exists(config_file):
        logger.error(f"Config file {config_file} does not exist.")
        sys.exit(1)
    config = bagman_utils.load_config(config_file)

    logger.info("Starting flow tasks...")
    result_add_recording = add_recording(recording_name, config)
    generate_map_plot(recording_name, config_file, wait_for=[result_add_recording])
    generate_video_files(recording_name, config_file, wait_for=[result_add_recording])
    logger.info("Flow completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the default flow.")
    parser.add_argument("recording_name", type=str, help="Name of the recording.")
    parser.add_argument("config_file", type=str, help="Path to the configuration file.")
    args = parser.parse_args()

    flow_default(args.recording_name, args.config_file)
