from pyxavi.config import Config
from pyxavi.storage import Storage
from telethon import TelegramClient
from telethon.types import Message as TelegramMessage
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz
from pyxavi.debugger import dd


class TelegramParser:

    _telegram: TelegramClient
    
    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
        self._toots_queue = Storage(self._config.get("toots_queue_storage.file"))
        self._chats_storage = Storage(self._config.get("telegram_parser.storage_file"))
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
        # Chats and channels are managed equally, but under different entities.
        chats = self._config.get("telegram_parser.chats", [])
        chats += self._config.get("telegram_parser.channels", [])

        if not chats:
            self._logger.info("No Telegram conversations registered to parse, skipping,")
            return
        else:
            # We only need the chat IDs to then retrieve later the Entities.
            chats = list(filter(bool,[abs(chat["id"]) if "id" in chat else False for chat in chats]))
        
        # Get the entities that match with the given IDs.
        self._logger.info(f"Get matching entities from the current user's dialogs")
        entities = list(filter(bool,[
            dialog.entity if dialog.entity.id in chats else False\
                for dialog in self._telegram.iter_dialogs()
        ]))

        # If no entities found, return.
        logger_string = f"Got {len(entities)} entities."
        if not entities:
            logger_string += " Returning."
            self._logger.info(logger_string)
            return
        self._logger.info(logger_string)

        # Now work with the messages for each entity
        for entity in entities:

            # Shall we ignore the offsets?
            ignore_offsets = self._config.get("telegram_parser.ignore_offsets", False)

            # We have to control what did we already see, to avoid duplicates
            seen_message_ids = list(self._chats_storage.get(f"entity_{entity.id}", []))

            # Do we have defined a date to start from?
            offset_date = self._config.get("telegram_parser.date_to_start_from", None)

            # Retrieving messages:
            #   reverse=True -> from oldest to newest, to keep the posting order
            #   offset_id -> avoid retrieving messages that we already know
            #   offset_date -> avoid retrieving messages older than the given datetime
            self._logger.info(f"Getting messages for entity {entity.title}")
            for message in self._telegram.iter_messages(
                entity=entity,
                reverse=True,
                offset_id=max(seen_message_ids) if seen_message_ids and not ignore_offsets else 0,
                offset_date=offset_date if not ignore_offsets else None
            ):
                # Theoreticaly we don't need to check again the seen message IDs, but...
                if message.id in seen_message_ids and not ignore_offsets:
                    self._logger.info(f"Discarding message: already seen {message.id}")
                    continue

                # We don't want anything older than 6 months
                if datetime.now().replace(tzinfo=pytz.UTC) - relativedelta(months=6) > message.date:
                    self._logger.info(f"Discarding message: too old {message.date}")
                    continue

                # Prepare the new toot
                filename = f"storage/media/{datetime.now().timestamp()}"
                self._telegram.loop.run_until_complete(
                    self._parse_media(
                        message=message,
                        filename=filename
                    )
                )
                # self._queue.append(
                #     {
                #         "status": self._format_toot(post, site["name"],site),
                #         "media": media if media else None,
                #         "language": metadata["language"],
                #         "published_at": post_date,
                #         "action": "new"
                #     }
                # )


                dd(message.id)
                dd(message.text)
                dd(message.date)
                dd(filename)    

                # Remember this message
                seen_message_ids.append(message.id)

            # Store the new seen value. In the worst case it is the same as before.
            self._chats_storage.set(f"entity_{entity.id}", seen_message_ids)
            self._chats_storage.write_file()

        
        self._logger.debug("Done")

    async def _parse_media(self, message: TelegramMessage, filename: str):

        # Initiate
        result = []

        # Download the media
        path = await self._telegram.download_media(
            message=message,
            file=filename
        )
        #images = self._telegram.download_media(message=message)
        dd(path)

        # if path:
        #     result.append(
        #         {
        #             "url": path,
        #             "alt_text": None
        #         }
        #     )

        # return result