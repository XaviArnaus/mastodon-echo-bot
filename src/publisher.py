from pyxavi.config import Config
from pyxavi.storage import Storage
from pyxavi.media import Media
from .queue import Queue
from mastodon import Mastodon
import logging

class Publisher:
    '''
    Publisher

    It is responsible to re-toot the queued toots.
    There are 2 methods, depending if we want to publish all in one shot or just the older one
    '''

    MAX_RETRIES = 3

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
                            shall_download = True
                            if "url" in item and item["url"] is not None:
                                media_file = item["url"]
                            elif "path" in item and item["path"] is not None:
                                media_file = item["path"]
                                shall_download = False

                            else:
                                self._logger.warning("the Media to post does not have an URL or a PATH")
                                continue
                            posted_result = self._post_media(
                                media_file=media_file,
                                download_file=shall_download,
                                description=item["alt_text"] if "alt_text" in item else None,
                                mime_type=item["mime_type"] if "mime_type" in item else None
                            )
                            if posted_result:
                                posted_media.append(posted_result["id"])
                            else:
                                self._logger.info("Could not post %s", media_file)
                    retry = 0
                    toot = None
                    while toot is None:
                        try:
                            self._logger.info("Tooting new post (retry: %d) %s", retry, toot["status"])
                            toot = self._mastodon.status_post(
                                toot["status"],
                                language=toot["language"],
                                media_ids=posted_media if posted_media else None
                            )
                            return toot
                        except Exception as e:
                            self._logger.exception(e)
                            retry += 1
                            if retry >= self.MAX_RETRIES:
                                self._logger.error(f"MAX RETRIES of {self.MAX_RETRIES} is reached. Discarding toot.")
                                break
                            
            else:
                self._logger.warn("Toot with published_at %s does not have an action, skipping.", toot["published_at"])
    
    def _post_media(self, media_file: str, download_file: bool, description: str, mime_type: str = None) -> dict:
        try:
            if download_file is True:
                downloaded = Media().download_from_url(media_file, self._config.get("publisher.media_storage"))
            else:
                downloaded = {
                    "file": media_file,
                    "mime_type": mime_type
                }
            return self._mastodon.media_post(
                downloaded["file"],
                mime_type=downloaded["mime_type"],
                description=description,
                focus=(0,1)
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


