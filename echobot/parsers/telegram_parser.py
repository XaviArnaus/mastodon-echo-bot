from pyxavi.config import Config
from pyxavi.storage import Storage
from echobot.lib.queue import Queue
from telethon import TelegramClient
from telethon.types import Message as TelegramMessage
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz
import math
import copy
from hashlib import sha1


class TelegramParser:

    MAX_MEDIA_PER_STATUS = 4
    MAX_STATUS_LENGTH = 400
    DATE_FORMAT = "%Y-%m-%d"
    DEFAULT_TELEGRAM_FILE = "storage/telegram.yaml"

    _telegram: TelegramClient

    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
        self._chats_storage = Storage(
            self._config.get("telegram_parser.storage_file", self.DEFAULT_TELEGRAM_FILE)
        )
        self._queue = Queue(config)

    def telegram_ok(self) -> None:
        self._telegram.get_me()

    def initialize_client(self) -> TelegramClient:
        api_id = self._config.get("telegram_parser.api_id")
        api_hash = self._config.get("telegram_parser.api_hash")
        session_name = self._config.get(
            "telegram_parser.session_name", self._config.get("app.name", "echo bot")
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

        # Initialize Client
        self._telegram = self.initialize_client()

        # We only need the chat IDs to then retrieve later the Entities.
        chat_ids = list(
            filter(bool, [abs(chat["id"]) if "id" in chat else False for chat in chats])
        )
        # Also, build a dict for the configuration
        chats_params = {}
        for chat in chats:
            chats_params[str(abs(chat["id"]))] = chat

        # Get the entities that match with the given IDs.
        self._logger.info("Get matching entities from the current user's dialogs")
        entities = list(
            filter(
                bool,
                [
                    dialog.entity if dialog.entity.id in chat_ids else False
                    for dialog in self._telegram.iter_dialogs()
                ]
            )
        )

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
            offset_date = datetime.strptime(offset_date, self.DATE_FORMAT)

            # First we get all messages in queue.
            # We must use the iter_messages to avoid using asyncs
            messages_to_post = []
            # Retrieving messages:
            #   reverse=True -> from oldest to newest, to keep the posting order
            #   offset_id -> avoid retrieving messages that we already know
            #   offset_date -> avoid retrieving messages older than the given datetime
            self._logger.info(f"Getting messages for entity {entity.title}")
            for message in self._telegram.iter_messages(
                    entity=entity,
                    reverse=True,
                    offset_id=max(seen_message_ids)
                    if seen_message_ids and not ignore_offsets else 0,
                    offset_date=offset_date if not ignore_offsets else None):
                # Theoreticaly we don't need to check again the seen message IDs, but...
                if message.id in seen_message_ids and not ignore_offsets:
                    self._logger.info(f"Discarding message: already seen {message.id}")
                    continue

                # We don't want anything older than 6 months
                if datetime.now().replace(tzinfo=pytz.UTC) - relativedelta(months=6
                                                                           ) > message.date:
                    self._logger.info(f"Discarding message: too old {message.date}")
                    continue

                # We don´t want any message that is empty and also does not contain any media
                if (message.text is None or message.text == "") \
                   and (message.file is None):
                    self._logger.info(f"Discarding message: no text or media {message.date}")
                    continue

                # If reached until here, we want this message
                messages_to_post.append(message)

                # Remember this message
                if message.id not in seen_message_ids:
                    seen_message_ids.append(message.id)

            # Store the new seen value. In the worst case it is the same as before.
            self._chats_storage.set(f"entity_{entity.id}", seen_message_ids)
            self._chats_storage.write_file()

            self._logger.info(f"Done. Received {len(messages_to_post)} messages to be posted.")

            if len(messages_to_post) > 0:
                # Now we need to group messages, as images are sent one per message,
                # if we have an original message with several pictures we'll receive
                # several messages with one picture with a very short time in between.
                self._logger.info("Grouping the messages.")
                grouped_messages = self.group_messages(messages=messages_to_post)
                self._logger.info(f"Done. {len(grouped_messages)} groups of messages.")

                # Lastly we loop the grouped messages and send each group to be posted,
                # which means an async task that downloads all possible meadia, builds and
                # formats the posts and sends them to the Mastodon API
                self._logger.info("Starting post preparation process")
                for group_of_messages in grouped_messages:

                    # From here on we make it async, because we need the media downloaded
                    # and attached to the message, and the lib functions are async.
                    self._logger.info(
                        f"Preparing group of {len(group_of_messages)} message(s)."
                    )
                    self.post_group_of_messages(
                        messages=group_of_messages,
                        entity=entity,
                        chat_params=chats_params[str(entity.id)]
                    )

        self._logger.debug("Done")

    def group_messages(self, messages: list[TelegramMessage]) -> list[list]:
        groups = []
        current_group = []
        last_message = None
        for message in messages:
            # If we don't have a last message, it's the first message
            if last_message is None:
                self._logger.debug(f"Message {message.date} is the first one. Creating group.")
                last_message = message
                current_group.append(message)
            else:
                # This is a new group if (with OR):
                # - The date diff between last message and this message is more than a minute.
                # - This message has text
                if last_message.date + timedelta(0, 0, 0, 0, 1) < message.date \
                   or (message.text is not None and len(message.text) > 0):
                    # We need to close the current group and start a new one
                    self._logger.debug(
                        f"Message {message.date} requires a new group. Creating."
                    )
                    groups.append(current_group)
                    current_group = []

                # Now add this message to the current group.
                # It will be a new group if the previous check reset it.
                self._logger.debug(
                    f"Added {message.date} into a group that has {len(current_group)} elements"
                )
                current_group.append(message)
                last_message = message

        # Outside the loop, if we still have a current group, we merge it.
        groups.append(current_group)

        return groups

    def post_group_of_messages(
        self, messages: list[TelegramMessage], entity, chat_params: dict
    ):
        """
        Do all the work to post a group of messages:
        - Download the media in all messages
        - Build the body of the post
        - Maybe even split the posting status into several posts due to length or amount of pics
        """

        # Go through all messages and get all text and all media
        text = ""
        media_stack = []
        status_date = None
        for message in messages:
            self._logger.debug(f"Message {message.id} in group")
            # First of all download the possible media
            if message.file is not None:
                file_name = str(message.file.media.id)\
                 if message.file.name is None else message.file.name

                filename = f"storage/media/{file_name}{message.file.ext}"
                self._logger.debug(f"Downloading media to {filename}")
                path = self._telegram.loop.run_until_complete(
                    self._download_media(message=message, filename=filename)
                )
                media_stack.append({"path": path, "mime_type": message.file.mime_type})

            # Now add the text to the text stack
            if message.text is not None and len(message.text) > 0:
                if len(text) > 0:
                    text += "\n\n"
                text += message.text

            if status_date is None:
                status_date = message.date

        # Now, we split based on:
        # - The text may be too long
        # - The amount of media is more than 4 items
        num_of_statuses_by_text = num_of_statuses_by_media = 1
        if len(media_stack) > self.MAX_MEDIA_PER_STATUS:
            num_of_statuses_by_media = math.ceil(len(media_stack) / self.MAX_MEDIA_PER_STATUS)
        if len(text) > self.MAX_STATUS_LENGTH:
            num_of_statuses_by_text = math.ceil(len(text) / self.MAX_STATUS_LENGTH)
        num_of_statuses = max(num_of_statuses_by_text, num_of_statuses_by_media)
        self._logger.debug(
            f"Ideal num of status: {num_of_statuses_by_text} for text" +
            f" and {num_of_statuses_by_media} for media." +
            f" Generating {num_of_statuses} statuses"
        )
        identification = sha1(text.encode()).hexdigest()
        self._logger.debug(f"This group of status has the ID: {identification}")
        for idx in range(num_of_statuses):
            status_num = idx + 1

            # Take as max media as possible from the stack
            media_to_post = []
            while media_stack:
                media_to_post.append(media_stack.pop(0))
                if len(media_to_post) >= self.MAX_MEDIA_PER_STATUS:
                    break

            # Take as max text as possible from the stack
            text_to_post = text[0:self.MAX_STATUS_LENGTH]
            # Leave the remaining text
            text = text[self.MAX_STATUS_LENGTH:]

            self._queue.append(
                {
                    "status": self._format_status(
                        text=text_to_post,
                        current_index=status_num,
                        total=num_of_statuses,
                        entity=entity,
                        show_name=chat_params["show_name"]
                        if "show_name" in chat_params and chat_params else False
                    ),
                    "media": media_to_post if media_to_post else None,
                    "language": chat_params["language"] or "en_US",
                    "published_at": copy.deepcopy(status_date),
                    "action": "new",
                    "group_id": identification
                }
            )

        # Update the toots queue, by adding the new ones at the end of the list
        self._queue.update()

    def _format_status(
        self, text: str, current_index: int, total: int, entity, show_name: bool
    ) -> str:
        result = f"{entity.title}:\n\n" if show_name else ""
        result += f"{text}"

        # Add the message counter
        if total > 1:
            if len(result) > 0:
                result += "\n\n"
            result += f"({current_index}/{total})"

        return result

    async def _download_media(self, message: TelegramMessage, filename: str) -> None:
        # Download the media. Returns the path where it finally got downloaded.
        path = await self._telegram.download_media(message=message, file=filename)
        self._logger.debug(f"File {filename} has been downloaded")
        return path
