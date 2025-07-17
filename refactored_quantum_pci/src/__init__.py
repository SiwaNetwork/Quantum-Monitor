"""
QUANTUM-PCI Refactored Package
Улучшенная архитектура для работы с платами QUANTUM-PCI
"""

__version__ = "2.0.0"
__author__ = "QUANTUM-PCI Development Team"

from .core.device import QuantumPCIDevice
from .core.config_manager import ConfigManager
from .api.status_reader import StatusReader

__all__ = [
    "QuantumPCIDevice",
    "ConfigManager", 
    "StatusReader"
]