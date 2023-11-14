from pyxavi.config import Config
from pyxavi.storage import Storage
import logging


class Queue:

    DEFAULT_STORAGE_FILE = "storage/queue.yaml"
    _queue = []

    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
        self.__storage_file = config.get("toots_queue_storage.file", self.DEFAULT_STORAGE_FILE)
        self.load()

    def load(self) -> int:
        self._toots_queue = Storage(self.__storage_file)
        self._queue = self._toots_queue.get("queue", [])
        return self.length()

    def append(self, item=dict) -> None:
        self._queue.append(item)

    def sort_by_date(self) -> None:
        self._logger.debug("Sorting queue by date ASC")
        self._queue = sorted(self._queue, key=lambda x: x["published_at"])

    def deduplicate(self) -> None:
        self._logger.debug("Deduplicating queue")
        new_queue = []
        [new_queue.append(x) for x in self._queue if x not in new_queue]
        self._queue = new_queue

    def save(self) -> None:
        self._logger.debug("Saving the queue")
        self._toots_queue.set("queue", self._queue)
        self._toots_queue.write_file()

    def update(self) -> None:
        self.sort_by_date()
        self.deduplicate()
        self.save()

    def is_empty(self) -> bool:
        return False if self._queue else True

    def get_all(self) -> list:
        return self._queue

    def clean(self) -> None:
        self._queue = []

    def length(self) -> int:
        return len(self._queue)

    def pop(self) -> dict:
        if not self.is_empty():
            return self._queue.pop(0)
        else:
            return None

    def first(self) -> dict:
        if not self.is_empty():
            return self._queue[0]
        else:
            return None

    def last(self) -> dict:
        if not self.is_empty():
            return self._queue[-1]
        else:
            return None
