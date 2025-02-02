from utils import bagman_utils
import argparse
import click
import os

def arg_parser():
    parser = argparse.ArgumentParser(description="bagman CLI")
    subparsers = parser.add_subparsers(dest="command")

    upload_parser = subparsers.add_parser("upload", help="Upload a recording")
    upload_parser.add_argument("recording_path", help="Path to the recording to upload")
    upload_parser.add_argument("-m", "--move", action="store_true", help="move instead of copy the recording")
    upload_parser.add_argument("-i", "--ingest", action="store_true", help="ingest the recording")

    ingest_parser = subparsers.add_parser("ingest", help="Ingest a recording to database")
    ingest_parser.add_argument("recording_name", help="Name of the recording")

    delete_parser = subparsers.add_parser("delete", help="Delete a recording from database")
    delete_parser.add_argument("recording_name", help="Name of the recording")

    delete_parser = subparsers.add_parser("exist", help="Check if recording exist in storage and database")
    delete_parser.add_argument("recording_name", help="Name of the recording")
    return parser

def ingest_recording(recording_path):
    if not os.path.exists():
        print("Recording does not exist in recordings storage.")
        exit(0)

    exists_recording = bagman_utils.db_exists_recording(args.recording_name, config["database_path"])
    if exists_recording:
        if not click.confirm("Recording already exists in database. Do you want to override it?", default=True):
            print("Operation cancelled.")
            exit(0)

        bagman_utils.db_ingest_recording(recording_path, config["database_path"], override=True, store_metadata_file=True)

if __name__ == "__main__":
    config = bagman_utils.load_config()
    args = arg_parser().parse_args()
    
    if args.command == "upload":
        recording_name = os.path.basename(os.path.normpath(args.recording_path))
        
        if os.path.exists(os.path.join(config["recordings_storage"], recording_name)):
            if not click.confirm("Recording already exists. Do you want to override it?", default=True):
                print("Operation cancelled.")
                exit(0)

        bagman_utils.upload_recording(args.recording_path, config["recordings_storeage"], move=args.move, verbose=True)

        if args.ingest:
            recording_path = os.path.join(config["recordings_storage"], args.recording_name)
            ingest_recording(recording_path)

    elif args.command == "ingest":
        recording_path = os.path.join(config["recordings_storage"], args.recording_name)
        ingest_recording(recording_path)

    elif args.command == "delete":
        exists_recording = bagman_utils.db_exists_recording(args.recording_name, config["database_path"])
        if not exists_recording:
            print("Recording does not exist.")
            exit(0)

        if not click.confirm("Are you sure you want to delete the recording?", default=False):
            print("Operation cancelled.")
            exit(0)

        bagman_utils.db_delete_recording(args.recording_name, config["database_path"])

        # TODO also delete from recordings storage?
    
    elif args.command == "exist":
        exists_recording_storage = os.path.exists(os.path.join(config["recordings_storage"], args.recording_name))
        exists_recording = bagman_utils.db_exists_recording(args.recording_name, config["database_path"])
        
        print(f"recording exists in storage: {'yes' if exists_recording_storage else 'no'}")
        print(f"recording exists in database: {'yes' if exists_recording else 'no'}")

