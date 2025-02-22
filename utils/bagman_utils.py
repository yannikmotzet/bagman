import os
import shutil
from math import atan2, cos, radians, sin, sqrt

import cv2
import yaml
from scipy.signal import medfilt
from tqdm import tqdm

from utils import db_utils, mcap_utils, plot_utils


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


def generate_map(recording_name, config="config.yaml", topic=None, speed=True):
    """
    Generates an HTML map from GPS data in a recording.
    Args:
        recording_name (str): The name of the recording directory.
        config (str, optional): Path to the configuration file. Defaults to "config.yaml".
        topic (str, optional): The specific topic to extract GPS data from. If None, the first topic of type
                               "sensor_msgs/msg/NavSatFix" will be used. Defaults to None.
        speed (bool, optional): If True, the speed of the vehicle will be calculated and displayed on the map. Defaults to True.
    Raises:
        FileNotFoundError: If the recording directory does not exist.
    Returns:
        None
    """

    def haversine(lat1, lon1, lat2, lon2):
        """
        Calculate the great-circle distance between two points on the Earth's surface.
        This function uses the Haversine formula to calculate the distance between two points
        specified by their latitude and longitude in decimal degrees.
        Parameters:
        lat1 (float): Latitude of the first point in decimal degrees.
        lon1 (float): Longitude of the first point in decimal degrees.
        lat2 (float): Latitude of the second point in decimal degrees.
        lon2 (float): Longitude of the second point in decimal degrees.
        Returns:
        float: Distance between the two points in kilometers.
        """
        R = 6371.0  # Earth radius in kilometers
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = (
            sin(dlat / 2) ** 2
            + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        )
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    config = load_config(config)

    recording_path = os.path.join(config["recordings_storage"], recording_name)
    if not os.path.exists(recording_path):
        raise FileNotFoundError(f"The directory {recording_path} does not exist.")

    try:
        metadata = load_metadata_file(recording_path, config["metadata_file"])
    except Exception as e:
        print(f"Error loading metadata file: {e}")
        return

    if topic is None:
        topics_nav_sat_fix = [
            t["name"]
            for t in metadata["topics"]
            if t["type"] == "sensor_msgs/msg/NavSatFix"
        ]
        topic = topics_nav_sat_fix[0]
    mcap_files = [os.path.join(recording_path, f["path"]) for f in metadata["files"]]

    gps_data = mcap_utils.read_msg_nav_sat_fix(mcap_files, topic)
    if len(gps_data) == 0:
        print("no NavSatFix messages found")
        return

    if speed:
        velocities = []
        for i in range(1, len(gps_data)):
            lat1, lon1 = gps_data[i - 1]["latitude"], gps_data[i - 1]["longitude"]
            lat2, lon2 = gps_data[i]["latitude"], gps_data[i]["longitude"]
            distance = haversine(lat1, lon1, lat2, lon2)  # km
            time_diff = (
                gps_data[i]["stamp"] - gps_data[i - 1]["stamp"]
            ) / 3600  # sec to h
            velocity = distance / time_diff if time_diff > 0 else 0
            velocities.append(velocity)

        # apply median filter to remove outliers caused by time jumps
        velocities = medfilt(velocities, kernel_size=9)

        gps_data = [
            {
                "latitude": data["latitude"],
                "longitude": data["longitude"],
                "speed": vel,
                "stamp": data["stamp"],
            }
            for data, vel in zip(gps_data, velocities)
        ]

    # generate and store html map
    html_path = os.path.join(
        recording_path, config["resources_folder"], f"{recording_name}_map.html"
    )
    os.makedirs(os.path.dirname(html_path), exist_ok=True)
    plot_utils.plot_map(gps_data, html_path)


def generate_video(
    recording_name,
    config="config.yaml",
    topics=None,
    types=["sensor_msgs/msg/Image", "sensor_msgs/msg/CompressedImage"],
):
    """
    Generates a video from image data in a recording.
    Args:
        recording_name (str): The name of the recording directory.
        config (str, optional): Path to the configuration file. Defaults to "config.yaml".
        topic (str, optional): The specific topic to extract image data from. If None, the first topic of type
                               "sensor_msgs/msg/Image" will be used. Defaults to None.
    Raises:
        FileNotFoundError: If the recording directory does not exist.
    Returns:
        None
    """

    config = load_config(config)

    recording_path = os.path.join(config["recordings_storage"], recording_name)
    if not os.path.exists(recording_path):
        raise FileNotFoundError(f"The directory {recording_path} does not exist.")

    try:
        metadata = load_metadata_file(recording_path, config["metadata_file"])
    except Exception as e:
        print(f"Error loading metadata file: {e}")
        return

    if topics is None:
        topics_image = [t["name"] for t in metadata["topics"] if t["type"] in types]

    # check that either Image or ImageCompressed topic is used
    topics = [t for t in topics_image if not t.endswith("/compressed")]
    topics += [
        t
        for t in topics_image
        if t.endswith("/compressed") and t.replace("/compressed", "") not in topics
    ]

    mcap_files = [os.path.join(recording_path, f["path"]) for f in metadata["files"]]

    for topic in topics:
        image_data = mcap_utils.read_msg_image(mcap_files, topic)

        if len(image_data) == 0:
            print("no image messages found")
            continue

        fps = (
            1 / ((image_data[-1]["stamp"] - image_data[0]["stamp"]) / len(image_data))
            if len(image_data) > 1
            else 30
        )

        file_name = f"{recording_name}{topic.replace('/', '_')}.mp4"
        video_path = os.path.join(recording_path, config["resources_folder"], file_name)
        os.makedirs(os.path.dirname(video_path), exist_ok=True)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(
            video_path,
            fourcc,
            fps,
            (image_data[0]["data"].shape[1], image_data[0]["data"].shape[0]),
        )

        for frame in image_data:
            out.write(frame["data"])

        out.release()

        # compress video to H.264 with ffmpeg since OpenCV does only support it in manually compiled version
        # https://github.com/opencv/opencv-python/issues/100#issuecomment-394159998
        compressed_video_path = video_path.replace(".mp4", "_compressed.mp4")
        command = f"ffmpeg -i {video_path} -vcodec libx264 {compressed_video_path}"
        os.system(f"{command} > /dev/null 2>&1")
        os.remove(video_path)
        os.rename(compressed_video_path, video_path)
