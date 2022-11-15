from bundle.config import Config
from bundle.storage import Storage
import logging

class Queue:

    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
        self._toots_queue = Storage(self._config.get("toots_queue_storage.file"))

    def update(self, new_toots: list) -> None:
        self._logger.info("Reading queue")
        saved_queue = self._toots_queue.get("queue", [])
        self._logger.info("Adding %d to the queue", len(new_toots))
        for toot in new_toots:
            saved_queue.append(toot)
        self._logger.info("Ensuring that the queue is sorted by date ASC and without duplications")
        saved_queue = sorted(saved_queue, key=lambda x: x["published_at"])
        processed_queue = []
        [processed_queue.append(x) for x in saved_queue if x not in processed_queue]
        self._logger.info("Saving the queue")
        self._toots_queue.set("queue", processed_queue)
        self._toots_queue.write_file()