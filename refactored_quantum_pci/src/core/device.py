"""
Основной класс для работы с QUANTUM-PCI устройством
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import logging

from .exceptions import DeviceNotFoundError, DeviceAccessError, ValidationError


class QuantumPCIDevice:
    """Класс для работы с QUANTUM-PCI устройством"""
    
    def __init__(self, device_path: Optional[str] = None, logger: Optional[logging.Logger] = None):
        """
        Инициализация устройства
        
        Args:
            device_path: Путь к устройству (если не указан, происходит автопоиск)
            logger: Логгер для записи сообщений
        """
        self.logger = logger or logging.getLogger(__name__)
        self.device_path = self._find_device_path(device_path)
        self._validate_device()
        
    def _find_device_path(self, device_path: Optional[str] = None) -> Path:
        """Поиск пути к устройству"""
        if device_path:
            path = Path(device_path)
            if path.exists():
                self.logger.info(f"Using specified device path: {path}")
                return path
            else:
                raise DeviceNotFoundError(f"Specified device path {device_path} does not exist")
        
        # Автоматический поиск в /sys/class/timecard/
        timecard_base = Path("/sys/class/timecard")
        if timecard_base.exists():
            for device_dir in timecard_base.iterdir():
                if device_dir.is_dir() and device_dir.name.startswith("ocp"):
                    self.logger.info(f"Found device at: {device_dir}")
                    return device_dir
        
        raise DeviceNotFoundError("No QUANTUM-PCI device found")
    
    def _validate_device(self) -> None:
        """Валидация устройства"""
        if not self.device_path.exists():
            raise DeviceNotFoundError(f"Device path {self.device_path} does not exist")
        
        # Проверка основных файлов устройства
        required_files = ["serialnum", "available_clock_sources"]
        for file_name in required_files:
            file_path = self.device_path / file_name
            if not file_path.exists():
                raise DeviceAccessError(f"Required device file {file_name} not found")
    
    def read_device_file(self, file_name: str) -> Optional[str]:
        """
        Безопасное чтение файла устройства
        
        Args:
            file_name: Имя файла для чтения
            
        Returns:
            Содержимое файла или None при ошибке
        """
        try:
            file_path = self.device_path / file_name
            if file_path.exists() and file_path.is_file():
                with open(file_path, 'r') as f:
                    content = f.read().strip()
                    self.logger.debug(f"Read from {file_name}: {content}")
                    return content
        except (OSError, IOError) as e:
            self.logger.error(f"Error reading {file_name}: {e}")
            return None
    
    def write_device_file(self, file_name: str, value: str) -> bool:
        """
        Безопасная запись в файл устройства
        
        Args:
            file_name: Имя файла для записи
            value: Значение для записи
            
        Returns:
            True при успехе, False при ошибке
        """
        try:
            file_path = self.device_path / file_name
            if file_path.exists() and file_path.is_file():
                with open(file_path, 'w') as f:
                    f.write(str(value))
                    self.logger.info(f"Written to {file_name}: {value}")
                    return True
            else:
                self.logger.error(f"Device file {file_name} not found or not writable")
                return False
        except (OSError, IOError, PermissionError) as e:
            self.logger.error(f"Error writing to {file_name}: {e}")
            return False
    
    def get_device_info(self) -> Dict[str, Any]:
        """Получение информации об устройстве"""
        info = {
            "timestamp": datetime.now().isoformat(),
            "device_path": str(self.device_path),
            "serial_number": self.read_device_file("serialnum"),
            "available_clock_sources": self.get_available_clock_sources(),
            "current_clock_source": self.read_device_file("clock_source"),
            "gnss_sync": self.read_device_file("gnss_sync"),
            "available_sma_inputs": self.get_available_sma_inputs(),
            "available_sma_outputs": self.get_available_sma_outputs()
        }
        
        # Добавление дополнительной информации
        utc_tai_offset = self.read_device_file("utc_tai_offset")
        if utc_tai_offset:
            info["utc_tai_offset"] = utc_tai_offset
            
        return info
    
    def get_available_clock_sources(self) -> List[str]:
        """Получение списка доступных источников синхронизации"""
        sources = self.read_device_file("available_clock_sources")
        return sources.split() if sources else []
    
    def get_current_clock_source(self) -> Optional[str]:
        """Получение текущего источника синхронизации"""
        return self.read_device_file("clock_source")
    
    def set_clock_source(self, source: str) -> bool:
        """
        Установка источника синхронизации
        
        Args:
            source: Название источника синхронизации
            
        Returns:
            True при успехе
        """
        available_sources = self.get_available_clock_sources()
        if source not in available_sources:
            raise ValidationError(f"Invalid clock source: {source}. Available: {available_sources}")
        
        return self.write_device_file("clock_source", source)
    
    def get_available_sma_inputs(self) -> List[str]:
        """Получение списка доступных SMA входов"""
        inputs = self.read_device_file("available_sma_inputs")
        return inputs.split() if inputs else []
    
    def get_available_sma_outputs(self) -> List[str]:
        """Получение списка доступных SMA выходов"""
        outputs = self.read_device_file("available_sma_outputs")
        return outputs.split() if outputs else []
    
    def get_sma_configuration(self) -> Dict[str, Any]:
        """Получение конфигурации SMA портов"""
        config = {
            "timestamp": datetime.now().isoformat(),
            "inputs": {},
            "outputs": {}
        }
        
        for i in range(1, 5):
            # SMA входы
            input_value = self.read_device_file(f"sma{i}")
            if input_value is not None:
                config["inputs"][f"sma{i}"] = input_value
            
            # SMA выходы  
            output_value = self.read_device_file(f"sma{i}_out")
            if output_value is not None:
                config["outputs"][f"sma{i}"] = output_value
        
        return config
    
    def set_sma_input(self, port: int, signal: str) -> bool:
        """
        Установка сигнала на SMA вход
        
        Args:
            port: Номер порта (1-4)
            signal: Тип сигнала
            
        Returns:
            True при успехе
        """
        if port < 1 or port > 4:
            raise ValidationError(f"Invalid SMA port: {port}. Must be 1-4")
        
        available_inputs = self.get_available_sma_inputs()
        if signal not in available_inputs:
            raise ValidationError(f"Invalid SMA input: {signal}. Available: {available_inputs}")
        
        return self.write_device_file(f"sma{port}", signal)
    
    def set_sma_output(self, port: int, signal: str) -> bool:
        """
        Установка сигнала на SMA выход
        
        Args:
            port: Номер порта (1-4) 
            signal: Тип сигнала
            
        Returns:
            True при успехе
        """
        if port < 1 or port > 4:
            raise ValidationError(f"Invalid SMA port: {port}. Must be 1-4")
        
        available_outputs = self.get_available_sma_outputs()
        if signal not in available_outputs:
            raise ValidationError(f"Invalid SMA output: {signal}. Available: {available_outputs}")
        
        return self.write_device_file(f"sma{port}_out", signal)
    
    def get_clock_status(self) -> Dict[str, Any]:
        """Получение статуса часов"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "gnss_sync": self.read_device_file("gnss_sync"),
            "drift": self.read_device_file("clock_status_drift"),
            "offset": self.read_device_file("clock_status_offset")
        }
        return status
    
    def is_healthy(self) -> bool:
        """Проверка работоспособности устройства"""
        try:
            # Базовые проверки
            if not self.device_path.exists():
                return False
            
            # Проверка доступности основных файлов
            serial = self.read_device_file("serialnum")
            if not serial:
                return False
            
            # Проверка синхронизации GNSS (если доступна)
            gnss_sync = self.read_device_file("gnss_sync")
            if gnss_sync and gnss_sync == "0":
                self.logger.warning("GNSS not synchronized")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False