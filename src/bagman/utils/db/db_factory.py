from bagman.utils.db.elasticsearch_backend import ElasticsearchBackend
from bagman.utils.db.mongodb_backend import MongoDBBackend
from bagman.utils.db.tinydb_backend import TinyDBBackend


# type based loader
def get_db(type, uri, name="bagman"):
    if type == "json":
        return TinyDBBackend(uri)
    elif type == "mongodb":
        return MongoDBBackend(uri, db_name=name, collection=name)
    elif type == "elasticsearch":
        return ElasticsearchBackend(uri, index=name)
    else:
        raise ValueError("unsupported backend type")
