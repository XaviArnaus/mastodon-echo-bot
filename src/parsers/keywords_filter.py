from bundle.config import Config
from bs4 import BeautifulSoup
import logging

class KeywordsFilter:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
    
    def profile_allows_text(self, text: str, profile: str) -> bool:
        if profile not in self._config["keywords_filter.profiles"]:
            raise RuntimeError(f"Can find the profile [{profile}] in the config's Keyword Filters")
        
        keywords = self._config[f"keywords_filter.profiles.{profile}.keywords"]
        text = self._clean_text(text)

        for keyword in keywords:
            if keyword in text:
                return True
        
        return False
    
    def _clean_text(self, text: str) -> str:
        # Remove HTML
        text = ''.join(BeautifulSoup(text, "html.parser").findAll(text=True))

        # All text to lowercase
        text = text.lower()

        # Map characters
        mapping = {
            "à": "a",
            "á": "a",
            "è": "e",
            "é": "e",
            "ì": "i",
            "í": "i",
            "ò": "o",
            "ó": "o",
            "ù": "u",
            "ú": "u",
            "ç": "c",
            "ñ": "n"
        }
        text: text.translate(mapping)

        # Remove characters
        mapping = {
            "-": None,
            ".": None
        }
        text: text.translate(mapping)

        return text