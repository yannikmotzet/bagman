import glob
import hashlib
import os
import time
from collections import defaultdict
from typing import Any, Dict

import cv2
import numpy as np
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory


def get_mcap_info(file: str) -> Dict[str, Any]:
    """
    Extracts and returns information about the channels in an MCAP file.

    Args:
        file (str): The path to the MCAP file.

    Returns:
        dict: A dictionary where the keys are channel topics and the values are dictionaries containing:
            - num_messages (int): The number of messages in the channel.
            - message_type (str): The type of messages in the channel.
            - start_time (float): The timestamp of the first message in the channel (in seconds).
            - end_time (float): The timestamp of the last message in the channel (in seconds).
            - frequency (float): The frequency of messages in the channel (messages per second).
    """
    with open(file, "rb") as f:
        reader = make_reader(f)

        channel_info: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "num_messages": 0,
                "message_type": None,
                "start_time": None,
                "end_time": None,
                "frequency": None,
            }
        )

        for schema, channel, message in reader.iter_messages():
            info = channel_info[channel.topic]
            info["num_messages"] += 1
            info["message_type"] = schema.name
            timestamp = message.log_time / 1e9 if message.log_time is not None else 0
            if info["start_time"] is None or timestamp < info["start_time"]:
                info["start_time"] = timestamp
            if info["end_time"] is None or timestamp > info["end_time"]:
                info["end_time"] = timestamp

        for info in channel_info.values():
            duration = (info["end_time"] or 0) - (info["start_time"] or 0)
            info["frequency"] = (
                info["num_messages"] / duration if duration > 0 else None
            )

    return channel_info


def get_rec_info(recording_path: str, recursive: bool = False) -> Dict[str, Any]:
    """
    Collects and merges information from all .mcap files in the specified directory path.

    Args:
        recording_path (str): The recording directory path to search for .mcap files.

    Returns:
        Dict[str, Any]: A dictionary containing merged information about the recordings, including:
            - start_time (float): The earliest start time among all files.
            - end_time (float): The latest end time among all files.
            - duration (float): The total duration from start_time to end_time.
            - size (int): The total size of all .mcap files.
            - path (str): The path to the recording directory.
            - size (int): The total size of all .mcap files.
            - time_modified (float): The time the recording info was last generated.
            - files (Dict[str, Dict[str, Any]]): Information about each file, including:
                - start_time (float): The start time of the file.
                - end_time (float): The end time of the file.
                - duration (float): The duration of the file.
                - md5sum (str): The MD5 checksum of the file.
                - size (int): The size of the file.
            - topics (List[Dict[str, Any]]): Information about each topic, including:
                - name (str): The name of the topic.
                - type (str): The type of messages in the topic.
                - count (int): The number of messages in the topic.
                - start_time (float): The earliest start time of the topic.
                - end_time (float): The latest end time of the topic.
                - frequency (float): The frequency of messages in the topic.
                - duration (float): The duration of the topic.
    """
    mcap_files = sorted(
        glob.glob(os.path.join(recording_path, "*.mcap"), recursive=recursive)
    )

    if len(mcap_files) == 0:
        return {}

    merged_info: Dict[str, Any] = {
        "name": os.path.basename(recording_path),
        "start_time": None,
        "end_time": None,
        "duration": None,
        "path": recording_path,
        "size": 0,
        "time_modified": time.time(),
        "files": {},
        "topics": {},
    }

    for file_path in mcap_files:
        mcap_info = get_mcap_info(file_path)

        # calculate file md5sum and size
        with open(file_path, "rb") as f:
            md5sum = hashlib.md5(f.read()).hexdigest()
        size = os.path.getsize(file_path)  # size in bytes

        # add file info
        file_start_time = min(info["start_time"] for info in mcap_info.values())
        file_end_time = max(info["end_time"] for info in mcap_info.values())
        file_duration = file_end_time - file_start_time
        relative_file_path = os.path.relpath(file_path, recording_path)
        merged_info["files"][relative_file_path] = {
            "path": relative_file_path,
            "start_time": file_start_time,
            "end_time": file_end_time,
            "duration": file_duration,
            "md5sum": md5sum,
            "size": size,
        }

        # update overall start and end times
        if (
            merged_info["start_time"] is None
            or file_start_time < merged_info["start_time"]
        ):
            merged_info["start_time"] = file_start_time
        if merged_info["end_time"] is None or file_end_time > merged_info["end_time"]:
            merged_info["end_time"] = file_end_time

        # merge topic info
        for topic, info in mcap_info.items():
            if topic not in merged_info["topics"]:
                merged_info["topics"][topic] = {
                    "name": topic,
                    "type": info["message_type"],
                    "start_time": None,
                    "end_time": None,
                    "duration": None,
                    "count": 0,
                    "frequency": None,
                }
            merged_topic_info = merged_info["topics"][topic]
            merged_topic_info["count"] += info["num_messages"]
            if (
                merged_topic_info["start_time"] is None
                or info["start_time"] < merged_topic_info["start_time"]
            ):
                merged_topic_info["start_time"] = info["start_time"]
            if (
                merged_topic_info["end_time"] is None
                or info["end_time"] > merged_topic_info["end_time"]
            ):
                merged_topic_info["end_time"] = info["end_time"]
            merged_topic_info["duration"] = (
                merged_topic_info["end_time"] - merged_topic_info["start_time"]
            )
            total_duration = (
                merged_topic_info["end_time"] - merged_topic_info["start_time"]
            )
            merged_topic_info["frequency"] = (
                merged_topic_info["count"] / total_duration if total_duration > 0 else 0
            )

    # calculate overall duration
    if merged_info["start_time"] is not None and merged_info["end_time"] is not None:
        merged_info["duration"] = merged_info["end_time"] - merged_info["start_time"]
        merged_info["size"] = sum(
            file_info["size"] for file_info in merged_info["files"].values()
        )

    # convert topics and files to lists
    merged_info["topics"] = list(merged_info["topics"].values())
    merged_info["files"] = list(merged_info["files"].values())

    return merged_info


def read_msg_nav_sat_fix(files, topic, step=1):
    """
    Reads latitude, longitude, and altitude from a NavSatFix topic in one or more MCAP files.

    Args:
        files (Union[str, List[str]]): The path to the MCAP file or a list of paths to MCAP files.
        topic (str): The topic to read the NavSatFix messages from.
        step (int): The number of frames to skip between reads.

    Returns:
        List[Dict[str, float]]: A list of dictionaries containing 'latitude', 'longitude', and 'altitude'.
    """

    if isinstance(files, str):
        files = [files]

    nav_sat_data = []
    frame_count = 0

    for file in files:
        with open(file, "rb") as f:
            reader = make_reader(f, decoder_factories=[DecoderFactory()])

            for schema, channel, _, ros_msg in reader.iter_decoded_messages():
                if (
                    channel.topic == topic
                    and schema.name == "sensor_msgs/msg/NavSatFix"
                ):
                    if frame_count % step == 0:
                        nav_sat_data.append(
                            {
                                "stamp": ros_msg.header.stamp.sec
                                + ros_msg.header.stamp.nanosec * 1e-9,
                                "latitude": ros_msg.latitude,
                                "longitude": ros_msg.longitude,
                                "altitude": ros_msg.altitude,
                            }
                        )
                    frame_count += 1

    return nav_sat_data


def read_msg_image(files, topic):
    """
    Reads image data from a Camera topic in one or more MCAP files.

    Args:
        files (Union[str, List[str]]): The path to the MCAP file or a list of paths to MCAP files.
        topic (str): The topic to read the Camera messages from.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing 'stamp', 'data'.
    """

    if isinstance(files, str):
        files = [files]

    camera_data = []

    for file in files:
        with open(file, "rb") as f:
            reader = make_reader(f, decoder_factories=[DecoderFactory()])

            for schema, channel, message, ros_msg in reader.iter_decoded_messages():
                if channel.topic == topic:
                    if schema.name == "sensor_msgs/msg/Image":
                        image_np = np.frombuffer(ros_msg.data, dtype=np.uint8).reshape(
                            (ros_msg.height, ros_msg.width, -1)
                        )
                    elif schema.name == "sensor_msgs/msg/CompressedImage":
                        np_arr = np.frombuffer(ros_msg.data, dtype=np.uint8)
                        # decode JPEG
                        image_np = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                    camera_data.append(
                        {
                            "stamp": ros_msg.header.stamp.sec
                            + ros_msg.header.stamp.nanosec * 1e-9,
                            "data": image_np,
                        }
                    )

    return camera_data
