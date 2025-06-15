import os

from tinydb import Query, TinyDB

from bagman.utils.db.db_interface import AbstractBagmanDB


class TinyDBBackend(AbstractBagmanDB):
    def __init__(self, database_path):
        self.database_path = database_path
        self.is_connected()
        self.db = TinyDB(database_path)

    def __del__(self):
        if hasattr(self, "db") and self.db is not None:
            self.db.close()

    def is_connected(self):
        if not os.path.exists(self.database_path):
            raise FileNotFoundError(
                f"The database file at {self.database_path} does not exist."
            )

    def get_all_records(self):
        return self.db.all()

    def upsert_record(self, record, column_name, value):
        query = Query()[column_name] == value
        self.db.upsert(record, query)

    def insert_record(self, record):
        self.db.insert(record)

    def contains_record(self, column_name, value):
        query = Query()[column_name] == value
        return self.db.contains(query)

    def get_record(self, column_name, value):
        query = Query()[column_name] == value
        return self.db.get(query)

    def search_record(self, column_name, value):
        query = Query()[column_name] == value
        return self.db.search(query)

    def remove_record(self, column_name, value):
        query = Query()[column_name] == value
        self.db.remove(query)

    def truncate_database(self):
        self.db.truncate()

    def insert_multiple_records(self, records):
        self.db.insert_multiple(records)
