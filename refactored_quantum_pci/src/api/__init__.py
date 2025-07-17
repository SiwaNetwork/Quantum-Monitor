"""
API модуль для работы с QUANTUM-PCI устройствами
"""

from .status_reader import StatusReader
from .web_api import WebAPI

__all__ = [
    "StatusReader",
    "WebAPI"
]