"""
Основной класс для работы с QUANTUM-PCI устройством
"""

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from contextlib import contextmanager
import logging

from .exceptions import DeviceNotFoundError, DeviceAccessError, ValidationError


@contextmanager
def timeout(duration):
    """Контекстный менеджер для операций с timeout"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {duration} seconds")
    
    # Сохраняем старый обработчик
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(duration)
    
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


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
        """Безопасный поиск пути к устройству с timeout и проверками"""
        
        self.logger.info("Starting safe device detection...")
        
        if device_path:
            path = Path(device_path)
            if path.exists():
                self.logger.info(f"Using specified device path: {path}")
                return path
            else:
                raise DeviceNotFoundError(f"Specified device path {device_path} does not exist")
        
        # Флаг обнаружения
        device_found = False
        found_device_path = None
        
        try:
            # Автоматический поиск в /sys/class/timecard/ без signal-based timeout
            timecard_path = Path("/sys/class/timecard")
            
            if timecard_path.exists() and timecard_path.is_dir():
                self.logger.info(f"Checking timecard directory: {timecard_path}")
                
                try:
                    # Получаем список директорий
                    device_dirs = [d for d in timecard_path.iterdir() 
                                 if d.is_dir() and d.name.startswith("ocp")]
                    
                    for device_dir in device_dirs:
                        self.logger.info(f"Checking device: {device_dir}")
                        
                        # Проверяем основные файлы устройства
                        essential_files = ["serialnum", "available_clock_sources"]
                        files_exist = []
                        
                        for file_name in essential_files:
                            file_path = device_dir / file_name
                            try:
                                # Убираем timeout для простых операций файловой системы
                                exists = file_path.exists() and file_path.is_file()
                                files_exist.append(exists)
                                if exists:
                                    # Проверяем возможность чтения
                                    file_path.read_text()
                                            
                            except (PermissionError, OSError) as e:
                                self.logger.warning(f"Cannot access {file_path}: {e}")
                                files_exist.append(False)
                        
                        # Если все основные файлы доступны
                        if all(files_exist):
                            found_device_path = device_dir
                            device_found = True
                            self.logger.info(f"Device found and verified: {device_dir}")
                            break
                        else:
                            self.logger.warning(f"Device {device_dir} failed verification")
                            
                except PermissionError as e:
                    self.logger.error(f"Permission denied accessing timecard directory: {e}")
                except OSError as e:
                    self.logger.error(f"OS error accessing timecard directory: {e}")
            else:
                self.logger.warning("Timecard directory not found or not accessible")
                    

            
        except Exception as e:
            self.logger.error(f"Unexpected error during device detection: {e}")
            device_found = False
        
        if device_found and found_device_path:
            self.logger.info("Device detection successful")
            return found_device_path
        else:
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
    
    def read_device_file(self, file_name: str, timeout_sec: int = 5) -> Optional[str]:
        """
        Безопасное чтение файла устройства с timeout и дополнительными проверками
        
        Args:
            file_name: Имя файла для чтения
            timeout_sec: Таймаут операции в секундах
            
        Returns:
            Содержимое файла или None при ошибке
        """
        try:
            file_path = self.device_path / file_name
            
            # Проверяем существование и доступность файла
            if not file_path.exists():
                self.logger.debug(f"File {file_name} does not exist")
                return None
                
            if not file_path.is_file():
                self.logger.debug(f"Path {file_name} is not a file")
                return None
            
            # Проверяем права доступа на чтение
            try:
                # Простая проверка доступности
                if not os.access(file_path, os.R_OK):
                    self.logger.warning(f"No read permission for {file_name}")
                    return None
            except OSError:
                self.logger.warning(f"Cannot check permissions for {file_name}")
                return None
            
            # Читаем файл с таймаутом
            start_time = time.time()
            try:
                with open(file_path, 'r') as f:
                    # Проверяем таймаут во время чтения
                    content = ""
                    while True:
                        if time.time() - start_time > timeout_sec:
                            self.logger.warning(f"Read timeout for {file_name}")
                            return None
                        
                        chunk = f.read(1024)  # Читаем по кускам
                        if not chunk:
                            break
                        content += chunk
                        
                        # Ограничиваем размер содержимого
                        if len(content) > 10240:  # 10KB максимум
                            self.logger.warning(f"File {file_name} too large, truncating")
                            break
                    
                    content = content.strip()
                    self.logger.debug(f"Read from {file_name}: {content}")
                    return content
                    
            except (OSError, IOError, UnicodeDecodeError) as e:
                self.logger.error(f"Error reading {file_name}: {e}")
                return None
                
        except Exception as e:
            self.logger.error(f"Unexpected error reading {file_name}: {e}")
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
    
    def set_sma_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Установка полной конфигурации SMA портов
        
        Args:
            config: Словарь с конфигурацией {'inputs': {...}, 'outputs': {...}}
            
        Returns:
            True при успехе
        """
        try:
            errors = []
            success_count = 0
            
            # Применение входных портов
            if 'inputs' in config:
                for port_name, signal in config['inputs'].items():
                    if signal and signal.lower() != 'none':
                        try:
                            port_num = int(port_name[-1])  # извлекаем номер из sma1, sma2, etc.
                            if self.set_sma_input(port_num, signal):
                                success_count += 1
                        except Exception as e:
                            errors.append(f"Failed to set {port_name} input to {signal}: {e}")
            
            # Применение выходных портов
            if 'outputs' in config:
                for port_name, signal in config['outputs'].items():
                    if signal and signal.lower() != 'none':
                        try:
                            port_num = int(port_name[3])  # извлекаем номер из sma1_out, sma2_out, etc.
                            if self.set_sma_output(port_num, signal):
                                success_count += 1
                        except Exception as e:
                            errors.append(f"Failed to set {port_name} output to {signal}: {e}")
            
            if errors:
                self.logger.warning(f"SMA configuration partially applied. Errors: {errors}")
                return False
            
            self.logger.info(f"SMA configuration applied successfully ({success_count} changes)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to apply SMA configuration: {e}")
            return False
    
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

    def is_connected(self) -> bool:
        """
        Проверка подключения устройства
        
        Returns:
            True если устройство подключено и доступно
        """
        try:
            # Проверяем существование пути устройства
            if not self.device_path.exists():
                return False
            
            # Проверяем доступность базовых файлов устройства
            serial = self.read_device_file("serialnum")
            return serial is not None and len(serial.strip()) > 0
            
        except Exception as e:
            self.logger.debug(f"Connection check failed: {e}")
            return False