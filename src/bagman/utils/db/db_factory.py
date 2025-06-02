from bagman.utils.db.elasticsearch_backend import ElasticsearchBackend
from bagman.utils.db.mongodb_backend import MongoDBBackend
from bagman.utils.db.tinydb_backend import TinyDBBackend


# type based loader
def get_db(type, uri):
    if type == "json":
        return TinyDBBackend(uri)
    elif type == "mongodb":
        return MongoDBBackend(uri)
    elif type == "elasticsearch":
        return ElasticsearchBackend(uri)
    else:
        raise ValueError("unsupported backend type")
