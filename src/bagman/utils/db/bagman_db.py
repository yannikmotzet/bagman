from bagman.utils.db.db_factory import get_db


class BagmanDB:
    """
    Unified public interface to the Bagman database, regardless of backend.
    """

    def __init__(self, type, uri, name="bagman"):
        """
        Args:
            config (dict): Must contain:
                - 'type': One of ['json', 'mongodb', 'elasticsearch']
                - 'uri': Path or connection string
        """
        self._backend = get_db(type, uri, name)

    def __getattr__(self, name):
        # delegate method calls to the backend
        return getattr(self._backend, name)
