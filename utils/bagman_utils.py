from utils import mcap_utils
import yaml
import os
from tinydb import TinyDB, Query

def load_config(file_path="config.yaml"):
    with open(file_path, "r") as file:
        return yaml.safe_load(file)

def load_rec_metadata(recording_path, file_name="rec_metadata.yaml"):
    try:
        with open(os.path.join(recording_path, file_name), 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        print(f"Error: The file {file_name} was not found in the directory {recording_path}.")
        return None
    except yaml.YAMLError as exc:
        print(f"Error parsing YAML file {file_name}: {exc}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def ingest_recording(recording_path, database, override=False, store_file=True):
    rec_info = mcap_utils.get_rec_info(recording_path)
    rec_metadata = load_rec_metadata(recording_path)

    if rec_metadata:
        rec_info.update(rec_metadata)

    if store_file:
        # TODO backup old file
        try:
            with open(os.path.join(recording_path, "rec_metadata.yaml"), 'w') as file:
                yaml.dump(rec_info, file)
        except Exception as e:
            pass

    db = TinyDB(database)
    Recordings = Query()

    if override:
        db.upsert(rec_info, Recordings.path == recording_path)
    else:
        if not db.contains(Recordings.path == recording_path):
            db.insert(rec_info)