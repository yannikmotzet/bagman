import os

from dotenv import load_dotenv
from elasticsearch import Elasticsearch, exceptions

from bagman.utils.db.db_interface import AbstractBagmanDB


class ElasticsearchBackend(AbstractBagmanDB):
    def __init__(self, url, index="bagman"):
        self.index = index

        # set up authentication
        try:
            load_dotenv()
            if "DATABASE_TOKEN" in os.environ:
                self.es = Elasticsearch(url, api_key=os.environ["DATABASE_TOKEN"])
            elif "DATABASE_USER" in os.environ and "DATABASE_PASSWORD" in os.environ:
                self.es = Elasticsearch(
                    url,
                    http_auth=(
                        os.environ["DATABASE_USER"],
                        os.environ["DATABASE_PASSWORD"],
                    ),
                )
            else:
                self.es = Elasticsearch(url)
        except Exception as e:
            raise ConnectionError(f"Failed to initialize Elasticsearch client: {e}")

        self.is_connected()

        # ensure index exists
        try:
            if not self.es.indices.exists(index=self.index):
                self.es.indices.create(index=self.index)
        except exceptions.AuthorizationException as e:
            raise PermissionError(
                f"Not authorized to access or create index '{self.index}': {e}"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to check or create index '{self.index}': {e}")

    def is_connected(self):
        # check if the cluster is reachable
        try:
            if not self.es.ping():
                raise ConnectionError("Elasticsearch cluster is not reachable.")
        except exceptions.AuthenticationException as e:
            raise PermissionError(f"Authentication failed: {e}")
        except Exception as e:
            raise ConnectionError(f"Ping failed: {e}")

    def _get_field_mapping(self, field_path):
        try:
            mapping = self.es.indices.get_mapping(index=self.index)
            # Defensive get with .get and default empty dicts
            index_mapping = mapping.get(self.index, {})
            mappings = index_mapping.get("mappings", {})
            properties = mappings.get("properties", {})
        except Exception:
            # Any failure to get mapping returns None
            return None

        keys = field_path.split(".")
        current = properties
        for key in keys:
            if key not in current:
                return None
            current = current[key]
            # Dive into nested properties if present
            if isinstance(current, dict) and "properties" in current:
                current = current["properties"]
        return current

    def _resolve_exact_field(self, column_name):
        field_mapping = self._get_field_mapping(column_name)
        if not field_mapping:
            # mapping not found; fallback to normal field name
            return column_name

        if isinstance(field_mapping, dict):
            if field_mapping.get("type") == "text":
                fields = field_mapping.get("fields", {})
                if "keyword" in fields:
                    return f"{column_name}.keyword"
                else:
                    return column_name
            # For other types, return as is
            if "type" in field_mapping:
                return column_name
            return column_name
        return column_name

    def get_all_records(self, timeout=10):
        resp = self.es.search(
            index=self.index,
            body={"query": {"match_all": {}}},
            size=10000,
            request_timeout=timeout,
        )
        return [doc["_source"] for doc in resp["hits"]["hits"]]

    def upsert_record(self, record, column_name, value):
        exact_field = self._resolve_exact_field(column_name)
        query = {"query": {"term": {exact_field: {"value": value}}}}
        resp = self.es.search(index=self.index, body=query, size=1)
        hits = resp["hits"]["hits"]

        if hits:
            # update the existing record
            doc_id = hits[0]["_id"]
            self.es.update(index=self.index, id=doc_id, body={"doc": record})
        else:
            # insert as a new record
            self.es.index(index=self.index, body=record, refresh="wait_for")

    def insert_record(self, record):
        self.es.index(index=self.index, body=record, refresh="wait_for")

    def contains_record(self, column_name, value):
        exact_field = self._resolve_exact_field(column_name)
        query = {"query": {"term": {exact_field: {"value": value}}}}
        resp = self.es.count(index=self.index, body=query)
        return resp["count"] > 0

    def get_record(self, column_name, value):
        exact_field = self._resolve_exact_field(column_name)
        query = {"query": {"term": {exact_field: {"value": value}}}}
        resp = self.es.search(index=self.index, body=query, size=1)
        hits = resp["hits"]["hits"]
        return hits[0]["_source"] if hits else None

    def search_record(self, column_name, value):
        exact_field = self._resolve_exact_field(column_name)
        query = {"query": {"term": {exact_field: {"value": value}}}}
        resp = self.es.search(index=self.index, body=query, size=100)
        return [doc["_source"] for doc in resp["hits"]["hits"]]

    def remove_record(self, column_name, value):
        exact_field = self._resolve_exact_field(column_name)
        query = {"query": {"term": {exact_field: {"value": value}}}}
        self.es.delete_by_query(index=self.index, body=query)

    def truncate_database(self):
        self.es.indices.delete(index=self.index, ignore=[400, 404])
        self.es.indices.create(index=self.index)

    def insert_multiple_records(self, records, timeout=10):
        from elasticsearch.helpers import bulk

        actions = [{"_index": self.index, "_source": r} for r in records]
        bulk(self.es, actions, request_timeout=timeout)
