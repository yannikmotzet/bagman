import os

from prefect import flow, task

from bagman.utils import bagman_utils, db_utils


@task
def add_recording(recording_name, config):
    recording_path = os.path.join(
        config["recordings_storage"],
        recording_name,
    )
    if not os.path.exists(recording_path):
        print(
            "Recording does not exist in recordings storage. "
            "First upload recording before adding to database."
        )
        exit(0)

    db = db_utils.BagmanDB(config["database_path"])
    exists_recording = db.contains_record("name", os.path.basename(recording_path))

    if exists_recording:
        print("Recording already exists in database. It will be overwritten.")

    bagman_utils.add_recording(
        db,
        recording_path,
        override=True,
        store_metadata_file=True,
    )


@task
def generate_map_plot(recording_name):
    bagman_utils.generate_map(recording_name)


@task
def generate_video_files(recording_name):
    bagman_utils.generate_video(recording_name)


@flow
def flow_default(recording_name: str, config_file: str):
    if not os.path.exists(config_file):
        print(f"Config file {config_file} does not exist.")
        exit(0)
    config = bagman_utils.load_config(config_file)

    result_add_recording = add_recording(recording_name, config)
    generate_map_plot(recording_name, wait_for=[result_add_recording])
    generate_video_files(recording_name, wait_for=[result_add_recording])


if __name__ == "__main__":
    flow_default()
