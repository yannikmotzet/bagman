#!/usr/bin/env python3
import argparse
import os
import sys

import click
from dotenv import load_dotenv

from bagman.utils import bagman_utils
from bagman.utils.db import BagmanDB


def arg_parser():
    parser = argparse.ArgumentParser(description="bagman CLI")
    subparsers = parser.add_subparsers(dest="command")

    # config command
    parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="path to config file, default: config.yaml in current directory",
    )

    # upload command
    upload_parser = subparsers.add_parser(
        "upload", help="upload local recording to storage (optional: add to database)"
    )
    upload_parser.add_argument(
        "recording_path_local", help="path to the local recording"
    )
    upload_parser.add_argument(
        "-m", "--move", action="store_true", help="move instead of copy the recording"
    )
    upload_parser.add_argument(
        "-a", "--add", action="store_true", help="add recording to database"
    )

    # add command
    add_parser = subparsers.add_parser(
        "add", help="add a recording to database or update existing one"
    )
    add_parser.add_argument("recording_name", help="name of the recording")

    # update command
    update_parser = subparsers.add_parser(
        "update", help="update an existing recording in database"
    )
    update_parser.add_argument("recording_name", help="name of the recording")

    # delete command
    delete_parser = subparsers.add_parser(
        "delete",
        help="delete a recording from storage (optional: remove from database)",
    )
    delete_parser.add_argument("recording_name", help="name of the recording")
    delete_parser.add_argument(
        "-r", "--remove", action="store_true", help="remove recording from database"
    )

    # remove command
    remove_parser = subparsers.add_parser(
        "remove", help="remove a recording from database"
    )
    remove_parser.add_argument("recording_name", help="name of the recording")

    # exist command
    exist_parser = subparsers.add_parser(
        "exist", help="check if recording exists in storage and database"
    )
    exist_parser.add_argument("recording_name", help="name of the recording")

    # connection command
    subparsers.add_parser(
        "connection", help="check connection to the storage and database"
    )

    # metadata command
    metadata_parser = subparsers.add_parser(
        "metadata", help="(re)generate metadata file for a local recording"
    )
    metadata_parser.add_argument(
        "recording_path_local", help="path to the local recording"
    )

    # map plot command
    map_parser = subparsers.add_parser(
        "map", help="generate a map plot of the recordings in storage"
    )
    map_parser.add_argument("recording_name", help="name of the recording")
    map_parser.add_argument(
        "-t",
        "--topic",
        default=None,
        help="specify a topic for the operation (optional)",
    )

    # video file command
    video_parser = subparsers.add_parser(
        "video", help="generate a video file from the recording"
    )
    video_parser.add_argument("recording_name", help="name of the recording")
    video_parser.add_argument(
        "-t",
        "--topic",
        default=None,
        help="specify a topic for the operation (optional)",
    )

    return parser


def add_or_update_recording(db, recording_path, metadata_file_name, sort_by, add=True):
    exists_recording = db.contains_record("name", os.path.basename(recording_path))

    if add:
        if not os.path.exists(recording_path):
            print(
                "Recording does not exist in recordings storage. First upload recording before adding to database."
            )
            sys.exit(0)

        if exists_recording:
            if not click.confirm(
                "Recording already exists in database. Do you want to override it?",
                default=True,
            ):
                print("Operation cancelled.")
                return
    else:
        if not exists_recording:
            print(
                "Recording does not exist in database. Use 'add' command to add it first."
            )
            sys.exit(0)

    metadata_file = os.path.join(recording_path, metadata_file_name)
    exists_metadata_file = os.path.exists(metadata_file)

    use_existing_metadata = False
    if exists_metadata_file:
        use_existing_metadata = not click.confirm(
            "Metadata file already exists. Do you want to regenerate the metadata instead of using it from the file?",
            default=True,
        )

    bagman_utils.add_recording(
        db,
        recording_path,
        metadata_file_name=metadata_file_name,
        use_existing_metadata=use_existing_metadata,
        override_db=True,
        sort_by=sort_by,
        store_metadata_file=True,
    )


def remove_recording(db, recording_name):
    exists_recording = db.contains_record("name", recording_name)

    if not exists_recording:
        print("Recording does not exist in database.")
        # TODO check if available in storage
        return

    if not click.confirm(
        f"Are you sure you want to delete {recording_name} from the database?",
        default=False,
    ):
        print("Operation cancelled.")
        sys.exit(0)

    db.remove_record("name", recording_name)


def main():
    args = arg_parser().parse_args()

    if not args.command:
        arg_parser().print_help()
        sys.exit(0)

    config_file = args.config
    if not os.path.exists(config_file):
        print(f"Config file {config_file} does not exist.")
        sys.exit(0)

    config = bagman_utils.load_config(config_file)

    load_dotenv()
    db_connected = False
    try:
        db = BagmanDB(
            config["database_type"], config["database_uri"], config["database_name"]
        )
        db_connected = True
    except Exception as e:
        print(f"Failed to connect to the database: {str(e)}")

    if args.command == "upload":
        recording_name = os.path.basename(os.path.normpath(args.recording_path_local))

        if os.path.exists(os.path.join(config["recordings_storage"], recording_name)):
            if not click.confirm(
                "Recording already exists in storage. Do you want to override it?",
                default=True,
            ):
                print("Operation cancelled.")
                sys.exit(0)

        try:
            bagman_utils.upload_recording(
                args.recording_path_local,
                config["recordings_storage"],
                move=args.move,
                verbose=True,
            )
        except Exception as e:
            print(f"Upload failed: {str(e)}")
            sys.exit(0)

        if args.add:
            recording_path = os.path.join(config["recordings_storage"], recording_name)
            add_or_update_recording(
                db,
                recording_path,
                config["metadata_file"],
                config["database_sort_by"],
                True,
            )

    elif args.command == "add":
        recording_path = os.path.join(config["recordings_storage"], args.recording_name)
        add_or_update_recording(
            db,
            recording_path,
            config["metadata_file"],
            config["database_sort_by"],
            True,
        )

    elif args.command == "update":
        recording_path = os.path.join(config["recordings_storage"], args.recording_name)
        add_or_update_recording(
            db,
            recording_path,
            config["metadata_file"],
            config["database_sort_by"],
            False,
        )

    elif args.command == "delete":
        recording_path = os.path.join(config["recordings_storage"], args.recording_name)
        if not os.path.exists(recording_path):
            print("Recording does not exist in storage")
        else:
            if click.confirm(
                f"Are you sure you want to delete {args.recording_name} from storage?",
                default=False,
            ):
                os.remove(recording_path)
                if os.path.exists(recording_path):
                    print(f"Failed to delete {args.recording_name} from storage.")
                else:
                    print(
                        f"{args.recording_name} has been successfully deleted from storage."
                    )
            else:
                print("Operation cancelled.")

        if args.remove:
            remove_recording(db, args.recording_name)

    elif args.command == "remove":
        remove_recording(db, args.recording_name)

    elif args.command == "exist":
        recording_path = os.path.join(config["recordings_storage"], args.recording_name)
        exists_recording_storage = os.path.exists(recording_path)
        exists_recording = db.contains_record("name", args.recording_name)

        print(
            f"Recording exists in storage: {'yes' if exists_recording_storage else 'no'}"
        )
        print(f"Recording exists in database: {'yes' if exists_recording else 'no'}")

    elif args.command == "connection":
        storage_connected = False
        database_connected = False

        # check storage connection
        if os.path.exists(config["recordings_storage"]):
            storage_connected = True

        # check database connection
        if db_connected:
            try:
                db.is_connected()
                database_connected = True
            except Exception:
                pass

        print(
            f"storage connection ({config['recordings_storage']}): {'yes' if storage_connected else 'no'}"
        )
        print(
            f"database connection ({config['database_uri']}): {'yes' if database_connected else 'no'}"
        )

    elif args.command == "metadata":
        if not os.path.exists(args.recording_path_local):
            print("Recording not found")
            sys.exit(0)

        # generate metadata (merge with existing and store to file)
        print("Generating metadata...")
        _ = bagman_utils.generate_metadata(
            args.recording_path_local,
            metadata_file_name=config["metadata_file"],
            merge_existing=True,
            store_file=True,
        )

    elif args.command == "map":
        print("Generating mcap plot ...")
        recording_path = os.path.join(config["recordings_storage"], args.recording_name)
        bagman_utils.generate_map(recording_path, config, args.topic)

    elif args.command == "video":
        print("Generating video file ...")
        recording_path = os.path.join(config["recordings_storage"], args.recording_name)
        bagman_utils.generate_video(recording_path, config, [args.topic])


if __name__ == "__main__":
    main()
