from bundle.config import Config
from bundle.storage import Storage
from mastodon import Mastodon
import logging

class Publisher:
    '''
    Publisher

    It is responsible to re-toot the queued toots.
    There are 2 methods, depending if we want to publish all in one shot or just the older one
    '''
    def __init__(self, config: Config, mastodon: Mastodon) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
        self._toots_queue = Storage(self._config.get("toots_queue_storage.file"))
        self._mastodon = mastodon

    def _execute_action(self, toot: dict) -> dict:
        if not self._config.get("publisher.dry_run"):
            if "action" in toot and toot["action"]:
                if toot["action"] == "reblog":
                    self._logger.info("Retooting post %d", toot["id"])
                    return self._mastodon.status_reblog(
                        toot["id"]
                    )
                elif toot["action"] == "new":
                    self._logger.info("Tooting new post %s", toot["status"])
                    return self._mastodon.status_post(
                        toot["status"],
                        language=toot["language"]
                    )
            else:
                self._logger.warn("Toot with published_at %s does not have an action, skipping.", toot["published_at"])

    def publish_all_from_queue(self) -> None:
        self._logger.info("Reading queue")
        saved_queue = self._toots_queue.get("queue", [])

        if not saved_queue:
            self._logger.info("The queue is empty, skipping.")
            return

        for queued_toot in saved_queue:
            self._execute_action(queued_toot)

        self._logger.info("Cleaning stored queue")
        if not self._config.get("publisher.dry_run"):
            self._toots_queue.set("queue", [])
            self._toots_queue.write_file()

    
    def publish_older_from_queue(self) -> None:
        self._logger.info("Reading queue")
        saved_queue = self._toots_queue.get("queue", [])

        if not saved_queue:
            self._logger.info("The queue is empty, skipping.")
            return


        if not self._config.get("publisher.dry_run"):
            older_queued_toot = saved_queue.pop(0)
        else:
            older_queued_toot = saved_queue[0]

        self._execute_action(older_queued_toot)

        self._logger.info("Updating stored queue")
        if not self._config.get("publisher.dry_run"):
            self._toots_queue.set("queue", saved_queue)
            self._toots_queue.write_file()


