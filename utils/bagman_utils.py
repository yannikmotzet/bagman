import os
import shutil

import yaml
from tqdm import tqdm

from utils import db_utils, mcap_utils


def load_config(file_path="config.yaml"):
    """
    Load configuration from a YAML file.
    Args:
        file_path (str): The path to the YAML configuration file. Defaults to "config.yaml".
    Returns:
        dict: The configuration data loaded from the YAML file.
    Raises:
        FileNotFoundError: If the specified file does not exist.
        yaml.YAMLError: If there is an error parsing the YAML file.
    """

    with open(file_path, "r") as file:
        return yaml.safe_load(file)


def upload_recording(path, recordings_path, move=False, verbose=True):
    """
    Upload a recording to the specified recordings directory.

        move (bool, optional): If True, the recording file will be moved to the recordings directory.
                               If False, the recording file will be copied. Default is False.
        verbose (bool, optional): If True, prints the upload progress. Default is True.

    Raises:
        FileNotFoundError: If the recordings directory does not exist.
        FileNotFoundError: If the recording file does not exist.
    """

    if not os.path.exists(recordings_path):
        raise FileNotFoundError(f"The directory {recordings_path} does not exist.")
    if not os.path.exists(path):
        raise FileNotFoundError(f"The file {path} does not exist.")

    if verbose:
        print(f"Uploading {path} to {recordings_path}...")
        # TODO add progress bar
    shutil.copy(path, recordings_path)
    if move:
        # TODO check if upload was successful
        os.remove(path)


def load_metadata_file(recording_path, file_name="rec_metadata.yaml"):
    """
    Load recording metadata from a YAML file.
    Args:
        recording_path (str): The directory path where the recording metadata file is located.
        file_name (str, optional): The name of the metadata file. Defaults to "rec_metadata.yaml".
    Returns:
        dict or None: The parsed metadata as a dictionary if successful, None otherwise.
    Raises:
        FileNotFoundError: If the specified file is not found.
        yaml.YAMLError: If there is an error parsing the YAML file.
        Exception: For any other unexpected errors.
    """

    try:
        with open(os.path.join(recording_path, file_name), "r") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        print(
            f"Error: The file {file_name} was not found in the directory {recording_path}."
        )
        return None
    except yaml.YAMLError as exc:
        print(f"Error parsing YAML file {file_name}: {exc}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None
    
def check_db_integrity(database, columns):
    # TODO
    pass


def add_recording(
    database,
    recording_path,
    metadata_file_name="rec_metadata.yaml",
    override=False,
    sort_by="start_time",
    store_metadata_file=True,
):
    """
    Adds a recording into the specified database and optionally stores the recording metadata file.
    Args:
        recording_path (str): The path to the recording file.
        database (BagmanDB): An instance of the BagmanDB class.
        override (bool, optional): If True, existing records with the same path will be updated. Defaults to False.
        sort_by (str, optional): The field by which to sort the database records. Defaults to "start_time".
        store_metadata_file (bool, optional): If True, the recording metadata will be stored in a YAML file at the recording path. Defaults to True.
    Raises:
        Exception: If there is an error writing the metadata file.
    Returns:
        None
    """

    rec_info = mcap_utils.get_rec_info(recording_path)

    # update existing metadata file
    rec_metadata = load_metadata_file(recording_path, metadata_file_name)
    if rec_metadata:
        rec_info.update(rec_metadata)

    if store_metadata_file:
        # TODO backup old file
        try:
            with open(os.path.join(recording_path, metadata_file_name), "w") as file:
                yaml.dump(rec_info, file)
        except Exception as e:
            pass

    if override:
        database.upsert_record(rec_info, "path", recording_path)
    else:
        if database.contains_record("path", recording_path):
            return
        database.insert_record(rec_info)

    # Sort the database (default sort by start_time, oldest on top)
    all_records = database.get_all_records()
    sorted_records = sorted(
        all_records, key=lambda x: x.get(sort_by, ""), reverse=False
    )
    database.truncate_database()  # Clear the database
    database.insert_multiple_records(sorted_records)  # Insert sorted records
