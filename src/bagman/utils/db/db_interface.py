from abc import ABC, abstractmethod


class AbstractBagmanDB(ABC):
    """
    Abstract interface for BagmanDB backends. All concrete database implementations
    (e.g., TinyDB, MongoDB, Elasticsearch) must implement this interface.
    """

    @abstractmethod
    def get_all_records(self):
        """
        Get all records from the database.
        Returns:
            list: A list of all records in the database.
        """
        pass

    @abstractmethod
    def upsert_record(self, record, column_name, value):
        """
        Upsert (update or insert) a record in the database.
        Args:
            record (dict): The record to upsert.
            column_name (str): The column name to match the record.
            value: The value to match the record.
        """
        pass

    @abstractmethod
    def insert_record(self, record):
        """
        Insert a record into the database.
        Args:
            record (dict): The record to insert.
        """
        pass

    @abstractmethod
    def contains_record(self, column_name, value):
        """
        Check if a record exists in the database.
        Args:
            column_name (str): The column name to match the record.
            value: The value to match the record.
        Returns:
            bool: True if the record exists, False otherwise.
        """
        pass

    @abstractmethod
    def get_record(self, column_name, value):
        """
        Get a record from the database.
        Args:
            column_name (str): The column name to match the record.
            value: The value to match the record.
        Returns:
            dict: The matched record, or None if not found.
        """
        pass

    @abstractmethod
    def search_record(self, column_name, value):
        """
        Search for records in the database that match a specific column value.
        Args:
            column_name (str): The column name to match the records.
            value: The value to match the records.
        Returns:
            list: A list of matched records.
        """
        pass

    @abstractmethod
    def remove_record(self, column_name, value):
        """
        Remove a record from the database.
        Args:
            column_name (str): The column name to match the record.
            value: The value to match the record.
        """
        pass

    @abstractmethod
    def truncate_database(self):
        """
        Truncate (clear) the entire database.
        """
        pass

    @abstractmethod
    def insert_multiple_records(self, records):
        """
        Insert multiple records into the database.
        Args:
            records (list): The list of records to insert.
        """
        pass
