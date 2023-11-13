from __future__ import annotations
from pyxavi.config import Config
from pyxavi.firefish import Firefish
from .mastodon_connection_params import MastodonConnectionParams
from mastodon import Mastodon
import logging
import os


class MastodonHelper:

    TYPE_MASTODON = "mastodon"
    TYPE_PLEROMA = "pleroma"
    TYPE_FIREFISH = "firefish"

    VALID_TYPES = [TYPE_MASTODON, TYPE_PLEROMA, TYPE_FIREFISH]

    FEATURE_SET_BY_INSTANCE_TYPE = {TYPE_MASTODON: "mainline", TYPE_PLEROMA: "pleroma"}

    WRAPPER = {TYPE_MASTODON: Mastodon, TYPE_PLEROMA: Mastodon, TYPE_FIREFISH: Firefish}

    @staticmethod
    def get_instance(
        config: Config,
        connection_params: MastodonConnectionParams,
        base_path: str = None
    ) -> Mastodon:
        logger = logging.getLogger(config.get("logger.name"))

        instance_type = MastodonHelper.valid_or_raise(connection_params.instance_type)
        user_file = connection_params.credentials.user_file
        client_file = connection_params.credentials.client_file
        if base_path is not None:
            user_file = os.path.join(base_path, user_file)
            client_file = os.path.join(base_path, client_file)

        # All actions are done under a Mastodon API instance
        logger.debug("Starting new Mastodon API instance")
        if (os.path.exists(user_file)):
            logger.debug("Reusing stored User Credentials")
            mastodon = MastodonHelper.WRAPPER[instance_type](
                access_token=user_file,
                feature_set=MastodonHelper.FEATURE_SET_BY_INSTANCE_TYPE[instance_type]
                if instance_type in [MastodonHelper.TYPE_MASTODON, MastodonHelper.TYPE_PLEROMA]
                else None
            )
        else:
            logger.debug("Using Client Credentials")
            mastodon = MastodonHelper.WRAPPER[instance_type](
                client_id=client_file,
                api_base_url=connection_params.api_base_url,
                feature_set=MastodonHelper.FEATURE_SET_BY_INSTANCE_TYPE[instance_type]
                if instance_type in [MastodonHelper.TYPE_MASTODON, MastodonHelper.TYPE_PLEROMA]
                else None
            )

            # Logging in is required for all individual runs
            logger.debug("Logging in")
            mastodon.log_in(
                connection_params.credentials.user.email,
                connection_params.credentials.user.password,
                to_file=user_file
            )

        return mastodon

    @staticmethod
    def valid_or_raise(value: str) -> str:
        if value not in MastodonHelper.VALID_TYPES:
            raise RuntimeError(f"Value [{value}] is not a valid instance type")

        return value

    @staticmethod
    def create_app(
        instance_type: str, client_name: str, api_base_url: str, to_file: str
    ) -> tuple:
        return MastodonHelper.WRAPPER[instance_type].create_app(
            client_name=client_name, api_base_url=api_base_url, to_file=to_file
        )
