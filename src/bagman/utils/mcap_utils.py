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
from mcap_ros2.writer import Writer as McapWriter

from bagman.utils.schema_ros import schema_ros


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


def get_opencv_conversion_code(encoding: str):
    """Map ROS encoding to OpenCV conversion code (to BGR)."""
    encoding = encoding.lower()
    return {
        "rgb8": cv2.COLOR_RGB2BGR,
        "rgba8": cv2.COLOR_RGBA2BGR,
        "mono8": cv2.COLOR_GRAY2BGR,
        "mono16": None,  # No direct conversion; usually for depth
        "bayer_rggb8": cv2.COLOR_BAYER_RG2BGR,
        "bayer_bggr8": cv2.COLOR_BAYER_BG2BGR,
        "bayer_grbg8": cv2.COLOR_BAYER_GR2BGR,
        "bayer_gbrg8": cv2.COLOR_BAYER_GB2BGR,
        "yuv422": cv2.COLOR_YUV2BGR_YUY2,
        "yuv422_yuy2": cv2.COLOR_YUV2BGR_YUY2,
        "uyvy": cv2.COLOR_YUV2BGR_UYVY,
        "bgr8": None,  # Already in OpenCV format
        "bgra8": cv2.COLOR_BGRA2BGR,
    }.get(encoding, None)


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

            for schema, channel, message, ros_msg in reader.iter_decoded_messages(
                topics=[topic]
            ):
                image_np = None
                if schema.name == "sensor_msgs/msg/Image":
                    encoding = ros_msg.encoding.lower()
                    height = ros_msg.height
                    width = ros_msg.width

                    img_data = np.frombuffer(ros_msg.data, dtype=np.uint8)

                    # Handle mono8, bayer, RGB, BGR, etc.
                    if encoding in ["mono8", "mono16"]:
                        img_np = img_data.reshape((height, width))
                    elif encoding in ["bgr8", "rgb8", "rgba8", "bgra8"]:
                        img_np = img_data.reshape(
                            (
                                height,
                                width,
                                3 if "8" in encoding and "a" not in encoding else 4,
                            )
                        )
                    elif encoding.startswith("bayer_"):
                        img_np = img_data.reshape((height, width))
                    elif encoding in ["yuv422", "yuv422_yuy2", "uyvy"]:
                        img_np = img_data.reshape((height, width, 2))
                    else:
                        raise ValueError(f"Unsupported encoding: {encoding}")

                    conversion_code = get_opencv_conversion_code(encoding)
                    if conversion_code is not None:
                        image_np = cv2.cvtColor(img_np, conversion_code)
                    else:
                        image_np = img_np  # Already in BGR

                elif schema.name == "sensor_msgs/msg/CompressedImage":
                    img_data = np.frombuffer(ros_msg.data, dtype=np.uint8)
                    # decode JPEG
                    image_np = cv2.imdecode(img_data, cv2.IMREAD_COLOR)

                if image_np is not None:
                    camera_data.append(
                        {
                            "stamp": ros_msg.header.stamp.sec
                            + ros_msg.header.stamp.nanosec * 1e-9,
                            "data": image_np,
                        }
                    )

    return camera_data


def compress_image(
    file,
    output_file,
    topics=None,
    compressed_suffix="/compressed",
    remove_uncompressed=False,
):
    with open(output_file, "wb") as fo:
        writer = McapWriter(fo)

        with open(file, "rb") as fi:
            reader = make_reader(fi, decoder_factories=[DecoderFactory()])

            schema_compressed_image = writer.register_msgdef(
                "sensor_msgs/msg/CompressedImage",
                schema_ros["sensor_msgs/msg/CompressedImage"],
            )

            for schema, channel, message, ros_msg in reader.iter_decoded_messages():
                schema.id = next(
                    (
                        s.id
                        for k, s in writer._writer._Writer__schemas.items()
                        if s.name == schema.name
                    ),
                    None,
                )
                if schema.id is None:
                    schema.id = writer._writer.register_schema(
                        schema.name, schema.encoding, schema.data
                    )

                if schema.name == "sensor_msgs/msg/Image":
                    if topics is not None and channel.topic not in topics:
                        continue

                    image_np = None
                    encoding = ros_msg.encoding.lower()
                    height = ros_msg.height
                    width = ros_msg.width

                    img_data = np.frombuffer(ros_msg.data, dtype=np.uint8)

                    # handle mono8, bayer, RGB, BGR, etc.
                    if encoding in ["mono8", "mono16"]:
                        img_np = img_data.reshape((height, width))
                    elif encoding in ["bgr8", "rgb8", "rgba8", "bgra8"]:
                        img_np = img_data.reshape(
                            (
                                height,
                                width,
                                3 if "8" in encoding and "a" not in encoding else 4,
                            )
                        )
                    elif encoding.startswith("bayer_"):
                        img_np = img_data.reshape((height, width))
                    elif encoding in ["yuv422", "yuv422_yuy2", "uyvy"]:
                        img_np = img_data.reshape((height, width, 2))
                    else:
                        raise ValueError(f"Unsupported encoding: {encoding}")

                    conversion_code = get_opencv_conversion_code(encoding)
                    if conversion_code is not None:
                        image_np = cv2.cvtColor(img_np, conversion_code)
                    else:
                        image_np = img_np  # Already in BGR

                    # compress image
                    encode_param = [cv2.IMWRITE_JPEG_QUALITY, 90]
                    result, encoded_image = cv2.imencode(".jpg", image_np, encode_param)
                    if result:
                        ros_msg_encoded = {
                            "header": {
                                "stamp": {
                                    "sec": ros_msg.header.stamp.sec,
                                    "nanosec": ros_msg.header.stamp.nanosec,
                                },
                                "frame_id": ros_msg.header.frame_id,
                            },
                            "format": "jpeg",
                            "data": encoded_image.tobytes(),
                        }

                        topic_compressed = channel.topic + compressed_suffix

                        writer.write_message(
                            topic=topic_compressed,
                            schema=schema_compressed_image,
                            message=ros_msg_encoded,
                            log_time=message.log_time,
                            publish_time=message.publish_time,
                        )

                        if remove_uncompressed:
                            continue

                # write the original message as well
                writer.write_message(
                    topic=channel.topic,
                    schema=schema,
                    message=ros_msg,
                    log_time=message.log_time,
                    publish_time=message.publish_time,
                    sequence=message.sequence,
                )

            writer.finish()
