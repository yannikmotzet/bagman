from elasticsearch import Elasticsearch

from bagman.utils.db.db_interface import AbstractBagmanDB


class ElasticsearchBackend(AbstractBagmanDB):
    def __init__(self, url, index="bagman"):
        self.es = Elasticsearch(url)
        self.index = index

    def get_all_records(self):
        resp = self.es.search(
            index=self.index, body={"query": {"match_all": {}}}, size=10000
        )
        return [doc["_source"] for doc in resp["hits"]["hits"]]

    def upsert_record(self, record, column_name, value):
        self.es.index(index=self.index, id=value, body=record)

    def insert_record(self, record):
        self.es.index(index=self.index, body=record)

    def contains_record(self, column_name, value):
        query = {"query": {"term": {column_name: value}}}
        resp = self.es.count(index=self.index, body=query)
        return resp["count"] > 0

    def get_record(self, column_name, value):
        query = {"query": {"term": {column_name: value}}}
        resp = self.es.search(index=self.index, body=query, size=1)
        hits = resp["hits"]["hits"]
        return hits[0]["_source"] if hits else None

    def search_record(self, column_name, value):
        query = {"query": {"term": {column_name: value}}}
        resp = self.es.search(index=self.index, body=query, size=100)
        return [doc["_source"] for doc in resp["hits"]["hits"]]

    def remove_record(self, column_name, value):
        query = {"query": {"term": {column_name: value}}}
        self.es.delete_by_query(index=self.index, body=query)

    def truncate_database(self):
        self.es.delete_by_query(index=self.index, body={"query": {"match_all": {}}})

    def insert_multiple_records(self, records):
        from elasticsearch.helpers import bulk

        actions = [{"_index": self.index, "_source": r} for r in records]
        bulk(self.es, actions)
