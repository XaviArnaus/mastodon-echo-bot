from pyxavi.config import Config
import telebot
import logging
from ..debugger import dd

class TelegramParser:

    _telegram: telebot.TeleBot
    
    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
        self._telegram = self.initialize_client()
        self.telegram_ok()
    
    @property
    def telegram(self) -> telebot.TeleBot:
        return self._telegram
    
    def telegram_ok(self) -> None:
        self._telegram.get_me()
    
    def initialize_client(self) -> telebot.TeleBot:
        #api_id = self._config.get("telegram_parser.api_id")
        #api_hash = self._config.get("telegram_parser.api_hash")
        bot_token = self._config.get("telegram_parser.bot_token")
        #session_name = self._config.get("telegram_parser.session_name", self._config.get("app.name", "echo bot"))

        self._logger.debug("Setting up Telegram Bot and handler...")
        bot = telebot.TeleBot(bot_token)

        # @bot.channel_post_handler()
        # def channel_message_handle(message) -> None:
        #     print(message.chat.id, message.text)

        self._logger.debug("Done")

        return bot

    def parse(self) -> None:
        """
        The Telegram wrapper is reactive. You can't parse a list of messages but
        react on an incomming message.
        """
        channels = self._config.get("telegram_parser.channels", [])
        # for channel in channels:
        #     channel_name = channel["name"]
        #     self._logger.info(f"Getting messages from chat {channel_name}")
        #     # From most-recent to oldest
        #     for message in self._client.iter_messages(channel_name):
        #         print(message.id, message.text)
        
        self._logger.debug("Getting Updates")
        # https://core.telegram.org/bots/api#getupdates
        updates = self._telegram.get_updates(
            offset=0,
            timeout=300
        )
        dd(updates)
        self._logger.debug(f"Received {len(updates)} updates")
        for update in updates:
            if "message" in update and update["message"] is not None:
                self._logger.debug("Received a message!")
                # https://core.telegram.org/bots/api#message
                print(update["message"].id, update["message"].text)
        self._logger.debug("Done")


class TelegramExceptionHandler(telebot.ExceptionHandler):

    def __init__(self, config: Config):
        self._logger = logging.getLogger(config.get("logger.name"))
        super.__init__()

    def handle(self, exception: Exception) -> bool:
        self._logger.exception(exception)
        return True


