from pyxavi.config import Config
from pyxavi.storage import Storage
from echobot.lib.queue_post import QueuePost, QueuePostMedia
from echobot.parsers.parser_protocol import ParserProtocol
from echobot.parsers.telegram_parser import TelegramParser
from telethon import TelegramClient
from datetime import datetime
from time import localtime
from dateutil import parser
from unittest.mock import patch, Mock, MagicMock, call
from unittest import TestCase
import pytest
from logging import Logger as BuiltInLogger
import copy
import math
from hashlib import sha1
from string import Template
from pyxavi.debugger import dd
import asyncio

pytest_plugins = ('pytest_asyncio',)

CONFIG = {
    "logger": {
        "name": "custom_logger"
    },
    "telegram_parser": {
        "storage_file": "telegram.yaml",
        "api_id": "123",
        "api_hash": "abcdef1234567890",
        "ignore_offsets": False,
        "channels": [
            {
                "id": -12345678,
                "name": "News",
                "show_name": True
            }
        ]
    }
}

# This keeps the state of already seen
TELEGRAM = {}

# We want to make sure that we have the TelegramClient mocked
_mock_telegram_client_instance = Mock(name="MockTelegramClient")
_mock_telegram_client_instance.__class__ = TelegramClient

class EntityFake:

    id: int

    def __init__(self, id: int) -> None:
        self.id = id

class DialogFake:

    entity: EntityFake

    def __init__(self, entity: EntityFake) -> None:
        self.entity = entity

class MediaFake:

    id: str

    def __init__(self, id: str) -> None:
        self.id = id

class FileFake:

    name: str
    ext: str
    mime_type: str
    media: MediaFake

    def __init__(
        self,
        name: str = None,
        ext: str = None,
        mime_type: str = None,
        media: MediaFake = None
    ) -> None:
        self.name = name
        self.ext = ext
        self.mime_type = mime_type
        self.media = media
        

class MessageFake:
    
    id: int
    text: str
    date: datetime
    file: FileFake

    def __init__(
        self,
        id: int,
        date: datetime,
        text: str = None,
        file: FileFake = None
    ) -> None:
        self.id = id
        self.date = date
        self.text = text
        self.file = file


@pytest.fixture(autouse=True)
def setup_function():

    global CONFIG,TELEGRAM

    backup_config = copy.deepcopy(CONFIG)
    backup_feeds = copy.deepcopy(TELEGRAM)

    yield

    TELEGRAM = backup_feeds
    CONFIG = backup_config


def get_a_dialog_instance(params: dict) -> DialogFake:
    
    entity = EntityFake(id=params["entity"]["id"])
    dialog = DialogFake(entity=entity)

    return dialog

def get_a_message_instance(params: dict) -> MessageFake:

    media = None
    file = None

    if "media" in params:
        # If there is a file, it should be always a media with it's id
        media = MediaFake(id=params["media"]["id"])
    if "file" in params:
        # If there is a file, not always need to be a file.name
        file = FileFake(
            name=params["file"]["name"] if "name" in params["file"] else None,
            ext=params["file"]["ext"] if "ext" in params["file"] else None,
            mime_type=params["file"]["mime_type"] if "mime_type" in params["file"] else None,
            media=media if media else None,
        )
    message = MessageFake(
        id=params["message"]["id"],
        date=params["message"]["date"],
        text=params["message"]["text"] if "text" in params["message"] else None,
        file=file if file else None,
    )
    return message

def get_a_queue_post_instance(message: MessageFake, dialog: DialogFake, language: str) -> QueuePost:
    return QueuePost(
        id=message.id,
        raw_content={
            "telegram_message": message,
            "telegram_entity": dialog.entity
        },
        raw_combined_content=message.text,
        published_at=message.date,
        language=language
    ) 

def get_a_final_queue_post_instance(params: dict) -> QueuePost:
    return QueuePost(
        id=sha1(str(params["text"]).encode()).hexdigest(),
        raw_content={
            "body": params["text"],
            "telegram_media_messages": params["media"] if "media" in params and params["media"] else []
        },
        group=params["identification"],
        published_at=params["date"],
        language=params["language"]
    ) 

def patch_storage_read_file(self):
    self._content = TELEGRAM

@patch.object(Storage, "read_file", new=patch_storage_read_file)
def get_instance() -> TelegramParser:
    config = Config(params=CONFIG)

    mock_telegram_client_start = Mock()
    mock_telegram_client_start.return_value = _mock_telegram_client_instance
    with patch.object(TelegramParser, "_initialize_client", new=mock_telegram_client_start):
        telegram_parser = TelegramParser(config=config)
    
    mock_telegram_client_start.assert_called_once()
    assert telegram_parser._telegram == _mock_telegram_client_instance

    return telegram_parser

def test_instantiation():

    instance = get_instance()

    assert isinstance(instance, TelegramParser)
    assert isinstance(instance, ParserProtocol)
    assert isinstance(instance._config, Config)
    assert isinstance(instance._logger, BuiltInLogger)
    assert isinstance(instance._chats_storage, Storage)
    assert instance._sources == {
        CONFIG["telegram_parser"]["channels"][0]["name"]: CONFIG["telegram_parser"]["channels"][0]
    }
    assert instance._sources_name_to_id == {
        CONFIG["telegram_parser"]["channels"][0]["name"]: str(abs(CONFIG["telegram_parser"]["channels"][0]["id"]))
    }

def test_get_sources():
    instance = get_instance()

    assert instance.get_sources() == {
        CONFIG["telegram_parser"]["channels"][0]["name"]: CONFIG["telegram_parser"]["channels"][0]
    }

def test_get_raw_content_for_source_no_entities_at_all_incoming():
    source = CONFIG["telegram_parser"]["channels"][0]["name"]

    instance = get_instance()

    # Returning an enntity that is not what we're looking for.
    mocked_telegram_iter_dialogs = MagicMock()
    mocked_telegram_iter_dialogs.__iter__.return_value = []
    _mock_telegram_client_instance.iter_dialogs = Mock()
    _mock_telegram_client_instance.iter_dialogs.return_value = mocked_telegram_iter_dialogs

    # Run it
    raw_content = instance.get_raw_content_for_source(source)
    
    _mock_telegram_client_instance.iter_dialogs.assert_called_once()
    assert raw_content == []

def test_get_raw_content_for_source_no_matching_entities_incoming():
    source = CONFIG["telegram_parser"]["channels"][0]["name"]

    instance = get_instance()

    # Returning an entity that is not what we're looking for.
    mocked_telegram_iter_dialogs = MagicMock()
    mocked_telegram_iter_dialogs.__iter__.return_value = [
        get_a_dialog_instance({"entity": {"id": 123}})
    ]
    _mock_telegram_client_instance.iter_dialogs = Mock()
    _mock_telegram_client_instance.iter_dialogs.return_value = mocked_telegram_iter_dialogs

    # Run it
    raw_content = instance.get_raw_content_for_source(source)
    
    _mock_telegram_client_instance.iter_dialogs.assert_called_once()
    assert raw_content == []

def test_get_raw_content_for_source_bad_source():
    source = "wrong"

    instance = get_instance()

    with TestCase.assertRaises(instance, RuntimeError):
        _ = instance.get_raw_content_for_source(source)

@pytest.fixture
def message_1():
    # Message with text and without file
    return get_a_message_instance({
        "message": {
            "id": 1111,
            "date": datetime(2024, 1, 1, 16, 00, 00),
            "text": "I am a message"
        }
    })

@pytest.fixture
def message_2():
    # Message with text and with file with filename
    return get_a_message_instance({
        "message": {
            "id": 2222,
            "date": datetime(2024, 1, 2, 16, 5, 00),
            "text": "I am a message 2"
        },
        "file": {
            "name": "filename2",
            "ext": "jpg",
            "mime_type": "image/jpg",
        },
        "media": {
            "id": "original_filename_2"
        }
    })

@pytest.fixture
def message_3():
    # Message with text and with file without filename
    return get_a_message_instance({
        "message": {
            "id": 3333,
            "date": datetime(2024, 1, 3, 16, 10, 00),
            "text": "I am a message 3"
        },
        "file": {
            "ext": "jpg",
            "mime_type": "image/jpg",
        },
        "media": {
            "id": "original_filename_3"
        }
    })

@pytest.fixture
def message_4():
    # Message without text and with file without filename
    return get_a_message_instance({
        "message": {
            "id": 4444,
            "date": datetime(2024, 1, 4, 16, 15, 00),
        },
        "file": {
            "ext": "jpg",
            "mime_type": "image/jpg",
        },
        "media": {
            "id": "original_filename_4"
        }
    })

@pytest.fixture
def message_5():
    # Message with text and without file, with same date as 1111
    #   It is used to show that 2 messages in the same date won't be bounded
    #   as long as both contain text (they are 2 separated messages!)
    return get_a_message_instance({
        "message": {
            "id": 5555,
            "date": datetime(2024, 1, 1, 16, 00, 00),
            "text": "I am NOT TO BE bounded to message 1"
        }
    })

@pytest.fixture
def message_6():
    # Message without text and with file, with same date as 1111
    #   It is used to show that 2 messages in the same date will be bounded
    #   as one contain text and the other an image (only)
    return get_a_message_instance({
        "message": {
            "id": 6666,
            "date": datetime(2024, 1, 1, 16, 00, 00),
        },
        "file": {
            "ext": "jpg",
            "mime_type": "image/jpg",
        },
        "media": {
            "id": "original_filename_6"
        }
    })

@pytest.fixture
def message_7():
    # Message with text and without file, will be split in several posts
    #   The test has to have a small max_length!
    return get_a_message_instance({
        "message": {
            "id": 7777,
            "date": datetime(2024, 1, 1, 16, 00, 00),
            "text": "I am meant to be split. I am meant to be split. "\
                "I am meant to be split. I am meant to be split. "\
                "I am meant to be split. I am meant to be split. "\
                "I am meant to be split. I am meant to be split. "\
                "I am meant to be split. I am meant to be split. "\
                "I am meant to be split. I am meant to be split. "\
                "I am meant to be split. I am meant to be split. "\
                "I am meant to be split. I am meant to be split. "\
                "I am meant to be split. I am meant to be split. "\
                "I am meant to be split. I am meant to be split. "\
                "I am meant to be split. I am meant to be split. "\
                "I am meant to be split. I am meant to be split. "\
                "I am meant to be split. I am meant to be split. "
        }
    })

def test_get_raw_content_for_source_not_yet_offset(message_1, message_2, message_3, message_4):

    CONFIG["telegram_parser"]["channels"][0]["language"] = "ca_ES"

    source = CONFIG["telegram_parser"]["channels"][0]["name"]
    entity_id = str(abs(CONFIG["telegram_parser"]["channels"][0]["id"]))
    dialog = get_a_dialog_instance({"entity": {"id": entity_id}})
    messages = [message_1, message_2, message_3, message_4]
    channel_language = CONFIG["telegram_parser"]["channels"][0]["language"]

    instance = get_instance()

    expected_messages = [
        get_a_queue_post_instance(
            message=message_1,
            dialog=dialog,
            language=channel_language
        ),
        get_a_queue_post_instance(
            message=message_2,
            dialog=dialog,
            language=channel_language
        ),
        get_a_queue_post_instance(
            message=message_3,
            dialog=dialog,
            language=channel_language
        ),
        get_a_queue_post_instance(
            message=message_4,
            dialog=dialog,
            language=channel_language
        ),
    ]

    # Mock iter_dialogs to return a matching entity
    mocked_telegram_iter_dialogs = MagicMock()
    mocked_telegram_iter_dialogs.__iter__.return_value = [dialog]
    _mock_telegram_client_instance.iter_dialogs = Mock()
    _mock_telegram_client_instance.iter_dialogs.return_value = mocked_telegram_iter_dialogs

    # Mock iter_messages to return a set of messages
    mocked_telegram_iter_messages = MagicMock()
    mocked_telegram_iter_messages.__iter__.return_value = messages
    _mock_telegram_client_instance.iter_messages = Mock()
    _mock_telegram_client_instance.iter_messages.return_value = mocked_telegram_iter_messages

    # Run it!
    raw_content = instance.get_raw_content_for_source(source)
    
    _mock_telegram_client_instance.iter_dialogs.assert_called_once()
    _mock_telegram_client_instance.iter_messages.assert_called()
    _mock_telegram_client_instance.iter_messages.assert_called_once_with(
        entity=dialog.entity,
        reverse=True,
        offset_id=0,
        offset_date=None
    )

    for idx in range(0,len(expected_messages)):
        assert isinstance(raw_content[idx], QueuePost)
        assert raw_content[idx].id == expected_messages[idx].id
        assert raw_content[idx].raw_content == expected_messages[idx].raw_content
        assert raw_content[idx].raw_combined_content == expected_messages[idx].raw_combined_content
        assert raw_content[idx].published_at == expected_messages[idx].published_at
        assert raw_content[idx].language == expected_messages[idx].language

def test_get_raw_content_for_source_date_offset(message_2, message_3, message_4):

    CONFIG["telegram_parser"]["date_to_start_from"] = "2024-01-02"
    CONFIG["telegram_parser"]["channels"][0]["language"] = "ca_ES"

    source = CONFIG["telegram_parser"]["channels"][0]["name"]
    entity_id = str(abs(CONFIG["telegram_parser"]["channels"][0]["id"]))
    dialog = get_a_dialog_instance({"entity": {"id": entity_id}})
    messages = [message_2, message_3, message_4]
    channel_language = CONFIG["telegram_parser"]["channels"][0]["language"]

    instance = get_instance()

    # We don't expect to receive the first message
    #   Of course, the filtering happens inside the method
    #   so here we're faking it.
    expected_messages = [
        get_a_queue_post_instance(
            message=message_2,
            dialog=dialog,
            language=channel_language
        ),
        get_a_queue_post_instance(
            message=message_3,
            dialog=dialog,
            language=channel_language
        ),
        get_a_queue_post_instance(
            message=message_4,
            dialog=dialog,
            language=channel_language
        ),
    ]

    # Mock iter_dialogs to return a matching entity
    mocked_telegram_iter_dialogs = MagicMock()
    mocked_telegram_iter_dialogs.__iter__.return_value = [dialog]
    _mock_telegram_client_instance.iter_dialogs = Mock()
    _mock_telegram_client_instance.iter_dialogs.return_value = mocked_telegram_iter_dialogs

    # Mock iter_messages to return a set of messages
    mocked_telegram_iter_messages = MagicMock()
    mocked_telegram_iter_messages.__iter__.return_value = messages
    _mock_telegram_client_instance.iter_messages = Mock()
    _mock_telegram_client_instance.iter_messages.return_value = mocked_telegram_iter_messages

    # Run it!
    raw_content = instance.get_raw_content_for_source(source)
    
    _mock_telegram_client_instance.iter_dialogs.assert_called_once()
    _mock_telegram_client_instance.iter_messages.assert_called()
    _mock_telegram_client_instance.iter_messages.assert_called_once_with(
        entity=dialog.entity,
        reverse=True,
        offset_id=0,
        offset_date=datetime(2024, 1, 2, 0, 0)
    )
    
    for idx in range(0,len(expected_messages)):
        assert isinstance(raw_content[idx], QueuePost)
        assert raw_content[idx].id == expected_messages[idx].id
        assert raw_content[idx].raw_content == expected_messages[idx].raw_content
        assert raw_content[idx].raw_combined_content == expected_messages[idx].raw_combined_content
        assert raw_content[idx].published_at == expected_messages[idx].published_at
        assert raw_content[idx].language == expected_messages[idx].language

def test_get_raw_content_for_source_no_offset_default_language(message_1, message_2, message_3, message_4):

    source = CONFIG["telegram_parser"]["channels"][0]["name"]
    entity_id = str(abs(CONFIG["telegram_parser"]["channels"][0]["id"]))
    dialog = get_a_dialog_instance({"entity": {"id": entity_id}})
    messages = [message_1, message_2, message_3, message_4]

    instance = get_instance()

    expected_messages = [
        get_a_queue_post_instance(
            message=message_1,
            dialog=dialog,
            language=instance.DEFAULT_LANGUAGE
        ),
        get_a_queue_post_instance(
            message=message_2,
            dialog=dialog,
            language=instance.DEFAULT_LANGUAGE
        ),
        get_a_queue_post_instance(
            message=message_3,
            dialog=dialog,
            language=instance.DEFAULT_LANGUAGE
        ),
        get_a_queue_post_instance(
            message=message_4,
            dialog=dialog,
            language=instance.DEFAULT_LANGUAGE
        ),
    ]

    # Mock iter_dialogs to return a matching entity
    mocked_telegram_iter_dialogs = MagicMock()
    mocked_telegram_iter_dialogs.__iter__.return_value = [dialog]
    _mock_telegram_client_instance.iter_dialogs = Mock()
    _mock_telegram_client_instance.iter_dialogs.return_value = mocked_telegram_iter_dialogs

    # Mock iter_messages to return a set of messages
    mocked_telegram_iter_messages = MagicMock()
    mocked_telegram_iter_messages.__iter__.return_value = messages
    _mock_telegram_client_instance.iter_messages = Mock()
    _mock_telegram_client_instance.iter_messages.return_value = mocked_telegram_iter_messages

    # Run it!
    raw_content = instance.get_raw_content_for_source(source)
    
    _mock_telegram_client_instance.iter_dialogs.assert_called_once()
    _mock_telegram_client_instance.iter_messages.assert_called()
    _mock_telegram_client_instance.iter_messages.assert_called_once_with(
        entity=dialog.entity,
        reverse=True,
        offset_id=0,
        offset_date=None
    )

    for idx in range(0,len(expected_messages)):
        assert isinstance(raw_content[idx], QueuePost)
        assert raw_content[idx].id == expected_messages[idx].id
        assert raw_content[idx].raw_content == expected_messages[idx].raw_content
        assert raw_content[idx].raw_combined_content == expected_messages[idx].raw_combined_content
        assert raw_content[idx].published_at == expected_messages[idx].published_at
        assert raw_content[idx].language == expected_messages[idx].language


def test_is_id_already_seen_for_source_no_stack():
    
    source = CONFIG["telegram_parser"]["channels"][0]["name"]
    
    instance = get_instance()

    assert instance.is_id_already_seen_for_source(source, 123) == False

def test_is_id_already_seen_for_source_match():
    global TELEGRAM

    source = CONFIG["telegram_parser"]["channels"][0]["name"]
    entity_id = str(abs(CONFIG["telegram_parser"]["channels"][0]["id"]))
    message_id = 123

    TELEGRAM = {
        f"entity_{entity_id}": [message_id]
    }
    
    instance = get_instance()
    
    assert instance.is_id_already_seen_for_source(source, message_id) == True

def test_is_id_already_seen_for_source_not_match():
    source = CONFIG["telegram_parser"]["channels"][0]["name"]
    entity_id = str(abs(CONFIG["telegram_parser"]["channels"][0]["id"]))
    message_id = 123
    
    instance = get_instance()
    instance._chats_storage.set(
        param_name=f"entity_{entity_id}",
        value=[message_id+1]
    )
    
    assert instance.is_id_already_seen_for_source(source, message_id) == False

def test_set_ids_as_seen_for_source_from_scratch():
    source = CONFIG["telegram_parser"]["channels"][0]["name"]
    id1 = 111
    id2 = 222
    id3 = 333
    id4 = 444

    instance = get_instance()

    assert instance.is_id_already_seen_for_source(source, id1) is False
    assert instance.is_id_already_seen_for_source(source, id2) is False
    assert instance.is_id_already_seen_for_source(source, id3) is False
    assert instance.is_id_already_seen_for_source(source, id4) is False

    mocked_storage_write_file = Mock()
    with patch.object(Storage, "write_file", new=mocked_storage_write_file):
        instance.set_ids_as_seen_for_source(source, [id1, id2, id3, id4])
    
    mocked_storage_write_file.assert_called_once()

    assert instance.is_id_already_seen_for_source(source, id1) is True
    assert instance.is_id_already_seen_for_source(source, id2) is True
    assert instance.is_id_already_seen_for_source(source, id3) is True
    assert instance.is_id_already_seen_for_source(source, id4) is True


def test_set_ids_as_seen_for_source_adding_some():
    global TELEGRAM

    source = CONFIG["telegram_parser"]["channels"][0]["name"]
    entity_id = str(abs(CONFIG["telegram_parser"]["channels"][0]["id"]))
    id1 = 111
    id2 = 222
    id3 = 333
    id4 = 444

    TELEGRAM = {
        f"entity_{entity_id}": [id1, id2]
    }

    instance = get_instance()

    assert instance.is_id_already_seen_for_source(source, id1) is True
    assert instance.is_id_already_seen_for_source(source, id2) is True
    assert instance.is_id_already_seen_for_source(source, id3) is False
    assert instance.is_id_already_seen_for_source(source, id4) is False

    mocked_storage_write_file = Mock()
    with patch.object(Storage, "write_file", new=mocked_storage_write_file):
        instance.set_ids_as_seen_for_source(source, [id3, id4])
    
    mocked_storage_write_file.assert_called_once()

    assert instance.is_id_already_seen_for_source(source, id1) is True
    assert instance.is_id_already_seen_for_source(source, id2) is True
    assert instance.is_id_already_seen_for_source(source, id3) is True
    assert instance.is_id_already_seen_for_source(source, id4) is True

def test_post_process_for_source_empty_list_do_nothing():

    posts = []

    instance = get_instance()

    assert instance.post_process_for_source("source", posts) == posts

def test_post_process_for_source_messages_are_ungrouped_due_to_date(message_1, message_2):

    source = CONFIG["telegram_parser"]["channels"][0]["name"]
    entity_id = str(abs(CONFIG["telegram_parser"]["channels"][0]["id"]))
    dialog = get_a_dialog_instance({"entity": {"id": entity_id}})

    instance = get_instance()
    
    posts = [
        get_a_queue_post_instance(
            message=message_1,
            dialog=dialog,
            language=instance.DEFAULT_LANGUAGE
        ),
        get_a_queue_post_instance(
            message=message_2,
            dialog=dialog,
            language=instance.DEFAULT_LANGUAGE
        ),
    ]

    expected_posts = [
        get_a_final_queue_post_instance({
            "text": message_1.text,
            "date": message_1.date,
            "identification": sha1(message_1.text.encode()).hexdigest(),
            "language": instance.DEFAULT_LANGUAGE
        }),
        get_a_final_queue_post_instance({
            "text": message_2.text,
            "date": message_2.date,
            "identification": sha1(message_2.text.encode()).hexdigest(),
            "language": instance.DEFAULT_LANGUAGE,
            "media": [message_2]
        })
    ]
    posts_to_publish = instance.post_process_for_source(source, posts)

    for idx in range(0,len(expected_posts)):
        assert isinstance(posts_to_publish[idx], QueuePost)
        assert posts_to_publish[idx].id == expected_posts[idx].id
        assert posts_to_publish[idx].raw_content["body"] == expected_posts[idx].raw_content["body"]
        assert posts_to_publish[idx].group == expected_posts[idx].group
        assert posts_to_publish[idx].published_at == expected_posts[idx].published_at
        assert posts_to_publish[idx].language == expected_posts[idx].language
        media_in_posts = posts_to_publish[idx].raw_content["telegram_media_messages"]
        media_in_expected_posts = expected_posts[idx].raw_content["telegram_media_messages"]
        assert len(media_in_posts) == len(media_in_expected_posts)
        if len(expected_posts[idx].raw_content["telegram_media_messages"]) > 0:
            for idx_media in range(0,len(media_in_expected_posts)):
                media_in_posts[idx_media].id == media_in_expected_posts[idx_media].id

def test_post_process_for_source_messages_are_ungrouped_due_to_text(message_1, message_5):

    source = CONFIG["telegram_parser"]["channels"][0]["name"]
    entity_id = str(abs(CONFIG["telegram_parser"]["channels"][0]["id"]))
    dialog = get_a_dialog_instance({"entity": {"id": entity_id}})

    instance = get_instance()
    
    posts = [
        get_a_queue_post_instance(
            message=message_1,
            dialog=dialog,
            language=instance.DEFAULT_LANGUAGE
        ),
        get_a_queue_post_instance(
            message=message_5,
            dialog=dialog,
            language=instance.DEFAULT_LANGUAGE
        ),
    ]

    expected_posts = [
        get_a_final_queue_post_instance({
            "text": message_1.text,
            "date": message_1.date,
            "identification": sha1(message_1.text.encode()).hexdigest(),
            "language": instance.DEFAULT_LANGUAGE
        }),
        get_a_final_queue_post_instance({
            "text": message_5.text,
            "date": message_5.date,
            "identification": sha1(message_5.text.encode()).hexdigest(),
            "language": instance.DEFAULT_LANGUAGE
        })
    ]
    posts_to_publish = instance.post_process_for_source(source, posts)

    for idx in range(0,len(expected_posts)):
        assert isinstance(posts_to_publish[idx], QueuePost)
        assert posts_to_publish[idx].id == expected_posts[idx].id
        assert posts_to_publish[idx].raw_content == expected_posts[idx].raw_content
        assert posts_to_publish[idx].group == expected_posts[idx].group
        assert posts_to_publish[idx].published_at == expected_posts[idx].published_at
        assert posts_to_publish[idx].language == expected_posts[idx].language

def test_post_process_for_source_messages_are_grouped_to_one(message_1, message_6):

    source = CONFIG["telegram_parser"]["channels"][0]["name"]
    entity_id = str(abs(CONFIG["telegram_parser"]["channels"][0]["id"]))
    dialog = get_a_dialog_instance({"entity": {"id": entity_id}})

    instance = get_instance()
    
    posts = [
        get_a_queue_post_instance(
            message=message_1,
            dialog=dialog,
            language=instance.DEFAULT_LANGUAGE
        ),
        get_a_queue_post_instance(
            message=message_6,
            dialog=dialog,
            language=instance.DEFAULT_LANGUAGE
        ),
    ]

    expected_posts = [
        get_a_final_queue_post_instance({
            "text": message_1.text,
            "date": message_1.date,
            "identification": sha1(message_1.text.encode()).hexdigest(),
            "language": instance.DEFAULT_LANGUAGE,
            "media": [message_6]
        })
    ]
    posts_to_publish = instance.post_process_for_source(source, posts)

    assert len(posts_to_publish) == 1
    for idx in range(0,len(expected_posts)):
        assert isinstance(posts_to_publish[idx], QueuePost)
        assert posts_to_publish[idx].id == expected_posts[idx].id
        assert posts_to_publish[idx].raw_content["body"] == expected_posts[idx].raw_content["body"]
        assert posts_to_publish[idx].group == expected_posts[idx].group
        assert posts_to_publish[idx].published_at == expected_posts[idx].published_at
        assert posts_to_publish[idx].language == expected_posts[idx].language
        media_in_posts = posts_to_publish[idx].raw_content["telegram_media_messages"]
        media_in_expected_posts = expected_posts[idx].raw_content["telegram_media_messages"]
        assert len(media_in_posts) == len(media_in_expected_posts)
        if len(expected_posts[idx].raw_content["telegram_media_messages"]) > 0:
            for idx_media in range(0,len(media_in_expected_posts)):
                media_in_posts[idx_media].id == media_in_expected_posts[idx_media].id

def test_post_process_for_source_long_message_is_split(message_7):

    # Let's force the split by setting short max length
    CONFIG["default"] = {"max_length": 56}

    source = CONFIG["telegram_parser"]["channels"][0]["name"]
    entity_id = str(abs(CONFIG["telegram_parser"]["channels"][0]["id"]))
    dialog = get_a_dialog_instance({"entity": {"id": entity_id}})

    instance = get_instance()
    
    posts = [
        get_a_queue_post_instance(
            message=message_7,
            dialog=dialog,
            language=instance.DEFAULT_LANGUAGE
        )
    ]

    expected_posts = []
    text = message_7.text
    status_num = 1
    max_status_length = instance._TelegramParser__calculate_max_status_length()
    num_of_statuses_by_text = math.ceil(len(text) / max_status_length)
    identification = sha1(text.encode()).hexdigest()
    while text:
        # The text is sliced and have the 1/n footer added.
        text_to_post = Template(instance.TEMPLATE_BODY_WITH_THREAD).substitute(
            body=text[0:max_status_length],
            thread=Template(instance.TEMPLATE_THREAD_INFO).substitute(
                current=status_num,
                total=num_of_statuses_by_text
            )
        )
        # Reduce the available text
        if len(text) > max_status_length:
            text = text[max_status_length:len(text)]
        else:
            text = ""
        # Increase the post counter
        status_num += 1

        expected_posts.append(get_a_final_queue_post_instance({
            "text": text_to_post,
            "date": message_7.date,
            "identification": identification,
            "language": instance.DEFAULT_LANGUAGE
        }))

    posts_to_publish = instance.post_process_for_source(source, posts)

    for idx in range(0,len(expected_posts)):
        dd(posts_to_publish[idx].raw_content)
        dd(expected_posts[idx].raw_content)
        assert isinstance(posts_to_publish[idx], QueuePost)
        assert posts_to_publish[idx].id == expected_posts[idx].id
        assert posts_to_publish[idx].raw_content == expected_posts[idx].raw_content
        assert posts_to_publish[idx].group == expected_posts[idx].group
        assert posts_to_publish[idx].published_at == expected_posts[idx].published_at
        assert posts_to_publish[idx].language == expected_posts[idx].language

def test_post_process_for_source_long_message_is_split_and_grouped_with_media(message_7, message_6):

    # Let's force the split by setting short max length
    CONFIG["default"] = {"max_length": 56}

    source = CONFIG["telegram_parser"]["channels"][0]["name"]
    entity_id = str(abs(CONFIG["telegram_parser"]["channels"][0]["id"]))
    dialog = get_a_dialog_instance({"entity": {"id": entity_id}})

    instance = get_instance()
    
    posts = [
        get_a_queue_post_instance(
            message=message_7,
            dialog=dialog,
            language=instance.DEFAULT_LANGUAGE
        ),
        get_a_queue_post_instance(
            message=message_6,
            dialog=dialog,
            language=instance.DEFAULT_LANGUAGE
        )
    ]

    expected_posts = []
    text = message_7.text
    status_num = 1
    max_status_length = instance._TelegramParser__calculate_max_status_length()
    num_of_statuses_by_text = math.ceil(len(text) / max_status_length)
    identification = sha1(text.encode()).hexdigest()
    while text:
        # The text is sliced and have the 1/n footer added.
        text_to_post = Template(instance.TEMPLATE_BODY_WITH_THREAD).substitute(
            body=text[0:max_status_length],
            thread=Template(instance.TEMPLATE_THREAD_INFO).substitute(
                current=status_num,
                total=num_of_statuses_by_text
            )
        )
        # Reduce the available text
        if len(text) > max_status_length:
            text = text[max_status_length:len(text)]
        else:
            text = ""
        
        expected_posts.append(get_a_final_queue_post_instance({
            "text": text_to_post,
            "date": message_7.date,
            "identification": identification,
            "language": instance.DEFAULT_LANGUAGE,
            "media": [message_6] if status_num == 1 else []
        }))

        # Increase the post counter
        status_num += 1

    posts_to_publish = instance.post_process_for_source(source, posts)

    for idx in range(0,len(expected_posts)):
        assert isinstance(posts_to_publish[idx], QueuePost)
        assert posts_to_publish[idx].id == expected_posts[idx].id
        assert posts_to_publish[idx].raw_content["body"] == expected_posts[idx].raw_content["body"]
        assert posts_to_publish[idx].group == expected_posts[idx].group
        assert posts_to_publish[idx].published_at == expected_posts[idx].published_at
        assert posts_to_publish[idx].language == expected_posts[idx].language
        media_in_posts = posts_to_publish[idx].raw_content["telegram_media_messages"]
        media_in_expected_posts = expected_posts[idx].raw_content["telegram_media_messages"]
        assert len(media_in_posts) == len(media_in_expected_posts)
        if len(expected_posts[idx].raw_content["telegram_media_messages"]) > 0:
            for idx_media in range(0,len(media_in_expected_posts)):
                media_in_posts[idx_media].id == media_in_expected_posts[idx_media].id

def test_parse_media_post_has_no_media_then_just_initialise(message_1):
    post = get_a_final_queue_post_instance({
        "text": message_1.text,
        "date": message_1.date,
        "identification": None,
        "language": "ES_ca" 
    })

    instance = get_instance()

    assert post.media == None
    assert instance.parse_media(post) is None
    assert post.media == []

def test_parse_media_has_one_media(message_2):
    post = get_a_final_queue_post_instance({
        "text": message_2.text,
        "date": message_2.date,
        "identification": None,
        "language": "ES_ca",
        "media": [message_2]
    })
    path = f"storage/media/{message_2.file.name}.{message_2.file.ext}"

    instance = get_instance()

    assert post.media == None
    
    # Mock iter_messages to return a set of messages
    mock_download_media = Mock
    mock_download_media.return_value = path
    with patch.object(instance, "_download_media", new=mock_download_media):
        instance.parse_media(post)

    assert len(post.media) == 1
    assert isinstance(post.media[0], QueuePostMedia)
    assert post.media[0].path == path
    assert post.media[0].mime_type == message_2.file.mime_type

# @pytest.mark.asyncio
def test_parse_media_has_two_media(message_2, message_4):
    post = get_a_final_queue_post_instance({
        "text": message_2.text,
        "date": message_2.date,
        "identification": None,
        "language": "ES_ca",
        "media": [message_2, message_4]
    })
    path_2 = f"storage/media/{message_2.file.name}.{message_2.file.ext}"
    path_4 = f"storage/media/{message_4.file.media.id}.{message_4.file.ext}"

    instance = get_instance()

    assert post.media == None
    
    # Mock iter_messages to return a set of messages
    mock_loop_async_download = Mock()
    mock_loop_async_download.side_effect = [path_2, path_4]
    with patch.object(instance, "_loop_async_download", new=mock_loop_async_download):
        instance.parse_media(post)

    assert len(post.media) == 2
    assert isinstance(post.media[0], QueuePostMedia)
    assert isinstance(post.media[1], QueuePostMedia)
    assert post.media[0].path == path_2
    assert post.media[0].mime_type == message_2.file.mime_type
    assert post.media[1].path == path_4
    assert post.media[1].mime_type == message_4.file.mime_type

def test_format_post_for_source_show_name(message_1):

    source = CONFIG["telegram_parser"]["channels"][0]["name"]
    post = get_a_final_queue_post_instance({
        "text": message_1.text,
        "date": message_1.date,
        "identification": None,
        "language": "ES_ca" 
    })
    
    instance = get_instance()

    expected_body = Template(instance.TEMPLATE_BODY_WITH_ORIGIN).substitute(
        origin=source,
        body=post.raw_content["body"]
    )
    
    instance.format_post_for_source(source, post)

    assert post.text == expected_body

def test_format_post_for_source_no_show_name(message_1):

    CONFIG["telegram_parser"]["channels"][0]["show_name"] =  False
    source = CONFIG["telegram_parser"]["channels"][0]["name"]
    post = get_a_final_queue_post_instance({
        "text": message_1.text,
        "date": message_1.date,
        "identification": None,
        "language": "ES_ca" 
    })
    
    instance = get_instance()

    expected_body = post.raw_content["body"]
    
    instance.format_post_for_source(source, post)

    assert post.text == expected_body
