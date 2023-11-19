from pyxavi.config import Config
from pyxavi.media import Media
from pyxavi.terminal_color import TerminalColor
from echobot.lib.queue import Queue
from pyxavi.mastodon_helper import MastodonHelper, MastodonConnectionParams,\
    StatusPost, StatusPostVisibility, StatusPostContentType
import logging
import time


class Publisher:
    '''
    Publisher

    It is responsible to publish the queued status posts.
    '''

    MAX_RETRIES = 3
    SLEEP_TIME = 10

    # These params are supported in Janitor but not in Echo,
    #   so we set them up here by now waiting for a next iteration for Echo.
    STATUS_PARAMS = {
        "max_length": 1000,
        "content_type": StatusPostContentType.PLAIN,
        "visibility": StatusPostVisibility.PUBLIC,
        "username_to_dm": None
    }

    def __init__(
        self, config: Config, base_path: str = None, only_oldest: bool = False
    ) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
        self._queue = Queue(config)
        self._connection_params = self._get_connection_params(config=config)
        self._instance_type = MastodonHelper.valid_or_raise(
            self._connection_params.instance_type
        )
        self._is_dry_run = config.get("publisher.dry_run", False)
        self._media_storage = self._config.get("publisher.media_storage")

        self._mastodon = MastodonHelper.get_instance(
            connection_params=self._connection_params, logger=self._logger, base_path=base_path
        )
        self._only_oldest = only_oldest if only_oldest is not None\
            else config.get("publisher.only_oldest_post_every_iteration", False)

    def _execute_action(self, toot: dict, previous_id: int = None) -> dict:
        if self._is_dry_run:
            self._logger.debug("It's a Dry Run, stopping here.")
            return None

        if "action" in toot and toot["action"]:
            if toot["action"] == "reblog":
                self._logger.info("Retooting post %d", toot["id"])
                return self._mastodon.status_reblog(toot["id"])
            elif toot["action"] == "new":
                posted_media = []
                if "media" in toot and toot["media"]:
                    self._logger.info(
                        f"{TerminalColor.CYAN}Posting first %s media items{TerminalColor.END}",
                        len(toot["media"])
                    )
                    for item in toot["media"]:
                        shall_download = True
                        if "url" in item and item["url"] is not None:
                            media_file = item["url"]
                        elif "path" in item and item["path"] is not None:
                            media_file = item["path"]
                            shall_download = False

                        else:
                            self._logger.warning(
                                f"{TerminalColor.RED}the Media to post does " +
                                f"not have an URL or a PATH{TerminalColor.END}"
                            )
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
                            self._logger.info(
                                f"{TerminalColor.RED}Could not post %s{TerminalColor.END}",
                                media_file
                            )

                # Let's ensure that it fits according to the params
                toot["status"] = self.__slice_status_if_longer_than_defined(
                    status=toot["status"]
                )

                # Avoid posting if there's no image AND no body
                if len(posted_media) == 0 and len(toot["status"]) == 0:
                    self._logger.warning("No media AND no body, skipping this post")
                    return None

                retry = 0
                published = None
                while published is None:
                    try:
                        self._logger.info(
                            f"{TerminalColor.CYAN}Tooting new post (retry {retry})" +
                            f" \"%s\"]{TerminalColor.END}",
                            toot["status"]
                        )
                        status_post = StatusPost(
                            status=toot["status"],
                            language=toot["language"],
                            in_reply_to_id=previous_id if previous_id else None,
                            media_ids=posted_media if posted_media else None,
                            visibility=self._connection_params.status_params.visibility,
                            content_type=self._connection_params.status_params.content_type,
                        )
                        published = self._do_status_publish(status_post=status_post)
                        return published
                    except Exception as e:
                        self._logger.exception(e)
                        self._logger.debug(f"sleeping {self.SLEEP_TIME} seconds")
                        time.sleep(self.SLEEP_TIME)
                        retry += 1
                        if retry >= self.MAX_RETRIES:
                            self._logger.error(
                                f"MAX RETRIES of {self.MAX_RETRIES} is reached. " +
                                "Discarding toot."
                            )
                            break

        else:
            self._logger.warn(
                "Toot with published_at %s does not have an action, skipping.",
                toot["published_at"]
            )

    def _post_media(
        self,
        media_file: str,
        download_file: bool,
        description: str,
        mime_type: str = None
    ) -> dict:
        try:
            if download_file is True:
                downloaded = Media().download_from_url(media_file, self._media_storage)
            else:
                downloaded = {"file": media_file, "mime_type": mime_type}
            return self._mastodon.media_post(
                downloaded["file"],
                mime_type=downloaded["mime_type"],
                description=description,
                focus=(0, 1)
            )
        except Exception as e:
            self._logger.exception(e)

    def publish_all_from_queue(self) -> None:
        if self._queue.is_empty():
            self._logger.info(
                f"{TerminalColor.CYAN}The queue is empty, skipping.{TerminalColor.END}"
            )
            return

        should_continue = True
        previous_id = None
        while should_continue and not self._queue.is_empty():
            # Get the first element from the queue
            queued_post = self._queue.pop()
            # Publish it
            result = self._execute_action(queued_post, previous_id=previous_id)
            # Let's capture the ID in case we want to do a thread
            if result is not None:
                # If it's a dry-run, there won't be any result returned.
                previous_id = result["id"]
                self._logger.debug(f"Post was published with ID {previous_id}")

            # Maybe we have several posts in a group that we need to post
            #  all together, regardless of the rest of conditions
            if previous_id is not None and "group_id" in queued_post and\
               self.__next_in_queue_matches_group_id(queued_post["group_id"]):
                self._logger.debug(
                    "Post was published and there are more in this group. Continue"
                )
                should_continue = True
            else:
                # Do we want to publish only the oldest in every iteration?
                #   This means that the queue gets empty one item every run
                if self._only_oldest:
                    self._logger.info(
                        f"{TerminalColor.CYAN}We're meant to publish only the oldest." +
                        f" Finishing.{TerminalColor.END}"
                    )
                    should_continue = False

        if not self._is_dry_run:
            self._queue.save()

    def __next_in_queue_matches_group_id(self, group_id: str) -> bool:
        """
        Posts may have an ID representing a belonging group.
            They mostly come from slicing posts due to length,
            so we want to do a thread.

        True if the next in the queue also have the same ID,
            otherwise False
        """
        if self._queue.is_empty():
            return False

        queued_post = self._queue.first()
        if queued_post is not None and "group_id" not in queued_post:
            return False

        if queued_post["group_id"] == group_id:
            return True

        return False

    def reload_queue(self) -> int:
        # Previous length
        previous = self._queue.length()
        new = self._queue.load()

        return new - previous

    def _do_status_publish(self, status_post: StatusPost) -> dict:
        """
        This is the method that executes the post of the status.

        No checks, no validations, just the action.
        """

        if self._instance_type == MastodonHelper.TYPE_MASTODON:
            published = self._mastodon.status_post(
                status=status_post.status,
                in_reply_to_id=status_post.in_reply_to_id,
                media_ids=status_post.media_ids,
                sensitive=status_post.sensitive,
                visibility=status_post.visibility,
                spoiler_text=status_post.spoiler_text,
                language=status_post.language,
                idempotency_key=status_post.idempotency_key,
                scheduled_at=status_post.scheduled_at,
                poll=status_post.poll
            )
        elif self._instance_type == MastodonHelper.TYPE_PLEROMA:
            published = self._mastodon.status_post(
                status=status_post.status,
                in_reply_to_id=status_post.in_reply_to_id,
                media_ids=status_post.media_ids,
                sensitive=status_post.sensitive,
                visibility=status_post.visibility,
                spoiler_text=status_post.spoiler_text,
                language=status_post.language,
                idempotency_key=status_post.idempotency_key,
                content_type=status_post.content_type,
                scheduled_at=status_post.scheduled_at,
                poll=status_post.poll,
                quote_id=status_post.quote_id
            )
        elif self._instance_type == MastodonHelper.TYPE_FIREFISH:
            published = self._mastodon.status_post(
                status=status_post.status,
                in_reply_to_id=status_post.in_reply_to_id,
                media_ids=status_post.media_ids,
                sensitive=status_post.sensitive,
                visibility=status_post.visibility,
                spoiler_text=status_post.spoiler_text,
                # language=status_post.language,
                idempotency_key=status_post.idempotency_key,
                content_type=status_post.content_type,
                scheduled_at=status_post.scheduled_at,
                poll=status_post.poll,
                quote_id=status_post.quote_id
            )
        else:
            raise RuntimeError(f"Unknown instance type {self._instance_type}")
        return published

    def __slice_status_if_longer_than_defined(self, status: str) -> str:
        max_length = self._connection_params.status_params.max_length
        if len(status) > max_length:
            self._logger.debug(
                f"The status post is longer than the max length of {max_length}. Cutting..."
            )
            status = status[:max_length - 3] + "..."

        return status

    def _get_connection_params(self, config: Config) -> MastodonConnectionParams:
        return MastodonConnectionParams.from_dict(
            {
                "app_name": config.get("app.name"),
                "api_base_url": config.get("app.api_base_url"),
                "instance_type": config.get("app.instance_type"),
                "credentials": {
                    "client_file": config.get("app.client_credentials"),
                    "user_file": config.get("app.user_credentials"),
                    "user": {
                        "email": config.get("app.user.email"),
                        "password": config.get("app.user.password")
                    }
                },  # Configuration regarding the Status itself
                "status_params": {
                    # [Integer] Status max length
                    "max_length": self.STATUS_PARAMS["max_length"],
                    # [String] Status Post content type:
                    #   "text/plain" | "text/markdown" | "text/html" | "text/bbcode"
                    # Only vaild for Pleroma and Akkoma instances.
                    #   Mastodon instances will ignore it
                    "content_type": self.STATUS_PARAMS["content_type"],
                    # [String] Status Post visibility:
                    #   "direct" | "private" | "unlisted" | "public"
                    "visibility": self.STATUS_PARAMS["visibility"],
                    # [String] Username to mention for "direct" visibility
                    "username_to_dm": self.STATUS_PARAMS["username_to_dm"]
                }
            }
        )


class PublisherException(BaseException):
    pass
