import os
from tinydb import TinyDB, Query

class BagmanDB:
    def __init__(self, database_path):
        """
        Initialize the BagmanDB class.
        Args:
            database_path (str): The path to the TinyDB database file.
        """
        if not os.path.exists(database_path):
            raise FileNotFoundError(f"The database file at {database_path} does not exist.")
        self.db = TinyDB(database_path)

    def get_all_records(self):
        """
        Get all records from the TinyDB database.
        Returns:
            list: A list of all records in the database.
        """
        return self.db.all()

    def upsert_record(self, record, column_name, value):
        """
        Upsert (update or insert) a record in the TinyDB database.
        Args:
            record (dict): The record to upsert.
            column_name (str): The column name to match the record.
            value: The value to match the record.
        """
        query = Query()[column_name] == value
        self.db.upsert(record, query)

    def insert_record(self, record):
        """
        Insert a record into the TinyDB database.
        Args:
            record (dict): The record to insert.
        """
        self.db.insert(record)

    def contains_record(self, column_name, value):
        """
        Check if a record exists in the TinyDB database.
        Args:
            column_name (str): The column name to match the record.
            value: The value to match the record.
        Returns:
            bool: True if the record exists, False otherwise.
        """
        query = Query()[column_name] == value
        return self.db.contains(query)

    def get_record(self, column_name, value):
        """
        Get a record from the TinyDB database.
        Args:
            column_name (str): The column name to match the record.
            value: The value to match the record.
        Returns:
            dict: The matched record, or None if not found.
        """
        query = Query()[column_name] == value
        return self.db.get(query)
    
    def search_record(self, column_name, value):
        """
        Search for records in the TinyDB database that match a specific column value.
        Args:
            column_name (str): The column name to match the records.
            value: The value to match the records.
        Returns:
            list: A list of matched records.
        """
        query = Query()[column_name] == value
        return self.db.search(query)

    def remove_record(self, column_name, value):
        """
        Remove a record from the TinyDB database.
        Args:
            column_name (str): The column name to match the record.
            value: The value to match the record.
        """
        query = Query()[column_name] == value
        self.db.remove(query)

    def truncate_database(self):
        """
        Truncate the TinyDB database.
        """
        self.db.truncate()

    def insert_multiple_records(self, records):
        """
        Insert multiple records into the TinyDB database.
        Args:
            records (list): The list of records to insert.
        """
        self.db.insert_multiple(records)
