from pyxavi.config import Config
from pyxavi.logger import Logger
from pyxavi.terminal_color import TerminalColor
from pyxavi.mastodon_publisher import MastodonPublisher
from pyxavi.queue_stack import Queue
from pyxavi.mastodon_helper import MastodonConnectionParams,\
    StatusPost, StatusPostVisibility, StatusPostContentType
import os


class Publisher(MastodonPublisher):
    '''
    Publisher

    It is responsible to publish the queued status posts.
    '''

    # These params are supported in Janitor but not in Echo,
    #   so we set them up here by now waiting for a next iteration for Echo.
    STATUS_PARAMS = {
        "max_length": 1000,
        "content_type": StatusPostContentType.PLAIN,
        "visibility": StatusPostVisibility.PUBLIC,
        "username_to_dm": None
    }
    DEFAULT_QUEUE_FILE = "storage/queue.yaml"

    def __init__(
        self, config: Config, base_path: str = None, only_oldest: bool = False
    ) -> None:
        
        logger = Logger(config=config).get_logger()

        super().__init__(
            config=config, logger=logger, base_path=base_path
        )

        queue_storage_file = config.get("toots_queue_storage.file", self.DEFAULT_QUEUE_FILE)
        if base_path is not None:
            queue_storage_file = os.path.join(base_path, queue_storage_file)
        self._queue = Queue(logger=logger, storage_file=queue_storage_file)
        self._only_oldest = only_oldest if only_oldest is not None\
            else config.get("publisher.only_oldest_post_every_iteration", False)

    def _execute_action(self, toot: dict, previous_id: int = None) -> dict:

        if "action" in toot and toot["action"]:
            if toot["action"] == "reblog":
                self._logger.info("Retooting post %d", toot["id"])
                return self._mastodon.status_reblog(toot["id"])
            elif toot["action"] == "new":
                self._logger.debug("The Publisher._execute_action has a new post")

                posted_media = []
                if "media" in toot and toot["media"]:
                    posted_media = self.publish_media(media=toot["media"])

                status_post = StatusPost(
                    status=toot["status"],
                    language=toot["language"],
                    in_reply_to_id=previous_id if previous_id else None,
                    media_ids=posted_media if posted_media else None,
                    visibility=self._connection_params.status_params.visibility,
                    content_type=self._connection_params.status_params.content_type,
                )

                published = self.publish_status_post(status_post=status_post)
                return published

        else:
            self._logger.warn(
                "Toot with published_at %s does not have an action, skipping.",
                toot["published_at"]
            )

    def publish_all_from_queue(self) -> None:
        if self._queue.is_empty():
            self._logger.info(
                f"{TerminalColor.CYAN}The queue is empty, skipping.{TerminalColor.END}"
            )
            return

        should_continue = True
        previous_id = None
        self._logger.debug("Queue is not empty, publishing from it")
        while should_continue and not self._queue.is_empty():
            # Get the first element from the queue
            queued_post = self._queue.pop().to_dict()
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

        queued_post = self._queue.first().to_dict()
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

    def load_connection_params(self, named_account=None) -> None:
        # While we don't migrate this config section to a proper
        #   mastodon.named_account config parameterset,
        #   we need to continue emulating it like this.
        self._logger.debug("Emulating the loading of params")
        self._connection_params = MastodonConnectionParams.from_dict(
            {
                "app_name": self._config.get("app.name"),
                "api_base_url": self._config.get("app.api_base_url"),
                "instance_type": self._config.get("app.instance_type"),
                "credentials": {
                    "client_file": self._config.get("app.client_credentials"),
                    "user_file": self._config.get("app.user_credentials"),
                    "user": {
                        "email": self._config.get("app.user.email"),
                        "password": self._config.get("app.user.password")
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
