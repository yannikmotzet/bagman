import argparse
import os

import click

from utils import bagman_utils
from utils import db_utils


def arg_parser():
    parser = argparse.ArgumentParser(description="bagman CLI")
    subparsers = parser.add_subparsers(dest="command")

    # upload command
    upload_parser = subparsers.add_parser("upload", help="upload a recording")
    upload_parser.add_argument("recording_path", help="path to the recording to upload")
    upload_parser.add_argument(
        "-m", "--move", action="store_true", help="move instead of copy the recording"
    )
    upload_parser.add_argument(
        "-i", "--ingest", action="store_true", help="ingest the recording"
    )

    # ingest command
    ingest_parser = subparsers.add_parser(
        "ingest", help="ingest a recording to database"
    )
    ingest_parser.add_argument("recording_name", help="name of the recording")

    # delete command
    delete_parser = subparsers.add_parser(
        "delete", help="delete a recording from database"
    )
    delete_parser.add_argument("recording_name", help="name of the recording")

    # exist command
    exist_parser = subparsers.add_parser(
        "exist", help="check if recording exist in storage and database"
    )
    exist_parser.add_argument("recording_name", help="name of the recording")
    return parser


def ingest_recording(db, recording_path):
    if not os.path.exists(recording_path):
        print("Recording does not exist in recordings storage. First upload recording.")
        exit(0)

    exists_recording = db.contains_record("name", args.recording_name)

    if exists_recording:
        if not click.confirm(
            "Recording already exists in database. Do you want to override it?",
            default=True,
        ):
            print("Operation cancelled.")
            exit(0)

    bagman_utils.db_ingest_recording(
        recording_path,
        db,
        override=True,
        store_metadata_file=True,
    )


if __name__ == "__main__":
    config = bagman_utils.load_config()
    args = arg_parser().parse_args()
    
    if not args.command:
        arg_parser().print_help()
        exit(0)

    db = db_utils.BagmanDB(config["database_path"])

    if args.command == "upload":
        recording_name = os.path.basename(os.path.normpath(args.recording_path))

        if os.path.exists(os.path.join(config["recordings_storage"], recording_name)):
            if not click.confirm(
                "Recording already exists in storage. Do you want to override it?", default=True
            ):
                print("Operation cancelled.")
                exit(0)

        bagman_utils.upload_recording(
            args.recording_path,
            config["recordings_storage"],
            move=args.move,
            verbose=True,
        )

        if args.ingest:
            recording_path = os.path.join(
                config["recordings_storage"], args.recording_name
            )
            ingest_recording(db, recording_path)

    elif args.command == "ingest":
        recording_path = os.path.join(config["recordings_storage"], args.recording_name)
        ingest_recording(db, recording_path)

    elif args.command == "delete":
        exists_recording = db.contains_record("name", args.recording_name)

        if not exists_recording:
            print("Recording does not exist in database.")
            # TODO check if available in storage
            exit(0)

        if not click.confirm(
            f"Are you sure you want to delete {args.recording_name} from the database?", default=False
        ):
            print("Operation cancelled.")
            exit(0)

        db.remove_record("name", args.recording_name)
        # TODO also delete from recordings storage?

    elif args.command == "exist":
        exists_recording_storage = os.path.exists(
            os.path.join(config["recordings_storage"], args.recording_name)
        )
        exists_recording = db.contains_record("name", args.recording_name)
        
        print(
            f"recording exists in storage: {'yes' if exists_recording_storage else 'no'}"
        )
        print(f"recording exists in database: {'yes' if exists_recording else 'no'}")
