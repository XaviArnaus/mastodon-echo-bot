from pyxavi.config import Config
from mastodon import Mastodon
import logging
import os

class MastodonHelper:
    def get_instance(config: Config) -> Mastodon:
        logger = logging.getLogger(config.get("logger.name"))

        # All actions are done under a Mastodon API instance
        logger.info("Starting new Mastodon API instance")
        if (os.path.exists(config.get("app.user_credentials"))):
            logger.debug("Reusing stored User Credentials")
            mastodon = Mastodon(
                access_token = config.get("app.user_credentials")
            )
        else:
            logger.debug("Using Client Credentials")
            mastodon = Mastodon(
                client_id = config.get("app.client_credentials"),
                api_base_url = config.get("app.api_base_url")
            )

            # Logging in is required for all individual runs
            logger.debug("Logging in")
            mastodon.log_in(
                config.get("app.user.email"),
                config.get("app.user.password"),
                to_file = config.get("app.user_credentials")
            )

        return mastodon