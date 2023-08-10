from pyxavi.config import Config
from pyxavi.storage import Storage
from telethon import TelegramClient
from telethon.utils import get_input_channel, get_input_peer
# from telethon.tl.functions.channels import TypeInputChannel
from telethon.tl.types import InputPeerChannel
from telethon.tl.types import ChannelMessagesFilter
import logging
from pyxavi.debugger import dd


class TelegramParser:

    _telegram: TelegramClient
    
    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
        self._toots_queue = Storage(self._config.get("toots_queue_storage.file"))
        self._feeds_storage = Storage(self._config.get("telegram_parser.storage_file"))
        self._telegram = self.initialize_client()
    
    def telegram_ok(self) -> None:
        self._telegram.get_me()
    
    def initialize_client(self) -> TelegramClient:
        api_id = self._config.get("telegram_parser.api_id")
        api_hash = self._config.get("telegram_parser.api_hash")
        session_name = self._config.get(
            "telegram_parser.session_name",
            self._config.get("app.name", "echo bot")
        )

        self._logger.debug("Setting up Telegram Client, reusing if exists...")
        client = TelegramClient(session_name, api_id, api_hash).start()
        self._logger.debug("Done")

        return client

    def parse(self) -> None:
        """
        The Telegram wrapper is reactive. You can't parse a list of messages but
        react on an incomming message.
        """
        channels = self._config.get("telegram_parser.channels", [])

        if not channels:
            self._logger.info("No Telegram channels registered to parse, skipping,")
            return

        for channel in channels:
            channel_name = channel["name"]
            channel_id = channel["id"]

            self._logger.info(f"Getting possible stored data for {channel_name}")
            channel_data = self._feeds_storage.get_hashed(str(channel_id), None)

            # Print all dialog IDs and the title, nicely formatted
            self._logger.info(f"Print all dialog IDs and the title")
            for dialog in self._telegram.iter_dialogs():
                # print('{:>14}: {}'.format(dialog.id, dialog.title))
                if dialog.id == channel_id:
                    dd(dialog.title)

            # self._logger.info("Get all dialogs of the acount")
            # dialogs = self._telegram.get_dialogs()
            # for dialog in dialogs:
            #     dd(dialog.title)

            # self._logger.info(f"Getting the channel entity for {channel_name}")
            # entity = self._telegram.get_entity(channel_id)
            # dd(entity)

            self._logger.info(f"Getting messages from chat {channel_name}")
            # From most-recent to oldest
            # "peer_id": (PeerChannel){"channel_id": (int)1668477107}
            #input_channel = get_input_channel(get_input_peer(channel_id))
            for message in self._telegram.iter_messages(
                channel_id,
                reverse=True,
                #filter=ChannelMessagesFilter()
            ):
                dd(message.id)
                dd(message.text)
                dd(message.date)
        
        self._logger.debug("Done")