from bundle.config import Config
from bundle.storage import Storage
from bundle.downloader import download_media_from_url
from .queue import Queue
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
        self._queue = Queue(config)
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
                    posted_media = []
                    if "media" in toot and toot["media"]:
                        self._logger.info("Posting first %s media items", len(toot["media"]))
                        for item in toot["media"]:
                            posted_result = self._post_media(
                                item["url"],
                                description=item["alt_text"] if "alt_text" in item else None
                            )
                            if posted_result:
                                posted_media.append(posted_result["id"])
                            else:
                                self._logger.info("Could not post %s", item["url"])
                    self._logger.info("Tooting new post %s", toot["status"])
                    return self._mastodon.status_post(
                        toot["status"],
                        language=toot["language"],
                        media_ids=posted_media if posted_media else None
                    )
            else:
                self._logger.warn("Toot with published_at %s does not have an action, skipping.", toot["published_at"])
    
    def _post_media(self, media_file: str, description: str) -> dict:
        try:
            downloaded = download_media_from_url(media_file, self._config.get("publisher.media_storage"))
            return self._mastodon.media_post(
                downloaded["file"],
                mime_type=downloaded["mime_type"],
                description=description
            )
        except Exception as e:
            self._logger.exception(e)


    def publish_all_from_queue(self) -> None:
        if self._queue.is_empty():
            self._logger.info("The queue is empty, skipping.")
            return

        for queued_toot in self._queue.get_all():
            self._execute_action(queued_toot)

        self._logger.info("Cleaning stored queue")
        if not self._config.get("publisher.dry_run"):
            self._queue.clean()
            self._queue.save()

    
    def publish_older_from_queue(self) -> None:
        if self._queue.is_empty():
            self._logger.info("The queue is empty, skipping.")
            return

        self._execute_action(self._queue.pop())

        if not self._config.get("publisher.dry_run"):
            self._queue.save()


