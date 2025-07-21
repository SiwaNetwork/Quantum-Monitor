"""
Менеджер конфигурации для QUANTUM-PCI устройств
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
import logging

from .exceptions import ConfigurationError, ValidationError


class ConfigManager:
    """Менеджер для работы с конфигурацией устройства"""
    
    def __init__(self, config_dir: Optional[Union[str, Path]] = None, logger: Optional[logging.Logger] = None):
        """
        Инициализация менеджера конфигурации
        
        Args:
            config_dir: Директория для сохранения конфигураций
            logger: Логгер для записи сообщений
        """
        self.logger = logger or logging.getLogger(__name__)
        self.config_dir = Path(config_dir) if config_dir else Path.home() / ".quantum_pci"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
    def save_config(self, config: Dict[str, Any], name: str, format: str = "json") -> bool:
        """
        Сохранение конфигурации в файл
        
        Args:
            config: Словарь конфигурации
            name: Имя конфигурации
            format: Формат файла ("json" или "yaml")
            
        Returns:
            True при успехе
        """
        try:
            # Добавление метаданных
            config_with_meta = {
                "metadata": {
                    "name": name,
                    "created_at": datetime.now().isoformat(),
                    "version": "2.0.0"
                },
                "configuration": config
            }
            
            if format.lower() == "json":
                file_path = self.config_dir / f"{name}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config_with_meta, f, indent=4, ensure_ascii=False)
            elif format.lower() == "yaml":
                file_path = self.config_dir / f"{name}.yaml"
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_with_meta, f, default_flow_style=False, allow_unicode=True)
            else:
                raise ConfigurationError(f"Unsupported format: {format}")
            
            self.logger.info(f"Configuration saved: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def load_config(self, name: str, format: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Загрузка конфигурации из файла
        
        Args:
            name: Имя конфигурации
            format: Формат файла (если не указан, определяется автоматически)
            
        Returns:
            Словарь конфигурации или None при ошибке
        """
        try:
            if format:
                file_path = self.config_dir / f"{name}.{format}"
            else:
                # Автоматическое определение формата
                json_path = self.config_dir / f"{name}.json"
                yaml_path = self.config_dir / f"{name}.yaml"
                
                if json_path.exists():
                    file_path = json_path
                    format = "json"
                elif yaml_path.exists():
                    file_path = yaml_path
                    format = "yaml"
                else:
                    self.logger.error(f"Configuration file not found: {name}")
                    return None
            
            if not file_path.exists():
                self.logger.error(f"Configuration file not found: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                if format == "json":
                    data = json.load(f)
                elif format == "yaml":
                    data = yaml.safe_load(f)
                else:
                    raise ConfigurationError(f"Unsupported format: {format}")
            
            # Валидация структуры
            if not isinstance(data, dict) or "configuration" not in data:
                raise ConfigurationError("Invalid configuration file structure")
            
            self.logger.info(f"Configuration loaded: {file_path}")
            return data["configuration"]
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            return None
    
    def list_configs(self) -> List[Dict[str, Any]]:
        """Получение списка сохраненных конфигураций"""
        configs = []
        
        for file_path in self.config_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "metadata" in data:
                        metadata = data["metadata"]
                        metadata["file_path"] = str(file_path)
                        metadata["format"] = "json"
                        configs.append(metadata)
            except Exception as e:
                self.logger.warning(f"Error reading config metadata from {file_path}: {e}")
        
        for file_path in self.config_dir.glob("*.yaml"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if "metadata" in data:
                        metadata = data["metadata"]
                        metadata["file_path"] = str(file_path)
                        metadata["format"] = "yaml"
                        configs.append(metadata)
            except Exception as e:
                self.logger.warning(f"Error reading config metadata from {file_path}: {e}")
        
        # Сортировка по времени создания
        configs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return configs
    
    def delete_config(self, name: str) -> bool:
        """
        Удаление конфигурации
        
        Args:
            name: Имя конфигурации
            
        Returns:
            True при успехе
        """
        try:
            deleted = False
            
            # Удаление JSON файла
            json_path = self.config_dir / f"{name}.json"
            if json_path.exists():
                json_path.unlink()
                deleted = True
                
            # Удаление YAML файла
            yaml_path = self.config_dir / f"{name}.yaml"
            if yaml_path.exists():
                yaml_path.unlink()
                deleted = True
            
            if deleted:
                self.logger.info(f"Configuration deleted: {name}")
                return True
            else:
                self.logger.warning(f"Configuration not found: {name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting configuration: {e}")
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Валидация конфигурации
        
        Args:
            config: Словарь конфигурации
            
        Returns:
            True если конфигурация валидна
        """
        try:
            # Базовая валидация структуры
            if not isinstance(config, dict):
                raise ValidationError("Configuration must be a dictionary")
            
            # Проверка обязательных секций
            required_sections = ["device_info", "clock_settings", "sma_settings"]
            for section in required_sections:
                if section not in config:
                    raise ValidationError(f"Missing required section: {section}")
            
            # Валидация настроек часов
            clock_settings = config["clock_settings"]
            if "source" in clock_settings:
                valid_sources = ["NONE", "PPS", "TOD", "IRIG", "DCF"]
                if clock_settings["source"] not in valid_sources:
                    raise ValidationError(f"Invalid clock source: {clock_settings['source']}")
            
            # Валидация SMA настроек
            sma_settings = config["sma_settings"]
            if "inputs" in sma_settings:
                for port, signal in sma_settings["inputs"].items():
                    if not port.startswith("sma") or not port[3:].isdigit():
                        raise ValidationError(f"Invalid SMA port name: {port}")
                    
                    port_num = int(port[3:])
                    if port_num < 1 or port_num > 4:
                        raise ValidationError(f"Invalid SMA port number: {port_num}")
            
            if "outputs" in sma_settings:
                for port, signal in sma_settings["outputs"].items():
                    if not port.startswith("sma") or not port[3:].isdigit():
                        raise ValidationError(f"Invalid SMA port name: {port}")
                    
                    port_num = int(port[3:])
                    if port_num < 1 or port_num > 4:
                        raise ValidationError(f"Invalid SMA port number: {port_num}")
            
            return True
            
        except ValidationError as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during validation: {e}")
            return False
    
    def create_default_config(self) -> Dict[str, Any]:
        """Создание конфигурации по умолчанию"""
        return {
            "device_info": {
                "name": "Default QUANTUM-PCI Configuration",
                "description": "Default configuration for QUANTUM-PCI device"
            },
            "clock_settings": {
                "source": "PPS",
                "utc_tai_offset": 37
            },
            "sma_settings": {
                "inputs": {
                    "sma1": "PPS1",
                    "sma2": "None",
                    "sma3": "None",
                    "sma4": "None"
                },
                "outputs": {
                    "sma1": "PHC",
                    "sma2": "GND",
                    "sma3": "GND",
                    "sma4": "GND"
                }
            },

        }