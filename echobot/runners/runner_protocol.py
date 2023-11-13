from typing import Protocol
from pyxavi.config import Config
import logging


class RunnerProtocol(Protocol):

    def __init__(
        self, config: Config = None, logger: logging = None, params: dict = None
    ) -> None:
        """Initializing the class"""

    def run(self) -> None:
        """Method that will be called to trigger the runner"""
