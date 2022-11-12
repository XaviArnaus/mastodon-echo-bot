from bundle.config import Config
from bundle.storage import Storage
from .mastodon_helper import MastodonHelper
from datetime import datetime
from mastodon import Mastodon
import logging

class Publisher:
    '''
    Publisher

    It is responsible to re-toot the queued toots.
    There are 2 methods, depending if we want to publish all in one shot or just the older one
    '''
    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
        self._toots_queue = Storage(self._config.get("toots_queue_storage.file"))

    def publish_all_from_queue(self, mastodon: Mastodon) -> None:
        self._logger.info("Reading queue")
        saved_queue = self._toots_queue.get("queue", [])

        for queued_toot in saved_queue:
            self._logger.info("Retooting post %d", queued_toot["id"])
            if not self._config.get("publisher.dry_run"):
                new_toot = mastodon.status_reblog(
                    queued_toot["id"]
                )

        self._logger.info("Cleaning stored queue")
        if not self._config.get("publisher.dry_run"):
            self._toots_queue.set("queue", [])
            self._toots_queue.write_file()

    
    def publish_older_from_queue(self, mastodon: Mastodon) -> None:
        self._logger.info("Reading queue")
        saved_queue = self._toots_queue.get("queue", [])

        if not self._config.get("publisher.dry_run"):
            older_queued_toot = saved_queue.pop(0)
        else:
            older_queued_toot = saved_queue[0]

        self._logger.info("Retooting post %d", older_queued_toot["id"])
        if not self._config.get("publisher.dry_run"):
            new_toot = mastodon.status_reblog(
                older_queued_toot["id"]
            )

        self._logger.info("Updating stored queue")
        if not self._config.get("publisher.dry_run"):
            self._toots_queue.set("queue", saved_queue)
            self._toots_queue.write_file()


