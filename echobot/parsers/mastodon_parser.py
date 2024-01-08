from pyxavi.config import Config
from pyxavi.storage import Storage
from pyxavi.terminal_color import TerminalColor
from echobot.lib.keywords_filter import KeywordsFilter
from echobot.parsers.parser_protocol import ParserProtocol
from mastodon import Mastodon
from pyxavi.queue_stack import Queue, SimpleQueueItem
import logging


class MastodonParser(ParserProtocol):
    '''
    Parses the toots from the registered accounts and feed the queue list of toots to publish.
    '''
    DEFAULT_STORAGE_FILE = "storage/accounts.yaml"
    DEFAULT_QUEUE_FILE = "storage/queue.yaml"

    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
        self._accounts_storage = Storage(
            config.get("mastodon_parser.storage_file", self.DEFAULT_STORAGE_FILE)
        )
        self._queue = Queue(
            logger=self._logger,
            storage_file=config.get("toots_queue_storage.file", self.DEFAULT_QUEUE_FILE)
        )
        self._keywords_filter = KeywordsFilter(config)

    def parse(self, params: dict = None) -> None:

        if "mastodon" not in params or not isinstance(params["mastodon"], Mastodon):
            raise RuntimeError("Expecting a Mastodon instance as a parameter")

        mastodon = params["mastodon"]

        # Do we have accounts defined?
        accounts_params = self._config.get("mastodon_parser.accounts", None)
        if not accounts_params:
            self._logger.info("No accounts registered to parse, skipping,")
            return

        # Get info about the bot itself.
        # Will be useful later on to get the relations with other accounts.
        bot_account = mastodon.me()

        # For each user in the config
        for account_params in accounts_params:
            account_user = account_params["user"]
            self._logger.info(
                f"{TerminalColor.BLUE}Processing account {account_user}{TerminalColor.END}"
            )

            account_id = None
            last_seen_toot = None
            keywords_filter_profile = account_params["keywords_filter_profile"] \
                if "keywords_filter_profile" in account_params\
                and account_params["keywords_filter_profile"] else None

            # Do we have any config relating this user already?
            self._logger.debug("Getting possible stored data for %s", account_user)
            user = self._accounts_storage.get_hashed(account_user)
            if user:
                self._logger.debug("Reusing stored data for %s", account_user)
                account_id = user["id"]

                if not self._config.get("mastodon_parser.ignore_toots_offset") \
                   and user["last_seen_toot"]:
                    last_seen_toot = user["last_seen_toot"]
            else:
                # Get the account ID from the given user string
                self._logger.debug("Searching for %s", account_user)
                accounts = mastodon.account_search(account_user)

                if not accounts:
                    self._logger.warn("No account found for %s, skipping", account_user)
                    continue
                else:
                    account_id = accounts[0]["id"]
                    user = {"id": account_id}

                    # Do we need to follow this account?
                    if "auto_follow" in account_params and account_params["auto_follow"]:
                        self._logger.info("Following the account %s", account_user)
                        # Get first the bot's data
                        bot_is_following = mastodon.account_following(bot_account["id"])
                        found = False
                        for following in bot_is_following:
                            if following["id"] == account_id:
                                self._logger.debug(
                                    "The bot is already following %s, skipping", account_user
                                )
                                found = True
                        if not found:
                            self._logger.debug("Registering the following to %s", account_user)
                            mastodon.account_follow(account_id, reblogs=True)
                            # The federation does not get updated instantly.
                            # Toots will appear after some time

            # Get the statuses from the given account ID
            self._logger.debug(
                "Getting toots from %s since %s",
                account_user,
                last_seen_toot if last_seen_toot else "ever"
            )
            toots = mastodon.account_statuses(account_id, since_id=last_seen_toot)
            self._logger.debug("got %s", len(toots))

            # If no toots, just go for the next account
            if len(toots) == 0:
                self._logger.debug(
                    "No Toots received for account %s.May be a federation issue. " +
                    "Is the bot following the account?",
                    account_user
                )
                continue

            # Keep track of the last toot seen
            new_last_seen_toot = toots[0].id

            # For each status
            queued_toots = 0
            total_toots = len(toots)
            for received_toot in toots:

                toot = {
                    "id": received_toot.id,
                    "published_at": received_toot.created_at,
                    "action": "reblog"
                }

                # Is visibility matching?
                if self._config.get("mastodon_parser.only_public_visibility"):
                    if received_toot.visibility != "public":
                        continue

                # Only in case that we need to filter per
                #   keywords and the filtering bans the content.
                if keywords_filter_profile and \
                    not self._keywords_filter.profile_allows_text(
                        keywords_filter_profile,
                        received_toot.content):
                    self._logger.debug(
                        "Filtering %s per keyword profile '%s', this toot is not allowed",
                        account_user,
                        keywords_filter_profile
                    )
                    continue

                # Is an own status?
                if not received_toot.in_reply_to_id \
                    and not received_toot.in_reply_to_account_id \
                        and account_params["toots"]:
                    # queue to publish if the config say so
                    queued_toots += 1
                    self._queue.append(SimpleQueueItem(toot))

                # Is a retoot?
                if received_toot.reblog \
                   and account_params["retoots"]:
                    # queue to publish if the config say so
                    queued_toots += 1
                    self._queue.append(SimpleQueueItem(toot))

            # Log minimal stats
            if queued_toots > 0:
                self._logger.info(
                    f"{TerminalColor.GREEN}Added {queued_toots} posts of" +
                    f" {total_toots} to the queue{TerminalColor.END}"
                )

            # Update our storage with what we found
            self._logger.debug("Updating gathered account data for %s", account_user)
            self._accounts_storage.set_hashed(
                account_user, {
                    **user, **{
                        "last_seen_toot": new_last_seen_toot
                    }
                }
            )
            self._logger.debug("Storing data for %s", account_user)
            self._accounts_storage.write_file()

        # Update the toots queue, by adding the new ones at the end of the list
        self._queue.sort(param="published_at")
        self._queue.deduplicate(param="id")
        self._queue.save()
