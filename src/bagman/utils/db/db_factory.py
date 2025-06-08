from bagman.utils.db.elasticsearch_backend import ElasticsearchBackend
from bagman.utils.db.mongodb_backend import MongoDBBackend
from bagman.utils.db.tinydb_backend import TinyDBBackend


# type based loader
def get_db(type, uri, table="bagman"):
    if type == "json":
        return TinyDBBackend(uri)
    elif type == "mongodb":
        return MongoDBBackend(uri, collection=table)
    elif type == "elasticsearch":
        return ElasticsearchBackend(uri, index=table)
    else:
        raise ValueError("unsupported backend type")
