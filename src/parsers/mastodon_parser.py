from bundle.config import Config
from bundle.storage import Storage
from mastodon import Mastodon
from ..queue import Queue
import logging

class MastodonParser:
    '''
    Parses the toots from the registered accounts and feed the queue list of toots to publish.
    '''
    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
        self._accounts_storage = Storage(config.get("mastodon_parser.storage_file"))
        self._queue = Queue(config)

    def parse(self, mastodon: Mastodon) -> None:
        # This will contain the queue to re-toot
        toots_queue = []

        # Do we have accounts defined?
        accounts_params = self._config.get("mastodon_parser.accounts", None)
        if not accounts_params:
            self._logger.info("No accounts registered to parse, skipping,")
            return

        # For each user in the config
        for account_params in accounts_params:

            account_id = None
            last_seen_toot = None

            # Do we have any config relating this user already?
            self._logger.info("Getting possible stored data for %s", account_params["user"])
            user = self._accounts_storage.get_hashed(account_params["user"])
            if user:
                self._logger.info("Reusing stored data for %s", account_params["user"])
                account_id = user["id"]

                if not self._config.get("mastodon_parser.ignore_toots_offset") \
                    and user["last_seen_toot"]:
                    last_seen_toot = user["last_seen_toot"]
            else:
                # Get the account ID from the given user string
                self._logger.info("Searching for %s", account_params["user"])
                accounts = mastodon.account_search(account_params["user"])

                if not accounts:
                    self._logger.warn("No account found for %s, skipping", account_params["user"])
                    continue
                else:
                    account_id = accounts[0]["id"]

                    user = {
                        "id": account_id
                    }

            # Get the statuses from the given account ID
            self._logger.info("Getting toots from %s since %s", account_params["user"], last_seen_toot if last_seen_toot else "ever")
            toots = mastodon.account_statuses(account_id, since_id=last_seen_toot)
            self._logger.info("got %s", len(toots))

            # If no toots, just go for the next account
            if len(toots) == 0:
                continue
            
            # Keep track of the last toot seen
            new_last_seen_toot = toots[0].id

            # For each status
            for received_toot in toots:

                toot = {
                    "id": toot.id,
                    "published_at": toot.created_at,
                    "action": "reblog"
                }

                # Is visibility matching?
                if self._config.get("mastodon_parser.only_public_visibility"):
                    if received_toot.visibility != "public":
                        continue

                # Is an own status?
                if not received_toot.in_reply_to_id \
                    and not received_toot.in_reply_to_account_id \
                        and account_params["toots"]:
                    # queue to publish if the config say so
                    toots_queue.append(toot)

                # Is a retoot?
                if received_toot.reblog \
                    and account_params["retoots"]:
                    # queue to publish if the config say so
                    toots_queue.append(toot)

            # Update our storage with what we found
            self._logger.debug("Updating gathered account data for %s", account_params["user"])
            self._accounts_storage.set_hashed(
                account_params["user"],
                {
                    **user,
                    **{"last_seen_toot": new_last_seen_toot}
                }
            )
            self._logger.info("Storing data for %s", account_params["user"])
            self._accounts_storage.write_file()

        # Update the toots queue, by adding the new ones at the end of the list
        self._queue.update(toots_queue)