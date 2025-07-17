"""
GUI модуль для QUANTUM-PCI устройств
"""

from .main_window import QuantumPCIGUI
from .components.device_panel import DevicePanel
from .components.clock_panel import ClockPanel
from .components.sma_panel import SMAPanel

__all__ = [
    "QuantumPCIGUI",
    "DevicePanel",
    "ClockPanel", 
    "SMAPanel"
]