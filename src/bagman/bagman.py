#!/usr/bin/env python3
import argparse
import os

import click

from bagman.utils import bagman_utils, db_utils


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

    # upload command (upload local recording to storage and optionally add to database)
    upload_parser = subparsers.add_parser(
        "upload", help="upload a recording to storage (optional: add to database)"
    )
    upload_parser.add_argument(
        "recording_path_local", help="path to the local recording to upload"
    )
    upload_parser.add_argument(
        "-m", "--move", action="store_true", help="move instead of copy the recording"
    )
    upload_parser.add_argument(
        "-a", "--add", action="store_true", help="add recording to database"
    )

    # add command (add a recording to database or update existing one)
    add_parser = subparsers.add_parser(
        "add", help="add a recording to database or update existing one"
    )
    add_parser.add_argument("recording_name", help="name of the recording")

    # delete command (delete recording from storage and optionally remove from database)
    delete_parser = subparsers.add_parser(
        "delete",
        help="delete a recording from storage (optional: remove from database)",
    )
    delete_parser.add_argument("recording_name", help="name of the recording")
    delete_parser.add_argument(
        "-r", "--remove", action="store_true", help="remove recording from database"
    )

    # remove command (remove recording from database)
    remove_parser = subparsers.add_parser(
        "remove", help="remove a recording from database"
    )
    remove_parser.add_argument("recording_name", help="name of the recording")

    # exist command
    exist_parser = subparsers.add_parser(
        "exist", help="check if recording exists in storage and database"
    )
    exist_parser.add_argument("recording_name", help="name of the recording")

    # metadata command (generate metadata for a recording and save it to file)
    metadata_parser = subparsers.add_parser(
        "metadata", help="generate metadata for a recording"
    )
    metadata_parser.add_argument(
        "recording_name",
        help="name of the recording (or local path) to generate metadata for",
    )
    metadata_parser.add_argument(
        "-p",
        "--path",
        action="store_true",
        help="use recording path instead of recording name from strorage",
    )

    return parser


def cli_add_recording(db, recording_path, metadata_file_name):
    if not os.path.exists(recording_path):
        print(
            "Recording does not exist in recordings storage. First upload recording before adding to database."
        )
        exit(0)

    exists_recording = db.contains_record("name", os.path.basename(recording_path))
    metadata_file = os.path.join(recording_path, metadata_file_name)
    exists_metadata_file = os.path.exists(metadata_file)

    if exists_recording:
        if not click.confirm(
            "Recording already exists in database. Do you want to override it?",
            default=True,
        ):
            print("Operation cancelled.")
            return

    use_existing_metadata = False
    if exists_metadata_file:
        use_existing_metadata = not click.confirm(
            "Metadata file already exists. Do you want to regenerate it?", default=True
        )

    bagman_utils.add_recording(
        db,
        recording_path,
        metadata_file_name=metadata_file_name,
        use_existing_metadata=use_existing_metadata,
        override_db=True,
        store_metadata_file=True,
    )


def cli_remove_recording(db, recording_name):
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
        exit(0)

    db.remove_record("name", recording_name)


def main():
    args = arg_parser().parse_args()

    if not args.command:
        arg_parser().print_help()
        exit(0)

    config_file = args.config
    if not os.path.exists(config_file):
        print(f"Config file {config_file} does not exist.")
        exit(0)

    config = bagman_utils.load_config(config_file)
    db = db_utils.BagmanDB(config["database_path"])

    if args.command == "upload":
        recording_name = os.path.basename(os.path.normpath(args.recording_path_local))

        if os.path.exists(os.path.join(config["recordings_storage"], recording_name)):
            if not click.confirm(
                "Recording already exists in storage. Do you want to override it?",
                default=True,
            ):
                print("Operation cancelled.")
                exit(0)

        try:
            bagman_utils.upload_recording(
                args.recording_path_local,
                config["recordings_storage"],
                move=args.move,
                verbose=True,
            )
        except Exception as e:
            print(f"Upload failed: {str(e)}")
            exit(0)

        if args.add:
            recording_path = os.path.join(config["recordings_storage"], recording_name)
            cli_add_recording(db, recording_path, config["metadata_file"])

    elif args.command == "add":
        recording_path = os.path.join(config["recordings_storage"], args.recording_name)
        cli_add_recording(db, recording_path, config["metadata_file"])

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
            cli_remove_recording(db, args.recording_name)

    elif args.command == "remove":
        cli_remove_recording(db, args.recording_name)

    elif args.command == "exist":
        recording_path = os.path.join(config["recordings_storage"], args.recording_name)
        exists_recording_storage = os.path.exists(recording_path)
        exists_recording = db.contains_record("name", args.recording_name)

        print(
            f"Recording exists in storage: {'yes' if exists_recording_storage else 'no'}"
        )
        print(f"Recording exists in database: {'yes' if exists_recording else 'no'}")

    elif args.command == "metadata":
        if args.path:
            recording_path = args.recording_name
        else:
            recording_path = os.path.join(
                config["recordings_storage"], args.recording_name
            )

        if not os.path.exists(recording_path):
            print("Recording not found")
            exit(0)

        # generate metadata (merge with existing and store to file)
        print("Generating metadata...")
        _ = bagman_utils.generate_metadata(
            recording_path,
            metadata_file_name=config["metadata_file"],
            merge_existing=True,
            store_file=True,
        )


if __name__ == "__main__":
    main()
