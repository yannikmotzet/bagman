import os

from dotenv import load_dotenv
from pymongo import MongoClient

from bagman.utils.db.db_interface import AbstractBagmanDB


class MongoDBBackend(AbstractBagmanDB):
    def __init__(self, uri, db_name="bagman", collection="bagman"):
        load_dotenv()
        if "DATABASE_USER" in os.environ and "DATABASE_PASSWORD" in os.environ:
            self.client = MongoClient(
                uri,
                username=os.environ["DATABASE_USER"],
                password=os.environ["DATABASE_PASSWORD"],
            )
        else:
            self.client = MongoClient(uri)

        try:
            # Attempt to connect to the database
            self.client.admin.command("ping")
        except Exception as e:
            raise ConnectionError("Unable to connect to the MongoDB server.") from e

        self.db = self.client[db_name]

        # Check if the database can be accessed
        if db_name not in self.client.list_database_names():
            raise PermissionError(f"Access to the database '{db_name}' is denied.")

        self.collection = self.db[collection]

    def get_all_records(self):
        return list(self.collection.find({}, {"_id": 0}))

    def upsert_record(self, record, column_name, value):
        self.collection.update_one({column_name: value}, {"$set": record}, upsert=True)

    def insert_record(self, record):
        self.collection.insert_one(record)

    def contains_record(self, column_name, value):
        return self.collection.count_documents({column_name: value}, limit=1) > 0

    def get_record(self, column_name, value):
        return self.collection.find_one({column_name: value}, {"_id": 0})

    def search_record(self, column_name, value):
        return list(self.collection.find({column_name: value}, {"_id": 0}))

    def remove_record(self, column_name, value):
        self.collection.delete_many({column_name: value})

    def truncate_database(self):
        self.collection.delete_many({})

    def insert_multiple_records(self, records):
        self.collection.insert_many(records)
